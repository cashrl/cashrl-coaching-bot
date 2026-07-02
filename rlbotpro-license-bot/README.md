# RLBotPro License Bot

Bot Discord para gerenciamento de licenças do RLBotPro. Slash commands para criar, consultar, revogar e renovar licenças. Dados armazenados num Gist privado do GitHub.

## Comandos

| Comando | Quem pode | O que faz |
|---------|-----------|-----------|
| `/criar-id` | Qualquer membro | Cria licença vinculada ao seu Discord ID (válida por 6 meses). Só 1 por pessoa. |
| `/status` | Qualquer membro | Mostra status da sua licença (ativa/expirada/revogada) e data de expiração. |
| `/revogar @usuario` | Admin | Revoga a licença do usuário mencionado. |
| `/renovar @usuario` | Admin | Estende a licença do usuário por +6 meses. Se já expirou, conta a partir de hoje. |

## Variáveis de ambiente

| Variável | Descrição | Onde pegar |
|----------|-----------|------------|
| `DISCORD_TOKEN` | Token do bot Discord | [Discord Developer Portal](https://discord.com/developers/applications) > Bot > Token |
| `GITHUB_TOKEN` | Token GitHub com permissão de gist | [GitHub Settings > Tokens](https://github.com/settings/tokens) > Generate (scope: `gist`) |
| `GIST_ID` | ID do Gist privado | Criar um Gist privado e copiar o ID da URL |
| `ADMIN_ROLE_NAME` | Nome do cargo admin (opcional, padrão: "Admin RLBotPro") | Configurar no servidor Discord |

## Setup rápido

### 1. Criar o bot no Discord Developer Portal

1. Acesse https://discord.com/developers/applications
2. Clique em **New Application** → nomeie (ex: "RLBotPro License")
3. Vá em **Bot** → copie o **Token** → salve como `DISCORD_TOKEN`
4. Em **Privileged Gateway Intents**, mantenha tudo desligado (não precisa de intents especiais)
5. Vá em **OAuth2 > URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Use Slash Commands`
6. Copie a URL gerada e abra no navegador para adicionar o bot ao servidor

### 2. Criar o Gist privado

1. Acesse https://gist.github.com
2. Crie um arquivo chamado `licencas.json` com o conteúdo:
```json
{
  "licencas": {}
}
```
3. Marque o Gist como **Secret** (privado)
4. Copie o ID da URL (parte final: `https://gist.github.com/USUARIO/`**`ABC123...`**)
5. Crie um token GitHub em https://github.com/settings/tokens com escopo `gist`
6. Salve o ID como `GIST_ID` e o token como `GITHUB_TOKEN`

### 3. Rodar o bot

```bash
cd rlbotpro-license-bot
pip install -r requirements.txt

# Linux/Mac
export DISCORD_TOKEN="seu-token"
export GITHUB_TOKEN="seu-token-github"
export GIST_ID="id-do-gist"

# Windows (PowerShell)
$env:DISCORD_TOKEN="seu-token"
$env:GITHUB_TOKEN="seu-token-github"
$env:GIST_ID="id-do-gist"

python bot.py
```

### 4. Sincronizar comandos

Na primeira vez que o bot inicia, os slash commands são sincronizados automaticamente. Pode levar até 1 hora para aparecer em todos os servidores (mas costuma ser instantâneo no servidor onde foi adicionado).

## Hospedagem

### Opção 1: Máquina do admin (recomendado para grupo pequeno)

**Prós:**
- Zero custo
- Controle total
- Setup rápido

**Contras:**
- Só funciona quando o PC está ligado
- Se o admin desligar, ninguém cria licença (mas licenças existentes continuam funcionando no app)

**Como fazer:**
- Rodar `python bot.py` em background
- No Windows: usar `pythonw bot.py` ou criar um atalho .bat
- No Linux/Mac: usar `nohup python bot.py &` ou systemd

### Opção 2: Railway (free tier)

**Prós:**
- Online 24/7
- Deploy com GitHub push

**Contras:**
- Free tier tem 500h/mês (suficiente para um bot leve)
- Precisa configurar variáveis de ambiente no painel

**Como fazer:**
1. Criar conta no https://railway.app
2. Conectar o repositório GitHub
3. Adicionar as variáveis de ambiente no painel
4. Deploy automático

### Opção 3: Oracle Cloud Free Tier

**Prós:**
- VM gratuita para sempre (ARM, 4GB RAM)
- Online 24/7

**Contras:**
- Setup mais complexo (SSH, systemd, etc.)
- Precisa manter a VM atualizada

**Recomendação:** Para um grupo de amigos, a **máquina do admin** é suficiente. As licenças já criadas funcionam mesmo com o bot offline (o app RLBotPro consulta o Gist diretamente).

## Como funciona ponta a ponta

1. **Admin cria o bot** e configura no Discord Developer Portal
2. **Membro roda `/criar-id`** no Discord → licença criada no Gist
3. **Membro abre o RLBotPro** → entra com Discord ID → app valida no Gist
4. **Admin roda `/revogar @user`** → licença revogada → próxima vez que o app checar, bloqueia acesso
5. **Admin roda `/renovar @user`** → expiração estendida em 6 meses

## Notas técnicas

- **Duração da licença:** 6 meses a partir da criação
- **Renovação:** se a licença ainda é válida, adiciona 6 meses à data de expiração atual. Se já expirou, 6 meses a partir de hoje.
- **Grandeza:** o app RLBotPro tem uma tolerância de alguns dias offline caso o Gist não esteja acessível
- **Formato do Gist:**
```json
{
  "licencas": {
    "123456789": {
      "nome_discord": "cash the runner",
      "ativada_em": "2026-07-01",
      "expira_em": "2027-01-01",
      "revogada": false
    }
  }
}
```
