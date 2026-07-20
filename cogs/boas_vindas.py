# cogs/boas_vindas.py
import discord
from discord import app_commands
from discord.ext import commands
from database import supabase

class ModalBoasVindas(discord.ui.Modal, title='Personalizar Boas-Vindas'):
    titulo = discord.ui.TextInput(label='Título da Embed', placeholder='Ex: Bem-vindo ao servidor!', required=True, default="Bem-vindo!")
    descricao = discord.ui.TextInput(label='Descrição (use {user} e {membros})', placeholder='Ex: Olá {user}! Temos {membros} membros.', required=True, style=discord.TextStyle.paragraph, default="Olá {user}! Bem-vindo(a) ao nosso servidor.\nTemos agora **{membros}** membros!")
    cor = discord.ui.TextInput(label='Cor (hex sem #)', placeholder='Ex: FF5733', required=True, default="FF5733")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cor_hex = int(self.cor.value.strip(), 16)
        except ValueError:
            return await interaction.response.send_message("❌ Cor inválida! Usa o formato hex (ex: FF5733).", ephemeral=True)
        
        supabase.table("boas_vindas_config").upsert({
            "guilda_id": str(interaction.guild_id),
            "titulo": self.titulo.value,
            "descricao": self.descricao.value,
            "cor": cor_hex,
            "habilitado": True
        }).execute()
        
        await interaction.response.send_message(
            f"✅ **Configuração de boas-vindas atualizada!**\n\n"
            f"**Título:** {self.titulo.value}\n"
            f"**Descrição:** {self.descricao.value[:100]}...\n"
            f"**Cor:** #{self.cor.value}",
            ephemeral=True
        )

class SelectCanalBoasVindas(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Seleciona o canal de boas-vindas...")
    async def select_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal_selecionado = select.values[0]
        supabase.table("boas_vindas_config").upsert({
            "guilda_id": str(interaction.guild_id),
            "canal_id": str(canal_selecionado.id)
        }).execute()
        await interaction.response.send_message(f"✅ Canal de boas-vindas alterado para {canal_selecionado.mention}.", ephemeral=True)

class BoasVindasConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Personalizar Mensagem", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="bv_config_personalizar")
    async def btn_personalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalBoasVindas())

    @discord.ui.button(label="Canal de Boas-Vindas", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="bv_config_canal")
    async def btn_canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 **Seleciona o canal de boas-vindas:**", view=SelectCanalBoasVindas(), ephemeral=True)

    @discord.ui.button(label="Ativar/Desativar", style=discord.ButtonStyle.success, emoji="✅", custom_id="bv_config_toggle")
    async def btn_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_config = supabase.table("boas_vindas_config").select("habilitado").eq("guilda_id", str(interaction.guild_id)).execute()
        
        if db_config.data:
            atual = db_config.data[0].get("habilitado", True)
            novo = not atual
            supabase.table("boas_vindas_config").update({"habilitado": novo}).eq("guilda_id", str(interaction.guild_id)).execute()
            status = "ativado" if novo else "desativado"
            await interaction.response.send_message(f"✅ Sistema de boas-vindas **{status}**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Configura o sistema primeiro.", ephemeral=True)

class BoasVindas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def enviar_boas_vindas(self, member: discord.Member):
        id_servidor = str(member.guild.id)
        db_config = supabase.table("boas_vindas_config").select("*").eq("guilda_id", id_servidor).execute()
        
        if not db_config.data or not db_config.data[0].get("habilitado"):
            return
        
        cfg = db_config.data[0]
        canal_id = cfg.get("canal_id")
        
        if not canal_id or not str(canal_id).isdigit():
            return
        
        canal = member.guild.get_channel(int(canal_id))
        if not canal:
            return
        
        titulo = cfg.get("titulo", "Bem-vindo!")
        descricao = cfg.get("descricao", "Olá {user}! Bem-vindo(a) ao nosso servidor.")
        cor = cfg.get("cor", 0x00FF80)
        
        descricao = descricao.replace("{user}", member.mention).replace("{membros}", str(member.guild.member_count))
        
        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=discord.Color(cor)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Membro #{member.guild.member_count}")
        
        await canal.send(content=member.mention, embed=embed)

async def setup(bot):
    await bot.add_cog(BoasVindas(bot))
