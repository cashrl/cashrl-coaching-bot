"""
RLBotPro - Baseline System
Analisa múltiplos replays para criar uma baseline de performance.
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

try:
    import subtr_actor
    HAS_SUBTR = True
except ImportError:
    HAS_SUBTR = False


class BaselineSystem:
    """Sistema para criar e gerenciar baselines de performance."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.baselines_dir = self.data_dir / "baselines"
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    def analyze_folder(self, folder_path: str, player_name: str, limit: int = 100) -> Dict[str, Any]:
        """
        Analisa todos os replays de uma pasta e cria uma baseline.
        
        Args:
            folder_path: Caminho da pasta com replays
            player_name: Nome do jogador para identificar
            limit: Número máximo de replays para analisar
            
        Returns:
            Baseline calculada
        """
        if not HAS_SUBTR:
            raise ImportError("subtr-actor-py não está instalado")

        from bot.local_analyzer import LocalReplayAnalyzer
        
        analyzer = LocalReplayAnalyzer(player_name)
        
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Pasta não encontrada: {folder_path}")
        
        replay_files = [f for f in os.listdir(folder_path) if f.endswith(".replay")]
        replay_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)
        
        print(f"Encontrados {len(replay_files)} replays")
        print(f"Analisando até {min(len(replay_files), limit)} replays...")
        
        results = []
        for i, replay_file in enumerate(replay_files[:limit]):
            replay_path = os.path.join(folder_path, replay_file)
            print(f"  [{i+1}/{min(len(replay_files), limit)}] {replay_file[:30]}...")
            
            result = analyzer.analyze_replay(replay_path)
            if result:
                result["file_name"] = replay_file
                results.append(result)
        
        if not results:
            raise ValueError("Nenhum replay foi analisado com sucesso")
        
        # Calcular baseline
        baseline = self._calculate_baseline(results, player_name)
        
        # Salvar baseline
        self._save_baseline(baseline)
        
        print(f"\nBaseline criada com {len(results)} replays!")
        return baseline

    def _calculate_baseline(self, results: List[Dict], player_name: str) -> Dict[str, Any]:
        """Calcula estatísticas médias dos replays."""
        if not results:
            return {}
        
        # Inicializar contadores
        stats = {
            "total_matches": len(results),
            "wins": 0,
            "losses": 0,
            "goals": [],
            "assists": [],
            "saves": [],
            "shots": [],
            "score": [],
            "demos": [],
            "avg_distance_to_ball": [],
            "time_near_ball_pct": [],
            "time_offensive_pct": [],
            "duration_seconds": [],
        }
        
        for result in results:
            # Contar vitórias/derrotas
            score_str = result.get("score", "0-0")
            scores = score_str.split("-")
            if len(scores) == 2:
                try:
                    my_score = int(scores[0])
                    their_score = int(scores[1])
                    if my_score > their_score:
                        stats["wins"] += 1
                    else:
                        stats["losses"] += 1
                except:
                    pass
            
            # Coletar stats
            stats["goals"].append(result.get("goals", 0))
            stats["assists"].append(result.get("assists", 0))
            stats["saves"].append(result.get("saves", 0))
            stats["shots"].append(result.get("shots", 0))
            stats["score"].append(result.get("score", 0))
            stats["demos"].append(result.get("demos_inflicted", 0))
            
            # Métricas avançadas
            if "avg_distance_to_ball" in result:
                stats["avg_distance_to_ball"].append(result["avg_distance_to_ball"])
            if "time_near_ball_pct" in result:
                stats["time_near_ball_pct"].append(result["time_near_ball_pct"])
            if "time_offensive_pct" in result:
                stats["time_offensive_pct"].append(result["time_offensive_pct"])
            if "duration_seconds" in result:
                stats["duration_seconds"].append(result["duration_seconds"])
        
        # Calcular médias
        baseline = {
            "player_name": player_name,
            "created_at": datetime.now().isoformat(),
            "total_matches": stats["total_matches"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "win_rate": round(stats["wins"] / stats["total_matches"] * 100, 1) if stats["total_matches"] > 0 else 0,
            "averages": {},
            "totals": {},
            "min_max": {},
        }
        
        # Calcular médias para cada stat
        for key in ["goals", "assists", "saves", "shots", "score", "demos",
                     "avg_distance_to_ball", "time_near_ball_pct", "time_offensive_pct",
                     "duration_seconds"]:
            values = stats[key]
            if values:
                avg = sum(values) / len(values)
                baseline["averages"][key] = round(avg, 2)
                baseline["totals"][key] = sum(values)
                baseline["min_max"][key] = {
                    "min": min(values),
                    "max": max(values)
                }
        
        return baseline

    def _save_baseline(self, baseline: Dict) -> None:
        """Salva a baseline em arquivo JSON."""
        player_name = baseline.get("player_name", "unknown")
        filename = f"baseline_{player_name.lower().replace(' ', '_')}.json"
        filepath = self.baselines_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
        
        print(f"Baseline salva em: {filepath}")

    def load_baseline(self, player_name: str) -> Optional[Dict]:
        """Carrega a baseline de um jogador."""
        filename = f"baseline_{player_name.lower().replace(' ', '_')}.json"
        filepath = self.baselines_dir / filename
        
        if not filepath.exists():
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def compare_with_baseline(self, match_result: Dict, baseline: Dict) -> Dict[str, Any]:
        """
        Compara uma partida com a baseline.
        
        Args:
            match_result: Resultado da partida atual
            baseline: Baseline do jogador
            
        Returns:
            Comparação com variações
        """
        comparison = {
            "match": {},
            "baseline": baseline.get("averages", {}),
            "variations": {},
            "better": [],
            "worse": [],
        }
        
        # Stats para comparar
        stats_to_compare = ["goals", "assists", "saves", "shots", "score"]
        
        for stat in stats_to_compare:
            match_value = match_result.get(stat, 0)
            baseline_value = baseline.get("averages", {}).get(stat, 0)
            
            comparison["match"][stat] = match_value
            
            if baseline_value > 0:
                variation = ((match_value - baseline_value) / baseline_value) * 100
                comparison["variations"][stat] = round(variation, 1)
                
                if variation > 10:
                    comparison["better"].append(stat)
                elif variation < -10:
                    comparison["worse"].append(stat)
            else:
                comparison["variations"][stat] = 0
        
        return comparison

    def get_all_baselines(self) -> List[Dict]:
        """Retorna todas as baselines salvas."""
        baselines = []
        
        for filepath in self.baselines_dir.glob("baseline_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    baselines.append(json.load(f))
            except:
                continue
        
        return baselines


# ══════════════════════════════════════════════════════════════════════════════
# PRO COMPARISON — Médias profissionais, ranges alvo e cálculo de skill scores
# ══════════════════════════════════════════════════════════════════════════════

# Médias profissionais de referência (RLCS Grand Champion 3v3).
# Baseadas em dados de replays coletados via Ballchasing.
# Formato: {chave_metrica: valor_medio_profissional}
# Nota: métricas de boost/velocidade são por minuto de jogo.
PRO_AVERAGES: Dict[str, float] = {
    "goals_per_min": 1.0,
    "assists_per_min": 0.7,
    "saves_per_min": 0.8,
    "shots_per_min": 2.5,
    "avg_speed": 1550,
    "time_supersonic_pct": 17.0,
    "boost_collected_per_min": 2100,
    "boost_used_per_min": 1850,
    "big_pads_per_min": 8,
    "small_pads_per_min": 25,
    "time_full_boost_pct": 7.0,
    "time_zero_boost_pct": 6.0,
    "time_boost_low_pct": 22.0,
    "aerial_height_high_pct": 8.0,
    "shot_speed_avg": 95,
    "shot_speed_aerial_avg": 105,
    "time_offensive_pct": 48.0,
    "time_defensive_pct": 35.0,
    "avg_distance_to_ball": 550,
    "demos_per_min": 0.15,
    "score_per_min": 150,
}

# Range alvo = meta ± tolerância. Usado para status "Dentro da Meta".
TARGET_RANGES: Dict[str, Dict[str, float]] = {
    "goals_per_min":           {"min": 0.6,  "max": 1.5},
    "assists_per_min":         {"min": 0.4,  "max": 1.1},
    "saves_per_min":           {"min": 0.4,  "max": 1.3},
    "shots_per_min":           {"min": 1.5,  "max": 3.5},
    "avg_speed":               {"min": 1400, "max": 1700},
    "time_supersonic_pct":     {"min": 12.0, "max": 22.0},
    "boost_collected_per_min": {"min": 1700, "max": 2500},
    "boost_used_per_min":      {"min": 1500, "max": 2200},
    "big_pads_per_min":        {"min": 5,    "max": 11},
    "small_pads_per_min":      {"min": 18,   "max": 32},
    "time_full_boost_pct":     {"min": 4.0,  "max": 10.0},
    "time_zero_boost_pct":     {"min": 3.0,  "max": 9.0},
    "time_boost_low_pct":      {"min": 15.0, "max": 30.0},
    "aerial_height_high_pct":  {"min": 4.0,  "max": 12.0},
    "shot_speed_avg":          {"min": 80,   "max": 110},
    "shot_speed_aerial_avg":   {"min": 90,   "max": 120},
    "time_offensive_pct":      {"min": 40.0, "max": 56.0},
    "time_defensive_pct":      {"min": 28.0, "max": 42.0},
    "avg_distance_to_ball":    {"min": 450,  "max": 650},
    "demos_per_min":           {"min": 0.05, "max": 0.25},
    "score_per_min":           {"min": 110,  "max": 200},
}


def get_target_range(metric_key: str) -> Optional[Dict[str, float]]:
    """Retorna o range alvo (min/max) para uma métrica específica."""
    return TARGET_RANGES.get(metric_key)


def _classify_status(value: float, pro_avg: float,
                     target_min: float, target_max: float) -> str:
    """Classifica o status de um valor em relação ao alvo profissional."""
    if value < target_min * 0.7:
        return "muito_baixo"
    if value < target_min:
        return "abaixo"
    if value > target_max * 1.3:
        return "muito_alto"
    if value > target_max:
        return "acima"
    return "dentro_meta"


def compare_to_target(match_data: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Compara cada métrica da partida com o range alvo profissional.

    Retorna lista de dicts:
    [
        {
            "metric_key": "boost_collected_per_min",
            "label": "Boost Coletado/min",
            "value": 1920.0,
            "pro_avg": 2100.0,
            "target_min": 1700,
            "target_max": 2500,
            "unit": "uu/min",
            "status": "abaixo"  # muito_baixo | abaixo | dentro_meta | acima | muito_alto
        },
        ...
    ]
    """
    duration = match_data.get("duration_seconds", 300)
    if duration <= 0:
        duration = 300
    minutes = duration / 60.0

    raw_metrics = [
        ("goals_per_min",           "Gols/min",              match_data.get("goals", 0) / minutes, "un"),
        ("assists_per_min",         "Assistências/min",      match_data.get("assists", 0) / minutes, "un"),
        ("saves_per_min",           "Defesas/min",           match_data.get("saves", 0) / minutes, "un"),
        ("shots_per_min",           "Finalizações/min",      match_data.get("shots", 0) / minutes, "un"),
        ("avg_speed",               "Velocidade Média",      match_data.get("avg_speed", 0), "u/s"),
        ("time_supersonic_pct",     "Tempo Supersônico",     match_data.get("time_supersonic_pct", 0), "%"),
        ("boost_collected_per_min", "Boost Coletado/min",    match_data.get("boost_collected", 0) / minutes, "uu/min"),
        ("boost_used_per_min",      "Boost Usado/min",       match_data.get("boost_used", 0) / minutes, "uu/min"),
        ("big_pads_per_min",        "Big Pads/min",          match_data.get("big_pads_collected", 0) / minutes, "un"),
        ("small_pads_per_min",      "Small Pads/min",        match_data.get("small_pads_collected", 0) / minutes, "un"),
        ("time_full_boost_pct",     "Tempo 100% Boost",      match_data.get("time_boost_100_pct", 0), "%"),
        ("time_zero_boost_pct",     "Tempo 0% Boost",        match_data.get("time_boost_0_pct", 0), "%"),
        ("time_boost_low_pct",      "Tempo <25% Boost",      match_data.get("time_boost_low_pct", 0), "%"),
        ("aerial_height_high_pct",  "Aéreo Alto",            match_data.get("aerial_high_pct", 0), "%"),
        ("shot_speed_avg",          "Vel. Finalização Média", match_data.get("shot_speed_avg", 0), "km/h"),
        ("shot_speed_aerial_avg",   "Vel. Aérea Média",      match_data.get("shot_speed_aerial_avg", 0), "km/h"),
        ("time_offensive_pct",      "Tempo Ataque",          match_data.get("time_offensive_pct", 0), "%"),
        ("time_defensive_pct",      "Tempo Defesa",          match_data.get("time_defensive_pct", 0), "%"),
        ("avg_distance_to_ball",    "Dist. à Bola",          match_data.get("avg_distance_to_ball", 0), "uu"),
        ("demos_per_min",           "Demos/min",             match_data.get("demos_inflicted", 0) / minutes, "un"),
        ("score_per_min",           "Score/min",             match_data.get("player_score", 0) / minutes, "pts"),
    ]

    results = []
    for key, label, value, unit in raw_metrics:
        pro_avg = PRO_AVERAGES.get(key, value)
        rng = TARGET_RANGES.get(key)
        if rng is None:
            continue

        status = _classify_status(value, pro_avg, rng["min"], rng["max"])

        results.append({
            "metric_key": key,
            "label": label,
            "value": round(value, 2),
            "pro_avg": pro_avg,
            "target_min": rng["min"],
            "target_max": rng["max"],
            "unit": unit,
            "status": status,
        })

    return results


def _skill_score(value: float, pro_avg: float, lower_is_better: bool = False) -> float:
    """Converte um valor em score 0-100 (100 = igual ao profissional)."""
    if pro_avg == 0:
        return 50.0
    if lower_is_better:
        ratio = pro_avg / max(value, 0.01)
    else:
        ratio = value / pro_avg
    score = max(0.0, min(100.0, ratio * 100.0))
    return round(score, 1)


def calculate_skill_scores(match_data: Dict[str, float]) -> Dict[str, float]:
    """
    Calcula os 4 scores de competência (0-100) com base nas métricas da partida.

    - Movimentação: velocidade média + tempo supersônico + demos
    - Competência Aérea: tempo aéreo alto + velocidade aérea
    - Posicionamento de Campo: tempo ofensivo + tempo perto da bola + defesa
    - Gestão de Boost: coleta + uso + big pads + tempo 100%
    """
    duration = match_data.get("duration_seconds", 300)
    if duration <= 0:
        duration = 300
    minutes = duration / 60.0

    # Movimentação
    speed = _skill_score(match_data.get("avg_speed", 0), PRO_AVERAGES["avg_speed"])
    supersonic = _skill_score(match_data.get("time_supersonic_pct", 0), PRO_AVERAGES["time_supersonic_pct"])
    demos = _skill_score(match_data.get("demos_inflicted", 0) / minutes, PRO_AVERAGES["demos_per_min"])
    movement = (speed * 0.5 + supersonic * 0.3 + demos * 0.2)

    # Competência Aérea
    aerial_high = _skill_score(match_data.get("aerial_high_pct", 0), PRO_AVERAGES["aerial_height_high_pct"])
    shot_aerial = _skill_score(match_data.get("shot_speed_aerial_avg", 0), PRO_AVERAGES["shot_speed_aerial_avg"])
    aerial = (aerial_high * 0.6 + shot_aerial * 0.4)

    # Posicionamento de Campo
    offensive = _skill_score(match_data.get("time_offensive_pct", 0), PRO_AVERAGES["time_offensive_pct"])
    dist = _skill_score(match_data.get("avg_distance_to_ball", 999), PRO_AVERAGES["avg_distance_to_ball"])
    defensive = _skill_score(match_data.get("time_defensive_pct", 0), PRO_AVERAGES["time_defensive_pct"])
    positioning = (offensive * 0.4 + dist * 0.4 + defensive * 0.2)

    # Gestão de Boost
    collected = _skill_score(match_data.get("boost_collected", 0) / minutes, PRO_AVERAGES["boost_collected_per_min"])
    big_pads = _skill_score(match_data.get("big_pads_collected", 0) / minutes, PRO_AVERAGES["big_pads_per_min"])
    full_boost = _skill_score(match_data.get("time_boost_100_pct", 0), PRO_AVERAGES["time_full_boost_pct"])
    zero_penalty = _skill_score(match_data.get("time_boost_0_pct", 0), PRO_AVERAGES["time_zero_boost_pct"], lower_is_better=True)
    boost_mgmt = (collected * 0.3 + big_pads * 0.25 + full_boost * 0.25 + zero_penalty * 0.2)

    return {
        "movimentacao": round(movement, 1),
        "competencia_aerea": round(aerial, 1),
        "posicionamento_campo": round(positioning, 1),
        "gestao_de_boost": round(boost_mgmt, 1),
    }


def calculate_composite_scores(match_data: Dict[str, float]) -> Dict[str, float]:
    """
    Calcula o score composto geral e por área, normalizado 0-100.
    Peso: Movimentação 30%, Aéreo 25%, Posicionamento 25%, Boost 20%.
    """
    skills = calculate_skill_scores(match_data)
    composite = (
        skills["movimentacao"] * 0.30 +
        skills["competencia_aerea"] * 0.25 +
        skills["posicionamento_campo"] * 0.25 +
        skills["gestao_de_boost"] * 0.20
    )
    return {
        "movimentacao": skills["movimentacao"],
        "competencia_aerea": skills["competencia_aerea"],
        "posicionamento_campo": skills["posicionamento_campo"],
        "gestao_de_boost": skills["gestao_de_boost"],
        "composite": round(composite, 1),
    }


def build_pro_comparison(match_data: Dict[str, float]) -> Dict[str, Any]:
    """
    Função principal: monta a comparação completa jogador vs profissional.

    Retorna:
    {
        "metrics": [  # lista de métricas com status
            {"metric_key": ..., "label": ..., "value": ..., "pro_avg": ...,
             "target_min": ..., "target_max": ..., "unit": ..., "status": ...},
            ...
        ],
        "skill_scores": {  # scores 0-100
            "movimentacao": ...,
            "competencia_aerea": ...,
            "posicionamento_campo": ...,
            "gestao_de_boost": ...,
        },
        "composite": float,  # score composto geral
    }
    """
    metrics = compare_to_target(match_data)
    skills = calculate_skill_scores(match_data)

    composite = (
        skills["movimentacao"] * 0.30 +
        skills["competencia_aerea"] * 0.25 +
        skills["posicionamento_campo"] * 0.25 +
        skills["gestao_de_boost"] * 0.20
    )

    return {
        "metrics": metrics,
        "skill_scores": skills,
        "composite": round(composite, 1),
    }


if __name__ == "__main__":
    # Teste rápido
    system = BaselineSystem()
    
    # Analisar replays
    replay_folder = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "My Games",
        "Rocket League",
        "TAGame",
        "Demos"
    )
    
    print(f"Pasta de replays: {replay_folder}")
    
    if os.path.exists(replay_folder):
        try:
            baseline = system.analyze_folder(replay_folder, "cash the runner", limit=5)
            print("\n=== BASELINE CRIADA ===")
            print(f"Partidas: {baseline['total_matches']}")
            print(f"Vitórias: {baseline['wins']}")
            print(f"Derrotas: {baseline['losses']}")
            print(f"Win Rate: {baseline['win_rate']}%")
            print("\nMédias:")
            for stat, value in baseline.get("averages", {}).items():
                print(f"  {stat}: {value}")
        except Exception as e:
            print(f"Erro: {e}")
    else:
        print("Pasta de replays não encontrada!")
