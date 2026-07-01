"""
RLBotPro - Comparer Module
Compara estatísticas do jogador com baselines de profissionais.
"""
import json
import math
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from bot.uploader import BallchasingUploader
from bot.analyzer import ReplayAnalyzer
from database import Database


class ProComparer:
    """Classe para comparar stats do jogador com profissionais."""

    def __init__(self, uploader: BallchasingUploader, analyzer: ReplayAnalyzer, 
                 db: Database):
        """
        Inicializa o comparador.
        
        Args:
            uploader: Instância do BallchasingUploader
            analyzer: Instância do ReplayAnalyzer
            db: Instância do Database
        """
        self.uploader = uploader
        self.analyzer = analyzer
        self.db = db
        self.baselines_cache: Dict[str, Dict[str, Any]] = {}

    def fetch_pro_baseline(self, playlist: str) -> Dict[str, Any]:
        """
        Busca baseline de todos os pros para uma playlist.
        
        Args:
            playlist: Nome da playlist
            
        Returns:
            Dicionário com médias e desvios padrão
        """
        # Verificar cache primeiro
        cache_key = f"pros_{playlist}"
        if cache_key in self.baselines_cache:
            return self.baselines_cache[cache_key]
        
        # Verificar banco de dados
        db_baseline = self.db.get_baseline(playlist, None)
        if db_baseline:
            self.baselines_cache[cache_key] = db_baseline['averages']
            return db_baseline['averages']
        
        # Buscar da API
        replays = self.uploader.get_pro_replays(playlist, count=200)
        if not replays:
            print(f"Nenhum replay de pros encontrado para {playlist}")
            return {}
        
        # Extrair stats de todos os pros
        players_stats = []
        for replay_summary in replays:
            replay_id = replay_summary.get('id')
            if not replay_id:
                continue
            
            replay_data = self.uploader.get_replay_details(replay_id)
            if not replay_data:
                continue
            
            # Extrair stats de cada pro no replay
            players = replay_data.get('players', [])
            for player in players:
                if player.get('is_pro', False):
                    stats = self.analyzer.extract_player_from_replay(
                        replay_data, player.get('name', '')
                    )
                    if stats:
                        players_stats.append(stats)
        
        if not players_stats:
            return {}
        
        # Calcular médias e desvios padrão
        averages = self._compute_averages(players_stats)
        
        # Salvar no cache e banco
        self.baselines_cache[cache_key] = averages
        self.db.save_baseline(playlist, None, len(players_stats), averages)
        
        return averages

    def fetch_specific_pro_baseline(self, pro_name: str, playlist: str) -> Dict[str, Any]:
        """
        Busca baseline de um pro específico.
        
        Args:
            pro_name: Nome do pro
            playlist: Nome da playlist
            
        Returns:
            Dicionário com médias e desvios padrão
        """
        # Verificar cache primeiro
        cache_key = f"{pro_name}_{playlist}"
        if cache_key in self.baselines_cache:
            return self.baselines_cache[cache_key]
        
        # Verificar banco de dados
        db_baseline = self.db.get_baseline(playlist, pro_name)
        if db_baseline:
            self.baselines_cache[cache_key] = db_baseline['averages']
            return db_baseline['averages']
        
        # Buscar da API
        replays = self.uploader.get_player_replays(pro_name, playlist, count=200)
        if not replays:
            print(f"Nenhum replay encontrado para {pro_name} em {playlist}")
            return {}
        
        # Extrair stats do pro específico
        players_stats = []
        for replay_summary in replays:
            replay_id = replay_summary.get('id')
            if not replay_id:
                continue
            
            replay_data = self.uploader.get_replay_details(replay_id)
            if not replay_data:
                continue
            
            stats = self.analyzer.extract_player_from_replay(replay_data, pro_name)
            if stats:
                players_stats.append(stats)
        
        if not players_stats:
            return {}
        
        # Calcular médias e desvios padrão
        averages = self._compute_averages(players_stats)
        
        # Salvar no cache e banco
        self.baselines_cache[cache_key] = averages
        self.db.save_baseline(playlist, pro_name, len(players_stats), averages)
        
        return averages

    def _compute_averages(self, players_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula médias e desvios padrão de uma lista de stats.
        
        Args:
            players_stats: Lista de dicionários com stats
            
        Returns:
            Dicionário com médias e desvios padrão
        """
        if not players_stats:
            return {}
        
        # Stats para calcular
        stats_to_compute = [
            'boost_avg', 'time_zero_boost', 'time_full_boost', 'big_pads', 'small_pads',
            'total_collected', 'time_boost_0_25', 'time_boost_25_50', 'time_boost_50_75',
            'time_boost_75_100', 'avg_distance_to_ball', 'time_defensive_third',
            'time_offensive_third', 'time_neutral_third', 'time_behind_ball',
            'time_infront_ball', 'avg_speed', 'time_supersonic', 'time_boost_speed',
            'time_slow_speed', 'time_on_ground', 'time_in_low_air', 'time_in_high_air',
            'score', 'goals', 'assists', 'saves', 'shooting_pct', 'demos_inflicted',
            'demos_taken'
        ]
        
        averages = {}
        
        for stat in stats_to_compute:
            values = [p.get(stat, 0) for p in players_stats if stat in p]
            
            if values:
                mean = sum(values) / len(values)
                std = self._std_dev(values, mean)
                averages[stat] = {
                    'mean': round(mean, 2),
                    'std': round(std, 2),
                    'min': round(min(values), 2),
                    'max': round(max(values), 2)
                }
        
        return averages

    def _std_dev(self, values: List[float], mean: float) -> float:
        """
        Calcula desvio padrão.
        
        Args:
            values: Lista de valores
            mean: Média dos valores
            
        Returns:
            Desvio padrão
        """
        if len(values) < 2:
            return 0.0
        
        squared_diff_sum = sum((x - mean) ** 2 for x in values)
        variance = squared_diff_sum / (len(values) - 1)
        return math.sqrt(variance)

    def compare(self, my_stats: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compara as stats do jogador com a baseline.
        
        Args:
            my_stats: Stats do jogador
            baseline: Baseline de referência (pros)
            
        Returns:
            Dicionário com resultado da comparação
        """
        if not baseline:
            return {
                'score': 0,
                'comparisons': [],
                'tips': ['Baseline não disponível. Tente atualizar.'],
                'sample_size': 0
            }
        
        comparisons = []
        total_score = 0
        stat_count = 0
        
        # Labels amigáveis para cada stat
        stat_labels = {
            'boost_avg': 'Boost Médio',
            'time_zero_boost': 'Tempo sem Boost',
            'time_full_boost': 'Tempo com Boost Cheio',
            'big_pads': 'Pads Grandes',
            'small_pads': 'Pads Pequenos',
            'total_collected': 'Total Coletado',
            'avg_distance_to_ball': 'Distância Média da Bola',
            'time_defensive_third': 'Tempo no Terço Defensivo',
            'time_offensive_third': 'Tempo no Terço Ofensivo',
            'time_neutral_third': 'Tempo no Terço Neutro',
            'time_behind_ball': 'Tempo Atrás da Bola',
            'time_infront_ball': 'Tempo à Frente da Bola',
            'avg_speed': 'Velocidade Média',
            'time_supersonic': 'Tempo Supersônico',
            'time_boost_speed': 'Tempo com Boost',
            'time_slow_speed': 'Tempo Lento',
            'time_on_ground': 'Tempo no Chão',
            'time_in_low_air': 'Tempo no Ar Baixo',
            'time_in_high_air': 'Tempo no Ar Alto',
            'score': 'Score',
            'goals': 'Gols',
            'assists': 'Assistências',
            'saves': 'Defesas',
            'shooting_pct': '% de Finalização',
            'demos_inflicted': 'Demos Aplicados',
            'demos_taken': 'Demos Sofridos'
        }
        
        # Comparar cada stat
        for stat_name, label in stat_labels.items():
            if stat_name not in baseline:
                continue
            
            my_value = my_stats.get(stat_name, 0)
            pro_data = baseline[stat_name]
            # Handle both formats: {'mean': x, 'std': y} or flat float
            if isinstance(pro_data, dict):
                pro_avg = pro_data.get('mean', 0)
                pro_std = pro_data.get('std', 0)
            else:
                pro_avg = float(pro_data)
                pro_std = 0
            
            # Calcular diferença e normalizar
            diff = my_value - pro_avg
            
            # Calcular score baseado em quantos desvios padrão está
            if pro_std > 0:
                z_score = abs(diff) / pro_std
                # Quanto mais perto do pro, maior o score (0-100)
                stat_score = max(0, min(100, 100 - (z_score * 20)))
            else:
                # Se não há variação, comparar diretamente
                if pro_avg > 0:
                    ratio = my_value / pro_avg
                    stat_score = max(0, min(100, ratio * 100))
                else:
                    stat_score = 100 if my_value == 0 else 0
            
            # Determinar status
            if diff > pro_std * 0.5:
                status = 'above'
            elif diff < -pro_std * 0.5:
                status = 'below'
            else:
                status = 'similar'
            
            comparisons.append({
                'stat': stat_name,
                'label': label,
                'my_val': round(my_value, 2),
                'pro_avg': round(pro_avg, 2),
                'pro_std': round(pro_std, 2),
                'diff': round(diff, 2),
                'status': status,
                'score': round(stat_score, 1)
            })
            
            total_score += stat_score
            stat_count += 1
        
        # Calcular score final
        final_score = round(total_score / stat_count, 1) if stat_count > 0 else 0
        
        # Gerar dicas
        tips = self._get_improvement_tips(comparisons)
        
        # Pegar sample size da baseline
        sample_size = baseline.get('sample_size', 0)
        if 'sample_size' not in baseline:
            # Tentar calcular de um dos stats
            for stat_data in baseline.values():
                if isinstance(stat_data, dict) and 'mean' in stat_data:
                    sample_size = stat_data.get('count', 0)
                    break
        
        return {
            'score': final_score,
            'comparisons': comparisons,
            'tips': tips,
            'sample_size': sample_size
        }

    def _get_improvement_tips(self, comparisons: List[Dict[str, Any]]) -> List[str]:
        """
        Gera dicas de melhoria baseadas nas stats mais fracas.
        
        Args:
            comparisons: Lista de comparações
            
        Returns:
            Lista com até 3 dicas em PT-BR
        """
        # Ordenar por score (menor primeiro = mais precisa melhorar)
        sorted_comparisons = sorted(comparisons, key=lambda x: x['score'])
        
        tips = []
        tip_templates = {
            'boost_avg': 'Colete mais boost! Seu média de {my_val:.0f} está abaixo dos {pro_avg:.0f} dos pros. Tente coletar mais pads pequenos.',
            'time_zero_boost': 'Você fica sem boost com frequência ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Foque em coletar pads pequenos quando estiver a camado.',
            'big_pads': 'Você pega poucos pads grandes ({my_val:.0f} vs {pro_avg:.0f} dos pros). Controle melhor a região de boost grande.',
            'small_pads': 'Colete mais pads pequenos ({my_val:.0f} vs {pro_avg:.0f} dos pros). Eles são essenciais para manter o boost.',
            'avg_distance_to_ball': 'Sua distância média da bola é {my_val:.1f}m vs {pro_avg:.1f}m dos pros. Mantenha uma posição mais compacta.',
            'time_defensive_third': 'Pouco tempo na defesa ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Equilibre sua posição.',
            'time_offensive_third': 'Muito tempo na defesa, pouco na ofensiva ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Seja mais agressivo quando tiver oportunidade.',
            'time_behind_ball': 'Fique mais atrás da bola ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Isso ajuda em contra-ataques.',
            'time_infront_ball': 'Pouco tempo à frente da bola ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Pressione mais quando seu time estiver com a bola.',
            'avg_speed': 'Sua velocidade média é {my_val:.0f} vs {pro_avg:.0f} dos pros. Mantenha um ritmo mais constante.',
            'time_supersonic': 'Pouco tempo supersônico ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Use o boost para atingir velocidade máxima.',
            'time_on_ground': 'Muito tempo no chão ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Pratique voos e aerials.',
            'time_in_high_air': 'Pouco tempo no ar alto ({my_val:.0f}s vs {pro_avg:.0f}s dos pros). Trabalhe seus aerials.',
            'shooting_pct': 'Sua taxa de finalização é {my_val:.0f}% vs {pro_avg:.0f}% dos pros. Foque no gol e seja mais preciso.',
            'goals': 'Poucos gols ({my_val:.0f} vs {pro_avg:.0f} dos pros). Procure mais oportunidades de gol.',
            'assists': 'Poucas assistências ({my_val:.0f} vs {pro_avg:.0f} dos pros). Olhe mais para seus companheiros.',
            'saves': 'Poucas defesas ({my_val:.0f} vs {pro_avg:.0f} dos pros). Posicione-se melhor na defesa.',
            'demos_inflicted': 'Poucos demos ({my_val:.0f} vs {pro_avg:.0f} dos pros). Use demos estratégicos para abrir espaço.'
        }
        
        for comp in sorted_comparisons[:3]:
            stat = comp['stat']
            if stat in tip_templates:
                tip = tip_templates[stat].format(
                    my_val=comp['my_val'],
                    pro_avg=comp['pro_avg']
                )
                tips.append(tip)
            else:
                if comp['status'] == 'below':
                    tips.append(f"Trabalhe sua {comp['label']}: {comp['my_val']:.1f} vs {comp['pro_avg']:.1f} dos pros.")
                elif comp['status'] == 'above':
                    tips.append(f"Excelente {comp['label']}! Você está acima da média dos pros.")
        
        return tips[:3]  # Máximo 3 dicas
