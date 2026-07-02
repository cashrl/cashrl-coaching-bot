"""
RLBotPro - Metric Interpretation Module
Fonte única de verdade para interpretação de métricas.
Todas as funções de geração de texto devem usar este módulo.
"""

# ══════════════════════════════════════════════════════════════════════════════
# DEFINIÇÕES DE MÉTRICAS E INTERPRETAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

METRIC_INTERPRETATIONS = {
    "boost_ratio": {
        "label": "Razão Boost Usado/Coletado",
        "unit": "%",
        "ranges": [
            {"min": 0, "max": 80, "status": "muito_baixo", "interpretation": "Muito eficiente - pode estar segurando boost demais"},
            {"min": 80, "max": 100, "status": "abaixo", "interpretation": "Eficiente - usando boost de forma controlada"},
            {"min": 100, "max": 115, "status": "dentro_meta", "interpretation": "Normal - usando boost do spawn + coletado"},
            {"min": 115, "max": 130, "status": "acima", "interpretation": "Pode estar usando boost do spawn eficientemente"},
            {"min": 130, "max": 999, "status": "muito_alto", "interpretation": "Ineficiente - desperdiçando boost ou não coletando suficiente"},
        ],
        "description": "Razão entre boost usado e coletado. Valores >100% são normais porque incluem o boost inicial do spawn."
    },
    "avg_distance_to_ball": {
        "label": "Distância Média à Bola",
        "unit": "uu",
        "ranges": [
            {"min": 0, "max": 400, "status": "muito_baixo", "interpretation": "Muito perto da bola - pode estar pressionando demais"},
            {"min": 400, "max": 650, "status": "dentro_meta", "interpretation": "Boa distância - posicionamento equilibrado"},
            {"min": 650, "max": 900, "status": "acima", "interpretation": "Distante da bola - pode estar hesitando"},
            {"min": 900, "max": 9999, "status": "muito_alto", "interpretation": "Muito distante - posicionamento passivo ou medo da bola"},
        ],
        "description": "Distância média do jogador à bola durante a partida. ~550uu é a média profissional."
    },
    "time_offensive_pct": {
        "label": "Tempo no Terço Ofensivo",
        "unit": "%",
        "ranges": [
            {"min": 0, "max": 30, "status": "muito_baixo", "interpretation": "Muito passivo - raramente ataca"},
            {"min": 30, "max": 40, "status": "abaixo", "interpretation": "Pouco tempo ofensivo - pode estar defendendo demais"},
            {"min": 40, "max": 56, "status": "dentro_meta", "interpretation": "Bom equilíbrio entre ataque e defesa"},
            {"min": 56, "max": 70, "status": "acima", "interpretation": "Muito tempo atacando - pode estar negligenciando defesa"},
            {"min": 70, "max": 100, "status": "muito_alto", "interpretation": "Demais tempo atacando - vulnerável a contra-ataques"},
        ],
        "description": "Porcentagem do tempo gasto no terço ofensivo do campo. ~48% é a média profissional."
    },
    "avg_speed": {
        "label": "Velocidade Média",
        "unit": "u/s",
        "ranges": [
            {"min": 0, "max": 1200, "status": "muito_baixo", "interpretation": "Muito lento - precisa acelerar mais"},
            {"min": 1200, "max": 1400, "status": "abaixo", "interpretation": "Velocidade abaixo da média"},
            {"min": 1400, "max": 1700, "status": "dentro_meta", "interpretation": "Velocidade adequada"},
            {"min": 1700, "max": 1900, "status": "acima", "interpretation": "Rápido - bom para pressionar"},
            {"min": 1900, "max": 9999, "status": "muito_alto", "interpretation": "Muito rápido - pode estar queimando boost desnecessariamente"},
        ],
        "description": "Velocidade média durante a partida. ~1550 u/s é a média profissional."
    },
    "time_supersonic_pct": {
        "label": "Tempo Supersônico",
        "unit": "%",
        "ranges": [
            {"min": 0, "max": 8, "status": "muito_baixo", "interpretation": "Raramente atinge velocidade máxima"},
            {"min": 8, "max": 12, "status": "abaixo", "interpretation": "Pouco tempo supersônico"},
            {"min": 12, "max": 22, "status": "dentro_meta", "interpretation": "Bom uso de velocidade máxima"},
            {"min": 22, "max": 30, "status": "acima", "interpretation": "Muito tempo supersônico - pode estar queimando boost"},
            {"min": 30, "max": 100, "status": "muito_alto", "interpretation": "Demais tempo supersônico - inefficiência de boost"},
        ],
        "description": "Porcentagem do tempo em velocidade supersônica. ~17% é a média profissional."
    },
    "aerial_high_pct": {
        "label": "Tempo Aéreo Alto",
        "unit": "%",
        "ranges": [
            {"min": 0, "max": 3, "status": "muito_baixo", "interpretation": "Raramente voa alto"},
            {"min": 3, "max": 6, "status": "abaixo", "interpretation": "Pouco tempo aéreo alto"},
            {"min": 6, "max": 12, "status": "dentro_meta", "interpretation": "Bom equilíbrio aéreo"},
            {"min": 12, "max": 20, "status": "acima", "interpretation": "Muito tempo alto - pode estar desperdiçando boost"},
            {"min": 20, "max": 100, "status": "muito_alto", "interpretation": "Demais tempo alto - vulnerável no chão"},
        ],
        "description": "Porcentagem do tempo voando alto (>4m). ~8% é a média profissional."
    },
    "shot_speed_avg": {
        "label": "Velocidade Média de Finalização",
        "unit": "km/h",
        "ranges": [
            {"min": 0, "max": 60, "status": "muito_baixo", "interpretation": "Finalizações muito fracas"},
            {"min": 60, "max": 80, "status": "abaixo", "interpretation": "Finalizações abaixo da média"},
            {"min": 80, "max": 110, "status": "dentro_meta", "interpretation": "Finalizações com boa velocidade"},
            {"min": 110, "max": 130, "status": "acima", "interpretation": "Finalizações fortes"},
            {"min": 130, "max": 999, "status": "muito_alto", "interpretation": "Finalizações extremamente fortes"},
        ],
        "description": "Velocidade média das finalizações. ~95 km/h é a média profissional."
    },
    "demos_per_min": {
        "label": "Demos por Minuto",
        "unit": "/min",
        "ranges": [
            {"min": 0, "max": 0.05, "status": "muito_baixo", "interpretation": "Raramente derruba adversários"},
            {"min": 0.05, "max": 0.15, "status": "dentro_meta", "interpretation": "Uso adequado de demos"},
            {"min": 0.15, "max": 0.3, "status": "acima", "interpretation": "Muitas demos - pode estar focando em derrubar"},
            {"min": 0.3, "max": 999, "status": "muito_alto", "interpretation": "Demais demos - pode estar negligenciando其他 aspectos"},
        ],
        "description": "Número médio de demolições por minuto. ~0.15 é a média profissional."
    },
    "score_per_min": {
        "label": "Score por Minuto",
        "unit": "pts/min",
        "ranges": [
            {"min": 0, "max": 80, "status": "muito_baixo", "interpretation": "Score muito baixo - pouca contribuição"},
            {"min": 80, "max": 110, "status": "abaixo", "interpretation": "Score abaixo da média"},
            {"min": 110, "max": 200, "status": "dentro_meta", "interpretation": "Score adequado"},
            {"min": 200, "max": 250, "status": "acima", "interpretation": "Score alto - boa contribuição"},
            {"min": 250, "max": 9999, "status": "muito_alto", "interpretation": "Score muito alto - contribuição excepcional"},
        ],
        "description": "Score médio por minuto de jogo. ~150 é a média profissional."
    }
}


def interpret_metric(metric_key: str, value: float) -> dict:
    """
    Interpreta um valor de métrica usando as definições centralizadas.
    
    Args:
        metric_key: Chave da métrica (ex: "boost_ratio")
        value: Valor da métrica
        
    Returns:
        Dict com label, status, interpretation, unit
    """
    if metric_key not in METRIC_INTERPRETATIONS:
        return {"label": metric_key, "status": "desconhecido", "interpretation": "Métrica não disponível"}
    
    metric = METRIC_INTERPRETATIONS[metric_key]
    
    for r in metric["ranges"]:
        if r["min"] <= value < r["max"]:
            return {
                "label": metric["label"],
                "status": r["status"],
                "interpretation": r["interpretation"],
                "unit": metric["unit"],
                "value": value
            }
    
    # Fallback
    return {
        "label": metric["label"],
        "status": "desconhecido",
        "interpretation": "Valor fora das faixas definidas",
        "unit": metric["unit"],
        "value": value
    }


def get_boost_ratio_interpretation(boost_used: float, boost_collected: float) -> dict:
    """Interpreta a razão de boost de forma consistente."""
    if boost_collected <= 0:
        return {"status": "sem_dados", "interpretation": "Dados de boost indisponíveis"}
    
    ratio = (boost_used / boost_collected) * 100
    return interpret_metric("boost_ratio", ratio)


def get_status_label(status: str) -> str:
    """Retorna label legível para o status."""
    labels = {
        "muito_baixo": "Muito Baixo",
        "abaixo": "Abaixo",
        "dentro_meta": "Dentro da Meta",
        "acima": "Acima",
        "muito_alto": "Muito Alto",
        "sem_dados": "Sem Dados",
        "desconhecido": "Desconhecido"
    }
    return labels.get(status, status)


def format_interpretation(interpretation: dict, include_value: bool = True) -> str:
    """Formata interpretação para exibição."""
    parts = []
    if include_value and "value" in interpretation:
        parts.append(f"{interpretation['label']}: {interpretation['value']:.1f}{interpretation.get('unit', '')}")
    parts.append(f"Status: {get_status_label(interpretation.get('status', ''))}")
    parts.append(f"Interpretação: {interpretation.get('interpretation', 'N/A')}")
    return " | ".join(parts)
