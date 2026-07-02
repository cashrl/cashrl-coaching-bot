"""
RLBotPro - Moment Baseline
Agrega momentos detectados por categoria e por pro para criar uma
baseline de "como pros se comportam" em cada tipo de situação.
"""
import json
from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict

from database import Database


class MomentBaseline:
    """
    Agrega momentos detectados em replays de pros e cria baselines
    por categoria de momento.

    Cada baseline descreve, para uma dada categoria:
      - padrao_dominante: qual ação os pros mais tomam nessa situação
      - frequência: quantas vezes essa categoria aparece por replay
      - distribuição detalhada das ações tomadas
    """

    def __init__(self, db: Database):
        self.db = db

    def build_from_moments(
        self,
        moments: List[Dict[str, Any]],
        pro_name: str,
        playlist: Optional[str] = None,
        replay_count: int = 1,
    ) -> Dict[str, str]:
        """
        Processa uma lista de momentos detectados e salva baselines
        por categoria.

        Args:
            moments: Lista de dicts com keys {category, context, severity}
            pro_name: Nome do profissional
            playlist: Playlist dos replays (ex: "ranked-2v2")
            replay_count: Quantidade de replays analisados (para calcular frequência)

        Returns:
            Dict {category: dominant_pattern} — resumo do que foi salvo
        """
        # Agrupar por categoria
        by_cat: Dict[str, List[Dict]] = defaultdict(list)
        for m in moments:
            by_cat[m["category"]].append(m)

        saved = {}
        for category, cat_moments in by_cat.items():
            freq = len(cat_moments) / max(replay_count, 1)
            pattern, details = self._analyze_category(cat_moments)

            self.db.save_moment_baseline(
                category=category,
                pro_name=pro_name,
                playlist=playlist,
                dominant_pattern=pattern,
                frequency=round(freq, 2),
                sample_moments=len(cat_moments),
                details=details,
            )
            saved[category] = pattern
            print(f"  {category}: {pattern} ({len(cat_moments)} momentos, {freq:.1f}/replay)")

        return saved

    def _analyze_category(self, moments: List[Dict]) -> tuple:
        """
        Analisa os momentos de uma categoria e retorna o padrão dominante
        e detalhes da distribuição.

        Returns:
            (dominant_pattern, details_dict)
        """
        # Extrair ações baseadas no contexto
        actions = []
        for m in moments:
            ctx = m.get("context", {})
            action = self._infer_action(m["category"], ctx)
            actions.append(action)

        counter = Counter(actions)
        if not counter:
            return "sem_dados", {}

        dominant = counter.most_common(1)[0][0]
        total = len(actions)

        details = {
            "distribuicao": {
                action: {"count": count, "pct": round(count / total * 100, 1)}
                for action, count in counter.most_common()
            },
            "total_momentos": total,
        }

        return dominant, details

    def _infer_action(self, category: str, ctx: Dict) -> str:
        """
        Infere a ação tomada pelo pro baseado na categoria e no contexto.

        Retorna uma string descritiva da ação (ex: "recuou_pro_gol",
        "pegou_boost_grande", etc.)
        """
        boost_pct = ctx.get("boost_pct", 50)
        dist_bola = ctx.get("distancia_bola", 0)
        speed = ctx.get("velocidade", 0)
        px = ctx.get("pos_x", 0)
        dist_gol = ctx.get("distancia_gol_proprio", 0)

        if category == "boost_baixo_perigoso":
            if boost_pct < 10:
                return "buscou_boost_grande"
            elif dist_bola < 500:
                return "continuou_pressao_sem_boost"
            else:
                return "recuou_para_safety"

        elif category == "defesa_fora_posicao":
            if dist_gol < 2000:
                return "voltou_para_gol"
            elif speed > 500:
                return "rotacionou_rapido"
            else:
                return "rotacionou_lento"

        elif category == "rush_sem_boost":
            if dist_bola < 500:
                return "fez_challenge"
            elif speed > 1000:
                return "foi_agressivo"
            else:
                return "desistiu_do_rush"

        elif category == "hesitacao":
            if dist_bola < 300:
                return "esperou_oportunidade"
            else:
                return "recuou_para_boost"

        elif category == "posicao_ruim":
            if px > 0:
                return "permaneceu_ofensivo"
            else:
                return "rotacionou_para_tras"

        elif category == "recovery_lenta":
            if boost_pct > 50:
                return "usou_boost_para_recuperar"
            else:
                return "esperou_recuperacao"

        return "acao_desconhecida"

    def get_baseline_for_category(
        self, category: str, playlist: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retorna a baseline consolidada (todos os pros) para uma categoria.

        Agrega os padrões de todos os pros disponíveis para essa categoria.
        """
        all_bl = self.db.get_all_moment_baselines(category=category, playlist=playlist)
        if not all_bl:
            return None

        # Consolidar padrões de todos os pros
        action_counts: Counter = Counter()
        total_moments = 0

        for bl in all_bl:
            details = bl.get("details", {})
            dist = details.get("distribuicao", {})
            for action, info in dist.items():
                action_counts[action] += info.get("count", 0)
                total_moments += info.get("count", 0)

        if not action_counts:
            return None

        dominant = action_counts.most_common(1)[0][0]
        return {
            "category": category,
            "dominant_pattern": dominant,
            "total_moments": total_moments,
            "pros_included": [bl["pro_name"] for bl in all_bl],
            "distribuicao": {
                action: {"count": c, "pct": round(c / total_moments * 100, 1)}
                for action, c in action_counts.most_common()
            },
        }
