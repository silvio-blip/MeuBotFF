# cogs/ajuda.py
import discord
from discord import app_commands
from discord.ext import commands

PAGINAS = {
    "inicio": ("🏠 Início", discord.Color.from_rgb(255, 50, 50),
        "Bem-vindo ao **S.art Engine**, o bot definitivo para gestão de guildas Free Fire!\n\n"
        "**📋 Categorias:**\n"
        "1️⃣ Verificação · 2️⃣ Perfil · 3️⃣ Gestão · 4️⃣ Torneios\n"
        "5️⃣ Ranking · 6️⃣ Warns · 7️⃣ Boas-Vindas\n"
        "8️⃣ Anti-Raid · 9️⃣ Notificações · 🔟 Admin"),

    "verificacao": ("1️⃣ Verificação", discord.Color.from_rgb(0, 255, 128),
        "Garante que apenas membros da tua guilda FF entram no servidor.\n\n"
        "**`/entrar`** — Inicia verificação\n"
        "• Envia teu ID do Free Fire\n"
        "• Verifica se pertences à guilda\n"
        "• Muda idioma no perfil FF\n"
        "• Tens 5 minutos\n"
        "• Recebes cargo automaticamente\n\n"
        "**`/desvincular`** — Remove teu registo"),

    "perfil": ("2️⃣ Perfil", discord.Color.from_rgb(100, 150, 255),
        "Dados completos de qualquer jogador verificado.\n\n"
        "**`/perfil`** — Teu perfil\n"
        "**`/perfil @membro`** — Perfil de outro\n\n"
        "Dados: Nick, UID, Guilda, Nível, Likes, Patente BR/CS, Veterano, Data criação"),

    "gestao": ("3️⃣ Gestão", discord.Color.from_rgb(255, 165, 0),
        "Ferramentas de moderação (requer cargo de gestão).\n\n"
        "**`/dar_cargo @membro cargo`**\n"
        "**`/remover_cargo @membro cargo`**\n"
        "**`/limpar quantidade`** — Até 100 msgs\n"
        "**`/limpar_membro @membro qtd`**\n"
        "**`/gestao_info`** — Info dos comandos"),

    "torneios": ("4️⃣ Torneios", discord.Color.from_rgb(255, 215, 0),
        "Torneios com equipas: Solo, Duo, Trio ou Squad.\n\n"
        "**Admin:**\n"
        "`/torneio_criar` — Criar torneio (escolhe o modo)\n"
        "`/torneio_iniciar id` — Iniciar (verifica aprovações)\n"
        "`/torneio_resultado id @venc` — Registar vencedor\n"
        "`/torneio_finalizar id` — Encerrar\n\n"
        "**Membros:**\n"
        "`/torneio_equipa_criar id nome @m1 @m2...` — Criar equipa\n"
        "`/torneio_equipa_ver id` — Ver equipas inscritas\n\n"
        "**Como funciona:**\n"
        "1. Admin cria torneio com modo (Duo, Squad, etc)\n"
        "2. Capitão cria equipa com os membros\n"
        "3. Cada membro recebe DM com botão Aprovar/Rejeitar\n"
        "4. Ao iniciar, equipas não aprovadas são eliminadas\n"
        "5. Brackets gerados automaticamente com fases"),

    "ranking": ("5️⃣ Ranking", discord.Color.from_rgb(255, 215, 0),
        "Ranking por pontos Battle Royale em tempo real.\n\n"
        "**`/ranking_guilda`** — Top 10\n"
        "**`/meu_ranking`** — Tua posição\n"
        "**`/atualizar_ranking`** — Força update (admin)"),

    "warns": ("6️⃣ Warns", discord.Color.from_rgb(255, 100, 100),
        "Configurável pelo admin via `/painel`.\n\n"
        "**`/dar_warn @membro`** — Adverte\n"
        "**`/remover_warn @membro id`** — Remove\n"
        "**`/lista_warns @membro`** — Lista\n\n"
        "Limite: 3 strikes = ban (configurável)\n"
        "Expiração: 30 dias (configurável)"),

    "boas_vindas": ("7️⃣ Boas-Vindas", discord.Color.from_rgb(0, 200, 255),
        "Embed automática ao entrar no servidor.\n"
        "Configura via `/painel` → Boas-Vindas.\n\n"
        "Opções: Título, descrição ({user}, {membros}), cor, canal, toggle"),

    "anti_raid": ("8️⃣ Anti-Raid", discord.Color.from_rgb(255, 50, 50),
        "Proteção contra joins em massa.\n"
        "Configura via `/painel` → Anti-Raid.\n\n"
        "Rate limit + auto-lock contra spam de joins"),

    "notificacoes": ("9️⃣ Notificações", discord.Color.from_rgb(150, 100, 255),
        "Alertas automáticos sobre o Free Fire.\n"
        "Configura via `/painel` → Notificações.\n\n"
        "**`/verificar_membros`** — Verifica guilda FF\n\n"
        "Tipos: Membros que saíram, Atualizações, Temporada"),

    "admin": ("🔟 Admin", discord.Color.from_rgb(43, 45, 49),
        "Apenas dono do servidor.\n\n"
        "**`/configurar`** — Registra servidor\n"
        "**`/painel`** — Painel completo para configurar TUDO\n\n"
        "No painel podes configurar:\n"
        "Guilda, Cargo, Canal, Warns, Boas-Vindas, Anti-Raid, Notificações"),
}

ORDEM = list(PAGINAS.keys())

def build_ajuda(pagina_key):
    titulo, cor, texto = PAGINAS[pagina_key]
    idx = ORDEM.index(pagina_key)
    embed = discord.Embed(title=titulo, description=texto, color=cor)
    embed.set_footer(text=f"Página {idx+1}/{len(ORDEM)} — Usa os botões ou o menu")
    return embed, AjudaView(pagina_key)


class AjudaView(discord.ui.View):
    def __init__(self, pagina="inicio"):
        super().__init__(timeout=300)
        self.pagina = pagina

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="ajuda_prev")
    async def btn_prev(self, interaction, button):
        idx = ORDEM.index(self.pagina)
        self.pagina = ORDEM[(idx - 1) % len(ORDEM)]
        embed, view = build_ajuda(self.pagina)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🏠", style=discord.ButtonStyle.primary, custom_id="ajuda_home")
    async def btn_home(self, interaction, button):
        self.pagina = "inicio"
        embed, view = build_ajuda("inicio")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="ajuda_next")
    async def btn_next(self, interaction, button):
        idx = ORDEM.index(self.pagina)
        self.pagina = ORDEM[(idx + 1) % len(ORDEM)]
        embed, view = build_ajuda(self.pagina)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.select(
        placeholder="Navegar...",
        options=[discord.SelectOption(label=v[0], value=k) for k, v in PAGINAS.items()],
        custom_id="ajuda_select"
    )
    async def select_pagina(self, interaction, select):
        self.pagina = select.values[0]
        embed, view = build_ajuda(self.pagina)
        await interaction.response.edit_message(embed=embed, view=view)


class Ajuda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ajuda", description="Guia completo de como usar o bot")
    async def ajuda(self, interaction):
        embed, view = build_ajuda("inicio")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ajuda(bot))
