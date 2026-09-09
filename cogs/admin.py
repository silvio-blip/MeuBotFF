# cogs/admin.py
import discord
from discord import app_commands
from discord.ext import commands
import random
import string
import asyncio
import config
from datetime import datetime, timezone
from database import supabase

def log_sart(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚙️ [S.art] {msg}")

def ler_config(guild_id):
    db = supabase.table("servidores").select("*").eq("id_discord", guild_id).execute()
    return db.data[0] if db.data else {}

def ler_sub(tabela, guild_id):
    try:
        db = supabase.table(tabela).select("*").eq("guilda_id", guild_id).execute()
        return db.data[0] if db.data else {}
    except Exception as e:
        print(f"🚨 Economia ler_sub erro [{tabela}]: {e}")
        return {}

def safe_role(guild, role_id):
    if role_id and str(role_id).isdigit():
        return guild.get_role(int(role_id))
    return None


def tem_permissao_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.id == interaction.guild.owner_id:
        return True
    if interaction.user.guild_permissions.administrator:
        return True
    dados = supabase.table("servidores").select("cargo_gestao_id").eq("id_discord", str(interaction.guild_id)).execute()
    if dados.data and dados.data[0].get("cargo_gestao_id"):
        cargo_gestao_id = int(dados.data[0]["cargo_gestao_id"])
        cargo_gestao = interaction.guild.get_role(cargo_gestao_id)
        if cargo_gestao and cargo_gestao in interaction.user.roles:
            return True
    return False

def safe_channel(guild, channel_id):
    if channel_id and str(channel_id).isdigit():
        return guild.get_channel(int(channel_id))
    return None

def toggle_config(tabela, guild_id):
    try:
        db = supabase.table(tabela).select("habilitado").eq("guilda_id", guild_id).execute()
    except Exception as e:
        print(f"🚨 Economia toggle_config erro: {e}")
        return None
    if db.data:
        atual = db.data[0].get("habilitado", True)
        try:
            supabase.table(tabela).update({"habilitado": not atual}).eq("guilda_id", guild_id).execute()
        except Exception as e:
            print(f"🚨 Economia toggle_config update erro: {e}")
        return not atual
    return None

def on_off(s):
    return "🟢 ON" if s else "🔴 OFF"

class ViewMenuPrincipal(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="📂 Seleciona uma categoria para configurar...",
        options=[
            discord.SelectOption(label="Visão Geral", value="main", emoji="📋", description="Resumo de todos os sistemas"),
            discord.SelectOption(label="Configuração Base", value="base", emoji="🛡️", description="Guilda, Cargo, Canal, Gestão"),
            discord.SelectOption(label="Sistema de Warns", value="warns", emoji="⚠️", description="Advertências e punições"),
            discord.SelectOption(label="Boas-Vindas", value="boas_vindas", emoji="👋", description="Mensagem automática ao entrar"),
            discord.SelectOption(label="Anti-Raid", value="anti_raid", emoji="🛡️", description="Proteção contra spam de joins"),
            discord.SelectOption(label="Notificações", value="notificacoes", emoji="🔔", description="Alertas do Free Fire"),
            discord.SelectOption(label="Torneios", value="torneios", emoji="🏆", description="Criar e gerir torneios"),
            discord.SelectOption(label="Ranking", value="ranking", emoji="📊", description="Ranking dos membros"),
            discord.SelectOption(label="Estatísticas", value="stats", emoji="📊", description="Dados do servidor"),
            discord.SelectOption(label="Verificação Automática", value="verificacao", emoji="🔄", description="Remover cargo de quem saiu da guilda FF"),
            discord.SelectOption(label="Economia", value="economia", emoji="💰", description="Moedas, recompensas e configurações"),
        ],
        custom_id="painel_menu_principal"
    )
    async def select_cat(self, interaction, select):
        embed, view = build_categoria(interaction.guild, select.values[0])
        await interaction.response.edit_message(embed=embed, view=view)

class ViewBase(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="base_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Alterar Guilda FF", style=discord.ButtonStyle.danger, emoji="🛡️", custom_id="base_guilda", row=1)
    async def btn_guilda(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        codigo = "".join(random.choices(string.ascii_letters + string.digits, k=20))
        supabase.table("codigos_seguranca").insert({"codigo": codigo, "id_servidor": guild_id}).execute()
        try:
            await interaction.user.send(embed=discord.Embed(title="🔐 Código de Segurança", description=f"Usa o código:\n\n```yaml\n{codigo}\n```", color=discord.Color.red()))
            await interaction.followup.send("🔐 Código enviado para a tua DM!", view=ViewInserirCodigo(guild_id, interaction.client), ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ DMs fechadas!", ephemeral=True)

    @discord.ui.button(label="Alterar Cargo de Membros", style=discord.ButtonStyle.secondary, emoji="🎖️", custom_id="base_cargo", row=1)
    async def btn_cargo(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o novo Cargo que os membros verificados recebem:**", view=SelectCargoComUpdate(str(interaction.guild_id), interaction.client, "base"), ephemeral=True)

    @discord.ui.button(label="Alterar Canal de Logs", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="base_canal", row=2)
    async def btn_canal(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot envia os registos:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "servidores", "canal_id", "base"), ephemeral=True)

    @discord.ui.button(label="Alterar Cargo de Gestão", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id="base_gestao", row=2)
    async def btn_gestao(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Cargo que os moderadores recebem:**", view=SelectCargoGestaoComUpdate(str(interaction.guild_id), interaction.client, "base"), ephemeral=True)

class ViewWarns(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="warns_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Configurar Limites", style=discord.ButtonStyle.secondary, emoji="⚙️", custom_id="warns_config", row=1)
    async def btn_config(self, interaction, button):
        await interaction.response.send_modal(ModalConfigWarns(str(interaction.guild_id), interaction.client))

    @discord.ui.button(label="Canal de Notificações", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="warns_canal", row=1)
    async def btn_canal(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot avisa quando alguém leva warn:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "warns_config", "canal_notificacoes", "warns"), ephemeral=True)

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.success, emoji="🔄", custom_id="warns_toggle", row=2)
    async def btn_toggle(self, interaction, button):
        toggle_config("warns_config", str(interaction.guild_id))
        embed, view = build_categoria(interaction.guild, "warns")
        await interaction.response.edit_message(embed=embed, view=view)

class ViewBV(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="bv_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Personalizar Mensagem", style=discord.ButtonStyle.secondary, emoji="✏️", custom_id="bv_config", row=1)
    async def btn_config(self, interaction, button):
        await interaction.response.send_modal(ModalBoasVindas(str(interaction.guild_id), interaction.client))

    @discord.ui.button(label="Definir Canal", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="bv_canal", row=1)
    async def btn_canal(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde a mensagem de boas-vindas é enviada:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "boas_vindas_config", "canal_id", "boas_vindas"), ephemeral=True)

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.success, emoji="🔄", custom_id="bv_toggle", row=2)
    async def btn_toggle(self, interaction, button):
        toggle_config("boas_vindas_config", str(interaction.guild_id))
        embed, view = build_categoria(interaction.guild, "boas_vindas")
        await interaction.response.edit_message(embed=embed, view=view)

class ViewRaid(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="raid_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Configurar Limites", style=discord.ButtonStyle.danger, emoji="⚙️", custom_id="raid_config", row=1)
    async def btn_config(self, interaction, button):
        await interaction.response.send_modal(ModalAntiRaid(str(interaction.guild_id), interaction.client))

    @discord.ui.button(label="Definir Canal de Alertas", style=discord.ButtonStyle.secondary, emoji="🚨", custom_id="raid_canal", row=1)
    async def btn_canal(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot avisa quando detecta raid:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "anti_raid_config", "canal_alertas", "anti_raid"), ephemeral=True)

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.success, emoji="🔄", custom_id="raid_toggle", row=2)
    async def btn_toggle(self, interaction, button):
        toggle_config("anti_raid_config", str(interaction.guild_id))
        embed, view = build_categoria(interaction.guild, "anti_raid")
        await interaction.response.edit_message(embed=embed, view=view)

class ViewNoti(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="noti_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Canal Atualizações", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="noti_atual", row=1)
    async def btn_atual(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot avisa sobre atualizações do Free Fire:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "notificacoes_config", "canal_atualizacoes", "notificacoes"), ephemeral=True)

    @discord.ui.button(label="Canal Membros Saíram", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="noti_membros", row=1)
    async def btn_membros(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot avisa quando um membro sai da guilda FF:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "notificacoes_config", "canal_membros", "notificacoes"), ephemeral=True)

    @discord.ui.button(label="Canal Temporada", style=discord.ButtonStyle.secondary, emoji="📅", custom_id="noti_temp", row=2)
    async def btn_temp(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot avisa sobre mudanças de temporada:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "notificacoes_config", "canal_temporada", "notificacoes"), ephemeral=True)

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.success, emoji="🔄", custom_id="noti_toggle", row=2)
    async def btn_toggle(self, interaction, button):
        toggle_config("notificacoes_config", str(interaction.guild_id))
        embed, view = build_categoria(interaction.guild, "notificacoes")
        await interaction.response.edit_message(embed=embed, view=view)

class ViewTorneios(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="torneios_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Definir Canal de Vitórias", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="torneios_canal_vitorias", row=1)
    async def btn_canal(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde as vitórias dos torneios são anunciadas:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "torneios_config", "canal_vitorias", "torneios"), ephemeral=True)

class ViewVerificacao(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="verificacao_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Definir Canal", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="verificacao_canal", row=1)
    async def btn_canal(self, interaction, button):
        await interaction.response.send_message("👇 **Seleciona o Canal onde o bot avisa sobre remoções de cargo:**", view=SelectCanalComUpdate(str(interaction.guild_id), interaction.client, "verificacao_automatica_config", "canal_verificacao_id", "verificacao"), ephemeral=True)

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.success, emoji="🔄", custom_id="verificacao_toggle", row=1)
    async def btn_toggle(self, interaction, button):
        toggle_config("verificacao_automatica_config", str(interaction.guild_id))
        embed, view = build_categoria(interaction.guild, "verificacao")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Verificar Agora", style=discord.ButtonStyle.danger, emoji="⚡", custom_id="verificacao_manual", row=2)
    async def btn_manual(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        cfg = ler_sub("verificacao_automatica_config", guild_id)
        servidor = ler_config(guild_id)
        if not servidor.get("id_guilda_ff"):
            return await interaction.followup.send("❌ Servidor sem guilda configurada.", ephemeral=True)

        removidos = []
        membros = supabase.table("membros_verificados").select("*").eq("id_servidor", guild_id).execute()
        cargo_id = int(servidor.get("cargo_id") or 0)
        cargo = interaction.guild.get_role(cargo_id) if cargo_id else None
        guilda_ff_id = str(servidor.get("id_guilda_ff", ""))
        for m in membros.data or []:
            uid = m.get("id_ff")
            if not uid:
                continue
            url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
            headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
            try:
                async with interaction.client.session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        continue
                    dados = await resp.json()
                    player_data = dados.get("player", dados)
                    clan_info = player_data.get("clanInfo") or {}
                    clan_id = str(clan_info.get("clanId", ""))
                    member = interaction.guild.get_member(int(m["id_discord"]))
                    if clan_id and clan_id != guilda_ff_id:
                        if member and cargo and cargo in member.roles:
                            try:
                                await member.remove_roles(cargo)
                                removidos.append(member.display_name)
                            except discord.Forbidden:
                                pass
                        supabase.table("membros_verificados").delete().eq("id_discord", str(m["id_discord"])).eq("id_servidor", guild_id).execute()
            except Exception:
                pass

        texto = "\n".join(f"• {nome}" for nome in removidos) if removidos else "Nenhum membro removido."
        await interaction.followup.send(f"✅ Verificação manual concluída.\n**Removidos:**\n{texto}", ephemeral=True)

class ViewEconomia(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="📂 Voltar ao menu principal...", options=[discord.SelectOption(label="Menu Principal", value="main", emoji="📋")], custom_id="economia_back")
    async def back(self, interaction, select):
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Configurar Recompensas", style=discord.ButtonStyle.secondary, emoji="⚙️", custom_id="economia_config_recompensas", row=1)
    async def btn_config_recompensas(self, interaction, button):
        await interaction.response.send_modal(ModalConfigEconomiaRecompensas(str(interaction.guild_id), interaction.client))

    @discord.ui.button(label="Configurar Daily/Limite", style=discord.ButtonStyle.secondary, emoji="📅", custom_id="economia_config_daily", row=1)
    async def btn_config_daily(self, interaction, button):
        await interaction.response.send_modal(ModalConfigEconomiaDaily(str(interaction.guild_id), interaction.client))

    @discord.ui.button(label="Nome da Moeda", style=discord.ButtonStyle.secondary, emoji="🏷️", custom_id="economia_config_nome", row=2)
    async def btn_config_nome(self, interaction, button):
        await interaction.response.send_modal(ModalConfigEconomiaNome(str(interaction.guild_id), interaction.client))

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.success, emoji="🔄", custom_id="economia_toggle", row=2)
    async def btn_toggle(self, interaction, button):
        toggle_config("economia_config", str(interaction.guild_id))
        embed, view = build_categoria(interaction.guild, "economia")
        await interaction.response.edit_message(embed=embed, view=view)

def build_categoria(guild, cat):
    guild_id = str(guild.id)
    dados = ler_config(guild_id)
    if not dados:
        return discord.Embed(title="⚠️ Usa `/configurar` primeiro.", color=discord.Color.red()), ViewMenuPrincipal()

    cargo_atual = safe_role(guild, dados.get("cargo_id"))
    canal_atual = safe_channel(guild, dados.get("canal_id"))
    cargo_gestao = safe_role(guild, dados.get("cargo_gestao_id"))
    id_guilda = dados.get("id_guilda_ff", "Não definido")

    warns_cfg = ler_sub("warns_config", guild_id)
    bv_cfg = ler_sub("boas_vindas_config", guild_id)
    raid_cfg = ler_sub("anti_raid_config", guild_id)
    noti_cfg = ler_sub("notificacoes_config", guild_id)

    db_members = supabase.table("membros_verificados").select("id_discord").eq("id_servidor", guild_id).execute()
    member_count = len(db_members.data) if db_members.data else 0

    if cat == "main":
        embed = discord.Embed(
            title="⚙️ Painel de Controlo S.art",
            description=(
                "Bem-vindo ao **painel de administração**!\n"
                "Seleciona uma categoria no menu abaixo para configurar.\n\n"
                "Aqui encontras todas as ferramentas para gerir o servidor."
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        
        status_fields = [
            ("🛡️ Configuração Base", f"{'✅' if dados else '⚠️'} Guilda: `{id_guilda}`\n📋 **Cargo:** {cargo_atual.mention if cargo_atual else '⚠️ Não definido'}\n📢 **Canal:** {canal_atual.mention if canal_atual else '⚠️ Não definido'}", False),
            ("⚠️ Warns", f"**Status:** {on_off(warns_cfg.get('habilitado', False))}\n📊 Limite: `{warns_cfg.get('max_warns', 3)}` warns\n⏰ Expira em: `{warns_cfg.get('dias_expiracao', 30)}` dias", True),
            ("👋 Boas-Vindas", f"**Status:** {on_off(bv_cfg.get('habilitado', False))}\n📢 Canal: {safe_channel(guild, bv_cfg.get('canal_id')).mention if safe_channel(guild, bv_cfg.get('canal_id')) else '⚠️ Não definido'}", True),
            ("🛡️ Anti-Raid", f"**Status:** {on_off(raid_cfg.get('habilitado', False))}\n📊 Limite: `{raid_cfg.get('limite_joins', 5)}` joins/min\n⏱️ Lock: `{raid_cfg.get('duracao_lock', 5)}` min", True),
            ("🔔 Notificações", f"**Status:** {on_off(noti_cfg.get('habilitado', False))}\n🎮 FF News, 👤 Saídas, 📅 Temporada", True),
            ("📊 Estatísticas", f"**👥 Verificados:** `{member_count}` membros\n🏆 Ranking ativo\n🔄 Verificação automática", True),
        ]
        
        for name, value, inline in status_fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        embed.set_footer(text="🔄 Usa o menu acima para navegar entre categorias")
        return embed, ViewMenuPrincipal()

    elif cat == "base":
        embed = discord.Embed(
            title="🛡️ Configuração Base",
            description="Configurações principais do servidor.\nCada botão permite alterar uma configuração.",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="🛡️ Guilda FF", value=f"`{id_guilda}`", inline=True)
        embed.add_field(name="🎖️ Cargo Membro", value=cargo_atual.mention if cargo_atual else "⚠️ Não definido", inline=True)
        embed.add_field(name="📢 Canal Logs", value=canal_atual.mention if canal_atual else "⚠️ Não definido", inline=True)
        embed.add_field(name="🛠️ Cargo Gestão", value=cargo_gestao.mention if cargo_gestao else "⚠️ Não definido", inline=True)
        embed.add_field(name="👥 Verificados", value=f"`{member_count}` membros", inline=True)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n🛡️ **Alterar Guilda** — Muda o ID da guilda FF\n🎖️ **Alterar Cargo** — Muda o cargo dos membros\n📢 **Alterar Canal** — Muda o canal de logs\n🛠️ **Cargo Gestão** — Muda o cargo dos mods", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewBase()

    elif cat == "warns":
        warns_on = warns_cfg.get("habilitado", False)
        mw = warns_cfg.get("max_warns", 3)
        de = warns_cfg.get("dias_expiracao", 30)
        canal_warns = safe_channel(guild, warns_cfg.get("canal_notificacoes"))
        embed = discord.Embed(
            title="⚠️ Sistema de Warns",
            description="Sistema de advertências.\nQuando um membro faz algo errado, o admin dá um warn.\nCom X warns, leva ban automático.",
            color=discord.Color.from_rgb(255, 140, 0)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1036/1036552.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="📊 Status", value=on_off(warns_on), inline=True)
        embed.add_field(name="🔢 Limite", value=f"`{mw}` strikes = ban", inline=True)
        embed.add_field(name="⏰ Expiração", value=f"`{de}` dias", inline=True)
        embed.add_field(name="📢 Canal Notificações", value=canal_warns.mention if canal_warns else "⚠️ Não definido", inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n⚙️ **Configurar Limites** — Muda o máximo de warns e dias\n📢 **Definir Canal** — Onde o bot avisa dos warns\n🔄 **Ligar/Desligar** — Ativa ou desativa o sistema", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewWarns()

    elif cat == "boas_vindas":
        bv_on = bv_cfg.get("habilitado", False)
        bv_canal = safe_channel(guild, bv_cfg.get("canal_id"))
        embed = discord.Embed(
            title="👋 Boas-Vindas",
            description="Envia uma embed automática quando novos membros entram.\nPersonaliza o título, descrição e cor.",
            color=discord.Color.from_rgb(0, 200, 255)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2583/2583344.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="📊 Status", value=on_off(bv_on), inline=True)
        embed.add_field(name="📢 Canal", value=bv_canal.mention if bv_canal else "⚠️ Não definido", inline=True)
        embed.add_field(name="📝 Título", value=bv_cfg.get("titulo", "—"), inline=False)
        descricao_curta = bv_cfg.get("descricao", "—")
        if len(descricao_curta) > 150:
            descricao_curta = descricao_curta[:150] + "..."
        embed.add_field(name="📄 Descrição", value=descricao_curta, inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n✏️ **Personalizar Mensagem** — Muda título, descrição e cor\n📢 **Definir Canal** — Onde a mensagem é enviada\n🔄 **Ligar/Desligar** — Ativa ou desativa o sistema\n\n**Variáveis:** `{user}` = menção, `{membros}` = total", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewBV()

    elif cat == "anti_raid":
        raid_on = raid_cfg.get("habilitado", False)
        rl = raid_cfg.get("limite_joins", 5)
        dl = raid_cfg.get("duracao_lock", 5)
        canal_raid = safe_channel(guild, raid_cfg.get("canal_alertas"))
        embed = discord.Embed(
            title="🛡️ Anti-Raid",
            description="Protege o servidor contra ataques de raid.\nSe muitos membros entrarem ao mesmo tempo, o bot bloqueia o servidor.",
            color=discord.Color.from_rgb(255, 50, 50)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1063/1063372.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="📊 Status", value=on_off(raid_on), inline=True)
        embed.add_field(name="🔢 Limite", value=f"`{rl}` joins/min", inline=True)
        embed.add_field(name="⏱️ Lock", value=f"`{dl}` minutos", inline=True)
        embed.add_field(name="🚨 Canal Alertas", value=canal_raid.mention if canal_raid else "⚠️ Não definido", inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n⚙️ **Configurar Limites** — Muda o máximo de joins e duração\n🚨 **Definir Canal** — Onde o bot avisa de raids\n🔄 **Ligar/Desligar** — Ativa ou desativa a proteção", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewRaid()

    elif cat == "notificacoes":
        noti_on = noti_cfg.get("habilitado", False)
        noti_atual = safe_channel(guild, noti_cfg.get('canal_atualizacoes'))
        noti_membros = safe_channel(guild, noti_cfg.get('canal_membros'))
        noti_temp = safe_channel(guild, noti_cfg.get('canal_temporada'))
        embed = discord.Embed(
            title="🔔 Notificações",
            description="Alertas automáticos sobre o Free Fire.\nO bot verifica e avisa sobre mudanças.",
            color=discord.Color.from_rgb(150, 100, 255)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/906/906334.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="📊 Status", value=on_off(noti_on), inline=True)
        embed.add_field(name="🎮 Canal Atualizações", value=noti_atual.mention if noti_atual else "❌ Não definido", inline=False)
        embed.add_field(name="👤 Canal Membros Saíram", value=noti_membros.mention if noti_membros else "❌ Não definido", inline=False)
        embed.add_field(name="📅 Canal Temporada", value=noti_temp.mention if noti_temp else "❌ Não definido", inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n🔄 **Atualizações** — Canal para news do jogo\n👤 **Membros** — Canal para quem saiu da guilda\n📅 **Temporada** — Canal para mudanças de rank\n🔄 **Ligar/Desligar** — Ativa ou desativa as notificações", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewNoti()

    elif cat == "torneios":
        db_torneios = supabase.table("torneios").select("*").eq("guilda_id", guild_id).eq("status", "em_andamento").execute()
        torneios_ativos = len(db_torneios.data) if db_torneios.data else 0
        
        # Buscar canal de vitórias configurado
        canal_vitorias_text = "⚠️ Não definido"
        try:
            db_tc = supabase.table("torneios_config").select("*").eq("guilda_id", guild_id).execute()
            if db_tc.data and db_tc.data[0].get("canal_vitorias"):
                cv = safe_channel(guild, db_tc.data[0]["canal_vitorias"])
                canal_vitorias_text = cv.mention if cv else "⚠️ Canal não encontrado"
        except Exception:
            pass
        
        embed = discord.Embed(
            title="🏆 Sistema de Torneios",
            description="Gerencia torneios da guilda.\nUsa os comandos slash para criar e gerir.",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2583/2583307.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="🏆 Torneios Ativos", value=f"**{torneios_ativos}**", inline=True)
        embed.add_field(name="📢 Canal de Vitórias", value=canal_vitorias_text, inline=True)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Comandos Admin:**\n`/torneio_criar` — Criar (Solo/Duo/Trio/Squad)\n`/torneio_iniciar id` — Iniciar\n`/torneio_resultado id @venc` — Resultado\n`/torneio_finalizar id` — Finalizar\n\n**Comandos Membros:**\n`/torneio_equipa_criar id nome @m1...` — Criar equipa\n`/torneio_equipa_ver id` — Ver equipas", inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**ℹ️ Ao finalizar:** DM ao campeão + mensagem no canal + dados eliminados", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewTorneios()

    elif cat == "ranking":
        db_cache = supabase.table("ranking_cache").select("*").eq("guilda_id", guild_id).order("ranking_points", desc=True).limit(5).execute()
        cache_count = len(db_cache.data) if db_cache.data else 0
        embed = discord.Embed(
            title="📊 Ranking da Guilda",
            description="Ranking dos membros por pontos Battle Royale.\nUsa os comandos slash para ver o ranking completo.",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2583/2583307.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="👥 Membros no Ranking", value=f"**{cache_count}**", inline=True)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Comandos Membros:**\n`/ranking_guilda` — Ver top 10\n`/meu_ranking` — Tua posição\n\n**Comandos Admin:**\n`/atualizar_ranking` — Forçar update do ranking", inline=False)
        if db_cache.data:
            top_text = ""
            for i, r in enumerate(db_cache.data[:5], 1):
                membro = guild.get_member(int(r["usuario_id"]))
                nome = membro.display_name if membro else "—"
                top_text += f"**{i}.** {nome} — **{r.get('ranking_points', 0)}** pts\n"
            embed.add_field(name="🥇 Top 5", value=top_text, inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewMenuPrincipal()

    elif cat == "stats":
        embed = discord.Embed(
            title="📊 Estatísticas do Servidor",
            description="Dados gerais do servidor e do bot.",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="👥 Membros Verificados", value=f"**{member_count}**", inline=True)
        embed.add_field(name="🏛️ Servidor", value=guild.name, inline=True)
        embed.add_field(name="🛡️ Guilda FF", value=f"`{id_guilda}`", inline=True)
        embed.add_field(name="⚠️ Warns", value=on_off(warns_cfg.get("habilitado", False)), inline=True)
        embed.add_field(name="👋 Boas-Vindas", value=on_off(bv_cfg.get("habilitado", False)), inline=True)
        embed.add_field(name="🛡️ Anti-Raid", value=on_off(raid_cfg.get("habilitado", False)), inline=True)
        embed.add_field(name="🔔 Notificações", value=on_off(noti_cfg.get("habilitado", False)), inline=True)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewMenuPrincipal()

    elif cat == "verificacao":
        ver_cfg = ler_sub("verificacao_automatica_config", guild_id)
        ver_on = ver_cfg.get("habilitado", False)
        canal_ver = safe_channel(guild, ver_cfg.get("canal_verificacao_id"))
        embed = discord.Embed(
            title="🔄 Verificação Automática",
            description="Remove automaticamente o cargo de registro de quem saiu da guilda FF.\nRoda a cada 24h (horário de Portugal).",
            color=discord.Color.from_rgb(0, 200, 150)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2583/2583297.png")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="📊 Status", value=on_off(ver_on), inline=True)
        embed.add_field(name="📢 Canal de Logs", value=canal_ver.mention if canal_ver else "⚠️ Não definido", inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n📢 **Definir Canal** — Onde o bot avisa das remoções\n🔄 **Ligar/Desligar** — Ativa ou desativa a verificação\n⚡ **Verificar Agora** — Roda a verificação manualmente", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewVerificacao()

    elif cat == "economia":
        from cogs.economia import get_emoji_moeda
        cfg = ler_sub("economia_config", guild_id)
        on = cfg.get("habilitado", True)
        entrada = cfg.get("moedas_entrada", 10)
        convite = cfg.get("moedas_convite", 15)
        tp = cfg.get("moedas_torneio_participar", 20)
        tv = cfg.get("moedas_torneio_vencer", 100)
        daily_min = cfg.get("moedas_daily_min", 5)
        daily_max = cfg.get("moedas_daily_max", 15)
        nome_moeda = cfg.get("nome_moeda", "moedas")
        emoji_moeda = get_emoji_moeda(guild)
        embed = discord.Embed(
            title=f"{emoji_moeda} Economia do Servidor",
            description="Configura as recompensas e limites do sistema de moedas.",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.add_field(name="📊 Status", value=on_off(on), inline=True)
        embed.add_field(name="🏷️ Nome da Moeda", value=f"`{nome_moeda}`", inline=True)
        embed.add_field(name="🎁 Recompensas", value=(
            f"**Entrada:** `{entrada}` {nome_moeda}\n"
            f"**Convite:** `{convite}` {nome_moeda}\n"
            f"**Participar Torneio:** `{tp}` {nome_moeda}\n"
            f"**Vencer Torneio:** `{tv}` {nome_moeda}\n"
            f"**Daily:** `{daily_min}`-`{daily_max}` {nome_moeda}"
        ), inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="**Ações disponíveis:**\n🔄 **Ligar/Desligar** — Ativa ou desativa a economia\n⚙️ **Configurar Recompensas** — Muda valores por ação\n📅 **Configurar Daily/Limite** — Muda valor do daily\n🏷️ **Nome da Moeda** — Altera o nome exibido", inline=False)
        embed.set_footer(text="🔄 Usa o menu abaixo para voltar ao menu principal")
        return embed, ViewEconomia()

    embed, view = build_categoria(guild, "main")
    return embed, view

class ModalNovaGuilda(discord.ui.Modal, title='Alterar Guilda FF'):
    novo_id = discord.ui.TextInput(label='Novo ID da Guilda FF', placeholder='Ex: 3054516545', required=True)
    codigo = discord.ui.TextInput(label='Código (da tua DM)', placeholder='Cola os 20 caracteres...', required=True, min_length=20, max_length=20)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        codigo = self.codigo.value.strip()
        novo_id = self.novo_id.value.strip()
        if not novo_id.isdigit():
            return await interaction.followup.send("❌ ID Inválido!")
        db = supabase.table("codigos_seguranca").select("*").eq("codigo", codigo).eq("id_servidor", self._guild_id).execute()
        if not db.data:
            return await interaction.followup.send("❌ Código inválido.", ephemeral=True)
        supabase.table("servidores").update({"id_guilda_ff": novo_id}).eq("id_discord", self._guild_id).execute()
        supabase.table("codigos_seguranca").delete().eq("codigo", codigo).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, "base")
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ModalConfigWarns(discord.ui.Modal, title='Configurar Limites de Warns'):
    max_warns = discord.ui.TextInput(label='Máximo de warns antes do ban', placeholder='Ex: 3', default="3", required=True)
    dias = discord.ui.TextInput(label='Dias para o warn expirar', placeholder='Ex: 30', default="30", required=True)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction):
        try:
            mw = int(self.max_warns.value)
            d = int(self.dias.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valores inválidos!", ephemeral=True)
        supabase.table("warns_config").upsert({"guilda_id": self._guild_id, "max_warns": mw, "dias_expiracao": d, "habilitado": True}).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, "warns")
            await interaction.response.edit_message(embed=embed, view=view)

class ModalBoasVindas(discord.ui.Modal, title='Personalizar Boas-Vindas'):
    titulo = discord.ui.TextInput(label='Título da embed', placeholder='Ex: Bem-vindo!', default="Bem-vindo!", required=True)
    descricao = discord.ui.TextInput(label='Descrição ({user} e {membros})', placeholder='Olá {user}! Temos {membros} membros!', default="Olá {user}! Bem-vindo(a) ao nosso servidor.\nTemos agora **{membros}** membros!", style=discord.TextStyle.paragraph, required=True)
    cor = discord.ui.TextInput(label='Cor da embed (hex sem #)', placeholder='Ex: FF5733', default="FF5733", required=True)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction):
        try:
            cor_hex = int(self.cor.value.strip(), 16)
        except ValueError:
            return await interaction.response.send_message("❌ Cor inválida! Usa formato hex (ex: FF5733).", ephemeral=True)
        supabase.table("boas_vindas_config").upsert({"guilda_id": self._guild_id, "titulo": self.titulo.value, "descricao": self.descricao.value, "cor": cor_hex, "habilitado": True}).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, "boas_vindas")
            await interaction.response.edit_message(embed=embed, view=view)

class ModalAntiRaid(discord.ui.Modal, title='Configurar Limites de Anti-Raid'):
    limite = discord.ui.TextInput(label='Máximo de joins por minuto', placeholder='Ex: 5', default="5", required=True)
    duracao = discord.ui.TextInput(label='Duração do bloqueio (minutos)', placeholder='Ex: 5', default="5", required=True)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction):
        try:
            l = int(self.limite.value)
            d = int(self.duracao.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valores inválidos!", ephemeral=True)
        supabase.table("anti_raid_config").upsert({"guilda_id": self._guild_id, "limite_joins": l, "duracao_lock": d, "habilitado": True}).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, "anti_raid")
            await interaction.response.edit_message(embed=embed, view=view)

class ModalConfigEconomiaRecompensas(discord.ui.Modal, title='Configurar Recompensas'):
    moedas_entrada = discord.ui.TextInput(label='Moedas por Verificação (/entrar)', placeholder='Ex: 10', default="10", required=True)
    moedas_convite = discord.ui.TextInput(label='Moedas por Convite', placeholder='Ex: 15', default="15", required=True)
    moedas_torneio_participar = discord.ui.TextInput(label='Moedas por Participar Torneio', placeholder='Ex: 20', default="20", required=True)
    moedas_torneio_vencer = discord.ui.TextInput(label='Moedas por Vencer Torneio', placeholder='Ex: 100', default="100", required=True)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction):
        try:
            valores = {
                "guilda_id": self._guild_id,
                "moedas_entrada": int(self.moedas_entrada.value),
                "moedas_convite": int(self.moedas_convite.value),
                "moedas_torneio_participar": int(self.moedas_torneio_participar.value),
                "moedas_torneio_vencer": int(self.moedas_torneio_vencer.value),
                "habilitado": True
            }
        except ValueError:
            return await interaction.response.send_message("❌ Valores inválidos! Usa apenas números.", ephemeral=True)
        supabase.table("economia_config").upsert(valores).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, "economia")
            await interaction.response.edit_message(embed=embed, view=view)


class ModalConfigEconomiaDaily(discord.ui.Modal, title='Configurar Daily'):
    moedas_daily_min = discord.ui.TextInput(label='Mínimo de moedas por Daily', placeholder='Ex: 5', default="5", required=True)
    moedas_daily_max = discord.ui.TextInput(label='Máximo de moedas por Daily', placeholder='Ex: 15', default="15", required=True)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction):
        try:
            valores = {
                "guilda_id": self._guild_id,
                "moedas_daily_min": int(self.moedas_daily_min.value),
                "moedas_daily_max": int(self.moedas_daily_max.value)
            }
        except ValueError:
            return await interaction.response.send_message("❌ Valores inválidos! Usa apenas números.", ephemeral=True)
        db = supabase.table("economia_config").select("*").eq("guilda_id", self._guild_id).execute()
        if db.data:
            supabase.table("economia_config").update(valores).eq("guilda_id", self._guild_id).execute()
        else:
            valores["habilitado"] = True
            valores.setdefault("moedas_entrada", 10)
            valores.setdefault("moedas_convite", 15)
            valores.setdefault("moedas_torneio_participar", 20)
            valores.setdefault("moedas_torneio_vencer", 100)
            valores.setdefault("moedas_daily", 10)
            supabase.table("economia_config").upsert(valores).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, "economia")
            await interaction.response.edit_message(embed=embed, view=view)


class ModalConfigEconomiaNome(discord.ui.Modal, title='Configurar Nome da Moeda'):
    nome_moeda = discord.ui.TextInput(label='Nome da Moeda', placeholder='Ex: Rubis, Créditos, Gold', default="moedas", required=True, max_length=30)

    def __init__(self, guild_id, bot):
        super().__init__()
        self._guild_id = guild_id
        self._bot = bot
        try:
            db = supabase.table("economia_config").select("nome_moeda").eq("guilda_id", str(guild_id)).execute()
            if db.data and db.data[0].get("nome_moeda"):
                self.nome_moeda.default = db.data[0]["nome_moeda"]
        except Exception:
            pass

    async def on_submit(self, interaction):
        valores = {
            "guilda_id": self._guild_id,
            "nome_moeda": self.nome_moeda.value.strip()
        }
        try:
            db = supabase.table("economia_config").select("*").eq("guilda_id", self._guild_id).execute()
            if db.data:
                supabase.table("economia_config").update(valores).eq("guilda_id", self._guild_id).execute()
            else:
                valores["habilitado"] = True
                valores.setdefault("moedas_entrada", 10)
                valores.setdefault("moedas_convite", 15)
                valores.setdefault("moedas_torneio_participar", 20)
                valores.setdefault("moedas_torneio_vencer", 100)
                valores.setdefault("moedas_daily", 10)
                valores.setdefault("limite_diario", 50)
                supabase.table("economia_config").upsert(valores).execute()
        except Exception as e:
            print(f"🚨 Economia Nome Moeda ERRO: {e}")
            await interaction.response.send_message("❌ Erro ao salvar o nome da moeda.", ephemeral=True)
            return

        try:
            await interaction.response.send_message(f"✅ Nome da moeda salvo: **{valores['nome_moeda']}**", ephemeral=True)
        except Exception as e:
            print(f"🚨 Economia Nome Moeda resposta ERRO: {e}")

        try:
            guild = self._bot.get_guild(int(self._guild_id))
            if guild:
                embed, view = build_categoria(guild, "economia")
                await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            print(f"🚨 Economia Nome Moeda painel ERRO: {e}")

class SelectCargoComUpdate(discord.ui.View):
    def __init__(self, guild_id, bot, cat):
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._bot = bot
        self._cat = cat

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="🎖️ Seleciona o Cargo...")
    async def select(self, interaction, select):
        supabase.table("servidores").update({"cargo_id": str(select.values[0].id)}).eq("id_discord", self._guild_id).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, self._cat)
            await interaction.response.edit_message(embed=embed, view=view)

class SelectCanalComUpdate(discord.ui.View):
    def __init__(self, guild_id, bot, tabela, campo, cat):
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._bot = bot
        self._tabela = tabela
        self._campo = campo
        self._cat = cat

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Seleciona o Canal...")
    async def select(self, interaction, select):
        supabase.table(self._tabela).upsert({"guilda_id": self._guild_id, self._campo: str(select.values[0].id)}).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, self._cat)
            await interaction.response.edit_message(embed=embed, view=view)

class SelectCargoGestaoComUpdate(discord.ui.View):
    def __init__(self, guild_id, bot, cat):
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._bot = bot
        self._cat = cat

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="🛠️ Seleciona o Cargo de Gestão...")
    async def select(self, interaction, select):
        supabase.table("servidores").update({"cargo_gestao_id": str(select.values[0].id)}).eq("id_discord", self._guild_id).execute()
        guild = self._bot.get_guild(int(self._guild_id))
        if guild:
            embed, view = build_categoria(guild, self._cat)
            await interaction.response.edit_message(embed=embed, view=view)

class ViewInserirCodigo(discord.ui.View):
    def __init__(self, guild_id, bot):
        super().__init__(timeout=None)
        self._guild_id = guild_id
        self._bot = bot

    @discord.ui.button(label="Inserir Código de Segurança", style=discord.ButtonStyle.success, emoji="🔑", custom_id="painel_inserir_codigo")
    async def inserir(self, interaction, button):
        await interaction.response.send_modal(ModalNovaGuilda(self._guild_id, self._bot))

class ModalConfiguracao(discord.ui.Modal, title='Registo da Guilda S.art'):
    nome_admin = discord.ui.TextInput(label='O teu Nome', placeholder='Ex: Silvanio', required=True)
    email_admin = discord.ui.TextInput(label='Email de Contacto', placeholder='admin@email.com', required=True)
    id_guilda = discord.ui.TextInput(label='ID da Guilda Oficial', placeholder='Ex: 3054516545', required=True)

    def __init__(self, cargo_id, canal_id):
        super().__init__()
        self.cargo_id = cargo_id
        self.canal_id = canal_id

    async def on_submit(self, interaction):
        supabase.table("servidores").upsert({"id_discord": str(interaction.guild_id), "id_guilda_ff": self.id_guilda.value, "cargo_id": self.cargo_id, "email": self.email_admin.value, "canal_id": self.canal_id}).execute()
        await interaction.response.send_message(f"✅ **Tudo pronto, {self.nome_admin.value}!** Usa `/painel`.", ephemeral=True)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurar", description="Configura a guilda pela primeira vez")
    async def configurar(self, interaction, cargo_membros: discord.Role, canal_notificacoes: discord.TextChannel):
        if not tem_permissao_admin(interaction):
            return await interaction.response.send_message("⛔ Apenas o Dono, Admins ou Gestão.", ephemeral=True)
        await interaction.response.send_modal(ModalConfiguracao(str(cargo_membros.id), str(canal_notificacoes.id)))

    @app_commands.command(name="painel", description="Abre o Painel de Controlo")
    async def painel(self, interaction):
        if not tem_permissao_admin(interaction):
            return await interaction.response.send_message("⛔ Apenas o Dono, Admins ou Gestão.", ephemeral=True)
        embed, view = build_categoria(interaction.guild, "main")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="remover_servidor", description="Apaga todos os dados do bot deste servidor no Supabase")
    async def remover_servidor(self, interaction):
        if not tem_permissao_admin(interaction):
            return await interaction.response.send_message("⛔ Apenas o Dono, Admins ou Gestão.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        
        tabelas = [
            ("servidores", "id_discord"),
            ("membros_verificados", "id_servidor"),
            ("warns_config", "guilda_id"),
            ("warns", "id_servidor"),
            ("boas_vindas_config", "guilda_id"),
            ("anti_raid_config", "guilda_id"),
            ("notificacoes_config", "guilda_id"),
            ("torneios", "guilda_id"),
            ("torneios_config", "guilda_id"),
            ("ranking_cache", "guilda_id"),
            ("convites_config", "guilda_id"),
            ("codigos_seguranca", "id_servidor"),
            ("verificacao_automatica_config", "guilda_id"),
        ]
        
        apagados = []
        for tabela, campo in tabelas:
            try:
                res = supabase.table(tabela).delete().eq(campo, guild_id).execute()
                if res.data:
                    apagados.append(f"✅ {tabela}: {len(res.data)} registos")
                else:
                    apagados.append(f"⚪ {tabela}: nada")
            except Exception as e:
                apagados.append(f"❌ {tabela}: erro - {e}")
        
        embed = discord.Embed(
            title="🗑️ Remoção de Dados do Servidor",
            description=f"Dados associados ao servidor **{interaction.guild.name}** apagados do Supabase.",
            color=discord.Color.from_rgb(255, 50, 50)
        )
        embed.add_field(name="Tabelas afetadas", value="\n".join(apagados), inline=False)
        embed.set_footer(text="⚠️ Esta ação remove permanentemente todos os dados do bot deste servidor.")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    for v in [ViewMenuPrincipal(), ViewBase(), ViewWarns(), ViewBV(), ViewRaid(), ViewNoti(), ViewTorneios(), ViewVerificacao(), ViewEconomia()]:
        bot.add_view(v)
    cog = Admin(bot)
    await bot.add_cog(cog)
    if not getattr(bot, "verificacao_automatica_task", None):
        bot.verificacao_automatica_task = bot.loop.create_task(verificacao_automatica_loop(bot))


async def verificacao_automatica_loop(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            agora = datetime.now(timezone.utc)
            if agora.hour == 0 and agora.minute == 0:
                for guild in bot.guilds:
                    guild_id = str(guild.id)
                    cfg = supabase.table("verificacao_automatica_config").select("*").eq("guilda_id", guild_id).execute()
                    if not cfg.data or not cfg.data[0].get("habilitado"):
                        continue
                    servidor = supabase.table("servidores").select("*").eq("id_discord", guild_id).execute()
                    if not servidor.data:
                        continue
                    dados_servidor = servidor.data[0]
                    guilda_ff_id = str(dados_servidor.get("id_guilda_ff", ""))
                    cargo_id = int(dados_servidor.get("cargo_id") or 0)
                    cargo = guild.get_role(cargo_id) if cargo_id else None
                    if not guilda_ff_id or not cargo:
                        continue

                    membros = supabase.table("membros_verificados").select("*").eq("id_servidor", guild_id).execute()
                    removidos = []
                    for m in membros.data or []:
                        uid = m.get("id_ff")
                        if not uid:
                            continue
                        url = f"{config.API_VERCEL_URL.rstrip('/')}/api/player?uid={uid}"
                        headers = {"x-api-key": config.API_VERCEL_KEY, "Accept": "application/json"}
                        try:
                            async with bot.session.get(url, headers=headers) as resp:
                                if resp.status != 200:
                                    continue
                                dados = await resp.json()
                                player_data = dados.get("player", dados)
                                clan_info = player_data.get("clanInfo") or {}
                                clan_id = str(clan_info.get("clanId", ""))
                                member = guild.get_member(int(m["id_discord"]))
                                nick = basic_info.get("nickname", "Desconhecido") if isinstance(dados, dict) else "Desconhecido"
                                log_sart(f"🔎 Verificação automática - UID {uid} ({nick}): clanId={clan_id}, guilda_config={guilda_ff_id}")
                                if clan_id and clan_id != guilda_ff_id:
                                    if member and cargo and cargo in member.roles:
                                        try:
                                            await member.remove_roles(cargo)
                                            removidos.append(member.display_name)
                                            log_sart(f"❌ Verificação automática - REMOVIDO: {nick} (clan {clan_id})")
                                        except discord.Forbidden:
                                            pass
                                    supabase.table("membros_verificados").delete().eq("id_discord", str(m["id_discord"])).eq("id_servidor", guild_id).execute()
                        except Exception:
                            pass

                    if removidos:
                        canal_id = cfg.data[0].get("canal_verificacao_id")
                        canal = guild.get_channel(int(canal_id)) if canal_id and str(canal_id).isdigit() else None
                        texto = "\n".join(f"• {nome}" for nome in removidos)
                        embed = discord.Embed(title="🔄 Verificação Automática", description=f"Removidos **{len(removidos)}** cargos de registro por saída da guilda:\n{texto}", color=discord.Color.from_rgb(255, 50, 50))
                        if canal:
                            try:
                                await canal.send(embed=embed)
                            except Exception:
                                pass
                        log_sart(f"🔄 Verificação automática em {guild.name}: {len(removidos)} removidos.")
        except Exception as e:
            log_sart(f"🚨 Erro na verificação automática: {e}")
        await asyncio.sleep(60)
