"""
RLBotPro - License Module
Valida licença via Gist do GitHub usando Discord ID do usuário.

Variáveis de ambiente:
  GIST_ID         - ID do Gist privado com as licenças
  GITHUB_TOKEN    - Token GitHub com permissão de gist (opcional,
                    necessário apenas para Gists privados)
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

# Carrega .env do diretório raiz do projeto
load_dotenv(Path(__file__).parent / ".env")

GITHUB_API = "https://api.github.com"
GIST_ID = os.environ.get("GIST_ID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GRACE_PERIOD_DAYS = 7
CACHE_FILE = Path("data/.license_cache.json")


def _load_cache() -> Optional[dict]:
    """Carrega cache local da última checagem bem-sucedida."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _save_cache(discord_id: str, valid: bool, expires: str) -> None:
    """Salva resultado da checagem no cache local."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump({
                "discord_id": discord_id,
                "valid": valid,
                "expires": expires,
                "checked_at": datetime.now().isoformat(),
            }, f, indent=2)
    except IOError:
        pass


def _fetch_licenses_from_gist() -> Optional[dict]:
    """Busca o JSON de licenças do Gist via API do GitHub.

    Usa autenticação via GITHUB_TOKEN para acessar Gists privados.
    """
    if not GIST_ID:
        return None

    api_url = f"{GITHUB_API}/gists/{GIST_ID}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content = resp.json()["files"]["licencas.json"]["content"]
            return json.loads(content)
    except (requests.RequestException, KeyError, json.JSONDecodeError):
        pass

    return None


def validate_license(discord_id: str) -> Tuple[bool, str, Optional[str]]:
    """
    Valida a licença de um usuário.

    Returns:
        (is_valid, message, expires_str)
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Tentar buscar do Gist
    data = _fetch_licenses_from_gist()

    if data is None:
        # Offline: usar cache com grace period
        cache = _load_cache()
        if cache and cache.get("discord_id") == discord_id:
            try:
                checked_at = datetime.fromisoformat(cache["checked_at"])
                days_since = (datetime.now() - checked_at).days
                if days_since <= GRACE_PERIOD_DAYS and cache.get("valid"):
                    return (
                        True,
                        f"Modo offline. Última checagem: {checked_at.strftime('%d/%m/%Y')} "
                        f"(válido por {GRACE_PERIOD_DAYS - days_since} dias restantes).",
                        cache.get("expires"),
                    )
            except (ValueError, KeyError):
                pass

        return (
            False,
            "Não foi possível verificar sua licença (servidor offline).\n\n"
            "Se você já tem licença, tente novamente mais tarde.\n"
            "Se ainda não tem, rode `/criar-id` no Discord do RLBotPro.",
            None,
        )

    licencas = data.get("licencas", {})
    lic = licencas.get(discord_id)

    if not lic:
        return (
            False,
            "Licença não encontrada.\n\n"
            "Rode `/criar-id` no Discord do RLBotPro para criar sua licença.",
            None,
        )

    if lic.get("revogada"):
        _save_cache(discord_id, False, lic.get("expira_em", ""))
        return (
            False,
            "Sua licença foi revogada.\nFale com o admin do RLBotPro.",
            lic.get("expira_em"),
        )

    expira_em = lic.get("expira_em", "")
    if expira_em < today:
        _save_cache(discord_id, False, expira_em)
        return (
            False,
            f"Sua licença expirou em {expira_em}.\n"
            "Renove no Discord ou crie uma nova com `/criar-id`.",
            expira_em,
        )

    _save_cache(discord_id, True, expira_em)
    return (
        True,
        f"Licença válida. Expira em {expira_em}.",
        expira_em,
    )
