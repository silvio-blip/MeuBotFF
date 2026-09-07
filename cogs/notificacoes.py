# cogs/notificacoes.py
import discord
from discord import app_commands
from discord.ext import commands, tasks
import config
from datetime import datetime, timezone
from database import supabase

class SelectCanalNotificacoes(discord.ui.View):
    def __init__(self, tipo: str):
        super().__init__(timeout=300)
        self.tipo = tipo

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Seleciona o canal...")
    async def select_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal_selecionado = select.values[0]
        campo = f"canal_{self.tipo}"
        supabase.table("notificacoes_config").upsert({
            "guilda_id": str(interaction.guild_id),
            campo: str(canal_selecionado.id)
        }).execute()
        await interaction.response.send_message(f"✅ Canal de {self.tipo} alterado para {canal_selecionado.mention}.", ephemeral=True)

class NotificacoesConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Canal Atualizações", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="noti_config_atualizacoes")
    async def btn_atualizacoes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 **Seleciona o canal de atualizações:**", view=SelectCanalNotificacoes("atualizacoes"), ephemeral=True)

    @discord.ui.button(label="Canal Membros", style=discord.ButtonStyle.primary, emoji="👤", custom_id="noti_config_membros")
    async def btn_membros(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 **Seleciona o canal de membros:**", view=SelectCanalNotificacoes("membros"), ephemeral=True)

    @discord.ui.button(label="Canal Temporada", style=discord.ButtonStyle.primary, emoji="📅", custom_id="noti_config_temporada")
    async def btn_temporada(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 **Seleciona o canal de temporada:**", view=SelectCanalNotificacoes("temporada"), ephemeral=True)

    @discord.ui.button(label="Ativar/Desativar", style=discord.ButtonStyle.success, emoji="✅", custom_id="noti_config_toggle")
    async def btn_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_config = supabase.table("notificacoes_config").select("habilitado").eq("guilda_id", str(interaction.guild_id)).execute()
        
        if db_config.data:
            atual = db_config.data[0].get("habilitado", True)
            novo = not atual
            supabase.table("notificacoes_config").update({"habilitado": novo}).eq("guilda_id", str(interaction.guild_id)).execute()
            status = "ativado" if novo else "desativado"
            await interaction.response.send_message(f"✅ Notificações **{status}**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Configura o sistema primeiro.", ephemeral=True)

class Notificacoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verificar_membros_task.start()

    def cog_unload(self):
        self.verificar_membros_task.cancel()

    @app_commands.command(name="verificar_membros", description="Verifica se os membros verificados ainda estão na guilda FF")
    async def verificar_membros(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ **Acesso Negado:** Apenas admins podem verificar membros.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        id_servidor = str(interaction.guild_id)
        
        db_server = supabase.table("servidores").select("id_guilda_ff").eq("id_discord", id_servidor).execute()
        if not db_server.data:
            return await interaction.followup.send("❌ Servidor não configurado.")
        
        guilda_ff_id = str(db_server.data[0]["id_guilda_ff"])
        
        db_membros = supabase.table("membros_verificados").select("*").eq("id_servidor", id_servidor).execute()
        if not db_membros.data:
            return await interaction.followup.send("❌ Nenhum membro verificado encontrado.")
        
        session = self.bot.session
        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
        
        sairam = []
        for membro in db_membros.data:
            uid = membro.get("id_ff")
            if not uid:
                continue
            
            try:
                url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
                async with session.get(url, headers=headers) as resposta:
                    if resposta.status == 200:
                        dados = await resposta.json()
                        player_data = dados.get("player", dados)
                        clan_id = str(player_data.get("clanInfo", {}).get("clanId", ""))
                        
                        if clan_id != guilda_ff_id:
                            sairam.append({
                                "discord_id": membro["id_discord"],
                                "nick_ff": membro.get("nick_ff", "Desconhecido"),
                                "uid": uid
                            })
            except Exception as e:
                print(f"🚨 Erro ao verificar UID {uid}: {e}")
        
        if not sairam:
            return await interaction.followup.send("✅ Todos os membros verificados ainda estão na guilda!")
        
        db_noti = supabase.table("notificacoes_config").select("*").eq("guilda_id", id_servidor).execute()
        canal_id = None
        if db_noti.data:
            canal_id = db_noti.data[0].get("canal_membros")
        
        embed = discord.Embed(
            title="⚠️ Membros que saíram da Guilda FF",
            description=f"**{len(sairam)}** membro(s) não estão mais na guilda oficial:",
            color=discord.Color.orange()
        )
        
        for m in sairam[:10]:
            membro_discord = interaction.guild.get_member(int(m["discord_id"]))
            nome = membro_discord.mention if membro_discord else f"ID: {m['discord_id']}"
            embed.add_field(
                name=f"👤 {nome}",
                value=f"FF: `{m['nick_ff']}` | UID: `{m['uid']}`",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
        if canal_id and str(canal_id).isdigit():
            canal = interaction.guild.get_channel(int(canal_id))
            if canal:
                await canal.send(embed=embed)

    @tasks.loop(hours=6)
    async def verificar_membros_task(self):
        print("🔄 Verificação automática de membros iniciada...")
        
        try:
            db_servers = supabase.table("notificacoes_config").select("guilda_id").eq("habilitado", True).execute()
        except Exception as e:
            print(f"⚠️ Tabela notificacoes_config não existe ou sem permissão: {e}")
            return
        
        if not db_servers.data:
            return
        
        for server in db_servers.data:
            guild = self.bot.get_guild(int(server["guilda_id"]))
            if not guild:
                continue
            
            try:
                db_server = supabase.table("servidores").select("id_guilda_ff").eq("id_discord", server["guilda_id"]).execute()
                if not db_server.data:
                    continue
                
                guilda_ff_id = str(db_server.data[0]["id_guilda_ff"])
                db_membros = supabase.table("membros_verificados").select("*").eq("id_servidor", server["guilda_id"]).execute()
                
                if not db_membros.data:
                    continue
                
                session = self.bot.session
                headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
                
                sairam = []
                for membro in db_membros.data:
                    uid = membro.get("id_ff")
                    if not uid:
                        continue
                    
                    try:
                        url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
                        async with session.get(url, headers=headers) as resposta:
                            if resposta.status == 200:
                                dados = await resposta.json()
                                player_data = dados.get("player", dados)
                                clan_id = str(player_data.get("clanInfo", {}).get("clanId", ""))
                                
                                if clan_id != guilda_ff_id:
                                    sairam.append({
                                        "discord_id": membro["id_discord"],
                                        "nick_ff": membro.get("nick_ff", "Desconhecido"),
                                        "uid": uid
                                    })
                    except Exception:
                        pass
                
                if sairam:
                    try:
                        db_noti = supabase.table("notificacoes_config").select("canal_membros").eq("guilda_id", server["guilda_id"]).execute()
                        canal_id = None
                        if db_noti.data:
                            canal_id = db_noti.data[0].get("canal_membros")
                    except Exception:
                        canal_id = None
                    
                    if canal_id and str(canal_id).isdigit():
                        canal = guild.get_channel(int(canal_id))
                        if canal:
                            embed = discord.Embed(
                                title="⚠️ Membros que saíram da Guilda FF",
                                description=f"**{len(sairam)}** membro(s) não estão mais na guilda oficial:",
                                color=discord.Color.orange()
                            )
                            for m in sairam[:10]:
                                membro_discord = guild.get_member(int(m["discord_id"]))
                                nome = membro_discord.mention if membro_discord else f"ID: {m['discord_id']}"
                                embed.add_field(
                                    name=f"👤 {nome}",
                                    value=f"FF: `{m['nick_ff']}` | UID: `{m['uid']}`",
                                    inline=False
                                )
                            await canal.send(embed=embed)
                
                print(f"✅ Verificação concluída para {guild.name}: {len(sairam)} membros saíram")
            except Exception as e:
                print(f"🚨 Erro na verificação automática para {guild.name}: {e}")

    @verificar_membros_task.before_loop
    async def before_verificar_membros(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Notificacoes(bot))
