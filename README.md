# RLBot Pro

Dashboard de análise de Rocket League que monitora replays, compara com profissionais e mostra estatísticas em tempo real.

## Funcionalidades

- **Dashboard** - Visualização completa com cards, gráficos e comparação com pros
- **Rank em Tempo Real** - Rank por playlist (1v1, 2v2, 3v3) via tracker.gg
- **Watcher** - Monitora a pasta de replays em tempo real (auto-upload)
- **Análise** - Extrai stats detalhadas via Ballchasing API
- **Comparação** - Compara suas stats com baselines de profissionais
- **Histórico** - Lista expandível de todas as partidas com métricas
- **Evolução** - Tabela de growth com variação e tendência

## Pré-requisitos

- Python 3.10+
- Licença do RLBotPro (obtida via bot Discord)
- Token da API do [Ballchasing](https://ballchasing.com) (opcional)

## Instalação

```bash
# Clone o repositório
git clone https://github.com/cashrl/cashrl-coaching-bot.git
cd cashrl-coaching-bot

# Instale as dependências
pip install -r requirements.txt

# Configure o .env (ver seções abaixo)
```

## Configuração

### 1. Licença (obrigatório)

Na primeira execução, o app vai pedir seu **Discord ID**. Para pegar:

1. Abra o Discord > **Configurações** > **Avançado**
2. Ative **Modo Desenvolvedor**
3. Volte ao chat, clique com botão direito no seu perfil
4. Selecione **Copiar ID**

Cole o ID quando solicitado. Ele é salvo no `config.json` para não pedir de novo.

**Para obter uma licença:** entre no servidor Discord do RLBotPro e rode o comando `/criar-id`.

**Problemas com licença?** O app funciona por 7 dias sem conexão (cache local). Se expirar ou estiver bloqueado, uma mensagem clara será exibida com instruções.

### 2. Rocket League Rank (via RapidAPI)

O rank do Player Card vem do [tracker.gg](https://rocketleague.tracker.network) via RapidAPI. É uma fonte não-oficial — dados podem ficar temporariamente indisponíveis.

**Nick no Rocket League:** Configure seu nick do jogo (Epic Games) em **Settings** > **Rocket League**. Este nick é usado para buscar seu rank.

#### Setup

1. Acesse [rapidapi.com/rocket-league-rocket-league-default/api/rocket-league1](https://rapidapi.com/rocket-league-rocket-league-default/api/rocket-league1)
2. Crie uma conta gratuita no RapidAPI
3. Assine o plano **Basic** (gratuito, com limite de requests)
4. Copie sua **X-RapidAPI-Key**
5. Coloque no `.env`:

```env
RAPIDAPI_KEY=sua_chave_aqui
```

**Limitações conhecidas:**
- Rate limit no plano gratuito (requests por mês)
- Dados podem ficar defasados por alguns minutos após partidas
- Em caso de indisponibilidade, o app mostra o último rank conhecido com aviso visual

### 3. Ballchasing API (opcional — para análise de replays)

1. Acesse [ballchasing.com](https://ballchasing.com)
2. Crie uma conta e gere uma API key
3. Coloque no `config.json`:

```json
{
  "ballchasing_api_key": "sua_chave_aqui"
}
```

## Arquivo `.env`

```env
# Discord Bot (para o license bot)
DISCORD_TOKEN=SEU_DISCORD_TOKEN_AQUI

# GitHub Gist (para armazenar licenças)
GIST_ID=6095fdd8e5d01d502a9fceb2e0d88927

# Discord OAuth2 — PKCE (sem client_secret)
DISCORD_CLIENT_ID=1521988282530136276

# Rocket League API (RapidAPI)
RAPIDAPI_KEY=SUA_RAPIDAPI_KEY_AQUI
```

## Uso

```bash
python main.py
```

## Estrutura

```
RLBotPro/
├── main.py              # Entry point
├── discord_auth.py      # OAuth2 Discord (PKCE, porta 47182)
├── license.py           # Validação de licença via Gist
├── database.py          # SQLite (matches + baselines + rank cache)
├── config.json          # Configurações
├── .env                 # Chaves secretas (NUNCA versionar)
├── requirements.txt     # Dependências
├── bot/
│   ├── rank_fetcher.py  # Busca rank via RapidAPI (tracker.gg)
│   ├── ai_coach.py      # AI coaching via NVIDIA NIM
│   ├── analyzer.py      # Análise de replays
│   ├── comparer.py      # Comparação com pros
│   ├── uploader.py      # Upload para Ballchasing
│   └── watcher.py       # Monitor de pasta
├── dashboard/
│   └── ui.py            # Interface NiceGUI
└── rlbotpro-license-bot/
    ├── bot.py           # Bot Discord (gerencia licenças)
    └── README.md        # Docs do bot
```

## Tecnologias

- **NiceGUI** - Interface desktop (pywebview)
- **SQLite** - Banco de dados local
- **RapidAPI** - Dados de rank (tracker.gg)
- **Ballchasing API** - Dados de replays
- **Watchdog** - Monitor de arquivos

## Licença

MIT
