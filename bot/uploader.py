"""
RLBotPro - Uploader Module
Gerencia o upload de replays para a API do Ballchasing.
"""
import os
import time
import json
import requests
from typing import Optional, Dict, Any
from pathlib import Path


class BallchasingUploader:
    """Classe para gerenciar uploads de replays para o Ballchasing."""

    BASE_URL = "https://ballchasing.com/api"
    
    # Rate limiting: 2 req/s, 500 req/h
    MIN_REQUEST_INTERVAL = 0.5  # 500ms entre requests
    MAX_REQUESTS_PER_HOUR = 500
    
    def __init__(self, token: str):
        """
        Inicializa o uploader com o token de autenticação.
        
        Args:
            token: Token de autenticação do Ballchasing
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"Authorization": token})
        
        # Controle de rate limiting
        self._last_request_time = 0
        self._requests_this_hour = 0
        self._hour_start = time.time()
        
        # Fila de uploads pendentes (para offline mode)
        self._pending_uploads: list[Dict[str, Any]] = []
        self._load_pending_uploads()

    def _rate_limit(self) -> None:
        """Aplica rate limiting entre requests."""
        current_time = time.time()
        
        # Reset contador a cada hora
        if current_time - self._hour_start > 3600:
            self._requests_this_hour = 0
            self._hour_start = current_time
        
        # Verificar limite por hora
        if self._requests_this_hour >= self.MAX_REQUESTS_PER_HOUR:
            wait_time = 3600 - (current_time - self._hour_start)
            print(f"Rate limit atingido. Aguardando {wait_time:.0f}s...")
            time.sleep(wait_time)
            self._requests_this_hour = 0
            self._hour_start = time.time()
        
        # Intervalo mínimo entre requests
        elapsed = current_time - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        
        self._last_request_time = time.time()
        self._requests_this_hour += 1

    def _load_pending_uploads(self) -> None:
        """Carrega uploads pendentes do arquivo de cache."""
        cache_file = Path("data/pending_uploads.json")
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self._pending_uploads = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._pending_uploads = []

    def _save_pending_uploads(self) -> None:
        """Salva uploads pendentes no arquivo de cache."""
        cache_file = Path("data/pending_uploads.json")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cache_file, 'w') as f:
                json.dump(self._pending_uploads, f, indent=2)
        except IOError as e:
            print(f"Erro ao salvar uploads pendentes: {e}")

    def upload_replay(self, file_path: str) -> Optional[str]:
        """
        Faz upload de um replay para o Ballchasing.
        
        Args:
            file_path: Caminho para o arquivo .replay
            
        Returns:
            ID do replay ou None se falhou
        """
        if not os.path.exists(file_path):
            print(f"Arquivo não encontrado: {file_path}")
            return None

        try:
            self._rate_limit()
            
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                response = self.session.post(
                    f"{self.BASE_URL}/v2/upload",
                    files=files,
                    timeout=30
                )

            # Replay duplicado - ignorar
            if response.status_code == 409:
                print(f"Replay já existe no Ballchasing: {os.path.basename(file_path)}")
                return None

            response.raise_for_status()
            data = response.json()
            replay_id = data.get('id')
            
            if replay_id:
                print(f"Upload concluído: {replay_id}")
                return replay_id
            else:
                print("Upload falhou: ID não retornado")
                return None

        except requests.exceptions.ConnectionError:
            print("Erro de conexão - salvando para upload posterior")
            self._queue_upload(file_path)
            return None
        except requests.exceptions.Timeout:
            print("Timeout no upload - salvando para upload posterior")
            self._queue_upload(file_path)
            return None
        except requests.exceptions.RequestException as e:
            print(f"Erro no upload: {e}")
            self._queue_upload(file_path)
            return None

    def _queue_upload(self, file_path: str) -> None:
        """
        Adiciona um upload à fila para processamento posterior.
        
        Args:
            file_path: Caminho para o arquivo .replay
        """
        self._pending_uploads.append({
            'file_path': file_path,
            'queued_at': time.time(),
            'attempts': 0
        })
        self._save_pending_uploads()
        print(f"Upload adicionado à fila: {os.path.basename(file_path)}")

    def process_pending_uploads(self) -> list[str]:
        """
        Processa uploads pendentes na fila.
        
        Returns:
            Lista de IDs dos replays processados com sucesso
        """
        if not self._pending_uploads:
            return []

        processed_ids = []
        remaining = []

        for upload in self._pending_uploads:
            file_path = upload['file_path']
            
            if not os.path.exists(file_path):
                print(f"Arquivo não encontrado, removendo da fila: {file_path}")
                continue

            replay_id = self.upload_replay(file_path)
            if replay_id:
                processed_ids.append(replay_id)
            else:
                upload['attempts'] += 1
                if upload['attempts'] < 3:  # Máximo 3 tentativas
                    remaining.append(upload)
                else:
                    print(f"Máximo de tentativas atingido: {file_path}")

        self._pending_uploads = remaining
        self._save_pending_uploads()
        
        return processed_ids

    def get_replay_details(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca detalhes completos de um replay.
        
        Args:
            replay_id: ID do replay no Ballchasing
            
        Returns:
            Dicionário com os dados do replay ou None
        """
        try:
            self._rate_limit()
            response = self.session.get(
                f"{self.BASE_URL}/replays/{replay_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar detalhes do replay {replay_id}: {e}")
            return None

    def get_pro_replays(self, playlist: str, count: int = 200) -> list[Dict[str, Any]]:
        """
        Busca replays de jogadores profissionais.
        
        Args:
            playlist: Nome da playlist
            count: Quantidade de replays para buscar
            
        Returns:
            Lista de replays de pros
        """
        try:
            self._rate_limit()
            response = self.session.get(
                f"{self.BASE_URL}/replays",
                params={
                    'pro': 'true',
                    'playlist': playlist,
                    'count': min(count, 200)  # Limite da API
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('list', [])
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar replays de pros: {e}")
            return []

    def get_player_replays(self, player_name: str, playlist: str, 
                           count: int = 200) -> list[Dict[str, Any]]:
        """
        Busca replays de um jogador específico.
        
        Args:
            player_name: Nome do jogador
            playlist: Nome da playlist
            count: Quantidade de replays para buscar
            
        Returns:
            Lista de replays do jogador
        """
        try:
            self._rate_limit()
            response = self.session.get(
                f"{self.BASE_URL}/replays",
                params={
                    'player-name': player_name,
                    'playlist': playlist,
                    'count': min(count, 200)
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('list', [])
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar replays de {player_name}: {e}")
            return []

    @property
    def pending_count(self) -> int:
        """ Retorna o número de uploads pendentes."""
        return len(self._pending_uploads)
