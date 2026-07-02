"""
RLBotPro - Ballchasing API Client
Busca e baixa replays públicos de jogadores profissionais.

IMPORTANTE: Este módulo faz chamadas DIRETAS à API do Ballchasing.
Ele SÓ deve ser usado pela máquina do ADMIN (is_admin=True).
Usuários comuns NUNCA devem instanciar esta classe.

O baseline profissional para usuários comuns é baixado via GitHub Gist
(usando bot/baseline_sync.py), não diretamente do Ballchasing.
"""
import os
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Importar verificação de admin
try:
    from bot.baseline_sync import is_admin
except ImportError:
    # Fallback se baseline_sync não existir
    def is_admin(discord_id: str) -> bool:
        return False


class BallchasingClient:
    """
    Cliente para a API do Ballchasing (https://ballchasing.com/doc/api).
    
    IMPORTANTE: Esta classe SÓ deve ser usada pelo admin.
    Usuários comuns devem usar baseline_sync.get_pro_baseline().
    """

    BASE_URL = "https://ballchasing.com/api"

    # Rate limiting: free tier = 2 req/s, 500 req/hora (list), 1000 req/hora (detail)
    MIN_REQUEST_INTERVAL = 0.6  # segundos entre requests (conservador: ~1.6/s)
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0  # backoff exponencial

    def __init__(self, api_key: str, data_dir: str = "data", discord_id: Optional[str] = None):
        """
        Args:
            api_key: Token de autenticação do Ballchasing (gratuito, obtido em
                     https://ballchasing.com/upload após login).
            data_dir: Diretório base para armazenar replays baixados.
            discord_id: Discord ID do usuário (para verificação de admin).
        """
        # VERIFICAÇÃO DE SEGURANÇA: Somente admin pode usar este cliente
        if discord_id and not is_admin(discord_id):
            raise PermissionError(
                "ERRO DE SEGURANÇA: Somente o admin pode acessar a API do Ballchasing.\n"
                "Usuários comuns devem usar baseline_sync.get_pro_baseline().\n"
                "Esta restrição existe para evitar chamadas diretas à API."
            )
        
        if not HAS_REQUESTS:
            raise ImportError("Lib 'requests' não instalada. Execute: pip install requests")

        if not api_key:
            raise ValueError(
                "API key do Ballchasing não configurada.\n"
                "Obtenha em https://ballchasing.com/upload (após login).\n"
                "Adicione 'ballchasing_api_key' no config.json."
            )

        self.api_key = api_key
        self.data_dir = Path(data_dir)
        self.pro_replays_dir = self.data_dir / "pro_replays"
        self.pro_replays_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0.0

    def _rate_limit_wait(self) -> None:
        """Espera o intervalo mínimo entre requests para respeitar rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Faz uma request à API com rate limiting e retry com backoff.

        Args:
            method: 'GET', 'POST', etc.
            endpoint: caminho relativo (ex: '/replays')
            **kwargs: argumentos extras para requests

        Returns:
            JSON response ou None se falhou
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": self.api_key}

        for attempt in range(self.MAX_RETRIES):
            self._rate_limit_wait()
            try:
                resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)

                if resp.status_code == 200:
                    return resp.json()

                if resp.status_code == 429:
                    # Rate limited — backoff exponencial
                    wait = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                    print(f"  Rate limit atingido. Aguardando {wait:.0f}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code == 404:
                    print(f"  Não encontrado: {endpoint}")
                    return None

                print(f"  Erro HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            except requests.RequestException as e:
                print(f"  Erro de conexão (tentativa {attempt+1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BACKOFF_BASE ** (attempt + 1))

        print(f"  Falha após {self.MAX_RETRIES} tentativas: {endpoint}")
        return None

    def search_pro_replays(
        self,
        player_name: Optional[str] = None,
        playlist: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Busca replays públicos de jogadores com tag 'pro' (Liquipedia).

        Filtro nativo do Ballchasing: ?pro=true

        Args:
            player_name: Filtrar por nome específico do pro (opcional).
                         Se None, retorna replays de qualquer pro.
            playlist: Filtrar por playlist (ex: 'ranked-2v2', 'ranked-3v3').
                      O Ballchasing usa: ranked-1v1, ranked-2v2, ranked-3v3, etc.
            limit: Número máximo de replays para buscar (máx 50 por request).

        Returns:
            Lista de dicts com info de cada replay.
        """
        params = {
            "pro": "true",
            "sort": "replay-date",
            "direction": "desc",
            "count": min(limit, 50),
        }

        if player_name:
            params["player-name"] = player_name
        if playlist:
            params["playlist"] = playlist

        print(f"Buscando replays de pro" + (f" ({player_name})" if player_name else "") + "...")

        data = self._request("GET", "/replays", params=params)
        if not data:
            return []

        replays = data.get("list", [])
        print(f"  Encontrados {len(replays)} replays")
        return replays

    def get_replay_detail(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca detalhes completos de um replay específico.

        Args:
            replay_id: ID do replay no Ballchasing

        Returns:
            Dict com detalhes do replay ou None
        """
        return self._request("GET", f"/replays?id={replay_id}")

    def download_replay(self, replay: Dict[str, Any], pro_name: str) -> Optional[str]:
        """
        Baixa o arquivo .replay para data/pro_replays/{pro_name}/

        Args:
            replay: Dict com info do replay (precisa ter 'id' e 'link')
            pro_name: Nome do pro (usado como subpasta)

        Returns:
            Caminho local do arquivo baixado, ou None se falhou
        """
        replay_id = replay.get("id", "")
        link = replay.get("link", "")

        if not link:
            print(f"  Replay {replay_id} não tem link de download")
            return None

        # Criar pasta do pro
        pro_dir = self.pro_replays_dir / self._safe_dirname(pro_name)
        pro_dir.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo
        filename = self._replay_filename(replay)
        filepath = pro_dir / filename

        # Pular se já existe
        if filepath.exists():
            print(f"  Já existe: {filename}")
            return str(filepath)

        # Baixar
        self._rate_limit_wait()
        try:
            print(f"  Baixando: {filename}...")
            resp = requests.get(link, headers={"Authorization": self.api_key}, timeout=60, stream=True)

            if resp.status_code != 200:
                print(f"  Erro ao baixar: HTTP {resp.status_code}")
                return None

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"  Salvo: {filepath} ({size_mb:.1f} MB)")
            return str(filepath)

        except Exception as e:
            print(f"  Erro ao baixar replay: {e}")
            if filepath.exists():
                filepath.unlink()
            return None

    def download_pro_replays(
        self,
        pro_name: str,
        playlist: Optional[str] = None,
        max_replays: int = 10,
    ) -> List[str]:
        """
        Busca e baixa replays de um pro específico.

        Args:
            pro_name: Nome do pro para buscar
            playlist: Filtrar por playlist (opcional)
            max_replays: Número máximo de replays para baixar

        Returns:
            Lista de caminhos locais dos replays baixados
        """
        replays = self.search_pro_replays(
            player_name=pro_name,
            playlist=playlist,
            limit=max_replays,
        )

        if not replays:
            print(f"Nenhum replay encontrado para {pro_name}")
            return []

        downloaded = []
        for replay in replays[:max_replays]:
            path = self.download_replay(replay, pro_name)
            if path:
                downloaded.append(path)

        print(f"\nTotal baixado: {len(downloaded)}/{len(replays[:max_replays])} para {pro_name}")
        return downloaded

    def _replay_filename(self, replay: Dict) -> str:
        """Gera nome de arquivo para o replay."""
        replay_id = replay.get("id", "unknown")
        playlist = replay.get("playlist", "unknown")
        date = replay.get("replay_date", "")[:10]
        # Truncar ID para não ter nomes absurdamente longos
        short_id = replay_id[:12] if len(replay_id) > 12 else replay_id
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in short_id)
        return f"{playlist}_{date}_{safe_id}.replay"

    @staticmethod
    def _safe_dirname(name: str) -> str:
        """Converte nome em string segura para diretório."""
        return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip().replace(" ", "_")


def get_ballchasing_client(config: Dict[str, Any]) -> Optional[BallchasingClient]:
    """
    Factory: cria um BallchasingClient a partir do config.

    Args:
        config: Dict de configuração do app (precisa ter 'ballchasing_api_key')

    Returns:
        BallchasingClient ou None se não configurado
    """
    api_key = config.get("ballchasing_api_key", "")
    if not api_key or api_key == "SUA_API_KEY_BALLCHASING":
        print("API key do Ballchasing não configurada.")
        print("Adicione 'ballchasing_api_key' no config.json.")
        print("Obtenha em: https://ballchasing.com/upload (após login)")
        return None

    return BallchasingClient(api_key)


if __name__ == "__main__":
    # Teste rápido
    config_path = Path("config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    client = get_ballchasing_client(config)
    if client:
        # Buscar replays de Zen
        replays = client.search_pro_replays(player_name="Zen", limit=5)
        for r in replays:
            print(f"  {r.get('id', '?')[:12]} - {r.get('playlist', '?')} - {r.get('replay_date', '?')[:10]}")
