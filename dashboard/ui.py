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
from bot.ai_coach import AICoach

from bot.rank_fetcher import fetch_current_rank
from discord_auth import start_oauth_flow, DISCORD_CLIENT_ID
from license import validate_license


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

def _tier_color(tier: str) -> str:
    """Retorna cor do tier de rank."""
    colors = {
        'bronze': '#cd7f32',
        'silver': '#c0c0c0',
        'gold': '#ffd700',
        'platinum': '#00d4aa',
        'diamond': '#adc6ff',
        'champion': '#d0bcff',
        'grand_champion': '#ff7eb3',
        'supersonic_legend': '#ffd700',
    }
    return colors.get(tier, C['text_var'])

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
        ('emoji_events',    'Pro Comparison'),
        ('person',          'Profile'),
    ]

    def __init__(self, db: Database, config: dict,
                 comparer=None,
                 ai_coach: Optional[AICoach] = None):
        self.db = db
        self.config = config
        self.ai_coach = ai_coach
        self.current_page = 0
        self.nav_buttons: list = []
        self.main_area = None
        self._current_player_name = config.get('rl_nickname', config.get('player_name', ''))

    # ── BUILD ───────────────────────────────────────────────────────────────

    def build(self) -> None:
        ui.dark_mode(True)
        ui.add_head_html(self._global_css())

        # Checar se usuario esta autenticado com licenca valida
        saved_id = self.config.get('discord_id', '')
        if saved_id:
            is_valid, message, expires = validate_license(saved_id)
            if is_valid:
                self.discord_id = saved_id
                self._build_dashboard()
                return

        # Sem licenca valida — mostrar tela de login (lock screen)
        self._build_login_page()

    # ── LOGIN PAGE (LOCK SCREEN) ─────────────────────────────────────────

    def _build_login_page(self) -> None:
        """Tela de login full-screen com design premium (baseado no design do usuario)."""
        self.login_container = ui.column().classes(
            'w-full h-screen items-center justify-center overflow-hidden'
        ).style('position: relative;')

        with self.login_container:
            # ── Ambient Background Layer ──
            ui.html(
                '<div style="position: fixed; inset: 0; z-index: 0; pointer-events: none;">'
                '<div class="floating-element" style="position: absolute; top: 10%; left: 15%; '
                'width: 384px; height: 384px; background: rgba(173,198,255,0.1); '
                'border-radius: 50%; filter: blur(120px);"></div>'
                '<div class="floating-element" style="position: absolute; bottom: 10%; right: 10%; '
                'width: 500px; height: 500px; background: rgba(76,215,246,0.05); '
                'border-radius: 50%; filter: blur(150px); animation-delay: -5s;"></div>'
                '</div>'
            )

            # ── Glass Card ──
            card = ui.card().classes('login-card-tilt fade-in').style(
                'background: rgba(22,24,34,0.8); backdrop-filter: blur(12px); '
                'border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; '
                'padding: 40px; max-width: 480px; width: 100%; '
                'box-shadow: 0 0 40px rgba(173,198,255,0.05); position: relative; z-index: 10;'
            )

            with card:
                # ── Brand Identity ──
                with ui.column().classes('w-full items-center text-center mb-8'):
                    # Logo image
                    ui.html(
                        '<img alt="RLBot Pro Logo" '
                        'style="width: 96px; height: 96px; margin-bottom: 24px; '
                        'filter: drop-shadow(0 0 15px rgba(173,198,255,0.4));" '
                        'src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0EH4k1N04noAeKM__GcoIBzz_YlZTPpi-5FOtj_x1dfm-Fn6OYDdYiUZH3MYRfgA_K5xoSdU_7h0_1HasPdENYRQ2XVDKbELvAOsOOAX8JTNfXP7_1KYmO7FbX_n8wIUiUTEnC86ob-hkoU2MdJshkwydK0b5lEVqRdyWOT0uBGC59-Rxe0Z90ImPaE-fwASX9VIV34PAsIAhHIVbow2UrlRH3WcFn_3CNwVEZs3LNzXOYzRvjBMHUztW1ZyOjO00CA">'
                    )
                    # Title
                    ui.html(
                        '<h1 style="font-size: 48px; font-weight: 900; color: #adc6ff; '
                        'margin: 0; line-height: 1.1; letter-spacing: -0.04em;">RLBot Pro</h1>'
                    )
                    # Subtitle
                    ui.html(
                        '<p style="font-size: 16px; line-height: 1.6; color: #c2c6d6; '
                        'margin-top: 8px;">Seu coach de Rocket League com IA</p>'
                    )

                # ── Discord Button ──
                if DISCORD_CLIENT_ID:
                    self.login_discord_btn = ui.button(
                        icon='login',
                        text='Login com Discord',
                        on_click=self._on_login_discord
                    ).classes('discord-btn w-full').style(
                        'padding: 16px 24px; border-radius: 12px; '
                        'color: white; font-size: 16px; font-weight: 700; '
                        'text-transform: none; min-height: 56px;'
                    )
                else:
                    ui.html(
                        '<p style="font-size: 12px; color: #ffb4ab; margin-bottom: 8px; '
                        'text-align: center;">'
                        'OAuth2 nao configurado. Edite o .env com DISCORD_CLIENT_ID.</p>'
                    )

                # ── Divider ──
                ui.html(
                    '<div style="display: flex; align-items: center; gap: 16px; '
                    'padding: 8px 0;">'
                    '<div style="height: 1px; flex: 1; background: rgba(66,71,84,0.3);"></div>'
                    '<span style="font-size: 12px; line-height: 1; letter-spacing: 0.1em; '
                    'font-weight: 600; text-transform: uppercase; color: #c2c6d6;">'
                    'Ou manualmente</span>'
                    '<div style="height: 1px; flex: 1; background: rgba(66,71,84,0.3);"></div>'
                    '</div>'
                )

                # ── Manual ID Input ──
                with ui.column().classes('w-full gap-3'):
                    ui.html(
                        '<label style="font-size: 12px; line-height: 1; letter-spacing: 0.1em; '
                        'font-weight: 600; text-transform: uppercase; color: #c2c6d6; '
                        'margin-left: 4px;">Discord ID</label>'
                    )

                    with ui.row().classes('w-full items-center'):
                        self.login_manual_input = ui.input(
                            placeholder='Ex: 974351584538550282'
                        ).classes('manual-input-field flex-1').props('borderless dense')
                        self.login_manual_btn = ui.button(
                            icon='arrow_forward',
                            on_click=self._on_login_manual
                        ).style(
                            f'background: rgba(173,198,255,0.1); color: {C["primary"]}; '
                            f'border-radius: 10px; padding: 12px; margin-left: 8px; '
                            f'min-width: 48px; min-height: 48px; '
                            f'transition: all 0.2s ease;'
                        )

                # ── Status ──
                self.login_status = ui.html('').style('margin-top: 16px; text-align: center;')

            # ── Help Section ──
            ui.html(
                '<div style="margin-top: 32px; width: 100%; border-top: 1px solid rgba(66,71,84,0.2); '
                'padding-top: 24px;">'
                '<details style="cursor: pointer;" id="login-help-details">'
                '<summary style="display: flex; align-items: center; justify-content: space-between; '
                'list-style: none; color: #c2c6d6; transition: color 0.2s;" '
                'onmouseover="this.style.color=\'#adc6ff\'" '
                'onmouseout="this.style.color=\'#c2c6d6\'">'
                '<div style="display: flex; align-items: center; gap: 8px;">'
                '<span class="material-symbols-outlined" style="font-size: 20px;">help_outline</span>'
                '<span style="font-size: 12px; line-height: 1; letter-spacing: 0.1em; '
                'font-weight: 600; text-transform: uppercase;">Como obter meu Discord ID?</span>'
                '</div>'
                '<span class="material-symbols-outlined" style="transition: transform 0.2s;">'
                'expand_more</span>'
                '</summary>'
                '<div style="margin-top: 16px; padding: 16px; border-radius: 12px; '
                'background: rgba(29,32,39,0.5); font-size: 13px; line-height: 1.6; '
                'color: #c2c6d6;">'
                'Abra o Discord, va em <strong style="color: #e1e2ec;">'
                'Configuracoes &gt; Avancado</strong> e ative o '
                '<strong style="color: #e1e2ec;">Modo Desenvolvedor</strong>. '
                'Depois, clique com o botao direito no seu perfil e '
                'selecione "Copiar ID do Usuario".'
                '</div>'
                '</details>'
                '</div>'
            )

            # ── Mouse Tilt Effect (JS) ──
            ui.run_javascript('''
                const card = document.querySelector('.login-card-tilt');
                if (card) {
                    card.addEventListener('mousemove', (e) => {
                        const rect = card.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        const centerX = rect.width / 2;
                        const centerY = rect.height / 2;
                        const rotateX = (y - centerY) / 50;
                        const rotateY = -(x - centerX) / 50;
                        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
                    });
                    card.addEventListener('mouseleave', () => {
                        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
                    });
                }
            ''')

    def _on_login_discord(self) -> None:
        """Inicia OAuth2 → valida licença → salva ID → mostra dashboard."""
        self.login_discord_btn.disable()
        self.login_status.content = f'<p style="font-size: 13px; color: {C["text_var"]}; text-align: center;">Abrindo navegador do Discord...</p>'

        def do_login():
            from nicegui import app as ng_app
            try:
                result = start_oauth_flow(timeout=120)

                if result:
                    discord_id = result['discord_id']
                    username = result.get('global_name') or result.get('username', '')

                    # Atualizar status durante validacao
                    ng_app.schedule(lambda: self._login_set_status(
                        f'Olá {username}! Verificando licença...', C['text_var']))

                    # Validar licenca automaticamente
                    is_valid, message, expires = validate_license(discord_id)

                    if is_valid:
                        # Salvar no config
                        self.config['discord_id'] = discord_id
                        self.config['discord_username'] = username
                        config_path = Path('config.json')
                        try:
                            with open(config_path, 'r') as f:
                                data = json.load(f)
                        except (FileNotFoundError, json.JSONDecodeError):
                            data = {}
                        data['discord_id'] = discord_id
                        data['discord_username'] = username
                        with open(config_path, 'w') as f:
                            json.dump(data, f, indent=2)

                        ng_app.schedule(lambda: self._on_login_success(discord_id, message))
                    else:
                        ng_app.schedule(lambda: self._on_login_license_invalid(message))
                else:
                    ng_app.schedule(lambda: self._on_login_failed('Login cancelado ou timeout.'))
            except Exception as e:
                ng_app.schedule(lambda: self._on_login_failed(str(e)))
            finally:
                ng_app.schedule(lambda: self.login_discord_btn.enable())

        import threading
        threading.Thread(target=do_login, daemon=True).start()

    def _on_login_manual(self) -> None:
        """Valida Discord ID colado manualmente."""
        discord_id = self.login_manual_input.value.strip()
        if not discord_id:
            self.login_status.content = f'<p style="font-size: 13px; color: {C["error"]}; text-align: center;">Cole seu Discord ID.</p>'
            return

        self.login_manual_btn.disable()
        self.login_status.content = f'<p style="font-size: 13px; color: {C["text_var"]}; text-align: center;">Verificando licenca...</p>'

        is_valid, message, expires = validate_license(discord_id)

        if is_valid:
            # Salvar no config
            self.config['discord_id'] = discord_id
            config_path = Path('config.json')
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}
            data['discord_id'] = discord_id
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)

            self._on_login_success(discord_id, message)
        else:
            self._on_login_license_invalid(message)

        self.login_manual_btn.enable()

    def _on_login_success(self, discord_id: str, message: str) -> None:
        """Login + licenca OK → recarrega pagina para mostrar dashboard."""
        self.discord_id = discord_id
        # Salvar discord_id no config para que build() detecte na reload
        config_path = Path('config.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            data['discord_id'] = discord_id
            if self.config.get('discord_username'):
                data['discord_username'] = self.config['discord_username']
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
        ui.notification('Login realizado!', type='positive', timeout=2)
        # Recarregar a pagina — build() detectara discord_id e mostrara dashboard
        ui.timer(1.0, lambda: ui.navigate.reload(), once=True)

    def _login_set_status(self, text: str, color: str) -> None:
        """Atualiza texto de status na tela de login."""
        self.login_status.content = f'<p style="font-size: 13px; color: {color}; text-align: center;">{text}</p>'

    def _on_login_license_invalid(self, message: str) -> None:
        """Login feito mas licenca invalida."""
        self.login_status.content = f'<p style="font-size: 13px; color: {C["error"]}; text-align: center;">{message}</p>'
        ui.notification(message, type='negative', timeout=10)

    def _on_login_failed(self, error: str) -> None:
        """Falha no login."""
        short = error[:100]
        self.login_status.content = f'<p style="font-size: 13px; color: {C["error"]}; text-align: center;">Erro: {short}</p>'
        ui.notification(f'Erro no login: {error[:80]}', type='negative', timeout=10)

    # ── DASHBOARD (apos login) ─────────────────────────────────────────────

    def _build_dashboard(self) -> None:
        """Constrói o dashboard completo apos login validado."""
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
        self.page_built = [False, False, False, False, False, False]
        with self.main_area:
            for _ in range(6):
                c = ui.column().classes('w-full').style('display: none;')
                self.page_containers.append(c)

        self._show_page(0)

        # Timer de verificacao periodica de licenca (a cada 5 min)
        if not hasattr(self, '_license_timer'):
            self._license_timer = ui.timer(interval=300, callback=self._periodic_license_check)

    def _periodic_license_check(self) -> None:
        """Re-checa a licenca periodicamente. Se expirar/revogar, bloqueia acesso."""
        if not self.discord_id:
            return

        is_valid, message, expires = validate_license(self.discord_id)

        if not is_valid:
            self._show_license_expired_overlay(message)

    def _show_license_expired_overlay(self, message: str) -> None:
        """Overlay que bloqueia todo o dashboard quando licenca expira."""
        if hasattr(self, '_license_overlay') and self._license_overlay:
            return  # Ja esta mostrando

        self._license_overlay = ui.column().classes(
            'w-full h-screen items-center justify-center'
        ).style(
            f'position: fixed; inset: 0; z-index: 9999; '
            f'background: rgba(10,11,15,0.95); backdrop-filter: blur(8px);'
        )

        with self._license_overlay:
            with ui.card().classes('fade-in').style(
                glass('padding: 48px; max-width: 440px; text-align: center;')
            ):
                ui.html(
                    f'<div style="margin-bottom: 24px;">'
                    f'<div style="width: 64px; height: 64px; border-radius: 50%; margin: 0 auto 16px; '
                    f'background: rgba(255,180,171,0.15); border: 2px solid rgba(255,180,171,0.3); '
                    f'display: flex; align-items: center; justify-content: center;">'
                    f'<span style="font-size: 28px;">&#128274;</span>'
                    f'</div>'
                    f'<h2 style="font-size: 22px; font-weight: 700; color: {C["error"]}; margin: 0;">'
                    f'Acesso Bloqueado</h2>'
                    f'</div>'
                )

                ui.label(message).style(
                    f'font-size: 14px; color: {C["text_var"]}; margin-bottom: 24px; '
                    f'text-align: center; line-height: 1.6;'
                )

                def logout_and_restart():
                    # Limpar discord_id do config
                    config_path = Path('config.json')
                    try:
                        with open(config_path, 'r') as f:
                            data = json.load(f)
                        data.pop('discord_id', None)
                        with open(config_path, 'w') as f:
                            json.dump(data, f, indent=2)
                    except Exception:
                        pass
                    self.config.pop('discord_id', None)
                    self.discord_id = None
                    # Recarregar pagina
                    ui.navigate.reload()

                ui.button(
                    icon='logout', text='Fazer login com outra conta',
                    on_click=logout_and_restart
                ).style(
                    f'background: {C["surface_high"]}; color: {C["text"]}; '
                    f'border-radius: 12px; padding: 12px 24px; font-weight: 600; '
                    f'text-transform: none; width: 100%;'
                )

    def _global_css(self) -> str:
        return '''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;600&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

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

            @keyframes float {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                50% { transform: translateY(-20px) rotate(2deg); }
            }
            .floating-element { animation: float 10s ease-in-out infinite; }

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

            .discord-btn {
                background: linear-gradient(135deg, #5865F2 0%, #4752C4 100%);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .discord-btn:hover {
                box-shadow: 0 0 20px rgba(88, 101, 242, 0.4);
                transform: translateY(-1px);
            }
            .discord-btn:active {
                transform: scale(0.98);
            }
            .discord-btn:disabled {
                opacity: 0.6;
                transform: none;
                box-shadow: none;
            }

            .login-card-tilt {
                transform: perspective(1000px) rotateX(0deg) rotateY(0deg);
                transition: transform 0.3s ease;
            }

            .manual-input-field input {
                background: rgba(11,14,21,0.5) !important;
                border: 1px solid rgba(66,71,84,0.5) !important;
                border-radius: 12px !important;
                padding: 16px 20px !important;
                color: #e1e2ec !important;
                font-size: 14px !important;
            }
            .manual-input-field input::placeholder {
                color: rgba(194,198,214,0.4) !important;
            }
            .manual-input-field input:focus {
                box-shadow: 0 0 0 2px rgba(173,198,255,0.2) !important;
                border-color: #adc6ff !important;
            }
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

            # Nav items (Dashboard, Replay, History, Pro Comparison)
            for i, (icon, label) in enumerate(self.NAV_ITEMS[:4]):
                is_active = (i == self.current_page)
                with ui.button(icon=icon).style(nav_item_style(is_active)).props('flat') as btn:
                    ui.tooltip(label).classes('text-xs')
                btn.on_click(lambda e, idx=i: self._on_nav(idx))
                self.nav_buttons.append((btn, i))
                if i == 2:
                    ui.space().style('height: 8px;')

            ui.space()

            # Settings (bottom)
            is_active = (self.current_page == 5)
            with ui.button(icon='settings').style(nav_item_style(is_active)).props('flat') as btn:
                ui.tooltip('Configurações').classes('text-xs')
            btn.on_click(lambda e: self._on_nav(5))
            self.nav_buttons.append((btn, 5))

            ui.space().style('height: 8px;')

            # Profile avatar (clickable -> Profile page)
            with ui.button(icon='account_circle').style(
                f'width: 40px; height: 40px; border-radius: 50%; '
                f'background: {C["surface_cont"]}; color: {C["text_var"]}; '
                f'border: 2px solid rgba(173,198,255,0.3);'
            ).props('flat') as avatar_btn:
                ui.tooltip('Perfil').classes('text-xs')
            avatar_btn.on_click(lambda e: self._on_nav(4))

    def _on_nav(self, index: int) -> None:
        self.current_page = index
        for btn, idx in self.nav_buttons:
            btn.style(nav_item_style(idx == index))
        self._show_page(index)

    def _show_page(self, index: int) -> None:
        for i, c in enumerate(self.page_containers):
            if i == index:
                if not self.page_built[i]:
                    builders = [
                        self._build_dashboard_page,
                        self._build_replay_analysis_page,
                        self._build_match_history_page,
                        self._build_pro_comparison_page,
                        self._build_profile_page,
                        self._build_settings_page,
                    ]
                    with self.page_containers[i]:
                        builders[i]()
                    self.page_built[i] = True
                c.style('display: block;')
            else:
                c.style('display: none;')

    # ════════════════════════════════════════════════════════════════════════
    # DASHBOARD PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_dashboard_page(self) -> None:
        self._build_top_bar('Dashboard', 'Acompanhe suas estatísticas e evolução')
        self._build_streak_warning()
        self._build_hero_stats()
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
                ui.button(icon='notifications', on_click=lambda: ui.notification(
                    'Sem notificacoes novas', type='info', timeout=2
                )).props('flat round').style(f'color: {C["text_var"]};')
                ui.button(icon='folder', on_click=lambda: self._on_nav(1)).props('flat round').style(
                    f'color: {C["text_var"]};'
                )



    # ── HERO STATS GRID ─────────────────────────────────────────────────────

    def _build_hero_stats(self) -> None:
        with ui.row().classes('w-full gap-4'):
            self._build_player_card()
            self._build_session_card()
            self._build_winrate_card()

    def _build_player_card(self) -> None:
        player_display = (
            self.config.get('discord_username', '')
            or self.config.get('player_name', '')
            or self.config.get('discord_id', 'Player')
        )

        # Buscar rank via nickname do Rocket League (digitado nas Settings)
        rl_nickname = self.config.get('rl_nickname', '')
        rank_data = None
        if rl_nickname:
            try:
                rank_data = fetch_current_rank(rl_nickname, "epic", self.db)
            except Exception:
                pass

        # Rank 2v2 (mais jogado) como rank principal
        main_rank = ""
        main_mmr = ""
        is_stale = False
        if rank_data and rank_data.get("success"):
            ranked = rank_data.get("ranked", {})
            primary = ranked.get("2v2") or ranked.get("3v3") or ranked.get("1v1") or {}
            main_rank = primary.get("rank", "").upper() or "UNRANKED"
            main_mmr = str(primary.get("mmr", "")) if primary.get("mmr") else ""
            is_stale = rank_data.get("cached", False)

        stale_indicator = " (desatualizado)" if is_stale else ""
        stale_color = C["text_dim"] if is_stale else C["primary"]

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
                    ui.label(player_display).style(
                        f'font-size: 18px; font-weight: 700; color: {C["text"]}; line-height: 1.2;'
                    )
                    with ui.row().classes('items-center gap-2'):
                        if main_rank:
                            ui.label(main_rank + stale_indicator).style(
                                label_caps(f'color: {stale_color};')
                            )
                        else:
                            ui.label('SEM RANK').style(label_caps(f'color: {C["text_dim"]};'))
                        if main_mmr:
                            ui.label('•').style(f'color: {C["text_dim"]}; font-size: 10px;')
                            ui.label(f'MMR {main_mmr}').style(
                                f'font-size: 12px; font-family: "JetBrains Mono"; color: {C["text_var"]};'
                            )

            ui.space().style('height: 16px;')

            # Rank por playlist
            if rank_data and rank_data.get("success") and rank_data.get("ranked"):
                ranked = rank_data["ranked"]
                with ui.row().classes('w-full gap-2'):
                    for playlist in ["1v1", "2v2", "3v3"]:
                        p = ranked.get(playlist, {})
                        if p:
                            tier_color = _tier_color(p.get("tier", ""))
                            with ui.column().classes('items-center gap-0').style(
                                f'flex: 1; padding: 6px; border-radius: 8px; '
                                f'background: rgba(255,255,255,0.03);'
                            ):
                                ui.label(playlist.upper()).style(
                                    f'font-size: 9px; color: {C["text_dim"]}; letter-spacing: 0.1em;'
                                )
                                ui.label(p.get("rank", "?").split()[-1] if p.get("rank") else "?").style(
                                    f'font-size: 11px; font-weight: 700; color: {tier_color};'
                                )
                                ui.label(str(p.get("mmr", ""))).style(
                                    f'font-size: 9px; font-family: "JetBrains Mono"; color: {C["text_dim"]};'
                                )
            else:
                # Sem dados de rank
                with ui.row().classes('w-full justify-between'):
                    ui.label('RANK POR PLAYLIST').style(label_caps(f'color: {C["text_var"]}; font-size: 10px;'))
                    if not rl_nickname:
                        ui.label('Configure o nick nas Settings').style(
                            f'font-size: 10px; color: {C["text_dim"]}; font-style: italic;'
                        )
                    elif rank_data and rank_data.get("error"):
                        ui.label(stale_indicator or 'Indisponivel').style(
                            f'font-size: 10px; color: {C["text_dim"]}; font-style: italic;'
                        )

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

    # ── STREAK / TILT WARNING ─────────────────────────────────────────────

    def _build_streak_warning(self) -> None:
        """Mostra aviso se detectar sequência de derrotas ou queda de qualidade."""
        try:
            streak = self.db.detect_lose_streak(min_streak=2)
            quality = self.db.detect_quality_drop(window=5)
        except Exception:
            return

        if not streak and not quality:
            return

        with ui.card().classes('w-full fade-in').style(
            glass('padding: 16px 20px; border-left: 4px solid rgba(255,180,171,0.7);')
        ):
            with ui.row().classes('w-full items-center gap-3'):
                ui.icon('warning', size='20px').style(f'color: {C["error"]};')
                if streak:
                    n = streak['streak_length']
                    ui.label(f'Sequência de {n} derrota(s) detectada').style(
                        f'font-size: 14px; font-weight: 700; color: {C["error"]};'
                    )
                if quality and quality.get('suggesting_pause'):
                    ui.label('  •  Queda de qualidade detectada após derrotas').style(
                        f'font-size: 13px; color: {C["text_var"]};'
                    )

            if quality and quality.get('suggesting_pause'):
                ui.label(
                    f'Performance caiu de {quality["before_avg"]}% para {quality["after_avg"]}% '
                    f'(-{quality["drop_pct"]}%). Considere fazer uma pausa.'
                ).style(f'font-size: 12px; color: {C["text_dim"]}; margin-top: 4px;')

    def _chat_msg(self, sender: str, message: str, container=None) -> None:
        is_ai = sender == 'ai'
        target = container
        if target is None:
            return
        with target:
            with ui.card().classes('w-full').style(
                f'background: {"rgba(50,53,60,0.8)" if is_ai else "rgba(173,198,255,0.15)"}; '
                f'border: 1px solid {"rgba(255,255,255,0.05)" if is_ai else "rgba(173,198,255,0.2)"}; '
                f'border-radius: {"16px 16px 16px 4px" if is_ai else "16px 16px 4px 16px"}; '
                f'padding: 12px 16px; margin-bottom: 8px; '
                f'{"max-width: 85%;" if is_ai else "max-width: 85%; margin-left: auto;"}'
            ):
                ui.markdown(message).style(
                    f'font-size: 14px; color: {C["text"]}; margin: 0; line-height: 1.5;'
                )

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
                    self._timeline_btns = {}
                    for label in ['7D', '30D', 'Season']:
                        is_active = label == '7D'
                        btn = ui.button(label, on_click=lambda e, l=label: self._on_timeline_range(l)).style(
                            f'padding: 6px 16px; border-radius: 8px; font-size: 12px; font-weight: 700; '
                            f'{"background: " + C["surface_highest"] + "; color: " + C["primary"] + ";" if is_active else "background: transparent; color: " + C["text_var"] + ";"}'
                            f'border: none; text-transform: none;'
                        ).props('flat')
                        self._timeline_btns[label] = btn

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

                def on_browse_upload(e):
                    import tempfile, asyncio
                    if e.file and not e.file.name.endswith('.replay'):
                        ui.notification('Selecione um arquivo .replay', type='warning')
                        return
                    if e.file:
                        async def save_and_analyze():
                            data = await e.file.read()
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.replay')
                            tmp.write(data)
                            tmp.close()
                            self._analyze_replay(tmp.name)
                        asyncio.ensure_future(save_and_analyze())

                self._hidden_upload = ui.upload(
                    multiple=False, auto_upload=True,
                    label='Selecionar arquivo .replay'
                ).on_upload(on_browse_upload).classes('w-full').style(
                    'position: absolute; opacity: 0; pointer-events: none; height: 0; overflow: hidden;'
                )

                ui.button(icon='folder_open', text='Browse').style(
                    f'background: {C["primary_container"]}; color: {C["on_primary"]}; '
                    f'border-radius: 8px; padding: 10px 16px; font-weight: 600; text-transform: none;'
                ).on_click(self._browse_replay)

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
                self.analysis_input.on('keydown.enter', self._send_analysis_chat)
                ui.button(icon='send').style(f'color: {C["primary"]};').on_click(self._send_analysis_chat)

    def _build_team_header(self, result: Dict[str, Any]) -> None:
        """Constrói cabeçalho com times e jogadores."""
        team_zero = result.get("team_zero", [])
        team_one = result.get("team_one", [])
        team_zero_score = result.get("team_zero_score", 0)
        team_one_score = result.get("team_one_score", 0)
        # Usar _current_player_name para manter consistência com o dropdown
        player_name = getattr(self, '_current_player_name', result.get("player_name", ""))
        game_mode = result.get("game_mode", "2v2")
        
        # Se não houver dados de time, não mostrar o cabeçalho
        if not team_zero and not team_one:
            return
        
        # Determinar número de jogadores por time
        team_size = len(team_zero) if team_zero else (3 if "3v3" in game_mode else (2 if "2v2" in game_mode else 1))
        
        # Função para truncar nomes longos
        def truncate_name(name: str, max_len: int = 12) -> str:
            return name[:max_len] + "..." if len(name) > max_len else name
        
        with ui.card().classes('w-full fade-in').style(glass('padding: 20px 24px;')):
            with ui.row().classes('w-full items-center justify-between'):
                # Time Orange (team_zero)
                with ui.column().classes('items-center gap-2').style('flex: 1;'):
                    with ui.row().classes('items-center gap-2'):
                        ui.html(f'<div style="width:16px; height:16px; border-radius:50%; background:#FF8C00;"></div>')
                        ui.label('ORANGE').style(
                            f'font-size: 12px; font-weight: 700; color: #FF8C00; letter-spacing: 0.1em;'
                        )
                    with ui.column().classes('items-center gap-1'):
                        for player in team_zero[:team_size]:
                            name = truncate_name(player.get("name", "Jogador desconhecido"))
                            is_main = player.get("name", "").lower() == player_name.lower()
                            style = (
                                f'font-size: {"14px" if is_main else "12px"}; '
                                f'font-weight: {"700" if is_main else "500"}; '
                                f'color: {"#FFFFFF" if is_main else "rgba(255,255,255,0.7)"}; '
                                f'{"text-decoration: underline;" if is_main else ""}'
                            )
                            ui.label(name).style(style)
                
                # Score central
                with ui.column().classes('items-center gap-1').style('padding: 0 24px;'):
                    with ui.row().classes('items-center gap-4'):
                        ui.label(str(team_zero_score)).style(
                            f'font-size: 32px; font-weight: 900; color: #FF8C00;'
                        )
                        ui.label('-').style(
                            f'font-size: 24px; font-weight: 700; color: rgba(255,255,255,0.5);'
                        )
                        ui.label(str(team_one_score)).style(
                            f'font-size: 32px; font-weight: 900; color: #0078D4;'
                        )
                
                # Time Blue (team_one)
                with ui.column().classes('items-center gap-2').style('flex: 1;'):
                    with ui.row().classes('items-center gap-2'):
                        ui.html(f'<div style="width:16px; height:16px; border-radius:50%; background:#0078D4;"></div>')
                        ui.label('BLUE').style(
                            f'font-size: 12px; font-weight: 700; color: #0078D4; letter-spacing: 0.1em;'
                        )
                    with ui.column().classes('items-center gap-1'):
                        for player in team_one[:team_size]:
                            name = truncate_name(player.get("name", "Jogador desconhecido"))
                            is_main = player.get("name", "").lower() == player_name.lower()
                            style = (
                                f'font-size: {"14px" if is_main else "12px"}; '
                                f'font-weight: {"700" if is_main else "500"}; '
                                f'color: {"#FFFFFF" if is_main else "rgba(255,255,255,0.7)"}; '
                                f'{"text-decoration: underline;" if is_main else ""}'
                            )
                            ui.label(name).style(style)
    
    def _send_analysis_chat(self) -> None:
        msg = self.analysis_input.value
        if not msg:
            return
        self.analysis_input.value = ''
        self._chat_msg('user', msg, container=self.analysis_chat)

        if self.ai_coach:
            import asyncio
            coach = self.ai_coach
            # Pegar stats do replay atualmente selecionado
            last_result = getattr(self, '_last_analysis_result', None)
            async def _call_coach():
                response = await asyncio.to_thread(coach.chat, msg, None, last_result)
                self._chat_msg('ai', response or 'Erro ao processar mensagem.', container=self.analysis_chat)
            asyncio.ensure_future(_call_coach())
        else:
            self._chat_msg('ai', 'AI Coach não disponível. Configure <b>nvidia_api_key</b> no config.json.', container=self.analysis_chat)

    def _load_replay_list(self) -> None:
        replay_folder = self.config.get('replays_folder', self.config.get('replay_folder', ''))
        # Expandir variáveis de ambiente e ~
        if replay_folder:
            replay_folder = os.path.expandvars(replay_folder)
            replay_folder = os.path.expanduser(replay_folder)
        # Fallback para pasta padrão do Rocket League
        if not replay_folder or not os.path.exists(replay_folder):
            replay_folder = os.path.join(
                os.path.expanduser('~'), 'Documents', 'My Games', 'Rocket League', 'TAGame', 'Demos'
            )
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

    def _on_timeline_range(self, label: str) -> None:
        for l, btn in self._timeline_btns.items():
            if l == label:
                btn.style(f'padding: 6px 16px; border-radius: 8px; font-size: 12px; font-weight: 700; background: {C["surface_highest"]}; color: {C["primary"]}; border: none; text-transform: none;')
            else:
                btn.style(f'padding: 6px 16px; border-radius: 8px; font-size: 12px; font-weight: 700; background: transparent; color: {C["text_var"]}; border: none; text-transform: none;')
        matches = self.db.get_matches(limit=50)
        self._update_timeline(matches)

    def _on_match_filter(self, label: str) -> None:
        for l, btn in self._filter_btns.items():
            if l == label:
                btn.style(f'padding: 8px 24px; border-radius: 8px; font-size: 12px; font-weight: 700; background: {C["primary"]}; color: {C["on_primary"]}; border: none; text-transform: none;')
            else:
                btn.style(f'padding: 8px 24px; border-radius: 8px; font-size: 12px; font-weight: 700; background: transparent; color: {C["text_var"]}; border: none; text-transform: none;')
        playlist_map = {'All': None, '1v1': '1v1', '2v2': '2v2', '3v3': '3v3'}
        playlist_filter = playlist_map.get(label)
        if playlist_filter:
            matches = [m for m in self.db.get_matches(limit=50) if playlist_filter in (m.get('playlist', '') or '')]
        else:
            matches = self.db.get_matches(limit=50)
        self._rebuild_match_history(matches)

    def _rebuild_match_history(self, matches: list) -> None:
        self._match_history_container.clear()
        with self._match_history_container:
            if not matches:
                with ui.column().classes('w-full items-center justify-center').style('padding: 80px 0;'):
                    ui.icon('inbox', size='64px').style(f'color: {C["text_dim"]}; opacity: 0.3;')
                    ui.label('Nenhuma partida registrada').style(f'font-size: 16px; color: {C["text_dim"]}; margin-top: 12px;')
                return
            for match in matches:
                self._build_history_card(match)

    def _on_replay_select(self, e) -> None:
        if not e.value:
            return
        default = os.path.join(
            os.path.expanduser('~'), 'Documents', 'My Games', 'Rocket League', 'TAGame', 'Demos'
        )
        replay_folder = self.config.get('replays_folder', self.config.get('replay_folder', default))
        # Expandir variáveis de ambiente e ~
        if replay_folder:
            replay_folder = os.path.expandvars(replay_folder)
            replay_folder = os.path.expanduser(replay_folder)
        if not replay_folder or not os.path.exists(replay_folder):
            replay_folder = default
        replay_path = os.path.join(replay_folder, e.value)
        self._analyze_replay(replay_path)

    def _browse_replay(self) -> None:
        ui.run_javascript('''
            const inputs = document.querySelectorAll('input[type="file"]');
            for (const input of inputs) {
                if (input.accept && input.accept.includes('.replay') || input.closest('.q-upload')) {
                    input.click();
                    return;
                }
            }
            if (inputs.length > 0) inputs[inputs.length - 1].click();
        ''')

    def _analyze_replay(self, replay_path: str, player_index: Optional[int] = None) -> None:
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

        import asyncio
        # Usar player_name do resultado anterior se disponível (para manter consistência)
        current_player = getattr(self, '_current_player_name', self.config.get('rl_nickname', self.config.get('player_name', '')))
        analyzer = LocalReplayAnalyzer(current_player)
        container = self.analysis_container
        ai_coach = self.ai_coach
        show_results = self._show_analysis_results
        show_player_selector = self._show_player_selector
        replay_path_ref = replay_path

        async def _do_analysis():
            try:
                result = await asyncio.to_thread(analyzer.analyze_replay, replay_path, player_index)
                
                if result:
                    self._last_analysis_result = result
                    self._last_replay_path = replay_path_ref
                    self._last_analyzer = analyzer
                    
                    # Atualizar player_name selecionado
                    self._current_player_name = result.get('player_name', current_player)
                    
                    # Limpar e recriar conteúdo dentro do container
                    container.clear()
                    with container:
                        # Mostrar seletor de jogador primeiro
                        all_players = result.get("all_players", [])
                        selected_idx = result.get("selected_player_index", 0)
                        if all_players and len(all_players) > 1:
                            self._show_player_selector(all_players, selected_idx)
                        
                        # Aviso de fallback se nome não encontrado
                        if result.get("fallback_used"):
                            fallback_name = result.get("fallback_player_name", "")
                            configured_name = self._current_player_name
                            with ui.card().classes('w-full fade-in').style(
                                'background: rgba(255, 193, 7, 0.1); border: 1px solid rgba(255, 193, 7, 0.3); '
                                'border-radius: 8px; padding: 12px 16px;'
                            ):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon('warning', size='20px').style('color: #ffc107;')
                                    ui.label(
                                        f'Não encontramos \'{configured_name}\' neste replay — '
                                        f'mostrando dados de {fallback_name} como melhor estimativa. '
                                        f'Confira se está correto.'
                                    ).style(
                                        'font-size: 13px; color: #ffc107; line-height: 1.4;'
                                    )
                        
                        show_results(result)
                        # Gerar resumo pós-jogo automático + análise IA
                        if ai_coach:
                            summary = await asyncio.to_thread(ai_coach.generate_postgame_summary, result)
                            if summary:
                                self._show_postgame_summary(summary)
                            ai_response = await asyncio.to_thread(ai_coach.analyze_replay, result, None, None)
                            if ai_response:
                                self._show_ai_analysis(ai_response)
                else:
                    container.clear()
                    with container:
                        ui.icon('warning', size='48px').style(f'color: {C["warning"]};')
                        ui.label('Replay não analisado').style(f'color: {C["warning"]}; margin-top: 8px;')
            except Exception as ex:
                container.clear()
                with container:
                    ui.icon('error', size='48px').style(f'color: {C["error"]};')
                    ui.label(str(ex)).style(f'color: {C["error"]}; margin-top: 8px; font-size: 12px;')

        asyncio.ensure_future(_do_analysis())

    def _show_player_selector(self, all_players: List[Dict], selected_index: int) -> None:
        """Mostra seletor de jogador do lobby."""
        with ui.card().classes('w-full fade-in').style(glass('padding: 16px 20px;')):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('people', size='20px').style(f'color: {C["primary"]};')
                ui.label('ANALISAR JOGADOR').style(
                    f'font-size: 12px; font-weight: 700; color: {C["text_var"]}; letter-spacing: 0.1em;'
                )
                
                # Montar opções do select
                options = {}
                for p in all_players:
                    team_icon = "🟠" if p["team"] == 0 else "🔵"
                    label = f"{team_icon} {p['name']} ({p['platform']})"
                    options[p["index"]] = label
                
                # Select de jogador
                self.player_select = ui.select(
                    options=options,
                    value=selected_index,
                    label='Jogador',
                    on_change=self._on_player_select
                ).classes('w-80').props('outlined dense')
            
            ui.label('Selecione outro jogador para comparar o lobby').style(
                f'font-size: 12px; color: {C["text_dim"]}; margin-top: 8px;'
            )

    def _on_player_select(self, e) -> None:
        """Chamado quando o usuário seleciona outro jogador."""
        if e.value is None or not hasattr(self, '_last_replay_path'):
            return
        
        player_index = int(e.value)
        # Atualizar player_name selecionado antes de re-analisar
        all_players = self._last_analysis_result.get('all_players', []) if hasattr(self, '_last_analysis_result') else []
        for p in all_players:
            if p.get('index') == player_index:
                self._current_player_name = p.get('name', self._current_player_name)
                break
        self._analyze_replay(self._last_replay_path, player_index)

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
        # Usar _current_player_name para manter consistência com o dropdown
        player_name = getattr(self, '_current_player_name', result.get('player_name', self.config.get('player_name', 'You')))
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

        # Movimentação: quanto menor a distância à bola, melhor
        # ~300uu = muito perto (score 100), ~3000uu = muito longe (score 0)
        if avg_dist > 0:
            movement_score = max(0, min(100, int(100 * (3000 - avg_dist) / 2700)))
        else:
            movement_score = 50
        aerial_score = max(0, min(100, int(boost_collected / 50))) if boost_collected > 0 else 30
        positioning_score = max(0, min(100, 100 - abs(time_off - 50) * 2))
        boost_eff = (boost_used / boost_collected * 100) if boost_collected > 0 else 0
        boost_score = max(0, min(100, int(boost_eff * 1.1)))
        shooting_score = int((goals / shots * 100)) if shots > 0 else 0

        overall_score = (movement_score + aerial_score + positioning_score + boost_score + shooting_score) // 5

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

            # Team header
            self._build_team_header(result)

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

            # AI Analysis (async LLM call)
            self._analysis_result_container = ui.column().classes('w-full')
            if self.ai_coach:
                with self._analysis_result_container:
                    with ui.card().classes('w-full fade-in').style(
                        glass('padding: 20px; border-left: 4px solid rgba(173,198,255,0.5); animation-delay: 0.4s;')
                    ):
                        with ui.row().classes('items-center gap-3').style('margin-bottom: 16px;'):
                            ui.icon('psychology', size='20px').style(f'color: {C["primary"]};')
                            ui.label('AI COACH ANALYSIS').style(
                                f'font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;'
                            )
                        ui.spinner(size='sm').style(f'color: {C["primary"]};')
                        ui.label(' Análise gerando...').style(f'font-size: 13px; color: {C["text_var"]};')
                import asyncio
                coach = self.ai_coach
                container = self._analysis_result_container
                async def _load_analysis():
                    analysis = await asyncio.to_thread(coach.generate_match_analysis, result)
                    container.clear()
                    with container:
                        with ui.card().classes('w-full fade-in').style(
                            glass('padding: 20px; border-left: 4px solid rgba(173,198,255,0.5); animation-delay: 0.4s;')
                        ):
                            with ui.row().classes('items-center gap-3').style('margin-bottom: 16px;'):
                                ui.icon('psychology', size='20px').style(f'color: {C["primary"]};')
                                ui.label('AI COACH ANALYSIS').style(
                                    f'font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;'
                                )
                            if analysis:
                                ui.markdown(analysis).style(
                                    f'font-size: 13px; color: {C["text_var"]}; line-height: 1.6;'
                                )
                            else:
                                ui.label('Não foi possível gerar a análise. Tente novamente.').style(
                                    f'font-size: 13px; color: {C["text_dim"]};'
                                )
                asyncio.ensure_future(_load_analysis())

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

            with ui.row().classes('w-full justify-between items-baseline').style('margin-bottom: 12px;'):
                ui.label('Avg Distance').style(label_caps(f'font-size: 10px; color: {C["text_var"]}; white-space: nowrap;'))
                ui.label(f'{avg_dist:.0f}u').style(stat_mono(f'font-size: 18px; font-weight: 600; color: {C["text"]}; white-space: nowrap;'))

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


    def _add_postgame_summary(self, result: Dict[str, Any]) -> None:
        pass  # Removido — agora usado via _show_postgame_summary

    def _add_ai_analysis_card(self, result: Dict[str, Any]) -> None:
        pass  # Removido — agora usado via _show_ai_analysis

    def _show_postgame_summary(self, summary: str) -> None:
        """Exibe resumo pós-jogo na área de análise."""
        with self.analysis_container:
            with ui.card().classes('w-full fade-in').style(
                glass('padding: 16px 20px; border-left: 4px solid rgba(76,215,246,0.5);')
            ):
                with ui.row().classes('items-center gap-3').style('margin-bottom: 8px;'):
                    ui.icon('summarize', size='18px').style(f'color: {C["tertiary"]};')
                    ui.label('RESUMO PÓS-JOGO').style(
                        f'font-size: 12px; font-weight: 700; color: {C["tertiary"]}; text-transform: uppercase; letter-spacing: 0.1em;'
                    )
                ui.markdown(summary).style(
                    f'font-size: 13px; color: {C["text_var"]}; line-height: 1.6;'
                )

    def _show_ai_analysis(self, analysis: str) -> None:
        """Exibe análise detalhada do AI Coach na área de análise."""
        with self.analysis_container:
            ui.space().style('height: 16px;')
            with ui.card().classes('w-full fade-in').style(
                glass('padding: 20px; border-left: 4px solid rgba(173,198,255,0.5); animation-delay: 0.4s;')
            ):
                with ui.row().classes('items-center gap-3').style('margin-bottom: 16px;'):
                    ui.icon('psychology', size='20px').style(f'color: {C["primary"]};')
                    ui.label('AI COACH ANALYSIS').style(
                        f'font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;'
                    )
                ui.markdown(analysis).style(
                    f'font-size: 13px; color: {C["text_var"]}; line-height: 1.6;'
                )

    def _generate_analysis_tips(self, result: Dict) -> list:
        # Removido — análise agora é gerada pelo LLM via generate_match_analysis()
        return []

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
            self._filter_btns = {}
            for label in ['All', '1v1', '2v2', '3v3']:
                is_active = label == 'All'
                btn = ui.button(label, on_click=lambda e, l=label: self._on_match_filter(l)).style(
                    f'padding: 8px 24px; border-radius: 8px; font-size: 12px; font-weight: 700; '
                    f'{"background: " + C["primary"] + "; color: " + C["on_primary"] + ";" if is_active else "background: transparent; color: " + C["text_var"] + ";"}'
                    f'border: none; text-transform: none;'
                ).props('flat')
                self._filter_btns[label] = btn

        matches = self.db.get_matches(limit=50)
        if not matches:
            with ui.column().classes('w-full items-center justify-center').style('padding: 80px 0;'):
                ui.icon('inbox', size='64px').style(f'color: {C["text_dim"]}; opacity: 0.3;')
                ui.label('Nenhuma partida registrada').style(f'font-size: 16px; color: {C["text_dim"]}; margin-top: 12px;')
                ui.label('Jogue algumas partidas para ver seus resultados aqui.').style(
                    f'font-size: 13px; color: {C["text_dim"]};'
                )
            return

        self._match_history_container = ui.column().classes('w-full gap-3')
        with self._match_history_container:
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
    # PRO COMPARISON PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_metric_card(self, metric: Dict[str, Any]) -> None:
        """Constrói um card individual de métrica: Jogador vs Profissional."""
        value = metric.get("value", 0)
        pro_avg = metric.get("pro_avg", 0)
        status = metric.get("status", "dentro_meta")
        label = metric.get("label", "?")
        unit = metric.get("unit", "")

        STATUS_STYLES = {
            "muito_baixo": {"color": "#ff5252", "bg": "#ff525215", "badge": "MUITO BAIXO", "icon": "arrow_downward"},
            "abaixo":      {"color": "#ff9800", "bg": "#ff980015", "badge": "ABAIXO",      "icon": "south"},
            "dentro_meta": {"color": "#4cd7f6", "bg": "#4cd7f615", "badge": "DENTRO DA META", "icon": "check"},
            "acima":       {"color": "#ff9800", "bg": "#ff980015", "badge": "ACIMA",       "icon": "north"},
            "muito_alto":  {"color": "#ff5252", "bg": "#ff525215", "badge": "MUITO ALTO",  "icon": "arrow_upward"},
        }
        s = STATUS_STYLES.get(status, STATUS_STYLES["dentro_meta"])

        with ui.card().classes('w-full fade-in').style(
            f'background: {C["surface"]}; border: 1px solid rgba(255,255,255,0.08); '
            f'border-radius: 16px; padding: 20px;'
        ):
            # Header: label + badge
            with ui.row().classes('w-full items-center justify-between'):
                ui.label(label).style(
                    f'font-size: 13px; font-weight: 600; color: {C["text_var"]};'
                )
                with ui.row().classes('items-center gap-1').style(
                    f'background: {s["bg"]}; padding: 3px 10px; border-radius: 12px;'
                ):
                    ui.label(s["badge"]).style(
                        f'font-size: 10px; font-weight: 700; color: {s["color"]}; text-transform: uppercase;'
                    )

            ui.space().style('height: 12px;')

            # Player value vs Pro value
            with ui.row().classes('w-full items-end justify-between'):
                # Player value
                with ui.column().classes('gap-1'):
                    ui.label('VOCÊ').style(
                        f'font-size: 9px; font-weight: 700; color: {C["text_var"]}; text-transform: uppercase;'
                    )
                    ui.label(f'{value:.1f}').style(
                        f'font-size: 24px; font-weight: 800; color: {C["text"]}; line-height: 1;'
                    )
                    ui.label(unit).style(
                        f'font-size: 10px; color: {C["text_var"]};'
                    )

                # Separator
                ui.html(f'<div style="width:1px; height:40px; background:rgba(255,255,255,0.1);"></div>')

                # Pro value
                with ui.column().classes('gap-1'):
                    ui.label('PRO').style(
                        f'font-size: 9px; font-weight: 700; color: {C["text_var"]}; text-transform: uppercase;'
                    )
                    ui.label(f'{pro_avg:.1f}').style(
                        f'font-size: 24px; font-weight: 800; color: {C["primary"]}; line-height: 1;'
                    )
                    ui.label(unit).style(
                        f'font-size: 10px; color: {C["text_var"]};'
                    )

            ui.space().style('height: 12px;')

            # Progress bar (value relative to pro)
            max_val = max(value, pro_avg) * 1.3 if max(value, pro_avg) > 0 else 100
            player_pct = min(100, (value / max_val) * 100) if max_val > 0 else 0
            pro_pct = min(100, (pro_avg / max_val) * 100) if max_val > 0 else 0

            ui.html(
                f'<div style="width:100%; height:6px; background:rgba(255,255,255,0.05); border-radius:3px; position:relative;">'
                f'<div style="position:absolute; left:0; top:0; height:100%; width:{player_pct:.0f}%; '
                f'background: {C["text"]}; border-radius:3px; opacity:0.7;"></div>'
                f'<div style="position:absolute; left:0; top:0; height:100%; width:{pro_pct:.0f}%; '
                f'background: {C["primary"]}; border-radius:3px; opacity:0.4;"></div>'
                f'</div>'
            )

    def _build_pro_comparison_page(self) -> None:
        """Página de Comparação Profissional — cada métrica vs baseline pro."""
        import asyncio
        self._build_top_bar('Comparação Profissional', 'Analise sua performance vs o meta profissional')

        # Check if we have analysis data
        last_result = getattr(self, '_last_analysis_result', None)

        with ui.column().classes('w-full gap-6').style('max-width: 1100px;'):
            if not last_result:
                # No data message
                with ui.card().classes('w-full fade-in').style(
                    f'background: {C["surface"]}; border: 1px solid rgba(255,255,255,0.08); '
                    f'border-radius: 16px; padding: 48px; text-align: center;'
                ):
                    ui.icon('analytics', size='48px').style(f'color: {C["text_var"]};')
                    ui.space().style('height: 16px;')
                    ui.label('Nenhum replay analisado ainda').style(
                        f'font-size: 18px; font-weight: 600; color: {C["text"]};'
                    )
                    ui.space().style('height: 8px;')
                    ui.label('Analise um replay na aba Replay Analysis para ver a comparação com profissionais.').style(
                        f'font-size: 13px; color: {C["text_var"]};'
                    )
                return

            # Import comparison module
            from bot.baseline import build_pro_comparison, calculate_composite_scores

            comparison = build_pro_comparison(last_result)
            metrics = comparison.get("metrics", [])
            skills = comparison.get("skill_scores", {})
            composite = comparison.get("composite", 0)

            # ── Composite Score Card ──
            with ui.card().classes('w-full fade-in').style(
                f'background: {C["surface"]}; border: 1px solid rgba(255,255,255,0.08); '
                f'border-radius: 16px; padding: 24px;'
            ):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('emoji_events', size='32px').style(f'color: {C["primary"]};')
                        with ui.column().classes('gap-1'):
                            ui.label('SCORE COMPOSTO').style(
                                f'font-size: 11px; font-weight: 700; color: {C["text_var"]}; text-transform: uppercase;'
                            )
                            ui.label(f'{composite:.0f}/100').style(
                                f'font-size: 28px; font-weight: 800; color: {C["primary"]};'
                            )

                    # Skill scores summary
                    with ui.row().classes('gap-6'):
                        skill_labels = {
                            "movimentacao": "Movimentação",
                            "competencia_aerea": "Aéreo",
                            "posicionamento_campo": "Posicionamento",
                            "gestao_de_boost": "Boost",
                        }
                        for key, lbl in skill_labels.items():
                            sc = skills.get(key, 0)
                            color = C["tertiary"] if sc >= 70 else (C["error"] if sc < 40 else C["text"])
                            with ui.column().classes('items-center gap-1'):
                                ui.label(f'{sc:.0f}').style(
                                    f'font-size: 18px; font-weight: 700; color: {color};'
                                )
                                ui.label(lbl).style(
                                    f'font-size: 9px; font-weight: 600; color: {C["text_var"]}; text-transform: uppercase;'
                                )

            # ── AI Recap ──
            if self.ai_coach:
                async def _load_recap():
                    from bot.ai_coach import AICoach
                    recap = await asyncio.to_thread(
                        self.ai_coach.generate_match_recap, last_result, comparison
                    )
                    if recap:
                        recap_card.clear()
                        with recap_card:
                            with ui.row().classes('items-start gap-3'):
                                ui.icon('auto_awesome', size='20px').style(f'color: {C["primary"]}; margin-top: 2px;')
                                ui.label(recap).style(
                                    f'font-size: 13px; color: {C["text"]}; line-height: 1.6;'
                                )

                with ui.card().classes('w-full fade-in').style(
                    f'background: {C["surface"]}; border: 1px solid rgba(173,198,255,0.15); '
                    f'border-radius: 16px; padding: 20px;'
                ) as recap_card:
                    with ui.row().classes('items-center gap-2'):
                        ui.spinner(size='sm').style(f'color: {C["primary"]};')
                        ui.label('Gerando resumo...').style(f'font-size: 13px; color: {C["text_var"]};')

                asyncio.ensure_future(_load_recap())

            # ── Metric Sections ──
            SECTIONS = {
                "Posicionamento de Zona": ["time_offensive_pct", "time_defensive_pct", "avg_distance_to_ball"],
                "Gestão de Boost": ["boost_collected_per_min", "boost_used_per_min", "big_pads_per_min",
                                    "small_pads_per_min", "time_full_boost_pct", "time_zero_boost_pct", "time_boost_low_pct"],
                "Finalização": ["goals_per_min", "shots_per_min", "shot_speed_avg", "shot_speed_aerial_avg"],
                "Distribuição de Altura Aérea": ["aerial_height_high_pct", "time_supersonic_pct"],
                "Velocidade e Potência": ["avg_speed", "demos_per_min", "score_per_min"],
            }

            for section_name, section_keys in SECTIONS.items():
                section_metrics = [m for m in metrics if m["metric_key"] in section_keys]
                if not section_metrics:
                    continue

                ui.space().style('height: 8px;')

                with ui.card().classes('w-full fade-in').style(
                    f'background: {C["surface"]}; border: 1px solid rgba(255,255,255,0.08); '
                    f'border-radius: 16px; padding: 20px;'
                ):
                    ui.label(section_name.upper()).style(
                        f'font-size: 11px; font-weight: 700; color: {C["text_var"]}; '
                        f'text-transform: uppercase; margin-bottom: 16px;'
                    )

                    with ui.grid(columns=3).classes('w-full gap-4'):
                        for m in section_metrics:
                            self._build_metric_card(m)

            # ── AI Metric Explanations (for anomalies) ──
            anomalous = [m for m in metrics if m["status"] in ("muito_baixo", "muito_alto")]
            if anomalous and self.ai_coach:
                ui.space().style('height: 8px;')

                with ui.card().classes('w-full fade-in').style(
                    f'background: {C["surface"]}; border: 1px solid rgba(255,82,82,0.15); '
                    f'border-radius: 16px; padding: 20px;'
                ):
                    ui.label('ANÁLISE DE ANOMALIAS').style(
                        f'font-size: 11px; font-weight: 700; color: {C["error"]}; '
                        f'text-transform: uppercase; margin-bottom: 16px;'
                    )

                    async def _load_explanations():
                        explanations = []
                        for m in anomalous:
                            exp = await asyncio.to_thread(
                                self.ai_coach.generate_metric_explanation,
                                m["label"], m["value"], m["pro_avg"],
                                m["unit"], m["status"]
                            )
                            if exp:
                                explanations.append((m["label"], exp))

                        expl_container.clear()
                        with expl_container:
                            if explanations:
                                for lbl, exp in explanations:
                                    with ui.row().classes('items-start gap-3').style('margin-bottom: 8px;'):
                                        ui.label(f'• {lbl}:').style(
                                            f'font-size: 13px; font-weight: 600; color: {C["text"]};'
                                        )
                                        ui.label(exp).style(
                                            f'font-size: 13px; color: {C["text_var"]};'
                                        )
                            else:
                                ui.label('Nenhuma anomalia significativa detectada.').style(
                                    f'font-size: 13px; color: {C["text_var"]};'
                                )

                    with ui.row().classes('items-center gap-2'):
                        expl_container = ui.column().classes('w-full')
                        ui.spinner(size='sm').style(f'color: {C["error"]};')
                        ui.label('Analisando anomalias...').style(f'font-size: 13px; color: {C["text_var"]};')

                    asyncio.ensure_future(_load_explanations())

    # ════════════════════════════════════════════════════════════════════════
    # PROFILE PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_profile_page(self) -> None:
        self._build_top_bar('Profile', 'Gerencie suas contas e informações')

        with ui.column().classes('w-full max-w-2xl gap-6'):
            # ── Profile Header Card ──
            with ui.card().classes('w-full fade-in').style(
                glass('padding: 0; overflow: hidden;')
            ):
                # Banner
                ui.html(
                    '<div style="height: 120px; background: linear-gradient(135deg, '
                    f'{C["primary_dim"]} 0%, {C["secondary_container"]} 50%, '
                    f'{C["tertiary_cont"]} 100%); position: relative;">'
                    '<div style="position: absolute; inset: 0; background: '
                    'radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 50%);"></div>'
                    '</div>'
                )
                with ui.column().classes('items-center').style('margin-top: -48px; padding: 0 32px 32px; position: relative; z-index: 1;'):
                    # Avatar
                    ui.avatar(
                        icon='person',
                        color=C['primary_container'],
                        text_color='white',
                        size='96px'
                    ).style(
                        f'border: 4px solid {C["surface"]}; box-shadow: 0 8px 32px rgba(0,0,0,0.3);'
                    )
                    # Name
                    display_name = (
                        self.config.get('discord_username', '')
                        or self.config.get('player_name', '')
                        or self.config.get('discord_id', 'Player')
                    )
                    ui.label(display_name).style(
                        f'font-size: 24px; font-weight: 700; color: {C["text"]}; margin-top: 12px;'
                    )
                    # Discord ID badge
                    discord_id = self.config.get('discord_id', '')
                    if discord_id:
                        ui.html(
                            f'<div style="display: flex; align-items: center; gap: 6px; '
                            f'padding: 6px 14px; border-radius: 20px; '
                            f'background: rgba(88,101,242,0.15); border: 1px solid rgba(88,101,242,0.3); '
                            f'margin-top: 8px;">'
                            f'<span class="material-symbols-outlined" style="font-size: 16px; color: #5865F2;">chat</span>'
                            f'<span style="font-size: 13px; color: #5865F2; font-weight: 600;">{discord_id}</span>'
                            f'</div>'
                        )

            # ── Player Name Editor ──
            # ── Discord Linking ──
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.1s;')):
                with ui.row().classes('w-full items-center gap-3'):
                    ui.html(
                        '<div style="width: 32px; height: 32px; border-radius: 8px; '
                        'background: linear-gradient(135deg, #5865F2, #4752C4); '
                        'display: flex; align-items: center; justify-content: center;">'
                        '<span class="material-symbols-outlined" style="font-size: 18px; color: white;">chat</span>'
                        '</div>'
                    )
                    ui.label('Discord').style(f'font-size: 16px; font-weight: 700; color: {C["text"]};')

                discord_id = self.config.get('discord_id', '')
                if discord_id:
                    discord_display = self.config.get('discord_username', '') or discord_id
                    with ui.row().classes('w-full items-center gap-2').style('margin: 12px 0;'):
                        ui.icon('check_circle', size='18px').style(f'color: {C["tertiary"]};')
                        ui.label(f'Conectado: {discord_display} ({discord_id})').style(
                            f'font-size: 13px; color: {C["tertiary"]};'
                        )
                    self.profile_discord_btn = ui.button(
                        icon='link', text='Vincular novamente',
                        on_click=self._link_discord
                    ).style(
                        f'background: {C["surface_high"]}; color: {C["text"]}; '
                        f'border-radius: 12px; padding: 10px 20px; font-weight: 600; text-transform: none;'
                    )
                else:
                    ui.label('Nenhuma conta Discord vinculada').style(
                        f'font-size: 13px; color: {C["text_var"]}; margin: 12px 0;'
                    )
                    self.profile_discord_btn = ui.button(
                        icon='login', text='Vincular Discord',
                        on_click=self._link_discord
                    ).classes('discord-btn').style(
                        f'color: white; border-radius: 12px; padding: 12px 24px; '
                        f'font-weight: 600; text-transform: none;'
                    )

                self.profile_discord_status = ui.label('').style(
                    f'font-size: 12px; color: {C["text_var"]}; margin-top: 8px;'
                )

            # ── Account Stats ──
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.2s;')):
                with ui.row().classes('w-full items-center gap-3'):
                    ui.icon('analytics', size='20px').style(f'color: {C["primary"]};')
                    ui.label('Estatisticas da Conta').style(f'font-size: 16px; font-weight: 700; color: {C["text"]};')

                try:
                    total_matches = len(self.db.get_matches(limit=1000))
                except Exception:
                    total_matches = 0

                with ui.row().classes('w-full gap-4').style('margin-top: 16px;'):
                    for label, value, color in [
                        ('Partidas', str(total_matches), C['primary']),
                        ('Discord', 'Vinculado' if self.config.get('discord_id') else 'N/A', C['tertiary']),
                    ]:
                        with ui.column().classes('items-center gap-1').style(
                            f'flex: 1; padding: 16px; border-radius: 12px; '
                            f'background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);'
                        ):
                            ui.label(value).style(
                                f'font-size: 20px; font-weight: 900; color: {color};'
                            )
                            ui.label(label).style(label_caps(f'font-size: 10px; color: {C["text_var"]};'))

            # ── Logout ──
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.25s;')):
                ui.button(
                    icon='logout', text='Desconectar e voltar ao login',
                    on_click=self._logout
                ).style(
                    f'background: rgba(255,180,171,0.1); color: {C["error"]}; '
                    f'border: 1px solid rgba(255,180,171,0.3); border-radius: 12px; '
                    f'padding: 12px 24px; font-weight: 600; text-transform: none; width: 100%;'
                )

    def _save_profile_name(self) -> None:
        name = self.profile_name_input.value.strip()
        if not name:
            ui.notification('Digite um nome', type='warning')
            return
        self.config['player_name'] = name
        config_path = Path('config.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            data['player_name'] = name
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
        ui.notification(f'Nome alterado para {name}!', type='positive')

    def _logout(self) -> None:
        config_path = Path('config.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            data.pop('discord_id', None)
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
        self.config.pop('discord_id', None)
        self.discord_id = None
        ui.navigate.reload()

    # ════════════════════════════════════════════════════════════════════════
    # SETTINGS PAGE
    # ════════════════════════════════════════════════════════════════════════

    def _build_settings_page(self) -> None:
        self._build_top_bar('Settings', 'Preferências do aplicativo')

        with ui.column().classes('w-96 gap-6'):
            # General
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px;')):
                ui.label('Geral').style(f'font-size: 16px; font-weight: 700; margin-bottom: 16px;')

                self.sw_notif = ui.switch(
                    'Notificações',
                    value=self.config.get('notifications', False)
                )

            # Rocket League Nickname (para rank)
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.15s;')):
                ui.label('Rocket League').style(f'font-size: 16px; font-weight: 700; margin-bottom: 8px;')
                ui.label('Nick usado no jogo (Epic Games). Usado para buscar seu rank atual no Player Card.').style(
                    f'font-size: 12px; color: {C["text_var"]}; margin-bottom: 16px;'
                )
                self.rl_nickname_input = ui.input(
                    label='Nick no Rocket League',
                    placeholder='ex: CashBR',
                    value=self.config.get('rl_nickname', '')
                ).classes('w-full')

            # Data Sources Disclaimer
            with ui.card().classes('w-full fade-in').style(glass('padding: 24px; animation-delay: 0.35s;')):
                with ui.row().classes('items-center gap-2').style('margin-bottom: 8px;'):
                    ui.icon('info', size='18px').style(f'color: {C["text_var"]};')
                    ui.label('Fontes de Dados').style(f'font-size: 16px; font-weight: 700;')
                ui.label(
                    'Dados de rank vem de fonte nao-oficial (tracker.gg via RapidAPI) '
                    'e podem ficar temporariamente indisponiveis. '
                    'Quando indisponivel, mostramos o ultimo rank conhecido com indicador visual.'
                ).style(
                    f'font-size: 12px; color: {C["text_dim"]}; line-height: 1.6;'
                )

            # Save
            ui.button('Salvar Configurações').style(
                f'background: {C["primary_container"]}; color: {C["on_primary"]}; '
                f'border-radius: 16px; padding: 14px 24px; font-weight: 700; '
                f'width: 100%; text-transform: none;'
            ).on_click(self._save_settings)

    def _link_discord(self) -> None:
        """Abre o fluxo OAuth2 do Discord para vincular a conta."""
        btn = getattr(self, 'profile_discord_btn', None)
        status = getattr(self, 'profile_discord_status', None)
        if not DISCORD_CLIENT_ID:
            if status:
                status.text = 'Configure DISCORD_CLIENT_ID no .env.'
                status.style(f'color: {C["error"]};')
            return

        if btn:
            btn.disable()
        if status:
            status.text = 'Abrindo navegador do Discord...'
            status.style(f'color: {C["text_var"]};')

        def do_oauth():
            from nicegui import app as ng_app
            try:
                result = start_oauth_flow(timeout=120)
                if result:
                    discord_id = result['discord_id']
                    username = result.get('global_name') or result.get('username', '')
                    print(f"[Link Discord] discord_id={discord_id}, username={username}, global_name={result.get('global_name')}, raw_username={result.get('username')}")
                    self.config['discord_id'] = discord_id
                    self.config['discord_username'] = username
                    config_path = Path('config.json')
                    try:
                        with open(config_path, 'r') as f:
                            data = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        data = {}
                    data['discord_id'] = discord_id
                    data['discord_username'] = username
                    with open(config_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"[Link Discord] Salvo em config.json: {data}")
                    ng_app.schedule(lambda: self._on_discord_linked(discord_id, username))
                else:
                    ng_app.schedule(lambda: self._on_discord_link_failed())
            except Exception as e:
                ng_app.schedule(lambda: self._on_discord_link_error(str(e)))
            finally:
                ng_app.schedule(lambda: btn.enable() if btn else None)

        import threading
        threading.Thread(target=do_oauth, daemon=True).start()

    def _on_discord_linked(self, discord_id: str, username: str) -> None:
        """Callback chamado quando o Discord e vinculado com sucesso."""
        self.config['discord_id'] = discord_id
        self.config['discord_username'] = username
        config_path = Path('config.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data['discord_id'] = discord_id
        data['discord_username'] = username
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)

        status = getattr(self, 'profile_discord_status', None)
        if status:
            status.text = f'Vinculado: {username} ({discord_id})'
            status.style(f'color: {C["tertiary"]};')
        ui.notification(f'Discord vinculado! ID: {discord_id}', type='positive')
        self.page_built[4] = False
        self.page_containers[4].clear()
        with self.page_containers[4]:
            self._build_profile_page()
        self.page_containers[4].style('display: block;')

    def _on_discord_link_failed(self) -> None:
        status = getattr(self, 'profile_discord_status', None)
        if status:
            status.text = 'Falha ao vincular. Tente novamente.'
            status.style(f'color: {C["error"]};')

    def _on_discord_link_error(self, error: str) -> None:
        status = getattr(self, 'profile_discord_status', None)
        if status:
            status.text = f'Erro: {error[:80]}'
            status.style(f'color: {C["error"]};')

    def _save_settings(self) -> None:
        self.config['notifications'] = self.sw_notif.value
        self.config['rl_nickname'] = self.rl_nickname_input.value or ''

        config_path = Path('config.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            data['notifications'] = self.sw_notif.value
            data['rl_nickname'] = self.rl_nickname_input.value or ''
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
