# Skill: Auditoria de Precisão de Dados — RLBotPro

## Quando usar
Rode esta auditoria: (1) antes de aprovar qualquer mudança em
`local_analyzer.py`, `ai_coach.py` ou `baseline.py`; (2) periodicamente,
mesmo sem mudança recente, como checagem de rotina; (3) sempre que uma
métrica parecer "estranha demais" (zero cravado, score destoante,
número redondo demais).

O objetivo não é achar bug óbvio (a UI quebrada é fácil de ver). É achar
bug **silencioso**: número errado que parece plausível, texto gerado que
soa confiável mas não é rastreável a dado real. Esse tipo de bug já
passou várias vezes despercebido neste projeto até alguém de fora
(usuário do grupo) notar por acaso.

---

## Categoria 1 — Precisão de dado (o número está certo?)

Todo bug real já encontrado nessa categoria teve a MESMA causa raiz:
uma suposição sobre estrutura de dado que não foi verificada.

**Checklist:**
- [ ] Pegar 1 replay de teste e conferir CADA estatística principal
  (gols, assists, saves, shots) do jogador selecionado contra uma fonte
  independente (Ballchasing, ou o scoreboard nativo do replay) —
  número por número, não "parece certo".
- [ ] Repetir isso pra TODOS os jogadores do lobby, não só o selecionado
  (um bug de mapeamento de índice afeta todo mundo, não só quem você
  testou por acaso).
- [ ] Se o código faz qualquer tipo de mapeamento por ÍNDICE de lista
  (ex: `team_zero[i]` correspondendo a `player_stats[i]`), desconfiar
  por padrão — já causou bug real neste projeto porque as duas listas
  não estavam na mesma ordem. Mapear por ID único (platform_id,
  remote_id) sempre que existir, nunca por posição.
- [ ] Se existe qualquer "fallback" de identificação (ex: escolher
  jogador por "menos gols" quando nome não bate), isso é uma aposta
  silenciosa. Forçar um aviso visível toda vez que o fallback for
  acionado — nunca deixar acontecer sem o usuário saber.
- [ ] Zero cravado em qualquer métrica (0, 0%, 0.0) é suspeito por
  padrão. Zero real de jogo é raro. Verificar se não é exception
  engolida silenciosamente por um try/except retornando 0 como
  fallback.
- [ ] Todo `try/except` no pipeline de análise precisa logar o erro
  real, nunca engolir silenciosamente. Se um except existe sem log,
  isso é o primeiro lugar a olhar quando um número parecer errado.

---

## Categoria 2 — Texto gerado por IA (a explicação é confiável?)

**Checklist:**
- [ ] Fazer uma tabela "claim → campo de dado → valor real" pra CADA
  frase do texto gerado que cita um número ou fato específico. Se uma
  claim não tem campo de dado correspondente, é alucinação — reportar
  antes de aprovar. (Este processo já pegou alucinações reais neste
  projeto: "gol de contra-ataque" e "gol de pressão sustentada" que não
  existiam como campos calculados.)
- [ ] Conferir se o prompt enviado ao LLM inclui a DEFINIÇÃO de cada
  métrica junto com o valor (não só o número cru) — sem isso o modelo
  já interpretou métrica errada (ex: "eficiência de boost 113%"
  interpretado como desperdício quando significava o oposto).
- [ ] Conferir se toda métrica numérica no prompt inclui a UNIDADE
  (uu/s, %, u) — sem isso o modelo já "adivinhou" unidade errada.
- [ ] Procurar por nomes de variável em snake_case vazando pro texto
  final (ex: `avg_distance_to_ball` aparecendo literal em vez de
  "distância média até a bola"). Confirmar que existe um dicionário de
  tradução técnico→legível ANTES do prompt, não confiar no LLM pra
  traduzir sozinho.
- [ ] Testar a MESMA métrica em TODOS os formatos de resposta que o
  projeto tem (bullets, resumo, pontos fortes/fracos, chat livre) e
  comparar a interpretação entre eles. Já aconteceu de a mesma razão de
  boost ser chamada "ineficiente" num formato e "ponto forte" em outro,
  porque cada função decidia sozinha o que é bom/ruim. Deve existir UMA
  fonte de verdade de interpretação (ex: `metric_interpretation.py`)
  compartilhada por todos os formatos.
- [ ] Gerar a resposta e checar se ela termina de forma completa (não
  corta no meio de uma frase ou de uma seção prometida no próprio
  formato pedido). Isso é sintoma de `max_tokens` insuficiente — checar
  TODAS as funções que chamam o LLM, não só a que foi testada, porque
  esse bug já voltou depois de corrigido uma vez por só cobrir uma
  função.
- [ ] Se o texto responde com placeholder/template não preenchido
  ("XXX", "[Nome do Jogador]", "forneça suas estatísticas"), isso
  significa que os dados reais não chegaram no prompt — bug de
  integração, não de LLM.

---

## Categoria 3 — Consistência entre telas/scores

**Checklist:**
- [ ] Se duas métricas/scores diferentes sobem e descem sempre juntos
  em todos os replays testados, desconfiar de redundância — pode ser
  a mesma característica calculada duas vezes com nomes diferentes
  (aconteceu com "Movement" e "Positioning" usando a mesma fórmula de
  distância à bola).
- [ ] Todo score normalizado (0-100) precisa ter a fórmula documentada
  em comentário — sem isso, ninguém consegue julgar se um valor baixo
  é bug ou é real.
- [ ] Campos derivados de contagem (ex: modo de jogo a partir de
  `TeamSize` do header do replay) devem ser cruzados contra uma segunda
  fonte de verificação (ex: contagem real de jogadores extraídos) —
  não confiar em um único campo de metadado do replay sem checagem.

---

## Como rodar esta auditoria

Cole isto na CLI como prompt:

> Rode a auditoria completa descrita em AUDITORIA-RLBOTPRO.md contra o
> estado atual do projeto. Para cada item do checklist, teste com pelo
> menos 1 replay real (ou mais, se o item pedir múltiplos formatos/
> jogadores) e reporte: (a) o item testado, (b) o resultado real
> encontrado, (c) se passou ou falhou, (d) se falhou, a causa raiz antes
> de qualquer correção. Não corrija nada ainda nesta rodada — só
> reporte o estado atual de cada item, pra eu decidir prioridade.

Depois de ver o relatório, você decide o que vale prompt de correção
imediata e o que pode esperar.

## Manutenção desta skill
Toda vez que um bug novo E DIFERENTE dos padrões acima for encontrado
(não uma repetição de categoria já coberta), adicionar um item novo
aqui. Esse arquivo deve crescer junto com o projeto — é a memória
institucional dos erros que já pegaram vocês de surpresa uma vez.

---

## Histórico de Auditorias

### 2026-07-02 - Primeira Rodada Completa

**Resultado:** 14/14 itens PASS

| Categoria | Itens | Passaram | Falharam |
|-----------|-------|----------|----------|
| 1 - Precisão de Dado | 4 | 4 | 0 |
| 2 - Texto Gerado por IA | 7 | 7 | 0 |
| 3 - Consistência entre Telas | 3 | 3 | 0 |

**Resumo:** Estado atual do código está sólido. Todos os bugs conhecidos
(BUG 1-5) já foram corrigidos. Sistema de fallback tem aviso visível.
Métricas são consistentes entre formatos. IA usa dados reais sem alucinações.

**Próximas auditorias:** Rodar antes de qualquer mudança em
`local_analyzer.py`, `ai_coach.py`, ou `baseline.py`.
