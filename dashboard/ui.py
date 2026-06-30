"""
RLBotPro - Dashboard Module
Interface Flet para visualização de estatísticas e comparação com pros.
Design baseado no Google Stitch.
"""
import flet as ft
from flet.controls.padding import Padding
from flet.controls.border import Border, BorderSide
from flet.controls.alignment import Alignment
from flet.controls.margin import Margin
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from database import Database
from bot.comparer import ProComparer


# Cores do tema escuro
COLORS = {
    'background': '#0f1117',
    'surface': '#1a1d27',
    'card': '#1e2230',
    'card_hover': '#252836',
    'primary': '#2563eb',
    'primary_hover': '#3b82f6',
    'primary_gradient': ['#2563eb', '#1d4ed8'],
    'accent': '#8b5cf6',
    'accent_gradient': ['#8b5cf6', '#7c3aed'],
    'cyan': '#06b6d4',
    'cyan_gradient': ['#06b6d4', '#0891b2'],
    'success': '#10b981',
    'success_gradient': ['#10b981', '#059669'],
    'warning': '#f59e0b',
    'warning_gradient': ['#f59e0b', '#d97706'],
    'error': '#ef4444',
    'text': '#f1f5f9',
    'text_secondary': '#94a3b8',
    'text_muted': '#64748b',
    'border': '#2a2d3a',
    'border_light': '#374151',
    'sidebar': '#111318',
    'sidebar_active': '#1e2230',
    'hover': '#252836',
    'shadow': '#000000',
    'glow_primary': '#2563eb33',
    'glow_accent': '#8b5cf633',
    'glow_cyan': '#06b6d433',
    'glow_success': '#10b98133',
}


class Dashboard:
    """Classe principal do dashboard Flet."""

    def __init__(self, db: Database, config: dict, comparer: Optional['ProComparer'] = None):
        self.db = db
        self.config = config
        self.comparer = comparer
        self.page: Optional[ft.Page] = None

        # Componentes da UI
        self.status_indicator = None
        self.status_text = None
        self.boost_card_value = None
        self.proximity_card_value = None
        self.proximity_progress = None
        self.matches_today_value = None
        self.tips_list = None
        self.comparison_list = None
        self.table_rows = []
        self.sidebar_items = []
        self.nav_index = 0

    def build(self, page: ft.Page) -> None:
        self.page = page
        page.title = "RLBot Pro"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = COLORS['background']
        page.padding = 0
        page.window.width = 1200
        page.window.height = 750
        page.window.min_width = 800
        page.window.min_height = 600

        # Container principal que será atualizado
        self.main_container = ft.Container(expand=True)

        # Loading overlay
        self.loading_overlay = ft.Container(
            content=ft.Column(
                controls=[
                    ft.ProgressRing(
                        width=40, height=40,
                        stroke_width=4,
                        color=COLORS['primary']
                    ),
                    ft.Container(height=16),
                    ft.Text("Carregando...", size=14, color=COLORS['text_secondary'])
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            bgcolor=COLORS['background'] + 'E0',
            expand=True,
            visible=False
        )

        page.add(
            ft.Stack(
                controls=[
                    ft.Row(
                        controls=[
                            self._build_sidebar(),
                            ft.VerticalDivider(width=1, color=COLORS['border']),
                            self.main_container
                        ],
                        expand=True,
                        spacing=0
                    ),
                    self.loading_overlay
                ],
                expand=True
            )
        )
        self._show_dashboard()

    def _show_loading(self, show: bool) -> None:
        """Mostra/esconde o loading overlay."""
        if self.loading_overlay:
            self.loading_overlay.visible = show
            if self.page:
                self.page.update()

    # ── SIDEBAR ────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> ft.Container:
        nav_items = [
            (ft.Icons.DASHBOARD_ROUNDED, "Dashboard", "Visão geral das estatísticas", self._show_dashboard),
            (ft.Icons.ANALYTICS_ROUNDED, "Análises", "Análises detalhadas de performance", self._show_analyses),
            (ft.Icons.HISTORY_ROUNDED, "Histórico", "Todas as partidas jogadas", self._show_history),
            (ft.Icons.SETTINGS_ROUNDED, "Config", "Configurações do aplicativo", self._show_settings),
        ]

        self.sidebar_items = []
        self._nav_controls = []
        
        for i, (icon, label, tooltip, callback) in enumerate(nav_items):
            is_active = i == self.nav_index
            item = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(icon, size=20,
                                color=COLORS['primary'] if is_active else COLORS['text_muted']),
                        ft.Text(label, size=13,
                                color=COLORS['text'] if is_active else COLORS['text_muted'],
                                weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL)
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                bgcolor=COLORS['sidebar_active'] if is_active else 'transparent',
                border_radius=8,
                padding=Padding.symmetric(horizontal=14, vertical=10),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ink=True,
                on_click=lambda e, idx=i, cb=callback: self._on_nav_click(idx, cb)
            )
            self.sidebar_items.append((item, i))
            self._nav_controls.append(item)

        logo = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.SPORTS_ESPORTS_ROUNDED, size=22, color='white'),
                        bgcolor=COLORS['primary'],
                        border_radius=8,
                        width=36,
                        height=36,
                        alignment=Alignment.CENTER
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("RLBot", size=16, weight=ft.FontWeight.BOLD, color=COLORS['text']),
                            ft.Text("Pro Analytics", size=10, color=COLORS['text_muted'])
                        ],
                        spacing=0
                    )
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=Padding.only(bottom=20, left=2, right=2)
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    logo,
                    ft.Divider(height=1, color=COLORS['border']),
                    ft.Container(height=8),
                    ft.Text("Menu", size=10, color=COLORS['text_muted'], weight=ft.FontWeight.W_600),
                    ft.Container(height=4),
                    ft.Column(controls=self._nav_controls, spacing=2),
                    ft.Container(expand=True),
                    self._build_sidebar_status()
                ],
                spacing=0
            ),
            width=220,
            bgcolor=COLORS['sidebar'],
            padding=Padding.symmetric(horizontal=12, vertical=16)
        )

    def _build_sidebar_status(self) -> ft.Container:
        self.status_indicator = ft.Container(
            content=ft.Container(
                bgcolor=COLORS['success'],
                width=8,
                height=8,
                border_radius=4
            )
        )
        self.status_text = ft.Text("Monitorando...", size=11, color=COLORS['text_secondary'])

        return ft.Container(
            content=ft.Row(
                controls=[
                    self.status_indicator,
                    self.status_text
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=Padding.symmetric(horizontal=8, vertical=10),
            bgcolor=COLORS['surface'],
            border_radius=8
        )

    def _on_nav_click(self, index: int, callback) -> None:
        """Callback quando clica em um item do sidebar."""
        self.nav_index = index
        
        # Atualizar visual dos itens
        for item, i in self.sidebar_items:
            is_active = i == index
            item.bgcolor = COLORS['sidebar_active'] if is_active else 'transparent'
            item.content.controls[0].color = COLORS['primary'] if is_active else COLORS['text_muted']
            item.content.controls[1].color = COLORS['text'] if is_active else COLORS['text_muted']
            item.content.controls[1].weight = ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL
        
        # Chamar callback para mostrar conteúdo
        callback()
        
        if self.page:
            self.page.update()

    def _show_dashboard(self) -> None:
        """Mostra o dashboard principal."""
        self.main_container.content = self._build_main_content()
        self._refresh_data()

    def _show_analyses(self) -> None:
        """Mostra a página de análises com seletor de replay e métricas."""
        # Container para resultados da análise
        self.analysis_results_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ANALYTICS_ROUNDED, size=48, color=COLORS['text_muted']),
                    ft.Text("Selecione um replay para analisar", size=16, color=COLORS['text_muted']),
                    ft.Text("Escolha um replay da lista abaixo ou clique para atualizar", 
                            size=12, color=COLORS['text_muted'])
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8
            ),
            expand=True,
            alignment=Alignment.CENTER
        )
        
        # Carregar replays disponíveis
        self.replay_dropdown = ft.Dropdown(
            width=400,
            bgcolor=COLORS['surface'],
            color=COLORS['text'],
            border_color=COLORS['border'],
            focused_border_color=COLORS['primary'],
            label_style=ft.TextStyle(color=COLORS['text_secondary']),
            text_style=ft.TextStyle(color=COLORS['text']),
            on_change=self._on_replay_dropdown_change
        )
        self._load_replay_list()
        
        self.main_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    # Header
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ANALYTICS_ROUNDED, size=24, color=COLORS['accent']),
                            ft.Text("Análises Detalhadas", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text']),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=16),
                    
                    # Seleção de replay
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, size=20, color=COLORS['text_secondary']),
                                self.replay_dropdown,
                                ft.Container(
                                    content=ft.Icon(ft.Icons.REFRESH_ROUNDED, size=18, color='white'),
                                    bgcolor=COLORS['primary'],
                                    border_radius=8,
                                    width=36,
                                    height=36,
                                    alignment=Alignment.CENTER,
                                    on_click=lambda _: self._load_replay_list()
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        bgcolor=COLORS['surface'],
                        border_radius=12,
                        padding=Padding.all(12),
                        border=Border.all(1, COLORS['border_light'])
                    ),
                    ft.Container(height=20),
                    
                    # Resultados da análise
                    self.analysis_results_container
                ],
                expand=True
            ),
            expand=True,
            padding=Padding.symmetric(horizontal=24, vertical=16)
        )

    def _load_replay_list(self) -> None:
        """Carrega a lista de replays disponíveis."""
        import os
        
        replay_folder = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "My Games",
            "Rocket League",
            "TAGame",
            "Demos"
        )
        
        if not os.path.exists(replay_folder):
            self.replay_dropdown.options = [
                ft.dropdown.Option(key="none", text="Pasta de replays não encontrada")
            ]
            return
        
        replay_files = [f for f in os.listdir(replay_folder) if f.endswith(".replay")]
        replay_files.sort(key=lambda x: os.path.getmtime(os.path.join(replay_folder, x)), reverse=True)
        
        if not replay_files:
            self.replay_dropdown.options = [
                ft.dropdown.Option(key="none", text="Nenhum replay encontrado")
            ]
            return
        
        options = []
        for f in replay_files[:20]:  # Limitar a 20 replays
            # Formatar nome: pegar data de modificação
            mtime = os.path.getmtime(os.path.join(replay_folder, f))
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            display_name = f"{date_str} - {f[:30]}..."
            options.append(ft.dropdown.Option(key=f, text=display_name))
        
        self.replay_dropdown.options = options
        if options:
            self.replay_dropdown.value = options[0].key
        self.page.update()

    def _on_replay_dropdown_change(self, e) -> None:
        """Callback quando um replay é selecionado no dropdown."""
        if not e.control.value or e.control.value == "none":
            return
        
        import os
        replay_folder = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "My Games",
            "Rocket League",
            "TAGame",
            "Demos"
        )
        replay_path = os.path.join(replay_folder, e.control.value)
        self._analyze_replay(replay_path)

    def _analyze_replay(self, replay_path: str) -> None:
        """Analisa o replay selecionado e mostra os resultados."""
        from bot.local_analyzer import LocalReplayAnalyzer, HAS_SUBTR
        
        if not HAS_SUBTR:
            self.analysis_results_container.content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ERROR_ROUNDED, size=48, color=COLORS['error']),
                    ft.Text("subtr-actor não instalado", size=16, color=COLORS['error']),
                    ft.Text("Execute: uv pip install subtr-actor-py", size=12, color=COLORS['text_muted'])
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8
            )
            self.page.update()
            return
        
        # Mostrar loading
        self.analysis_results_container.content = ft.Column(
            controls=[
                ft.ProgressRing(width=40, height=40, stroke_width=4, color=COLORS['primary']),
                ft.Container(height=8),
                ft.Text("Analisando replay...", size=14, color=COLORS['text_secondary'])
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )
        self.page.update()
        
        # Analisar replay
        try:
            analyzer = LocalReplayAnalyzer(self.config.get('player_name', ''))
            result = analyzer.analyze_replay(replay_path)
            
            if result:
                self._show_analysis_results(result)
            else:
                self.analysis_results_container.content = ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.WARNING_ROUNDED, size=48, color=COLORS['warning']),
                        ft.Text("Não foi possível analisar o replay", size=16, color=COLORS['warning']),
                        ft.Text("Verifique se o jogador está no replay", size=12, color=COLORS['text_muted'])
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8
                )
                self.page.update()
        except Exception as ex:
            self.analysis_results_container.content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ERROR_ROUNDED, size=48, color=COLORS['error']),
                    ft.Text("Erro na análise", size=16, color=COLORS['error']),
                    ft.Text(str(ex), size=12, color=COLORS['text_muted'])
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8
            )
            self.page.update()

    def _show_analysis_results(self, result: Dict[str, Any]) -> None:
        """Mostra os resultados da análise do replay."""
        # Extrair dados
        goals = result.get('goals', 0)
        assists = result.get('assists', 0)
        saves = result.get('saves', 0)
        shots = result.get('shots', 0)
        score = result.get('player_score', 0)
        demos = result.get('demos_inflicted', 0)
        
        # Dados do jogo
        game_mode = result.get('game_mode', '?')
        map_name = result.get('map_name', '?')
        team_score = result.get('score', '0-0')
        duration = result.get('duration_seconds', 0)
        duration_min = int(duration // 60)
        duration_sec = int(duration % 60)
        
        # Métricas avançadas
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near_ball = result.get('time_near_ball_pct', 0)
        time_offensive = result.get('time_offensive_pct', 0)
        
        # Determinar resultado (vitória/derrota)
        scores = team_score.split('-')
        if len(scores) == 2:
            try:
                my_score = int(scores[0])
                their_score = int(scores[1])
                won = my_score > their_score
            except:
                won = False
        else:
            won = False
        
        # Gerar dicas baseadas nas stats
        tips = self._generate_analysis_tips(result)
        
        # Construir UI
        controls = [
            # Header com resultado
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text("VITÓRIA" if won else "DERROTA", 
                                        size=14, weight=ft.FontWeight.BOLD, color='white'),
                        bgcolor=COLORS['success'] if won else COLORS['error'],
                        border_radius=8,
                        padding=Padding.symmetric(horizontal=12, vertical=6)
                    ),
                    ft.Text(f"{game_mode} • {map_name}", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"{duration_min}:{duration_sec:02d}", size=14, color=COLORS['text_muted']),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            ft.Container(height=16),
            
            # Placar
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(team_score, size=32, weight=ft.FontWeight.BOLD, color=COLORS['text']),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                bgcolor=COLORS['surface'],
                border_radius=12,
                padding=Padding.all(16),
                border=Border.all(1, COLORS['border_light'])
            ),
            ft.Container(height=20),
            
            # Stats principais
            ft.Text("ESTÁTISTICAS", size=12, weight=ft.FontWeight.W_700, 
                    color=COLORS['text_secondary']),
            ft.Container(height=8),
            ft.Row(
                controls=[
                    self._build_analysis_stat_card("GOLS", str(goals), COLORS['primary']),
                    self._build_analysis_stat_card("ASSISTÊNCIAS", str(assists), COLORS['cyan']),
                    self._build_analysis_stat_card("DEFESAS", str(saves), COLORS['warning']),
                    self._build_analysis_stat_card("CHUTES", str(shots), COLORS['text_muted']),
                    self._build_analysis_stat_card("DEMOS", str(demos), COLORS['error']),
                ],
                spacing=10,
                expand=True
            ),
            ft.Container(height=20),
            
            # Métricas avançadas
            ft.Text("MÉTRICAS AVANÇADAS", size=12, weight=ft.FontWeight.W_700, 
                    color=COLORS['text_secondary']),
            ft.Container(height=8),
            ft.Row(
                controls=[
                    self._build_analysis_metric_card(
                        "DISTÂNCIA À BOLA", 
                        f"{avg_dist:.0f}", 
                        "unidades",
                        COLORS['cyan']
                    ),
                    self._build_analysis_metric_card(
                        "TEMPO PERTO DA BOLA", 
                        f"{time_near_ball:.1f}", 
                        "%",
                        COLORS['primary']
                    ),
                    self._build_analysis_metric_card(
                        "TEMPO NO ATAQUE", 
                        f"{time_offensive:.1f}", 
                        "%",
                        COLORS['warning']
                    ),
                ],
                spacing=10,
                expand=True
            ),
            ft.Container(height=20),
            
            # Dicas
            ft.Text("DICAS DE MELHORIA", size=12, weight=ft.FontWeight.W_700, 
                    color=COLORS['text_secondary']),
            ft.Container(height=8),
        ]
        
        # Adicionar dicas
        for tip in tips:
            controls.append(self._build_tip_card(tip))
        
        self.analysis_results_container.content = ft.Column(
            controls=controls,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        self.page.update()

    def _build_analysis_stat_card(self, title: str, value: str, color: str) -> ft.Container:
        """Card de stat para a análise."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(title, size=10, weight=ft.FontWeight.W_600, 
                            color=COLORS['text_secondary']),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4
            ),
            bgcolor=COLORS['surface'],
            border_radius=12,
            padding=Padding.all(16),
            border=Border.all(1, COLORS['border_light']),
            expand=True
        )

    def _build_analysis_metric_card(self, title: str, value: str, unit: str, color: str) -> ft.Container:
        """Card de métrica avançada para a análise."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(unit, size=12, color=COLORS['text_muted']),
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    ft.Text(title, size=10, weight=ft.FontWeight.W_600, 
                            color=COLORS['text_secondary']),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4
            ),
            bgcolor=COLORS['surface'],
            border_radius=12,
            padding=Padding.all(16),
            border=Border.all(1, COLORS['border_light']),
            expand=True
        )

    def _build_tip_card(self, tip: Dict[str, str]) -> ft.Container:
        """Card de dica de melhoria."""
        icon_map = {
            'success': ft.Icons.CHECK_CIRCLE_ROUNDED,
            'warning': ft.Icons.WARNING_ROUNDED,
            'error': ft.Icons.ERROR_ROUNDED,
            'info': ft.Icons.INFO_ROUNDED
        }
        color_map = {
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'error': COLORS['error'],
            'info': COLORS['primary']
        }
        
        tip_type = tip.get('type', 'info')
        icon = icon_map.get(tip_type, ft.Icons.LIGHTBULB_ROUNDED)
        color = color_map.get(tip_type, COLORS['primary'])
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=20, color=color),
                    ft.Column(
                        controls=[
                            ft.Text(tip.get('title', ''), size=13, weight=ft.FontWeight.W_600, 
                                    color=COLORS['text']),
                            ft.Text(tip.get('message', ''), size=12, color=COLORS['text_secondary']),
                        ],
                        spacing=2,
                        expand=True
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START
            ),
            bgcolor=COLORS['surface'],
            border_radius=10,
            padding=Padding.all(12),
            border=Border.all(1, COLORS['border_light']),
            margin=Margin(bottom=8)
        )

    def _generate_analysis_tips(self, result: Dict[str, Any]) -> list:
        """Gera dicas de melhoria baseadas nas stats da análise."""
        tips = []
        
        goals = result.get('goals', 0)
        assists = result.get('assists', 0)
        saves = result.get('saves', 0)
        shots = result.get('shots', 0)
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near_ball = result.get('time_near_ball_pct', 0)
        time_offensive = result.get('time_offensive_pct', 0)
        
        # Dicas de boost
        if avg_dist > 1500:
            tips.append({
                'type': 'warning',
                'title': 'Muito longe da bola',
                'message': f'Sua distância média à bola foi {avg_dist:.0f}. Tente ficar mais perto para ter mais contato com a jogada.'
            })
        elif avg_dist < 500:
            tips.append({
                'type': 'success',
                'title': 'Boa proximidade',
                'message': f'Você ficou perto da bola ({avg_dist:.0f}). Continue assim!'
            })
        
        # Dicas de posicionamento
        if time_near_ball < 30:
            tips.append({
                'type': 'warning',
                'title': 'Pouco tempo com a bola',
                'message': f'Você passou apenas {time_near_ball:.1f}% do tempo perto da bola. Tente se posicionar melhor.'
            })
        
        if time_offensive > 60:
            tips.append({
                'type': 'success',
                'title': 'Bom tempo no ataque',
                'message': f'Você passou {time_offensive:.1f}% do tempo no ataque. Continue pressionando!'
            })
        elif time_offensive < 40:
            tips.append({
                'type': 'info',
                'title': 'Mais tempo no ataque',
                'message': f'Você passou apenas {time_offensive:.1f}% no ataque. Tente subir mais quando tiver oportunidade.'
            })
        
        # Dicas de eficiência
        if shots > 0 and goals == 0:
            tips.append({
                'type': 'warning',
                'title': 'Melhore a finalização',
                'message': f'Você chutou {shots} vezes mas não marcou. Pratique a finalização.'
            })
        elif goals > 0 and shots > 0:
            conversion = (goals / shots) * 100
            if conversion > 50:
                tips.append({
                    'type': 'success',
                    'title': 'Ótima conversão',
                    'message': f'Você converteu {conversion:.0f}% dos chutes em gols!'
                })
            else:
                tips.append({
                    'type': 'info',
                    'title': 'Conversão razoável',
                    'message': f'Você converteu {conversion:.0f}% dos chutes. Tente ser mais preciso.'
                })
        
        # Dicas de defesa
        if saves > 2:
            tips.append({
                'type': 'success',
                'title': 'Boa defesa',
                'message': f'Você fez {saves} defesas. Continue protegendo o gol!'
            })
        
        # Dicas gerais
        if not tips:
            tips.append({
                'type': 'info',
                'title': 'Continue jogando',
                'message': 'Jogue mais partidas para receber dicas mais detalhadas!'
            })
        
        return tips

    def _show_history(self) -> None:
        """Mostra o histórico de partidas."""
        self.main_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY_ROUNDED, size=24, color=COLORS['primary']),
                            ft.Text("Histórico de Partidas", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text']),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=20),
                    self._build_history_content()
                ],
                expand=True
            ),
            expand=True,
            padding=Padding.symmetric(horizontal=24, vertical=16)
        )

    def _build_history_content(self) -> ft.Container:
        """Conteúdo da página de histórico."""
        # Buscar todas as partidas
        matches = self.db.get_matches(limit=50)
        
        if not matches:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.INBOX_ROUNDED, size=48, color=COLORS['text_muted']),
                        ft.Text("Nenhuma partida registrada", size=16, color=COLORS['text_muted']),
                        ft.Text("Jogue partidas para vê-las aqui", size=12, color=COLORS['text_muted'])
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8
                ),
                expand=True,
                alignment=Alignment.CENTER
            )
        
        # Criar lista de partidas expandíveis
        history_items = []
        for match in matches:
            item = self._build_expandable_match(match)
            history_items.append(item)
        
        return ft.Container(
            content=ft.Column(
                controls=history_items,
                spacing=8,
                scroll=ft.ScrollMode.AUTO
            ),
            expand=True
        )

    def _build_expandable_match(self, match: dict) -> ft.Container:
        """Cria um item de partida expandível."""
        result = match.get('result', '')
        result_color = COLORS['success'] if result == 'win' else COLORS['error']
        result_label = "Vitória" if result == 'win' else "Derrota"
        prox = match.get('proximity_score', 0) or 0
        
        # Container do conteúdo expandido (inicialmente oculto)
        expanded_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Divider(height=1, color=COLORS['border']),
                    ft.Container(height=8),
                    ft.Text("Detalhes da Partida", size=12, weight=ft.FontWeight.W_600,
                            color=COLORS['text']),
                    ft.Container(height=8),
                    # Informações do lobby
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.GROUP_ROUNDED, size=16, color=COLORS['primary']),
                            ft.Text("Lobby", size=12, weight=ft.FontWeight.W_600,
                                    color=COLORS['text'])
                        ],
                        spacing=8
                    ),
                    ft.Container(height=4),
                    ft.Text(f"Playlist: {match.get('playlist', 'N/A')}", size=11,
                            color=COLORS['text_secondary']),
                    ft.Text(f"Oponentes: {match.get('opponent_rank', 'N/A')}", size=11,
                            color=COLORS['text_secondary']),
                    ft.Container(height=12),
                    # Métricas detalhadas
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ANALYTICS_ROUNDED, size=16, color=COLORS['cyan']),
                            ft.Text("Métricas", size=12, weight=ft.FontWeight.W_600,
                                    color=COLORS['text'])
                        ],
                        spacing=8
                    ),
                    ft.Container(height=4),
                    self._build_match_metrics(match),
                    ft.Container(height=8),
                    # Dados brutos
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CODE_ROUNDED, size=16, color=COLORS['warning']),
                            ft.Text("Dados Raw", size=12, weight=ft.FontWeight.W_600,
                                    color=COLORS['text'])
                        ],
                        spacing=8
                    ),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Text(
                            f"Replay ID: {match.get('replay_id', 'N/A')}",
                            size=10, color=COLORS['text_muted'],
                            selectable=True
                        ),
                        bgcolor=COLORS['surface'],
                        border_radius=6,
                        padding=Padding.all(8)
                    )
                ],
                spacing=0
            ),
            bgcolor=COLORS['surface'],
            border_radius=8,
            padding=Padding.all(12),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
        )
        
        # Estado de expansão
        is_expanded = [False]
        
        def on_click(e):
            is_expanded[0] = not is_expanded[0]
            expanded_content.visible = is_expanded[0]
            expand_icon.rotation = ft.Rotate(
                angle=3.14159 if is_expanded[0] else 0
            )
            e.control.update()
        
        # Ícone de expansão
        expand_icon = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=20,
                              color=COLORS['text_muted'])
        
        # Container principal
        main_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Text(result_label[0], size=14, color='white', 
                                              weight=ft.FontWeight.BOLD),
                                bgcolor=result_color,
                                width=36,
                                height=36,
                                border_radius=10,
                                alignment=Alignment.CENTER
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(result_label, size=14, color=COLORS['text'],
                                            weight=ft.FontWeight.W_700),
                                    ft.Text(f"{match.get('date', '')[:10]} | {match.get('playlist', 'N/A')}", 
                                            size=11, color=COLORS['text_muted'])
                                ],
                                spacing=2,
                                expand=True
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(f"{match.get('goals', 0)}G {match.get('assists', 0)}A {match.get('saves', 0)}S", 
                                            size=13, color=COLORS['text_secondary'],
                                            weight=ft.FontWeight.W_500),
                                    ft.Text(f"Score: {match.get('score', 0)}", size=11, color=COLORS['text_muted'])
                                ],
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.END
                            ),
                            ft.Container(
                                content=ft.Text(f"{prox:.0f}%", size=13, color='white',
                                              weight=ft.FontWeight.W_700),
                                bgcolor=COLORS['cyan'],
                                border_radius=8,
                                padding=Padding.symmetric(horizontal=10, vertical=5)
                            ),
                            expand_icon
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    expanded_content
                ],
                spacing=0
            ),
            bgcolor=COLORS['card'],
            border=Border.all(1, COLORS['border']),
            border_radius=12,
            padding=Padding.symmetric(horizontal=16, vertical=14),
            on_click=on_click,
            on_hover=lambda e: self._on_history_hover(e)
        )
        
        # Inicialmente oculto
        expanded_content.visible = False
        
        return main_content

    def _build_match_metrics(self, match: dict) -> ft.Container:
        """Constroi as métricas detalhadas de uma partida."""
        metrics = [
            ("Boost Médio", f"{match.get('boost_avg', 0):.1f}", COLORS['warning']),
            ("Velocidade", f"{match.get('avg_speed', 0):.0f} u/s", COLORS['primary']),
            ("Dist. Bola", f"{match.get('avg_distance_to_ball', 0):.0f}m", COLORS['accent']),
            ("Supersônico", f"{match.get('time_supersonic', 0):.1f}s", COLORS['cyan']),
        ]
        
        metric_items = []
        for label, value, color in metrics:
            metric_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Container(bgcolor=color, width=4, height=4, border_radius=2),
                                width=8, height=8, alignment=Alignment.CENTER
                            ),
                            ft.Text(label, size=11, color=COLORS['text_muted']),
                            ft.Container(expand=True),
                            ft.Text(value, size=12, color=COLORS['text'],
                                    weight=ft.FontWeight.W_600)
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    bgcolor=COLORS['card'],
                    border_radius=6,
                    padding=Padding.symmetric(horizontal=10, vertical=6)
                )
            )
        
        return ft.Container(
            content=ft.Column(controls=metric_items, spacing=4),
            bgcolor=COLORS['card'],
            border_radius=8,
            padding=Padding.all(8),
            border=Border.all(1, COLORS['border'])
        )

    def _on_history_hover(self, e) -> None:
        """Efeito hover nos itens do histórico."""
        if e.data == 'true':
            e.control.bgcolor = COLORS['card_hover']
            e.control.border = Border.all(1, COLORS['primary'] + '40')
        else:
            e.control.bgcolor = COLORS['card']
            e.control.border = Border.all(1, COLORS['border'])
        e.control.update()

    def _on_growth_row_hover(self, e) -> None:
        """Efeito hover nas linhas da tabela de evolução."""
        if e.data == 'true':
            e.control.bgcolor = COLORS['surface']
            e.control.border = Border.all(1, COLORS['primary'] + '40')
        else:
            e.control.bgcolor = 'transparent'
            e.control.border = Border.all(1, COLORS['border'])
        e.control.update()

    def _show_settings(self) -> None:
        """Mostra a página de configurações."""
        self.main_container.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SETTINGS_ROUNDED, size=24, color=COLORS['warning']),
                            ft.Text("Configurações", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text']),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=20),
                    self._build_settings_content()
                ],
                expand=True
            ),
            expand=True,
            padding=Padding.symmetric(horizontal=24, vertical=16)
        )

    def _build_settings_content(self) -> ft.Container:
        """Conteúdo da página de configurações."""
        # Switches de configuração
        switch_monitoring = ft.Switch(
            label="Monitoramento Automático",
            value=self.config.get('auto_start_watcher', True),
            active_color=COLORS['success'],
            thumb_color='white',
            inactive_thumb_color=COLORS['text_muted']
        )
        switch_notifications = ft.Switch(
            label="Notificações",
            value=self.config.get('notifications', False),
            active_color=COLORS['primary'],
            thumb_color='white',
            inactive_thumb_color=COLORS['text_muted']
        )
        switch_auto_upload = ft.Switch(
            label="Auto-Upload para Ballchasing",
            value=self.config.get('auto_upload', False),
            active_color=COLORS['accent'],
            thumb_color='white',
            inactive_thumb_color=COLORS['text_muted']
        )

        # Botão salvar
        save_btn = ft.ElevatedButton(
            content=ft.Text("Salvar Configurações", color='white'),
            icon=ft.Icons.SAVE_ROUNDED,
            on_click=lambda _: self._save_settings(switch_monitoring, 
                                                     switch_notifications, switch_auto_upload),
            bgcolor=COLORS['success'],
            color='white',
            width=300
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Preferências", size=14, weight=ft.FontWeight.W_700,
                                        color=COLORS['text']),
                                ft.Container(height=8),
                                switch_monitoring,
                                switch_notifications,
                                switch_auto_upload,
                                ft.Container(height=20),
                                save_btn
                            ],
                            spacing=4
                        ),
                        bgcolor=COLORS['card'],
                        border=Border.all(1, COLORS['border_light']),
                        border_radius=16,
                        padding=Padding.all(24),
                        width=400,
                        shadow=ft.BoxShadow(
                            spread_radius=0,
                            blur_radius=12,
                            color=COLORS['shadow'] + '30',
                            offset=ft.Offset(0, 4)
                        )
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            expand=True
        )

    def _save_settings(self, switch_monitoring, switch_notifications, switch_auto_upload) -> None:
        """Salva as configurações."""
        self.config['auto_start_watcher'] = switch_monitoring.value
        self.config['notifications'] = switch_notifications.value
        self.config['auto_upload'] = switch_auto_upload.value
        
        config_path = Path("config.json")
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            config_data['auto_start_watcher'] = switch_monitoring.value
            config_data['notifications'] = switch_notifications.value
            config_data['auto_upload'] = switch_auto_upload.value
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Mostrar mensagem de sucesso
        self._show_snackbar("Configurações salvas com sucesso!")
        self._refresh_data()

    def _show_snackbar(self, message: str) -> None:
        """Mostra uma mensagem de notificação."""
        if self.page:
            self.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(message, color='white'),
                    bgcolor=COLORS['success']
                )
            )
            self.page.overlay[-1].open = True
            self.page.update()

    # ── MAIN CONTENT ───────────────────────────────────────────────────────

    def _build_main_content(self) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    self._build_top_bar(),
                    ft.Container(height=16),
                    self._build_stats_row(),
                    ft.Container(height=16),
                    self._build_chart_section(),
                    ft.Container(height=16),
                    self._build_bottom_section()
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO
            ),
            bgcolor=COLORS['background'],
            expand=True,
            padding=Padding.symmetric(horizontal=24, vertical=16)
        )

    def _build_top_bar(self) -> ft.Row:
        # Tabs de playlist
        self.playlist_tabs = self._build_playlist_tabs()
        
        return ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Dashboard", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text']),
                        ft.Text("Acompanhe suas estatísticas e evolução", size=12, color=COLORS['text_muted'])
                    ],
                    spacing=4
                ),
                ft.Container(expand=True),
                self.playlist_tabs
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def _build_playlist_tabs(self) -> ft.Container:
        """Constroi as abas de filtro por playlist."""
        self.current_playlist = None
        self.playlist_buttons = []
        
        playlists = [
            ("Todas", None),
            ("2v2", "ranked-doubles"),
            ("3v3", "ranked-standard"),
            ("1v1", "ranked-duels"),
        ]
        
        buttons = []
        for label, playlist in playlists:
            is_active = playlist is None  # "Todas" ativo por padrão
            btn = ft.Container(
                content=ft.Text(
                    label, 
                    size=11, 
                    color=COLORS['text'] if is_active else COLORS['text_muted'],
                    weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500
                ),
                bgcolor=COLORS['primary'] if is_active else 'transparent',
                border_radius=8,
                padding=Padding.symmetric(horizontal=14, vertical=8),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                on_click=lambda e, p=playlist: self._on_playlist_change(p)
            )
            self.playlist_buttons.append((btn, playlist))
            buttons.append(btn)
        
        return ft.Container(
            content=ft.Row(controls=buttons, spacing=4),
            bgcolor=COLORS['surface'],
            border_radius=10,
            padding=Padding.all(4),
            border=Border.all(1, COLORS['border'])
        )

    def _on_playlist_change(self, playlist: Optional[str]) -> None:
        """Callback quando muda a playlist selecionada."""
        self.current_playlist = playlist
        
        # Atualizar visual dos botões
        for btn, pl in self.playlist_buttons:
            is_active = pl == playlist
            btn.bgcolor = COLORS['primary'] if is_active else 'transparent'
            btn.content.color = COLORS['text'] if is_active else COLORS['text_muted']
            btn.content.weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500
        
        # Atualizar dados com filtro
        self._refresh_data()
        
        if self.page:
            self.page.update()

    # ── STAT CARDS ─────────────────────────────────────────────────────────

    def _build_stats_row(self) -> ft.Row:
        self.boost_card_value = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=COLORS['warning'])
        boost_card = self._build_stat_card(
            icon=ft.Icons.BOLT_ROUNDED,
            icon_color=COLORS['warning'],
            title="BOOST MÉDIO",
            value_widget=self.boost_card_value,
            subtitle="pads coletados por partida",
            gradient_colors=COLORS['warning_gradient'],
            tooltip="Média de boost coletado por partida"
        )

        self.proximity_card_value = ft.Text("0%", size=32, weight=ft.FontWeight.BOLD, color=COLORS['cyan'])
        self.proximity_progress = ft.ProgressBar(
            width=160, height=6, color=COLORS['cyan'], bgcolor=COLORS['surface'], value=0
        )
        proximity_card = self._build_stat_card(
            icon=ft.Icons.TRENDING_UP_ROUNDED,
            icon_color=COLORS['cyan'],
            title="PROXIMIDADE",
            value_widget=self.proximity_card_value,
            subtitle="vs pro estudado",
            extra_widget=self.proximity_progress,
            gradient_colors=COLORS['cyan_gradient'],
            tooltip="Quão próximo você está do nível profissional"
        )

        self.matches_today_value = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=COLORS['primary'])
        matches_card = self._build_stat_card(
            icon=ft.Icons.PLAY_CIRCLE_ROUNDED,
            icon_color=COLORS['primary'],
            title="PARTIDAS HOJE",
            value_widget=self.matches_today_value,
            subtitle="jogadas",
            gradient_colors=COLORS['primary_gradient'],
            tooltip="Número de partidas jogadas hoje"
        )

        return ft.Row(
            controls=[boost_card, proximity_card, matches_card],
            spacing=14,
            expand=True
        )

    def _build_stat_card(self, icon, icon_color, title, value_widget,
                         subtitle="", extra_widget=None, gradient_colors=None, tooltip=None) -> ft.Container:
        # Container do ícone com glow effect
        icon_container = ft.Container(
            content=ft.Icon(icon, size=18, color='white'),
            bgcolor=icon_color,
            border_radius=10,
            width=38,
            height=38,
            alignment=Alignment.CENTER,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=icon_color + '40',
                offset=ft.Offset(0, 2)
            )
        )

        # Título com estilo melhorado
        title_widget = ft.Text(
            title, 
            size=11, 
            color=COLORS['text_secondary'],
            weight=ft.FontWeight.W_600
        )

        # Linha do cabeçalho
        header = ft.Row(
            controls=[
                icon_container,
                title_widget
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Valor principal com tamanho maior
        if hasattr(value_widget, 'size'):
            value_widget.size = 32
            value_widget.weight = ft.FontWeight.BOLD

        controls = [header, value_widget]
        
        if subtitle:
            controls.append(
                ft.Text(
                    subtitle, 
                    size=10, 
                    color=COLORS['text_muted'],
                    weight=ft.FontWeight.W_400
                )
            )
        if extra_widget:
            controls.append(extra_widget)

        # Card principal com sombra e gradiente sutil
        return ft.Container(
            content=ft.Column(controls=controls, spacing=8),
            expand=True,
            bgcolor=COLORS['card'],
            border=Border.all(1, COLORS['border_light']),
            border_radius=16,
            padding=Padding.symmetric(horizontal=18, vertical=16),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=COLORS['shadow'] + '40',
                offset=ft.Offset(0, 4)
            ),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            on_hover=lambda e: self._on_card_hover(e, icon_color)
        )

    def _on_card_hover(self, e, accent_color: str) -> None:
        """Efeito hover nos cards."""
        if e.data == 'true':
            e.control.border = Border.all(1, accent_color + '60')
            e.control.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=16,
                color=accent_color + '30',
                offset=ft.Offset(0, 4)
            )
        else:
            e.control.border = Border.all(1, COLORS['border_light'])
            e.control.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=COLORS['shadow'] + '40',
                offset=ft.Offset(0, 4)
            )
        e.control.update()

    # ── CHART SECTION ──────────────────────────────────────────────────────

    def _build_chart_section(self) -> ft.Row:
        return ft.Row(
            controls=[
                self._build_evolution_charts(),
                self._build_comparison_panel()
            ],
            spacing=14,
            expand=True
        )

    def _build_evolution_charts(self) -> ft.Container:
        """Constrói os gráficos de evolução."""
        from dashboard.charts import create_evolution_chart, CHART_COLORS
        
        # Placeholder para gráficos (será preenchido com dados reais)
        self.evolution_charts = ft.Column(spacing=12, expand=True)
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(ft.Icons.TRENDING_UP_ROUNDED, size=16, color='white'),
                                bgcolor=COLORS['success'],
                                border_radius=8,
                                width=32,
                                height=32,
                                alignment=Alignment.CENTER
                            ),
                            ft.Text("Evolução", size=15, weight=ft.FontWeight.W_700,
                                    color=COLORS['text']),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=12),
                    ft.Divider(height=1, color=COLORS['border']),
                    ft.Container(height=12),
                    self.evolution_charts
                ],
                spacing=0,
                expand=True
            ),
            expand=True,
            bgcolor=COLORS['card'],
            border=Border.all(1, COLORS['border_light']),
            border_radius=16,
            padding=Padding.symmetric(horizontal=20, vertical=18),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=COLORS['shadow'] + '30',
                offset=ft.Offset(0, 4)
            )
        )

    def _update_evolution_charts(self, matches: list) -> None:
        """Atualiza os gráficos de evolução com novos dados."""
        from dashboard.charts import create_evolution_chart, CHART_COLORS
        
        if not matches or len(matches) < 2:
            self.evolution_charts.controls = [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.SHOW_CHART_ROUNDED, size=32, 
                                   color=COLORS['text_muted']),
                            ft.Text("Jogue mais partidas para ver gráficos", 
                                   size=12, color=COLORS['text_muted']),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8
                    ),
                    height=200,
                    alignment=Alignment.CENTER
                )
            ]
            return
        
        # Ordenar por data
        sorted_matches = sorted(matches, key=lambda x: x.get('date', ''), reverse=False)
        
        # Criar gráficos
        charts = [
            create_evolution_chart(sorted_matches, 'goals', 'Gols por Partida', 
                                  CHART_COLORS['primary']),
            create_evolution_chart(sorted_matches, 'score', 'Score por Partida', 
                                  CHART_COLORS['cyan']),
            create_evolution_chart(sorted_matches, 'boost_avg', 'Boost Médio', 
                                  CHART_COLORS['warning']),
        ]
        
        self.evolution_charts.controls = [
            ft.Row(controls=charts[:2], spacing=12, expand=True),
            ft.Container(height=4),
            ft.Row(controls=charts[2:], spacing=12, expand=True),
        ]

    def _build_comparison_panel(self) -> ft.Container:
        self.comparison_list = ft.Column(spacing=8)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.COMPARE_ARROWS_ROUNDED, size=18, color=COLORS['accent']),
                            ft.Text("Comparação com Pro", size=14, weight=ft.FontWeight.W_700,
                                    color=COLORS['text']),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=8),
                    self.comparison_list
                ],
                spacing=0
            ),
            width=360,
            bgcolor=COLORS['card'],
            border=Border.all(1, COLORS['border_light']),
            border_radius=16,
            padding=Padding.symmetric(horizontal=20, vertical=18),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=COLORS['shadow'] + '30',
                offset=ft.Offset(0, 4)
            )
        )

    # ── BOTTOM SECTION ─────────────────────────────────────────────────────

    def _build_bottom_section(self) -> ft.Row:
        return ft.Row(
            controls=[
                self._build_recent_table(),
                self._build_tips_panel()
            ],
            spacing=14,
            expand=True
        )

    def _build_recent_table(self) -> ft.Container:
        self.table_rows = []
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("DATA", size=10, color=COLORS['text_muted'],
                                      weight=ft.FontWeight.W_700)),
                ft.DataColumn(ft.Text("RESULTADO", size=10, color=COLORS['text_muted'],
                                      weight=ft.FontWeight.W_700)),
                ft.DataColumn(ft.Text("G/A/S", size=10, color=COLORS['text_muted'],
                                      weight=ft.FontWeight.W_700)),
                ft.DataColumn(ft.Text("SCORE", size=10, color=COLORS['text_muted'],
                                      weight=ft.FontWeight.W_700)),
                ft.DataColumn(ft.Text("PROXIMIDADE", size=10, color=COLORS['text_muted'],
                                      weight=ft.FontWeight.W_700)),
            ],
            rows=self.table_rows,
            bgcolor='transparent',
            border=Border.all(1, COLORS['border_light']),
            border_radius=12,
            heading_row_color=COLORS['surface'],
            data_row_color={ft.ControlState.HOVERED: COLORS['hover']},
            horizontal_margin=16,
            column_spacing=20,
            divider_thickness=0.5
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY_ROUNDED, size=18, color=COLORS['primary']),
                            ft.Text("Últimas Partidas", size=14, weight=ft.FontWeight.W_700,
                                    color=COLORS['text']),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=12),
                    ft.Container(content=self.table, expand=True, border_radius=12)
                ],
                spacing=0,
                expand=True
            ),
            expand=True,
            bgcolor=COLORS['card'],
            border=Border.all(1, COLORS['border_light']),
            border_radius=16,
            padding=Padding.symmetric(horizontal=20, vertical=18),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=COLORS['shadow'] + '30',
                offset=ft.Offset(0, 4)
            )
        )

    def _build_tips_panel(self) -> ft.Container:
        self.tips_list = ft.Column(spacing=8, expand=True)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, size=18, color=COLORS['warning']),
                            ft.Text("Dicas de Melhoria", size=14, weight=ft.FontWeight.W_700,
                                    color=COLORS['text']),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(height=8),
                    self.tips_list
                ],
                spacing=0,
                expand=True
            ),
            width=320,
            bgcolor=COLORS['card'],
            border=Border.all(1, COLORS['border_light']),
            border_radius=16,
            padding=Padding.symmetric(horizontal=20, vertical=18),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=COLORS['shadow'] + '30',
                offset=ft.Offset(0, 4)
            )
        )

    # ── CALLBACKS ──────────────────────────────────────────────────────────

    def _on_update_baseline(self, e) -> None:
        if self.status_text:
            self.status_text.value = "Atualizando baseline..."
            self.page.update()
        self._refresh_data()
        if self.status_text:
            self.status_text.value = "Monitorando..."
            self.page.update()

    # ── DATA REFRESH ───────────────────────────────────────────────────────

    def _refresh_data(self) -> None:
        try:
            # Usar filtro de playlist se selecionado
            playlist_filter = getattr(self, 'current_playlist', None)
            matches = self.db.get_matches(limit=10, playlist=playlist_filter)
            today_matches = self.db.get_today_matches()

            if matches:
                latest = matches[0]
                if self.boost_card_value:
                    self.boost_card_value.value = f"{latest.get('boost_avg', 0):.1f}"
                if self.proximity_card_value:
                    score = latest.get('proximity_score', 0) or 0
                    self.proximity_card_value.value = f"{score:.1f}%"
                if self.proximity_progress:
                    self.proximity_progress.value = (score or 0) / 100

            if self.matches_today_value:
                self.matches_today_value.value = str(len(today_matches))

            self._update_table(matches)
            self._update_evolution_charts(matches)
            self._update_comparison()
            self._update_tips()

            if self.page:
                self.page.update()
        except Exception as e:
            print(f"Erro ao atualizar dados: {e}")

    def _update_table(self, matches: List[Dict[str, Any]]) -> None:
        if not self.table or self.table.rows is None:
            return
        self.table.rows.clear()

        for match in matches[:8]:
            result = match.get('result', '')
            result_color = COLORS['success'] if result == 'win' else COLORS['error']
            result_label = "Vitória" if result == 'win' else "Derrota"
            prox = match.get('proximity_score', 0) or 0

            self.table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(match.get('date', ''))[:10],
                                            size=12, color=COLORS['text_secondary'])),
                        ft.DataCell(ft.Container(
                            content=ft.Text(result_label, size=11, color='white',
                                            weight=ft.FontWeight.W_500),
                            bgcolor=result_color,
                            border_radius=6,
                            padding=Padding.symmetric(horizontal=10, vertical=4),
                            alignment=Alignment.CENTER
                        )),
                        ft.DataCell(ft.Text(
                            f"{match.get('goals', 0)} / {match.get('assists', 0)} / {match.get('saves', 0)}",
                            size=12, color=COLORS['text'])),
                        ft.DataCell(ft.Text(str(match.get('score', 0)),
                                            size=12, color=COLORS['text'])),
                        ft.DataCell(ft.Text(f"{prox:.0f}%",
                                            size=12, color=COLORS['cyan'],
                                            weight=ft.FontWeight.W_500)),
                    ]
                )
            )

    def _update_comparison(self) -> None:
        if not self.comparison_list:
            return
        self.comparison_list.controls.clear()

        stats_to_compare = [
            ("Boost Médio", "boost_avg", "pads", COLORS['warning'], ft.Icons.BOLT_ROUNDED),
            ("Velocidade", "avg_speed", "u/s", COLORS['primary'], ft.Icons.SPEED_ROUNDED),
            ("Tempo Supersônico", "time_supersonic", "s", COLORS['cyan'], ft.Icons.ROCKET_LAUNCH_ROUNDED),
            ("Dist. Bola", "avg_distance_to_ball", "m", COLORS['accent'], ft.Icons.GPS_FIXED_ROUNDED),
        ]

        pro_values = {
            'boost_avg': 42, 'avg_speed': 1600, 'time_supersonic': 35,
            'avg_distance_to_ball': 95
        }

        matches = self.db.get_matches(limit=1)
        latest = matches[0] if matches else {}

        for label, stat_key, unit, color, icon in stats_to_compare:
            my_val = latest.get(stat_key, 0) or 0
            pro_val = pro_values.get(stat_key, 50)
            pct = min(1.0, (my_val / pro_val * 100)) if pro_val > 0 else 0

            if my_val >= pro_val:
                dot_color = COLORS['success']
                status_text = "Acima"
            elif my_val >= pro_val * 0.8:
                dot_color = COLORS['warning']
                status_text = "Próximo"
            else:
                dot_color = COLORS['error']
                status_text = "Abaixo"

            # Container do ícone
            icon_container = ft.Container(
                content=ft.Icon(icon, size=14, color='white'),
                bgcolor=color,
                border_radius=6,
                width=28,
                height=28,
                alignment=Alignment.CENTER
            )

            # Barra de progresso estilizada
            progress_bar = ft.Container(
                content=ft.Container(
                    bgcolor=color,
                    width=pct * 180,
                    height=6,
                    border_radius=3,
                    animate=ft.Animation(500, ft.AnimationCurve.EASE_OUT)
                ),
                bgcolor=COLORS['surface'],
                width=180,
                height=6,
                border_radius=3
            )

            self.comparison_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    icon_container,
                                    ft.Column(
                                        controls=[
                                            ft.Text(label, size=12, color=COLORS['text'],
                                                    weight=ft.FontWeight.W_600),
                                            ft.Text(f"{status_text}", size=9, color=dot_color,
                                                    weight=ft.FontWeight.W_500)
                                        ],
                                        spacing=2,
                                        expand=True
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text(f"{my_val:.0f}", size=14, color=COLORS['text'],
                                                    weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT),
                                            ft.Text(f"{unit} (pro: {pro_val:.0f})", size=9,
                                                    color=COLORS['text_muted'], text_align=ft.TextAlign.RIGHT)
                                        ],
                                        spacing=2,
                                        horizontal_alignment=ft.CrossAxisAlignment.END
                                    )
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10
                            ),
                            progress_bar
                        ],
                        spacing=8
                    ),
                    bgcolor=COLORS['surface'],
                    border_radius=10,
                    padding=Padding.symmetric(horizontal=14, vertical=12),
                    border=Border.all(1, COLORS['border']),
                    animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
                )
            )

    def _update_tips(self) -> None:
        if not self.tips_list:
            return
        self.tips_list.controls.clear()

        # Buscar dicas reais do comparer
        real_tips = self._get_real_tips()

        if not real_tips:
            self.tips_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(ft.Icons.INFO_ROUNDED, size=16, color=COLORS['text_muted']),
                                bgcolor=COLORS['surface'],
                                border_radius=8,
                                width=32,
                                height=32,
                                alignment=Alignment.CENTER
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Sem dicas disponíveis", size=12, weight=ft.FontWeight.W_600,
                                            color=COLORS['text_muted']),
                                    ft.Text("Jogue partidas e tenha uma baseline do pro para ver dicas personalizadas",
                                            size=10, color=COLORS['text_muted'])
                                ],
                                spacing=2,
                                expand=True
                            )
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    bgcolor=COLORS['surface'],
                    border_radius=8,
                    padding=Padding.symmetric(horizontal=12, vertical=10)
                )
            )
            return

        # Mapear ícones e cores por tipo de dica
        tip_icons = {
            'boost': (ft.Icons.BOLT_ROUNDED, COLORS['warning']),
            'speed': (ft.Icons.SPEED_ROUNDED, COLORS['cyan']),
            'position': (ft.Icons.GPS_FIXED_ROUNDED, COLORS['success']),
            'aerial': (ft.Icons.ARROW_UPWARD_ROUNDED, COLORS['accent']),
            'shot': (ft.Icons.GPS_FIXED_ROUNDED, COLORS['success']),
            'default': (ft.Icons.LIGHTBULB_ROUNDED, COLORS['primary']),
        }

        for tip_text in real_tips[:3]:
            icon, color = tip_icons['default']
            tip_lower = tip_text.lower()

            # Detectar tipo da dica para usar ícone apropriado
            if 'boost' in tip_lower or 'pad' in tip_lower:
                icon, color = tip_icons['boost']
            elif 'velocidade' in tip_lower or 'supersônico' in tip_lower or 'speed' in tip_lower:
                icon, color = tip_icons['speed']
            elif 'distância' in tip_lower or 'posição' in tip_lower or 'terço' in tip_lower:
                icon, color = tip_icons['position']
            elif 'ar' in tip_lower or 'aerial' in tip_lower or 'voo' in tip_lower:
                icon, color = tip_icons['aerial']
            elif 'finalização' in tip_lower or 'gol' in tip_lower or 'shot' in tip_lower:
                icon, color = tip_icons['shot']

            # Extrair título e descrição da dica
            title = tip_text[:50] + "..." if len(tip_text) > 50 else tip_text
            desc = tip_text if len(tip_text) > 50 else ""

            self.tips_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, size=16, color=color),
                                bgcolor=color + '15',
                                border_radius=8,
                                width=32,
                                height=32,
                                alignment=Alignment.CENTER
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(title, size=12, weight=ft.FontWeight.W_600,
                                            color=COLORS['text']),
                                    ft.Text(desc, size=10, color=COLORS['text_muted']) if desc else ft.Container()
                                ],
                                spacing=2,
                                expand=True
                            )
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    bgcolor=COLORS['surface'],
                    border_radius=8,
                    padding=Padding.symmetric(horizontal=12, vertical=10)
                )
            )

    def _get_real_tips(self) -> List[str]:
        """Busca dicas reais usando o comparer e os dados do banco."""
        if not self.comparer:
            return []

        try:
            # Pegar última partida
            matches = self.db.get_matches(limit=1)
            if not matches:
                return []

            latest = matches[0]
            playlist = latest.get('playlist', 'ranked-doubles')
            pro_name = self.config.get('pro_to_study', 'Zen')

            # Buscar baseline do pro
            baseline_data = self.db.get_baseline(playlist, pro_name)
            if not baseline_data:
                return []

            baseline = baseline_data.get('averages', {})
            if not baseline:
                return []

            # Montar stats do jogador a partir da partida
            player_stats = {
                'boost_avg': latest.get('boost_avg', 0),
                'time_zero_boost': latest.get('time_zero_boost', 0),
                'big_pads': latest.get('big_pads', 0),
                'small_pads': latest.get('small_pads', 0),
                'avg_distance_to_ball': latest.get('avg_distance_to_ball', 0),
                'avg_speed': latest.get('avg_speed', 0),
                'time_supersonic': latest.get('time_supersonic', 0),
                'shooting_pct': latest.get('shooting_pct', 0),
                'goals': latest.get('goals', 0),
                'assists': latest.get('assists', 0),
                'saves': latest.get('saves', 0),
                'score': latest.get('score', 0),
            }

            # Rodar comparação
            comparison = self.comparer.compare(player_stats, baseline)
            return comparison.get('tips', [])

        except Exception as e:
            print(f"Erro ao buscar dicas reais: {e}")
            return []

    # ── PUBLIC API ─────────────────────────────────────────────────────────

    def update_status(self, is_monitoring: bool) -> None:
        if self.status_text:
            self.status_text.value = "Monitorando..." if is_monitoring else "Parado"
        if self.status_indicator:
            self.status_indicator.content.bgcolor = (
                COLORS['success'] if is_monitoring else COLORS['error']
            )
        if self.page:
            self.page.update()

    def refresh(self) -> None:
        self._refresh_data()
