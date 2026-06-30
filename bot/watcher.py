"""
RLBotPro - Watchdog Module
Monitora a pasta de replays em tempo real.
"""
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, Any

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from bot.uploader import BallchasingUploader
from bot.analyzer import ReplayAnalyzer
from bot.comparer import ProComparer
from database import Database


class ReplayHandler(FileSystemEventHandler):
    """Handler para eventos de criação de arquivos .replay."""

    def __init__(self, uploader: BallchasingUploader, analyzer: ReplayAnalyzer,
                 comparer: ProComparer, db: Database, 
                 on_replay_processed: Optional[Callable] = None):
        """
        Inicializa o handler.
        
        Args:
            uploader: Instância do BallchasingUploader
            analyzer: Instância do ReplayAnalyzer
            comparer: Instância do ProComparer
            db: Instância do Database
            on_replay_processed: Callback quando um replay é processado
        """
        self.uploader = uploader
        self.analyzer = analyzer
        self.comparer = comparer
        self.db = db
        self.on_replay_processed = on_replay_processed
        self._processing_files = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Chamado quando um novo arquivo é criado.
        
        Args:
            event: Evento do watchdog
        """
        if event.is_directory:
            return

        file_path = event.src_path
        
        # Verificar se é um arquivo .replay
        if not file_path.lower().endswith('.replay'):
            return

        # Evitar processar o mesmo arquivo múltiplas vezes
        if file_path in self._processing_files:
            return
        
        self._processing_files.add(file_path)
        
        # Processar em uma thread separada para não bloquear
        thread = threading.Thread(
            target=self._process_replay,
            args=(file_path,),
            daemon=True
        )
        thread.start()

    def _process_replay(self, file_path: str) -> None:
        """
        Processa um replay completo.
        
        Args:
            file_path: Caminho para o arquivo .replay
        """
        try:
            print(f"Novo replay detectado: {os.path.basename(file_path)}")
            
            # Esperar 2s para garantir que o arquivo terminou de ser escrito
            time.sleep(2)
            
            # Verificar se o arquivo ainda existe
            if not os.path.exists(file_path):
                print(f"Arquivo desapareceu: {file_path}")
                return
            
            # Upload para Ballchasing
            replay_id = self.uploader.upload_replay(file_path)
            
            if not replay_id:
                print(f"Falha no upload: {os.path.basename(file_path)}")
                return
            
            # Buscar detalhes do replay
            replay_data = self.uploader.get_replay_details(replay_id)
            
            if not replay_data:
                print(f"Falha ao buscar detalhes: {replay_id}")
                return
            
            # Analisar o replay
            player_stats = self.analyzer.analyze_replay(replay_data)
            
            if not player_stats:
                print(f"Falha ao analisar replay: {replay_id}")
                return
            
            # Comparar com baseline do pro atual
            config = self._load_config()
            pro_name = config.get('pro_to_study', 'Zen')
            playlist = player_stats.get('playlist', 'ranked-doubles')
            
            # Buscar baseline do pro
            pro_baseline = self.comparer.fetch_specific_pro_baseline(pro_name, playlist)
            
            # Se não encontrar baseline específica, usar média geral
            if not pro_baseline:
                pro_baseline = self.comparer.fetch_pro_baseline(playlist)
            
            # Calcular score de proximidade
            comparison = self.comparer.compare(player_stats, pro_baseline)
            proximity_score = comparison.get('score', 0)
            
            # Adicionar score de proximidade às stats
            player_stats['proximity_score'] = proximity_score
            
            # Salvar no banco de dados
            self.db.insert_match(player_stats)
            
            print(f"Replay processado com sucesso: {replay_id}")
            print(f"Score de proximidade: {proximity_score:.1f}%")
            
            # Chamar callback se existir
            if self.on_replay_processed:
                self.on_replay_processed(player_stats)
            
        except Exception as e:
            print(f"Erro ao processar replay {file_path}: {e}")
        finally:
            self._processing_files.discard(file_path)

    def _load_config(self) -> dict:
        """Carrega o config.json."""
        import json
        config_path = Path("config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}


class ReplayWatcher:
    """Classe principal para monitorar a pasta de replays."""

    def __init__(self, config: dict, db: Database,
                 on_replay_processed: Optional[Callable] = None):
        """
        Inicializa o watcher.
        
        Args:
            config: Configuração do aplicativo
            db: Instância do Database
            on_replay_processed: Callback quando um replay é processado
        """
        self.config = config
        self.db = db
        self.on_replay_processed = on_replay_processed
        self.observer: Optional[Observer] = None
        
        # Inicializar componentes
        token = config.get('ballchasing_token', '')
        self.uploader = BallchasingUploader(token)
        self.analyzer = ReplayAnalyzer(config.get('player_name', ''))
        self.comparer = ProComparer(self.uploader, self.analyzer, db)

    def _resolve_path(self, path: str) -> str:
        """
        Resolve variáveis de ambiente no caminho.
        
        Args:
            path: Caminho com possíveis variáveis de ambiente
            
        Returns:
            Caminho resolvido
        """
        # Substituir %UserProfile% pelo caminho real
        if '%UserProfile%' in path:
            user_profile = os.path.expanduser('~')
            path = path.replace('%UserProfile%', user_profile)
        
        # Substituir outras variáveis comuns
        path = os.path.expandvars(path)
        
        return path

    def start(self) -> bool:
        """
        Inicia o monitoramento da pasta de replays.
        
        Returns:
            True se iniciou com sucesso
        """
        if self.observer and self.observer.is_alive():
            print("Watcher já está rodando")
            return False
        
        # Resolver caminho da pasta
        replays_folder = self.config.get('replays_folder', '')
        replays_folder = self._resolve_path(replays_folder)
        
        if not os.path.exists(replays_folder):
            print(f"Pasta não encontrada: {replays_folder}")
            print("Criando pasta...")
            os.makedirs(replays_folder, exist_ok=True)
        
        print(f"Monitorando pasta: {replays_folder}")
        
        # Criar handler
        handler = ReplayHandler(
            uploader=self.uploader,
            analyzer=self.analyzer,
            comparer=self.comparer,
            db=self.db,
            on_replay_processed=self.on_replay_processed
        )
        
        # Iniciar observer
        self.observer = Observer()
        self.observer.schedule(handler, replays_folder, recursive=False)
        self.observer.start()
        
        print("Watcher iniciado com sucesso!")
        return True

    def stop(self) -> None:
        """Para o monitoramento."""
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            print("Watcher parado")

    def is_running(self) -> bool:
        """
        Verifica se o watcher está rodando.
        
        Returns:
            True se estiver rodando
        """
        return self.observer is not None and self.observer.is_alive()

    def process_pending_uploads(self) -> int:
        """
        Processa uploads pendentes na fila.
        
        Returns:
            Número de uploads processados
        """
        processed_ids = self.uploader.process_pending_uploads()
        return len(processed_ids)

    def force_baseline_refresh(self, pro_name: Optional[str] = None) -> bool:
        """
        Força atualização da baseline.
        
        Args:
            pro_name: Nome do pro (None para todos)
            
        Returns:
            True se atualizou com sucesso
        """
        try:
            playlist = self.config.get('playlists', ['ranked-doubles'])[0]
            
            if pro_name:
                self.comparer.fetch_specific_pro_baseline(pro_name, playlist)
            else:
                self.comparer.fetch_pro_baseline(playlist)
            
            return True
        except Exception as e:
            print(f"Erro ao atualizar baseline: {e}")
            return False
