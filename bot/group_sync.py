"""
RLBotPro - Group Sync Module
Permite exportar/importar resumos semanais JSON para comparação entre amigos.
Cada instância local exporta métricas agregadas (sem dado sensível) para uma
pasta compartilhada (Google Drive/Dropbox) ou GitHub Gist privado.
"""
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


def export_weekly_summary(db, player_name: str, output_path: str = "data/group_summaries") -> Optional[str]:
    """
    Exporta resumo semanal do jogador como JSON pequeno.

    Args:
        db: Instância de Database
        player_name: Nome do jogador
        output_path: Pasta de saída (local ou pasta sincronizada)

    Returns:
        Caminho do arquivo gerado ou None se erro
    """
    try:
        os.makedirs(output_path, exist_ok=True)

        # Últimos 7 dias
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT * FROM matches WHERE date >= ? ORDER BY date DESC",
            (cutoff,),
        )
        recent = [dict(row) for row in cursor.fetchall()]

        if not recent:
            print("Nenhuma partida nos últimos 7 dias para exportar.")
            return None

        # Métricas agregadas (sem dado sensível)
        total = len(recent)
        wins = sum(1 for m in recent if m.get('result') == 'win')
        losses = total - wins

        boost_values = [m.get('boost_avg', 0) or 0 for m in recent if m.get('boost_avg')]
        speed_values = [m.get('avg_speed', 0) or 0 for m in recent if m.get('avg_speed')]
        dist_values = [m.get('avg_distance_to_ball', 0) or 0 for m in recent if m.get('avg_distance_to_ball')]
        proximity_values = [m.get('proximity_score', 0) or 0 for m in recent if m.get('proximity_score')]

        summary = {
            "version": 1,
            "player_id": hashlib.md5(player_name.encode()).hexdigest()[:8],
            "player_name": player_name,
            "week_start": cutoff[:10],
            "week_end": datetime.now().strftime("%Y-%m-%d"),
            "exported_at": datetime.now().isoformat(),
            "matches": {
                "total": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            },
            "averages": {
                "boost_avg": round(sum(boost_values) / len(boost_values), 1) if boost_values else 0,
                "avg_speed": round(sum(speed_values) / len(speed_values), 1) if speed_values else 0,
                "avg_distance_to_ball": round(sum(dist_values) / len(dist_values), 1) if dist_values else 0,
                "proximity_score": round(sum(proximity_values) / len(proximity_values), 1) if proximity_values else 0,
            },
        }

        # Detectar momentos de erro (se disponível)
        try:
            cursor.execute(
                "SELECT category, COUNT(*) as cnt FROM detected_moments "
                "WHERE timestamp >= ? GROUP BY category ORDER BY cnt DESC LIMIT 5",
                (cutoff,),
            )
            moment_counts = {row['category']: row['cnt'] for row in cursor.fetchall()}
            if moment_counts:
                summary["error_moments"] = moment_counts
        except Exception:
            pass

        filename = f"{player_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(output_path, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"Resumo semanal exportado: {filepath}")
        return filepath

    except Exception as e:
        print(f"Erro ao exportar resumo semanal: {e}")
        return None


def import_group_summaries(path_or_url: str) -> List[Dict[str, Any]]:
    """
    Lê resumos semanais de outros jogadores de uma pasta local ou Gist.

    Args:
        path_or_url: Caminho local ou URL de Gist do GitHub

    Returns:
        Lista de resumos carregados
    """
    summaries = []

    if path_or_url.startswith(('http://', 'https://')):
        # TODO: Suporte a GitHub Gist (precisa de token)
        print("Suporte a Gist ainda não implementado. Use uma pasta local.")
        return summaries

    # Pasta local
    folder = Path(path_or_url)
    if not folder.exists():
        print(f"Pasta não encontrada: {path_or_url}")
        return summaries

    for json_file in folder.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('version') == 1 and 'player_name' in data:
                summaries.append(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Arquivo inválido ignorado: {json_file.name} ({e})")

    print(f"Carregados {len(summaries)} resumo(s) de grupo.")
    return summaries


def compare_group(summaries: List[Dict[str, Any]], current_player: str) -> Dict[str, Any]:
    """
    Monta comparação simples entre jogadores do grupo.
    Foco em "curiosidade de grupo", não ranking competitivo.

    Args:
        summaries: Lista de resumos de grupo
        current_player: Nome do jogador atual (para excluir da lista)

    Returns:
        Dict com comparações: who_improved, best_winrate, closest_to_pro, etc.
    """
    if len(summaries) < 2:
        return {"error": "Precisa de pelo menos 2 jogadores para comparar."}

    others = [s for s in summaries if s.get('player_name') != current_player]
    me = next((s for s in summaries if s.get('player_name') == current_player), None)

    result = {
        "players": [s.get('player_name', '?') for s in summaries],
        "stats": [],
    }

    for s in summaries:
        matches = s.get('matches', {})
        avgs = s.get('averages', {})
        result["stats"].append({
            "name": s.get('player_name', '?'),
            "win_rate": matches.get('win_rate', 0),
            "total_matches": matches.get('total', 0),
            "proximity_score": avgs.get('proximity_score', 0),
            "avg_speed": avgs.get('avg_speed', 0),
            "boost_avg": avgs.get('boost_avg', 0),
        })

    # Melhor win rate
    if result["stats"]:
        best = max(result["stats"], key=lambda x: x['win_rate'])
        result["best_win_rate"] = {"name": best['name'], "value": best['win_rate']}

        # Mais partidas jogadas
        most_active = max(result["stats"], key=lambda x: x['total_matches'])
        result["most_active"] = {"name": most_active['name'], "value": most_active['total_matches']}

        # Maior proximidade ao pro
        closest_pro = max(result["stats"], key=lambda x: x['proximity_score'])
        result["closest_to_pro"] = {"name": closest_pro['name'], "value": closest_pro['proximity_score']}

    return result
