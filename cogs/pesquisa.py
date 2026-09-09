# cogs/pesquisa.py
import discord
from discord import app_commands
from discord.ext import commands
import config
from database import supabase


def calcular_patente(pontos):
    if pontos >= 6000:
        return "🏆 Elite / Desafiante"
    elif pontos >= 3200:
        return "🏅 Mestre"
    elif pontos >= 2600:
        return "💎 Diamante"
    elif pontos >= 2100:
        return " {* Platinum}"
    elif pontos >= 1600:
        return "🥇 Ouro"
    elif pontos >= 1300:
        return "🥈 Prata"
    else:
        return "🥉 Bronze"


def calcular_veterano(data_criacao):
    import time
    if data_criacao < 1000000000:
        return "❓ Desconhecido"
    idade_segundos = int(time.time()) - data_criacao
    um_ano = 31536000
    if idade_segundos >= um_ano * 4:
        return "👑 Lenda Ancestral (4+ Anos)"
    elif idade_segundos >= um_ano * 2:
        return "🎖️ Veterano Experiente (2+ Anos)"
    elif idade_segundos >= um_ano:
        return "⚔️ Soldado Frequente (1+ Ano)"
    else:
        return "azer Novato Promissor"


async def fetch_api(session, url, headers):
    try:
        async with session.get(url, headers=headers, timeout=15) as resposta:
            if resposta.status == 200:
                return await resposta.json()
    except Exception:
        pass
    return None


class Pesquisa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pesquisa", description="Pesquisa um jogador pelo nome ou UID do Free Fire")
    async def pesificar(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer(ephemeral=True)

        session = self.bot.session
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        dados = None
        tipo = ""

        if busca.strip().isdigit():
            uid = busca.strip()
            url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
            dados = await fetch_api(session, url, headers)
            tipo = "uid"
        else:
            url_search = f"{config.API_VERCEL_URL}/api/search?name={busca}"
            resultados = await fetch_api(session, url_search, headers)

            if resultados and len(resultados) > 0:
                primeiro = resultados[0]
                uid = primeiro.get("uid") or primeiro.get("accountId")
                if uid:
                    url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
                    dados = await fetch_api(session, url, headers)
                    tipo = "nome"

        if not dados:
            return await interaction.followup.send(f"❌ Não encontrei ninguém com **{busca}**.")

        if isinstance(dados, dict):
            player_data = dados.get("player", dados)
        else:
            player_data = {}

        basic_info = player_data.get("basicInfo", {}) if isinstance(player_data, dict) else {}
        clan_info = player_data.get("clanInfo", {}) if isinstance(player_data, dict) else {}
        profile_info = player_data.get("profileInfo", {}) if isinstance(player_data, dict) else {}

        jogador_nome = basic_info.get("nickname", "Desconhecido")
        uid = basic_info.get("accountId", "—")
        nivel = basic_info.get("level", 0)
        likes = basic_info.get("liked", 0)
        br_pontos = int(basic_info.get("rankingPoints", 0))
        cs_pontos = int(basic_info.get("csRankingPoints", 0))
        head_pic = basic_info.get("headPic", "")
        avatar_id = profile_info.get("avatarId", "")
        nome_guilda = clan_info.get("clanName", "Sem Guilda")
        ff_criacao = int(basic_info.get("createAt", 0))

        patente = calcular_patente(br_pontos)
        status_veterano = calcular_veterano(ff_criacao)

        thumbnail_id = head_pic or avatar_id

        embed = discord.Embed(
            title=f"🔍 Pesquisa: {jogador_nome}",
            description=f"Informações atualizadas do jogador {jogador_nome}.",
            color=discord.Color.from_rgb(100, 200, 255)
        )

        embed.add_field(name="👤 Nick", value=f"`{jogador_nome}`", inline=True)
        embed.add_field(name="🆔 UID", value=f"`{uid}`", inline=True)
        embed.add_field(name="🛡️ Guilda", value=f"**{nome_guilda}**", inline=True)

        embed.add_field(name="📊 Nível", value=f"**{nivel}**", inline=True)
        embed.add_field(name="❤️ Likes", value=f"**{likes}**", inline=True)
        embed.add_field(name="🌍 Patente", value=patente, inline=True)

        embed.add_field(name="🎯 BR", value=f"**{br_pontos}** pts", inline=True)
        embed.add_field(name="⚔️ CS", value=f"**{cs_pontos}** pts", inline=True)
        embed.add_field(name="🌟 Veterano", value=status_veterano, inline=True)

        if ff_criacao > 0:
            embed.add_field(name="📅 Criação", value=f"<t:{ff_criacao}:D>", inline=True)

        if thumbnail_id:
            embed.set_thumbnail(url=f"https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/{thumbnail_id}.png")

        embed.set_footer(text="Pesquisas ilimitadas disponíveis")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Pesquisa(bot))