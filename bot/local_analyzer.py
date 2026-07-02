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

    def analyze_replay(self, replay_path: str, player_index: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Analisa um replay local e retorna stats extraídas.
        
        Args:
            replay_path: Caminho para o arquivo .replay
            player_index: Índice do jogador para analisar (None = auto-detect)
            
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
            
            # Listar todos os jogadores do lobby
            all_players = self._get_all_players(replay_meta, summed_stats)
            
            # Encontrar nosso jogador
            player_stats = None
            if player_index is not None:
                # Usar índice específico se fornecido
                core = summed_stats.get("modules", {}).get("core", {})
                player_stats_list = core.get("player_stats", [])
                if 0 <= player_index < len(player_stats_list):
                    player_stats = self._build_player_dict(
                        player_index, 
                        player_stats_list[player_index], 
                        player_stats_list, 
                        summed_stats, 
                        replay_meta=replay_meta
                    )
            else:
                # Auto-detectar jogador
                player_stats = self._find_player_stats(replay_meta, summed_stats)
                if not player_stats:
                    player_stats = self._find_player_by_process(replay_meta, summed_stats)
            
            if not player_stats:
                print(f"Jogador {self.player_name} não encontrado no replay")
                return None

            # Extrair metadata
            result = self._extract_metadata(replay_meta)
            duration = result.get("duration_seconds", 300)
            
            # Adicionar lista de todos os jogadores
            result["all_players"] = all_players
            result["selected_player_index"] = player_stats.get("player_index", 0)
            
            # Flag de fallback para identificação do jogador
            result["fallback_used"] = player_stats.get("fallback_used", False)
            result["fallback_reason"] = player_stats.get("fallback_reason", "")
            result["fallback_player_name"] = player_stats.get("name", "") if player_stats.get("fallback_used") else ""
            
            # Extrair stats do jogador
            result.update(self._extract_player_stats(player_stats))
            
            # Extrair boost, movimentação e finalização dos módulos corretos
            idx = player_stats.get("player_index", 0)
            result.update(self._extract_boost_stats(idx, summed_stats, duration))
            result.update(self._extract_movement_stats(idx, summed_stats, duration))
            result.update(self._extract_shooting_stats(idx, summed_stats))
            
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

    def _get_all_players(self, replay_meta: Dict, summed_stats: Dict) -> List[Dict[str, Any]]:
        """
        Retorna lista de todos os jogadores do lobby com seus times.
        
        Returns:
            Lista de dicts: [{"index": 0, "name": "Player1", "team": 0, "platform": "Steam"}, ...]
        """
        players = []
        
        # Obter nomes dos times do replay_meta
        team_zero = replay_meta.get("team_zero", [])
        team_one = replay_meta.get("team_one", [])
        
        # Mapear index → nome/time a partir dos dados de time
        index_to_info = {}
        
        # Team Zero (time 0)
        for i, p in enumerate(team_zero):
            name = p.get("name", f"Player {i}")
            platform = list(p.get("remote_id", {}).keys())[0] if p.get("remote_id") else "Unknown"
            index_to_info[i] = {"name": name, "team": 0, "team_name": "Orange", "platform": platform}
        
        # Team One (time 1) - começa após o team_zero
        offset = len(team_zero)
        for i, p in enumerate(team_one):
            name = p.get("name", f"Player {offset + i}")
            platform = list(p.get("remote_id", {}).keys())[0] if p.get("remote_id") else "Unknown"
            index_to_info[offset + i] = {"name": name, "team": 1, "team_name": "Blue", "platform": platform}
        
        # Se não encontrou nos dados de time, usar core player_stats
        if not index_to_info:
            core = summed_stats.get("modules", {}).get("core", {})
            core_players = core.get("player_stats", [])
            
            for i, ps in enumerate(core_players):
                player_id = ps.get("player_id", {})
                name = f"Player {i}"
                platform = "Unknown"
                
                for p in ["Epic", "PlayStation", "PsyNet", "Steam"]:
                    if p in player_id:
                        platform = p
                        pid = player_id[p]
                        if isinstance(pid, dict):
                            name = pid.get("name", pid.get("online_id", f"Player {i}"))
                        elif isinstance(pid, str):
                            # Tentar encontrar nome no replay_meta
                            for team_key in ["team_zero", "team_one"]:
                                for team_player in replay_meta.get(team_key, []):
                                    remote_id = team_player.get("remote_id", {})
                                    if remote_id.get(p) == pid:
                                        name = team_player.get("name", f"Player {i}")
                                        break
                        break
                
                # Time baseado no índice (0,2,4 = orange; 1,3,5 = blue)
                team = 0 if i % 2 == 0 else 1
                team_name = "Orange" if team == 0 else "Blue"
                index_to_info[i] = {"name": name, "team": team, "team_name": team_name, "platform": platform}
        
        # Construir lista final
        for idx, info in sorted(index_to_info.items()):
            players.append({
                "index": idx,
                "name": info["name"],
                "team": info["team"],
                "team_name": info["team_name"],
                "platform": info["platform"],
            })
        
        return players

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
                            return self._build_player_dict(i, ps, player_stats, replay_meta=replay_meta)
                        elif isinstance(platform_id, dict) and platform_id.get("online_id") == self.player_id:
                            return self._build_player_dict(i, ps, player_stats, replay_meta=replay_meta)
        
        # Procurar por nome se fornecido
        if self.player_name:
            # Construir mapa de platform_id → (index, name) usando dados dos times
            # O problema: core.player_stats NÃO está na mesma ordem que team_zero/team_one
            # Solução: mapear por platform_id, não por índice
            
            id_to_info = {}  # (platform, pid) → (index_in_player_stats, name)
            
            team_zero = replay_meta.get("team_zero", [])
            team_one = replay_meta.get("team_one", [])
            
            # Primeiro, criar mapa de platform_id → nome dos times
            team_id_to_name = {}
            for team_data in [team_zero, team_one]:
                for team_player in team_data:
                    team_name = team_player.get("name", "")
                    remote_id = team_player.get("remote_id", {})
                    for platform, pid in remote_id.items():
                        if isinstance(pid, dict):
                            pid = pid.get("online_id", "")
                        if pid:
                            team_id_to_name[(platform, str(pid))] = team_name
            
            # Agora, mapear cada player_stats ao seu nome usando platform_id
            for i, ps in enumerate(player_stats):
                player_id_data = ps.get("player_id", {})
                for platform, pid in player_id_data.items():
                    if isinstance(pid, dict):
                        pid = pid.get("online_id", "")
                    if pid:
                        key = (platform, str(pid))
                        if key in team_id_to_name:
                            id_to_info[key] = (i, team_id_to_name[key])
            
            # Procurar por nome usando substring matching
            for (platform, pid), (idx, name) in id_to_info.items():
                if name and self.player_name.lower() in name.lower():
                    return self._build_player_dict(idx, player_stats[idx], player_stats, summed_stats, replay_meta=replay_meta)
        
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
        player_dict = self._build_player_dict(candidate_idx, player_stats[candidate_idx], player_stats, summed_stats, replay_meta=replay_meta)
        if player_dict:
            player_dict["fallback_used"] = True
            player_dict["fallback_reason"] = "menos_gols"
        return player_dict

    def _build_player_dict(self, index: int, player_stat: Dict, all_stats: List, summed_stats: Dict = None, replay_meta: Dict = None) -> Dict:
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
        
        # Se o nome for um ID (não um nome de usuário), tentar encontrar nos dados do replay
        # Critérios: "Unknown", ou ID longo (>15 chars), ou contém caracteres não-alfabéticos
        is_id_like = (
            name == "Unknown" or
            (name and len(name) > 15) or
            (name and not name.replace('_', '').replace('-', '').isalpha())
        )
        
        if is_id_like and replay_meta:
            for team_key in ["team_zero", "team_one"]:
                team_players = replay_meta.get(team_key, [])
                for team_player in team_players:
                    team_name = team_player.get("name", "")
                    team_remote_id = team_player.get("remote_id", {})
                    
                    # Verificar se o ID corresponde
                    if team_remote_id.get(platform) == pid or team_remote_id.get(platform) == name:
                        name = team_name
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
            "team_zero": [],
            "team_one": [],
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
            elif key == "MapName":
                result["map_name"] = value
        
        # Extrair jogadores de cada time
        team_zero_data = replay_meta.get("team_zero", [])
        team_one_data = replay_meta.get("team_one", [])
        
        for player in team_zero_data:
            name = player.get("name", "Jogador desconhecido")
            result["team_zero"].append({
                "name": name,
                "platform": list(player.get("remote_id", {}).keys())[0] if player.get("remote_id") else "Unknown",
                "player_id": list(player.get("remote_id", {}).values())[0] if player.get("remote_id") else None,
            })
        
        for player in team_one_data:
            name = player.get("name", "Jogador desconhecido")
            result["team_one"].append({
                "name": name,
                "platform": list(player.get("remote_id", {}).keys())[0] if player.get("remote_id") else "Unknown",
                "player_id": list(player.get("remote_id", {}).values())[0] if player.get("remote_id") else None,
            })
        
        # Determinar game_mode baseado no número REAL de jogadores por time
        # (TeamSize do replay pode estar errado em alguns replays)
        team_size = max(len(result["team_zero"]), len(result["team_one"]))
        if team_size > 0:
            result["game_mode"] = f"{team_size}v{team_size}"
        else:
            # Fallback para TeamSize se não houver jogadores nos dados de time
            for item in replay_meta.get("all_headers", []):
                if item[0] == "TeamSize":
                    result["game_mode"] = f"{item[1]}v{item[1]}"
                    break
        
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
            "player_score": stats.get("score", 0),
            "demos_inflicted": stats.get("demos_inflicted", 0),
            "boost_collected": stats.get("boost_collected", 0),
            "boost_used": stats.get("boost_used", 0),
        }

    def _extract_boost_stats(self, player_index: int, summed_stats: Dict,
                             duration: float = 300.0) -> Dict[str, Any]:
        """Extrai boost completo do módulo boost (não do core)."""
        boost_module = summed_stats.get("modules", {}).get("boost", {})
        boost_players = boost_module.get("player_stats", [])

        if player_index >= len(boost_players):
            return {
                "boost_collected": 0, "boost_used": 0,
                "big_pads_collected": 0, "small_pads_collected": 0,
                "time_boost_100_pct": 0, "time_boost_0_pct": 0,
                "time_boost_low_pct": 0,
            }

        bs = boost_players[player_index].get("stats", {})
        tracked = bs.get("tracked_time", duration)
        if tracked <= 0:
            tracked = duration

        return {
            "boost_collected": bs.get("amount_collected", 0),
            "boost_used": bs.get("amount_used", 0),
            "big_pads_collected": bs.get("big_pads_collected", 0),
            "small_pads_collected": bs.get("small_pads_collected", 0),
            "time_boost_100_pct": round((bs.get("time_hundred_boost", 0) / tracked) * 100, 2),
            "time_boost_0_pct": round((bs.get("time_zero_boost", 0) / tracked) * 100, 2),
            "time_boost_low_pct": round((bs.get("time_boost_0_25", 0) / tracked) * 100, 2),
        }

    def _extract_movement_stats(self, player_index: int, summed_stats: Dict,
                                duration: float = 300.0) -> Dict[str, Any]:
        """Extrai stats de movimentação do módulo movement."""
        mv_module = summed_stats.get("modules", {}).get("movement", {})
        mv_players = mv_module.get("player_stats", [])

        if player_index >= len(mv_players):
            return {}

        ms = mv_players[player_index].get("stats", {})
        tracked = ms.get("tracked_time", duration)
        if tracked <= 0:
            tracked = duration

        avg_speed = ms.get("speed_integral", 0) / tracked if tracked > 0 else 0

        return {
            "avg_speed": round(avg_speed, 2),
            "time_supersonic_pct": round((ms.get("time_supersonic_speed", 0) / tracked) * 100, 2),
            "time_ground_pct": round((ms.get("time_on_ground", 0) / tracked) * 100, 2),
            "aerial_high_pct": round((ms.get("time_high_air", 0) / tracked) * 100, 2),
            "aerial_low_pct": round((ms.get("time_low_air", 0) / tracked) * 100, 2),
            "total_distance": round(ms.get("total_distance", 0), 2),
        }

    def _extract_shooting_stats(self, player_index: int, summed_stats: Dict) -> Dict[str, Any]:
        """Extrai stats de finalização do módulo core."""
        core = summed_stats.get("modules", {}).get("core", {})
        core_players = core.get("player_stats", [])

        if player_index >= len(core_players):
            return {}

        cs = core_players[player_index].get("stats", {})

        return {
            "long_goal_count": cs.get("long_goal_count", 0),
            "medium_goal_count": cs.get("medium_goal_count", 0),
            "short_goal_count": cs.get("short_goal_count", 0),
            "counter_attack_goals": cs.get("counter_attack_goal_count", 0),
            "sustained_pressure_goals": cs.get("sustained_pressure_goal_count", 0),
        }

    def _calculate_advanced_metrics(self, frames_data: Dict, player_index: int) -> Dict[str, Any]:
        """Calcula métricas avançadas dos dados frame-a-frame."""
        result = {}
        
        try:
            # Estrutura real do subtr-actor:
            # frames_data["frame_data"]["players"] = [player0, player1]
            # player = [identity_dict, {"frames": [frame0, frame1, ...]}]
            # frame = {"Data": {"rigid_body": {"location": {"x": ..., "y": ..., "z": ...}}}}
            fd = frames_data.get("frame_data", {})
            players_raw = fd.get("players", [])
            ball_frames = fd.get("ball_data", {}).get("frames", [])
            
            if not players_raw or not ball_frames:
                return result
            
            if player_index >= len(players_raw):
                return result
            
            player_entry = players_raw[player_index]
            # player_entry é [identity_dict, frames_dict]
            if not isinstance(player_entry, list) or len(player_entry) < 2:
                return result
            
            player_frames_list = player_entry[1].get("frames", [])
            
            if not player_frames_list:
                return result
            
            # Calcular distância média à bola
            distances = []
            positions_x = []
            positions_y = []
            
            num_frames = min(len(ball_frames), len(player_frames_list))
            
            for frame_idx in range(num_frames):
                ball_frame = ball_frames[frame_idx]
                player_frame = player_frames_list[frame_idx]
                
                # Pular frames "Empty" do subtr-actor
                if not isinstance(ball_frame, dict) or not isinstance(player_frame, dict):
                    continue
                
                ball_loc = ball_frame.get("Data", {}).get("rigid_body", {}).get("location", {})
                player_loc = player_frame.get("Data", {}).get("rigid_body", {}).get("location", {})
                
                px = player_loc.get("x", 0)
                py = player_loc.get("y", 0)
                bx = ball_loc.get("x", 0)
                by = ball_loc.get("y", 0)
                
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
                
                # Hotspot data (para heatmap)
                result["positions_sample"] = list(zip(positions_x[::10], positions_y[::10]))[:100]

        except Exception as e:
            print(f"Erro ao calcular métricas avançadas: {e}")
            import traceback
            traceback.print_exc()
        
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
