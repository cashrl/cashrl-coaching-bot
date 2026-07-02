"""
RLBotPro - Moment Detector
Detecta momentos categorizados (erros/decisões) frame-a-frame usando dados do subtr-actor.

Categorias implementadas (viáveis com dados do subtr-actor ndarray):
  hesitacao             - jogador perto da bola mas com velocidade muito baixa por tempo prolongado
  boost_baixo_perigoso  - boost < 14% com bola vindo na direção do jogador
  defesa_fora_posicao   - adversário com oportunidade e jogador longe do gol próprio
  rush_sem_boost        - velocidade alta em direção à bola com boost < 20%
  posicao_ruim          - muito longe da bola por tempo prolongado
  recovery_lenta        - caiu no chão e demora pra levantar
"""
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import subtr_actor
    HAS_SUBTR = True
except ImportError:
    HAS_SUBTR = False


# ══════════════════════════════════════════════════════════════════════════════
# LIMITES DO JOGO (Unreal Units / subtr-actor units)
# ══════════════════════════════════════════════════════════════════════════════

FIELD_X_HALF = 4200
FIELD_Y_HALF = 5100

BOOST_MAX_RAW = 255
BOOST_LOW = 36          # ~14 %
BOOST_RUSH = 51         # ~20 %

VELOCITY_STOPPED = 100
VELOCITY_SLOW = 500

DIST_BALL_CLOSE = 500
DIST_BALL_FAR = 1500
DIST_CRITICAL = 2000

HESITATION_MIN_FRAMES = 6     # 0.6 s a 10 fps
POSITIONING_BAD_FRAMES = 10
RECOVERY_SLOW_FRAMES = 8


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedMoment:
    """Um momento detectado no replay."""
    timestamp: float
    frame_index: int
    category: str
    context: Dict[str, Any]
    replay_id: str = ""
    player_name: str = ""
    severity: str = "normal"        # normal | alto | critico


# ══════════════════════════════════════════════════════════════════════════════
# DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class MomentDetector:
    """
    Detecta momentos categorizados em replays usando ndarray do subtr-actor.

    Exemplo:
        det = MomentDetector()
        moments = det.detect_from_replay("replay.replay", player_name="Zen")
    """

    GLOBAL_FEATURES = ["BallRigidBody", "SecondsRemaining"]
    PLAYER_FEATURES = ["PlayerRigidBody", "PlayerBoost"]

    def __init__(self):
        if not HAS_SUBTR:
            raise ImportError("subtr-actor-py não instalado")
        if not HAS_NUMPY:
            raise ImportError("numpy não instalado")

    # ── PUBLIC ─────────────────────────────────────────────────────────────

    def detect_from_replay(
        self,
        replay_path: str,
        player_name: str = "",
        player_index: Optional[int] = None,
        fps: float = 10.0,
    ) -> List[DetectedMoment]:
        if not os.path.exists(replay_path):
            print(f"Replay não encontrado: {replay_path}")
            return []

        try:
            meta, ndarray = subtr_actor.get_ndarray_with_info_from_replay_filepath(
                replay_path,
                global_feature_adders=self.GLOBAL_FEATURES,
                player_feature_adders=self.PLAYER_FEATURES,
                fps=fps,
                dtype="float32",
            )

            headers = subtr_actor.get_column_headers(
                global_feature_adders=self.GLOBAL_FEATURES,
                player_feature_adders=self.PLAYER_FEATURES,
            )

            col_map = self._build_col_map(headers)
            if not col_map:
                return []

            # A forma do ndarray é (frames, features) onde features =
            #   global_cols + num_players * player_cols
            # Precisamos calcular quantos globals e quantos por player.
            num_frames = ndarray.shape[0]

            global_header = headers.get("global_headers", {})
            player_header = headers.get("player_headers", {})

            num_global_cols = sum(
                len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 1
                for v in global_header.values()
            )
            num_player_cols = sum(
                len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 1
                for v in player_header.values()
            )

            # Determinar num_players a partir do ndarray
            total_cols = ndarray.shape[1] if ndarray.ndim == 2 else 0
            if num_player_cols > 0 and total_cols > num_global_cols:
                num_players = (total_cols - num_global_cols) // num_player_cols
            else:
                num_players = 1

            if player_index is None:
                player_index = 0

            replay_name = os.path.basename(replay_path)
            raw_moments: List[DetectedMoment] = []

            # Estado acumulado para detecção de hesitação
            hesit_counter = 0
            posbad_counter = 0
            recovery_counter = 0

            for fi in range(num_frames):
                frame = ndarray[fi]
                ts = round(fi / fps, 3)

                # Extrair seções: globals, player_i, opponents
                ball_data = frame[:num_global_cols] if num_global_cols > 0 else frame[:6]
                plr_start = num_global_cols + player_index * num_player_cols
                plr_end = plr_start + num_player_cols
                plr_data = frame[plr_start:plr_end]

                ball = self._parse_ball(ball_data, col_map)
                plr = self._parse_player(plr_data, col_map)

                if not plr or not ball:
                    continue

                # Calcular distância à bola
                plr["dist_ball"] = ((plr["px"] - ball["bx"])**2 +
                                    (plr["py"] - ball["by"])**2) ** 0.5

                # Oponentes
                opps = []
                for oi in range(num_players):
                    if oi == player_index:
                        continue
                    o_start = num_global_cols + oi * num_player_cols
                    o_end = o_start + num_player_cols
                    op = self._parse_player(frame[o_start:o_end], col_map)
                    if op:
                        opps.append(op)

                # ── Hesitação ──
                close_to_ball = plr["dist_ball"] < DIST_BALL_CLOSE
                is_slow = plr["speed"] < VELOCITY_STOPPED
                if close_to_ball and is_slow:
                    hesit_counter += 1
                else:
                    if hesit_counter >= HESITATION_MIN_FRAMES:
                        raw_moments.append(DetectedMoment(
                            timestamp=ts, frame_index=fi,
                            category="hesitacao",
                            context={
                                "duracao_frames": hesit_counter,
                                "distancia_bola": round(plr["dist_ball"]),
                                "velocidade": round(plr["speed"]),
                                "boost_pct": round(plr["boost"] / BOOST_MAX_RAW * 100),
                                "pos_x": round(plr["px"]), "pos_y": round(plr["py"]),
                            },
                            severity="alto" if hesit_counter >= 12 else "normal",
                        ))
                    hesit_counter = 0

                # ── Boost baixo perigoso ──
                if plr["boost"] < BOOST_LOW and plr["dist_ball"] < DIST_BALL_FAR:
                    severity = "critico" if plr["dist_ball"] < DIST_BALL_CLOSE else "alto"
                    raw_moments.append(DetectedMoment(
                        timestamp=ts, frame_index=fi,
                        category="boost_baixo_perigoso",
                        context={
                            "boost_pct": round(plr["boost"] / BOOST_MAX_RAW * 100),
                            "distancia_bola": round(plr["dist_ball"]),
                            "velocidade": round(plr["speed"]),
                            "pos_x": round(plr["px"]), "pos_y": round(plr["py"]),
                            "ball_x": round(ball["bx"]), "ball_y": round(ball["by"]),
                        },
                        severity=severity,
                    ))

                # ── Defesa fora de posição ──
                if opps and ball["bx"] > FIELD_X_HALF - 2000:
                    # Bola está no terço ofensivo do adversário = perigo pro nosso gol
                    own_goal_dist = abs(plr["px"] + FIELD_X_HALF)  # distância ao gol próprio (x negativo)
                    if own_goal_dist > 3000:
                        raw_moments.append(DetectedMoment(
                            timestamp=ts, frame_index=fi,
                            category="defesa_fora_posicao",
                            context={
                                "distancia_gol_proprio": round(own_goal_dist),
                                "boost_pct": round(plr["boost"] / BOOST_MAX_RAW * 100),
                                "pos_x": round(plr["px"]), "pos_y": round(plr["py"]),
                                "ball_x": round(ball["bx"]), "ball_y": round(ball["by"]),
                            },
                            severity="alto",
                        ))

                # ── Rush sem boost ──
                if plr["speed"] > VELOCITY_SLOW and plr["boost"] < BOOST_RUSH:
                    # Indo rápido mas sem boost = possível rush imprudente
                    if plr["dist_ball"] < DIST_BALL_FAR:
                        raw_moments.append(DetectedMoment(
                            timestamp=ts, frame_index=fi,
                            category="rush_sem_boost",
                            context={
                                "velocidade": round(plr["speed"]),
                                "boost_pct": round(plr["boost"] / BOOST_MAX_RAW * 100),
                                "distancia_bola": round(plr["dist_ball"]),
                                "pos_x": round(plr["px"]), "pos_y": round(plr["py"]),
                            },
                            severity="normal",
                        ))

                # ── Posição ruim (muito longe da bola) ──
                if plr["dist_ball"] > DIST_CRITICAL:
                    posbad_counter += 1
                else:
                    if posbad_counter >= POSITIONING_BAD_FRAMES:
                        raw_moments.append(DetectedMoment(
                            timestamp=ts, frame_index=fi,
                            category="posicao_ruim",
                            context={
                                "duracao_frames": posbad_counter,
                                "distancia_bola_max": round(plr["dist_ball"]),
                                "boost_pct": round(plr["boost"] / BOOST_MAX_RAW * 100),
                                "pos_x": round(plr["px"]), "pos_y": round(plr["py"]),
                            },
                            severity="alto" if posbad_counter >= 20 else "normal",
                        ))
                    posbad_counter = 0

                # ── Recovery lenta ──
                is_airborne = plr["pz"] > 200 and abs(plr["vz"]) > 100
                is_falling = plr["vz"] < -200 and plr["pz"] < 500
                is_on_ground = plr["pz"] < 100 and plr["speed"] < VELOCITY_STOPPED

                if is_falling or (is_on_ground and not is_airborne):
                    recovery_counter += 1
                else:
                    if recovery_counter >= RECOVERY_SLOW_FRAMES:
                        raw_moments.append(DetectedMoment(
                            timestamp=ts, frame_index=fi,
                            category="recovery_lenta",
                            context={
                                "duracao_frames": recovery_counter,
                                "altura": round(plr["pz"]),
                                "vel_z": round(plr["vz"]),
                                "boost_pct": round(plr["boost"] / BOOST_MAX_RAW * 100),
                            },
                            severity="normal",
                        ))
                    recovery_counter = 0

            consolidated = self._consolidate(raw_moments, fps, replay_name, player_name)
            return consolidated

        except Exception as e:
            print(f"Erro ao detectar momentos: {e}")
            import traceback
            traceback.print_exc()
            return []

    # ── COLUMN MAPPING ─────────────────────────────────────────────────────

    def _build_col_map(self, headers: Dict) -> Dict[str, Dict[str, int]]:
        result = {}
        for section_key in ("player_headers", "global_headers"):
            section = headers.get(section_key, {})
            for feat, cols in section.items():
                prefix = "g_" if section_key == "global_headers" else ""
                if isinstance(cols, dict):
                    result[prefix + feat] = cols
                elif isinstance(cols, list):
                    result[prefix + feat] = {name: i for i, name in enumerate(cols)}
        return result

    def _parse_ball(self, ball_data: np.ndarray, col_map: Dict) -> Optional[Dict[str, float]]:
        """Extrai dados da bola de um array 1D de colunas globais."""
        key = "g_BallRigidBody"
        if key in col_map:
            m = col_map[key]
            try:
                return {
                    "bx": float(ball_data[m["pos_x"]]),
                    "by": float(ball_data[m["pos_y"]]),
                    "bz": float(ball_data[m["pos_z"]]),
                    "bvx": float(ball_data[m["vel_x"]]),
                    "bvy": float(ball_data[m["vel_y"]]),
                    "bvz": float(ball_data[m["vel_z"]]),
                }
            except (KeyError, IndexError):
                pass

        # Fallback: primeiras 6 colunas = BallRigidBody padrão
        if len(ball_data) >= 6:
            return {
                "bx": float(ball_data[0]), "by": float(ball_data[1]), "bz": float(ball_data[2]),
                "bvx": float(ball_data[3]), "bvy": float(ball_data[4]), "bvz": float(ball_data[5]),
            }
        return None

    def _parse_player(self, pdata: np.ndarray, col_map: Dict) -> Optional[Dict[str, float]]:
        """Extrai dados de um player de um array 1D já fatiado."""
        try:
            # Posição e velocidade via col_map
            rb_key = "PlayerRigidBody"
            boost_key = "PlayerBoost"

            px = py = pz = vx = vy = vz = 0.0
            if rb_key in col_map:
                m = col_map[rb_key]
                px = float(pdata[m["pos_x"]])
                py = float(pdata[m["pos_y"]])
                pz = float(pdata[m["pos_z"]])
                vx = float(pdata[m["vel_x"]])
                vy = float(pdata[m["vel_y"]])
                vz = float(pdata[m["vel_z"]])
            elif len(pdata) >= 6:
                px, py, pz = float(pdata[0]), float(pdata[1]), float(pdata[2])
                vx, vy, vz = float(pdata[3]), float(pdata[4]), float(pdata[5])

            # Boost
            boost = 0.0
            if boost_key in col_map:
                m = col_map[boost_key]
                boost = float(pdata[m["boost"]])
            elif len(pdata) > 6:
                boost = float(pdata[6])

            speed = (vx**2 + vy**2 + vz**2) ** 0.5

            return {
                "px": px, "py": py, "pz": pz,
                "vx": vx, "vy": vy, "vz": vz,
                "boost": boost,
                "speed": speed,
                "dist_ball": 0.0,
            }
        except (KeyError, IndexError, TypeError):
            return None

    # ── CONSOLIDATION ──────────────────────────────────────────────────────

    def _consolidate(
        self,
        raw: List[DetectedMoment],
        fps: float,
        replay_id: str,
        player_name: str,
        merge_window_sec: float = 2.0,
    ) -> List[DetectedMoment]:
        """Mescla momentos da mesma categoria próximos no tempo."""
        if not raw:
            return []

        raw.sort(key=lambda m: m.timestamp)
        merged: List[DetectedMoment] = []
        window = merge_window_sec

        for m in raw:
            m.replay_id = replay_id
            m.player_name = player_name

            if merged and merged[-1].category == m.category and (m.timestamp - merged[-1].timestamp) < window:
                # Atualizar contexto com duração acumulada
                prev = merged[-1]
                prev.context["duracao_frames"] = prev.context.get("duracao_frames", 1) + m.context.get("duracao_frames", 1)
                prev.context["fim_timestamp"] = m.timestamp
                # Manter severidade mais alta
                if m.severity == "critico" or (m.severity == "alto" and prev.severity != "critico"):
                    prev.severity = m.severity
            else:
                merged.append(m)

        return merged


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO CONVENIENCE
# ══════════════════════════════════════════════════════════════════════════════

def detect_moments_from_replay(
    replay_path: str,
    player_name: str = "",
    player_index: Optional[int] = None,
    fps: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    Função convenience: detecta momentos e retorna como lista de dicts.

    Returns:
        Lista de dicts serializáveis (timestamp, category, context, severity, etc.)
    """
    detector = MomentDetector()
    moments = detector.detect_from_replay(replay_path, player_name, player_index, fps)
    return [asdict(m) for m in moments]


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Uso: python -m bot.moment_detector <replay.replay> [player_name]")
        _sys.exit(1)

    path = _sys.argv[1]
    name = _sys.argv[2] if len(_sys.argv) > 2 else "TestPlayer"

    print(f"Analisando: {path}")
    moments = detect_moments_from_replay(path, name)
    print(f"\nMomentos detectados: {len(moments)}")
    for m in moments[:20]:
        print(f"  [{m['severity']:>8}] {m['timestamp']:.1f}s  {m['category']}")
