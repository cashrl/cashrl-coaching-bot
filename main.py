"""
RLBotPro - Main Entry Point
Inicia o watchdog e o dashboard NiceGUI.

Instruções de uso:
1. pip install -r requirements.txt
2. Editar config.json com token e nick
3. python main.py (roda o app)

Empacotamento com PyInstaller:
pyinstaller --onefile --name "RLBotPro" --icon icone.ico --add-data "data;data" --add-data "config.json;." --hidden-import=watchdog --hidden-import=nicegui main.py

O RLBotPro.exe + config.json = programa portátil
"""
import json
import sys
from pathlib import Path
from typing import Optional

from nicegui import app, ui

from database import Database
from bot.uploader import BallchasingUploader
from bot.analyzer import ReplayAnalyzer
from bot.comparer import ProComparer
from bot.ai_coach import create_coach, AICoach
from dashboard.ui import Dashboard


class RLBotPro:
    """Classe principal do aplicativo RLBotPro."""

    def __init__(self):
        """Inicializa o aplicativo."""
        self.config: dict = {}
        self.db: Optional[Database] = None
        self.dashboard: Optional[Dashboard] = None
        self.comparer: Optional[ProComparer] = None
        self.ai_coach: Optional[AICoach] = None

    def load_config(self) -> bool:
        """
        Carrega o arquivo de configuração.

        Returns:
            True se carregou com sucesso
        """
        config_path = Path("config.json")

        if not config_path.exists():
            print("Arquivo config.json não encontrado!")
            print("Criando config.json com valores padrão...")

            default_config = {
                "ballchasing_token": "SEU_TOKEN",
                "player_name": "SEU_NICK",
                "replays_folder": "%UserProfile%/Documents/My Games/Rocket League/TAGame/Demos",
                "pro_to_study": "Zen",
                "playlists": ["ranked-doubles", "ranked-standard", "ranked-duels"],
                "theme": "dark",
                "auto_start_watcher": True
            }

            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)

            print("Por favor, edite config.json com seu token e nick.")
            return False

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)

            # Validações básicas
            if self.config.get('ballchasing_token') == 'SEU_TOKEN':
                print("AVISO: Token do Ballchasing não configurado!")
                print("Edite config.json com seu token.")

            if self.config.get('player_name') == 'SEU_NICK':
                print("AVISO: Nome do jogador não configurado!")
                print("Edite config.json com seu nick.")

            return True

        except json.JSONDecodeError as e:
            print(f"Erro ao ler config.json: {e}")
            return False
        except IOError as e:
            print(f"Erro ao acessar config.json: {e}")
            return False

    def init_database(self) -> bool:
        """
        Inicializa o banco de dados.

        Returns:
            True se inicializou com sucesso
        """
        try:
            self.db = Database("data/history.db")
            print("Banco de dados inicializado com sucesso!")
            self.db.clean_old_baselines()
            return True
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {e}")
            return False

    def init_comparer(self) -> bool:
        """
        Inicializa o comparador de pros.

        Returns:
            True se inicializou com sucesso
        """
        try:
            token = self.config.get('ballchasing_token', '')
            player_name = self.config.get('player_name', '')
            uploader = BallchasingUploader(token)
            analyzer = ReplayAnalyzer(player_name)
            self.comparer = ProComparer(uploader, analyzer, self.db)
            print("Comparador de pros inicializado!")
            return True
        except Exception as e:
            print(f"Erro ao inicializar comparador: {e}")
            return False

    def init_ai_coach(self) -> bool:
        """
        Inicializa o coach de IA (NVIDIA NIM).

        Returns:
            True se inicializou com sucesso
        """
        api_key = self.config.get('nvidia_api_key', '')
        self.ai_coach = create_coach(api_key)
        if self.ai_coach:
            print("AI Coach inicializado com sucesso!")
            return True
        else:
            print("AI Coach não disponível (configure nvidia_api_key no config.json)")
            return False

    def start_dashboard(self) -> None:
        """Inicia o dashboard NiceGUI."""
        self.dashboard = Dashboard(self.db, self.config, self.comparer, self.ai_coach)

        @ui.page('/')
        def index():
            self.dashboard.build()

        # Configurar janela nativa (pywebview)
        app.native.window_args['title'] = 'RLBot Pro'
        app.native.window_args['min_size'] = (900, 650)

        # Iniciar NiceGUI em janela nativa (pywebview)
        ui.run(
            native=True,
            window_size=(1280, 800),
            dark=True,
            reload=False,
        )

    def run(self) -> None:
        """Executa o aplicativo completo."""
        print("=" * 50)
        print("RLBot Pro - Iniciando...")
        print("=" * 50)

        # 1. Carregar configuração
        if not self.load_config():
            input("Pressione Enter para sair...")
            sys.exit(1)

        # 2. Inicializar banco de dados
        if not self.init_database():
            input("Pressione Enter para sair...")
            sys.exit(1)

        # 3. Inicializar comparador
        self.init_comparer()

        # 4. Inicializar AI Coach
        self.init_ai_coach()

        # 5. Iniciar dashboard
        print("\nIniciando dashboard...")
        print("Janela nativa será aberta automaticamente.")
        print("Para fechar, feche a janela do aplicativo.\n")

        try:
            self.start_dashboard()
        except KeyboardInterrupt:
            print("\nEncerrando aplicativo...")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Limpa recursos ao encerrar."""
        print("Fechando banco de dados...")
        if self.db:
            self.db.close()

        print("Aplicativo encerrado com sucesso!")


def main():
    """Função principal."""
    app = RLBotPro()
    app.run()


if __name__ == "__main__":
    main()
