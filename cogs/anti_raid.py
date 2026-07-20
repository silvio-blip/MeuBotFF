# cogs/anti_raid.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from database import supabase

def log_sart(msg):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] ⚙️ [S.art] {msg}")

class ModalAntiRaid(discord.ui.Modal, title='Configurar Anti-Raid'):
    limite_joins = discord.ui.TextInput(label='Máximo de joins por minuto', placeholder='Ex: 5', required=True, default="5")
    duracao_lock = discord.ui.TextInput(label='Duração do lock (minutos)', placeholder='Ex: 5', required=True, default="5")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limite = int(self.limite_joins.value)
            duracao = int(self.duracao_lock.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valores inválidos! Insere números.", ephemeral=True)
        
        if limite < 1 or limite > 50:
            return await interaction.response.send_message("❌ O limite deve ser entre 1 e 50.", ephemeral=True)
        
        if duracao < 1 or duracao > 60:
            return await interaction.response.send_message("❌ A duração deve ser entre 1 e 60 minutos.", ephemeral=True)
        
        supabase.table("anti_raid_config").upsert({
            "guilda_id": str(interaction.guild_id),
            "limite_joins": limite,
            "duracao_lock": duracao,
            "habilitado": True
        }).execute()
        
        await interaction.response.send_message(
            f"✅ **Anti-Raid configurado!**\n\n"
            f"**Limite:** {limite} joins/minuto\n"
            f"**Lock:** {duracao} minutos",
            ephemeral=True
        )

class SelectCanalAlertasRaid(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Seleciona o canal de alertas de raid...")
    async def select_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal_selecionado = select.values[0]
        supabase.table("anti_raid_config").upsert({
            "guilda_id": str(interaction.guild_id),
            "canal_alertas": str(canal_selecionado.id)
        }).execute()
        await interaction.response.send_message(f"✅ Canal de alertas de raid alterado para {canal_selecionado.mention}.", ephemeral=True)

class AntiRaidConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Configurar Limites", style=discord.ButtonStyle.primary, emoji="🔢", custom_id="raid_config_limites")
    async def btn_limites(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalAntiRaid())

    @discord.ui.button(label="Canal de Alertas", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="raid_config_canal")
    async def btn_canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 **Seleciona o canal de alertas:**", view=SelectCanalAlertasRaid(), ephemeral=True)

    @discord.ui.button(label="Ativar/Desativar", style=discord.ButtonStyle.success, emoji="✅", custom_id="raid_config_toggle")
    async def btn_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_config = supabase.table("anti_raid_config").select("habilitado").eq("guilda_id", str(interaction.guild_id)).execute()
        
        if db_config.data:
            atual = db_config.data[0].get("habilitado", True)
            novo = not atual
            supabase.table("anti_raid_config").update({"habilitado": novo}).eq("guilda_id", str(interaction.guild_id)).execute()
            status = "ativado" if novo else "desativado"
            await interaction.response.send_message(f"✅ Sistema anti-raid **{status}**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Configura o sistema primeiro.", ephemeral=True)

class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_tracker = defaultdict(list)
        self.locked_servers = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        
        id_servidor = str(member.guild.id)
        agora = datetime.now(timezone.utc)
        
        # Verificar se o lock expirou
        if id_servidor in self.locked_servers:
            if agora > self.locked_servers[id_servidor]:
                del self.locked_servers[id_servidor]
                log_sart(f"🛡️ Lock expirado em {member.guild.name}")
            else:
                try:
                    await member.kick(reason="Servidor bloqueado por anti-raid")
                    log_sart(f"🛡️ Raid: {member.name} expulso (servidor bloqueado)")
                except discord.Forbidden:
                    pass
                return
        
        db_config = supabase.table("anti_raid_config").select("*").eq("guilda_id", id_servidor).execute()
        
        if not db_config.data or not db_config.data[0].get("habilitado"):
            return
        
        cfg = db_config.data[0]
        limite = cfg.get("limite_joins", 5)
        duracao = cfg.get("duracao_lock", 5)
        canal_alertas_id = cfg.get("canal_alertas")
        
        agora = datetime.now(timezone.utc)
        self.join_tracker[id_servidor].append(agora)
        
        cutoff = agora - timedelta(minutes=1)
        self.join_tracker[id_servidor] = [t for t in self.join_tracker[id_servidor] if t > cutoff]
        
        if len(self.join_tracker[id_servidor]) >= limite:
            self.locked_servers[id_servidor] = agora + timedelta(minutes=duracao)
            
            log_sart(f"🚨 RAID DETECTADO em {member.guild.name}! Servidor bloqueado por {duracao} minutos.")
            
            if canal_alertas_id and str(canal_alertas_id).isdigit():
                canal = member.guild.get_channel(int(canal_alertas_id))
                if canal:
                    embed = discord.Embed(
                        title="🚨 RAID DETECTADO!",
                        description=(
                            f"**Ação tomada:** Servidor bloqueado temporariamente.\n"
                            f"**Duração:** {duracao} minutos\n"
                            f"**Joins detectados:** {len(self.join_tracker[id_servidor])} no último minuto\n\n"
                            f"Todos os novos membros serão expulsos automaticamente."
                        ),
                        color=discord.Color.red()
                    )
                    embed.set_footer(text=f"Bloqueado até: <t:{int(self.locked_servers[id_servidor].timestamp())}:R>")
                    await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
