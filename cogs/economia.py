# cogs/economia.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from database import supabase


def get_emoji_moeda(guild_id):
    try:
        db = supabase.table("economia_config").select("emoji_moeda").eq("guilda_id", str(guild_id)).execute()
        if db.data and db.data[0].get("emoji_moeda"):
            return db.data[0]["emoji_moeda"]
    except Exception:
        pass
    return "<:moedas:1547276353420656794>"




def ler_config(guild_id):
    try:
        db = supabase.table("economia_config").select("*").eq("guilda_id", str(guild_id)).execute()
        return db.data[0] if db.data else {}
    except Exception:
        return {}


def adicionar_moedas(guild_id, user_id, quantidade):
    try:
        db_user = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(user_id)).eq("id_servidor", str(guild_id)).execute()
        saldo_atual = db_user.data[0]["moedas"] if db_user.data and db_user.data[0].get("moedas") is not None else 0
        supabase.table("membros_verificados").update({"moedas": saldo_atual + int(quantidade)}).eq("id_discord", str(user_id)).eq("id_servidor", str(guild_id)).execute()
    except Exception:
        pass


def get_saldo(guild_id, user_id):
    try:
        db = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(user_id)).eq("id_servidor", str(guild_id)).execute()
        if db.data:
            return db.data[0].get("moedas") or 0
    except Exception:
        pass
    return 0


def get_top(guild_id, limite=10):
    try:
        db = supabase.table("membros_verificados").select("moedas", "id_discord").eq("id_servidor", str(guild_id)).gt("moedas", 0).order("moedas", desc=True).limit(limite).execute()
        return db.data or []
    except Exception:
        return []


def pode_ganhar_hoje(guild_id, user_id):
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        db = supabase.table("economia_daily").select("*").eq("user_id", str(user_id)).eq("servidor_id", str(guild_id)).eq("data", hoje).execute()
        if db.data:
            return not db.data[0].get("usado", False)
    except Exception:
        pass
    return True


def marcar_daily(guild_id, user_id):
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        supabase.table("economia_daily").upsert({"user_id": str(user_id), "servidor_id": str(guild_id), "data": hoje, "usado": True}).execute()
    except Exception:
        pass


class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="saldo", description="Mostra o teu saldo de moedas no servidor")
    async def saldo(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.response.send_message("❌ A economia está desativada neste servidor.", ephemeral=True)

        saldo_atual = get_saldo(guild_id, user_id)
        nome_moeda = cfg.get("nome_moeda", "moedas")
        emoji_moeda = get_emoji_moeda(interaction.guild_id)
        embed = discord.Embed(
            title=f"{emoji_moeda} Carteira de {interaction.user.display_name}",
            description=f"Saldo atual: **{saldo_atual}** {nome_moeda}",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_footer(text="Ganha moedas participando no servidor!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="topmoedas", description="Mostra o top 10 membros com mais moedas")
    async def topmoedas(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.response.send_message("❌ A economia está desativada neste servidor.", ephemeral=True)

        top = get_top(guild_id, 10)
        if not top:
            return await interaction.response.send_message("❌ Ainda ninguém tem moedas neste servidor.", ephemeral=True)

        nome_moeda = cfg.get("nome_moeda", "moedas")
        emoji_moeda = get_emoji_moeda(interaction.guild_id)
        linhas = []
        for i, item in enumerate(top, 1):
            membro = interaction.guild.get_member(int(item["id_discord"]))
            nome = membro.display_name if membro else f"`{item['id_discord']}`"
            linhas.append(f"**{i}.** {nome} — {emoji_moeda} `{item['moedas']}` {nome_moeda}")

        embed = discord.Embed(
            title=f"{emoji_moeda} Top Moedas do Servidor",
            description="\n".join(linhas),
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_footer(text="Ganha mais moedas participando!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Reseta o teu daily e ganha moedas")
    async def daily(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.response.send_message("❌ A economia está desativada neste servidor.", ephemeral=True)

        if not pode_ganhar_hoje(guild_id, user_id):
            return await interaction.response.send_message("❌ Já usaste o daily hoje! Volta amanhã.", ephemeral=True)

        daily_min = cfg.get("moedas_daily_min", 5)
        daily_max = cfg.get("moedas_daily_max", 15)
        import random
        quantidade = random.randint(daily_min, daily_max)
        adicionar_moedas(guild_id, user_id, quantidade)
        marcar_daily(guild_id, user_id)
        saldo_atual = get_saldo(guild_id, user_id)
        nome_moeda = cfg.get("nome_moeda", "moedas")
        emoji_moeda = get_emoji_moeda(interaction.guild_id)

        embed = discord.Embed(
            title=f"✅ Daily Resgatado! {emoji_moeda}",
            description=f"Ganhas-te **{quantidade}** {nome_moeda}!\nSaldo atual: **{saldo_atual}** {nome_moeda}",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_footer(text="Volta amanhã para mais!")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Economia(bot))
