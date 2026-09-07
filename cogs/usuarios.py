# cogs/usuarios.py
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import time
import asyncio
import random
import config
from datetime import datetime
from database import supabase


def log_sart(mensagem):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] ⚙️ [S.art] {mensagem}")


IDIOMAS_FF = {
    1: "English", 3: "中文 (繁)", 4: "ไทย", 5: "Tiếng Việt",
    6: "Indonesia", 7: "Português", 8: "Español", 9: "Русский",
    11: "Français", 13: "Türkçe", 14: "हिन्दी", 17: "العربية",
    20: "বাংলা", 21: "Malay"
}


def calcular_patente(pontos):
    if pontos >= 6000: return "🏆 Elite / Desafiante"
    elif pontos >= 3200: return "🏅 Mestre"
    elif pontos >= 2600: return "💎 Diamante"
    elif pontos >= 2100: return "💠 Platina"
    elif pontos >= 1600: return "🥇 Ouro"
    elif pontos >= 1300: return "🥈 Prata"
    else: return "🥉 Bronze"


def calcular_veterano(data_criacao):
    if data_criacao < 1000000000:
        return "❓ Desconhecido"
    idade_segundos = int(time.time()) - data_criacao
    um_ano = 31536000
    if idade_segundos >= um_ano * 4: return "👑 Lenda Ancestral (4+ Anos)"
    elif idade_segundos >= um_ano * 2: return "🎖️ Veterano Experiente (2+ Anos)"
    elif idade_segundos >= um_ano: return "⚔️ Soldado Frequente (1+ Ano)"
    else: return "🔰 Novato Promissor"


class ViewApagarDM(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apagar Mensagem", style=discord.ButtonStyle.secondary, emoji="🗑️", custom_id="apagar_dm_sart")
    async def apagar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        except Exception as e:
            log_sart(f"🚨 Erro ao apagar DM persistente: {e}")


class ViewSelecionarGenero(discord.ui.View):
    def __init__(self, dados_server, bot):
        super().__init__(timeout=300)
        self.dados_server = dados_server
        self.bot = bot

    @discord.ui.select(
        placeholder="Seleciona o teu gênero...",
        options=[
            discord.SelectOption(label="Masculino", value="Masculino", emoji="♂️"),
            discord.SelectOption(label="Feminino", value="Feminino", emoji="♀️"),
            discord.SelectOption(label="Outro", value="Outro", emoji="🧑"),
            discord.SelectOption(label="Prefiro não dizer", value="Prefiro não dizer", emoji="🤐")
        ]
    )
    async def select_genero(self, interaction: discord.Interaction, select: discord.ui.Select):
        genero = select.values[0]
        await interaction.response.send_modal(ModalDadosPessoais(self.dados_server, self.bot, genero))


class ModalDadosPessoais(discord.ui.Modal, title='Dados Pessoais'):
    idade = discord.ui.TextInput(label='Idade', placeholder='Ex: 18', required=True, min_length=1, max_length=3)
    id_ff = discord.ui.TextInput(label='O teu ID do Free Fire', placeholder='Ex: 7648336857', required=True, min_length=5, max_length=15)

    def __init__(self, dados_server, bot, genero):
        super().__init__()
        self.dados_server = dados_server
        self.bot = bot
        self.genero = genero

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            idade_valor = int(self.idade.value.strip())
            if idade_valor < 1 or idade_valor > 120:
                raise ValueError
        except ValueError:
            return await interaction.followup.send("❌ Idade inválida! Insere um número entre 1 e 120.", ephemeral=True)
        
        uid = self.id_ff.value.strip()
        guilda_oficial = str(self.dados_server["id_guilda_ff"])
        url = f"{config.API_VERCEL_URL}/api/player?uid={uid}&fields=basic,profile"
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        
        session = self.bot.session
        try:
            async with session.get(url, headers=headers) as resposta_api:
                if resposta_api.status != 200:
                    return await interaction.followup.send("⚠️ Erro de conexão com a API da Vercel.")
                    
                dados_iniciais = await resposta_api.json()
                clan_id_raw = dados_iniciais.get("clanInfo", {}).get("clanId")
                if not clan_id_raw:
                    return await interaction.followup.send("❌ **Acesso Negado:** Esta conta não está associada a nenhuma guilda no Free Fire.", ephemeral=True)
                clan_id = str(clan_id_raw)
                jogador_nome = dados_iniciais.get("basicInfo", {}).get("nickname", "Desconhecido")
                
                if clan_id != guilda_oficial:
                    return await interaction.followup.send(f"❌ **Acesso Negado:** A conta `{jogador_nome}` está na guilda `{clan_id}`, mas este servidor exige a guilda `{guilda_oficial}`.", ephemeral=True)

                dados_pessoais = {
                    "genero": self.genero,
                    "idade": idade_valor
                }
                
                await interaction.followup.send_modal(ModalConfirmacao(self.dados_server, self.bot, dados_pessoais, uid, jogador_nome))
                
        except Exception as e:
                log_sart(f"🚨 Erro ao iniciar verificação: {e}")
                await interaction.followup.send("🚨 Erro ao iniciar a verificação. Tenta novamente.", ephemeral=True)


class ModalConfirmacao(discord.ui.Modal, title='Confirmação Final'):
    def __init__(self, dados_server, bot, dados_pessoais, uid, jogador_nome):
        super().__init__()
        self.dados_server = dados_server
        self.bot = bot
        self.dados_pessoais = dados_pessoais
        self.uid = uid
        self.jogador_nome = jogador_nome

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guilda_oficial = str(self.dados_server["id_guilda_ff"])
        idioma_atual = 7
        
        idiomas_disponiveis = [k for k in IDIOMAS_FF.keys() if k != idioma_atual]
        id_idioma_alvo = random.choice(idiomas_disponiveis)
        nome_idioma_alvo = IDIOMAS_FF[id_idioma_alvo]

        embed_tutorial = discord.Embed(
            title="⏳ Radar de Segurança Iniciado!",
            description=(
                f"Olá **{self.jogador_nome}**,\n\n"
                f"1️⃣ Vai ao teu perfil do Free Fire **agora mesmo**.\n"
                f"2️⃣ Muda o idioma da assinatura para: **`{nome_idioma_alvo}`**.\n\n"
                f"**🔎 STATUS DO RADAR AO VIVO:**\n"
                f"▶️ Verificação: `Iniciando...`\n"
                f"🗣️ Idioma que o bot está a ver: **{IDIOMAS_FF.get(idioma_atual, 'Desconhecido')}**\n\n"
                f"*(Tens 5 minutos. Podes fechar este aviso, recebes uma DM no final)*"
            ),
            color=discord.Color.orange()
        )
        embed_tutorial.set_image(url="https://i.imgur.com/aqLKQcU.png")
        embed_tutorial.set_footer(text=f"A preparar o rastreio no UID {self.uid}...")

        mensagem_tutorial = await interaction.followup.send(embed=embed_tutorial, ephemeral=True, wait=True)
        
        task = asyncio.create_task(self.processar_radar(
            interaction, interaction.user, interaction.guild, self.uid, id_idioma_alvo, nome_idioma_alvo, self.dados_server, embed_tutorial, self.jogador_nome, mensagem_tutorial, self.dados_pessoais.get("genero", "Prefiro não dizer"), self.dados_pessoais.get("idade", 0)
        ))
        self.bot.background_tasks.add(task)
        task.add_done_callback(self.bot.background_tasks.discard)

    async def processar_radar(self, interaction: discord.Interaction, user: discord.Member, guild: discord.Guild, uid: str, id_idioma_alvo: int, nome_idioma_alvo: str, dados_server: dict, embed_tutorial: discord.Embed, jogador_nome: str, mensagem_tutorial, genero: str, idade: int):
        url = f"{config.API_VERCEL_URL}/api/player?uid={uid}&fields=basic,profile"
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        
        log_sart(f"📡 Radar ativado para o UID {uid} ({user.name}). À espera do idioma alvo: {id_idioma_alvo}")
        
        session = interaction.client.session
        verificado = False
        tentativas = 0
        dados_radar = None
        
        while tentativas < 30: 
            await asyncio.sleep(10)
            tentativas += 1
            try:
                async with session.get(url, headers=headers) as resposta_radar:
                    if resposta_radar.status == 200:
                        dados_radar = await resposta_radar.json()
                        
                        novo_idioma_raw = dados_radar.get("socialInfo", {}).get("language")
                        novo_idioma = int(novo_idioma_raw) if novo_idioma_raw is not None else -1
                        
                        nome_idioma_detetado = IDIOMAS_FF.get(novo_idioma, f"Desconhecido (ID: {novo_idioma})")
                        log_sart(f"🔄 Scan {tentativas}/30 [UID: {uid}] -> Idioma: {novo_idioma}")
                        
                        embed_tutorial.description = (
                            f"Olá **{jogador_nome}**,\n\n"
                            f"1️⃣ Vai ao teu perfil do Free Fire **agora mesmo**.\n"
                            f"2️⃣ Muda o idioma da assinatura para: **`{nome_idioma_alvo}`**.\n\n"
                            f"**🔎 STATUS DO RADAR AO VIVO:**\n"
                            f"▶️ Verificação: `{tentativas}/30`\n"
                            f"🗣️ Idioma que o bot está a ver: **{nome_idioma_detetado}**\n\n"
                            f"*(Tens 5 minutos. Podes fechar este aviso, recebes uma DM no final)*"
                        )
                        
                        try:
                            await mensagem_tutorial.edit(embed=embed_tutorial)
                        except Exception as e:
                            log_sart(f"⚠️ Aviso: Não foi possível atualizar visualmente o Embed: {e}")
                        
                        if novo_idioma == id_idioma_alvo:
                            verificado = True
                            log_sart(f"✅ SUCESSO! Idioma alvo detetado no UID {uid}!")
                            break
            except Exception as e:
                log_sart(f"⚠️ Radar scan error: {e}")
        
        if verificado and dados_radar:
            log_sart(f"🛠️ A processar registo final para {user.name}...")
            basic_info = dados_radar.get("basicInfo", {})
            clan_info = dados_radar.get("clanInfo", {})
            profile_info = dados_radar.get("profileInfo", {})
            nome_guilda = clan_info.get("clanName", "Sem Guilda")
            nivel = basic_info.get("level", "0")
            likes = basic_info.get("liked", "0")
            head_pic_id = basic_info.get("headPic", "")
            avatar_id = profile_info.get("avatarId", "")
            br_pontos = int(basic_info.get("rankingPoints", 0))
            cs_pontos = int(basic_info.get("csRankingPoints", 0))
            patente_br = calcular_patente(br_pontos)
            ff_criacao = int(basic_info.get("createAt", 0))
            status_veterano = calcular_veterano(ff_criacao)
            
            cargo_id = int(dados_server["cargo_id"])
            canal_id = int(dados_server["canal_id"])
            cargo = guild.get_role(cargo_id)
            
            if cargo:
                try:
                    await user.add_roles(cargo)
                    log_sart(f"🎖️ Cargo entregue a {user.name}.")
                    
                    db_user_check = supabase.table("membros_verificados").select("log_message_id").eq("id_discord", str(user.id)).eq("id_servidor", str(guild.id)).execute()
                    old_log_id = None
                    if db_user_check.data and db_user_check.data[0].get("log_message_id"):
                        old_log_id = db_user_check.data[0]["log_message_id"]

                    thumbnail_id = avatar_id or head_pic_id
                    
                    embed_perfil = discord.Embed(
                        title="🚨 Registo S.art | Perfil Verificado",
                        description=f"O membro {user.mention} entrou no servidor e os seus dados foram guardados na base de dados com sucesso.",
                        color=discord.Color.from_rgb(0, 255, 128)
                    )
                    embed_perfil.add_field(name="👤 Nick FF", value=f"`{jogador_nome}`", inline=True)
                    embed_perfil.add_field(name="🆔 UID", value=f"`{uid}`", inline=True)
                    embed_perfil.add_field(name="🛡️ Guilda do Jogo", value=f"**{nome_guilda}**", inline=True)
                    embed_perfil.add_field(name="📊 Desempenho", value=f"Nível: **{nivel}**\nLikes: **{likes}**", inline=True)
                    embed_perfil.add_field(name="🌍 Patentes", value=f"BR: **{patente_br}** ({br_pontos} pts)\nCS: **{cs_pontos} pts**", inline=True)
                    embed_perfil.add_field(name="🌟 Status Jogo", value=f"**{status_veterano}**", inline=True)
                    embed_perfil.add_field(name="━━━━━━━━━━━━━━━━━━", value="**👤 Perfil Discord**", inline=False)
                    embed_perfil.add_field(name="🖼️ Avatar", value=f"[Link]({user.display_avatar.url})", inline=True)
                    embed_perfil.add_field(name="📅 Criação da Conta", value=f"<t:{int(user.created_at.timestamp())}:D>", inline=True)
                    embed_perfil.add_field(name="📅 Entrada no Servidor", value=f"<t:{int(user.joined_at.timestamp())}:D>", inline=True)
                    embed_perfil.add_field(name="🎭 Cargo Principal", value=user.top_role.mention, inline=True)
                    embed_perfil.add_field(name="🎂 Idade", value=f"**{idade}** anos", inline=True)
                    embed_perfil.add_field(name="🚻 Gênero", value=genero, inline=True)
                    if ff_criacao > 0:
                        embed_perfil.add_field(name="📅 Criação da conta do jogo", value=f"<t:{ff_criacao}:D> *(<t:{ff_criacao}:R>)*", inline=False)
                    
                    if thumbnail_id:
                        embed_perfil.set_thumbnail(url=f"https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/{thumbnail_id}.png")
                    embed_perfil.set_footer(text="S.art Engine • Proteção e Base de Dados")

                    msg_log_id = None
                    canal_log = guild.get_channel(canal_id)
                    
                    if canal_log:
                        if old_log_id:
                            try:
                                old_msg = await canal_log.fetch_message(int(old_log_id))
                                await old_msg.delete()
                            except Exception:
                                pass

                        nova_mensagem = await canal_log.send(embed=embed_perfil)
                        msg_log_id = str(nova_mensagem.id)

                    dados_membro = {
                        "id_discord": str(user.id),
                        "id_servidor": str(guild.id),
                        "id_ff": uid,
                        "nick_ff": jogador_nome,
                        "log_message_id": msg_log_id,
                        "genero": genero,
                        "idade": idade
                    }
                    supabase.table("membros_verificados").upsert(dados_membro).execute()

                    try:
                        await user.send(
                            f"✅ **Identidade Confirmada no servidor {guild.name}!**\n\nDetetei a mudança para `{nome_idioma_alvo}`. O teu cargo foi entregue com sucesso e os teus dados foram puxados para o nosso sistema! Bem-vindo à equipa **{jogador_nome}**.\n**Gênero:** {genero} | **Idade:** {idade} anos\n*(Já podes voltar a colocar o teu idioma normal no jogo)*",
                            embed=embed_perfil, 
                            view=ViewApagarDM()
                        )
                    except discord.Forbidden:
                        pass
                    
                    embed_tutorial.title = "✅ Identidade Confirmada!"
                    embed_tutorial.description = (
                        f"Parabéns **{jogador_nome}**!\n\n"
                        f"A tua conta foi verificada com sucesso e o cargo foi entregue.\n"
                        f"Verifica as tuas Mensagens Privadas (DM) para veres o teu cartão de perfil completo.\n\n"
                        f"*(Já podes voltar a colocar o teu idioma normal no jogo)*"
                    )
                    embed_tutorial.color = discord.Color.green()
                    embed_tutorial.set_image(url="https://i.pinimg.com/originals/98/e5/ca/98e5ca56164596bcbb13bc847f92e8b7.gif")
                    embed_tutorial.set_footer(text="Processo de Verificação Concluído.")
                    
                    try:
                        await mensagem_tutorial.edit(embed=embed_tutorial)
                    except Exception as e:
                        log_sart(f"⚠️ Aviso: Não foi possível atualizar o Embed de sucesso: {e}")

                except discord.Forbidden:
                    log_sart(f"❌ O Discord bloqueou a entrega do cargo a {user.name}.")
        else:
            log_sart(f"❌ TIMEOUT: O radar expirou para {user.name}.")
            
            embed_tutorial.title = "❌ Tempo Esgotado!"
            embed_tutorial.description = f"Não consegui detetar a mudança para `{nome_idioma_alvo}` em 5 minutos. Tenta `/entrar` novamente."
            embed_tutorial.color = discord.Color.red()
            embed_tutorial.set_image(url=None) 
            embed_tutorial.set_footer(text="Processo Cancelado.")
            try:
                await mensagem_tutorial.edit(embed=embed_tutorial)
            except:
                pass


class Usuarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="entrar", description="Verifica o teu ID para entrares no servidor")
    async def entrar(self, interaction: discord.Interaction):
        id_servidor = str(interaction.guild_id)
        db_res = supabase.table("servidores").select("*").eq("id_discord", id_servidor).execute()
        
        if not db_res.data:
            return await interaction.response.send_message("⚠️ **Servidor Não Validado!**", ephemeral=True)

        db_user = supabase.table("membros_verificados").select("id_ff").eq("id_discord", str(interaction.user.id)).eq("id_servidor", id_servidor).execute()
        if db_user.data:
            uid_existente = db_user.data[0]["id_ff"]
            return await interaction.response.send_message(f"✅ **Já estás verificado!** A tua conta FF (`{uid_existente}`) está registada. Usa `/perfil` para ver os teus dados.", ephemeral=True)
            
        dados_server = db_res.data[0]
        await interaction.response.send_message("👇 **Seleciona o teu gênero para continuar:**", view=ViewSelecionarGenero(dados_server, self.bot), ephemeral=True)

    @app_commands.command(name="desvincular", description="Remove o teu registo e cargo da guilda")
    async def desvincular(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        id_discord = str(interaction.user.id)
        id_servidor = str(interaction.guild_id)

        db_user = supabase.table("membros_verificados").select("*").eq("id_discord", id_discord).eq("id_servidor", id_servidor).execute()
        if not db_user.data:
            return await interaction.followup.send("⚠️ Não estás registado neste servidor. Não há nada para desvincular.")

        dados_user = db_user.data[0]
        old_log_id = dados_user.get("log_message_id")
        nick_ff = dados_user.get("nick_ff", "Desconhecido")
        uid_ff = dados_user.get("id_ff", "Desconhecido")

        db_server = supabase.table("servidores").select("*").eq("id_discord", id_servidor).execute()
        if db_server.data:
            dados_server = db_server.data[0]
            cargo_id = int(dados_server.get("cargo_id") or 0)
            canal_id = int(dados_server.get("canal_id") or 0)

            canal_log = interaction.guild.get_channel(canal_id)
            
            if canal_log and old_log_id:
                try:
                    old_msg = await canal_log.fetch_message(int(old_log_id))
                    await old_msg.delete()
                    log_sart(f"🗑️ Cartão de {nick_ff} removido do canal do Admin pelo /desvincular.")
                except Exception:
                    pass

            cargo = interaction.guild.get_role(cargo_id)
            if cargo and cargo in interaction.user.roles:
                try:
                    await interaction.user.remove_roles(cargo)
                except discord.Forbidden:
                    pass

            if canal_log:
                embed_saida = discord.Embed(
                    title="👋 Remoção de Registo",
                    description=f"O utilizador {interaction.user.mention} desvinculou a sua conta voluntariamente.",
                    color=discord.Color.from_rgb(255, 50, 50)
                )
                embed_saida.add_field(name="Nick FF", value=f"`{nick_ff}`", inline=True)
                embed_saida.add_field(name="UID", value=f"`{uid_ff}`", inline=True)
                embed_saida.set_footer(text="O cartão de membro antigo foi automaticamente apagado.")
                await canal_log.send(embed=embed_saida)

        supabase.table("membros_verificados").delete().eq("id_discord", id_discord).eq("id_servidor", id_servidor).execute()

        await interaction.followup.send(f"✅ **Registo Removido com Sucesso!**\nOs teus dados (`{nick_ff}`) foram apagados da nossa base de dados e o teu cargo foi retirado.")


    @app_commands.command(name="perfil", description="Consulta o perfil completo e atualizado de um jogador registado")
    async def perfil(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        
        await interaction.response.defer(ephemeral=True) 

        db_res = supabase.table("membros_verificados").select("id_ff").eq("id_discord", str(alvo.id)).eq("id_servidor", str(interaction.guild_id)).execute()

        if not db_res.data:
            return await interaction.followup.send(
                f"⛔ **Acesso Negado:** {'Tu não estás registado' if alvo == interaction.user else f'O membro {alvo.display_name} não está registado'} neste servidor. Apenas membros verificados possuem perfil."
            )

        uid = db_res.data[0]["id_ff"]
        url = f"{config.API_VERCEL_URL}/api/player?uid={uid}&fields=basic,profile"
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}

        session = interaction.client.session
        try:
            async with session.get(url, headers=headers) as resposta_api:
                if resposta_api.status != 200:
                    return await interaction.followup.send("⚠️ Erro de conexão com a API ao tentar buscar os dados atualizados do jogo.")
                dados = await resposta_api.json()
        except Exception as e:
            log_sart(f"🚨 Erro na API durante /perfil: {e}")
            return await interaction.followup.send(f"🚨 Erro de rede ao consultar o perfil.")

        basic_info = dados.get("basicInfo", {})
        clan_info = dados.get("clanInfo", {})
        profile_info = dados.get("profileInfo", {})

        nome_guilda = clan_info.get("clanName", "Sem Guilda")
        jogador_nome = basic_info.get("nickname", "Desconhecido")
        nivel = basic_info.get("level", "0")
        likes = basic_info.get("liked", "0")
        head_pic_id = basic_info.get("headPic", "")
        avatar_id = profile_info.get("avatarId", "")
        br_pontos = int(basic_info.get("rankingPoints", 0))
        cs_pontos = int(basic_info.get("csRankingPoints", 0))
        ff_criacao = int(basic_info.get("createAt", 0))

        patente_br = calcular_patente(br_pontos)
        status_veterano = calcular_veterano(ff_criacao)

        cs_stats_text = f"**{cs_pontos}** pts"
        try:
            cs_url = f"{config.API_VERCEL_URL}/api/csstats?uid={uid}"
            async with session.get(cs_url, headers=headers) as cs_resp:
                if cs_resp.status == 200:
                    cs_dados = await cs_resp.json()
                    cs_data = cs_dados.get("clashSquad", {})
                    cs_wins = cs_data.get("wins", 0)
                    cs_kills = cs_data.get("kills", 0)
                    cs_matches = cs_data.get("matches", 0)
                    cs_wr = cs_data.get("winRate", 0)
                    cs_stats_text = f"**{cs_pontos}** pts | **{cs_wins}** vitórias | **{cs_kills}** kills | **{cs_matches}** partidas"
        except Exception:
            pass

        thumbnail_id = avatar_id or head_pic_id

        embed_perfil = discord.Embed(
            title="🚨 Registo S.art | Perfil Verificado",
            description=f"Informações atualizadas do jogador {alvo.mention} sincronizadas com a base de dados.",
            color=discord.Color.from_rgb(0, 255, 128)
        )

        embed_perfil.add_field(name="👤 Nick FF", value=f"`{jogador_nome}`", inline=True)
        embed_perfil.add_field(name="🆔 UID", value=f"`{uid}`", inline=True)
        embed_perfil.add_field(name="🛡️ Guilda do Jogo", value=f"**{nome_guilda}**", inline=True)

        embed_perfil.add_field(name="📊 Desempenho", value=f"Nível: **{nivel}**\nLikes: **{likes}**", inline=True)
        embed_perfil.add_field(name="🌍 Patente BR", value=f"{patente_br} ({br_pontos} pts)", inline=True)
        embed_perfil.add_field(name="⚔️ Clash Squad", value=cs_stats_text, inline=True)
        embed_perfil.add_field(name="🌟 Status Jogo", value=f"**{status_veterano}**", inline=True)

        embed_perfil.add_field(name="━━━━━━━━━━━━━━━━━━", value="**👤 Perfil Discord**", inline=False)

        embed_perfil.add_field(name="🖼️ Avatar", value=f"[Link]({alvo.display_avatar.url})", inline=True)
        embed_perfil.add_field(name="📅 Criação da Conta", value=f"<t:{int(alvo.created_at.timestamp())}:D>", inline=True)
        embed_perfil.add_field(name="📅 Entrada no Servidor", value=f"<t:{int(alvo.joined_at.timestamp())}:D>", inline=True)
        embed_perfil.add_field(name="🎭 Cargo Principal", value=alvo.top_role.mention, inline=True)

        if thumbnail_id:
            embed_perfil.set_thumbnail(url=f"https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/{thumbnail_id}.png")

        if ff_criacao > 0:
            embed_perfil.add_field(
                name="📅 Criação da conta do jogo",
                value=f"<t:{ff_criacao}:D> *(<t:{ff_criacao}:R>)*",
                inline=False
            )

        embed_perfil.set_footer(text="S.art Engine • Proteção e Base de Dados")
        await interaction.followup.send(embed=embed_perfil)


async def setup(bot):
    bot.add_view(ViewApagarDM()) 
    await bot.add_cog(Usuarios(bot))
