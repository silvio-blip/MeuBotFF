# cogs/gestao.py
import discord
from discord import app_commands
from discord.ext import commands
from database import supabase

class Gestao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- FUNÇÃO MESTRA DE VERIFICAÇÃO ---
    # Substitui o "has_permissions" nativo pelo teu sistema ligado ao Supabase
    async def verificar_permissao_gestao(self, interaction: discord.Interaction) -> bool:
        # Se for o dono do servidor ou admin nativo, passa sempre
        if interaction.user.guild_permissions.administrator:
            return True
            
        # Vai ao Supabase ver qual é o cargo configurado para este servidor
        id_servidor = str(interaction.guild_id)
        db_res = supabase.table("servidores").select("cargo_gestao_id").eq("id_discord", id_servidor).execute()
        
        if db_res.data and db_res.data[0].get("cargo_gestao_id"):
            cargo_id = int(db_res.data[0]["cargo_gestao_id"])
            cargo_gestao = interaction.guild.get_role(cargo_id)
            
            # Se o cargo existir e o utilizador o tiver, deixa passar
            if cargo_gestao and cargo_gestao in interaction.user.roles:
                return True
                
        return False

    # --- 1. COMANDO PARA DAR CARGO ---
    @app_commands.command(name="dar_cargo", description="Atribui um cargo específico a um membro")
    async def dar_cargo(self, interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)

        if cargo >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Não consigo atribuir esse cargo (o meu cargo é inferior).", ephemeral=True)
        
        if cargo >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ **Acesso Negado:** Não podes atribuir cargos iguais ou superiores ao teu.", ephemeral=True)

        try:
            await membro.add_roles(cargo)
            await interaction.response.send_message(f"✅ O cargo {cargo.mention} foi atribuído ao {membro.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para atribuir este cargo.", ephemeral=True)

    # --- 2. COMANDO PARA REMOVER CARGO ---
    @app_commands.command(name="remover_cargo", description="Remove um cargo específico de um membro")
    async def remover_cargo(self, interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)

        if cargo not in membro.roles:
            return await interaction.response.send_message("⚠️ Este membro não possui esse cargo.", ephemeral=True)

        try:
            await membro.remove_roles(cargo)
            await interaction.response.send_message(f"➖ O cargo {cargo.mention} foi removido do {membro.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para remover este cargo.", ephemeral=True)

    # --- 3. COMANDO PARA LIMPAR CHAT (PURGE GERAL) ---
    @app_commands.command(name="limpar", description="Limpa uma quantidade específica de mensagens no canal")
    async def limpar(self, interaction: discord.Interaction, quantidade: int):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)

        if quantidade < 1 or quantidade > 100:
            return await interaction.response.send_message("❌ Indica uma quantidade entre 1 e 100 mensagens.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"🧹 {len(deleted)} mensagens foram apagadas com sucesso!", ephemeral=True)

    # --- 4. COMANDO PARA LIMPAR CHAT DE UM UTILIZADOR ESPECÍFICO ---
    @app_commands.command(name="limpar_membro", description="Limpa mensagens de um membro específico neste canal")
    async def limpar_membro(self, interaction: discord.Interaction, membro: discord.Member, quantidade: int):
        if not await self.verificar_permissao_gestao(interaction):
            return await interaction.response.send_message("❌ **Acesso Negado:** Não tens o cargo de gestão necessário.", ephemeral=True)

        if quantidade < 1 or quantidade > 100:
            return await interaction.response.send_message("❌ Indica uma quantidade entre 1 e 100 mensagens.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        def verificar_autor(mensagem):
            return mensagem.author.id == membro.id
            
        deleted = await interaction.channel.purge(limit=quantidade, check=verificar_autor)
        
        await interaction.followup.send(
            f"🧹 Varredura concluída! Foram apagadas **{len(deleted)}** mensagens do utilizador {membro.mention}.", 
            ephemeral=True
        )

    # --- 5. COMANDO DE INFO/GESTÃO ---
    @app_commands.command(name="gestao_info", description="Verifica o estado das permissões de gestão")
    async def gestao_info(self, interaction: discord.Interaction):
        # Vai buscar o cargo atual para mostrar no painel
        id_servidor = str(interaction.guild_id)
        db_res = supabase.table("servidores").select("cargo_gestao_id").eq("id_discord", id_servidor).execute()
        
        cargo_mencionado = "Nenhum cargo configurado. Apenas Admins."
        if db_res.data and db_res.data[0].get("cargo_gestao_id"):
            c_id = int(db_res.data[0]["cargo_gestao_id"])
            role_obj = interaction.guild.get_role(c_id)
            if role_obj:
                cargo_mencionado = role_obj.mention

        embed = discord.Embed(
            title="🛠️ Painel de Gestão S.art",
            description=f"**Cargo Autorizado:** {cargo_mencionado}\n\nAqui tens os comandos de gestão ativos no servidor:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Cargos", value="`/dar_cargo`\n`/remover_cargo`", inline=True)
        embed.add_field(name="Chat", value="`/limpar`\n`/limpar_membro`", inline=True)
        embed.set_footer(text="S.art Engine • Gestão Dinâmica")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Gestao(bot))