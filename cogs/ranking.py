# cogs/ranking.py
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
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

async def fetch_api_com_retry(session, url, headers, max_tentativas=3):
    for tentativa in range(max_tentativas):
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resposta:
                if resposta.status == 200:
                    return await resposta.json()
                if resposta.status == 429:
                    await asyncio.sleep(3 * (tentativa + 1))
                    continue
                if resposta.status >= 500:
                    await asyncio.sleep(2 * (tentativa + 1))
                    continue
                return None
        except asyncio.TimeoutError:
            await asyncio.sleep(2 * (tentativa + 1))
        except Exception:
            await asyncio.sleep(2 * (tentativa + 1))
    return None

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ranking_guilda", description="Mostra o ranking dos membros da guilda por pontos BR")
    async def ranking_guilda(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        id_servidor = str(interaction.guild_id)
        
        # Buscar guilda FF registrada
        db_server = supabase.table("servidores").select("id_guilda_ff").eq("id_discord", id_servidor).execute()
        guilda_ff_id = str(db_server.data[0]["id_guilda_ff"]) if db_server.data else None
        
        db_res = supabase.table("membros_verificados").select("id_discord, id_ff, nick_ff").eq("id_servidor", id_servidor).execute()
        
        if not db_res.data:
            return await interaction.followup.send("❌ Nenhum membro verificado encontrado neste servidor.")
        
        # Tentar usar cache primeiro
        db_cache = supabase.table("ranking_cache").select("*").eq("guilda_id", id_servidor).execute()
        ranking_data = []
        
        if db_cache.data and len(db_cache.data) == len(db_res.data):
            for cache in db_cache.data:
                # Buscar nick FF do banco de membros
                nick_db = "—"
                for m in db_res.data:
                    if m["id_discord"] == cache["usuario_id"]:
                        nick_db = m.get("nick_ff", "—")
                        break
                
                ranking_data.append({
                    "discord_id": cache["usuario_id"],
                    "nick_ff": nick_db,
                    "br_pontos": cache.get("ranking_points", 0),
                    "rank_tier": cache.get("rank_tier", 0),
                    "nivel": cache.get("nivel", 0),
                    "likes": cache.get("likes", 0),
                    "uid": "—",
                    "na_guilda": True
                })
        else:
            session = self.bot.session
            headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
            
            for membro in db_res.data:
                uid = membro.get("id_ff")
                if not uid:
                    continue
                
                url = f"{config.API_VERCEL_URL}?uid={uid}"
                dados = await fetch_api_com_retry(session, url, headers)
                
                if dados:
                    basic_info = dados.get("basicInfo", {})
                    clan_info = dados.get("clanInfo", {})
                    
                    br_pontos = int(basic_info.get("rankingPoints", 0))
                    rank_tier = basic_info.get("rank", 0)
                    nivel = basic_info.get("level", 0)
                    likes = basic_info.get("liked", 0)
                    nick_ff = basic_info.get("nickname", membro.get("nick_ff", "Desconhecido"))
                    
                    # Verificar se está na guilda FF
                    clan_id = str(clan_info.get("clanId", ""))
                    na_guilda = True
                    if guilda_ff_id and clan_id != guilda_ff_id:
                        na_guilda = False
                    
                    ranking_data.append({
                        "discord_id": membro["id_discord"],
                        "nick_ff": nick_ff,
                        "br_pontos": br_pontos,
                        "rank_tier": rank_tier,
                        "nivel": nivel,
                        "likes": likes,
                        "uid": uid,
                        "na_guilda": na_guilda
                    })
                    
                    supabase.table("ranking_cache").upsert({
                        "usuario_id": membro["id_discord"],
                        "guilda_id": id_servidor,
                        "ranking_points": br_pontos,
                        "rank_tier": str(rank_tier),
                        "nivel": nivel,
                        "likes": likes,
                        "data_atualizacao": datetime.now(timezone.utc).isoformat()
                    }).execute()
                else:
                    # API falhou após 3 tentativas
                    ranking_data.append({
                        "discord_id": membro["id_discord"],
                        "nick_ff": membro.get("nick_ff", "Desconhecido"),
                        "br_pontos": 0,
                        "rank_tier": 0,
                        "nivel": 0,
                        "likes": 0,
                        "uid": uid,
                        "na_guilda": None  # Não sabemos
                    })
        
        if not ranking_data:
            return await interaction.followup.send("❌ Não foi possível obter os dados de ranking dos membros.")
        
        ranking_data.sort(key=lambda x: x["br_pontos"], reverse=True)
        
        embed = discord.Embed(
            title="🏆 Ranking da Guilda - Battle Royale",
            description="Top membros por pontos de ranking BR",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        
        top_10 = ranking_data[:10]
        
        ranking_text = ""
        emojis = ["🥇", "🥈", "🥉"] + [f"**{i}.**" for i in range(4, 11)]
        
        for i, membro in enumerate(top_10):
            emoji = emojis[i] if i < len(emojis) else f"**{i+1}.**"
            patente = calcular_patente(membro["br_pontos"])
            discord_member = interaction.guild.get_member(int(membro["discord_id"]))
            mention = discord_member.mention if discord_member else f"ID: {membro['discord_id']}"
            
            status_guilda = ""
            if membro["na_guilda"] is False:
                status_guilda = " ⚠️"
            elif membro["na_guilda"] is None:
                status_guilda = " ❓"
            
            ranking_text += f"{emoji} {mention}{status_guilda}\n"
            ranking_text += f"    `{membro['nick_ff']}` | {patente} | **{membro['br_pontos']}** pts\n\n"
        
        embed.description = ranking_text
        embed.set_footer(text=f"Total: {len(ranking_data)} | ⚠️=Fora da guilda | ❓=Erro API | Atualizado: {datetime.now().strftime('%H:%M')}")
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="meu_ranking", description="Mostra a tua posição no ranking da guilda")
    async def meu_ranking(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        id_servidor = str(interaction.guild_id)
        id_usuario = str(interaction.user.id)
        
        db_user = supabase.table("membros_verificados").select("id_ff, nick_ff").eq("id_discord", id_usuario).eq("id_servidor", id_servidor).execute()
        
        if not db_user.data:
            return await interaction.followup.send("❌ Não estás registado neste servidor. Usa `/entrar` primeiro.")
        
        uid = db_user.data[0]["id_ff"]
        session = self.bot.session
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        
        url = f"{config.API_VERCEL_URL}?uid={uid}"
        dados = await fetch_api_com_retry(session, url, headers)
        
        if not dados:
            return await interaction.followup.send("❌ Erro ao buscar dados do jogo. Tenta de novo.")
        
        basic_info = dados.get("basicInfo", {})
        br_pontos = int(basic_info.get("rankingPoints", 0))
        nivel = basic_info.get("level", 0)
        likes = basic_info.get("liked", 0)
        nick_ff = basic_info.get("nickname", db_user.data[0].get("nick_ff", "Desconhecido"))
        
        # Usar cache para calcular posição (mais rápido)
        db_cache = supabase.table("ranking_cache").select("usuario_id, ranking_points").eq("guilda_id", id_servidor).execute()
        
        posicao = 1
        if db_cache.data:
            for cache in db_cache.data:
                if cache["usuario_id"] != id_usuario:
                    if cache.get("ranking_points", 0) > br_pontos:
                        posicao += 1
        else:
            # Sem cache, buscar API para cada membro
            db_ranking = supabase.table("membros_verificados").select("id_ff").eq("id_servidor", id_servidor).execute()
            for membro in db_ranking.data:
                if membro["id_ff"] != uid:
                    url_outro = f"{config.API_VERCEL_URL}?uid={membro['id_ff']}"
                    dados_outro = await fetch_api_com_retry(session, url_outro, headers)
                    if dados_outro:
                        pontos_outro = int(dados_outro.get("basicInfo", {}).get("rankingPoints", 0))
                        if pontos_outro > br_pontos:
                            posicao += 1
        
        patente = calcular_patente(br_pontos)
        
        embed = discord.Embed(
            title=f"🏆 Teu Ranking - #{posicao}",
            description=f"A tua posição na guilda **{interaction.guild.name}**",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        
        embed.add_field(name="👤 Nick FF", value=f"`{nick_ff}`", inline=True)
        embed.add_field(name="📊 Posição", value=f"**#{posicao}**", inline=True)
        embed.add_field(name="🌍 Patente", value=patente, inline=True)
        embed.add_field(name="🎯 Pontos BR", value=f"**{br_pontos}**", inline=True)
        embed.add_field(name="📈 Nível", value=f"**{nivel}**", inline=True)
        embed.add_field(name="❤️ Likes", value=f"**{likes}**", inline=True)
        
        embed.set_footer(text="S.art Engine • Ranking da Guilda")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="atualizar_ranking", description="Força a atualização dos dados de ranking")
    async def atualizar_ranking(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas admins podem atualizar o ranking.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        id_servidor = str(interaction.guild_id)
        db_res = supabase.table("membros_verificados").select("id_discord, id_ff").eq("id_servidor", id_servidor).execute()
        
        if not db_res.data:
            return await interaction.followup.send("❌ Nenhum membro verificado encontrado.")
        
        session = self.bot.session
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        atualizados = 0
        
        for membro in db_res.data:
            uid = membro.get("id_ff")
            if not uid:
                continue
            
            url = f"{config.API_VERCEL_URL}?uid={uid}"
            dados = await fetch_api_com_retry(session, url, headers)
            
            if dados:
                basic_info = dados.get("basicInfo", {})
                supabase.table("ranking_cache").upsert({
                    "usuario_id": membro["id_discord"],
                    "guilda_id": id_servidor,
                    "ranking_points": int(basic_info.get("rankingPoints", 0)),
                    "rank_tier": str(basic_info.get("rank", 0)),
                    "nivel": basic_info.get("level", 0),
                    "likes": basic_info.get("liked", 0),
                    "data_atualizacao": datetime.now(timezone.utc).isoformat()
                }).execute()
                atualizados += 1
        
        await interaction.followup.send(f"✅ Ranking atualizado! **{atualizados}** de **{len(db_res.data)}** membros processados.")

async def setup(bot):
    await bot.add_cog(Ranking(bot))
