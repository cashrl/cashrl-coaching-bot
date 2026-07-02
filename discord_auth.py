"""
RLBotPro - Discord OAuth2 Authentication Module (PKCE)

Usa PKCE (Proof Key for Code Exchange) para NAO enviar client_secret.
Isso e seguro para apps desktop distribuidos — o secret nunca sai da maquina.

Porta fixa: 47182
Redirect URI: http://localhost:47182/callback
"""
import os
import hashlib
import base64
import secrets
import webbrowser
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

import requests
from dotenv import load_dotenv
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")

DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")

DISCORD_API = "https://discord.com/api/v10"
OAUTH_AUTHORIZE = "https://discord.com/api/oauth2/authorize"
OAUTH_TOKEN = "https://discord.com/api/oauth2/token"

OAUTH_PORT = 47182
OAUTH_HOST = "localhost"
REDIRECT_URI = f"http://{OAUTH_HOST}:{OAUTH_PORT}/callback"


# ---------------------------------------------------------------------------
# PKCE helpers (RFC 7636)
# ---------------------------------------------------------------------------

def _generate_code_verifier() -> str:
    """Gera code_verifier aleatório (43-128 chars, URL-safe)."""
    return secrets.token_urlsafe(64)


def _generate_code_challenge(verifier: str) -> str:
    """SHA-256 do verifier, base64url sem padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Callback storage
# ---------------------------------------------------------------------------

class _OAuthCallback:
    """Armazena o resultado do callback OAuth2."""

    def __init__(self):
        self.code: Optional[str] = None
        self.received_state: Optional[str] = None
        self.error: Optional[str] = None
        self.received = threading.Event()

    def set_code(self, code: str, state: str) -> None:
        self.code = code
        self.received_state = state
        self.received.set()

    def set_error(self, error: str) -> None:
        self.error = error
        self.received.set()


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

_SUCCESS_HTML = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>RLBotPro - Sucesso</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0a0b0f; color: #e1e2ec;
      font-family: 'Inter', -apple-system, sans-serif;
      display: flex; align-items: center; justify-content: center;
      height: 100vh;
    }
    .card {
      text-align: center; padding: 48px; border-radius: 16px;
      background: #1a1b26; border: 1px solid #2a2b3d;
      max-width: 400px;
    }
    .icon { font-size: 56px; margin-bottom: 16px; }
    h2 { color: #4ade80; font-size: 22px; margin-bottom: 8px; }
    p  { color: #8c909f; font-size: 14px; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">&#9989;</div>
    <h2>Discord vinculado com sucesso!</h2>
    <p>Voce pode fechar esta aba e voltar ao RLBotPro.</p>
  </div>
</body>
</html>"""

_ERROR_HTML = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>RLBotPro - Erro</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0a0b0f; color: #e1e2ec;
      font-family: 'Inter', -apple-system, sans-serif;
      display: flex; align-items: center; justify-content: center;
      height: 100vh;
    }}
    .card {{
      text-align: center; padding: 48px; border-radius: 16px;
      background: #1a1b26; border: 1px solid #2a2b3d;
      max-width: 400px;
    }}
    .icon {{ font-size: 56px; margin-bottom: 16px; }}
    h2 {{ color: #ffb4ab; font-size: 22px; margin-bottom: 8px; }}
    p  {{ color: #8c909f; font-size: 14px; margin-top: 8px; }}
    .detail {{ color: #5a5b6d; font-size: 12px; margin-top: 12px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">&#10060;</div>
    <h2>Erro na autorizacao</h2>
    <p>{error}</p>
    <p class="detail">Feche esta aba e tente novamente.</p>
  </div>
</body>
</html>"""


class _OAuthHandler(BaseHTTPRequestHandler):
    """Handler HTTP para receber o callback do Discord OAuth2."""

    callback: Optional[_OAuthCallback] = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if "error" in params:
            error = params["error"][0]
            _OAuthCallback.set_error(self.callback, error)
            self.wfile.write(_ERROR_HTML.format(error=error).encode())
            return

        if "code" not in params:
            _OAuthCallback.set_error(self.callback, "Codigo nao encontrado")
            self.wfile.write(_ERROR_HTML.format(error="Codigo nao encontrado").encode())
            return

        code = params["code"][0]
        state = params.get("state", [None])[0]

        _OAuthCallback.set_code(self.callback, code, state)
        self.wfile.write(_SUCCESS_HTML.encode())

    def log_message(self, format: str, *args) -> None:
        pass


# ---------------------------------------------------------------------------
# Token exchange + user info (PKCE, sem client_secret)
# ---------------------------------------------------------------------------

def _exchange_code(code: str, code_verifier: str) -> Optional[dict]:
    """Troca code por access token usando PKCE.

    Com PKCE NAO enviamos client_secret — seguro para apps desktop.
    """
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        resp = requests.post(OAUTH_TOKEN, data=data, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[OAuth] Erro ao trocar code por token: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[OAuth] Resposta Discord: {exc.response.text}")
        return None


def _fetch_user_info(access_token: str) -> Optional[dict]:
    """Busca info do usuario em /users/@me."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(f"{DISCORD_API}/users/@me", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[OAuth] Erro ao buscar usuario: {exc}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_oauth_flow(timeout: int = 120) -> Optional[dict]:
    """
    Fluxo completo OAuth2 + PKCE.

    Returns:
        {"discord_id": "...", "username": "...", "global_name": "...", "avatar_url": "..."}
        ou None em caso de erro/timeout.
    """
    if not DISCORD_CLIENT_ID:
        print("[OAuth] DISCORD_CLIENT_ID nao configurado no .env")
        return None

    # --- PKCE ---
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)

    # --- State (CSRF) ---
    state = secrets.token_urlsafe(32)

    # --- Callback handler ---
    callback = _OAuthCallback()
    _OAuthHandler.callback = callback

    # --- Servidor local ---
    try:
        server = HTTPServer((OAUTH_HOST, OAUTH_PORT), _OAuthHandler)
    except OSError:
        print(f"[OAuth] Porta {OAUTH_PORT} ja em uso. Feche outro programa.")
        return None

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # --- URL de autorizacao ---
        params = {
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "identify",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{OAUTH_AUTHORIZE}?{urllib.parse.urlencode(params)}"

        # Log diagnostico
        print(f"[OAuth] Redirect URI (deve bater com o portal): {REDIRECT_URI}")
        print(f"[OAuth] Abrindo navegador...")
        print(f"[OAuth] URL completa:\n  {auth_url}")

        # --- Abrir navegador ---
        webbrowser.open(auth_url)

        # --- Esperar callback ---
        print(f"[OAuth] Aguardando autorizacao (timeout {timeout}s)...")
        if not callback.received.wait(timeout=timeout):
            print("[OAuth] Timeout — usuario nao autorizou")
            return None

        if callback.error:
            print(f"[OAuth] Discord retornou erro: {callback.error}")
            return None

        # --- Validar state ---
        if callback.received_state != state:
            print("[OAuth] State mismatch — possivel CSRF")
            return None

        # --- Trocar code por token (PKCE, sem client_secret) ---
        token_data = _exchange_code(callback.code, code_verifier)
        if not token_data or "access_token" not in token_data:
            print("[OAuth] Falha ao obter access token")
            return None

        # --- Buscar usuario ---
        user_info = _fetch_user_info(token_data["access_token"])
        if not user_info or "id" not in user_info:
            print("[OAuth] Falha ao buscar info do usuario")
            return None

        avatar_url = ""
        if user_info.get("avatar"):
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/"
                f"{user_info['id']}/{user_info['avatar']}.png"
            )

        result = {
            "discord_id": user_info["id"],
            "username": user_info.get("username", ""),
            "global_name": user_info.get("global_name", ""),
            "avatar_url": avatar_url,
        }
        print(f"[OAuth] Sucesso! {result['username']} (ID: {result['discord_id']})")
        return result

    finally:
        server.shutdown()
