"""
RLBotPro - Dashboard Module
Interface NiceGUI para visualização de estatísticas e comparação com pros.
Design baseado no Trophy.ai - limpo e profissional.
Migrado de Flet para NiceGUI.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from nicegui import ui

from database import Database
from bot.comparer import ProComparer


# Cores do tema escuro - Trophy.ai style
COLORS = {
    'background': '#0a0b0f',
    'surface': '#12141c',
    'card': '#161822',
    'card_hover': '#1c1f2e',
    'primary': '#3b82f6',
    'primary_hover': '#60a5fa',
    'accent': '#8b5cf6',
    'cyan': '#06b6d4',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'text': '#f8fafc',
    'text_secondary': '#94a3b8',
    'text_muted': '#64748b',
    'border': '#1e2130',
    'border_light': '#252836',
    'sidebar': '#0d0f15',
    'sidebar_active': '#161822',
    'hover': '#1c1f2e',
}


def _card_style(extra: str = "") -> str:
    return (
        f'background: {COLORS["card"]}; border: 1px solid {COLORS["border_light"]}; '
        f'border-radius: 12px; box-shadow: 0 3px 10px #00000040; {extra}'
    )


def _surface_style(extra: str = "") -> str:
    return (
        f'background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; '
        f'border-radius: 8px; {extra}'
    )


class Dashboard:
    """Classe principal do dashboard NiceGUI."""

    def __init__(self, db: Database, config: dict, comparer: Optional['ProComparer'] = None):
        self.db = db
        self.config = config
        self.comparer = comparer
        self.current_playlist: Optional[str] = None
        self.nav_index = 0
        self.current_page = 0  # 0=Dashboard, 1=Análises, 2=Histórico, 3=Config

    def build(self) -> None:
        """Constrói a UI principal no NiceGUI."""
        ui.dark_mode(True)
        ui.add_head_html(f'''
            <style>
                body {{ background: {COLORS["background"]}; margin: 0; padding: 0; }}
                .nicegui-content {{ padding: 0 !important; }}
                @keyframes fadeInUp {{
                    from {{ opacity: 0; transform: translateY(14px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                .fade-in {{
                    animation: fadeInUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
                    opacity: 0;
                }}
            </style>
        ''')

        with ui.column().classes('w-full h-screen').style('margin: 0; padding: 0;'):
            with ui.row().classes('w-full flex-1').style('margin: 0; padding: 0;'):
                self._build_sidebar()
                ui.separator().style(f'width: 1px; background: {COLORS["border"]}; margin: 0;')
                self.main_area = ui.column().classes('flex-1 overflow-auto').style(
                    f'background: {COLORS["background"]}; padding: 18px 28px;'
                )

        self._show_dashboard()

        # Auto-refresh a cada 30 segundos
        ui.timer(30.0, self._refresh_data)

    # ── SIDEBAR ────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        self.nav_buttons: list = []

        with ui.column().classes('h-full').style(
            f'width: 200px; background: {COLORS["sidebar"]}; padding: 14px 10px;'
        ):
            # Logo
            with ui.row().classes('items-center gap-2').style('padding-bottom: 18px;'):
                ui.icon('sports_esports', size='18px').classes('text-white').style(
                    f'background: {COLORS["primary"]}; border-radius: 7px; '
                    f'width: 32px; height: 32px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                with ui.column().classes('gap-0'):
                    ui.label('RLBot').classes('text-sm font-bold').style(f'color: {COLORS["text"]}')
                    ui.label('Pro Analytics').classes('text-xs').style(f'color: {COLORS["text_muted"]}')

            ui.space()

            # Nav items
            nav_items = [
                ('dashboard', 'Dashboard', 0),
                ('analytics', 'Análises', 1),
                ('history', 'Histórico', 2),
                ('settings', 'Config', 3),
            ]

            for icon_name, label, idx in nav_items:
                is_active = idx == self.nav_index
                btn = ui.button(icon=icon_name, text=label).classes(
                    'w-full justify-start text-xs'
                ).style(
                    self._nav_btn_style(is_active)
                )
                btn.on_click(lambda e, i=idx: self._on_nav_click(i))
                self.nav_buttons.append((btn, idx))

            ui.space()

            # Status
            with ui.row().classes('items-center gap-1').style(
                f'background: {COLORS["surface"]}; border-radius: 6px; padding: 8px;'
            ):
                self.status_dot = ui.label().style(
                    f'width: 7px; height: 7px; border-radius: 4px; '
                    f'background: {COLORS["success"]};'
                )
                self.status_label = ui.label('Monitorando...').classes('text-xs').style(
                    f'color: {COLORS["text_secondary"]}'
                )

    def _nav_btn_style(self, is_active: bool) -> str:
        bg = COLORS['sidebar_active'] if is_active else 'transparent'
        color = COLORS['primary'] if is_active else COLORS['text_muted']
        text_color = COLORS['text'] if is_active else COLORS['text_muted']
        weight = '600' if is_active else '400'
        return (
            f'background: {bg}; border-radius: 8px; padding: 9px 12px; '
            f'color: {text_color}; font-weight: {weight}; text-transform: none; '
            f'border: none; box-shadow: none; transition: all 0.2s ease;'
        )

    def _on_nav_click(self, index: int) -> None:
        self.nav_index = index
        self.current_page = index
        # Update nav button styles
        for btn, idx in self.nav_buttons:
            is_active = idx == index
            btn.style(self._nav_btn_style(is_active))

        # Show the corresponding page
        pages = [self._show_dashboard, self._show_analyses, self._show_history, self._show_settings]
        pages[index]()

    # ── DASHBOARD PAGE ─────────────────────────────────────────────────────

    def _show_dashboard(self) -> None:
        self.main_area.clear()
        with self.main_area:
            self._build_top_bar()
            ui.space()
            self._build_stats_grid()
            ui.space()
            self._build_chart_section()
            ui.space()
            self._build_bottom_section()
            self._refresh_data()

    def _build_top_bar(self) -> None:
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-0'):
                ui.label('Dashboard').classes('text-2xl font-bold').style(f'color: {COLORS["text"]}')
                ui.label('Acompanhe suas estatísticas e evolução').classes('text-xs').style(
                    f'color: {COLORS["text_muted"]}'
                )
            self._build_playlist_tabs()

    def _build_playlist_tabs(self) -> None:
        playlists = [
            ("Todas", None),
            ("2v2", "ranked-doubles"),
            ("3v3", "ranked-standard"),
            ("1v1", "ranked-duels"),
        ]

        with ui.row().classes('items-center').style(
            f'background: {COLORS["surface"]}; border-radius: 8px; padding: 3px; '
            f'border: 1px solid {COLORS["border"]};'
        ):
            self.playlist_buttons: list = []
            for label, playlist in playlists:
                is_active = playlist is None
                btn = ui.button(label).classes('text-xs').style(
                    f'background: {COLORS["primary"] if is_active else "transparent"}; '
                    f'color: {COLORS["text"] if is_active else COLORS["text_muted"]}; '
                    f'border-radius: 6px; padding: 6px 12px; font-weight: {"600" if is_active else "500"}; '
                    f'border: none; box-shadow: none; text-transform: none; transition: all 0.2s ease;'
                )
                btn.on_click(lambda e, p=playlist: self._on_playlist_change(p))
                self.playlist_buttons.append((btn, playlist))

    def _on_playlist_change(self, playlist: Optional[str]) -> None:
        self.current_playlist = playlist
        for btn, pl in self.playlist_buttons:
            is_active = pl == playlist
            btn.style(
                f'background: {COLORS["primary"] if is_active else "transparent"}; '
                f'color: {COLORS["text"] if is_active else COLORS["text_muted"]}; '
                f'border-radius: 6px; padding: 6px 12px; font-weight: {"600" if is_active else "500"}; '
                f'border: none; box-shadow: none; text-transform: none; transition: all 0.2s ease;'
            )
        self._refresh_data()

    # ── STATS GRID ─────────────────────────────────────────────────────────

    def _build_stats_grid(self) -> None:
        with ui.row().classes('w-full gap-3'):
            self.boost_value = self._build_stat_card('bolt', COLORS['warning'], 'BOOST MÉDIO', '0', 'pads coletados por partida')
            self.proximity_value, self.proximity_bar = self._build_stat_card_with_extra(
                'trending_up', COLORS['cyan'], 'PROXIMIDADE', '0%', 'vs pro estudado'
            )
            self.matches_value = self._build_stat_card('play_circle', COLORS['primary'], 'PARTIDAS HOJE', '0', 'jogadas')
            self.winrate_value = self._build_stat_card('emoji_events', COLORS['success'], 'WIN RATE', '0%', 'taxa de vitória')

    def _build_stat_card(self, icon: str, icon_color: str, title: str,
                         initial_value: str, subtitle: str = "") -> ui.label:
        with ui.card().classes('flex-1').style(_card_style('padding: 14px 16px;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon(icon, size='16px').classes('text-white').style(
                    f'background: {icon_color}; border-radius: 8px; '
                    f'width: 34px; height: 34px; display: flex; align-items: center; '
                    f'justify-content: center; box-shadow: 0 2px 6px {icon_color}40;'
                )
                ui.label(title).classes('text-xs font-semibold').style(f'color: {COLORS["text_secondary"]}')

            ui.space()
            value_label = ui.label(initial_value).classes('text-3xl font-bold').style(f'color: {icon_color}')
            if subtitle:
                ui.label(subtitle).classes('text-xs').style(f'color: {COLORS["text_muted"]}')
        return value_label

    def _build_stat_card_with_extra(self, icon: str, icon_color: str, title: str,
                                     initial_value: str, subtitle: str = "") -> tuple:
        with ui.card().classes('flex-1').style(_card_style('padding: 14px 16px;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon(icon, size='16px').classes('text-white').style(
                    f'background: {icon_color}; border-radius: 8px; '
                    f'width: 34px; height: 34px; display: flex; align-items: center; '
                    f'justify-content: center; box-shadow: 0 2px 6px {icon_color}40;'
                )
                ui.label(title).classes('text-xs font-semibold').style(f'color: {COLORS["text_secondary"]}')

            ui.space()
            value_label = ui.label(initial_value).classes('text-3xl font-bold').style(f'color: {icon_color}')
            if subtitle:
                ui.label(subtitle).classes('text-xs').style(f'color: {COLORS["text_muted"]}')
            progress_bar = ui.linear_progress(value=0).style(
                f'width: 140px; background: {COLORS["surface"]};'
            ).props(f'color={icon_color}')
        return value_label, progress_bar

    # ── CHART SECTION ──────────────────────────────────────────────────────

    def _build_chart_section(self) -> None:
        with ui.row().classes('w-full gap-3'):
            self._build_evolution_panel()
            self._build_comparison_panel()

    def _build_evolution_panel(self) -> None:
        with ui.card().classes('flex-1').style(_card_style('padding: 16px 18px;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('trending_up', size='14px').classes('text-white').style(
                    f'background: {COLORS["success"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('Evolução').classes('text-sm font-bold').style(f'color: {COLORS["text"]}')

            ui.separator().style(f'background: {COLORS["border"]};')
            self.evolution_container = ui.column().classes('w-full gap-2')

    def _build_comparison_panel(self) -> None:
        with ui.card().classes('w-80').style(_card_style('padding: 16px 18px;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('compare_arrows', size='14px').classes('text-white').style(
                    f'background: {COLORS["accent"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('Comparação com Pro').classes('text-sm font-bold').style(f'color: {COLORS["text"]}')

            self.comparison_container = ui.column().classes('w-full gap-2')

    # ── BOTTOM SECTION ─────────────────────────────────────────────────────

    def _build_bottom_section(self) -> None:
        with ui.row().classes('w-full gap-3'):
            self._build_recent_table_panel()
            self._build_tips_panel()

    def _build_recent_table_panel(self) -> None:
        with ui.card().classes('flex-1').style(_card_style('padding: 16px 18px;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('history', size='14px').classes('text-white').style(
                    f'background: {COLORS["primary"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('Últimas Partidas').classes('text-sm font-bold').style(f'color: {COLORS["text"]}')

            self.table_container = ui.column().classes('w-full')

    def _build_tips_panel(self) -> None:
        with ui.card().classes('w-72').style(_card_style('padding: 16px 18px;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('lightbulb', size='14px').classes('text-white').style(
                    f'background: {COLORS["warning"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('Dicas de Melhoria').classes('text-sm font-bold').style(f'color: {COLORS["text"]}')

            self.tips_container = ui.column().classes('w-full gap-2')

    # ── ANALYSES PAGE ──────────────────────────────────────────────────────

    def _show_analyses(self) -> None:
        self.main_area.clear()
        with self.main_area:
            # Header
            with ui.row().classes('items-center gap-3'):
                ui.icon('analytics', size='18px').classes('text-white').style(
                    f'background: {COLORS["accent"]}; border-radius: 8px; '
                    f'width: 36px; height: 36px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                with ui.column().classes('gap-0'):
                    ui.label('Análises Detalhadas').classes('text-xl font-bold').style(f'color: {COLORS["text"]}')
                    ui.label('Análise completa de um replay').classes('text-xs').style(f'color: {COLORS["text_muted"]}')

            ui.space()

            # Replay selection
            with ui.card().classes('w-full').style(_card_style('padding: 10px;')):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('folder_open', size='18px').style(f'color: {COLORS["text_secondary"]}')
                    self.replay_select = ui.select(
                        options={}, value=None, label='Selecionar replay',
                        on_change=self._on_replay_select
                    ).classes('flex-1').style(
                        f'background: {COLORS["surface"]};'
                    ).props(f'dense options-dense color="{COLORS["primary"]}"')
                    ui.button(icon='refresh', on_click=self._load_replay_list).classes('text-white').style(
                        f'background: {COLORS["primary"]}; border-radius: 6px; '
                        f'width: 32px; height: 32px; min-width: 32px;'
                    )

            ui.space()

            # Results area
            self.analysis_container = ui.column().classes('w-full flex-1 items-center justify-center')
            with self.analysis_container:
                ui.icon('analytics', size='48px').style(f'color: {COLORS["text_muted"]}')
                ui.label('Selecione um replay para analisar').classes('text-base').style(f'color: {COLORS["text_muted"]}')

        self._load_replay_list()

    def _load_replay_list(self) -> None:
        replay_folder = os.path.join(
            os.path.expanduser("~"),
            "Documents", "My Games", "Rocket League", "TAGame", "Demos"
        )

        if not os.path.exists(replay_folder):
            self.replay_select.options = {'none': 'Pasta de replays não encontrada'}
            self.replay_select.update()
            return

        replay_files = [f for f in os.listdir(replay_folder) if f.endswith(".replay")]
        replay_files.sort(key=lambda x: os.path.getmtime(os.path.join(replay_folder, x)), reverse=True)

        if not replay_files:
            self.replay_select.options = {'none': 'Nenhum replay encontrado'}
            self.replay_select.update()
            return

        options = {}
        for f in replay_files[:20]:
            mtime = os.path.getmtime(os.path.join(replay_folder, f))
            date_str = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            display_name = f"{date_str} - {f[:30]}..."
            options[f] = display_name

        self.replay_select.options = options
        first_key = list(options.keys())[0]
        self.replay_select.value = first_key
        self.replay_select.update()

    def _on_replay_select(self, e) -> None:
        if not e.value or e.value == "none":
            return
        replay_folder = os.path.join(
            os.path.expanduser("~"),
            "Documents", "My Games", "Rocket League", "TAGame", "Demos"
        )
        replay_path = os.path.join(replay_folder, e.value)
        self._analyze_replay(replay_path)

    def _analyze_replay(self, replay_path: str) -> None:
        from bot.local_analyzer import LocalReplayAnalyzer, HAS_SUBTR

        self.analysis_container.clear()

        if not HAS_SUBTR:
            with self.analysis_container:
                ui.icon('error', size='48px').style(f'color: {COLORS["error"]}')
                ui.label('subtr-actor não instalado').classes('text-base').style(f'color: {COLORS["error"]}')
                ui.label('Execute: uv pip install subtr-actor-py').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
            return

        with self.analysis_container:
            ui.spinner(size='40px').style(f'color: {COLORS["primary"]}')
            ui.label('Analisando replay...').classes('text-sm').style(f'color: {COLORS["text_secondary"]}')

        try:
            analyzer = LocalReplayAnalyzer(self.config.get('player_name', ''))
            result = analyzer.analyze_replay(replay_path)

            self.analysis_container.clear()

            if result:
                self._show_analysis_results(result)
            else:
                with self.analysis_container:
                    ui.icon('warning', size='48px').style(f'color: {COLORS["warning"]}')
                    ui.label('Não foi possível analisar o replay').classes('text-base').style(f'color: {COLORS["warning"]}')
                    ui.label('Verifique se o jogador está no replay').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
        except Exception as ex:
            self.analysis_container.clear()
            with self.analysis_container:
                ui.icon('error', size='48px').style(f'color: {COLORS["error"]}')
                ui.label('Erro na análise').classes('text-base').style(f'color: {COLORS["error"]}')
                ui.label(str(ex)).classes('text-xs').style(f'color: {COLORS["text_muted"]}')

    def _show_analysis_results(self, result: Dict[str, Any]) -> None:
        """Show analysis results in Trophi.ai style layout."""
        # Extract data
        goals = result.get('goals', 0)
        assists = result.get('assists', 0)
        saves = result.get('saves', 0)
        shots = result.get('shots', 0)
        game_mode = result.get('game_mode', '?')
        map_name = result.get('map_name', '?')
        team_zero_score = result.get('team_zero_score', 0)
        team_one_score = result.get('team_one_score', 0)
        duration = result.get('duration_seconds', 0)
        player_name = result.get('player_name', self.config.get('player_name', 'You'))
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near = result.get('time_near_ball_pct', 0)
        time_off = result.get('time_offensive_pct', 0)
        boost_collected = result.get('boost_collected', 0)
        boost_used = result.get('boost_used', 0)
        demos = result.get('demos_inflicted', 0)

        dur_min = int(duration // 60)
        dur_sec = int(duration % 60)
        won = team_zero_score > team_one_score
        score_str = f"{team_zero_score} - {team_one_score}"

        # Skill scores (0-100)
        movement_score = max(0, min(100, int(100 - (avg_dist - 500) / 15))) if avg_dist > 0 else 50
        aerial_score = max(0, min(100, int(boost_collected / 50))) if boost_collected > 0 else 30
        positioning_score = max(0, min(100, 100 - abs(time_off - 50) * 2))
        boost_eff = (boost_used / boost_collected * 100) if boost_collected > 0 else 0
        boost_score = max(0, min(100, int(boost_eff * 1.1)))
        shooting_score = int((goals / shots * 100)) if shots > 0 else 0

        # Get pro comparison
        comparison = self._get_analysis_comparison(result)
        overall_score = comparison.get('score', 0) if comparison else 0

        tips = self._generate_analysis_tips(result)

        with self.analysis_container:
            # ── HEADER ──
            with ui.row().classes('w-full items-center justify-between fade-in').style(
                f'background: {COLORS["card"]}; border: 1px solid {COLORS["border_light"]}; '
                f'border-radius: 12px; padding: 16px 20px; animation-delay: 0s;'
            ):
                with ui.row().classes('items-center gap-4'):
                    result_color = COLORS['success'] if won else COLORS['error']
                    result_text = "WIN" if won else "LOSS"
                    ui.label(result_text).classes('text-xs font-bold').style(
                        f'background: {result_color}; color: white; border-radius: 6px; '
                        f'padding: 6px 14px; letter-spacing: 1px;'
                    )
                    with ui.column().classes('gap-0'):
                        ui.label(player_name).classes('text-lg font-bold').style(f'color: {COLORS["text"]}')
                        with ui.row().classes('items-center gap-2'):
                            ui.label(score_str).classes('text-sm font-semibold').style(f'color: {COLORS["text_secondary"]}')
                            ui.label('•').style(f'color: {COLORS["text_muted"]}')
                            ui.label(game_mode).classes('text-xs').style(f'color: {COLORS["text_secondary"]}')
                            ui.label('•').style(f'color: {COLORS["text_muted"]}')
                            ui.label(map_name).classes('text-xs').style(f'color: {COLORS["text_secondary"]}')
                with ui.row().classes('items-center gap-3'):
                    ui.label(f'{dur_min}:{dur_sec:02d}').classes('text-sm font-semibold').style(f'color: {COLORS["text_muted"]}')
                    score_color = COLORS['success'] if overall_score >= 70 else COLORS['warning'] if overall_score >= 50 else COLORS['error']
                    ui.label(f'{overall_score:.0f}/100').classes('text-sm font-bold').style(
                        f'background: {score_color}20; color: {score_color}; border-radius: 6px; padding: 4px 10px;'
                    )

            ui.space()

            # ── TWO-COLUMN LAYOUT ──
            with ui.row().classes('w-full gap-4'):
                # LEFT COLUMN
                with ui.column().classes('flex-1 gap-4'):
                    self._build_skill_gauges(movement_score, aerial_score, positioning_score, boost_score, shooting_score)
                    self._build_stat_categories(result)

                    # Heatmap
                    positions = result.get('positions_sample', [])
                    if positions and len(positions) >= 3:
                        self._build_heatmap(positions)

                # RIGHT COLUMN
                self._build_overview_report(overall_score, tips, result)

    def _make_gauge_option(self, value: int, label: str, color: str) -> dict:
        """Create ECharts gauge option for skill scores."""
        return {
            'backgroundColor': 'transparent',
            'series': [{
                'type': 'gauge',
                'startAngle': 220,
                'endAngle': -40,
                'min': 0,
                'max': 100,
                'progress': {'show': True, 'width': 14},
                'axisLine': {'lineStyle': {'width': 14, 'color': [[1, '#31344b']]}},
                'axisTick': {'show': False},
                'splitLine': {'show': False},
                'axisLabel': {'show': False},
                'pointer': {'show': False},
                'title': {'show': True, 'offsetCenter': [0, '75%'], 'fontSize': 11, 'color': '#94a3b8'},
                'detail': {
                    'valueAnimation': True, 'fontSize': 22, 'fontWeight': 'bold',
                    'offsetCenter': [0, '35%'], 'color': color
                },
                'data': [{'value': value, 'name': label}]
            }]
        }

    def _build_skill_gauges(self, movement: int, aerial: int, positioning: int,
                              boost: int, shooting: int) -> None:
        """Build circular gauge charts for skill scores."""
        with ui.card().classes('w-full fade-in').style(_card_style('padding: 20px; animation-delay: 0.1s;')):
            ui.label('SKILL SCORES').classes('text-xs font-bold tracking-wider').style(
                f'color: {COLORS["text_secondary"]}'
            )
            ui.space()

            gauges = [
                (movement, 'Movement', COLORS['primary']),
                (aerial, 'Aerial', COLORS['accent']),
                (positioning, 'Positioning', COLORS['cyan']),
                (boost, 'Boost', COLORS['warning']),
                (shooting, 'Shooting', COLORS['success']),
            ]

            with ui.row().classes('w-full justify-between'):
                for value, label, color in gauges:
                    option = self._make_gauge_option(value, label, color)
                    ui.echart(option).style('width: 150px; height: 130px;')

    def _get_status(self, stat: str, value: float) -> tuple:
        """Get status label and color for a stat value vs pro reference."""
        pro_refs = {
            'boost_collected': (4500, True),
            'boost_used': (3500, False),
            'goals': (1.5, True),
            'assists': (1.0, True),
            'shots': (4.0, True),
            'avg_distance_to_ball': (950, False),
            'time_near_ball_pct': (35, True),
            'time_offensive_pct': (48, True),
        }
        if stat not in pro_refs:
            return ('WITHIN TARGET', COLORS['text_muted'])
        ref, higher_better = pro_refs[stat]
        if ref == 0:
            return ('WITHIN TARGET', COLORS['text_muted'])
        ratio = value / ref
        if higher_better:
            if ratio >= 0.9:
                return ('WITHIN TARGET', COLORS['success'])
            elif ratio >= 0.6:
                return ('TOO LOW', COLORS['warning'])
            else:
                return ('TOO LOW', COLORS['error'])
        else:
            if ratio <= 1.1:
                return ('WITHIN TARGET', COLORS['success'])
            elif ratio <= 1.4:
                return ('TOO HIGH', COLORS['warning'])
            else:
                return ('TOO HIGH', COLORS['error'])

    def _build_stat_card_row(self, label: str, value: str, status_text: str, status_color: str) -> None:
        """Build a single stat row with label, value, and status indicator."""
        with ui.row().classes('w-full items-center justify-between').style('padding: 6px 0;'):
            ui.label(label).classes('text-xs').style(f'color: {COLORS["text_secondary"]}')
            with ui.row().classes('items-center gap-2'):
                ui.label(value).classes('text-sm font-semibold').style(f'color: {COLORS["text"]}')
                ui.label(status_text).classes('text-xs font-semibold').style(
                    f'color: {status_color}; background: {status_color}15; '
                    f'border-radius: 4px; padding: 2px 6px;'
                )

    def _build_stat_categories(self, result: Dict[str, Any]) -> None:
        """Build stat category cards grouped by area."""
        boost_collected = result.get('boost_collected', 0)
        boost_used = result.get('boost_used', 0)
        goals = result.get('goals', 0)
        assists = result.get('assists', 0)
        saves = result.get('saves', 0)
        shots = result.get('shots', 0)
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near = result.get('time_near_ball_pct', 0)
        time_off = result.get('time_offensive_pct', 0)

        # ── BOOST ──
        with ui.card().classes('w-full fade-in').style(_card_style('padding: 16px 18px; animation-delay: 0.2s;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('bolt', size='14px').classes('text-white').style(
                    f'background: {COLORS["warning"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('BOOST').classes('text-xs font-bold tracking-wider').style(f'color: {COLORS["text"]}')

            ui.separator().style(f'background: {COLORS["border"]}; margin: 8px 0;')

            s_text, s_color = self._get_status('boost_collected', boost_collected)
            self._build_stat_card_row('Boost Collected', f'{boost_collected:.0f}', s_text, s_color)
            s_text, s_color = self._get_status('boost_used', boost_used)
            self._build_stat_card_row('Boost Used', f'{boost_used:.0f}', s_text, s_color)
            eff = (boost_used / boost_collected * 100) if boost_collected > 0 else 0
            eff_color = COLORS['success'] if 50 <= eff <= 85 else COLORS['warning']
            self._build_stat_card_row('Efficiency', f'{eff:.0f}%', 'WITHIN TARGET', eff_color)

        # ── SHOOTING ──
        shooting_pct = (goals / shots * 100) if shots > 0 else 0
        with ui.card().classes('w-full fade-in').style(_card_style('padding: 16px 18px; animation-delay: 0.3s;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('sports_soccer', size='14px').classes('text-white').style(
                    f'background: {COLORS["success"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('SHOOTING').classes('text-xs font-bold tracking-wider').style(f'color: {COLORS["text"]}')

            ui.separator().style(f'background: {COLORS["border"]}; margin: 8px 0;')

            s_text, s_color = self._get_status('goals', goals)
            self._build_stat_card_row('Goals', str(goals), s_text, s_color)
            s_text, s_color = self._get_status('assists', assists)
            self._build_stat_card_row('Assists', str(assists), s_text, s_color)
            s_text, s_color = self._get_status('shots', shots)
            self._build_stat_card_row('Shots', str(shots), s_text, s_color)
            conv_color = COLORS['success'] if shooting_pct > 25 else COLORS['error']
            conv_status = 'WITHIN TARGET' if shooting_pct > 25 else 'TOO LOW'
            self._build_stat_card_row('Conversion', f'{shooting_pct:.0f}%', conv_status, conv_color)

        # ── POSITIONING ──
        with ui.card().classes('w-full fade-in').style(_card_style('padding: 16px 18px; animation-delay: 0.4s;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('my_location', size='14px').classes('text-white').style(
                    f'background: {COLORS["cyan"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('POSITIONING').classes('text-xs font-bold tracking-wider').style(f'color: {COLORS["text"]}')

            ui.separator().style(f'background: {COLORS["border"]}; margin: 8px 0;')

            s_text, s_color = self._get_status('avg_distance_to_ball', avg_dist)
            self._build_stat_card_row('Avg Distance', f'{avg_dist:.0f}m', s_text, s_color)
            s_text, s_color = self._get_status('time_near_ball_pct', time_near)
            self._build_stat_card_row('Time Near Ball', f'{time_near:.1f}%', s_text, s_color)
            s_text, s_color = self._get_status('time_offensive_pct', time_off)
            self._build_stat_card_row('Time Offensive', f'{time_off:.1f}%', s_text, s_color)

            # Zone positioning bar
            ui.space()
            ui.label('ZONE POSITIONING').classes('text-xs font-semibold').style(f'color: {COLORS["text_muted"]}')
            self._build_zone_bar(time_off)

    def _build_zone_bar(self, offensive_pct: float) -> None:
        """Build zone positioning visualization bar."""
        offensive_pct = min(100, max(0, offensive_pct))
        neutral_pct = max(0, 100 - offensive_pct) * 0.55
        defensive_pct = 100 - offensive_pct - neutral_pct

        with ui.column().classes('w-full gap-1'):
            with ui.row().classes('w-full').style('height: 24px; border-radius: 6px; overflow: hidden;'):
                if defensive_pct > 0:
                    ui.label('').style(
                        f'width: {defensive_pct}%; background: {COLORS["error"]}90; height: 100%;'
                    )
                if neutral_pct > 0:
                    ui.label('').style(
                        f'width: {neutral_pct}%; background: {COLORS["text_muted"]}60; height: 100%;'
                    )
                if offensive_pct > 0:
                    ui.label('').style(
                        f'width: {offensive_pct}%; background: {COLORS["success"]}90; height: 100%;'
                    )

            with ui.row().classes('w-full justify-between'):
                ui.label(f'DEF {defensive_pct:.0f}%').classes('text-xs').style(f'color: {COLORS["error"]}')
                ui.label(f'NEU {neutral_pct:.0f}%').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
                ui.label(f'OFF {offensive_pct:.0f}%').classes('text-xs').style(f'color: {COLORS["success"]}')

    def _build_overview_report(self, overall_score: int, tips: list, result: Dict[str, Any]) -> None:
        """Build the Overview Report panel on the right side."""
        with ui.column().classes('w-80 gap-4'):
            # Score card
            with ui.card().classes('w-full fade-in').style(_card_style('padding: 20px; animation-delay: 0.15s;')):
                ui.label('OVERVIEW REPORT').classes('text-xs font-bold tracking-wider').style(
                    f'color: {COLORS["text_secondary"]}'
                )
                ui.space()

                score_color = COLORS['success'] if overall_score >= 70 else COLORS['warning'] if overall_score >= 50 else COLORS['error']
                score_option = self._make_gauge_option(overall_score, 'Score', score_color)
                score_option['series'][0]['progress']['width'] = 10
                score_option['series'][0]['axisLine']['lineStyle']['width'] = 10
                score_option['series'][0]['detail']['fontSize'] = 28
                ui.echart(score_option).style('width: 100%; height: 160px;')

                pro_name = self.config.get('pro_to_study', 'Zen')
                with ui.row().classes('items-center gap-2'):
                    ui.icon('person', size='14px').style(f'color: {COLORS["accent"]}')
                    ui.label(f'Comparing to: {pro_name}').classes('text-xs').style(f'color: {COLORS["text_secondary"]}')

            # Tips card
            with ui.card().classes('w-full fade-in').style(_card_style('padding: 16px 18px; animation-delay: 0.25s;')):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('lightbulb', size='14px').classes('text-white').style(
                        f'background: {COLORS["warning"]}; border-radius: 6px; '
                        f'width: 28px; height: 28px; display: flex; align-items: center; '
                        f'justify-content: center;'
                    )
                    ui.label('TIPS').classes('text-xs font-bold tracking-wider').style(f'color: {COLORS["text"]}')

                ui.separator().style(f'background: {COLORS["border"]}; margin: 8px 0;')

                if tips:
                    for tip in tips[:4]:
                        with ui.row().classes('items-start gap-2').style('margin-bottom: 8px;'):
                            ui.icon('arrow_right', size='12px').style(
                                f'color: {COLORS["primary"]}; margin-top: 2px;'
                            )
                            ui.label(tip).classes('text-xs').style(f'color: {COLORS["text_secondary"]}')
                else:
                    ui.label('Jogue mais para receber dicas personalizadas.').classes('text-xs').style(
                        f'color: {COLORS["text_muted"]}'
                    )

    def _build_heatmap(self, positions_sample: list) -> None:
        """Build field heatmap showing player positions as a scatter plot."""
        if not positions_sample or len(positions_sample) < 3:
            return

        positions = [[int(p[0]), int(p[1])] for p in positions_sample]

        option = {
            'backgroundColor': '#1a3a2a',
            'grid': {'left': 0, 'top': 0, 'right': 0, 'bottom': 0},
            'xAxis': {'show': False, 'min': -4200, 'max': 4200, 'type': 'value'},
            'yAxis': {'show': False, 'min': -5100, 'max': 5100, 'type': 'value'},
            'series': [{
                'type': 'scatter',
                'data': positions,
                'itemStyle': {
                    'color': 'rgba(59, 130, 246, 0.7)',
                    'shadowBlur': 8,
                    'shadowColor': 'rgba(59, 130, 246, 0.3)',
                },
                'symbolSize': 10,
                'markLine': {
                    'silent': True,
                    'symbol': 'none',
                    'lineStyle': {'color': 'rgba(255,255,255,0.25)', 'type': 'solid', 'width': 1},
                    'data': [
                        [{'xAxis': 0, 'yAxis': -5100}, {'xAxis': 0, 'yAxis': 5100}],
                    ],
                    'label': {'show': False},
                },
                'markArea': {
                    'silent': True,
                    'label': {'show': False},
                    'data': [
                        # Field boundary
                        [{'xAxis': -4200, 'yAxis': -5100, 'itemStyle': {'color': 'transparent', 'borderColor': 'rgba(255,255,255,0.15)', 'borderWidth': 2}}, {'xAxis': 4200, 'yAxis': 5100}],
                        # Left goal area
                        [{'xAxis': -4200, 'yAxis': -900, 'itemStyle': {'color': 'rgba(255,255,255,0.05)', 'borderColor': 'rgba(255,255,255,0.2)', 'borderWidth': 1}}, {'xAxis': -3900, 'yAxis': 900}],
                        # Right goal area
                        [{'xAxis': 3900, 'yAxis': -900, 'itemStyle': {'color': 'rgba(255,255,255,0.05)', 'borderColor': 'rgba(255,255,255,0.2)', 'borderWidth': 1}}, {'xAxis': 4200, 'yAxis': 900}],
                    ],
                },
            }]
        }

        with ui.card().classes('w-full fade-in').style(_card_style('padding: 16px 18px; animation-delay: 0.5s;')):
            with ui.row().classes('items-center gap-2'):
                ui.icon('place', size='14px').classes('text-white').style(
                    f'background: {COLORS["primary"]}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                ui.label('POSITION HEATMAP').classes('text-xs font-bold tracking-wider').style(f'color: {COLORS["text"]}')

            ui.echart(option).style(
                'width: 100%; height: 250px; border-radius: 8px; '
                f'border: 1px solid {COLORS["border"]};'
            )

            with ui.row().classes('w-full justify-between').style('margin-top: 4px;'):
                ui.label('← Defending').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
                ui.label(f'{len(positions)} positions sampled').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
                ui.label('Attacking →').classes('text-xs').style(f'color: {COLORS["text_muted"]}')

    def _get_analysis_comparison(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get pro comparison data for the analysis page."""
        if not self.comparer:
            return None
        try:
            playlist = 'ranked-doubles'
            pro_name = self.config.get('pro_to_study', 'Zen')
            baseline_data = self.db.get_baseline(playlist, pro_name)
            if not baseline_data:
                return None
            baseline = baseline_data.get('averages', {})
            if not baseline:
                return None
            player_stats = {
                'boost_avg': result.get('boost_collected', 0) / 100,  # rough proxy from local replay
                'avg_distance_to_ball': result.get('avg_distance_to_ball', 0),
                'goals': result.get('goals', 0),
                'assists': result.get('assists', 0),
                'saves': result.get('saves', 0),
                'shooting_pct': (result.get('goals', 0) / result.get('shots', 1) * 100) if result.get('shots', 0) > 0 else 0,
            }
            return self.comparer.compare(player_stats, baseline)
        except Exception as e:
            print(f"Erro na comparação: {e}")
            return None

    def _build_tip_card(self, tip: Dict[str, str]) -> None:
        icon_map = {'success': 'check_circle', 'warning': 'warning', 'error': 'error', 'info': 'info'}
        color_map = {'success': COLORS['success'], 'warning': COLORS['warning'], 'error': COLORS['error'], 'info': COLORS['primary']}

        tip_type = tip.get('type', 'info')
        icon_name = icon_map.get(tip_type, 'lightbulb')
        color = color_map.get(tip_type, COLORS['primary'])

        with ui.card().classes('w-full').style(
            f'background: {COLORS["card"]}; border-radius: 8px; padding: 10px; '
            f'border: 1px solid {COLORS["border"]}; margin-bottom: 6px;'
        ):
            with ui.row().classes('items-start gap-2'):
                ui.icon(icon_name, size='14px').style(
                    f'background: {color}20; color: {color}; border-radius: 6px; '
                    f'width: 28px; height: 28px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                with ui.column().classes('flex-1 gap-0'):
                    ui.label(tip.get('title', '')).classes('text-xs font-semibold').style(f'color: {COLORS["text"]}')
                    ui.label(tip.get('message', '')).classes('text-xs').style(f'color: {COLORS["text_secondary"]}')

    def _generate_analysis_tips(self, result: Dict[str, Any]) -> list:
        tips = []
        goals = result.get('goals', 0)
        saves = result.get('saves', 0)
        shots = result.get('shots', 0)
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near_ball = result.get('time_near_ball_pct', 0)
        time_offensive = result.get('time_offensive_pct', 0)

        if avg_dist > 1500:
            tips.append({'type': 'warning', 'title': 'Muito longe da bola', 'message': f'Distância média: {avg_dist:.0f}. Fique mais perto para ter mais contato.'})
        elif avg_dist < 500:
            tips.append({'type': 'success', 'title': 'Boa proximidade', 'message': f'Distância média: {avg_dist:.0f}. Continue assim!'})
        if time_near_ball < 30:
            tips.append({'type': 'warning', 'title': 'Pouco tempo com a bola', 'message': f'Apenas {time_near_ball:.1f}% do tempo perto da bola.'})
        if time_offensive > 60:
            tips.append({'type': 'success', 'title': 'Bom tempo no ataque', 'message': f'{time_offensive:.1f}% do tempo no ataque. Continue pressionando!'})
        elif time_offensive < 40:
            tips.append({'type': 'info', 'title': 'Mais tempo no ataque', 'message': f'Apenas {time_offensive:.1f}% no ataque. Suba mais quando possível.'})
        if shots > 0 and goals == 0:
            tips.append({'type': 'warning', 'title': 'Melhore a finalização', 'message': f'{shots} chutes, 0 gols. Pratique a finalização.'})
        elif goals > 0 and shots > 0:
            conversion = (goals / shots) * 100
            if conversion > 50:
                tips.append({'type': 'success', 'title': 'Ótima conversão', 'message': f'{conversion:.0f}% de conversão!'})
            else:
                tips.append({'type': 'info', 'title': 'Conversão razoável', 'message': f'{conversion:.0f}% de conversão. Seja mais preciso.'})
        if saves > 2:
            tips.append({'type': 'success', 'title': 'Boa defesa', 'message': f'{saves} defesas. Continue protegendo o gol!'})
        if not tips:
            tips.append({'type': 'info', 'title': 'Continue jogando', 'message': 'Jogue mais partidas para receber dicas mais detalhadas!'})
        return tips

    # ── HISTORY PAGE ───────────────────────────────────────────────────────

    def _show_history(self) -> None:
        self.main_area.clear()
        with self.main_area:
            with ui.row().classes('items-center gap-3'):
                ui.icon('history', size='18px').classes('text-white').style(
                    f'background: {COLORS["primary"]}; border-radius: 8px; '
                    f'width: 36px; height: 36px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                with ui.column().classes('gap-0'):
                    ui.label('Histórico de Partidas').classes('text-xl font-bold').style(f'color: {COLORS["text"]}')
                    ui.label('Todas as partidas jogadas').classes('text-xs').style(f'color: {COLORS["text_muted"]}')

            ui.space()
            self._build_history_content()

    def _build_history_content(self) -> None:
        matches = self.db.get_matches(limit=50)

        if not matches:
            with ui.column().classes('w-full items-center justify-center flex-1'):
                ui.icon('inbox', size='48px').style(f'color: {COLORS["text_muted"]}')
                ui.label('Nenhuma partida registrada').classes('text-base').style(f'color: {COLORS["text_muted"]}')
                ui.label('Jogue partidas para vê-las aqui').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
            return

        for match in matches:
            self._build_history_item(match)

    def _build_history_item(self, match: dict) -> None:
        result = match.get('result', '')
        result_color = COLORS['success'] if result == 'win' else COLORS['error']
        result_label = "Vitória" if result == 'win' else "Derrota"
        prox = match.get('proximity_score', 0) or 0

        with ui.card().classes('w-full').style(
            f'background: {COLORS["card"]}; border: 1px solid {COLORS["border"]}; '
            f'border-radius: 10px; padding: 12px 14px; margin-bottom: 6px;'
        ):
            with ui.row().classes('w-full items-center gap-3'):
                ui.label(result_label[0]).classes('text-xs font-bold text-white').style(
                    f'background: {result_color}; border-radius: 8px; '
                    f'width: 32px; height: 32px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                with ui.column().classes('flex-1 gap-0'):
                    ui.label(result_label).classes('text-xs font-bold').style(f'color: {COLORS["text"]}')
                    ui.label(f"{str(match.get('date', ''))[:10]} | {match.get('playlist', 'N/A')}").classes('text-xs').style(f'color: {COLORS["text_muted"]}')

                with ui.column().classes('items-end gap-0'):
                    ui.label(f"{match.get('goals', 0)}G {match.get('assists', 0)}A {match.get('saves', 0)}S").classes('text-xs font-medium').style(f'color: {COLORS["text_secondary"]}')
                    ui.label(f"Score: {match.get('score', 0)}").classes('text-xs').style(f'color: {COLORS["text_muted"]}')

                ui.label(f"{prox:.0f}%").classes('text-xs font-bold text-white').style(
                    f'background: {COLORS["cyan"]}; border-radius: 6px; padding: 4px 8px;'
                )

            # Expanded details
            with ui.expansion('Detalhes da Partida', icon='expand_more').classes('w-full').style(
                f'background: {COLORS["surface"]}; border-radius: 8px; margin-top: 8px;'
            ):
                ui.label(f"Playlist: {match.get('playlist', 'N/A')}").classes('text-xs').style(f'color: {COLORS["text_secondary"]}')
                ui.label(f"Oponentes: {match.get('opponent_rank', 'N/A')}").classes('text-xs').style(f'color: {COLORS["text_secondary"]}')

                ui.label('Métricas').classes('text-xs font-semibold').style(f'color: {COLORS["text"]}')
                self._build_match_metrics_inline(match)

                ui.label(f"Replay ID: {match.get('replay_id', 'N/A')}").classes('text-xs').style(
                    f'color: {COLORS["text_muted"]}; background: {COLORS["surface"]}; '
                    f'border-radius: 6px; padding: 8px;'
                )

    def _build_match_metrics_inline(self, match: dict) -> None:
        metrics = [
            ("Boost Médio", f"{match.get('boost_avg', 0):.1f}", COLORS['warning']),
            ("Velocidade", f"{match.get('avg_speed', 0):.0f} u/s", COLORS['primary']),
            ("Dist. Bola", f"{match.get('avg_distance_to_ball', 0):.0f}m", COLORS['accent']),
            ("Supersônico", f"{match.get('time_supersonic', 0):.1f}s", COLORS['cyan']),
        ]

        with ui.row().classes('w-full gap-2'):
            for label, value, color in metrics:
                with ui.card().classes('flex-1').style(
                    f'background: {COLORS["card"]}; border-radius: 6px; padding: 5px 8px; '
                    f'border: 1px solid {COLORS["border"]};'
                ):
                    with ui.row().classes('items-center gap-1'):
                        ui.label().style(
                            f'width: 3px; height: 3px; border-radius: 2px; background: {color};'
                        )
                        ui.label(label).classes('text-xs').style(f'color: {COLORS["text_muted"]}')
                        ui.space()
                        ui.label(value).classes('text-xs font-semibold').style(f'color: {COLORS["text"]}')

    # ── SETTINGS PAGE ──────────────────────────────────────────────────────

    def _show_settings(self) -> None:
        self.main_area.clear()
        with self.main_area:
            with ui.row().classes('items-center gap-3'):
                ui.icon('settings', size='18px').classes('text-white').style(
                    f'background: {COLORS["warning"]}; border-radius: 8px; '
                    f'width: 36px; height: 36px; display: flex; align-items: center; '
                    f'justify-content: center;'
                )
                with ui.column().classes('gap-0'):
                    ui.label('Configurações').classes('text-xl font-bold').style(f'color: {COLORS["text"]}')
                    ui.label('Preferências do aplicativo').classes('text-xs').style(f'color: {COLORS["text_muted"]}')

            ui.space()

            with ui.card().classes('w-96').style(
                _card_style('padding: 20px;')
            ):
                ui.label('Preferências').classes('text-sm font-bold').style(f'color: {COLORS["text"]}')
                ui.space()

                self.switch_monitoring = ui.switch(
                    'Monitoramento Automático',
                    value=self.config.get('auto_start_watcher', True)
                ).props(f'color="{COLORS["success"]}"')

                self.switch_notifications = ui.switch(
                    'Notificações',
                    value=self.config.get('notifications', False)
                ).props(f'color="{COLORS["primary"]}"')

                self.switch_auto_upload = ui.switch(
                    'Auto-Upload para Ballchasing',
                    value=self.config.get('auto_upload', False)
                ).props(f'color="{COLORS["accent"]}"')

                ui.space()

                ui.button('Salvar Configurações', on_click=self._save_settings).classes(
                    'text-white w-72'
                ).style(f'background: {COLORS["success"]}; text-transform: none;')

    def _save_settings(self) -> None:
        self.config['auto_start_watcher'] = self.switch_monitoring.value
        self.config['notifications'] = self.switch_notifications.value
        self.config['auto_upload'] = self.switch_auto_upload.value

        config_path = Path("config.json")
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            config_data['auto_start_watcher'] = self.switch_monitoring.value
            config_data['notifications'] = self.switch_notifications.value
            config_data['auto_upload'] = self.switch_auto_upload.value
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except (json.JSONDecodeError, IOError):
            pass

        ui.notification('Configurações salvas com sucesso!', type='positive',
                        color=COLORS['success'])
        self._refresh_data()

    # ── DATA REFRESH ───────────────────────────────────────────────────────

    def _refresh_data(self) -> None:
        # Only update dashboard widgets when on the dashboard page
        # Other pages destroy these widgets via main_area.clear()
        if self.current_page != 0:
            return

        try:
            matches = self.db.get_matches(limit=10, playlist=self.current_playlist)
            today_matches = self.db.get_today_matches()

            if matches:
                latest = matches[0]
                self.boost_value.text = f"{latest.get('boost_avg', 0):.1f}"
                score = latest.get('proximity_score', 0) or 0
                self.proximity_value.text = f"{score:.1f}%"
                self.proximity_bar.value = (score or 0) / 100

            self.matches_value.text = str(len(today_matches))

            if matches:
                wins = sum(1 for m in matches if m.get('result') == 'win')
                win_rate = (wins / len(matches)) * 100
                self.winrate_value.text = f"{win_rate:.0f}%"

            self._update_evolution_charts(matches)
            self._update_comparison(matches)
            self._update_tips()
            self._update_table(matches)

        except Exception as e:
            print(f"Erro ao atualizar dados: {e}")

    def _update_evolution_charts(self, matches: list) -> None:
        from dashboard.charts import create_evolution_chart, CHART_COLORS

        self.evolution_container.clear()

        if not matches or len(matches) < 2:
            with self.evolution_container:
                with ui.column().classes('w-full items-center justify-center').style('height: 180px;'):
                    ui.icon('show_chart', size='28px').style(f'color: {COLORS["text_muted"]}')
                    ui.label('Jogue mais partidas para ver gráficos').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
            return

        sorted_matches = sorted(matches, key=lambda x: x.get('date', ''), reverse=False)

        with self.evolution_container:
            with ui.row().classes('w-full gap-2'):
                create_evolution_chart(sorted_matches, 'goals', 'Gols por Partida', CHART_COLORS['primary'])
                create_evolution_chart(sorted_matches, 'score', 'Score por Partida', CHART_COLORS['cyan'])
            with ui.row().classes('w-full gap-2'):
                create_evolution_chart(sorted_matches, 'boost_avg', 'Boost Médio', CHART_COLORS['warning'])

    def _update_comparison(self, matches: list) -> None:
        self.comparison_container.clear()

        pro_values = {
            'boost_avg': 42, 'avg_speed': 1600, 'time_supersonic': 35,
            'avg_distance_to_ball': 95
        }

        stats_to_compare = [
            ("Boost Médio", "boost_avg", "pads", COLORS['warning'], 'bolt'),
            ("Velocidade", "avg_speed", "u/s", COLORS['primary'], 'speed'),
            ("Tempo Supersônico", "time_supersonic", "s", COLORS['cyan'], 'rocket_launch'),
            ("Dist. Bola", "avg_distance_to_ball", "m", COLORS['accent'], 'gps_fixed'),
        ]

        latest = matches[0] if matches else {}

        with self.comparison_container:
            for label, stat_key, unit, color, icon_name in stats_to_compare:
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

                with ui.card().classes('w-full').style(_surface_style('padding: 10px 12px;')):
                    with ui.row().classes('w-full items-center gap-2'):
                        ui.icon(icon_name, size='12px').classes('text-white').style(
                            f'background: {color}; border-radius: 5px; '
                            f'width: 24px; height: 24px; display: flex; align-items: center; '
                            f'justify-content: center;'
                        )
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label(label).classes('text-xs font-semibold').style(f'color: {COLORS["text"]}')
                            ui.label(status_text).classes('text-xs').style(f'color: {dot_color}')
                        with ui.column().classes('items-end gap-0'):
                            ui.label(f"{my_val:.0f}").classes('text-sm font-bold').style(f'color: {COLORS["text"]}')
                            ui.label(f"{unit} (pro: {pro_val:.0f})").classes('text-xs').style(f'color: {COLORS["text_muted"]}')

                    ui.linear_progress(value=pct).style(
                        f'background: {COLORS["surface"]};'
                    ).props(f'color={color}')

    def _update_tips(self) -> None:
        self.tips_container.clear()

        real_tips = self._get_real_tips()

        if not real_tips:
            with self.tips_container:
                with ui.card().classes('w-full').style(_surface_style('padding: 8px 10px;')):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('info', size='14px').style(f'color: {COLORS["text_muted"]}')
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label('Sem dicas disponíveis').classes('text-xs font-semibold').style(f'color: {COLORS["text_muted"]}')
                            ui.label('Jogue partidas e tenha uma baseline do pro para ver dicas personalizadas').classes('text-xs').style(f'color: {COLORS["text_muted"]}')
            return

        tip_icons = {
            'boost': ('bolt', COLORS['warning']),
            'speed': ('speed', COLORS['cyan']),
            'position': ('gps_fixed', COLORS['success']),
            'aerial': ('arrow_upward', COLORS['accent']),
            'shot': ('gps_fixed', COLORS['success']),
            'default': ('lightbulb', COLORS['primary']),
        }

        with self.tips_container:
            for tip_text in real_tips[:3]:
                icon_name, color = tip_icons['default']
                tip_lower = tip_text.lower()

                if 'boost' in tip_lower or 'pad' in tip_lower:
                    icon_name, color = tip_icons['boost']
                elif 'velocidade' in tip_lower or 'supersônico' in tip_lower or 'speed' in tip_lower:
                    icon_name, color = tip_icons['speed']
                elif 'distância' in tip_lower or 'posição' in tip_lower or 'terço' in tip_lower:
                    icon_name, color = tip_icons['position']
                elif 'ar' in tip_lower or 'aerial' in tip_lower or 'voo' in tip_lower:
                    icon_name, color = tip_icons['aerial']
                elif 'finalização' in tip_lower or 'gol' in tip_lower or 'shot' in tip_lower:
                    icon_name, color = tip_icons['shot']

                title = tip_text[:45] + "..." if len(tip_text) > 45 else tip_text
                desc = tip_text if len(tip_text) > 45 else ""

                with ui.card().classes('w-full').style(_surface_style('padding: 8px 10px;')):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon(icon_name, size='14px').style(
                            f'background: {color}15; color: {color}; border-radius: 6px; '
                            f'width: 28px; height: 28px; display: flex; align-items: center; '
                            f'justify-content: center;'
                        )
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label(title).classes('text-xs font-semibold').style(f'color: {COLORS["text"]}')
                            if desc:
                                ui.label(desc).classes('text-xs').style(f'color: {COLORS["text_muted"]}')

    def _update_table(self, matches: list) -> None:
        self.table_container.clear()

        if not matches:
            return

        columns = [
            {'name': 'date', 'label': 'DATA', 'field': 'date', 'align': 'left'},
            {'name': 'result', 'label': 'RESULTADO', 'field': 'result', 'align': 'left'},
            {'name': 'gas', 'label': 'G/A/S', 'field': 'gas', 'align': 'left'},
            {'name': 'score', 'label': 'SCORE', 'field': 'score', 'align': 'left'},
            {'name': 'prox', 'label': 'PROXIMIDADE', 'field': 'prox', 'align': 'left'},
        ]

        rows = []
        for match in matches[:8]:
            result = match.get('result', '')
            result_label = "Vitória" if result == 'win' else "Derrota"
            prox = match.get('proximity_score', 0) or 0
            rows.append({
                'date': str(match.get('date', ''))[:10],
                'result': result_label,
                'gas': f"{match.get('goals', 0)} / {match.get('assists', 0)} / {match.get('saves', 0)}",
                'score': str(match.get('score', 0)),
                'prox': f"{prox:.0f}%",
            })

        with self.table_container:
            ui.table(columns=columns, rows=rows).style(
                f'background: transparent; color: {COLORS["text"]};'
            ).props('dark flat dense')

    def _get_real_tips(self) -> List[str]:
        if not self.comparer:
            return []
        try:
            matches = self.db.get_matches(limit=1)
            if not matches:
                return []
            latest = matches[0]
            playlist = latest.get('playlist', 'ranked-doubles')
            pro_name = self.config.get('pro_to_study', 'Zen')
            baseline_data = self.db.get_baseline(playlist, pro_name)
            if not baseline_data:
                return []
            baseline = baseline_data.get('averages', {})
            if not baseline:
                return []
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
            comparison = self.comparer.compare(player_stats, baseline)
            return comparison.get('tips', [])
        except Exception as e:
            print(f"Erro ao buscar dicas reais: {e}")
            return []

    # ── PUBLIC API ─────────────────────────────────────────────────────────

    def update_status(self, is_monitoring: bool) -> None:
        self.status_label.text = "Monitorando..." if is_monitoring else "Parado"
        self.status_dot.style(
            f'width: 7px; height: 7px; border-radius: 4px; '
            f'background: {COLORS["success"] if is_monitoring else COLORS["error"]};'
        )

    def refresh(self) -> None:
        self._refresh_data()
