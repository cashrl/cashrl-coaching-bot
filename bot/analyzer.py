"""
RLBotPro - Analyzer Module
Extrai e processa estatísticas dos replays do Ballchasing.
"""
from typing import Dict, Any, Optional, List, Tuple


class ReplayAnalyzer:
    """Classe para analisar dados de replays do Ballchasing."""

    # Mapeamento de playlists
    PLAYLIST_MAP = {
        'ranked-duels': '1',
        'duel': '1',
        'ranked-doubles': '2',
        'doubles': '2',
        'ranked-standard': '3',
        'standard': '3'
    }

    def __init__(self, player_name: str):
        """
        Inicializa o analisador.
        
        Args:
            player_name: Nome do jogador para identificar nos replays
        """
        self.player_name = player_name
        self._all_players_cache: Optional[List[Tuple[str, Dict[str, Any], str]]] = None

    def analyze_replay(self, replay_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analisa um replay completo e extrai todas as stats.
        
        Args:
            replay_data: Dados completos do replay do Ballchasing
            
        Returns:
            Dicionário com todas as stats extraídas ou None
        """
        if not replay_data:
            return None

        # Reset cache para cada replay novo
        self._all_players_cache = None

        try:
            # Detectar playlist
            playlist = self._detect_playlist(replay_data)
            
            # Encontrar o jogador nos dados
            player_stats = self._find_player(replay_data)
            if not player_stats:
                print(f"Jogador {self.player_name} não encontrado no replay")
                return None

            # Extrair stats de cada categoria
            boost_stats = self._extract_boost_stats(player_stats)
            position_stats = self._extract_position_stats(player_stats)
            movement_stats = self._extract_movement_stats(player_stats)
            core_stats = self._extract_core_stats(player_stats)
            
            # Metadata do replay
            metadata = self._extract_metadata(replay_data, playlist)
            
            # Combinar todas as stats
            result = {
                **metadata,
                **boost_stats,
                **position_stats,
                **movement_stats,
                **core_stats
            }
            
            return result

        except Exception as e:
            print(f"Erro ao analisar replay: {e}")
            return None

    def _detect_playlist(self, replay_data: Dict[str, Any]) -> str:
        """
        Detecta a playlist do replay.
        
        Args:
            replay_data: Dados do replay
            
        Returns:
            Nome da playlist (ranked-duels, ranked-doubles, ranked-standard)
        """
        # Tentar pegar direto dos dados
        playlist_id = str(replay_data.get('playlist_id', ''))
        
        playlist_map_reverse = {
            '1': 'ranked-duels',
            '2': 'ranked-doubles',
            '3': 'ranked-standard'
        }
        
        return playlist_map_reverse.get(playlist_id, 'ranked-doubles')

    # ── PLAYER MATCHING ──────────────────────────────────────────────────────

    def _get_all_players(self, replay_data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any], str]]:
        """
        Coleta todos os jogadores de todos os formatos de dados.
        Retorna lista de (nome, player_dict, team).
        """
        if self._all_players_cache is not None:
            return self._all_players_cache

        seen = set()
        result: List[Tuple[str, Dict[str, Any], str]] = []

        # Formato top-level (replay_data['players'])
        for player in replay_data.get('players', []):
            name = player.get('name', '')
            if name and name not in seen:
                seen.add(name)
                result.append((name, player, 'unknown'))

        # Formato Ballchasing API (blue/orange teams)
        for team in ['blue', 'orange']:
            for player in replay_data.get(team, {}).get('players', []):
                name = player.get('name', '')
                if name and name not in seen:
                    seen.add(name)
                    result.append((name, player, team))

        self._all_players_cache = result
        return result

    def _names_match(self, candidate: str, target: str) -> bool:
        """
        Compara nomes com matching fuzzy.
        Suporta: exato, comecando com, contendo, ou por token.
        """
        c = candidate.strip().lower()
        t = target.strip().lower()

        # Exato
        if c == t:
            return True

        # Um contem o outro (minimo 3 chars para evitar falsos positivos)
        if len(t) >= 3 and len(c) >= 3:
            if t in c or c in t:
                return True

        # Matching por token (primeiras letras, sem caracteres especiais)
        c_clean = ''.join(ch for ch in c if ch.isalnum() or ch == ' ')
        t_clean = ''.join(ch for ch in t if ch.isalnum() or ch == ' ')
        if len(t_clean) >= 3 and len(c_clean) >= 3:
            if t_clean in c_clean or c_clean in t_clean:
                return True

        # Comparar sem espacos e sem pontuacao
        c_alpha = ''.join(ch for ch in c if ch.isalnum())
        t_alpha = ''.join(ch for ch in t if ch.isalnum())
        if c_alpha == t_alpha:
            return True
        if len(t_alpha) >= 3 and len(c_alpha) >= 3:
            if t_alpha in c_alpha or c_alpha in t_alpha:
                return True

        return False

    def _find_player(self, replay_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Encontra os dados do jogador nos replays.
        Estrategia:
          1. Match exato pelo nome
          2. Match fuzzy (contem, prefixo, token)
          3. Fallback: jogador com maior score
        """
        all_players = self._get_all_players(replay_data)

        # 1. Match exato
        for name, player, team in all_players:
            if name.lower() == self.player_name.lower():
                return player

        # 2. Match fuzzy
        for name, player, team in all_players:
            if self._names_match(name, self.player_name):
                return player

        # 3. Fallback: jogador com maior score
        if all_players:
            best = None
            best_score = -1
            for name, player, team in all_players:
                core = self._get_stats_section(player, 'core')
                score = core.get('score', 0) if isinstance(core, dict) else 0
                if score > best_score:
                    best_score = score
                    best = player
            if best:
                print(f"  Fallback: usando jogador com maior score ({best_score})")
                return best

        return None

    def _get_stats_section(self, player_stats: Dict[str, Any], section: str) -> Dict[str, Any]:
        """
        Busca uma secao de stats, compativel com API Ballchasing.
        A API retorna stats dentro de player['stats'][section],
        mas o analyzer antigo procurava player[section].
        
        Args:
            player_stats: Dicionario do jogador
            section: Nome da secao (boost, positioning, movement, core)
            
        Returns:
            Dicionario com a secao de stats
        """
        # Tentar caminho direto (formato antigo)
        result = player_stats.get(section, {})
        if result:
            return result
        # Tentar caminho via stats (formato da API Ballchasing)
        stats = player_stats.get('stats', {})
        if isinstance(stats, dict):
            return stats.get(section, {})
        return {}

    def _extract_boost_stats(self, player_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai estatísticas de boost.
        
        Args:
            player_stats: Stats do jogador
            
        Returns:
            Dicionário com stats de boost
        """
        boost = self._get_stats_section(player_stats, 'boost')
        
        return {
            'boost_avg': boost.get('avg_amount', 0),
            'time_zero_boost': boost.get('time_zero_boost', 0),
            'time_full_boost': boost.get('time_full_boost', 0),
            'big_pads': boost.get('bumps', {}).get('big_pads', 0) if isinstance(boost.get('bumps'), dict) else boost.get('big_pads', 0),
            'small_pads': boost.get('bumps', {}).get('small_pads', 0) if isinstance(boost.get('bumps'), dict) else boost.get('small_pads', 0),
            'total_collected': boost.get('total_collected', 0),
            'time_boost_0_25': boost.get('time_boost_0_25', 0),
            'time_boost_25_50': boost.get('time_boost_25_50', 0),
            'time_boost_50_75': boost.get('time_boost_50_75', 0),
            'time_boost_75_100': boost.get('time_boost_75_100', 0)
        }

    def _extract_position_stats(self, player_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai estatísticas de posicionamento.
        
        Args:
            player_stats: Stats do jogador
            
        Returns:
            Dicionário com stats de posicionamento
        """
        position = self._get_stats_section(player_stats, 'positioning')
        
        return {
            'avg_distance_to_ball': position.get('avg_distance_to_ball', 0),
            'time_defensive_third': position.get('time_defensive_third', 0),
            'time_offensive_third': position.get('time_offensive_third', 0),
            'time_neutral_third': position.get('time_neutral_third', 0),
            'time_behind_ball': position.get('time_behind_ball', 0),
            'time_infront_ball': position.get('time_infront_ball', 0)
        }

    def _extract_movement_stats(self, player_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai estatísticas de movimento.
        
        Args:
            player_stats: Stats do jogador
            
        Returns:
            Dicionário com stats de movimento
        """
        movement = self._get_stats_section(player_stats, 'movement')
        
        return {
            'avg_speed': movement.get('avg_speed', 0),
            'time_supersonic': movement.get('time_supersonic_speed', 0),
            'time_boost_speed': movement.get('time_boost_speed', 0),
            'time_slow_speed': movement.get('time_slow_speed', 0),
            'time_on_ground': movement.get('time_on_ground', 0),
            'time_in_low_air': movement.get('time_in_low_air', 0),
            'time_in_high_air': movement.get('time_in_high_air', 0)
        }

    def _extract_core_stats(self, player_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai estatísticas principais (core).
        
        Args:
            player_stats: Stats do jogador
            
        Returns:
            Dicionário com stats core
        """
        core = self._get_stats_section(player_stats, 'core')
        
        # Calcular shooting percentage de forma segura
        shots = core.get('shots', 0)
        goals = core.get('goals', 0)
        shooting_pct = (goals / shots * 100) if shots > 0 else 0
        
        return {
            'score': core.get('score', 0),
            'goals': goals,
            'assists': core.get('assists', 0),
            'saves': core.get('saves', 0),
            'shooting_pct': shooting_pct,
            'demos_inflicted': 0,
            'demos_taken': 0
        }

    def _extract_metadata(self, replay_data: Dict[str, Any], playlist: str) -> Dict[str, Any]:
        """
        Extrai metadados do replay.
        
        Args:
            replay_data: Dados do replay
            playlist: Playlist detectada
            
        Returns:
            Dicionário com metadados
        """
        # Determinar resultado (win/loss)
        winner = replay_data.get('winner', '')
        player_team = self._get_player_team(replay_data)
        
        if winner == player_team:
            result = 'win'
        elif winner == 'orange' and player_team == 'blue':
            result = 'loss'
        elif winner == 'blue' and player_team == 'orange':
            result = 'loss'
        else:
            result = 'draw'
        
        # Extrair ranks dos oponentes
        opponent_ranks = self._get_opponent_ranks(replay_data)
        
        return {
            'replay_id': replay_data.get('id', ''),
            'playlist': playlist,
            'date': replay_data.get('created_at', ''),
            'result': result,
            'opponent_rank': ', '.join(opponent_ranks) if opponent_ranks else 'Unknown',
            'my_rank': self._get_player_rank(replay_data),
            'raw_json': replay_data
        }

    def _get_player_team(self, replay_data: Dict[str, Any]) -> str:
        """
        Retorna o time do jogador (blue/orange).
        """
        all_players = self._get_all_players(replay_data)
        for name, player, team in all_players:
            if team in ('blue', 'orange') and self._names_match(name, self.player_name):
                return team
        return 'blue'

    def _get_player_rank(self, replay_data: Dict[str, Any]) -> str:
        """
        Retorna o rank do jogador.
        """
        all_players = self._get_all_players(replay_data)
        for name, player, team in all_players:
            if self._names_match(name, self.player_name):
                return player.get('rank', 'Unknown')
        return 'Unknown'

    def _get_opponent_ranks(self, replay_data: Dict[str, Any]) -> List[str]:
        """
        Retorna os ranks dos oponentes.
        """
        player_team = self._get_player_team(replay_data)
        opponent_team = 'orange' if player_team == 'blue' else 'blue'
        
        all_players = self._get_all_players(replay_data)
        return [player.get('rank', 'Unknown')
                for _, player, team in all_players
                if team == opponent_team]

    def extract_player_from_replay(self, replay_data: Dict[str, Any], 
                                   target_name: str) -> Optional[Dict[str, Any]]:
        """
        Extrai stats de um jogador específico de um replay.
        Usa matching fuzzy para encontrar o jogador.
        
        Args:
            replay_data: Dados do replay
            target_name: Nome do jogador alvo
            
        Returns:
            Stats do jogador ou None
        """
        self._all_players_cache = None
        all_players = self._get_all_players(replay_data)

        # 1. Match exato
        for name, player, team in all_players:
            if name.lower() == target_name.lower():
                return self._build_player_stats(player)

        # 2. Match fuzzy
        for name, player, team in all_players:
            if self._names_match(name, target_name):
                return self._build_player_stats(player)

        return None

    def _build_player_stats(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """
        Constoi o dict de stats a partir de um objeto player.
        
        Args:
            player: Objeto player da API Ballchasing
            
        Returns:
            Dicionario com todas as stats
        """
        demo = self._get_stats_section(player, 'demo')
        return {
            **self._extract_boost_stats(player),
            **self._extract_position_stats(player),
            **self._extract_movement_stats(player),
            **self._extract_core_stats(player),
            'is_pro': player.get('is_pro', False),
            'name': player.get('name', ''),
            'demos_inflicted': demo.get('inflicted', 0),
            'demos_taken': demo.get('taken', 0)
        }
