"""
RLBotPro - Local Replay Analyzer (subtr-actor)
Analisa replays localmente sem precisar da API do Ballchasing.
"""
import os
import sys
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

try:
    import subtr_actor
    HAS_SUBTR = True
except ImportError:
    HAS_SUBTR = False

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


class LocalReplayAnalyzer:
    """Analisa replays Rocket League localmente usando subtr-actor."""

    def __init__(self, player_name: str, player_id: Optional[str] = None, platform: Optional[str] = None):
        """
        Inicializa o analisador local.
        
        Args:
            player_name: Nome do jogador para identificar nos replays
            player_id: ID do jogador na plataforma (opcional, ex: Steam ID)
            platform: Plataforma do jogador (Steam, Epic, PlayStation, Xbox)
        """
        self.player_name = player_name
        self.player_id = player_id
        self.platform = platform
        if not HAS_SUBTR:
            raise ImportError(
                "subtr-actor-py não está instalado. "
                "Execute: uv pip install subtr-actor-py"
            )

    def analyze_replay(self, replay_path: str) -> Optional[Dict[str, Any]]:
        """
        Analisa um replay local e retorna stats extraídas.
        
        Args:
            replay_path: Caminho para o arquivo .replay
            
        Returns:
            Dicionário com stats ou None se erro
        """
        if not os.path.exists(replay_path):
            print(f"Replay não encontrado: {replay_path}")
            return None

        try:
            # Pegar metadata do replay
            replay_meta_data = subtr_actor.get_replay_meta(replay_path)
            replay_meta = replay_meta_data.get("replay_meta", {})
            
            # Pegar stats somados (core, boost, movement)
            summed_stats = subtr_actor.get_summed_stats(
                replay_path,
                module_names=["core", "boost", "movement"]
            )
            
            # Encontrar nosso jogador
            player_stats = self._find_player_stats(replay_meta, summed_stats)
            if not player_stats:
                # Tentar encontrar por índice (se não encontrar por nome/ID)
                player_stats = self._find_player_by_process(replay_meta, summed_stats)
            
            if not player_stats:
                print(f"Jogador {self.player_name} não encontrado no replay")
                return None

            # Extrair metadata
            result = self._extract_metadata(replay_meta)
            
            # Extrair stats do jogador
            result.update(self._extract_player_stats(player_stats))
            
            # Pegar dados frame-a-frame para métricas avançadas
            try:
                frames_data = subtr_actor.get_replay_frames_data(replay_path)
                if frames_data:
                    advanced = self._calculate_advanced_metrics(frames_data, player_stats.get("player_index", 0))
                    result.update(advanced)
            except Exception as e:
                print(f"Aviso: Não foi possível pegar dados frame-a-frame: {e}")

            return result

        except Exception as e:
            print(f"Erro ao analisar replay: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _find_player_stats(self, replay_meta: Dict, summed_stats: Dict) -> Optional[Dict]:
        """Encontra as stats do nosso jogador no replay."""
        core = summed_stats.get("modules", {}).get("core", {})
        player_stats = core.get("player_stats", [])
        
        # Procurar por player_id se fornecido
        if self.player_id:
            for i, ps in enumerate(player_stats):
                player_id_data = ps.get("player_id", {})
                
                # Verificar se o ID corresponde
                if self.platform:
                    platform_id = player_id_data.get(self.platform)
                    if platform_id:
                        if isinstance(platform_id, str) and platform_id == self.player_id:
                            return self._build_player_dict(i, ps, player_stats)
                        elif isinstance(platform_id, dict) and platform_id.get("online_id") == self.player_id:
                            return self._build_player_dict(i, ps, player_stats)
        
        # Procurar por nome se fornecido
        if self.player_name:
            # Primeiro verificar nos goals para obter nomes
            goals = []
            for item in replay_meta.get("all_headers", []):
                if item[0] == "Goals":
                    goals = item[1]
                    break
            
            # Mapear player_id para nome
            player_names = {}
            for g in goals:
                pname = g.get("PlayerName", "")
                if pname:
                    # Encontrar qual player fez esse goal
                    for i, ps in enumerate(player_stats):
                        pid = ps.get("player_id", {})
                        for platform in ["Epic", "PlayStation", "PsyNet", "Steam"]:
                            if platform in pid:
                                pid_val = pid[platform]
                                if isinstance(pid_val, dict):
                                    # PlayStation tem nome
                                    if pid_val.get("name") == pname:
                                        player_names[i] = pname
                                break
            
            # Procurar por nome
            for i, ps in enumerate(player_stats):
                if i in player_names:
                    pname = player_names[i]
                    if self.player_name.lower() in pname.lower():
                        return self._build_player_dict(i, ps, player_stats, summed_stats)
        
        return None

    def _find_player_by_process(self, replay_meta: Dict, summed_stats: Dict) -> Optional[Dict]:
        """Encontra jogador por processo de eliminação (menos gols = mais provável ser você)."""
        core = summed_stats.get("modules", {}).get("core", {})
        player_stats = core.get("player_stats", [])
        
        if len(player_stats) == 0:
            return None
        
        # Encontrar o jogador com menos gols (provavelmente é você se você é o "fraco")
        min_goals = float('inf')
        candidate_idx = 0
        
        for i, ps in enumerate(player_stats):
            goals = ps.get("stats", {}).get("goals", 0)
            if goals < min_goals:
                min_goals = goals
                candidate_idx = i
        
        print(f"Usando jogador por processo de eliminação (Player {candidate_idx} com {min_goals} gols)")
        return self._build_player_dict(candidate_idx, player_stats[candidate_idx], player_stats, summed_stats)

    def _build_player_dict(self, index: int, player_stat: Dict, all_stats: List, summed_stats: Dict = None) -> Dict:
        """Constrói dicionário com stats do jogador."""
        player_id = player_stat.get("player_id", {})
        
        # Determinar plataforma e nome
        platform = "Unknown"
        name = "Unknown"
        pid = None
        
        for p in ["Epic", "PlayStation", "PsyNet", "Steam"]:
            if p in player_id:
                platform = p
                pid = player_id[p]
                if isinstance(pid, dict):
                    name = pid.get("name", pid.get("online_id", "Unknown"))
                    pid = pid.get("online_id", pid)
                else:
                    name = str(pid)
                break
        
        # Determinar time
        # time_zero = team 0, time_one = team 1
        # player_stats é uma lista, precisamos descobrir qual time
        core = summed_stats.get("modules", {}).get("core", {}) if summed_stats else {}
        
        return {
            "player_index": index,
            "platform": platform,
            "player_id": pid,
            "name": name if name != "Unknown" else self.player_name,
            "stats": player_stat.get("stats", {})
        }

    def _extract_metadata(self, replay_meta: Dict) -> Dict[str, Any]:
        """Extrai metadata do replay."""
        result = {
            "map_name": "Unknown",
            "game_mode": "Unknown",
            "team_zero_score": 0,
            "team_one_score": 0,
            "duration_seconds": 0,
            "timestamp": "",
        }
        
        for item in replay_meta.get("all_headers", []):
            key = item[0]
            value = item[1]
            
            if key == "Team0Score":
                result["team_zero_score"] = value
            elif key == "Team1Score":
                result["team_one_score"] = value
            elif key == "TotalSecondsPlayed":
                result["duration_seconds"] = value
            elif key == "MatchStartEpoch":
                result["timestamp"] = datetime.fromtimestamp(int(value)).isoformat() if value else ""
            elif key == "TeamSize":
                result["game_mode"] = f"{value}v{value}"
            elif key == "MapName":
                result["map_name"] = value
        
        # Calcular resultado para o jogador
        result["score"] = f"{result['team_zero_score']}-{result['team_one_score']}"
        
        return result

    def _extract_player_stats(self, player_stat: Dict) -> Dict[str, Any]:
        """Extrai stats do jogador encontradas."""
        stats = player_stat.get("stats", {})
        
        return {
            "player_name": player_stat.get("name", self.player_name),
            "platform": player_stat.get("platform", "Unknown"),
            "player_id": player_stat.get("player_id"),
            "goals": stats.get("goals", 0),
            "assists": stats.get("assists", 0),
            "saves": stats.get("saves", 0),
            "shots": stats.get("shots", 0),
            "score": stats.get("score", 0),
            "demos_inflicted": stats.get("demos_inflicted", 0),
            "boost_collected": stats.get("boost_collected", 0),
            "boost_used": stats.get("boost_used", 0),
        }

    def _calculate_advanced_metrics(self, frames_data: Dict, player_index: int) -> Dict[str, Any]:
        """Calcula métricas avançadas dos dados frame-a-frame."""
        result = {}
        
        try:
            # Pegar dados do jogador e da bola
            player_frames = frames_data.get("players", [])
            ball_frames = frames_data.get("ball", [])
            
            if not player_frames or not ball_frames:
                return result
            
            if player_index >= len(player_frames):
                return result
            
            player_data = player_frames[player_index]
            
            # Calcular distância média à bola
            distances = []
            positions_x = []
            positions_y = []
            
            num_frames = min(len(ball_frames), len(player_data))
            
            for frame_idx in range(num_frames):
                ball = ball_frames[frame_idx]
                player = player_data[frame_idx]
                
                # Pegar posições (colunas 0-2 são x, y, z)
                if len(player) >= 3 and len(ball) >= 3:
                    px, py = player[0], player[1]
                    bx, by = ball[0], ball[1]
                    
                    dx = bx - px
                    dy = by - py
                    dist = (dx**2 + dy**2) ** 0.5
                    distances.append(dist)
                    
                    positions_x.append(px)
                    positions_y.append(py)
            
            if distances:
                result["avg_distance_to_ball"] = round(sum(distances) / len(distances), 2)
                result["time_near_ball_pct"] = round((sum(1 for d in distances if d < 300) / len(distances)) * 100, 2)
            
            if positions_x:
                # Calcular tempo no ataque vs defesa (campo positivo = ataque)
                time_offensive = sum(1 for x in positions_x if x > 0)
                result["time_offensive_pct"] = round((time_offensive / len(positions_x)) * 100, 2)
                
                # Hotspot data (para heatmap futura)
                result["positions_sample"] = list(zip(positions_x[::10], positions_y[::10]))[:100]

        except Exception as e:
            print(f"Erro ao calcular métricas avançadas: {e}")
        
        return result

    def analyze_replay_folder(self, folder_path: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Analisa todos os replays em uma pasta.
        
        Args:
            folder_path: Caminho da pasta com replays
            limit: Número máximo de replays para analisar
            
        Returns:
            Lista de resultados de análise
        """
        if not os.path.exists(folder_path):
            print(f"Pasta não encontrada: {folder_path}")
            return []
        
        replay_files = [f for f in os.listdir(folder_path) if f.endswith(".replay")]
        replay_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)
        
        results = []
        for i, replay_file in enumerate(replay_files[:limit]):
            replay_path = os.path.join(folder_path, replay_file)
            print(f"Analisando {i+1}/{min(len(replay_files), limit)}: {replay_file}")
            
            result = self.analyze_replay(replay_path)
            if result:
                result["file_name"] = replay_file
                result["file_path"] = replay_path
                results.append(result)
        
        return results


def get_default_replay_folder() -> str:
    """Retorna a pasta padrão de replays do Rocket League no Windows."""
    return os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "My Games",
        "Rocket League",
        "TAGame",
        "Demos"
    )


if __name__ == "__main__":
    # Teste rápido
    analyzer = LocalReplayAnalyzer("cash the runner")
    replay_folder = get_default_replay_folder()
    
    print(f"Pasta de replays: {replay_folder}")
    print(f"Subtr-actor disponível: {HAS_SUBTR}")
    
    if os.path.exists(replay_folder):
        replay_files = [f for f in os.listdir(replay_folder) if f.endswith(".replay")]
        print(f"Replays encontrados: {len(replay_files)}")
        
        if replay_files:
            # Analisar o mais recente
            latest = max(replay_files, key=lambda x: os.path.getmtime(os.path.join(replay_folder, x)))
            print(f"\nAnalisando: {latest}")
            result = analyzer.analyze_replay(os.path.join(replay_folder, latest))
            
            if result:
                print("\n=== RESULTADO DA ANÁLISE ===")
                for k, v in result.items():
                    if k != "positions_sample":  # Pular dados de posição
                        print(f"{k}: {v}")
    else:
        print("Pasta de replays não encontrada!")
