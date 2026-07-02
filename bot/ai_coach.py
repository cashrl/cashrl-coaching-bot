"""
RLBotPro - AI Coach Module
Usa NVIDIA NIM para gerar dicas personalizadas de coaching.
"""
import json
from collections import Counter
from typing import Dict, Any, Optional, List

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from bot.metric_interpretation import (
    interpret_metric, get_boost_ratio_interpretation, 
    get_status_label, format_interpretation, METRIC_INTERPRETATIONS
)


SYSTEM_PROMPT = """Você é um coach profissional de Rocket League. Analise as estatísticas REAIS do jogador abaixo e gere dicas práticas.

REGRAS OBRIGATÓRIAS:
- Responda SEMPRE em português brasileiro
- Use APENAS os dados numéricos fornecidos pelo contexto — NUNCA invente dados
- NÃO copie exemplos de formato — use os dados reais para preencher sua resposta
- NÃO use placeholders como XXX, [Nome], ou valores genéricos
- Seja direto e prático (máximo 3 parágrafos)
- Foque nos 2-3 pontos mais importantes para melhorar
- Use os números reais do jogador nas suas explicações (ex: "Seu boost coletado foi 5500u, mas você usou apenas 4800u")
- Formato: título curto + explicação com dados + ação prática
- Se o contexto contiver dados de um replay, use EXATAMENTE esses números
- Se não houver dados disponíveis, diga "Selecione um replay primeiro para eu poder te dar uma resposta com base nos seus dados reais"
- NUNCA diga "como não forneceu suas estatísticas" se houver dados no contexto
- INTERPRETAÇÃO DE MÉTRICAS (SEMPRE USE ESTAS DEFINIÇÕES):
  * Razão boost usado/coletado: 100-115% = NORMAL (inclui boost do spawn); >130% = INEFICIENTE; <80% = MUITO EFICIENTE
  * Distância à bola: 400-650uu = DENTRO DA META; <400 = MUITO PERTO; >650 = DISTANTE
  * Tempo ofensivo: 40-56% = DENTRO DA META; <40% = PASSIVO; >56% = AGRESSIVO
  * Velocidade média: 1400-1700 u/s = DENTRO DA META
  * Tempo supersônico: 12-22% = DENTRO DA META
  * Tempo aéreo alto: 6-12% = DENTRO DA META"""


class AICoach:
    """Coach de IA usando NVIDIA NIM.

    Mantém memória de sessão (chat_history) para que o usuário
    possa referenciar conversas anteriores dentro da mesma abertura do app.
    """

    BASE_URL = "https://integrate.api.nvidia.com/v1"
    MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"

    # Limite de mensagens na janela de contexto (para não estourar tokens)
    MAX_HISTORY = 20

    def __init__(self, api_key: str):
        if not HAS_OPENAI:
            raise ImportError("Lib 'openai' não instalada. Execute: pip install openai")
        if not api_key:
            raise ValueError("API key da NVIDIA não configurada")

        self.client = OpenAI(
            base_url=self.BASE_URL,
            api_key=api_key
        )
        # Memória de sessão: lista de {role, content}
        self.chat_history: List[Dict[str, str]] = []

    # Padrões que indicam que o LLM devolveu template cru
    _TEMPLATE_MARKERS = ["XXX", "[Nome do Jogador]", "[Nome]", "Aguardando suas estat", "Nivel Atual"]

    def _validate_response(self, text: str) -> str:
        """Valida se a resposta do LLM contém dados reais e não template cru."""
        if not text:
            return text
        for marker in self._TEMPLATE_MARKERS:
            if marker in text:
                print(f"[AICoach] Resposta continha template marker '{marker}', descartando.")
                return ""
        return text

    def _is_incomplete_response(self, text: str) -> bool:
        """Verifica se a resposta foi cortada no meio (incompleta)."""
        if not text:
            return True
        # Verificar se termina com pontuação ou se foi cortada
        text = text.rstrip()
        # Se termina com caractere que não é pontuação final, pode estar cortado
        if text and text[-1] not in '.!?。，；：':
            # Verificar se tem parênteses/chaves/colchetes não fechados
            open_parens = text.count('(') - text.count(')')
            open_brackets = text.count('[') - text.count(']')
            open_braces = text.count('{') - text.count('}')
            if open_parens > 0 or open_brackets > 0 or open_braces > 0:
                return True
        return False

    def _safe_call(self, messages: list, temperature: float = 0.7, 
                   max_tokens: int = 800, retries: int = 1) -> str:
        """Chamada segura ao NVIDIA NIM com retry e validação de resposta incompleta."""
        for attempt in range(retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                reply = response.choices[0].message.content
                reply = self._validate_response(reply)
                
                # Se resposta vazia ou inválida, retry
                if not reply and attempt < retries:
                    print(f"[AICoach] Resposta vazia, tentando novamente ({attempt + 1}/{retries})...")
                    continue
                
                # Se resposta incompleta e ainda tem retry, aumentar max_tokens
                if self._is_incomplete_response(reply) and attempt < retries:
                    print(f"[AICoach] Resposta possivelmente incompleta, retry com mais tokens...")
                    max_tokens = min(max_tokens + 400, 2000)
                    continue
                
                return reply
            except Exception as e:
                print(f"[AICoach] Erro na chamada (tentativa {attempt + 1}): {e}")
                if attempt < retries:
                    continue
                return ""
        return ""

    def get_coaching_tips(self, player_stats: Dict[str, Any],
                          baseline: Dict[str, Any],
                          pro_name: str = "Zen") -> str:
        """
        Gera dicas de coaching baseadas nas stats do jogador vs baseline do pro.

        Args:
            player_stats: Stats da última partida do jogador
            baseline: Baseline do profissional (formato {stat: {mean, std, min, max}})
            pro_name: Nome do profissional

        Returns:
            Texto com as dicas geradas pela IA
        """
        user_msg = self._build_prompt(player_stats, baseline, pro_name)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.7, max_tokens=800, retries=1)

    def analyze_replay(self, replay_stats: Dict[str, Any],
                       baseline: Optional[Dict[str, Any]] = None,
                       pro_name: Optional[str] = None) -> str:
        """
        Analisa um replay completo e dá feedback detalhado.

        Args:
            replay_stats: Stats extraídas do replay
            baseline: Baseline do pro (opcional)
            pro_name: Nome do profissional (opcional)

        Returns:
            Análise detalhada em texto
        """
        stats_text = self._format_stats(replay_stats)
        baseline_text = self._format_baseline(baseline, pro_name or "N/A") if baseline else "Baseline não disponível."

        user_msg = f"""Analise este replay de Rocket League e dê um feedback completo:

## Stats do Jogador
{stats_text}

## Baseline do Pro
{baseline_text}

Forneça:
1. Pontos fortes (2-3 itens)
2. Pontos fracos (2-3 itens)
3. Plano de melhoria para as próximas 5 partidas"""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.7, max_tokens=1200, retries=1)

    def chat(self, message: str, context: Optional[str] = None,
             replay_stats: Optional[Dict[str, Any]] = None) -> str:
        """
        Chat livre com o coach de IA, com memória de sessão.

        O histórico da conversa é mantido em self.chat_history e
        enviado a cada chamada (janela deslizante de MAX_HISTORY).
        Isso permite perguntas como "e aquele erro que você citou antes?"
        sem repetir contexto.

        Args:
            message: Mensagem do usuário
            context: Contexto opcional (texto livre)
            replay_stats: Stats do replay atualmente selecionado (opcional)

        Returns:
            Resposta do coach
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Se temos stats do replay, incluir como contexto estruturado
        if replay_stats:
            stats_context = self._format_chat_context(replay_stats)
            messages.append({"role": "system", "content": stats_context})
        elif context:
            messages.append({"role": "system", "content": f"Contexto do jogador:\n{context}"})
        else:
            messages.append({"role": "system", "content": (
                "Nenhum replay selecionado. O jogador ainda não forneceu dados de partida. "
                "Se ele perguntar sobre stats específicas, peça para selecionar um replay primeiro."
            )})

        # Adicionar histórico da sessão (janela deslizante)
        if self.chat_history:
            messages.extend(self.chat_history[-self.MAX_HISTORY:])

        # Adicionar mensagem atual do usuário
        messages.append({"role": "user", "content": message})

        reply = self._safe_call(messages, temperature=0.7, max_tokens=1000, retries=1)
        
        # Se validação descartou, retornar mensagem de erro
        if not reply:
            return "Não consegui gerar uma análise válida. Tente novamente com uma pergunta mais específica."

        # Salvar no histórico da sessão
        self.chat_history.append({"role": "user", "content": message})
        self.chat_history.append({"role": "assistant", "content": reply})

        # Manter janela deslizante
        if len(self.chat_history) > self.MAX_HISTORY:
            self.chat_history = self.chat_history[-self.MAX_HISTORY:]

        return reply

    def _format_chat_context(self, stats: Dict[str, Any]) -> str:
        """
        Formata as stats do replay como contexto para o chat livre.
        Usa os mesmos nomes legíveis e unidades da análise automática.
        """
        duration = stats.get("duration_seconds", 300)
        if duration <= 0:
            duration = 300
        minutes = duration / 60.0

        lines = [
            "## DADOS DO REPLAY ATUAL (use ESTES números nas suas respostas)",
            "",
            f"Resultado: {stats.get('team_zero_score', 0)}-{stats.get('team_one_score', 0)} "
            f"({'VITÓRIA' if stats.get('team_zero_score', 0) > stats.get('team_one_score', 0) else 'DERROTA'})",
            f"Modo: {stats.get('game_mode', '?')} | Mapa: {stats.get('map_name', '?')} | "
            f"Duração: {duration:.0f}s ({minutes:.1f} min)",
            "",
            "### Estatísticas Básicas",
            f"- Gols: {stats.get('goals', 0)}",
            f"- Assistências: {stats.get('assists', 0)}",
            f"- Defesas: {stats.get('saves', 0)}",
            f"- Finalizações: {stats.get('shots', 0)}",
            f"- Score: {stats.get('player_score', 0)}",
            f"- Demos: {stats.get('demos_inflicted', 0)}",
            "",
            "### Posicionamento",
            f"- Distância média à bola: {stats.get('avg_distance_to_ball', 0):.0f}u",
            f"- Tempo perto da bola: {stats.get('time_near_ball_pct', 0):.1f}%",
            f"- Tempo no terço ofensivo: {stats.get('time_offensive_pct', 0):.1f}%",
            "",
            "### Gestão de Boost",
            f"- Boost coletado: {stats.get('boost_collected', 0):.0f}u ({stats.get('boost_collected', 0)/minutes:.0f}u/min)",
            f"- Boost usado: {stats.get('boost_used', 0):.0f}u ({stats.get('boost_used', 0)/minutes:.0f}u/min)",
            f"- Tempo com 100% boost: {stats.get('time_boost_100_pct', 0):.1f}%",
            f"- Tempo sem boost: {stats.get('time_boost_0_pct', 0):.1f}%",
            f"- Tempo com boost baixo (<25%): {stats.get('time_boost_low_pct', 0):.1f}%",
            "",
            "### Velocidade",
            f"- Velocidade média: {stats.get('avg_speed', 0):.0f} u/s",
            f"- Tempo supersônico: {stats.get('time_supersonic_pct', 0):.1f}%",
            "",
            "### Altura Aérea",
            f"- Tempo no chão: {stats.get('time_ground_pct', 0):.1f}%",
            f"- Tempo aéreo baixo: {stats.get('aerial_low_pct', 0):.1f}%",
            f"- Tempo aéreo alto: {stats.get('aerial_high_pct', 0):.1f}%",
            "",
            "### Finalização",
            f"- Velocidade média de chute: {stats.get('shot_speed_avg', 0):.0f} km/h",
            f"- Velocidade média aérea: {stats.get('shot_speed_aerial_avg', 0):.0f} km/h",
            f"- Gols longos (>1500u): {stats.get('long_goal_count', 0)} | "
            f"Médios (500-1500u): {stats.get('medium_goal_count', 0)} | "
            f"Curtos (<500u): {stats.get('short_goal_count', 0)}",
            "",
            "IMPORTANTE: Use APENAS estes números reais nas suas respostas. "
            "NÃO invente dados. Se o jogador perguntar sobre algo que não está nestes dados, "
            "dig que aquele dado não está disponível no replay atual."
        ]

        return "\n".join(lines)

    def _build_prompt(self, player_stats: Dict, baseline: Dict, pro_name: str) -> str:
        """Monta o prompt para dicas de coaching."""
        parts = []

        # Stats principais do jogador
        parts.append("## Última Partida do Jogador")
        key_stats = [
            ("Boost Médio", "boost_avg", "pads"),
            ("Velocidade", "avg_speed", "u/s"),
            ("Supersônico", "time_supersonic", "s"),
            ("Distância Bola", "avg_distance_to_ball", "m"),
            ("Gols", "goals", ""),
            ("Assists", "assists", ""),
            ("Defesas", "saves", ""),
            ("Shots", "shots", ""),
            ("Score", "score", ""),
            ("Win Rate", "win_rate", "%"),
        ]

        for label, key, unit in key_stats:
            value = player_stats.get(key, 0)
            parts.append(f"- {label}: {value}{unit}")

        # Baseline do pro
        parts.append(f"\n## Baseline do Pro ({pro_name})")
        for stat_name, stat_data in baseline.items():
            if isinstance(stat_data, dict) and 'mean' in stat_data:
                parts.append(f"- {stat_name}: {stat_data['mean']:.1f} (±{stat_data.get('std', 0):.1f})")

        parts.append("\nGere 2-3 dicas práticas e específicas para melhorar.")

        return "\n".join(parts)

    def _format_stats(self, stats: Dict) -> str:
        """Formata stats para o prompt."""
        lines = []
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                lines.append(f"- {key}: {value:.1f}")
        return "\n".join(lines)

    def _format_baseline(self, baseline: Dict, pro_name: str) -> str:
        """Formata baseline para o prompt."""
        lines = [f"Baseline de {pro_name}:"]
        for stat_name, stat_data in baseline.items():
            if isinstance(stat_data, dict) and 'mean' in stat_data:
                lines.append(f"- {stat_name}: {stat_data['mean']:.1f} (±{stat_data.get('std', 0):.1f})")
        return "\n".join(lines)

    # ════════════════════════════════════════════════════════════════════
    # PLANO DE TREINO SUGERIDO
    # ════════════════════════════════════════════════════════════════════

    TRAINING_PROMPT = """Você é um coach profissional de Rocket League.

Com base nos erros mais frequentes do jogador esta semana, sugira
2-3 exercícios práticos de treino (training pack ou freeplay).

Formato:
- Nome do exercício
- Onde treinar (Training Pack code, Freeplay, ou Custom Training)
- O que focar (1 frase curta)

Seja prático e específico. Português brasileiro."""

    def suggest_training(self, recent_moments: List[Dict[str, Any]]) -> str:
        """
        Sugere plano de treino baseado nos erros mais frequentes da semana.

        Se moment_detector.py tiver dados, usa categorias de erro.
        Caso contrário, usa métricas agregadas como fallback.

        Args:
            recent_moments: Lista de dicts com keys {category, count} ou
                           {avg_distance, time_near, boost_avg, etc.}

        Returns:
            Texto com sugestões de treino
        """
        if not recent_moments:
            return "Jogue mais partidas para receber sugestões de treino personalizadas."

        # Detectar se temos dados de momentos ou stats agregadas
        has_categories = any('category' in m for m in recent_moments)

        if has_categories:
            # Contar categorias de erro
            cat_counts = Counter(m['category'] for m in recent_moments)
            top_errors = cat_counts.most_common(3)
            errors_text = "\n".join(
                f"- {cat}: {count} ocorrências" for cat, count in top_errors
            )
            user_msg = f"""Erros mais frequentes esta semana:
{errors_text}

Sugira exercícios focados nesses problemas."""
        else:
            # Fallback: stats agregadas
            stats_text = self._format_stats(recent_moments[0] if recent_moments else {})
            user_msg = f"""Stats agregadas recentes:
{stats_text}

Sugira exercícios para melhorar os pontos fracos."""

        messages = [
            {"role": "system", "content": self.TRAINING_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.7, max_tokens=800, retries=1)

    # ════════════════════════════════════════════════════════════════════
    # RESUMO PÓS-JOGO (3 frases automáticas)
    # ════════════════════════════════════════════════════════════════════

    SUMMARY_PROMPT = """Gere um resumo de 3 frases sobre este replay de Rocket League.

Formato:
1. Resultado e contexto geral
2. Ponto forte principal
3. Ponto fraco principal + 1 ação concreta

Seja direto, máximo 3 frases. Português brasileiro."""

    def generate_postgame_summary(self, replay_stats: Dict[str, Any]) -> str:
        """
        Gera resumo automático pós-jogo (3 frases).
        Chamado automaticamente ao analisar um replay.
        """
        stats_text = self._format_stats(replay_stats)
        won = replay_stats.get('team_zero_score', 0) > replay_stats.get('team_one_score', 0)
        user_msg = f"""Resultado: {'VITÓRIA' if won else 'DERROTA'} {replay_stats.get('team_zero_score', 0)}-{replay_stats.get('team_one_score', 0)}
{stats_text}"""

        messages = [
            {"role": "system", "content": self.SUMMARY_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.5, max_tokens=500, retries=1)

    # ════════════════════════════════════════════════════════════════════
    # ANÁLISE DETALHADA DA PARTIDA (bullets cruzados com ações)
    # ════════════════════════════════════════════════════════════════════

    ANALYSIS_PROMPT = """Você é um coach profissional de Rocket League. Analise os dados COMPLETOS desta partida e gere uma análise no formato de bullets.

## REGRAS OBRIGATÓRIAS:
- Responda em português brasileiro, tom direto tipo trophy.gg (curto, sem enrolação)
- Gere entre 3 e 5 bullets (nunca mais que 5)
- Cada bullet DEVE cruzar pelo menos 2 métricas quando fizer sentido
- Cada bullet termina com UMA ação concreta e treinável
- Só comente métricas que REALMENTE destoam — se está bom, não elogie
- Se tudo estiver consistente, 2 bullets bastam
- Use SOMENTE os números fornecidos nos dados abaixo. NÃO invente detalhes específicos (tipo de gol, distância de chute, contexto de jogada) que não estejam explicitamente nos dados.
- Formato de cada bullet: **Título curto** — 1-2 frases cruzando métricas com dados → 1 frase de ação

## INTERPRETAÇÃO DE MÉTRICAS (USE ESTAS DEFINIÇÕES):
- Razão boost usado/coletado: 100-115% = NORMAL (inclui boost do spawn); >130% = INEFICIENTE; <80% = MUITO EFICIENTE
- Distância à bola: 400-650uu = DENTRO DA META; <400 = MUITO PERTO; >650 = DISTANTE
- Tempo ofensivo: 40-56% = DENTRO DA META; <40% = PASSIVO; >56% = AGRESSIVO
- Velocidade média: 1400-1700 u/s = DENTRO DA META
- Tempo supersônico: 12-22% = DENTRO DA META

## DADOS DA PARTIDA:
{stats_text}"""

    def generate_match_analysis(self, replay_stats: Dict[str, Any]) -> str:
        """
        Gera análise detalhada da partida com bullets cruzando métricas.

        Args:
            replay_stats: Stats completas extraídas do replay

        Returns:
            Texto com 3-5 bullets de análise detalhada
        """
        # Montar todas as métricas relevantes de forma organizada
        duration = replay_stats.get('duration_seconds', 300)
        if duration <= 0:
            duration = 300  # fallback para 5 min se dados ausentes
        minutes = duration / 60.0

        sections = []

        # Resultado
        won = replay_stats.get('team_zero_score', 0) > replay_stats.get('team_one_score', 0)
        sections.append(f"Resultado: {'VITÓRIA' if won else 'DERROTA'} "
                       f"{replay_stats.get('team_zero_score', 0)}-{replay_stats.get('team_one_score', 0)} "
                       f"({replay_stats.get('game_mode', '?')}, {replay_stats.get('map_name', '?')})")
        sections.append(f"Duração: {duration:.0f}s ({minutes:.1f} min)")

        # Básicas
        sections.append("\n## Estatísticas Básicas")
        for key, label in [('goals', 'Gols'), ('assists', 'Assistências'),
                          ('saves', 'Defesas'), ('shots', 'Finalizações'),
                          ('player_score', 'Score'), ('demos_inflicted', 'Demos')]:
            val = replay_stats.get(key, 0)
            sections.append(f"- {label}: {val}")

        # Posicionamento
        sections.append("\n## Posicionamento")
        avg_dist = replay_stats.get('avg_distance_to_ball', 0)
        time_near = replay_stats.get('time_near_ball_pct', 0)
        time_off = replay_stats.get('time_offensive_pct', 0)
        sections.append(f"- Distância média à bola: {avg_dist:.0f}u")
        sections.append(f"- Tempo perto da bola: {time_near:.1f}%")
        sections.append(f"- Tempo no terço ofensivo: {time_off:.1f}%")

        # Boost
        sections.append("\n## Gestão de Boost")
        boost_col = replay_stats.get('boost_collected', 0)
        boost_used = replay_stats.get('boost_used', 0)
        boost_eff = (boost_used / boost_col * 100) if boost_col > 0 else 0
        sections.append(f"- Boost coletado (de pads no chão): {boost_col:.0f}u ({boost_col/minutes:.0f}u/min)")
        sections.append(f"- Boost usado (total gasto): {boost_used:.0f}u ({boost_used/minutes:.0f}u/min)")
        sections.append(f"- Razão usado/coletado: {boost_eff:.0f}% (100% = gasta exatamente o que coleta; >100% = usou boost inicial do spawn; <100% = sobrou boost coletado)")

        # Velocidade
        sections.append("\n## Velocidade")
        avg_speed = replay_stats.get('avg_speed', 0)
        time_supersonic = replay_stats.get('time_supersonic_pct', 0)
        sections.append(f"- Velocidade média: {avg_speed:.0f} u/s")
        sections.append(f"- Tempo supersônico: {time_supersonic:.1f}%")

        # Altura aérea
        aerial_high = replay_stats.get('aerial_high_pct', 0)
        aerial_low = replay_stats.get('aerial_low_pct', 0)
        ground = replay_stats.get('time_ground_pct', 0)
        sections.append(f"- Tempo no chão: {ground:.1f}%")
        sections.append(f"- Tempo aéreo baixo: {aerial_low:.1f}%")
        sections.append(f"- Tempo aéreo alto: {aerial_high:.1f}%")

        # Finalização
        shot_speed = replay_stats.get('shot_speed_avg', 0)
        shot_speed_air = replay_stats.get('shot_speed_aerial_avg', 0)
        long_goals = replay_stats.get('long_goal_count', 0)
        medium_goals = replay_stats.get('medium_goal_count', 0)
        short_goals = replay_stats.get('short_goal_count', 0)
        sections.append(f"- Velocidade média de finalização: {shot_speed:.0f} km/h (0 = sem dados)")
        sections.append(f"- Velocidade média aérea: {shot_speed_air:.0f} km/h (0 = sem dados)")
        sections.append(f"- Gols longos (>1500u): {long_goals} | Médios (500-1500u): {medium_goals} | Curtos (<500u): {short_goals}")

        stats_text = "\n".join(sections)

        user_msg = self.ANALYSIS_PROMPT.format(stats_text=stats_text)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.6, max_tokens=1200, retries=1)

    # ════════════════════════════════════════════════════════════════════
    # COMPARAÇÃO PRO — Resumo + Explicações por Métrica
    # ════════════════════════════════════════════════════════════════════

    RECAP_PROMPT = (
        "Você é um coach profissional de Rocket League.\n"
        "Gere um resumo curto (2-3 frases) da performance do jogador comparada ao profissional.\n\n"
        "Formato:\n"
        "1. Contexto geral (resultado + score composto)\n"
        "2. Maior destaque (melhor skill score)\n"
        "3. Ponto-chave para melhorar (pior skill score)\n\n"
        "Seja direto. Português brasileiro. Máximo 3 frases."
    )

    METRIC_PROMPT = (
        "Você é um coach profissional de Rocket League.\n"
        "O jogador teve a seguinte métrica comparada ao profissional:\n\n"
        "- Métrica: {label}\n"
        "- Valor do jogador: {value} {unit}\n"
        "- Média profissional: {pro_avg} {unit}\n"
        "- Status: {status_label}\n\n"
        "Gere UMA frase curta explicando o que isso significa e como o jogador pode melhorar.\n"
        "Português brasileiro. Máximo 2 frases."
    )

    STATUS_LABELS = {
        "muito_baixo": "Muito abaixo do profissional",
        "abaixo": "Abaixo da meta profissional",
        "dentro_meta": "Dentro da meta profissional",
        "acima": "Acima da meta profissional",
        "muito_alto": "Muito acima do profissional",
    }

    def generate_match_recap(self, match_data: Dict[str, Any],
                             comparison: Dict[str, Any]) -> str:
        """Gera um resumo curto da performance vs profissional."""
        skills = comparison.get("skill_scores", {})
        composite = comparison.get("composite", 0)
        best_skill = max(skills, key=skills.get) if skills else "N/A"
        worst_skill = min(skills, key=skills.get) if skills else "N/A"
        skill_labels = {
            "movimentacao": "Movimentação",
            "competencia_aerea": "Competência Aérea",
            "posicionamento_campo": "Posicionamento de Campo",
            "gestao_de_boost": "Gestão de Boost",
        }
        won = match_data.get("team_zero_score", 0) > match_data.get("team_one_score", 0)
        user_msg = (
            f"Resultado: {'VITÓRIA' if won else 'DERROTA'} "
            f"{match_data.get('team_zero_score', 0)}-{match_data.get('team_one_score', 0)}\n"
            f"Score composto: {composite}/100\n"
            f"Melhor skill: {skill_labels.get(best_skill, best_skill)} ({skills.get(best_skill, 0)}/100)\n"
            f"Pior skill: {skill_labels.get(worst_skill, worst_skill)} ({skills.get(worst_skill, 0)}/100)"
        )
        messages = [
            {"role": "system", "content": self.RECAP_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.5, max_tokens=500, retries=1)

    def generate_metric_explanation(self, label: str, value: float,
                                    pro_avg: float, unit: str,
                                    status: str) -> str:
        """Gera explicação curta para métrica com status anômalo."""
        if status not in ("muito_baixo", "muito_alto"):
            return ""
        status_label = self.STATUS_LABELS.get(status, status)
        user_msg = self.METRIC_PROMPT.format(
            label=label, value=round(value, 1),
            pro_avg=round(pro_avg, 1), unit=unit,
            status_label=status_label,
        )
        messages = [
            {"role": "system", "content": "Coach de Rocket League. Responda em português brasileiro. Maximo 2 frases."},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.5, max_tokens=300, retries=1)

    # ════════════════════════════════════════════════════════════════════
    # COACHING PONTUAL POR MOMENTO
    # ════════════════════════════════════════════════════════════════════

    MOMENT_COACH_PROMPT = """Você é um coach profissional de Rocket League.

Analise o momento específico abaixo e explique em 2-3 frases:
1. O que o jogador fez (ação detectada)
2. O que a regra geral diz para essa situação
3. O que profissionais tipicamente fazem nesse cenário (baseline)
4. O que o jogador deveria ter feito

Seja direto, prático, e use português brasileiro. Não invente dados."""

    def coach_moment(
        self,
        category: str,
        context: Dict[str, Any],
        rule_text: str,
        pro_baseline: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Gera coaching pontual para um momento detectado.

        Args:
            category: Categoria do momento (hesitacao, boost_baixo_perigoso, etc.)
            context: Dados contextuais do momento (boost, posição, velocidade, etc.)
            rule_text: Texto da regra fixa para essa categoria
            pro_baseline: Baseline dos pros para essa categoria (opcional)

        Returns:
            Texto com a explicação do coach
        """
        # Montar contexto do jogador
        ctx_lines = []
        for k, v in context.items():
            ctx_lines.append(f"- {k}: {v}")
        ctx_text = "\n".join(ctx_lines)

        # Montar baseline dos pros
        pro_text = "Baseline de pros não disponível."
        if pro_baseline:
            dist = pro_baseline.get("distribuicao", {})
            if dist:
                pattern_lines = []
                for action, info in dist.items():
                    pattern_lines.append(f"  - {action}: {info['pct']:.0f}%")
                pro_text = (
                    f"Padrão dominante dos pros: {pro_baseline.get('dominant_pattern', '?')}\n"
                    f"Distribuição:\n" + "\n".join(pattern_lines)
                )

        user_msg = f"""## Momento Detectado: {category}

## Contexto do Jogador
{ctx_text}

## Regra Fixa
{rule_text}

## Baseline dos Pros
{pro_text}"""

        messages = [
            {"role": "system", "content": self.MOMENT_COACH_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        return self._safe_call(messages, temperature=0.6, max_tokens=800, retries=1)


def create_coach(api_key: str) -> Optional[AICoach]:
    """
    Factory para criar instância do AICoach.

    Args:
        api_key: Chave API da NVIDIA

    Returns:
        Instância do AICoach ou None se erro
    """
    if not api_key:
        print("Chave API da NVIDIA não configurada.")
        print("Adicione 'nvidia_api_key' no config.json.")
        return None

    if not HAS_OPENAI:
        print("Lib 'openai' não instalada.")
        print("Execute: pip install openai")
        return None

    try:
        return AICoach(api_key)
    except Exception as e:
        print(f"Erro ao criar AICoach: {e}")
        return None
