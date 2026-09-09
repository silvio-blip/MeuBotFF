import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import config
from database import supabase

sys.stdout.reconfigure(encoding='utf-8')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session: aiohttp.ClientSession = None
        self.background_tasks = set()
        self.verificacao_automatica_task = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await self.load_extension('cogs.admin')
        await self.load_extension('cogs.gestao')
        await self.load_extension('cogs.usuarios')
        await self.load_extension('cogs.warns')
        await self.load_extension('cogs.boas_vindas')
        await self.load_extension('cogs.anti_raid')
        await self.load_extension('cogs.ranking')
        await self.load_extension('cogs.torneios')
        await self.load_extension('cogs.notificacoes')
        await self.load_extension('cogs.ajuda')
        await self.load_extension('cogs.pesquisa')
        await self.load_extension('cogs.convites')
        await self.load_extension('cogs.economia')
        self.tree.interaction_check = self.global_check
        if os.getenv("SYNC_COMMANDS", "true").lower() == "true":
            await self.tree.sync()
            print("✅ Comandos de Barra (/) sincronizados e prontos!")
        else:
            print("⏭️ Sincronização de comandos ignorada.")

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

    async def global_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.command:
            return True
        if interaction.command.name in ["configurar", "entrar", "pesquisa"]:
            return True

        try:
            db_res = supabase.table("servidores").select("id_discord", "cargo_gestao_id").eq("id_discord", str(interaction.guild_id)).execute()
            if not db_res.data:
                await interaction.response.send_message("⛔ **Servidor não registado!** O dono deve usar o `/configurar` primeiro.", ephemeral=True)
                return False
        except Exception as e:
            print(f"🚨 Erro no global_check (servidores): {e}")
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id
        is_admin = interaction.user.guild_permissions.administrator
        is_gestao = False
        if not is_owner and not is_admin:
            servidor = db_res.data[0]
            cargo_gestao_id = servidor.get("cargo_gestao_id")
            if cargo_gestao_id:
                cargo_gestao = interaction.guild.get_role(int(cargo_gestao_id))
                if cargo_gestao and cargo_gestao in interaction.user.roles:
                    is_gestao = True

        if is_owner or is_admin or is_gestao:
            return True

        try:
            db_user = supabase.table("membros_verificados").select("id_discord").eq("id_discord", str(interaction.user.id)).eq("id_servidor", str(interaction.guild_id)).execute()
            if not db_user.data:
                await interaction.response.send_message("⛔ **Acesso Negado!** Precisas de estar verificado (`/entrar`) para usar comandos.", ephemeral=True)
                return False
        except Exception as e:
            print(f"🚨 Erro no global_check (membros): {e}")
            return False

        return True

    async def on_application_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            return
        cmd_name = interaction.command.name if interaction.command else "desconhecido"
        print(f"🚨 Erro no comando {cmd_name}: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro ao processar o comando.", ephemeral=True)
        except discord.HTTPException:
            pass


bot = MeuBot()

@bot.event
async def on_ready():
    print(f'🔥 Bot Online e a correr limpo: {bot.user}')

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    cog_bv = bot.get_cog("BoasVindas")
    if cog_bv:
        try:
            await cog_bv.enviar_boas_vindas(member)
        except Exception as e:
            print(f"🚨 Erro boas-vindas: {e}")
    cog_raid = bot.get_cog("AntiRaid")
    if cog_raid:
        try:
            await cog_raid.on_member_join(member)
        except Exception as e:
            print(f"🚨 Erro anti-raid: {e}")

@bot.event
async def on_member_remove(member: discord.Member):
    if member.bot:
        return
    cog_noti = bot.get_cog("Notificacoes")
    if cog_noti:
        try:
            await cog_noti.on_member_remove(member)
        except Exception as e:
            print(f"🚨 Erro notificações: {e}")

bot.run(config.DISCORD_TOKEN)