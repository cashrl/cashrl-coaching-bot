"""
RLBotPro - Baseline Sync Module
Sincroniza dados de baseline profissional entre admin e usuários.

IMPORTANTE: Somente a máquina do ADMIN faz sync com Ballchasing.
Usuários comuns (is_admin=False) NUNCA chamam a API do Ballchasing.
Eles recebem o baseline já processado via GitHub (Gist público).

Variáveis de ambiente (apenas no ambiente do admin):
  GIST_ID         - ID do Gist para baseline (pode ser o mesmo de licenças)
  GITHUB_TOKEN    - Token GitHub com permissão de gist (APENAS ADMIN)
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

# Carrega .env do diretório raiz do projeto
load_dotenv(Path(__file__).parent.parent / ".env")

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Discord ID do admin - SOMENTE ESTE ID PODE FAZER SYNC COM BALLCHASING
# Este valor é hardcoded por segurança e não deve ser alterado
ADMIN_DISCORD_ID = "974351584538550282"

GITHUB_API = "https://api.github.com"
# Gist ID para baseline (público, somente leitura para não-admins)
# Será criado pelo admin na primeira execução
BASELINE_GIST_ID = os.environ.get("BASELINE_GIST_ID", "")
# Token GitHub APENAS para o admin (para escrever no Gist)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Cache local do baseline
BASELINE_CACHE_FILE = Path("data/baseline_cache.json")
BASELINE_CACHE_EXPIRY_HOURS = 24  # Re-sync a cada 24h


def is_admin(discord_id: str) -> bool:
    """
    Verifica se o usuário é o admin do sistema.
    
    IMPORTANTE: Somente o admin pode fazer sync com Ballchasing.
    Usuários comuns NUNCA devem chamar a API do Ballchasing.
    """
    return discord_id == ADMIN_DISCORD_ID


def _load_baseline_cache() -> Optional[Dict[str, Any]]:
    """Carrega baseline do cache local."""
    try:
        if BASELINE_CACHE_FILE.exists():
            with open(BASELINE_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Verificar se o cache não expirou
                cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                hours_since = (datetime.now() - cached_at).total_seconds() / 3600
                if hours_since < BASELINE_CACHE_EXPIRY_HOURS:
                    return data
    except (json.JSONDecodeError, IOError, ValueError):
        pass
    return None


def _save_baseline_cache(data: Dict[str, Any]) -> None:
    """Salva baseline no cache local."""
    try:
        BASELINE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["cached_at"] = datetime.now().isoformat()
        with open(BASELINE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError:
        pass


def _fetch_baseline_from_gist() -> Optional[Dict[str, Any]]:
    """
    Busca baseline do Gist público (somente leitura).
    
    IMPORTANTE: Esta função NÃO requer token de autenticação.
    O Gist de baseline é público para que todos os usuários possam baixar.
    """
    if not BASELINE_GIST_ID:
        return None

    api_url = f"{GITHUB_API}/gists/{BASELINE_GIST_ID}"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            content = resp.json()["files"]["pro_baseline.json"]["content"]
            return json.loads(content)
    except (requests.RequestException, KeyError, json.JSONDecodeError):
        pass

    return None


def _upload_baseline_to_gist(baseline_data: Dict[str, Any]) -> bool:
    """
    Faz upload do baseline para o Gist (APENAS ADMIN).
    
    IMPORTANTE: Esta função SÓ deve ser chamada no ambiente do admin.
    Requer GITHUB_TOKEN com permissão de escrita.
    """
    if not BASELINE_GIST_ID or not GITHUB_TOKEN:
        print("[BaselineSync] GIST_ID ou GITHUB_TOKEN não configurado")
        return False

    api_url = f"{GITHUB_API}/gists/{BASELINE_GIST_ID}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
    }

    payload = {
        "files": {
            "pro_baseline.json": {
                "content": json.dumps(baseline_data, indent=2, ensure_ascii=False)
            }
        }
    }

    try:
        resp = requests.patch(api_url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            print("[BaselineSync] Baseline enviado para Gist com sucesso")
            return True
        else:
            print(f"[BaselineSync] Erro ao enviar: {resp.status_code}")
    except requests.RequestException as e:
        print(f"[BaselineSync] Erro de rede ao enviar: {e}")

    return False


def get_pro_baseline(discord_id: str) -> Optional[Dict[str, Any]]:
    """
    Retorna o baseline profissional para o usuário.
    
    Para admin: retorna baseline local (atualizado via Ballchasing).
    Para outros: baixa do Gist público ou usa cache local.
    
    Args:
        discord_id: Discord ID do usuário
        
    Returns:
        Dict com baseline ou None se não disponível
    """
    user_is_admin = is_admin(discord_id)
    
    if user_is_admin:
        # Admin: usar baseline local (atualizado pelo sync com Ballchasing)
        # O sync é feito em background pelo bot de sync
        cache = _load_baseline_cache()
        if cache:
            return cache.get("baseline")
        return None
    else:
        # Não-admin: baixar do Gist público
        # 1. Tentar buscar do Gist
        baseline = _fetch_baseline_from_gist()
        
        if baseline:
            # Salvar no cache local
            _save_baseline_cache({"baseline": baseline})
            return baseline
        
        # 2. Fallback: usar cache local
        cache = _load_baseline_cache()
        if cache:
            print("[BaselineSync] Usando baseline do cache local (offline)")
            return cache.get("baseline")
        
        return None


def export_baseline_for_gist(baseline_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara o baseline para upload ao Gist.
    
    Converte o formato interno do SQLite para um JSON simples
    que pode ser compartilhado com outros usuários.
    
    Args:
        baseline_data: Baseline no formato interno
        
    Returns:
        Dict formatado para o Gist
    """
    # Extrair apenas dados agregados (não replays brutos)
    export = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "admin_id": ADMIN_DISCORD_ID,
        "pro_averages": baseline_data.get("pro_averages", {}),
        "target_ranges": baseline_data.get("target_ranges", {}),
        "skill_weights": baseline_data.get("skill_weights", {}),
        "sample_size": baseline_data.get("sample_size", 0),
        "last_replay_date": baseline_data.get("last_replay_date", ""),
    }
    
    return export


def sync_baseline_as_admin(local_baseline: Dict[str, Any]) -> bool:
    """
    Sincroniza o baseline local com o Gist (APENAS ADMIN).
    
    IMPORTANTE: Esta função SÓ deve ser chamada quando is_admin é True.
    Ela exporta o baseline processado e faz upload para o Gist público.
    
    Args:
        local_baseline: Baseline processado localmente
        
    Returns:
        True se sucesso, False se erro
    """
    # Preparar dados para o Gist
    export_data = export_baseline_for_gist(local_baseline)
    
    # Fazer upload
    success = _upload_baseline_to_gist(export_data)
    
    if success:
        # Atualizar cache local
        _save_baseline_cache({"baseline": export_data})
    
    return success


def create_baseline_gist_if_needed() -> Optional[str]:
    """
    Cria o Gist de baseline se não existir (APENAS ADMIN).
    
    Returns:
        ID do Gist criado ou None se erro
    """
    if not GITHUB_TOKEN:
        print("[BaselineSync] GITHUB_TOKEN não configurado")
        return None

    api_url = f"{GITHUB_API}/gists"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
    }

    initial_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "admin_id": ADMIN_DISCORD_ID,
        "pro_averages": {},
        "target_ranges": {},
        "skill_weights": {},
        "sample_size": 0,
        "last_replay_date": "",
    }

    payload = {
        "description": "RLBotPro - Professional Baseline Data (auto-updated by admin)",
        "public": True,
        "files": {
            "pro_baseline.json": {
                "content": json.dumps(initial_data, indent=2, ensure_ascii=False)
            }
        }
    }

    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 201:
            gist_id = resp.json()["id"]
            print(f"[BaselineSync] Gist criado: {gist_id}")
            print(f"[BaselineSync] Adicione BASELINE_GIST_ID={gist_id} ao .env")
            return gist_id
    except requests.RequestException as e:
        print(f"[BaselineSync] Erro ao criar Gist: {e}")

    return None
