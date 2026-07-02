"""
RLBotPro - Rocket League Rank Fetcher

Busca o rank atual do jogador por playlist via RapidAPI (Rocket League API).
Fonte de dados: tracker.gg (via intermediario RapidAPI).

AVISO IMPORTANTE: Esta e uma dependencia de terceiro FORA do controle do projeto.
- O servico pode ficar indisponivel, mudar endpoints, ou alterar politicas
- Dados podem ficar defasados ou incompletos
- Rate limits podem ser aplicados
- O app trata falhas com cache local e indicador visual de "dado desatualizado"
"""
import os
import time
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "rocket-league1.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"

# Cache: 20 minutos (rank nao muda a cada segundo)
CACHE_TTL_SECONDS = 20 * 60

# Playlist IDs do Rocket League (valores do tracker.gg)
PLAYLIST_NAMES = {
    "1": "1v1",
    "2": "2v2",
    "3": "3v3",
}


def fetch_current_rank(
    rl_nickname: str,
    platform: str = "epic",
    db=None,
) -> Dict[str, Any]:
    """
    Busca o rank atual do jogador por playlist.

    Args:
        rl_nickname: Nick do jogador no Rocket League
        platform: "epic", "steam", "psn", "xbox" (default: "epic")
        db: instancia Database para cache (opcional)

    Returns:
        {
            "success": True/False,
            "player_name": "NickDoJogador",
            "platform": "epic",
            "ranked": {
                "1v1": {"rank": "Diamond II", "division": 3, "mmr": 1042, "tier": "diamond"},
                "2v2": {"rank": "Champion I", "division": 1, "mmr": 1250, "tier": "champion"},
                "3v3": {"rank": "Platinum III", "division": 2, "mmr": 890, "tier": "platinum"},
            },
            "cached": False,
            "last_updated": "2026-07-01T15:30:00",
            "error": None
        }
    """
    result = {
        "success": False,
        "player_name": "",
        "platform": platform,
        "ranked": {},
        "cached": False,
        "last_updated": None,
        "error": None,
    }

    if not rl_nickname:
        result["error"] = "Nick do Rocket League nao fornecido"
        return result

    if not RAPIDAPI_KEY or RAPIDAPI_KEY == "SUA_RAPIDAPI_KEY_AQUI":
        result["error"] = "RAPIDAPI_KEY nao configurada no .env"
        return result

    # Verificar cache primeiro
    if db:
        cached = db.get_rank_cache(rl_nickname, platform)
        if cached and cached.get("expires_at"):
            try:
                expires = datetime.fromisoformat(cached["expires_at"])
                if datetime.now() < expires:
                    result["cached"] = True
                    result["last_updated"] = cached.get("fetched_at")
                    result["ranked"] = json.loads(cached.get("rank_data_json", "{}"))
                    result["player_name"] = cached.get("player_name", "")
                    result["success"] = True
                    return result
            except (ValueError, json.JSONDecodeError):
                pass

    # Buscar da API
    try:
        api_result = _fetch_from_rapidapi(rl_nickname, platform)
        if api_result:
            result["success"] = True
            result["player_name"] = api_result.get("player_name", "")
            result["ranked"] = api_result.get("ranked", {})
            result["last_updated"] = datetime.now().isoformat()

            # Salvar no cache
            if db:
                db.save_rank_cache(
                    rl_nickname=rl_nickname,
                    platform=platform,
                    player_name=result["player_name"],
                    rank_data=result["ranked"],
                )
        else:
            # Tentar cache antigo (stale) como fallback
            if db:
                cached = db.get_rank_cache(rl_nickname, platform)
                if cached:
                    result["cached"] = True
                    result["last_updated"] = cached.get("fetched_at")
                    result["ranked"] = json.loads(cached.get("rank_data_json", "{}"))
                    result["player_name"] = cached.get("player_name", "")
                    result["success"] = True
                    result["error"] = "Dados de cache (fonte temporariamente indisponivel)"
                    return result
            result["error"] = "Nenhum dado encontrado"
    except Exception as e:
        result["error"] = f"Erro ao buscar rank: {str(e)[:100]}"
        # Fallback para cache stale
        if db:
            cached = db.get_rank_cache(rl_nickname, platform)
            if cached:
                result["cached"] = True
                result["last_updated"] = cached.get("fetched_at")
                result["ranked"] = json.loads(cached.get("rank_data_json", "{}"))
                result["player_name"] = cached.get("player_name", "")
                result["success"] = True

    return result


def _fetch_from_rapidapi(rl_nickname: str, platform: str) -> Optional[Dict[str, Any]]:
    """Faz a requisicao a RapidAPI e parseia a resposta."""
    url = f"{BASE_URL}/ranks/{rl_nickname}"

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }

    params = {
        "platform": platform,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        print("[Rank Fetcher] Timeout ao buscar rank na RapidAPI")
        return None
    except requests.RequestException as e:
        print(f"[Rank Fetcher] Erro HTTP: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"[Rank Fetcher] Resposta: {e.response.text[:200]}")
        return None
    except json.JSONDecodeError:
        print("[Rank Fetcher] Resposta invalida da RapidAPI")
        return None

    return _parse_rapidapi_response(data)


def _parse_rapidapi_response(data: Any) -> Optional[Dict[str, Any]]:
    """Parseia a resposta da RapidAPI em formato padronizado."""
    if not data:
        return None

    result = {
        "player_name": "",
        "ranked": {},
    }

    # A resposta pode ser uma lista ou dict
    if isinstance(data, list):
        if not data:
            return None
        data = data[0] if isinstance(data[0], dict) else None
        if not data:
            return None

    result["player_name"] = data.get("name", "") or data.get("playerName", "")

    # Parsear playlists
    playlists = data.get("ranked", []) or data.get("playlists", []) or data.get("stats", [])

    for playlist in playlists:
        if isinstance(playlist, dict):
            # Extrair nome/tipo da playlist
            playlist_name = (
                playlist.get("name", "")
                or playlist.get("type", "")
                or playlist.get("gameMode", "")
                or playlist.get("playlist", "")
            )
            playlist_name = playlist_name.lower().strip()

            # Mapear para nome padronizado
            standard_name = _normalize_playlist_name(playlist_name)
            if not standard_name:
                continue

            # Extrair rank/MMR
            rank_info = {
                "rank": playlist.get("rank", "") or playlist.get("tier", "") or "",
                "division": playlist.get("division", 0) or playlist.get("div", 0),
                "mmr": playlist.get("rating", 0) or playlist.get("mmr", 0) or playlist.get("score", 0),
                "tier": _extract_tier(playlist),
            }

            # Converter MMR de string "1,042" para int
            if isinstance(rank_info["mmr"], str):
                rank_info["mmr"] = int(rank_info["mmr"].replace(",", "").replace(".", "") or 0)

            result["ranked"][standard_name] = rank_info

    return result if result["ranked"] else None


def _normalize_playlist_name(name: str) -> Optional[str]:
    """Normaliza nome de playlist para formato padronizado."""
    name_lower = name.lower()

    if "duel" in name_lower or "1v1" in name_lower or "1s" in name_lower:
        return "1v1"
    if "doubl" in name_lower or "2v2" in name_lower or "2s" in name_lower:
        return "2v2"
    if "standard" in name_lower or "3v3" in name_lower or "3s" in name_lower:
        return "3v3"

    return None


def _extract_tier(playlist: Dict) -> str:
    """Extrai o tier (bronze, silver, etc.) do rank."""
    rank = (
        playlist.get("rank", "")
        or playlist.get("tier", "")
        or playlist.get("tierName", "")
    ).lower()

    tiers = [
        "bronze", "silver", "gold", "platinum", "diamond",
        "champion", "grand champion", "supersonic legend",
        "ssl",
    ]
    for tier in tiers:
        if tier in rank:
            if tier == "ssl":
                return "supersonic_legend"
            return tier.replace(" ", "_")

    return "unranked"
