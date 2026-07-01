"""
RLBotPro - Main Entry Point
Coach de Rocket League com AI + análise de replay local.

Instruções de uso:
1. pip install -r requirements.txt
2. Editar config.json com nvidia_api_key
3. python main.py (roda o app)

Empacotamento com PyInstaller:
pyinstaller --onefile --name "RLBotPro" --icon icone.ico --add-data "data;data" --add-data "config.json;." main.py
"""
import json
import sys
from pathlib import Path
from typing import Optional

from nicegui import app, ui

from database import Database
from bot.local_analyzer import LocalReplayAnalyzer
from bot.ai_coach import create_coach, AICoach
from dashboard.ui import Dashboard


class RLBotPro:
    def __init__(self):
        self.config: dict = {}
        self.db: Optional[Database] = None
        self.dashboard: Optional[Dashboard] = None
        self.ai_coach: Optional[AICoach] = None

    def load_config(self) -> bool:
        config_path = Path("config.json")

        if not config_path.exists():
            print("Criando config.json com valores padrão...")
            default_config = {
                "player_name": "SEU_NICK",
                "nvidia_api_key": "SUA_API_KEY_NVIDIA",
                "replays_folder": "%UserProfile%/Documents/My Games/Rocket League/TAGame/Demos",
                "theme": "dark"
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print("Edite config.json com sua API key NVIDIA.")
            return False

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erro ao ler config.json: {e}")
            return False

    def init_database(self) -> bool:
        try:
            self.db = Database("data/history.db")
            print("Banco de dados inicializado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {e}")
            return False

    def init_ai_coach(self) -> bool:
        api_key = self.config.get('nvidia_api_key', '')
        self.ai_coach = create_coach(api_key)
        if self.ai_coach:
            print("AI Coach inicializado com sucesso!")
            return True
        else:
            print("AI Coach não disponível (configure nvidia_api_key no config.json)")
            return False

    def start_dashboard(self) -> None:
        self.dashboard = Dashboard(self.db, self.config, None, self.ai_coach)

        @ui.page('/')
        def index():
            self.dashboard.build()

        ui.run(dark=True, reload=False, port=8000)

    def run(self) -> None:
        print("=" * 50)
        print("RLBot Pro - Iniciando...")
        print("=" * 50)

        if not self.load_config():
            input("Pressione Enter para sair...")
            sys.exit(1)

        if not self.init_database():
            input("Pressione Enter para sair...")
            sys.exit(1)

        self.init_ai_coach()

        print("\nIniciando dashboard...")
        print("Acesse http://localhost:8000 no browser\n")

        try:
            self.start_dashboard()
        except KeyboardInterrupt:
            print("\nEncerrando aplicativo...")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        if self.db:
            self.db.close()
        print("Aplicativo encerrado com sucesso!")


def main():
    app = RLBotPro()
    app.run()


if __name__ == "__main__":
    main()
