# RLBot Pro

Dashboard de análise de Rocket League que monitora replays, compara com profissionais e mostra estatísticas em tempo real.

## Funcionalidades

- **Dashboard** - Visualização completa com cards, gráficos e comparação com pros
- **Watcher** - Monitora a pasta de replays em tempo real (auto-upload)
- **Análise** - Extrai stats detalhadas via Ballchasing API
- **Comparação** - Compara suas stats com baselines de profissionais
- **Histórico** - Lista expandível de todas as partidas com métricas
- **Evolução** - Tabela de growth com variação e tendência

## Pré-requisitos

- Python 3.10+
- Token da API do [Ballchasing](https://ballchasing.com)

## Instalação

```bash
# Clone o repositório
git clone https://github.com/cashrl/cashrl-coaching-bot.git
cd cashrl-coaching-bot

# Instale as dependências
pip install -r requirements.txt

# Configure o config.json com seu token
```

## Configuração

Edite `config.json`:

```json
{
  "ballchasing_token": "SEU_TOKEN_AQUI",
  "player_name": "seu_nick",
  "replays_folder": "%UserProfile%/Documents/My Games/Rocket League/TAGame/Demos",
  "pro_to_study": "Zen",
  "playlists": ["ranked-doubles", "ranked-standard", "ranked-duels"],
  "theme": "dark",
  "auto_start_watcher": true
}
```

## Uso

```bash
python main.py
```

## Estrutura

```
RLBotPro/
├── main.py              # Entry point
├── database.py          # SQLite (matches + baselines)
├── config.json          # Configurações
├── requirements.txt     # Dependências
├── bot/
│   ├── analyzer.py      # Análise de replays
│   ├── comparer.py      # Comparação com pros
│   ├── uploader.py      # Upload para Ballchasing
│   └── watcher.py       # Monitor de pasta
└── dashboard/
    └── ui.py            # Interface Flet
```

## Tecnologias

- **Flet 0.85.3** - Interface desktop
- **SQLite** - Banco de dados local
- **Ballchasing API** - Dados de replays
- **Watchdog** - Monitor de arquivos

## Licença

MIT
