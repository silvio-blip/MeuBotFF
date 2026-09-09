# cogs/convites.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from database import supabase

class Convites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._invites_cache = {}

    async def cog_load(self):
        # Cache invites de todos os servidores
        await self._cache_invites()

    async def _cache_invites(self):
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self._invites_cache[guild.id] = {inv.code: inv for inv in invites}
            except:
                self._invites_cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        
        guild = member.guild
        id_servidor = str(guild.id)
        
        # Verificar se convites estão habilitados
        try:
            db_config = supabase.table("convites_config").select("*").eq("guilda_id", id_servidor).execute()
            if not db_config.data or not db_config.data[0].get("habilitado"):
                return
        except:
            return
        
        # Descobrir quem convidou
        try:
            novos_invites = await guild.invites()
            antigos_invites = self._invites_cache.get(guild.id, {})
            
            convidador = None
            for invite in novos_invites:
                if invite.code in antigos_invites:
                    if invite.uses > antigos_invites[invite.code].uses:
                        convidador = invite.inviter
                        break
                else:
                    convidador = invite.inviter
                    break
            
            # Atualizar cache
            self._invites_cache[guild.id] = {inv.code: inv for inv in novos_invites}
            
            if convidador and convidador.id != member.id:
                # Guardar convite no Supabase
                supabase.table("convites").insert({
                    "convidador_id": str(convidador.id),
                    "convidado_id": str(member.id),
                    "guilda_id": id_servidor
                }).execute()
                
                # Economia: recompensa por convite válido
                try:
                    cfg_economia = supabase.table("economia_config").select("*").eq("guilda_id", id_servidor).execute()
                    if cfg_economia.data and cfg_economia.data[0].get("habilitado"):
                        moedas = cfg_economia.data[0].get("moedas_convite", 15)
                        db_user = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(convidador.id)).eq("id_servidor", id_servidor).execute()
                        saldo_atual = db_user.data[0]["moedas"] if db_user.data and db_user.data[0].get("moedas") is not None else 0
                        supabase.table("membros_verificados").update({"moedas": saldo_atual + int(moedas)}).eq("id_discord", str(convidador.id)).eq("id_servidor", id_servidor).execute()
                except Exception:
                    pass
                
                # Enviar notificação se canal configurado
                canal_id = db_config.data[0].get("canal_notificacoes") if db_config.data else None
                if canal_id and str(canal_id).isdigit():
                    canal = guild.get_channel(int(canal_id))
                    if canal:
                        embed = discord.Embed(
                            title="📩 Novo Convite!",
                            description=f"**{convidador.display_name}** convidou **{member.display_name}**!",
                            color=discord.Color.from_rgb(0, 200, 255)
                        )
                        embed.add_field(name="Total de convites", value=f"**{self._contar_convites(str(convidador.id), id_servidor)}**", inline=True)
                        await canal.send(embed=embed)
        except Exception as e:
            print(f"🚨 Erro ao processar convite: {e}")

    def _contar_convites(self, user_id, guild_id):
        try:
            db = supabase.table("convites").select("*").eq("convidador_id", user_id).eq("guilda_id", guild_id).execute()
            return len(db.data) if db.data else 0
        except:
            return 0

    @app_commands.command(name="convites", description="Mostra estatísticas de convites do servidor")
    async def convites(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        id_servidor = str(interaction.guild_id)
        
        db_convites = supabase.table("convites").select("*").eq("convidador_id", str(alvo.id)).eq("guilda_id", id_servidor).execute()
        
        total = len(db_convites.data) if db_convites.data else 0
        
        embed = discord.Embed(
            title=f"📩 Convites de {alvo.display_name}",
            color=discord.Color.from_rgb(0, 200, 255)
        )
        
        embed.add_field(name="Total de Convites", value=f"**{total}**", inline=True)
        
        if db_convites.data:
            ultimos = db_convites.data[-5:]
            lista = ""
            for c in reversed(ultimos):
                convidado = interaction.guild.get_member(int(c["convidado_id"]))
                nome = convidado.display_name if convidado else "Saiu"
                data = c.get("data", "")
                if data:
                    try:
                        dt = datetime.fromisoformat(data.replace("Z", "+00:00"))
                        lista += f"• {nome} — <t:{int(dt.timestamp())}:R>\n"
                    except:
                        lista += f"• {nome}\n"
                else:
                    lista += f"• {nome}\n"
            embed.add_field(name="Últimos Convites", value=lista or "Nenhum", inline=False)
        
        embed.set_footer(text="S.art Engine • Sistema de Convites")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Convites(bot))
