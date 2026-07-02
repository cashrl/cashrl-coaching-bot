"""
RLBotPro License Bot - Bot Discord para gerenciamento de licenças.

Slash commands:
  /criar-id  - Cria licença para o usuário (1 por pessoa)
  /status    - Mostra status da licença do usuário
  /revogar   - Revoga licença de um usuário (admin only)
  /renovar   - Renova licença de um usuário por +6 meses (admin only)
  /listar    - Lista todas as licenças registradas (admin only)

Variáveis de ambiente necessárias:
  DISCORD_TOKEN   - Token do bot Discord
  GITHUB_TOKEN    - Token GitHub com permissão de gist
  GIST_ID         - ID do Gist privado onde as licenças são salvas
  ADMIN_ROLE_NAME - Nome do cargo admin (padrão: "Admin RLBotPro")
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Carrega .env do diretório do bot
load_dotenv(Path(__file__).parent / ".env")

import discord
from discord import app_commands
from discord.ext import commands
import requests


# ── Configuração ────────────────────────────────────────────────────────────

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GIST_ID = os.environ["GIST_ID"]
ADMIN_ROLE_NAME = os.environ.get("ADMIN_ROLE_NAME", "Admin RLBotPro")

GITHUB_API = "https://api.github.com"

LICENSE_DURATION_MONTHS = 6
GRACE_PERIOD_DAYS = 3
ALLOWED_CHANNEL_ID = int(os.environ.get("ALLOWED_CHANNEL_ID", "1521956532969803907"))


# ── Helpers: GitHub Gist ────────────────────────────────────────────────────

def _gist_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


GIST_FILENAME = "licencas.json"


async def load_licenses() -> dict:
    """Carrega o JSON do Gist (async, não bloqueia o event loop)."""
    def _fetch():
        url = f"{GITHUB_API}/gists/{GIST_ID}"
        resp = requests.get(url, headers=_gist_headers(), timeout=15)
        resp.raise_for_status()
        files = resp.json().get("files", {})
        if GIST_FILENAME not in files:
            raise FileNotFoundError(
                f"Arquivo '{GIST_FILENAME}' não encontrado no Gist. "
                f"Arquivos existentes: {list(files.keys())}"
            )
        return json.loads(files[GIST_FILENAME]["content"])
    return await asyncio.to_thread(_fetch)


async def save_licenses(data: dict) -> None:
    """Sobrescreve o Gist com o JSON atualizado (async, não bloqueia o event loop)."""
    def _save():
        url = f"{GITHUB_API}/gists/{GIST_ID}"
        payload = {
            "files": {
                GIST_FILENAME: {
                    "content": json.dumps(data, indent=2, ensure_ascii=False)
                }
            }
        }
        resp = requests.patch(url, headers=_gist_headers(), json=payload, timeout=15)
        resp.raise_for_status()
    await asyncio.to_thread(_save)


# ── Bot Setup ───────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


async def _check_channel(interaction: discord.Interaction) -> bool:
    """Verifica se o comando foi usado no canal permitido."""
    if interaction.channel_id == ALLOWED_CHANNEL_ID:
        return True
    await interaction.response.send_message(
        "❌ Use este comando no canal correto.",
        ephemeral=True,
    )
    return False


def _is_admin(interaction: discord.Interaction) -> bool:
    """Verifica se o membro tem o cargo admin."""
    if interaction.user.guild_permissions.administrator:
        return True
    return any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles)


# ── /criar-id ───────────────────────────────────────────────────────────────

@bot.tree.command(name="criar-id", description="Cria sua licença do RLBotPro (válida por 6 meses)")
async def criar_id(interaction: discord.Interaction):
    if not await _check_channel(interaction):
        return
    await interaction.response.defer(ephemeral=True)

    discord_id = str(interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    expires = (datetime.now() + timedelta(days=LICENSE_DURATION_MONTHS * 30)).strftime("%Y-%m-%d")

    try:
        data = await load_licenses()
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao acessar o sistema de licenças. Tente novamente mais tarde.\n`{e}`",
            ephemeral=True,
        )
        return

    licencas = data.get("licencas", {})

    # Verificar se já tem licença ativa
    if discord_id in licencas:
        lic = licencas[discord_id]
        if lic.get("expira_em", "") >= today and not lic.get("revogada"):
            await interaction.followup.send(
                f"Você já tem uma licença ativa!\n"
                f"**Expira em:** {lic['expira_em']}\n"
                f"Use `/status` para ver detalhes.",
                ephemeral=True,
            )
            return
        # Licença expirada ou revogada — reativar com nova data
        lic["ativada_em"] = today
        lic["expira_em"] = expires
        lic["revogada"] = False
    else:
        licencas[discord_id] = {
            "nome_discord": interaction.user.display_name,
            "ativada_em": today,
            "expira_em": expires,
            "revogada": False,
        }

    data["licencas"] = licencas

    try:
        await save_licenses(data)
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao salvar a licença. Tente novamente.\n`{e}`",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"✅ Licença criada com sucesso!\n\n"
        f"**Discord ID:** `{discord_id}`\n"
        f"**Criada em:** {today}\n"
        f"**Expira em:** {expires}\n\n"
        f"Para usar o RLBotPro, cole seu Discord ID no app quando solicitado.\n"
        f"**Como pegar:** Configurações > Avançado > Modo Desenvolvedor, "
        f"depois clique com botão direito no seu perfil > Copiar ID.",
        ephemeral=True,
    )


# ── /status ─────────────────────────────────────────────────────────────────

@bot.tree.command(name="status", description="Mostra o status da sua licença do RLBotPro")
async def status(interaction: discord.Interaction):
    if not await _check_channel(interaction):
        return
    await interaction.response.defer(ephemeral=True)

    discord_id = str(interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        data = await load_licenses()
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao acessar o sistema de licenças.\n`{e}`",
            ephemeral=True,
        )
        return

    lic = data.get("licencas", {}).get(discord_id)

    if not lic:
        await interaction.followup.send(
            "Você ainda não tem uma licença.\n"
            "Use `/criar-id` para criar uma.",
            ephemeral=True,
        )
        return

    if lic.get("revogada"):
        status_text = "🚫 **Revogada**"
    elif lic.get("expira_em", "") < today:
        status_text = "⏰ **Expirada**"
    else:
        status_text = "✅ **Ativa**"

    await interaction.followup.send(
        f"**Status da sua licença:**\n\n"
        f"**Status:** {status_text}\n"
        f"**Criada em:** {lic.get('ativada_em', '?')}\n"
        f"**Expira em:** {lic.get('expira_em', '?')}\n",
        ephemeral=True,
    )


# ── /listar ─────────────────────────────────────────────────────────────────

@bot.tree.command(name="listar", description="Lista todas as licenças registradas (admin)")
async def listar(interaction: discord.Interaction):
    if not await _check_channel(interaction):
        return
    if not _is_admin(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        data = await load_licenses()
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao acessar o sistema de licenças.\n`{e}`",
            ephemeral=True,
        )
        return

    licencas = data.get("licencas", {})
    today = datetime.now().strftime("%Y-%m-%d")

    if not licencas:
        await interaction.followup.send(
            "Nenhuma licença registrada.",
            ephemeral=True,
        )
        return

    ativas = []
    revogadas = []
    expiradas = []

    for discord_id, lic in licencas.items():
        nome = lic.get("nome_discord", "Desconhecido")
        expira = lic.get("expira_em", "?")
        revogada = lic.get("revogada", False)

        if revogada:
            revogadas.append(f"🚫 **{nome}** (`{discord_id}`) — expira {expira}")
        elif expira < today:
            expiradas.append(f"⏰ **{nome}** (`{discord_id}`) — expirou {expira}")
        else:
            ativas.append(f"✅ **{nome}** (`{discord_id}`) — expira {expira}")

    total = len(licencas)
    linhas = [f"**📋 Licenças registradas: {total}**\n"]

    if ativas:
        linhas.append(f"**✅ Ativas ({len(ativas)}):**")
        linhas.extend(ativas)
        linhas.append("")
    if expiradas:
        linhas.append(f"**⏰ Expiradas ({len(expiradas)}):**")
        linhas.extend(expiradas)
        linhas.append("")
    if revogadas:
        linhas.append(f"**🚫 Revogadas ({len(revogadas)}):**")
        linhas.extend(revogadas)
        linhas.append("")

    await interaction.followup.send("\n".join(linhas), ephemeral=True)


# ── /revogar ────────────────────────────────────────────────────────────────

@bot.tree.command(name="revogar", description="Revoga a licença de um usuário (admin)")
@app_commands.describe(usuario="Usuário para revogar")
async def revogar(interaction: discord.Interaction, usuario: discord.Member):
    if not await _check_channel(interaction):
        return
    if not _is_admin(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    discord_id = str(usuario.id)

    try:
        data = await load_licenses()
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao acessar o sistema de licenças.\n`{e}`",
            ephemeral=True,
        )
        return

    lic = data.get("licencas", {}).get(discord_id)

    if not lic:
        await interaction.followup.send(
            f"O usuário {usuario.mention} não possui uma licença.",
            ephemeral=True,
        )
        return

    if lic.get("revogada"):
        await interaction.followup.send(
            f"A licença de {usuario.mention} já está revogada.",
            ephemeral=True,
        )
        return

    lic["revogada"] = True
    data["licencas"][discord_id] = lic

    try:
        await save_licenses(data)
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao salvar alteração.\n`{e}`",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"✅ Licença de {usuario.mention} revogada com sucesso.",
        ephemeral=True,
    )


# ── /renovar ────────────────────────────────────────────────────────────────

@bot.tree.command(name="renovar", description="Renova a licença de um usuário por +6 meses (admin)")
@app_commands.describe(usuario="Usuário para renovar")
async def renovar(interaction: discord.Interaction, usuario: discord.Member):
    if not await _check_channel(interaction):
        return
    if not _is_admin(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    discord_id = str(usuario.id)
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    try:
        data = await load_licenses()
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao acessar o sistema de licenças.\n`{e}`",
            ephemeral=True,
        )
        return

    lic = data.get("licencas", {}).get(discord_id)

    if not lic:
        await interaction.followup.send(
            f"O usuário {usuario.mention} não possui uma licença.\n"
            f"Use `/criar-id` no chat do servidor para ele criar.",
            ephemeral=True,
        )
        return

    # Lógica: se a licença ainda não expirou, estende a partir da expiração atual.
    # Se já expirou, conta 6 meses a partir de hoje.
    expira_atual = lic.get("expira_em", today_str)
    try:
        data_expiracao = datetime.strptime(expira_atual, "%Y-%m-%d")
    except ValueError:
        data_expiracao = today

    if data_expiracao >= today:
        nova_expiracao = data_expiracao + timedelta(days=LICENSE_DURATION_MONTHS * 30)
    else:
        nova_expiracao = today + timedelta(days=LICENSE_DURATION_MONTHS * 30)

    lic["expira_em"] = nova_expiracao.strftime("%Y-%m-%d")
    lic["revogada"] = False  # Reativa caso estivesse revogada
    data["licencas"][discord_id] = lic

    try:
        await save_licenses(data)
    except Exception as e:
        await interaction.followup.send(
            f"Erro ao salvar alteração.\n`{e}`",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"✅ Licença de {usuario.mention} renovada!\n"
        f"**Nova data de expiração:** {nova_expiracao.strftime('%Y-%m-%d')}",
        ephemeral=True,
    )


# ── Sync & Start ────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user} (ID: {bot.user.id})")
    print(f"Servidores: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")


def main():
    print("Iniciando RLBotPro License Bot...")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
