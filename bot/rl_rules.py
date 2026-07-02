"""
RLBotPro - Rocket League Rules Engine
Regras heurísticas fixas de Rocket League como base factual para o coaching.

Cada regra descreve:
  - A situação (categoria + contexto)
  - A ação correta / ideal
  - Por que essa ação é melhor
  - A ação comum de erro (o que o jogador provavelmente fez)

Isso serve de "grounding" pro LLM não inventar explicação sem embasamento.
"""

# ══════════════════════════════════════════════════════════════════════════════
# REGRAS POR CATEGORIA DE MOMENTO
# ══════════════════════════════════════════════════════════════════════════════

RULES: dict = {
    "boost_baixo_perigoso": {
        "titulo": "Boost Baixo em Situação Perigosa",
        "regra": (
            "Quando o boost está abaixo de ~14% e a bola está próxima, "
            "a jogada correta é recuar para o gol próprio pegando o boost "
            "grande no caminho (padrão de rotation). Não tente pegar boost "
            "pequeno no meio de campo — isso te deixa exposto sem recuperar "
            "boost suficiente."
        ),
        "porque": (
            "Recuar para o boost grande (100) te reposiciona defensivamente "
            "E te dá boost completo. Boost pequeno (12-36) não resolve o problema "
            "e te mantém numa posição vulnerável."
        ),
        "erro_comum": (
            "Jogadores tentam manter pressão com boost baixo, ficam parados no "
            "meio campo, ou pegam boost pequeno e voltam pro play sem boost "
            "suficiente pra fazer qualquer coisa útil."
        ),
        "contexto": {
            "boost_max_pct": 14,
            "boost_grande_perto": "recue_e_pegue",
            "boost_grande_longo": "rotacione_para_atras",
        },
    },

    "defesa_fora_posicao": {
        "titulo": "Fora de Posição Defensiva",
        "regra": (
            "Quando a bola está no terço ofensivo do adversário e você está "
            "muito longe do próprio gol (>3000 uu), rotacione imediatamente "
            "para o gol. Posição ideal de defesa: perto do poste traseiro "
            "(back post), de onde você cobre o gol inteiro."
        ),
        "porque": (
            "Do back post, você tem visão de todo o campo e pode reagir a "
            "qualquer chute. Ficar no campo adversário sem boost ou sem "
            "posicionamento cria um 2v1 ou 1v0 pro adversário."
        ),
        "erro_comum": (
            "Ficar avançado tentando fazer uma terceira pessoa pressionando, "
            "quando o melhor é recuar e rotacionar pelo lado do boost grande."
        ),
        "contexto": {
            "dist_gol_min": 3000,
            "acao_correta": "rotacionar_para_back_post",
        },
    },

    "rush_sem_boost": {
        "titulo": "Rush Agressivo sem Boost",
        "regra": (
            "Ir rápido em direção à bola com menos de ~20% de boost é "
            "arriscado. Se você não tem boost pra chegar antes do adversário "
            "ou pra fazer um challenge efetivo, é melhor recuar e esperar "
            "uma oportunidade melhor."
        ),
        "porque": (
            "Um rush sem boost te coloca fora de posição se perder o "
            "challenge, e o adversário pode simplesmente passar por você. "
            "Sem boost você não consegue recuperar a posição."
        ),
        "erro_comum": (
            "Ir no 'autopilot' direto na bola sem considerar o boost, "
            "perder o challenge, e ficar preso no terço adversário."
        ),
        "contexto": {
            "boost_max_pct": 20,
            "velocidade_min": 500,
        },
    },

    "hesitacao": {
        "titulo": "Hesitação / Paralisia",
        "regra": (
            "Quando a bola está perto (<500 uu) e você está parado ou "
            "muito lento por mais de 0.5s, você está hesitando. Nessa "
            "situação: ou faça o play (challenge, clear, pass) ou recue "
            "rapidamente. Ficar parado é o pior cenário."
        ),
        "porque": (
            "Hesitação te coloca numa posição onde você não está "
            "atacando nem defendendo. O adversário tem tempo de se "
            "posicionar enquanto você decide."
        ),
        "erro_comum": (
            "Ficar no campo de batalha sem decidir, esperando a bola "
            "chegar em vez de ir até ela ou recuar."
        ),
        "contexto": {
            "dist_bola_max": 500,
            "velocidade_max": 100,
            "duracao_min_frames": 6,
        },
    },

    "posicao_ruim": {
        "titulo": "Posicionamento Muito Distante da Bola",
        "regra": (
            "Estar mais de 2000 uu da bola por tempo prolongado indica "
            "que você está 'fora do play'. Em 2v2/3v3, isso cria uma "
            "situação onde seu teammate está sozinho. Recupere posição "
            "mais próxima da bola ou rotacione para uma zona útil."
        ),
        "porque": (
            "Rocket League é um jogo de posicional. Estar longe da bola "
            "significa que você não pode reagir a mudanças de posse, "
            "não pode dar suporte ao teammate, e cria um 2v1 pro "
            "adversário."
        ),
        "erro_comum": (
            "Ficar 'spectando' do lado oposto do campo, ou estar "
            "muito atrás enquanto a bola está no terço ofensivo."
        ),
        "contexto": {
            "dist_bola_min": 2000,
            "duracao_min_frames": 10,
        },
    },

    "recovery_lenta": {
        "titulo": "Recuperação Lenta After Air / Fall",
        "regra": (
            "Após ficar no ar e cair, tente sempre aterrissar com "
            "um dodge/flap para manter momentum, ou use boost para "
            "recuperar posição rapidamente. Ficar parado no chão "
            "depois de cair te tira do play."
        ),
        "porque": (
            "Recuperações lentas te deixam vulneráveis. Se a bola "
            "mudar de posse enquanto você está no chão, você não "
            "consegue reagir. Profissionais sempre mantêm momentum."
        ),
        "erro_comum": (
            "Cair no chão e ficar parado esperando, ou tentar "
            "andar sem boost perdendo tempo valioso."
        ),
        "contexto": {
            "duracao_min_frames": 8,
        },
    },
}


def get_rule(category: str) -> Optional[dict]:
    """Retorna a regra para uma categoria, ou None se não existe."""
    return RULES.get(category)


def get_rule_text(category: str) -> str:
    """Retorna a regra formatada como texto para o prompt do LLM."""
    rule = RULES.get(category)
    if not rule:
        return f"Sem regra definida para a categoria '{category}'."

    parts = [
        f"## Regra: {rule['titulo']}",
        f"",
        f"**O que fazer:** {rule['regra']}",
        f"",
        f"**Por quê:** {rule['porque']}",
        f"",
        f"**Erro comum:** {rule['erro_comum']}",
    ]
    return "\n".join(parts)


def get_all_rules_summary() -> str:
    """Retorna um resumo de todas as regras para referência."""
    lines = ["# Regras de Rocket League - Resumo\n"]
    for cat, rule in RULES.items():
        lines.append(f"### {cat}")
        lines.append(f"  Título: {rule['titulo']}")
        lines.append(f"  Regra: {rule['regra'][:100]}...")
        lines.append("")
    return "\n".join(lines)

