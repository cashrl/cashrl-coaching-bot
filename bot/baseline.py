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
