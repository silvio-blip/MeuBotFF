# cogs/pesquisa.py
import discord
from discord import app_commands
from discord.ext import commands
import config
from datetime import datetime, timezone
from database import supabase

def calcular_patente(pontos):
    if pontos >= 6000: return "🏆 Elite / Desafiante"
    elif pontos >= 3200: return "🏅 Mestre"
    elif pontos >= 2600: return "💎 Diamante"
    elif pontos >= 2100: return "💠 Platina"
    elif pontos >= 1600: return "🥇 Ouro"
    elif pontos >= 1300: return "🥈 Prata"
    else: return "🥉 Bronze"

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

    @app_commands.command(name="pesquisar", description="Pesquisa um jogador pelo nome ou UID do Free Fire")
    async def pesquisar(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Verificar limite diário
        db_limite = supabase.table("pesquisa_diaria").select("*").eq("user_id", user_id).eq("data", hoje).execute()
        
        if db_limite.data:
            contador = db_limite.data[0].get("contador", 0)
            if contador >= 3:
                return await interaction.followup.send(
                    "❌ **Limite diário atingido!**\n"
                    "Podes fazer apenas **3 pesquisas por dia**.\n"
                    f"Volta amanhã! 🕐"
                )
            supabase.table("pesquisa_diaria").update({"contador": contador + 1}).eq("user_id", user_id).eq("data", hoje).execute()
        else:
            supabase.table("pesquisa_diaria").insert({"user_id": user_id, "data": hoje, "contador": 1}).execute()
        
        session = self.bot.session
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        dados = None
        tipo = ""
        
        # Se é número → buscar por UID
        if busca.strip().isdigit():
            uid = busca.strip()
            url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
            dados = await fetch_api(session, url, headers)
            tipo = "uid"
        else:
            # Buscar por nome
            url_search = f"{config.API_VERCEL_URL}/api/search?name={busca}"
            resultados = await fetch_api(session, url_search, headers)
            
            if resultados and len(resultados) > 0:
                # Pegar o primeiro resultado
                primeiro = resultados[0]
                uid = primeiro.get("uid") or primeiro.get("accountId")
                if uid:
                    url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
                    dados = await fetch_api(session, url, headers)
                    tipo = "nome"
        
        if not dados:
            return await interaction.followup.send(f"❌ Não encontrei ninguém com **{busca}**.")
        
        basic_info = dados.get("player", dados).get("basicInfo", {})
        clan_info = dados.get("player", dados).get("clanInfo", {})
        
        jogador_nome = basic_info.get("nickname", "Desconhecido")
        uid = basic_info.get("accountId", "—")
        nivel = basic_info.get("level", 0)
        likes = basic_info.get("liked", 0)
        br_pontos = int(basic_info.get("rankingPoints", 0))
        cs_pontos = int(basic_info.get("csRankingPoints", 0))
        head_pic = basic_info.get("headPic", "")
        nome_guilda = clan_info.get("clanName", "Sem Guilda")
        
        patente = calcular_patente(br_pontos)
        
        embed = discord.Embed(
            title=f"🔍 Pesquisa: {jogador_nome}",
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
        
        if head_pic:
            embed.set_thumbnail(url=f"https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/{head_pic}.png")
        
        # Mostrar pesquisas restantes
        db_limite2 = supabase.table("pesquisa_diaria").select("contador").eq("user_id", user_id).eq("data", hoje).execute()
        restantes = 3 - (db_limite2.data[0]["contador"] if db_limite2.data else 0)
        embed.set_footer(text=f"Pesquisas restantes hoje: {restantes}/3")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pesquisa(bot))
