"""
RLBotPro - Build Pro Baseline
Busca replays de um pro na API do Ballchasing e cria uma baseline.
"""
import os
import sys
import json
import time
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database


class ProBaselineBuilder:
    """Constroi baseline de um pro usando a API do Ballchasing."""

    BASE_URL = "https://ballchasing.com/api"
    MIN_REQUEST_INTERVAL = 0.5

    def __init__(self, token: str, db: Database):
        self.token = token
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({"Authorization": token})
        self._last_request_time = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def search_replays(self, player_name: str, playlist: str = None, count: int = 200) -> List[Dict]:
        """Busca replays que contem o jogador."""
        params = {
            'player-name': player_name,
            'count': min(count, 200),
            'sort': 'replay-date',
            'dir': 'desc'
        }
        if playlist:
            params['playlist'] = playlist

        all_replays = []
        offset = 0

        while len(all_replays) < count:
            params['offset'] = offset
            params['count'] = min(50, count - len(all_replays))

            try:
                self._rate_limit()
                resp = self.session.get(f"{self.BASE_URL}/replays", params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                replays = data.get('list', [])

                if not replays:
                    break

                all_replays.extend(replays)
                offset += len(replays)

                print(f"  Buscados {len(all_replays)} replays...")
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                print(f"  Erro ao buscar replays: {e}")
                break

        return all_replays[:count]

    def get_replay_stats(self, replay_id: str) -> Optional[Dict]:
        """Busca stats detalhadas de um replay."""
        try:
            self._rate_limit()
            resp = self.session.get(f"{self.BASE_URL}/replays/{replay_id}", timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"  Erro ao buscar replay {replay_id}: {e}")
            return None

    def extract_player_stats(self, replay_data: Dict, player_name: str) -> Optional[Dict]:
        """Extrai stats de um jogador especifico de um replay."""
        player_name_lower = player_name.lower()

        # Ballchasing API stores players in blue/orange team objects
        blue_team = replay_data.get('blue', {})
        orange_team = replay_data.get('orange', {})

        my_team_data = None
        my_team_color = None

        # Find which team the player is on
        for color_name, team_data in [('blue', blue_team), ('orange', orange_team)]:
            team_players = team_data.get('players', [])
            for p in team_players:
                name = p.get('name', '')
                if player_name_lower in name.lower():
                    my_team_data = team_data
                    my_team_color = color_name
                    break
            if my_team_data:
                break

        if not my_team_data:
            return None

        # Find the player in the team
        for p in my_team_data.get('players', []):
            name = p.get('name', '')
            if player_name_lower in name.lower():
                stats = p.get('stats', {})
                core = stats.get('core', {})
                boost = stats.get('boost', {})
                movement = stats.get('movement', {})
                positioning = stats.get('positioning', {})
                demo = stats.get('demo', {})

                team_score = my_team_data.get('score', 0)
                opp_team = orange_team if my_team_color == 'blue' else blue_team
                opp_score = opp_team.get('score', 0)

                duration = replay_data.get('duration', 0)

                return {
                    'replay_id': replay_data.get('id', ''),
                    'player_name': name,
                    'goals': core.get('goals', 0),
                    'assists': core.get('assists', 0),
                    'saves': core.get('saves', 0),
                    'shots': core.get('shots', 0),
                    'score': core.get('score', 0),
                    'shooting_pct': core.get('shooting_percentage', 0),
                    'demos_inflicted': demo.get('inflicted', 0),
                    'demos_taken': demo.get('taken', 0),
                    'boost_avg': boost.get('avg_amount', 0),
                    'boost_bpm': boost.get('bpm', 0),
                    'boost_bcpm': boost.get('bcpm', 0),
                    'big_pads': boost.get('count_collected_big', 0),
                    'small_pads': boost.get('count_collected_small', 0),
                    'time_zero_boost': boost.get('time_zero_boost', 0),
                    'time_supersonic': movement.get('time_supersonic_speed', 0),
                    'avg_speed': movement.get('avg_speed', 0),
                    'total_distance': movement.get('total_distance', 0),
                    'time_ground': movement.get('time_ground', 0),
                    'time_low_air': movement.get('time_low_air', 0),
                    'time_high_air': movement.get('time_high_air', 0),
                    'avg_distance_to_ball': positioning.get('avg_distance_to_ball', 0),
                    'time_offensive_third': positioning.get('time_offensive_third', 0),
                    'time_defensive_third': positioning.get('time_defensive_third', 0),
                    'time_offensive_pct': positioning.get('percent_offensive_half', 0),
                    'time_defensive_pct': positioning.get('percent_defensive_half', 0),
                    'time_behind_ball': positioning.get('time_behind_ball', 0),
                    'time_closest_to_ball': positioning.get('time_closest_to_ball', 0),
                    'team_score': team_score,
                    'opp_score': opp_score,
                    'result': 'win' if team_score > opp_score else 'loss',
                    'duration': duration,
                    'playlist': replay_data.get('playlist', ''),
                    'map': replay_data.get('map', {}).get('name', ''),
                }

        return None

    def build_baseline(self, player_name: str, playlist: str = None,
                       target_count: int = 200) -> Dict[str, Any]:
        """Constroi baseline completa do jogador."""
        print(f"\n{'='*60}")
        print(f"  Construindo baseline de: {player_name}")
        print(f"{'='*60}\n")

        # Buscar replays
        print("[1/3] Buscando replays...")
        replays = self.search_replays(player_name, playlist, target_count)
        print(f"  Encontrados {len(replays)} replays\n")

        if not replays:
            print("Nenhum replay encontrado!")
            return {}

        # Coletar stats
        print("[2/3] Coletando stats detalhadas...")
        all_stats = []
        for i, replay in enumerate(replays):
            replay_id = replay.get('id')
            if not replay_id:
                continue

            print(f"  [{i+1}/{len(replays)}] {replay_id[:12]}...")

            replay_data = self.get_replay_stats(replay_id)
            if not replay_data:
                continue

            player_stats = self.extract_player_stats(replay_data, player_name)
            if player_stats:
                all_stats.append(player_stats)

            time.sleep(0.3)

        print(f"\n  Stats coletadas de {len(all_stats)} replays\n")

        if not all_stats:
            print("Nenhuma stat coletada!")
            return {}

        # Calcular baseline
        print("[3/3] Calculando baseline...")
        baseline = self._calculate_averages(all_stats, player_name, playlist)

        # Salvar no banco
        self._save_to_database(baseline, player_name, playlist)

        print(f"\nBaseline criada com sucesso!")
        print(f"  Partidas: {baseline['total_matches']}")
        print(f"  Win Rate: {baseline['win_rate']}%")
        avg = baseline['averages']
        print(f"  Gols/partida: {avg.get('goals', 0):.2f}")
        print(f"  Assists/partida: {avg.get('assists', 0):.2f}")
        print(f"  Defesas/partida: {avg.get('saves', 0):.2f}")
        print(f"  Chutes/partida: {avg.get('shots', 0):.2f}")
        print(f"  Score/partida: {avg.get('score', 0):.0f}")
        print(f"  Boost medio: {avg.get('boost_avg', 0):.1f}")
        print(f"  Distancia bola: {avg.get('avg_distance_to_ball', 0):.0f}")
        print(f"  Velocidade media: {avg.get('avg_speed', 0):.0f}")

        return baseline

    def _calculate_averages(self, stats_list: List[Dict], player_name: str,
                            playlist: str = None) -> Dict[str, Any]:
        """Calcula medias de todas as stats."""
        n = len(stats_list)
        if n == 0:
            return {}

        # Acumular valores
        totals = {}
        wins = 0

        # Keys to average
        avg_keys = [
            'goals', 'assists', 'saves', 'shots', 'score', 'shooting_pct',
            'demos_inflicted', 'demos_taken',
            'boost_avg', 'boost_bpm', 'boost_bcpm', 'big_pads', 'small_pads', 'time_zero_boost',
            'time_supersonic', 'avg_speed', 'total_distance', 'time_ground', 'time_low_air', 'time_high_air',
            'avg_distance_to_ball', 'time_offensive_third', 'time_defensive_third',
            'time_offensive_pct', 'time_defensive_pct', 'time_behind_ball', 'time_closest_to_ball',
        ]

        for k in avg_keys:
            totals[k] = 0

        for s in stats_list:
            for k in avg_keys:
                totals[k] += s.get(k, 0)

            if s.get('result') == 'win':
                wins += 1

        # Calcular medias
        averages = {k: round(v / n, 2) for k, v in totals.items()}

        return {
            'player_name': player_name,
            'playlist': playlist or 'all',
            'created_at': datetime.now().isoformat(),
            'total_matches': n,
            'wins': wins,
            'losses': n - wins,
            'win_rate': round(wins / n * 100, 1),
            'averages': averages,
        }

    def _save_to_database(self, baseline: Dict, player_name: str,
                          playlist: str = None):
        """Salva baseline no banco de dados."""
        try:
            playlist_key = playlist or 'all'
            self.db.save_baseline(
                playlist=playlist_key,
                pro_name=player_name,
                sample_size=baseline['total_matches'],
                averages=baseline['averages']
            )
            print(f"  Baseline salva no banco ({playlist_key})")
        except Exception as e:
            print(f"  Erro ao salvar no banco: {e}")


def main():
    # Carregar config
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    token = config.get('ballchasing_token', '')
    if not token:
        print("Token do Ballchasing nao configurado!")
        return

    # Inicializar banco
    db = Database()

    # Criar builder
    builder = ProBaselineBuilder(token, db)

    # Build baseline para Zen em cada playlist
    playlists = ['ranked-doubles', 'ranked-standard', 'ranked-duels']

    for playlist in playlists:
        print(f"\n\n{'#'*60}")
        print(f"  PLAYLIST: {playlist}")
        print(f"{'#'*60}")

        builder.build_baseline(
            player_name="Zen",
            playlist=playlist,
            target_count=100
        )

    # Salvar baseline "all" (media de todas)
    print(f"\n\n{'#'*60}")
    print(f"  BASELINE GERAL (todas playlists)")
    print(f"{'#'*60}")

    builder.build_baseline(
        player_name="Zen",
        playlist=None,
        target_count=200
    )

    db.close()
    print("\n\nBaseline completa!")


if __name__ == "__main__":
    main()
