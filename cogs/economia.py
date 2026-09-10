# cogs/economia.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from database import supabase

from typing import Optional

ICONE_MOEDA = "https://media.discordapp.net/attachments/1487374232886448248/1487556792614391888/correto_1446515346201776283_1774.png?ex=6aa27178&is=6aa11ff8&hm=13d109fdc3a542816f941c58f78489e1df56b1dfbf6a901bc28659038b0290fc"


def ler_config(guild_id):
    try:
        db = supabase.table("economia_config").select("*").eq("guilda_id", str(guild_id)).execute()
        return db.data[0] if db.data else {}
    except Exception:
        return {}


def adicionar_moedas(guild_id, user_id, quantidade):
    try:
        db_user = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(user_id)).eq("id_servidor", str(guild_id)).execute()
        saldo_atual = db_user.data[0]["moedas"] if db_user.data and db_user.data[0].get("moedas") is not None else 0
        supabase.table("membros_verificados").update({"moedas": saldo_atual + int(quantidade)}).eq("id_discord", str(user_id)).eq("id_servidor", str(guild_id)).execute()
    except Exception as e:
        print(f"[ECONOMIA] Erro adicionando moedas para {user_id}: {e}")


def get_saldo(guild_id, user_id):
    try:
        db = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(user_id)).eq("id_servidor", str(guild_id)).execute()
        if db.data:
            return db.data[0].get("moedas") or 0
    except Exception as e:
        print(f"[ECONOMIA] Erro ao ler saldo de {user_id}: {e}")
    return 0


def get_top(guild_id, limite=10):
    try:
        db = supabase.table("membros_verificados").select("moedas", "id_discord").eq("id_servidor", str(guild_id)).gt("moedas", 0).order("moedas", desc=True).limit(limite).execute()
        return db.data or []
    except Exception:
        return []


def pode_ganhar_hoje(guild_id, user_id):
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        db = supabase.table("economia_daily").select("*").eq("user_id", str(user_id)).eq("servidor_id", str(guild_id)).eq("data", hoje).execute()
        if db.data:
            return not db.data[0].get("usado", False)
    except Exception:
        pass
    return True


def marcar_daily(guild_id, user_id):
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        supabase.table("economia_daily").upsert({"user_id": str(user_id), "servidor_id": str(guild_id), "data": hoje, "usado": True}).execute()
    except Exception:
        pass


class PedirMoedasView(discord.ui.View):
    def __init__(self, bot, bot_owner_id, guild_id, remetente_id, destinatario_id, quantidade, nome_moeda):
        super().__init__(timeout=300)
        self.bot = bot
        self.bot_owner_id = bot_owner_id
        self.guild_id = guild_id
        self.remetente_id = remetente_id
        self.destinatario_id = destinatario_id
        self.quantidade = quantidade
        self.nome_moeda = nome_moeda
        self.mensagem = None

    async def on_timeout(self):
        if self.mensagem:
            try:
                await self.mensagem.edit(view=None)
            except:
                pass

    @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.success)
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[PEDIDO_MOEDAS] ACEPTAR clicked by {interaction.user.id}, expecting {self.destinatario_id}")
        if interaction.user.id != self.destinatario_id:
            return await interaction.response.send_message("❌ Este pedido não é teu.", ephemeral=True)
        saldo_destinatario = get_saldo(self.guild_id, str(self.destinatario_id))
        if saldo_destinatario < self.quantidade:
            await interaction.response.edit_message(
                embed=discord.Embed(title="⚠️ Saldo Insuficiente", description=f"Tu tens apenas **{saldo_destinatario}** {self.nome_moeda}. Precisas de **{self.quantidade}**.", color=discord.Color.red()),
                view=None
            )
            self.stop()
            return
        supabase.table("membros_verificados").update({"moedas": saldo_destinatario - self.quantidade}).eq("id_discord", str(self.destinatario_id)).eq("id_servidor", self.guild_id).execute()
        supabase.table("membros_verificados").update({"moedas": get_saldo(self.guild_id, str(self.remetente_id)) + self.quantidade}).eq("id_discord", str(self.remetente_id)).eq("id_servidor", self.guild_id).execute()
        await interaction.response.edit_message(
            embed=discord.Embed(title="✅ Pedido Aprovado", description=f"Enviaste **{self.quantidade}** {self.nome_moeda} a <@{self.remetente_id}>.", color=discord.Color.gold()),
            view=None
        )
        novo_saldo_rem = get_saldo(self.guild_id, str(self.remetente_id))
        novo_saldo_des = saldo_destinatario - self.quantidade
        try:
            bot_owner = await self.bot.fetch_user(self.bot_owner_id)
            await bot_owner.send(embed=discord.Embed(title="✅ Moedas Recebidas", description=f"Recebeste **{self.quantidade}** {self.nome_moeda}. Novo saldo: **{novo_saldo_rem}** {self.nome_moeda}.", color=discord.Color.gold()))
        except Exception as e:
            print(f"[PEDIDO_MOEDAS] ERRO DM remetente: {e}")
        try:
            bot_destinatario = await self.bot.fetch_user(self.destinatario_id)
            await bot_destinatario.send(embed=discord.Embed(title="💸 Pagamento Efetuado", description=f"Pagaste **{self.quantidade}** {self.nome_moeda} a <@{self.remetente_id}>. Novo saldo: **{novo_saldo_des}** {self.nome_moeda}.", color=discord.Color.gold()))
        except Exception as e:
            print(f"[PEDIDO_MOEDAS] ERRO DM destinatário: {e}")
        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[PEDIDO_MOEDAS] User {interaction.user.id} clicked CANCELAR")
        if interaction.user.id != self.destinatario_id:
            return await interaction.response.send_message("❌ Este pedido não é teu.", ephemeral=True)
        await interaction.response.edit_message(
            embed=discord.Embed(title="❌ Pedido Cancelado", description=f"Recusaste o pedido.", color=discord.Color.red()),
            view=None
        )
        bot_owner = await self.bot.fetch_user(self.bot_owner_id)
        await bot_owner.send(embed=discord.Embed(title="❌ Pedido Recusado", description=f"Pedido de {self.quantidade} {self.nome_moeda} recusado.", color=discord.Color.red()))
        self.stop()


class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="saldo", description="Mostra o teu saldo de moedas no servidor")
    async def saldo(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.response.send_message("❌ A economia está desativada neste servidor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        saldo_atual = get_saldo(guild_id, user_id)
        nome_moeda = cfg.get("nome_moeda", "moedas")
        embed = discord.Embed(
            title=f"💰 Carteira de {interaction.user.display_name}",
            description=f"Saldo atual: **{saldo_atual}** {nome_moeda}",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url=ICONE_MOEDA)
        embed.set_footer(text="Ganha moedas participando no servidor!")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="topmoedas", description="Mostra o top 10 membros com mais moedas")
    async def topmoedas(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.response.send_message("❌ A economia está desativada neste servidor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        top = get_top(guild_id, 10)
        if not top:
            return await interaction.followup.send("❌ Ainda ninguém tem moedas neste servidor.", ephemeral=True)

        nome_moeda = cfg.get("nome_moeda", "moedas")
        linhas = []
        for i, item in enumerate(top, 1):
            membro = interaction.guild.get_member(int(item["id_discord"]))
            nome = membro.display_name if membro else f"`{item['id_discord']}`"
            linhas.append(f"**{i}.** {nome} — 💰 `{item['moedas']}` {nome_moeda}")

        embed = discord.Embed(
            title=f"💰 Top Moedas do Servidor",
            description="\n".join(linhas),
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url=ICONE_MOEDA)
        embed.set_footer(text="Ganha mais moedas participando!")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Reseta o teu daily e ganha moedas")
    async def daily(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.response.send_message("❌ A economia está desativada neste servidor.", ephemeral=True)

        if not pode_ganhar_hoje(guild_id, user_id):
            return await interaction.response.send_message("❌ Já usaste o daily hoje! Volta amanhã.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        daily_min = cfg.get("moedas_daily_min", 5)
        daily_max = cfg.get("moedas_daily_max", 15)
        import random
        quantidade = random.randint(daily_min, daily_max)
        adicionar_moedas(guild_id, user_id, quantidade)
        marcar_daily(guild_id, user_id)
        saldo_atual = get_saldo(guild_id, user_id)
        nome_moeda = cfg.get("nome_moeda", "moedas")

        embed = discord.Embed(
            title=f"✅ Daily Resgatado!",
            description=f"Ganhas-te **{quantidade}** {nome_moeda}!\nSaldo atual: **{saldo_atual}** {nome_moeda}",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url=ICONE_MOEDA)
        embed.set_footer(text="Volta amanhã para mais!")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="add-moedas", description="Adiciona moedas ao saldo de um utilizador (Cargo Gestão)")
    async def add_moedas(self, interaction: discord.Interaction, membro: discord.Member, quantidade: int):
        from utils import verificar_permissao_gestao
        await interaction.response.defer(ephemeral=True)
        if not await verificar_permissao_gestao(interaction, supabase):
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores.", ephemeral=True)
        if quantidade <= 0:
            return await interaction.followup.send("❌ Quantidade deve ser maior que 0.", ephemeral=True)
        guild_id = str(interaction.guild_id)
        user_id = str(membro.id)

        db_check = supabase.table("membros_verificados").select("moedas").eq("id_discord", user_id).eq("id_servidor", guild_id).execute()
        if not db_check.data:
            return await interaction.followup.send(f"❌ **{membro.display_name}** não está registado. Pede-lhe que verifique-se com `/entrar` primeiro.", ephemeral=True)

        adicionar_moedas(guild_id, user_id, quantidade)
        novo_saldo = get_saldo(guild_id, user_id)
        nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
        embed = discord.Embed(
            title="✅ Moedas Adicionadas",
            description=f"Adicionaste **{quantidade}** {nome_moeda} a {membro.mention}.\nNovo saldo: **{novo_saldo}** {nome_moeda}",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=ICONE_MOEDA)
        await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            dm_embed = discord.Embed(
                title="💸 Transferência Recebida",
                description=f"Recebeste **{quantidade}** {nome_moeda} de {interaction.user.mention} em **{interaction.guild.name}**.\nNovo saldo: **{novo_saldo}** {nome_moeda}",
                color=discord.Color.gold()
            )
            dm_embed.set_thumbnail(url=ICONE_MOEDA)
            await membro.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ {membro.mention} tem DMs fechadas. A adição de moedas foi concluída, mas a notificação por DM não foi entregue.",
                ephemeral=True
            )

    @app_commands.command(name="remove-moedas", description="Remove moedas do saldo de um utilizador (Cargo Gestão)")
    async def remove_moedas(self, interaction: discord.Interaction, membro: discord.Member, quantidade: int):
        from utils import verificar_permissao_gestao
        await interaction.response.defer(ephemeral=True)
        if not await verificar_permissao_gestao(interaction, supabase):
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores.", ephemeral=True)
        if quantidade <= 0:
            return await interaction.followup.send("❌ Quantidade deve ser maior que 0.", ephemeral=True)
        guild_id = str(interaction.guild_id)
        user_id = str(membro.id)
        db_check = supabase.table("membros_verificados").select("id_discord").eq("id_discord", user_id).eq("id_servidor", guild_id).execute()
        if not db_check.data:
            return await interaction.followup.send(f"❌ **{membro.display_name}** não está registado. Pede-lhe que verifique-se com `/entrar` primeiro.", ephemeral=True)

        saldo_atual = get_saldo(guild_id, user_id)
        nova_quantidade = max(0, saldo_atual - quantidade)
        supabase.table("membros_verificados").update({"moedas": nova_quantidade}).eq("id_discord", user_id).eq("id_servidor", guild_id).execute()
        nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
        embed = discord.Embed(
            title="✅ Moedas Removidas",
            description=f"Removeste **{quantidade}** {nome_moeda} de {membro.mention}.\nNovo saldo: **{nova_quantidade}** {nome_moeda}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=ICONE_MOEDA)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="pagar", description="Transfere moedas para outro utilizador")
    async def pagar(self, interaction: discord.Interaction, destinatario: discord.Member, quantidade: int):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        remetente = interaction.user
        if quantidade <= 0:
            return await interaction.followup.send("❌ Quantidade deve ser maior que 0.", ephemeral=True)
        if destinatario.id == remetente.id:
            return await interaction.followup.send("❌ Não podes enviar moedas a ti mesmo.", ephemeral=True)
        saldo_remetente = get_saldo(guild_id, str(remetente.id))
        if saldo_remetente < quantidade:
            nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
            return await interaction.followup.send(f"❌ Saldo insuficiente. Tens **{saldo_remetente}** {nome_moeda}.", ephemeral=True)
        supabase.table("membros_verificados").update({"moedas": saldo_remetente - quantidade}).eq("id_discord", str(remetente.id)).eq("id_servidor", guild_id).execute()
        saldo_destinatario = get_saldo(guild_id, str(destinatario.id))
        supabase.table("membros_verificados").update({"moedas": saldo_destinatario + quantidade}).eq("id_discord", str(destinatario.id)).eq("id_servidor", guild_id).execute()
        nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
        novo_saldo_rem = saldo_remetente - quantidade
        novo_saldo_des = saldo_destinatario + quantidade
        try:
            dm_embed = discord.Embed(
                title="💸 Transferência Recebida",
                description=f"Recebeste **{quantidade}** {nome_moeda} de {remetente.mention}.\nNovo saldo: **{novo_saldo_des}** {nome_moeda}",
                color=discord.Color.gold()
            )
            dm_embed.set_thumbnail(url=ICONE_MOEDA)
            await destinatario.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ {destinatario.mention}, a transferência foi concluída, mas não consegui entregar a DM (Diretas fechadas).",
                ephemeral=False
            )
        try:
            dm_remetente = discord.Embed(
                title="💸 Transferência Enviada",
                description=f"Enviaste **{quantidade}** {nome_moeda} a {destinatario.mention}.\nNovo saldo: **{novo_saldo_rem}** {nome_moeda}",
                color=discord.Color.gold()
            )
            dm_remetente.set_thumbnail(url=ICONE_MOEDA)
            await remetente.send(embed=dm_remetente)
        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ {remetente.mention}, não consegui entregar a DM de confirmação.",
                ephemeral=True
            )
        sucesso_embed = discord.Embed(
            title="✅ Transferência Concluída",
            description=f"Enviaste **{quantidade}** {nome_moeda} a {destinatario.mention}.\nSaldo atual: **{novo_saldo_rem}** {nome_moeda}",
            color=discord.Color.green()
        )
        sucesso_embed.set_thumbnail(url=ICONE_MOEDA)
        await interaction.followup.send(embed=sucesso_embed, ephemeral=True)

    @app_commands.command(name="transferir", description="Transfere moedas para outro utilizador")
    async def transferir(self, interaction: discord.Interaction, destinatario: discord.Member, quantidade: int):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        remetente = interaction.user
        if quantidade <= 0:
            return await interaction.followup.send("❌ Quantidade deve ser maior que 0.", ephemeral=True)
        if destinatario.id == remetente.id:
            return await interaction.followup.send("❌ Não podes enviar moedas a ti mesmo.", ephemeral=True)
        if destinatario.bot:
            return await interaction.followup.send("❌ Não podes enviar moedas a bots.", ephemeral=True)
        saldo_remetente = get_saldo(guild_id, str(remetente.id))
        if saldo_remetente < quantidade:
            nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
            return await interaction.followup.send(f"❌ Saldo insuficiente. Tens **{saldo_remetente}** {nome_moeda}.", ephemeral=True)
        supabase.table("membros_verificados").update({"moedas": saldo_remetente - quantidade}).eq("id_discord", str(remetente.id)).eq("id_servidor", guild_id).execute()
        saldo_destinatario = get_saldo(guild_id, str(destinatario.id))
        supabase.table("membros_verificados").update({"moedas": saldo_destinatario + quantidade}).eq("id_discord", str(destinatario.id)).eq("id_servidor", guild_id).execute()
        nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
        novo_saldo_rem = saldo_remetente - quantidade
        novo_saldo_des = saldo_destinatario + quantidade
        servidor = interaction.guild.name
        try:
            dm_embed = discord.Embed(
                title="💸 Transferência Recebida",
                description=f"Recebeste **{quantidade}** {nome_moeda} de {remetente.mention} em **{servidor}**.\nNovo saldo: **{novo_saldo_des}** {nome_moeda}",
                color=discord.Color.gold()
            )
            dm_embed.set_thumbnail(url=ICONE_MOEDA)
            await destinatario.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ {destinatario.mention}, a transferência foi concluída, mas não consegui entregar a DM (Diretas fechadas).",
                ephemeral=False
            )
        try:
            dm_remetente = discord.Embed(
                title="💸 Transferência Enviada",
                description=f"Enviaste **{quantidade}** {nome_moeda} a {destinatario.mention} em **{servidor}**.\nNovo saldo: **{novo_saldo_rem}** {nome_moeda}",
                color=discord.Color.gold()
            )
            dm_remetente.set_thumbnail(url=ICONE_MOEDA)
            await remetente.send(embed=dm_remetente)
        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ {remetente.mention}, não consegui entregar a DM de confirmação.",
                ephemeral=True
            )
        sucesso_embed = discord.Embed(
            title="✅ Transferência Concluída",
            description=f"Enviaste **{quantidade}** {nome_moeda} a {destinatario.mention}.\nSaldo atual: **{novo_saldo_rem}** {nome_moeda}",
            color=discord.Color.green()
        )
        sucesso_embed.set_thumbnail(url=ICONE_MOEDA)
        await interaction.followup.send(embed=sucesso_embed, ephemeral=True)

    @app_commands.command(name="pedir_moedas", description="Pede moedas a outro utilizador (envia DM para aprovação)")
    async def pedir_moedas(self, interaction: discord.Interaction, destinatario: discord.Member, quantidade: int):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        remetente = interaction.user
        if quantidade <= 0:
            return await interaction.followup.send("❌ Quantidade deve ser maior que 0.", ephemeral=True)
        if destinatario.id == remetente.id:
            return await interaction.followup.send("❌ Não podes pedir moedas a ti mesmo.", ephemeral=True)
        if destinatario.bot:
            return await interaction.followup.send("❌ Não podes pedir moedas a bots.", ephemeral=True)
        nome_moeda = ler_config(guild_id).get("nome_moeda", "moedas")
        view = PedirMoedasView(self.bot, interaction.user.id, guild_id, remetente.id, destinatario.id, quantidade, nome_moeda)
        saldo_destinatario = get_saldo(guild_id, str(destinatario.id))
        try:
            dm_embed = discord.Embed(
                title="💸 Pedido de Moedas",
                description=f"<@{remetente.id}> pediu **{quantidade}** {nome_moeda}.\n**Tu** tens **{saldo_destinatario}** {nome_moeda} atualmente.",
                color=discord.Color.gold()
            )
            dm_embed.set_thumbnail(url=ICONE_MOEDA)
            dm_embed.add_field(name="⏱️ Timeout", value="Este pedido expira em 5 minutos.", inline=False)
            dm_embed.add_field(name="🌐 Servidor", value=f"[{interaction.guild.name}](https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id})", inline=False)
            mensagem = await destinatario.send(embed=dm_embed, view=view)
            view.mensagem = mensagem
            await interaction.followup.send(f"✅ Pedido de **{quantidade}** {nome_moeda} enviado para {destinatario.mention} por DM. Aguarda a aprovação.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ {destinatario.mention} tem DMs fechadas.", ephemeral=True)

    @app_commands.command(name="dar-moedas-massa", description="Distribui moedas a vários utilizadores ou a todos (Cargo Gestão)")
    async def dar_moedas_mass(self, interaction: discord.Interaction, quantidade: int, alvo: str = None):
        from utils import verificar_permissao_gestao
        await interaction.response.defer(ephemeral=True)
        if not await verificar_permissao_gestao(interaction, supabase):
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores.", ephemeral=True)
        if quantidade <= 0:
            return await interaction.followup.send("❌ Quantidade deve ser maior que 0.", ephemeral=True)
        guild_id = str(interaction.guild_id)
        cfg = ler_config(guild_id)
        nome_moeda = cfg.get("nome_moeda", "moedas")
        if alvo and alvo.lower() in ("@todos", "todos", "all"):
            membros = [m for m in interaction.guild.members if not m.bot]
        else:
            return await interaction.followup.send("❌ Uso: `/dar-moedas-massa [quantidade] todos`", ephemeral=True)
        if not membros:
            return await interaction.followup.send("❌ Nenhum membro encontrado para distribuir.", ephemeral=True)
        for membro in membros:
            adicionar_moedas(guild_id, str(membro.id), quantidade)
        embed = discord.Embed(
            title="✅ Moedas Distribuídas em Massa",
            description=f"Distribuíste **{quantidade}** {nome_moeda} a **{len(membros)}** membros.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=ICONE_MOEDA)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Economia(bot))
