"""
RLBotPro - AI Coach Module
Usa NVIDIA NIM para gerar dicas personalizadas de coaching.
"""
import json
from typing import Dict, Any, Optional, List

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


SYSTEM_PROMPT = """Você é um coach profissional de Rocket League. Analise as estatísticas do jogador e a baseline do profissional para gerar dicas práticas e específicas.

Regras:
- Responda SEMPRE em português brasileiro
- Seja direto e prático (máximo 3 parágrafos)
- Foque nos 2-3 pontos mais importantes para melhorar
- Use dados numéricos para sustentar suas dicas
- Não repita o que o jogador já faz bem, foque no que falta
- Formato: título curto + explicação + ação prática"""


class AICoach:
    """Coach de IA usando NVIDIA NIM."""

    BASE_URL = "https://integrate.api.nvidia.com/v1"
    MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"

    def __init__(self, api_key: str):
        if not HAS_OPENAI:
            raise ImportError("Lib 'openai' não instalada. Execute: pip install openai")
        if not api_key:
            raise ValueError("API key da NVIDIA não configurada")

        self.client = OpenAI(
            base_url=self.BASE_URL,
            api_key=api_key
        )

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

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro ao chamar NVIDIA NIM: {e}")
            return ""

    def analyze_replay(self, replay_stats: Dict[str, Any],
                       baseline: Optional[Dict[str, Any]] = None,
                       pro_name: str = "Zen") -> str:
        """
        Analisa um replay completo e dá feedback detalhado.

        Args:
            replay_stats: Stats extraídas do replay
            baseline: Baseline do pro (opcional)
            pro_name: Nome do profissional

        Returns:
            Análise detalhada em texto
        """
        stats_text = self._format_stats(replay_stats)
        baseline_text = self._format_baseline(baseline, pro_name) if baseline else "Baseline não disponível."

        user_msg = f"""Analise este replay de Rocket League e dê um feedback completo:

## Stats do Jogador
{stats_text}

## Baseline do Pro ({pro_name})
{baseline_text}

Forneça:
1. Pontos fortes (2-3 itens)
2. Pontos fracos (2-3 itens)
3. Plano de melhoria para as próximas 5 partidas"""

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro ao chamar NVIDIA NIM: {e}")
            return ""

    def chat(self, message: str, context: Optional[str] = None) -> str:
        """
        Chat livre com o coach de IA.

        Args:
            message: Mensagem do usuário
            context: Contexto opcional (stats atuais, etc.)

        Returns:
            Resposta do coach
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            messages.append({"role": "system", "content": f"Contexto do jogador:\n{context}"})

        messages.append({"role": "user", "content": message})

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro ao chamar NVIDIA NIM: {e}")
            return ""

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
