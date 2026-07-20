# cogs/warns.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from database import supabase

class ModalWarn(discord.ui.Modal, title='Advertir Membro'):
    motivo = discord.ui.TextInput(label='Motivo da Advertência', placeholder='Ex: Comportamento inadequado...', required=True, style=discord.TextStyle.paragraph)

    def __init__(self, membro_id: str):
        super().__init__()
        self.membro_id = membro_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        id_servidor = str(interaction.guild_id)
        
        db_config = supabase.table("warns_config").select("*").eq("guilda_id", id_servidor).execute()
        
        max_warns = 3
        dias_expiracao = 30
        if db_config.data:
            max_warns = db_config.data[0].get("max_warns", 3)
            dias_expiracao = db_config.data[0].get("dias_expiracao", 30)
        
        db_warns = supabase.table("warns").select("*").eq("usuario_id", self.membro_id).eq("guilda_id", id_servidor).eq("ativo", True).execute()
        warns_ativos = len(db_warns.data) if db_warns.data else 0
        
        expira_em = datetime.now(timezone.utc) + timedelta(days=dias_expiracao)
        
        motivo_texto = self.motivo.value

        supabase.table("warns").insert({
            "usuario_id": self.membro_id,
            "guilda_id": id_servidor,
            "motivo": motivo_texto,
            "dado_por": str(interaction.user.id),
            "expira_em": expira_em.isoformat(),
            "ativo": True
        }).execute()
        
        warns_ativos += 1
        
        membro = interaction.guild.get_member(int(self.membro_id))
        nome_membro = membro.display_name if membro else "Desconhecido"
        
        embed = discord.Embed(
            title="⚠️ Advertência Registrada",
            description=f"O membro **{nome_membro}** recebeu uma advertência.",
            color=discord.Color.orange()
        )
        embed.add_field(name="📝 Motivo", value=motivo_texto, inline=False)
        embed.add_field(name="👤 Dado por", value=interaction.user.mention, inline=True)
        embed.add_field(name="📊 Warnings", value=f"{warns_ativos}/{max_warns}", inline=True)
        
        if warns_ativos >= max_warns:
            embed.add_field(name="🚨 Status", value="**LIMITE ATINGIDO!** Ban automático pendente.", inline=False)
            embed.color = discord.Color.red()
            if membro:
                try:
                    await membro.ban(reason=f"Auto-ban: {warns_ativos} warns atingidos")
                    embed.add_field(name="🔨 Ban", value=f"{membro.mention} foi banido automaticamente.", inline=False)
                except discord.Forbidden:
                    embed.add_field(name="🔨 Ban", value="❌ Sem permissão para banir.", inline=False)
        else:
            restam = max_warns - warns_ativos
            embed.add_field(name="📢 Aviso", value=f"Faltam **{restam}** advertência(s) para banimento automático.", inline=False)
        
        embed.set_footer(text=f"Expira em: <t:{int(expira_em.timestamp())}:R>")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        try:
            dm_embed = discord.Embed(
                title="⚠️ Advertência no servidor " + interaction.guild.name,
                description=f"Recebeste uma advertência.\n\n**Motivo:** {motivo_texto}\n**Warnings ativos:** {warns_ativos}/{max_warns}",
                color=discord.Color.orange()
            )
            if membro:
                await membro.send(embed=dm_embed)
        except discord.Forbidden:
            pass

class SelectCanalNotificacoesWarns(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Seleciona o canal de notificações de warns...")
    async def select_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal_selecionado = select.values[0]
        supabase.table("warns_config").upsert({
            "guilda_id": str(interaction.guild_id),
            "canal_notificacoes": str(canal_selecionado.id)
        }).execute()
        await interaction.response.send_message(f"✅ Canal de notificações de warns alterado para {canal_selecionado.mention}.", ephemeral=True)

class WarnsConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Alterar Limite de Warns", style=discord.ButtonStyle.secondary, emoji="🔢", custom_id="warns_config_limite")
    async def btn_limite(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalConfigWarns())

    @discord.ui.button(label="Canal de Notificações", style=discord.ButtonStyle.primary, emoji="📢", custom_id="warns_config_canal")
    async def btn_canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 **Seleciona o canal para notificações de warns:**", view=SelectCanalNotificacoesWarns(), ephemeral=True)

class ModalConfigWarns(discord.ui.Modal, title='Configurar Limite de Warns'):
    max_warns = discord.ui.TextInput(label='Máximo de warns antes do ban', placeholder='Ex: 3', required=True, default="3")
    dias = discord.ui.TextInput(label='Dias para expirar o warn', placeholder='Ex: 30', required=True, default="30")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            max_w = int(self.max_warns.value)
            dias = int(self.dias.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valores inválidos! Insere números.", ephemeral=True)
        
        if max_w < 1 or max_w > 10:
            return await interaction.response.send_message("❌ O limite deve ser entre 1 e 10.", ephemeral=True)
        
        supabase.table("warns_config").upsert({
            "guilda_id": str(interaction.guild_id),
            "max_warns": max_w,
            "dias_expiracao": dias
        }).execute()
        
        await interaction.response.send_message(f"✅ Configuração atualizada: **{max_w}** warns = ban, expira em **{dias}** dias.", ephemeral=True)

class Warns(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def verificar_permissao_gestao(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        id_servidor = str(interaction.guild_id)
        db_res = supabase.table("servidores").select("cargo_gestao_id").eq("id_discord", id_servidor).execute()
        if db_res.data and db_res.data[0].get("cargo_gestao_id"):
            try:
                cargo_id = int(db_res.data[0]["cargo_gestao_id"])
                cargo_gestao = interaction.guild.get_role(cargo_id)
                if cargo_gestao and cargo_gestao in interaction.user.roles:
                    return True
            except (ValueError, TypeError):
                pass
        return False

    @app_commands.command(name="dar_warn", description="Adverte um membro do servidor")
    async def dar_warn(self, interaction: discord.Interaction, membro: discord.Member):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)
        
        if membro.id == interaction.user.id:
            return await interaction.response.send_message("❌ Não podes advertir a ti mesmo.", ephemeral=True)
        
        if membro.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Não podes advertir um administrador.", ephemeral=True)
        
        await interaction.response.send_modal(ModalWarn(str(membro.id)))

    @app_commands.command(name="remover_warn", description="Remove uma advertência de um membro")
    async def remover_warn(self, interaction: discord.Interaction, membro: discord.Member, warn_id: int):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)
        
        db_res = supabase.table("warns").select("*").eq("id", warn_id).eq("usuario_id", str(membro.id)).eq("guilda_id", str(interaction.guild_id)).execute()
        
        if not db_res.data:
            return await interaction.response.send_message("❌ Advertência não encontrada.", ephemeral=True)
        
        supabase.table("warns").update({"ativo": False}).eq("id", warn_id).execute()
        
        await interaction.response.send_message(f"✅ Advertência #{warn_id} removida de {membro.mention}.", ephemeral=True)

    @app_commands.command(name="lista_warns", description="Lista as advertências de um membro")
    async def lista_warns(self, interaction: discord.Interaction, membro: discord.Member):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)
        
        db_res = supabase.table("warns").select("*").eq("usuario_id", str(membro.id)).eq("guilda_id", str(interaction.guild_id)).eq("ativo", True).order("data", desc=True).execute()
        
        if not db_res.data:
            return await interaction.response.send_message(f"✅ {membro.mention} não tem advertências ativas.", ephemeral=True)
        
        embed = discord.Embed(
            title=f"⚠️ Advertências de {membro.display_name}",
            description=f"Total: **{len(db_res.data)}** advertência(s) ativa(s)",
            color=discord.Color.orange()
        )
        
        for warn in db_res.data[:10]:
            data_warn = warn.get("data", "Data desconhecida")
            motivo = warn.get("motivo", "Sem motivo")
            dado_por = warn.get("dado_por", "Desconhecido")
            embed.add_field(
                name=f"#{warn['id']} - <t:{int(datetime.fromisoformat(data_warn.replace('Z', '+00:00')).timestamp())}:R>",
                value=f"**Motivo:** {motivo}\n**Por:** <@{dado_por}>",
                inline=False
            )
        
        embed.set_footer(text=f"ID do membro: {membro.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Warns(bot))
