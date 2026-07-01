"""
RLBot Pro - Premium Dashboard UI
Fiel ao design Stitch: glassmorphism, neon accents, Material Design 3 colors.
Migrado de Flet para NiceGUI. Design inspirado em esports/rocket league.
"""
import json
import math
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from nicegui import ui

from database import Database
from bot.comparer import ProComparer
from bot.ai_coach import AICoach


# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — Material Design 3 inspired, esport gaming
# ══════════════════════════════════════════════════════════════════════════════

C = {
    'bg':                   '#0a0b0f',
    'surface':              '#10131a',
    'surface_dim':          '#10131a',
    'surface_bright':       '#363941',
    'surface_low':          '#191b23',
    'surface_cont':         '#1d2027',
    'surface_high':         '#272a31',
    'surface_highest':      '#32353c',
    'card':                 '#161822',
    'card_border':          'rgba(255,255,255,0.1)',
    'primary':              '#adc6ff',
    'primary_container':    '#4d8eff',
    'primary_dim':          '#00285d',
    'on_primary':           '#002e6a',
    'secondary':            '#d0bcff',
    'secondary_container':  '#571bc1',
    'tertiary':             '#4cd7f6',
    'tertiary_cont':        '#009eb9',
    'error':                '#ffb4ab',
    'error_cont':           '#93000a',
    'success':              '#4ade80',
    'text':                 '#e1e2ec',
    'text_var':             '#c2c6d6',
    'text_dim':             '#8c909f',
    'outline':              '#8c909f',
    'outline_var':          '#424754',
    'surface_variant':      '#2a2d35',
}


# ══════════════════════════════════════════════════════════════════════════════
# STYLE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def glass(extra: str = "") -> str:
    return (
        f'background: rgba(22,24,34,0.8); backdrop-filter: blur(12px); '
        f'border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; '
        f'{extra}'
    )

def surface(extra: str = "") -> str:
    return (
        f'background: {C["surface"]}; border: 1px solid rgba(255,255,255,0.06); '
        f'border-radius: 16px; {extra}'
    )

def label_caps(extra: str = "") -> str:
    return f'font-size: 11px; letter-spacing: 0.1em; font-weight: 600; text-transform: uppercase; {extra}'

def stat_mono(extra: str = "") -> str:
    return f'font-family: "JetBrains Mono", monospace; {extra}'

def icon_circle(size: int, bg: str, extra: str = "") -> str:
    return (
        f'width: {size}px; height: {size}px; border-radius: {size//4}px; '
        f'background: {bg}; display: flex; align-items: center; '
        f'justify-content: center; {extra}'
    )

def glow(color: str, intensity: float = 0.2) -> str:
    hex_c = color.lstrip('#')
    r, g, b = int(hex_c[:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
    return f'box-shadow: 0 0 25px rgba({r},{g},{b},{intensity});'

def sidebar_btn(active: bool = False) -> str:
    if active:
        return (
            f'width: 48px; height: 48px; border-radius: 12px; display: flex; '
            f'align-items: center; justify-content: center; '
            f'background: rgba(173,198,255,0.1); border-left: 3px solid {C["primary"]}; '
            f'color: {C["primary"]}; transition: all 0.2s ease;'
        )
    return (
        f'width: 48px; height: 48px; border-radius: 12px; display: flex; '
        f'align-items: center; justify-content: center; '
        f'color: {C["text_var"]}; background: transparent; border: none; '
        f'transition: all 0.2s ease;'
    )

def nav_item_style(active: bool) -> str:
    if active:
        return (
            f'width: 48px; height: 48px; border-radius: 12px; display: flex; '
            f'align-items: center; justify-content: center; '
            f'background: rgba(173,198,255,0.1); border-left: 3px solid {C["primary"]}; '
            f'color: {C["primary"]}; transition: all 0.2s ease;'
        )
    return (
        f'width: 48px; height: 48px; border-radius: 12px; display: flex; '
        f'align-items: center; justify-content: center; '
        f'color: {C["text_var"]}; background: transparent; border: none; '
        f'cursor: pointer; transition: all 0.2s ease;'
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD CLASS
# ══════════════════════════════════════════════════════════════════════════════

class Dashboard:
    """Premium gaming analytics dashboard."""

    NAV_ITEMS = [
        ('dashboard',       'Dashboard'),
        ('analytics',       'Replay Analysis'),
        ('history',         'Match History'),
    ]

    def __init__(self, db: Database, config: dict,
                 comparer: Optional[ProComparer] = None,
                 ai_coach: Optional[AICoach] = None):
        self.db = db
        self.config = config
        self.comparer = comparer
        self.ai_coach = ai_coach
        self.current_page = 0
        self.nav_buttons: list = []
        self.main_area = None

    # ── BUILD ───────────────────────────────────────────────────────────────

    def build(self) -> None:
        ui.dark_mode(True)
        ui.add_head_html('''
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
        ''')
        ui.add_head_html(self._global_css())

        with ui.column().classes('w-full h-screen').style('margin:0; padding:0;'):
            with ui.row().classes('w-full flex-1').style('margin:0; padding:0;'):
                self._build_sidebar()
                ui.separator().style(f'width:1px; background:{C["outline_var"]}; margin:0;')
                self.main_area = (
                    ui.column()
                    .classes('flex-1 overflow-auto')
                    .style(f'background: {C["bg"]}; padding: 24px;')
                )

        self.page_containers = []
        with self.main_area:
            for _ in range(4):
                container = ui.column().classes('w-full')
                self.page_containers.append(container)

        self._build_page_content()
        self._show_page(0)

    def _global_css(self) -> str:
        return '''
        <style>
            body { background: #0a0b0f; color: #e1e2ec; -webkit-font-smoothing: antialiased; }
            .nicegui-content { padding: 0 !important; }

            * { font-family: 'Inter', sans-serif; }
            .material-symbols-outlined, .q-icon, [class*="q-icon"] { font-family: 'Material Symbols Outlined', 'Material Icons', sans-serif !important; }

            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(14px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .fade-in { animation: fadeInUp 0.45s cubic-bezier(0.22,1,0.36,1) forwards; opacity: 0; }

            @keyframes pulse-slow {
                0%, 100% { opacity: 0.8; transform: scale(1); }
                50% { opacity: 1; transform: scale(1.05); }
            }
            .animate-pulse-slow { animation: pulse-slow 3s infinite ease-in-out; }

            @keyframes ping-glow {
                0% { box-shadow: 0 0 0 0 rgba(76,215,246,0.5); }
                70% { box-shadow: 0 0 0 8px rgba(76,215,246,0); }
                100% { box-shadow: 0 0 0 0 rgba(76,215,246,0); }
            }
            .ping-glow { animation: ping-glow 2s infinite; }

            .glass-card {
                background: rgba(22,24,34,0.8);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 24px;
                transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
            }
            .glass-card:hover {
                border-color: rgba(173,198,255,0.3);
                transform: translateY(-2px);
                box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5), 0 0 15px rgba(173,198,255,0.1);
            }

            .glass-card-sm {
                background: rgba(22,24,34,0.8);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px;
            }

            .glow-primary { box-shadow: 0 0 25px rgba(173,198,255,0.2); }
            .glow-text { text-shadow: 0 0 10px rgba(173,198,255,0.5); }

            .radar-bg {
                background-image: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
                background-size: 30px 30px;
            }

            .tech-grid {
                background-image: radial-gradient(circle at 2px 2px, rgba(255,255,255,0.03) 1px, transparent 0);
                background-size: 40px 40px;
            }

            .win-border { box-shadow: inset 4px 0 0 0 #4ade80; }
            .loss-border { box-shadow: inset 4px 0 0 0 #f87171; }

            .ring-chart { transform: rotate(-90deg); }
            .ring-bg { fill: none; stroke: rgba(255,255,255,0.05); }
            .ring-progress { fill: none; stroke-linecap: round; transition: stroke-dashoffset 1s ease-out; }

            .stat-bar { height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }

            .custom-scroll::-webkit-scrollbar { width: 4px; }
            .custom-scroll::-webkit-scrollbar-track { background: transparent; }
            .custom-scroll::-webkit-scrollbar-thumb { background: rgba(173,198,255,0.2); border-radius: 10px; }

            .nav-btn:hover { background: rgba(50,53,60,0.8) !important; color: #e1e2ec !important; }
        </style>
        '''

    # ── SIDEBAR ─────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        self.nav_buttons = []
        with ui.column().classes('items-center py-4').style(
            f'width: 72px; background: rgba(16,19,26,0.95); '
            f'border-right: 1px solid rgba(255,255,255,0.1); '
            f'backdrop-filter: blur(20px);'
        ):
            # Logo
            ui.label('RL').style(
                f'font-size: 20px; font-weight: 900; color: {C["primary"]}; '
                f'margin-bottom: 28px; letter-spacing: -0.02em;'
            )

            # Nav items
            for i, (icon, label) in enumerate(self.NAV_ITEMS):
                is_active = (i == self.current_page)
                btn = (
                    ui.button(icon=icon)
                    .style(nav_item_style(is_active))
                    .props('flat')
                )
                btn.on_click(lambda e, idx=i: self._on_nav(idx))
                ui.tooltip(label).classes('text-xs')
                self.nav_buttons.append((btn, i))
                if i == 2:
                    ui.space().style('height: 8px;')

            ui.space()

            # Settings (below)
            settings_btn = (
                ui.button(icon='settings')
                .style(nav_item_style(self.current_page == 6))
                .props('flat')
            )
            settings_btn.on_click(lambda e: self._on_nav(6))
            ui.tooltip('Settings').classes('text-xs')

            ui.space().style('height: 8px;')

            # Profile avatar
            ui.avatar(
                icon='account_circle',
                color=C['surface_cont'],
                text_color=C['text_var'],
                size='40px'
            ).style(
                f'border: 2px solid rgba(173,198,255,0.3); border-radius: 50%; cursor: pointer;'
            )

    def _on_nav(self, index: int) -> None:
        self.current_page = index
        for btn, idx in self.nav_buttons:
            btn.style(nav_item_style(idx == index))
        self._show_page(index)

    def _show_page(self, index: int) -> None:
        for i, container in enumerate(self.page_containers):
            container.set_visibility(i == index)

    def _build_page_content(self) -> None:
        with self.page_containers[0]:
            self._build_dashboard_page()
        with self.page_containers[1]:
            self._build_replay_analysis_page()
        with self.page_containers[2]:
            self._build_match_history_page()
        with self.page_containers[3]:
            self._build_settings_page()

    # ════════════════════════════════════════════════════════════════════════
    # DASHBOARD PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_dashboard_page(self) -> None:
        self._build_top_bar('Dashboard', 'Acompanhe suas estatísticas e evolução')
        self._build_hero_stats()
        ui.space().style('height: 12px;')
        self._build_pro_comparison_section()
        ui.space().style('height: 12px;')
        self._build_performance_timeline()
        ui.space().style('height: 12px;')
        self._build_match_history_preview()

    # ── TOP BAR ─────────────────────────────────────────────────────────────

    def _build_top_bar(self, title: str, subtitle: str = "") -> None:
        with ui.row().classes('w-full items-center justify-between').style('margin-bottom: 24px;'):
            with ui.column().classes('gap-0'):
                ui.label(title).style(
                    f'font-size: 24px; font-weight: 700; color: {C["text"]}; line-height: 1.3;'
                )
                if subtitle:
                    ui.label(subtitle).style(f'font-size: 14px; color: {C["text_var"]};')

            # Right side: icons + player
            with ui.row().classes('items-center gap-2'):
                ui.button(icon='notifications').props('flat round').style(
                    f'color: {C["text_var"]};'
                )
                ui.button(icon='sensors').props('flat round').style(
                    f'color: {C["text_var"]};'
                )
                ui.button(icon='folder').props('flat round').style(
                    f'color: {C["text_var"]};'
                )

                ui.separator().style(f'width: 1px; height: 32px; background: rgba(255,255,255,0.1);')

                with ui.row().classes('items-center gap-3'):
                    ui.label(self.config.get('player_name', 'Player')).style(
                        f'font-size: 14px; font-weight: 500; color: {C["text_var"]};'
                    )
                    ui.avatar(
                        icon='person',
                        color=C['primary_container'],
                        text_color='white',
                        size='40px'
                    ).style(f'border: 2px solid rgba(173,198,255,0.3); border-radius: 50%;')

    # ── HERO STATS GRID ─────────────────────────────────────────────────────

    def _build_hero_stats(self) -> None:
        with ui.row().classes('w-full gap-4'):
            self._build_player_card()
            self._build_session_card()
            self._build_winrate_card()
            self._build_proximity_card()

    def _build_player_card(self) -> None:
        with ui.card().classes('flex-1 fade-in').style(glass('padding: 20px; border-radius: 24px;')):
            with ui.row().classes('items-center gap-4'):
                ui.avatar(
                    icon='sports_esports',
                    color=C['primary_container'],
                    text_color='white',
                    size='56px'
                ).style(
                    f'border-radius: 16px; border: 1px solid rgba(173,198,255,0.2);'
                )
                with ui.column().classes('gap-0'):
                    ui.label(self.config.get('player_name', 'Player')).style(
                        f'font-size: 18px; font-weight: 700; color: {C["text"]}; line-height: 1.2;'
                    )
                    with ui.row().classes('items-center gap-2'):
                        ui.label('DIAMOND III').style(label_caps(f'color: {C["primary"]};'))
                        ui.label('•').style(f'color: {C["text_dim"]}; font-size: 10px;')
                        ui.label('MMR 1042').style(
                            f'font-size: 12px; font-family: "JetBrains Mono"; color: {C["text_var"]};'
                        )

            ui.space().style('height: 16px;')

            # Season progress
            with ui.row().classes('w-full justify-between'):
                ui.label('SEASON PROGRESS').style(label_caps(f'color: {C["text_var"]}; font-size: 10px;'))
                ui.label('82%').style(label_caps(f'color: {C["primary"]}; font-size: 10px;'))
            ui.linear_progress(value=0.82).style(
                f'height: 6px; border-radius: 3px; background: rgba(255,255,255,0.05);'
            ).props(f'color="{C["primary_container"]}"')

    def _build_session_card(self) -> None:
        with ui.card().classes('flex-1 fade-in').style(glass('padding: 20px; animation-delay: 0.05s;')):
            with ui.column().classes('gap-0'):
                ui.label("TODAY'S SESSION").style(label_caps(f'color: {C["text_var"]}; font-size: 10px;'))
                with ui.row().classes('items-baseline gap-2'):
                    ui.label('05').style(
                        f'font-size: 40px; font-weight: 900; color: {C["primary"]}; '
                        f'line-height: 1; text-shadow: 0 0 10px rgba(173,198,255,0.5);'
                    )
                    ui.label('GAMES').style(f'color: {C["text_dim"]}; font-size: 14px;')

            ui.space().style('height: 12px;')

            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.label('3V').style(f'font-size: 16px; font-weight: 700; color: {C["tertiary"]};')
                    ui.label('/').style(f'color: {C["text_dim"]};')
                    ui.label('2D').style(f'font-size: 16px; font-weight: 700; color: {C["error"]};')

                with ui.row().classes('items-center gap-1').style(
                    f'background: rgba(76,215,246,0.1); padding: 3px 10px; border-radius: 6px;'
                ):
                    ui.icon('bolt', size='14px').style(f'color: {C["tertiary"]};')
                    ui.label('STREAK W2').style(
                        f'font-size: 10px; font-weight: 700; color: {C["tertiary"]};'
                    )

    def _build_winrate_card(self) -> None:
        with ui.card().classes('flex-1 fade-in').style(glass('padding: 20px; animation-delay: 0.1s;')):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label('WIN RATE').style(label_caps(f'color: {C["text_var"]}; font-size: 10px;'))
                    ui.label('65%').style(
                        f'font-size: 32px; font-weight: 900; color: {C["tertiary"]}; line-height: 1.2;'
                    )
                    ui.label('Últimas 10 partidas').style(
                        f'font-size: 10px; color: {C["text_dim"]}; font-style: italic; margin-top: 4px;'
                    )

                # SVG ring chart
                ui.html(self._svg_ring(65, 80, C['tertiary']))

    def _build_proximity_card(self) -> None:
        with ui.card().classes('flex-1 fade-in').style(
            glass(f'padding: 20px; border-color: rgba(173,198,255,0.2); animation-delay: 0.15s;')
        ):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label('PROXIMITY SCORE').style(
                        label_caps(f'color: {C["text_var"]}; font-size: 10px;')
                    )
                    ui.label('72%').style(
                        f'font-size: 32px; font-weight: 900; color: {C["primary"]}; line-height: 1.2;'
                    )

                ui.html(
                    f'<div style="{icon_circle(40, "rgba(173,198,255,0.2)")}">'
                    f'<span class="material-symbols-outlined" style="color:{C["primary"]};">psychology</span>'
                    f'</div>'
                )

            ui.space().style('height: 8px;')
            with ui.row().classes('w-full justify-between'):
                ui.label('VS ZEN').style(f'font-size: 10px; color: {C["text_dim"]};')
                ui.label('+2% week').style(stat_mono(f'font-size: 10px; color: {C["primary"]};'))

            ui.linear_progress(value=0.72).style(
                f'height: 4px; border-radius: 2px; background: rgba(255,255,255,0.05); margin-top: 8px;'
            ).props(f'color="{C["primary_container"]}"')

    # ── PRO COMPARISON (DASHBOARD CENTER) ───────────────────────────────────

    def _build_pro_comparison_section(self) -> None:
        with ui.row().classes('w-full gap-4'):
            self._build_radar_comparison()
            self._build_ai_coach_panel()

    def _build_radar_comparison(self) -> None:
        with ui.card().classes('flex-1 radar-bg fade-in').style(
            glass('padding: 32px; overflow: hidden; position: relative; animation-delay: 0.2s;')
        ):
            # Background glow
            ui.html(
                '<div style="position:absolute; top:-80px; right:-80px; width:256px; height:256px; '
                f'background: rgba(173,198,255,0.05); border-radius: 50%; filter: blur(80px); pointer-events:none;"></div>'
            )

            with ui.row().classes('w-full gap-10'):
                # Left: circular score
                with ui.column().classes('items-center justify-center flex-1'):
                    ui.html(self._svg_large_ring(72, 128, C['primary']))
                    ui.space().style('height: 24px;')

                    with ui.row().classes('items-center gap-6'):
                        with ui.row().classes('items-center gap-2'):
                            ui.html(f'<div style="width:12px; height:12px; border-radius:50%; background:{C["primary"]}; box-shadow: 0 0 8px rgba(173,198,255,1);"></div>')
                            ui.label('YOU').style(f'font-size: 11px; font-weight: 700;')
                        with ui.row().classes('items-center gap-2'):
                            ui.html(f'<div style="width:12px; height:12px; border-radius:50%; border: 2px solid {C["tertiary"]};"></div>')
                            ui.label('ZEN').style(f'font-size: 11px; font-weight: 700; color: {C["text_var"]};')

                # Right: metrics bars
                with ui.column().classes('flex-1 justify-center gap-6'):
                    ui.label('Professional Comparison').style(
                        f'font-size: 22px; font-weight: 700; color: {C["text"]};'
                    )
                    ui.label('Sua gameplay em comparação direta com o melhor jogador do mundo.').style(
                        f'font-size: 14px; color: {C["text_var"]}; line-height: 1.5;'
                    )

                    ui.space().style('height: 8px;')

                    metrics = [
                        ('Boost Management', 84, 92),
                        ('Positioning', 61, 98),
                        ('Defense', 91, 89),
                        ('Speed', 78, 95),
                        ('Shooting', 65, 88),
                    ]
                    for label, you, pro in metrics:
                        self._build_metric_bar(label, you, pro)

                    ui.space().style('height: 12px;')

                    ui.button('See detailed analysis →').style(
                        f'background: {C["primary_container"]}; color: {C["on_primary"]}; '
                        f'border-radius: 16px; padding: 12px 24px; font-weight: 700; '
                        f'width: 100%; text-transform: none; box-shadow: 0 0 25px rgba(173,198,255,0.2);'
                    ).on_click(lambda: self._on_nav(3))

    def _build_metric_bar(self, label: str, you: int, pro: int) -> None:
        with ui.column().classes('w-full gap-1'):
            with ui.row().classes('w-full justify-between'):
                ui.label(label).style(f'font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;')
                ui.label(f'{you} / {pro}').style(
                    stat_mono(f'font-size: 12px; color: {C["primary"]};')
                )
            with ui.row().classes('w-full').style('height: 6px;'):
                ui.html(
                    f'<div style="width: 100%; height: 6px; background: rgba(255,255,255,0.05); '
                    f'border-radius: 3px; overflow: hidden; display: flex;">'
                    f'<div style="width: {you}%; height: 100%; background: {C["primary"]}; border-radius: 3px;"></div>'
                    f'</div>'
                )

    # ── AI COACH PANEL ──────────────────────────────────────────────────────

    def _build_ai_coach_panel(self) -> None:
        with ui.card().classes('w-96 fade-in').style(
            glass('padding: 0; overflow: hidden; display: flex; flex-direction: column; height: 500px; animation-delay: 0.25s;')
        ):
            # Header
            with ui.row().classes('w-full items-center justify-between').style(
                f'padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.02);'
            ):
                with ui.row().classes('items-center gap-3'):
                    ui.html(
                        f'<div style="width:40px; height:40px; border-radius:12px; '
                        f'background: linear-gradient(135deg, {C["tertiary_cont"]}, {C["secondary_container"]}); '
                        f'display:flex; align-items:center; justify-content:center;" class="animate-pulse-slow">'
                        f'<span class="material-symbols-outlined" style="color:white; font-variation-settings:\'FILL\' 1;">auto_awesome</span>'
                        f'</div>'
                    )
                    with ui.column().classes('gap-0'):
                        ui.label('AI Coach').style(f'font-size: 14px; font-weight: 700; color: {C["text"]};')
                        ui.label('POWERED BY NVIDIA NIM').style(label_caps(f'color: {C["text_var"]}; opacity: 0.6; font-size: 9px;'))

                ui.html(
                    f'<div style="width:8px; height:8px; border-radius:50%; background:{C["tertiary"]}; '
                    f'animation: ping-glow 2s infinite;" class="ping-glow"></div>'
                )

            # Messages
            self.chat_messages = ui.column().classes('w-full').style(
                f'padding: 16px; flex: 1 1 0; overflow-y: auto; min-height: 0;'
            )
            with self.chat_messages:
                self._chat_msg('ai', 'Welcome back, <b>cash</b>. I\'ve analyzed your last 5 matches. Ready for the breakdown?')

            # Input
            with ui.row().classes('w-full items-center gap-2').style(
                f'padding: 16px; border-top: 1px solid rgba(255,255,255,0.05);'
            ):
                self.chat_input = ui.input(placeholder='Pergunte ao coach...').classes('flex-1').style(
                    f'background: {C["surface_cont"]}; border: 1px solid rgba(255,255,255,0.1); '
                    f'border-radius: 16px; padding: 12px 16px;'
                ).props('borderless dense')
                ui.button(icon='send').style(
                    f'color: {C["primary"]}; background: transparent; border: none;'
                ).on_click(self._send_chat)

    def _chat_msg(self, sender: str, message: str, container=None) -> None:
        is_ai = sender == 'ai'
        target = container or self.chat_messages
        with target:
            with ui.card().classes('w-full').style(
                f'background: {"rgba(50,53,60,0.8)" if is_ai else "rgba(173,198,255,0.15)"}; '
                f'border: 1px solid {"rgba(255,255,255,0.05)" if is_ai else "rgba(173,198,255,0.2)"}; '
                f'border-radius: {"16px 16px 16px 4px" if is_ai else "16px 16px 4px 16px"}; '
                f'padding: 12px 16px; margin-bottom: 8px; '
                f'{"max-width: 85%;" if is_ai else "max-width: 85%; margin-left: auto;"}'
            ):
                ui.html(f'<p style="font-size: 14px; color: {C["text"]}; margin: 0; line-height: 1.5;">{message}</p>')
        ui.run_javascript(f'''
            const el = document.querySelector("[style*='overflow-y: auto']");
            if (el) el.scrollTop = el.scrollHeight;
        ''')

    def _send_chat(self) -> None:
        msg = self.chat_input.value
        if not msg:
            return
        self._chat_msg('user', msg)
        self.chat_input.value = ''

        if self.ai_coach:
            context = self._get_chat_context()
            response = self.ai_coach.chat(msg, context)
            self._chat_msg('ai', response or 'Erro ao processar mensagem.')
        else:
            self._chat_msg('ai', 'AI Coach não disponível. Configure <b>nvidia_api_key</b> no config.json.')

    def _get_chat_context(self) -> str:
        try:
            matches = self.db.get_matches(limit=5)
            if not matches:
                return 'Nenhuma partida registrada.'
            latest = matches[0]
            return (
                f"Última partida: {latest.get('result', 'N/A')}\n"
                f"Boost médio: {latest.get('boost_avg', 0):.1f}\n"
                f"Velocidade: {latest.get('avg_speed', 0):.0f} u/s\n"
                f"Gols: {latest.get('goals', 0)}"
            )
        except Exception:
            return ''

    # ── PERFORMANCE TIMELINE ────────────────────────────────────────────────

    def _build_performance_timeline(self) -> None:
        with ui.card().classes('w-full fade-in').style(glass('padding: 20px; animation-delay: 0.3s;')):
            with ui.row().classes('w-full items-center justify-between').style('margin-bottom: 24px;'):
                with ui.column().classes('gap-0'):
                    ui.label('Performance Timeline').style(
                        f'font-size: 18px; font-weight: 700; color: {C["text"]};'
                    )
                    ui.label('Sua evolução histórica consolidada por métricas chave.').style(
                        f'font-size: 12px; color: {C["text_var"]}; margin-top: 4px;'
                    )

                with ui.row().classes('items-center').style(
                    f'background: {C["surface_low"]}; padding: 4px; border-radius: 12px; '
                    f'border: 1px solid rgba(255,255,255,0.05);'
                ):
                    for label in ['7D', '30D', 'Season']:
                        is_active = label == '7D'
                        ui.button(label).style(
                            f'padding: 6px 16px; border-radius: 8px; font-size: 12px; font-weight: 700; '
                            f'{"background: " + C["surface_highest"] + "; color: " + C["primary"] + ";" if is_active else "background: transparent; color: " + C["text_var"] + ";"}'
                            f'border: none; text-transform: none;'
                        ).props('flat')

            self.timeline_container = ui.element('div').classes('w-full').style('height: 260px;')

    def _update_timeline(self, matches: list) -> None:
        self.timeline_container.clear()
        if not matches or len(matches) < 2:
            with self.timeline_container:
                with ui.column().classes('w-full h-full items-center justify-center'):
                    ui.icon('show_chart', size='48px').style(f'color: {C["text_dim"]};')
                    ui.label('Jogue mais partidas para ver a timeline').style(
                        f'font-size: 13px; color: {C["text_dim"]};'
                    )
            return

        sorted_m = sorted(matches, key=lambda x: x.get('date', ''), reverse=False)
        labels = []
        winrate_data = []
        similarity_data = []

        for m in sorted_m:
            try:
                dt = datetime.strptime(str(m.get('date', ''))[:10], '%Y-%m-%d')
                labels.append(dt.strftime('%d/%m'))
            except (ValueError, TypeError):
                labels.append(str(len(labels) + 1))
            winrate_data.append(m.get('proximity_score', 50) or 50)
            similarity_data.append(m.get('proximity_score', 50) or 50)

        option = {
            'backgroundColor': 'transparent',
            'grid': {'left': '5%', 'right': '3%', 'top': '8%', 'bottom': '15%'},
            'tooltip': {
                'trigger': 'axis',
                'backgroundColor': C['surface_cont'],
                'borderColor': C['outline_var'],
                'textStyle': {'color': C['text'], 'fontSize': 11}
            },
            'legend': {
                'data': ['Win Rate', 'Pro Similarity'],
                'textStyle': {'color': C['text_dim'], 'fontSize': 10},
                'top': 0
            },
            'xAxis': {
                'type': 'category', 'data': labels,
                'axisLine': {'lineStyle': {'color': C['outline_var']}},
                'axisLabel': {'color': C['text_dim'], 'fontSize': 10},
                'axisTick': {'show': False}
            },
            'yAxis': {
                'type': 'value',
                'axisLine': {'show': False},
                'splitLine': {'lineStyle': {'color': C['outline_var'], 'type': 'dashed'}},
                'axisLabel': {'color': C['text_dim'], 'fontSize': 10}
            },
            'series': [
                {
                    'name': 'Win Rate',
                    'type': 'line',
                    'data': winrate_data,
                    'smooth': True,
                    'symbol': 'circle', 'symbolSize': 6,
                    'lineStyle': {'color': C['primary'], 'width': 3},
                    'itemStyle': {'color': C['primary'], 'borderWidth': 2, 'borderColor': '#fff'},
                    'areaStyle': {
                        'color': {
                            'type': 'linear', 'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                            'colorStops': [
                                {'offset': 0, 'color': 'rgba(173,198,255,0.3)'},
                                {'offset': 1, 'color': 'rgba(173,198,255,0.01)'}
                            ]
                        }
                    }
                },
                {
                    'name': 'Pro Similarity',
                    'type': 'line',
                    'data': similarity_data,
                    'smooth': True,
                    'symbol': 'circle', 'symbolSize': 5,
                    'lineStyle': {'color': C['tertiary'], 'width': 2, 'type': 'dashed'},
                    'itemStyle': {'color': C['tertiary']}
                }
            ]
        }

        with self.timeline_container:
            ui.echart(option).style('width: 100%; height: 240px;')

            with ui.row().classes('w-full items-center gap-6').style('margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 16px;'):
                for color, label in [(C['primary'], 'Win Rate'), (C['tertiary'], 'MMR Progress'), (C['secondary'], 'Pro Similarity')]:
                    with ui.row().classes('items-center gap-2'):
                        ui.html(f'<div style="width:10px; height:10px; border-radius:50%; background:{color};"></div>')
                        ui.label(label).style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))

    # ── MATCH HISTORY PREVIEW ───────────────────────────────────────────────

    def _build_match_history_preview(self) -> None:
        matches = self.db.get_matches(limit=5)

        with ui.card().classes('w-full fade-in').style(glass('padding: 20px; animation-delay: 0.35s;')):
            with ui.row().classes('w-full items-center justify-between').style('margin-bottom: 20px;'):
                ui.label('Recent Matches').style(
                    f'font-size: 18px; font-weight: 700; color: {C["text"]};'
                )
                ui.button('View All →').style(
                    f'color: {C["primary"]}; background: transparent; border: none; '
                    f'font-size: 13px; font-weight: 600; text-transform: none;'
                ).on_click(lambda: self._on_nav(2))

            if not matches:
                with ui.column().classes('w-full items-center justify-center').style('padding: 40px 0;'):
                    ui.icon('inbox', size='48px').style(f'color: {C["text_dim"]};')
                    ui.label('Nenhuma partida registrada').style(f'color: {C["text_dim"]}; margin-top: 8px;')
                return

            for match in matches[:4]:
                self._build_match_card(match)

    def _build_match_card(self, match: dict) -> None:
        result = match.get('result', '')
        is_win = result == 'win'
        border_class = 'win-border' if is_win else 'loss-border'
        result_color = C['success'] if is_win else C['error']
        result_letter = 'W' if is_win else 'L'

        with ui.card().classes(f'w-full {border_class}').style(
            glass('padding: 16px 20px; border-radius: 16px; margin-bottom: 12px;')
        ):
            with ui.row().classes('w-full items-center gap-6'):
                # Result circle
                ui.html(
                    f'<div style="width:48px; height:48px; border-radius:50%; '
                    f'border: 2px solid {result_color}40; background: {result_color}15; '
                    f'display:flex; align-items:center; justify-content:center; '
                    f'font-size: 18px; font-weight:900; color: {result_color}; flex-shrink:0;">'
                    f'{result_letter}</div>'
                )

                # Identity
                with ui.column().classes('flex-1 gap-0'):
                    ui.label(match.get('playlist', '2v2 Ranked')).style(
                        f'font-size: 15px; font-weight: 700; color: {C["text"]};'
                    )
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('groups', size='14px').style(f'color: {C["text_dim"]};')
                        ui.label(match.get('playlist', 'N/A')).style(
                            f'font-size: 12px; color: {C["text_var"]};'
                        )

                # Score
                goals = match.get('goals', 0)
                assists = match.get('assists', 0)
                saves = match.get('saves', 0)
                score = match.get('score', 0)

                with ui.column().classes('items-center gap-1'):
                    ui.label(str(score)).style(
                        stat_mono(f'font-size: 18px; font-weight: 700; color: {C["primary"]};')
                    )
                    ui.label('SCORE').style(label_caps(f'font-size: 9px; color: {C["text_dim"]};'))

                # GAS
                with ui.row().classes('items-center gap-3'):
                    for val, lbl in [(goals, 'G'), (assists, 'A'), (saves, 'S')]:
                        with ui.column().classes('items-center gap-0'):
                            ui.label(str(val)).style(stat_mono(f'font-size: 16px; font-weight: 700; color: {C["text"]};'))
                            ui.label(lbl).style(label_caps(f'font-size: 9px; color: {C["text_dim"]};'))

                # Proximity
                prox = match.get('proximity_score', 0) or 0
                ui.html(
                    f'<div style="padding: 6px 12px; border-radius: 20px; '
                    f'background: rgba(76,215,246,0.1); border: 1px solid rgba(76,215,246,0.3); '
                    f'display: flex; flex-direction: column; align-items: center;">'
                    f'<span style="font-size: 9px; color: {C["tertiary"]}; font-weight: 700; text-transform: uppercase;">PROX</span>'
                    f'<span style="font-size: 14px; font-weight: 700; color: {C["tertiary"]};">{prox:.0f}%</span>'
                    f'</div>'
                )

    # ════════════════════════════════════════════════════════════════════════
    # REPLAY ANALYSIS PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_replay_analysis_page(self) -> None:
        with ui.row().classes('w-full items-center justify-between').style('margin-bottom: 24px;'):
            with ui.column().classes('gap-0'):
                ui.label('Replay Analysis').style(
                    f'font-size: 24px; font-weight: 700; color: {C["text"]};'
                )
                ui.label('Análise completa de um replay com coaching IA').style(
                    f'font-size: 14px; color: {C["text_var"]};'
                )

            with ui.row().classes('items-center gap-3'):
                self.replay_select = ui.select(
                    options={}, value=None, label='Selecionar replay',
                    on_change=self._on_replay_select
                ).classes('w-80').props('outlined dense')
                ui.button(icon='refresh').style(
                    f'background: {C["surface_high"]}; border: 1px solid rgba(255,255,255,0.1); '
                    f'border-radius: 8px; padding: 10px;'
                ).on_click(self._load_replay_list)

        with ui.row().classes('w-full gap-6'):
            self.analysis_container = ui.column().classes('flex-1')
            with self.analysis_container:
                with ui.column().classes('w-full items-center justify-center').style('padding: 80px 0;'):
                    ui.icon('analytics', size='64px').style(f'color: {C["text_dim"]}; opacity: 0.3;')
                    ui.label('Selecione um replay para analisar').style(
                        f'font-size: 14px; color: {C["text_dim"]}; margin-top: 12px;'
                    )

            self._build_analysis_chat()

        self._load_replay_list()

    def _build_analysis_chat(self) -> None:
        with ui.card().classes('w-96').style(
            glass('padding: 0; overflow: hidden; display: flex; flex-direction: column; height: 560px;')
        ):
            with ui.row().classes('w-full items-center justify-between').style(
                f'padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.02);'
            ):
                with ui.row().classes('items-center gap-3'):
                    ui.html(
                        f'<div style="width:8px; height:8px; border-radius:50%; background:{C["tertiary"]};"></div>'
                    )
                    ui.label('AI COACH').style(f'font-size: 14px; font-weight: 700;')

            self.analysis_chat = ui.column().classes('w-full').style(
                f'padding: 16px; flex: 1 1 0; overflow-y: auto; min-height: 0;'
            )
            with self.analysis_chat:
                self._chat_msg('ai', 'Selecione um replay para receber uma análise detalhada da IA.', container=self.analysis_chat)

            with ui.row().classes('w-full items-center gap-2').style(
                f'padding: 16px; border-top: 1px solid rgba(255,255,255,0.05);'
            ):
                self.analysis_input = ui.input(placeholder='Pergunte sobre sua gameplay...').classes('flex-1').props('borderless dense')
                ui.button(icon='send').style(f'color: {C["primary"]};').on_click(self._send_analysis_chat)

    def _send_analysis_chat(self) -> None:
        msg = self.analysis_input.value
        if not msg:
            return
        self.analysis_input.value = ''
        self._chat_msg('user', msg, container=self.analysis_chat)

        if self.ai_coach:
            response = self.ai_coach.chat(msg)
            self._chat_msg('ai', response or 'Erro ao processar mensagem.', container=self.analysis_chat)
        else:
            self._chat_msg('ai', 'AI Coach não disponível. Configure <b>nvidia_api_key</b> no config.json.', container=self.analysis_chat)

    def _load_replay_list(self) -> None:
        replay_folder = self.config.get('replay_folder', os.path.join(
            os.path.expanduser('~'), 'Documents', 'My Games', 'Rocket League', 'TAGame', 'Demos'
        ))
        if not os.path.exists(replay_folder):
            return

        replay_files = sorted(
            [f for f in os.listdir(replay_folder) if f.endswith('.replay')],
            key=lambda x: os.path.getmtime(os.path.join(replay_folder, x)),
            reverse=True
        )

        options = {}
        for f in replay_files[:20]:
            mtime = os.path.getmtime(os.path.join(replay_folder, f))
            date_str = datetime.fromtimestamp(mtime).strftime('%d/%m %H:%M')
            options[f] = f'{date_str} - {f[:30]}'

        if options:
            self.replay_select.options = options
            self.replay_select.value = list(options.keys())[0]
            self.replay_select.update()

    def _on_replay_select(self, e) -> None:
        if not e.value:
            return
        replay_folder = self.config.get('replay_folder', os.path.join(
            os.path.expanduser('~'), 'Documents', 'My Games', 'Rocket League', 'TAGame', 'Demos'
        ))
        replay_path = os.path.join(replay_folder, e.value)
        self._analyze_replay(replay_path)

    def _analyze_replay(self, replay_path: str) -> None:
        from bot.local_analyzer import LocalReplayAnalyzer, HAS_SUBTR

        self.analysis_container.clear()
        if not HAS_SUBTR:
            with self.analysis_container:
                with ui.column().classes('w-full items-center justify-center').style('padding: 60px 0;'):
                    ui.icon('error', size='48px').style(f'color: {C["error"]};')
                    ui.label('subtr-actor não instalado').style(f'font-size: 16px; color: {C["error"]}; margin-top: 8px;')
                    ui.label('Execute: pip install subtr-actor-py').style(f'font-size: 12px; color: {C["text_dim"]};')
            return

        with self.analysis_container:
            ui.spinner(size='40px').style(f'color: {C["primary"]};')
            ui.label('Analisando replay...').style(f'color: {C["text_var"]}; margin-top: 8px;')

        try:
            analyzer = LocalReplayAnalyzer(self.config.get('player_name', ''))
            result = analyzer.analyze_replay(replay_path)
            self.analysis_container.clear()

            if result:
                self._show_analysis_results(result)
                if self.ai_coach:
                    self._add_ai_analysis_card(result)
            else:
                with self.analysis_container:
                    ui.icon('warning', size='48px').style(f'color: {C["warning"]};')
                    ui.label('Replay não analisado').style(f'color: {C["warning"]}; margin-top: 8px;')
        except Exception as ex:
            self.analysis_container.clear()
            with self.analysis_container:
                ui.icon('error', size='48px').style(f'color: {C["error"]};')
                ui.label(str(ex)).style(f'color: {C["error"]}; margin-top: 8px; font-size: 12px;')

    def _show_analysis_results(self, result: Dict[str, Any]) -> None:
        goals = result.get('goals', 0)
        assists = result.get('assists', 0)
        saves = result.get('saves', 0)
        shots = result.get('shots', 0)
        map_name = result.get('map_name', '?')
        game_mode = result.get('game_mode', '?')
        team_zero = result.get('team_zero_score', 0)
        team_one = result.get('team_one_score', 0)
        duration = result.get('duration_seconds', 0)
        player_name = result.get('player_name', self.config.get('player_name', 'You'))
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near = result.get('time_near_ball_pct', 0)
        time_off = result.get('time_offensive_pct', 0)
        boost_collected = result.get('boost_collected', 0)
        boost_used = result.get('boost_used', 0)
        demos = result.get('demos_inflicted', 0)

        won = team_zero > team_one
        score_str = f'{team_zero} - {team_one}'
        dur_min = int(duration // 60)
        dur_sec = int(duration % 60)

        movement_score = max(0, min(100, int(100 - (avg_dist - 500) / 15))) if avg_dist > 0 else 50
        aerial_score = max(0, min(100, int(boost_collected / 50))) if boost_collected > 0 else 30
        positioning_score = max(0, min(100, 100 - abs(time_off - 50) * 2))
        boost_eff = (boost_used / boost_collected * 100) if boost_collected > 0 else 0
        boost_score = max(0, min(100, int(boost_eff * 1.1)))
        shooting_score = int((goals / shots * 100)) if shots > 0 else 0

        comparison = self._get_analysis_comparison(result)
        overall_score = comparison.get('score', 0) if comparison else 0
        tips = self._generate_analysis_tips(result)

        with self.analysis_container:
            # Result header
            with ui.card().classes('w-full fade-in').style(glass('padding: 20px 24px;')):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-6'):
                        with ui.column().classes('items-center gap-2'):
                            ui.label('WIN' if won else 'LOSS').style(
                                label_caps(f'color: {C["tertiary"] if won else C["error"]}; '
                                           f'background: {(C["tertiary"] if won else C["error"])}20; '
                                           f'padding: 4px 14px; border-radius: 20px;')
                            )
                            ui.label(score_str).style(
                                f'font-size: 36px; font-weight: 900; color: {C["text"]}; line-height: 1;'
                            )

                        ui.html(f'<div style="width:1px; height:56px; background:rgba(255,255,255,0.1);"></div>')

                        for lbl, val in [('Game Mode', game_mode), ('Map', map_name)]:
                            with ui.column().classes('gap-1'):
                                ui.label(lbl.upper()).style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))
                                ui.label(val).style(stat_mono(f'font-size: 18px; font-weight: 600; color: {C["text"]};'))

                    with ui.column().classes('items-center gap-2'):
                        ui.label('OVERALL SCORE').style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))
                        ui.label(f'{overall_score:.0f}/100').style(
                            f'padding: 8px 20px; border-radius: 24px; font-size: 18px; font-weight: 700; '
                            f'background: rgba(173,198,255,0.15); border: 1px solid rgba(173,198,255,0.3); '
                            f'color: {C["primary"]};'
                        )

            ui.space().style('height: 16px;')

            # Skill gauges
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.1s;')):
                ui.label('PERFORMANCE BREAKDOWN').style(label_caps(f'color: {C["text_var"]}; margin-bottom: 24px;'))
                with ui.row().classes('w-full justify-between items-center px-4'):
                    gauges = [
                        (movement_score, 'Movement', C['primary']),
                        (aerial_score, 'Aerial', C['secondary']),
                        (positioning_score, 'Positioning', C['tertiary']),
                        (boost_score, 'Boost', C['error']),
                        (shooting_score, 'Shooting', '#acedff'),
                    ]
                    for value, label, color in gauges:
                        self._build_ring_gauge(value, label, color)

            ui.space().style('height: 16px;')

            # Two columns: stats + heatmap
            with ui.row().classes('w-full gap-6'):
                with ui.column().classes('flex-1 gap-4'):
                    self._build_boost_card_analysis(boost_collected, boost_used, boost_eff)
                    self._build_shooting_card_analysis(goals, shots)
                    self._build_positioning_card_analysis(avg_dist, time_off)

                with ui.column().classes('flex-1'):
                    self._build_heatmap_card(result.get('positions_sample', []))

            ui.space().style('height: 16px;')

            # Tips
            if tips:
                self._build_tips_analysis(tips)

    def _build_ring_gauge(self, value: int, label: str, color: str) -> None:
        circumference = 2 * math.pi * 36
        offset = circumference * (1 - value / 100)
        with ui.column().classes('items-center gap-3'):
            ui.html(
                f'<div style="position:relative; width:88px; height:88px;">'
                f'<svg class="ring-chart" viewBox="0 0 100 100" style="width:88px; height:88px;">'
                f'<circle class="ring-bg" cx="50" cy="50" r="36" stroke-width="8"/>'
                f'<circle class="ring-progress" cx="50" cy="50" r="36" stroke="{color}" '
                f'stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}" stroke-width="8"/>'
                f'</svg>'
                f'<div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; '
                f'font-family:JetBrains Mono; font-size:18px; font-weight:600; color:{color};">{value}</div>'
                f'</div>'
            )
            ui.label(label.upper()).style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))

    def _build_boost_card_analysis(self, collected: float, used: float, efficiency: float) -> None:
        with ui.card().classes('w-full fade-in').style(glass('padding: 16px 20px; animation-delay: 0.2s;')):
            with ui.row().classes('items-center gap-3'):
                ui.icon('bolt', size='18px').style(f'color: {C["primary"]};')
                ui.label('BOOST').style(f'font-size: 16px; font-weight: 700;')

            ui.separator().style(f'background: rgba(255,255,255,0.05); margin: 12px 0;')

            for lbl, val in [('Collected', f'{collected:.0f}'), ('Efficiency', f'{efficiency:.0f}%')]:
                with ui.row().classes('w-full justify-between').style('margin-bottom: 8px;'):
                    ui.label(lbl).style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))
                    ui.label(val).style(stat_mono(f'font-size: 18px; font-weight: 600; color: {C["text"]};'))

    def _build_shooting_card_analysis(self, goals: int, shots: int) -> None:
        pct = (goals / shots * 100) if shots > 0 else 0
        with ui.card().classes('w-full fade-in').style(glass('padding: 16px 20px; animation-delay: 0.25s;')):
            with ui.row().classes('items-center gap-3'):
                ui.icon('sports_soccer', size='18px').style(f'color: {C["primary"]};')
                ui.label('SHOOTING').style(f'font-size: 16px; font-weight: 700;')

            ui.separator().style(f'background: rgba(255,255,255,0.05); margin: 12px 0;')

            with ui.row().classes('w-full justify-between gap-4'):
                for lbl, val in [('Goals', str(goals)), ('Shots', str(shots)), ('Conversion', f'{pct:.0f}%')]:
                    with ui.column().classes('gap-1'):
                        ui.label(lbl.upper()).style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))
                        ui.label(val).style(stat_mono(f'font-size: 18px; font-weight: 600; color: {C["text"]};'))

    def _build_positioning_card_analysis(self, avg_dist: float, time_off: float) -> None:
        offensive = min(100, max(0, time_off))
        neutral = max(0, 100 - offensive) * 0.55
        defensive = 100 - offensive - neutral

        with ui.card().classes('w-full fade-in').style(glass('padding: 16px 20px; animation-delay: 0.3s;')):
            with ui.row().classes('items-center gap-3'):
                ui.icon('place', size='18px').style(f'color: {C["primary"]};')
                ui.label('POSITIONING').style(f'font-size: 16px; font-weight: 700;')

            ui.separator().style(f'background: rgba(255,255,255,0.05); margin: 12px 0;')

            with ui.row().classes('w-full justify-between').style('margin-bottom: 12px;'):
                ui.label('Avg Distance').style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))
                ui.label(f'{avg_dist:.0f}m').style(stat_mono(f'font-size: 18px; font-weight: 600; color: {C["text"]};'))

            ui.label('Zone Distribution').style(label_caps(f'font-size: 10px; color: {C["text_var"]}; margin-bottom: 8px;'))

            with ui.row().classes('w-full').style('height: 12px; border-radius: 6px; overflow: hidden; background: rgba(255,255,255,0.05);'):
                ui.html(
                    f'<div style="display:flex; width:100%; height:100%;">'
                    f'<div style="width:{defensive}%; background:{C["error_cont"]};"></div>'
                    f'<div style="width:{neutral}%; background:{C["surface_variant"]};"></div>'
                    f'<div style="width:{offensive}%; background:{C["tertiary_cont"]};"></div>'
                    f'</div>'
                )

            with ui.row().classes('w-full justify-between').style('margin-top: 8px;'):
                for lbl, val in [('DEF', defensive), ('NEU', neutral), ('OFF', offensive)]:
                    ui.label(f'{lbl} {val:.0f}%').style(label_caps(f'font-size: 9px; color: {C["text_var"]};'))

    def _build_heatmap_card(self, positions: list) -> None:
        with ui.card().classes('w-full fade-in').style(glass('padding: 16px 20px; animation-delay: 0.35s;')):
            ui.label('POSITION HEATMAP').style(label_caps(f'color: {C["text_var"]}; margin-bottom: 12px;'))

            if not positions or len(positions) < 3:
                with ui.column().classes('w-full items-center justify-center').style('height: 200px;'):
                    ui.icon('place', size='32px').style(f'color: {C["text_dim"]}; opacity: 0.3;')
                    ui.label('Sem dados de posição').style(f'font-size: 12px; color: {C["text_dim"]};')
                return

            pts = [[int(p[0]), int(p[1])] for p in positions]
            option = {
                'backgroundColor': '#0e2a1e',
                'grid': {'left': 0, 'top': 0, 'right': 0, 'bottom': 0},
                'xAxis': {'show': False, 'min': -4200, 'max': 4200, 'type': 'value'},
                'yAxis': {'show': False, 'min': -5100, 'max': 5100, 'type': 'value'},
                'series': [{
                    'type': 'scatter', 'data': pts,
                    'itemStyle': {'color': 'rgba(59,130,246,0.7)', 'shadowBlur': 8, 'shadowColor': 'rgba(59,130,246,0.3)'},
                    'symbolSize': 10,
                    'markLine': {
                        'silent': True, 'symbol': 'none',
                        'lineStyle': {'color': 'rgba(255,255,255,0.15)', 'type': 'solid', 'width': 1},
                        'data': [[{'xAxis': 0, 'yAxis': -5100}, {'xAxis': 0, 'yAxis': 5100}]],
                        'label': {'show': False}
                    }
                }]
            }

            ui.echart(option).style(
                f'width: 100%; height: 200px; border-radius: 12px; '
                f'border: 1px solid rgba(255,255,255,0.05);'
            )

    def _build_tips_analysis(self, tips: list) -> None:
        with ui.card().classes('w-full fade-in').style(
            glass('padding: 20px; border-left: 4px solid rgba(173,198,255,0.5); animation-delay: 0.4s;')
        ):
            with ui.row().classes('items-center gap-3').style('margin-bottom: 16px;'):
                ui.icon('psychology', size='20px').style(f'color: {C["primary"]};')
                ui.label('AI COACH ANALYSIS').style(
                    f'font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;'
                )

            for tip in tips[:3]:
                with ui.row().classes('items-start gap-3').style('margin-bottom: 12px;'):
                    ui.icon('check_circle', size='16px').style(f'color: {C["tertiary"]}; margin-top: 2px;')
                    ui.label(tip).style(f'font-size: 13px; color: {C["text_var"]}; line-height: 1.5;')

    def _add_ai_analysis_card(self, result: Dict[str, Any]) -> None:
        if not self.ai_coach:
            return
        pro_name = self.config.get('pro_to_study', 'Zen')
        playlist = result.get('playlist', 'ranked-doubles')
        baseline_data = self.db.get_baseline(playlist, pro_name)
        baseline = baseline_data.get('averages', {}) if baseline_data else None

        response = self.ai_coach.analyze_replay(result, baseline, pro_name)
        if response:
            with self.analysis_container:
                ui.space().style('height: 16px;')
                self._build_tips_analysis([response])

    def _get_analysis_comparison(self, result: Dict) -> Optional[Dict]:
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
                'boost_avg': result.get('boost_collected', 0) / 100,
                'avg_distance_to_ball': result.get('avg_distance_to_ball', 0),
                'goals': result.get('goals', 0),
                'assists': result.get('assists', 0),
                'saves': result.get('saves', 0),
                'shooting_pct': (result.get('goals', 0) / max(1, result.get('shots', 1)) * 100),
            }
            return self.comparer.compare(player_stats, baseline)
        except Exception:
            return None

    def _generate_analysis_tips(self, result: Dict) -> list:
        tips = []
        avg_dist = result.get('avg_distance_to_ball', 0)
        time_near = result.get('time_near_ball_pct', 0)
        time_off = result.get('time_offensive_pct', 0)
        goals = result.get('goals', 0)
        shots = result.get('shots', 0)
        saves = result.get('saves', 0)

        if avg_dist > 1500:
            tips.append(f'Muito longe da bola (distância: {avg_dist:.0f}). Fique mais perto para ter mais contato.')
        if time_near < 30:
            tips.append(f'Apenas {time_near:.1f}% do tempo perto da bola. Pressione mais.')
        if time_off > 60:
            tips.append(f'Bom tempo no ataque ({time_off:.1f}%). Continue pressionando!')
        if shots > 0 and goals == 0:
            tips.append(f'{shots} chutes, 0 gols. Pratique a finalização.')
        if saves > 2:
            tips.append(f'Boa defesa! {saves} defesas. Continue protegendo o gol.')
        if not tips:
            tips.append('Continue jogando para receber dicas mais detalhadas!')
        return tips

    # ════════════════════════════════════════════════════════════════════════
    # MATCH HISTORY PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_match_history_page(self) -> None:
        self._build_top_bar('Match History', 'Todas as partidas jogadas')

        # Filter tabs
        with ui.row().classes('items-center').style(
            f'background: {C["surface_low"]}; padding: 4px; border-radius: 12px; '
            f'border: 1px solid rgba(255,255,255,0.05); margin-bottom: 24px; width: fit-content;'
        ):
            for label in ['All', '1v1', '2v2', '3v3']:
                is_active = label == 'All'
                ui.button(label).style(
                    f'padding: 8px 24px; border-radius: 8px; font-size: 12px; font-weight: 700; '
                    f'{"background: " + C["primary"] + "; color: " + C["on_primary"] + ";" if is_active else "background: transparent; color: " + C["text_var"] + ";"}'
                    f'border: none; text-transform: none;'
                ).props('flat')

        matches = self.db.get_matches(limit=50)
        if not matches:
            with ui.column().classes('w-full items-center justify-center').style('padding: 80px 0;'):
                ui.icon('inbox', size='64px').style(f'color: {C["text_dim"]}; opacity: 0.3;')
                ui.label('Nenhuma partida registrada').style(f'font-size: 16px; color: {C["text_dim"]}; margin-top: 12px;')
                ui.label('Jogue algumas partidas para ver seus resultados aqui.').style(
                    f'font-size: 13px; color: {C["text_dim"]};'
                )
            return

        with ui.column().classes('w-full gap-3'):
            for match in matches:
                self._build_history_card(match)

    def _build_history_card(self, match: dict) -> None:
        result = match.get('result', '')
        is_win = result == 'win'
        border_class = 'win-border' if is_win else 'loss-border'
        result_color = C['success'] if is_win else C['error']
        result_letter = 'W' if is_win else 'L'

        with ui.card().classes(f'w-full {border_class}').style(
            glass('padding: 16px 20px;')
        ):
            with ui.row().classes('w-full items-center gap-6'):
                ui.html(
                    f'<div style="width:56px; height:56px; border-radius:50%; '
                    f'border: 2px solid {result_color}50; background: {result_color}10; '
                    f'display:flex; align-items:center; justify-content:center; '
                    f'font-size: 20px; font-weight:900; color: {result_color}; flex-shrink:0;">'
                    f'{result_letter}</div>'
                )

                with ui.column().classes('flex-1 gap-1'):
                    ui.label(match.get('playlist', '2v2 Ranked')).style(
                        f'font-size: 16px; font-weight: 700; color: {C["text"]};'
                    )
                    with ui.row().classes('items-center gap-4'):
                        ui.label(str(match.get('date', ''))[:10]).style(
                            f'font-size: 12px; color: {C["text_var"]};'
                        )
                        ui.label('•').style(f'color: {C["text_dim"]};')
                        ui.label(match.get('playlist', 'N/A')).style(
                            f'font-size: 12px; color: {C["text_var"]};'
                        )

                goals = match.get('goals', 0)
                assists = match.get('assists', 0)
                saves = match.get('saves', 0)
                score = match.get('score', 0)

                with ui.column().classes('items-center gap-1'):
                    ui.label(str(score)).style(stat_mono(f'font-size: 20px; font-weight: 700; color: {C["primary"]};'))
                    ui.label('SCORE').style(label_caps(f'font-size: 9px; color: {C["text_dim"]};'))

                with ui.row().classes('items-center gap-4'):
                    for val, lbl in [(goals, 'G'), (assists, 'A'), (saves, 'S')]:
                        with ui.column().classes('items-center gap-0'):
                            ui.label(str(val)).style(stat_mono(f'font-size: 16px; font-weight: 700;'))
                            ui.label(lbl).style(label_caps(f'font-size: 9px; color: {C["text_dim"]};'))

                prox = match.get('proximity_score', 0) or 0
                ui.html(
                    f'<div style="padding: 8px 14px; border-radius: 20px; '
                    f'background: rgba(76,215,246,0.1); border: 1px solid rgba(76,215,246,0.3); '
                    f'display: flex; flex-direction: column; align-items: center;">'
                    f'<span style="font-size: 9px; color: {C["tertiary"]}; font-weight: 700; text-transform: uppercase;">PROX</span>'
                    f'<span style="font-size: 16px; font-weight: 700; color: {C["tertiary"]};">{prox:.0f}%</span>'
                    f'</div>'
                )

    # ════════════════════════════════════════════════════════════════════════
    # SETTINGS PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_settings_page(self) -> None:
        self._build_top_bar('Settings', 'Preferências do aplicativo')

        with ui.column().classes('w-96 gap-6'):
            # Monitoring
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px;')):
                ui.label('Monitoring').style(f'font-size: 16px; font-weight: 700; margin-bottom: 16px;')

                self.sw_monitor = ui.switch(
                    'Monitoramento Automático',
                    value=self.config.get('auto_start_watcher', True)
                ).style(f'margin-bottom: 12px;')

                self.sw_upload = ui.switch(
                    'Auto-Upload para Ballchasing',
                    value=self.config.get('auto_upload', False)
                ).style(f'margin-bottom: 12px;')

                self.sw_notif = ui.switch(
                    'Notificações',
                    value=self.config.get('notifications', False)
                )

            # AI Coach
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.1s;')):
                ui.label('AI Coach').style(f'font-size: 16px; font-weight: 700; margin-bottom: 16px;')

                api_key = self.config.get('nvidia_api_key', '')
                if api_key:
                    ui.label(f'✓ Connected ({api_key[:12]}...)').style(
                        f'font-size: 13px; color: {C["tertiary"]}; margin-bottom: 8px;'
                    )
                else:
                    ui.label('✗ Not configured').style(
                        f'font-size: 13px; color: {C["error"]}; margin-bottom: 8px;'
                    )

                ui.label('Model: nvidia/llama-3.3-nemotron-super-49b-v1').style(
                    f'font-size: 11px; color: {C["text_dim"]};'
                )

            # Save
            ui.button('Salvar Configurações').style(
                f'background: {C["primary_container"]}; color: {C["on_primary"]}; '
                f'border-radius: 16px; padding: 14px 24px; font-weight: 700; '
                f'width: 100%; text-transform: none;'
            ).on_click(self._save_settings)

    def _save_settings(self) -> None:
        self.config['auto_start_watcher'] = self.sw_monitor.value
        self.config['auto_upload'] = self.sw_upload.value
        self.config['notifications'] = self.sw_notif.value

        config_path = Path('config.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            data['auto_start_watcher'] = self.sw_monitor.value
            data['auto_upload'] = self.sw_upload.value
            data['notifications'] = self.sw_notif.value
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

        ui.notification('Configurações salvas!', type='positive', color=C['tertiary'])

    # ════════════════════════════════════════════════════════════════════════
    # SVG HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _svg_ring(self, pct: int, size: int, color: str) -> str:
        r = size // 2 - 6
        c = 2 * math.pi * r
        offset = c * (1 - pct / 100)
        return (
            f'<div style="position:relative; width:{size}px; height:{size}px;">'
            f'<svg class="ring-chart" viewBox="0 0 100 100" style="width:{size}px; height:{size}px;">'
            f'<circle class="ring-bg" cx="50" cy="50" r="{r}" stroke-width="6"/>'
            f'<circle class="ring-progress" cx="50" cy="50" r="{r}" stroke="{color}" '
            f'stroke-dasharray="{c:.1f}" stroke-dashoffset="{offset:.1f}" stroke-width="6"/>'
            f'</svg>'
            f'<div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center;">'
            f'<span class="material-symbols-outlined" style="color:{color};">trending_up</span>'
            f'</div>'
            f'</div>'
        )

    def _svg_large_ring(self, pct: int, size: int, color: str) -> str:
        r = size // 2 - 8
        c = 2 * math.pi * r
        offset = c * (1 - pct / 100)
        return (
            f'<div style="position:relative; width:{size}px; height:{size}px;">'
            f'<svg class="ring-chart" viewBox="0 0 100 100" style="width:{size}px; height:{size}px;">'
            f'<circle class="ring-bg" cx="50" cy="50" r="{r}" stroke-width="3"/>'
            f'<circle class="ring-progress" cx="50" cy="50" r="{r}" stroke="{color}" '
            f'stroke-dasharray="{c:.1f}" stroke-dashoffset="{offset:.1f}" stroke-width="3" '
            f'style="filter: drop-shadow(0 0 15px {color}99);"/>'
            f'</svg>'
            f'<div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center;">'
            f'<span style="font-size: 48px; font-weight: 900; color: {color}; line-height: 1;">{pct}%</span>'
            f'<span style="font-size: 11px; letter-spacing: 0.1em; font-weight: 600; color: {C["text_var"]}; text-transform: uppercase; margin-top: 4px;">SIMILAR TO ZEN</span>'
            f'</div>'
            f'</div>'
        )

    # ════════════════════════════════════════════════════════════════════════
    # DATA REFRESH
    # ════════════════════════════════════════════════════════════════════════

    def _refresh_data(self) -> None:
        if self.current_page != 0:
            return
        try:
            matches = self.db.get_matches(limit=10)
            today = self.db.get_today_matches()
            if matches:
                latest = matches[0]
                # Update timeline
                self._update_timeline(matches)
        except Exception:
            pass

    def update_status(self, is_monitoring: bool) -> None:
        pass

    def refresh(self) -> None:
        self._refresh_data()
