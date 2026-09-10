# cogs/notificacoes.py
import discord
from discord import app_commands
from discord.ext import commands, tasks
import config
from datetime import datetime, timezone, timedelta
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

    async def on_member_remove(self, member: discord.Member):
        try:
            if member.bot:
                return
            guild = member.guild
            guild_id = str(guild.id)

            # --- Notificação de saída no canal_saida ---
            db_noti = supabase.table("notificacoes_config").select("canal_saida", "habilitado").eq("guilda_id", guild_id).execute()
            if not db_noti.data or not db_noti.data[0].get("habilitado", True):
                await self._auto_desvincular(guild, guild_id, member)
                return

            canal_saida_id = db_noti.data[0].get("canal_saida")

            db_user = supabase.table("membros_verificados").select("nick_ff, id_ff").eq("id_discord", str(member.id)).eq("id_servidor", guild_id).execute()
            verificado = bool(db_user.data and db_user.data[0])

            join_date = member.joined_at
            if join_date:
                tempo_no_servidor = datetime.now(timezone.utc) - join_date
                dias = tempo_no_servidor.days
                tempo_str = f"{dias} dias" if dias > 0 else f"{max(1, int(tempo_no_servidor.total_seconds() / 3600))} horas"
            else:
                tempo_str = "desconhecido"

            title = "👤 Membro Saiu do Servidor"
            if verificado:
                nick_ff = db_user.data[0].get("nick_ff", "N/A")
                uid = db_user.data[0].get("id_ff", "N/A")
                description = (
                    f"**{member.display_name}** (`{member.id}`) saiu do servidor.\n\n"
                    f"**Informações FF:**\n"
                    f"Nick: `{nick_ff}`\n"
                    f"UID: `{uid}`\n"
                    f"Tempo no servidor: `{tempo_str}`\n"
                    f"🔄 **Conta desvinculada automaticamente.**"
                )
            else:
                description = (
                    f"**{member.display_name}** (`{member.id}`) saiu do servidor.\n\n"
                    f"Não estava verificado.\n"
                    f"Tempo no servidor: `{tempo_str}`"
                )

            if canal_saida_id and str(canal_saida_id).isdigit():
                canal_saida = guild.get_channel(int(canal_saida_id))
                if canal_saida:
                    embed = discord.Embed(title=title, description=description, color=discord.Color.orange())
                    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
                    embed.set_footer(text="👋 Até logo!")
                    await canal_saida.send(embed=embed)
                    print(f"[NOTIFICACOES] Membro saiu: {member.display_name} em {guild.name} -> canal_saida")

            # --- Auto-desvinculo: remove dados do bot quando sai do servidor ---
            await self._auto_desvincular(guild, guild_id, member)
        except Exception as e:
            print(f"[NOTIFICACOES] Erro no on_member_remove: {e}")

    async def _auto_desvincular(self, guild, guild_id, member):
        try:
            db_user = supabase.table("membros_verificados").select("nick_ff, id_ff, log_message_id").eq("id_discord", str(member.id)).eq("id_servidor", guild_id).execute()
            if not db_user.data or not db_user.data[0]:
                return

            dados_user = db_user.data[0]
            nick_ff = dados_user.get("nick_ff", "Desconhecido")
            uid_ff = dados_user.get("id_ff", "Desconhecido")
            old_log_id = dados_user.get("log_message_id")

            db_server = supabase.table("servidores").select("canal_id").eq("id_discord", guild_id).execute()
            canal_log = None
            if db_server.data and db_server.data[0].get("canal_id"):
                canal_log = guild.get_channel(int(db_server.data[0]["canal_id"]))

            if canal_log and old_log_id:
                try:
                    old_msg = await canal_log.fetch_message(int(old_log_id))
                    await old_msg.delete()
                    print(f"[NOTIFICACOES] Auto-desvínculo: cartão de {nick_ff} removido do canal de logs.")
                except Exception as e:
                    print(f"[NOTIFICACOES] Auto-desvínculo: erro a deletar cartão ({e})")

            db_noti = supabase.table("notificacoes_config").select("canal_desvinculo").eq("guilda_id", guild_id).execute()
            canal_desvinculo = None
            if db_noti.data and db_noti.data[0].get("canal_desvinculo"):
                canal_desvinculo = guild.get_channel(int(db_noti.data[0]["canal_desvinculo"]))

            if canal_desvinculo:
                embed_saida = discord.Embed(
                    title="👋 Remoção Automática de Registo",
                    description=f"O utilizador **{member.display_name}** (`{member.id}`) saiu do servidor.\n"
                                f"Os dados de verificação foram removidos automaticamente.",
                    color=discord.Color.red()
                )
                embed_saida.add_field(name="Nick FF", value=f"`{nick_ff}`", inline=True)
                embed_saida.add_field(name="UID", value=f"`{uid_ff}`", inline=True)
                embed_saida.set_footer(text="Conta desvinculada automaticamente ao sair do servidor.")
                try:
                    await canal_desvinculo.send(embed=embed_saida)
                except (discord.Forbidden, discord.HTTPException):
                    pass

            supabase.table("membros_verificados").delete().eq("id_discord", str(member.id)).eq("id_servidor", guild_id).execute()
            print(f"[NOTIFICACOES] Auto-desvínculo concluído: {nick_ff} ({member.id}) em {guild.name}")
        except Exception as e:
            print(f"[NOTIFICACOES] Erro no auto_desvincular: {e}")

async def setup(bot):
    await bot.add_cog(Notificacoes(bot))
