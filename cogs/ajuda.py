# cogs/ajuda.py
import discord
from discord import app_commands
from discord.ext import commands

PAGINAS = {
    "inicio": ("🏠 Início", discord.Color.from_rgb(255, 50, 50),
        "Bem-vindo ao **S.art Engine** — Bot completo para gestão de guildas Free Fire.\n\n"
        "**📋 Categorias disponíveis:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔐 **Verificação** — Entrada segura via ID FF\n"
        "👤 **Perfil** — Dados completos do jogador\n"
        "🛠️ **Gestão** — Moderação (cargo necessário)\n"
        "🏆 **Torneios** — Solo/Duo/Trio/Squad\n"
        "📊 **Ranking** — Top BR por pontos\n"
        "💰 **Economia** — Moedas, daily e transferências\n"
        "⚠️ **Warns** — Sistema de advertências\n"
        "👋 **Boas-Vindas** — Embed personalizada\n"
        "🛡️ **Anti-Raid** — Proteção contra joins\n"
        "🔔 **Notificações** — Alertas do FF\n"
        "🚫 **Palavrões** — Auto-timeout por linguagem imprópria\n"
        "🎨 **Embeds** — Cria embeds personalizados no servidor\n"
        "🎵 **Música** — Sistema DJ com bloqueio de canal\n"
        "⚙️ **Admin** — Configuração do servidor\n\n"
        "💡 *Seleciona uma categoria abaixo para ver detalhes, exemplos e como usar cada comando.*"),

    "verificacao": ("🔐 Verificação", discord.Color.from_rgb(0, 200, 128),
        "**Como funciona:**\n"
        "O bot verifica se tu pertences à guilda oficial do servidor antes de dar o cargo.\n\n"
        "**Passo a passo:**\n"
        "1. Usa `/entrar`\n"
        "2. Escolhe o teu gênero\n"
        "3. Insere idade + ID do Free Fire\n"
        "4. O bot verifica se estás na guilda correta\n"
        "5. Muda o **idioma da assinatura** no perfil FF para o que o bot pedir\n"
        "6. Tens **5 minutos** — o radar detecta a mudança\n"
        "7. ✅ Cargo entregue + dados salvos + DM com perfil\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/entrar`** — Inicia verificação\n"
        "• *Parâmetros:* nenhum (interativo via botões/modal)\n"
        "• *Exemplo:* `/entrar` → seleciona gênero → preenche idade/UID\n\n"
        "**`/desvincular`** — Remove teu registo e cargo\n"
        "• *Parâmetros:* nenhum\n"
        "• *Exemplo:* `/desvincular` → apaga teus dados do bot\n\n"
        "🔄 **Auto-desvinculo:** Se saíres do servidor, o bot **remove teus dados automaticamente** e avisa no canal de desvinculamento (configurável no `/painel`).\n\n"
        "⚠️ **Importante:**\n"
        "• Precisas ter guilda no FF\n"
        "• A guilda deve ser a **oficial do servidor**\n"
        "• Não feches DMs — recebes o cartão de perfil no final"),

    "perfil": ("👤 Perfil", discord.Color.from_rgb(80, 160, 255),
        "**Mostra dados completos sincronizados do FF.**\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/perfil`** — Teu próprio perfil\n"
        "• *Parâmetros:* nenhum\n\n"
        "**`/perfil @membro`** — Perfil de outro jogador verificado\n"
        "• *Parâmetro:* `membro` (obrigatório)\n"
        "• *Exemplo:* `/perfil @Silvanio`\n\n"
        "**Dados mostrados:**\n"
        "• Nick FF + UID\n"
        "• Guilda do jogo + nível + likes\n"
        "• Patente BR (pontos) + CS (pontos + stats)\n"
        "• Status de veterano (tempo de conta FF)\n"
        "• Avatar FF + datas de criação (Discord + FF)\n"
        "• Cargo principal + idade + gênero\n\n"
        "⚠️ **Apenas membros verificados** têm perfil."),

    "gestao": ("🛠️ Gestão", discord.Color.from_rgb(255, 165, 0),
        "**Ferramentas de moderação** — Requer cargo de gestão configurado no `/painel` ou permissão de Administrador.\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/dar_cargo @membro @cargo`**\n"
        "• Adiciona cargo ao membro\n"
        "• *Exemplo:* `/dar_cargo @User @Membro`\n\n"
        "**`/remover_cargo @membro @cargo`**\n"
        "• Remove cargo do membro\n"
        "• *Exemplo:* `/remover_cargo @User @Membro`\n\n"
        "**`/limpar <quantidade>`**\n"
        "• Apaga mensagens recentes (1-100)\n"
        "• *Exemplo:* `/limpar 50`\n\n"
        "**`/limpar_membro @membro <quantidade>`**\n"
        "• Apaga só mensagens de um usuário (1-100)\n"
        "• *Exemplo:* `/limpar_membro @User 20`\n\n"
        "**`/gestao_info`** — Mostra cargo de gestão atual\n\n"
        "⚠️ **Regras:**\n"
        "• Não podes mexer em cargos ≥ teu topo\n"
        "• Bot precisa ter permissão + cargo acima do alvo"),

    "torneios": ("🏆 Torneios", discord.Color.from_rgb(255, 215, 0),
        "**Sistema completo de torneios com equipas.**\nModos: **Solo • Duo • Trio • Squad**\n\n"
        "**Fluxo completo:**\n"
        "1. Admin: `/torneio_criar` → escolhe modo + detalhes\n"
        "2. Capitães: `/torneio_equipa_criar` → forma equipa\n"
        "3. Cada membro recebe **DM com botão Aprovar/Rejeitar**\n"
        "4. Admin: `/torneio_iniciar` → elimina não aprovados + gera brackets\n"
        "5. Jogo rola → Admin: `/torneio_resultado` por partida\n"
        "6. Final: `/torneio_finalizar` → DM ao campeão + anúncio + limpeza\n\n"
        "**Comandos Admin:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/torneio_criar`** — Modal: nome, modo, descrição, data, prêmios\n"
        "**`/torneio_iniciar <id>`** — Inicia, verifica aprovações\n"
        "**`/torneio_resultado <id> @vencedor`** — Regista vencedor da partida\n"
        "**`/torneio_finalizar <id>`** — Encerra + anuncia campeão\n"
        "**`/torneio_lista`** — Lista torneios do servidor\n\n"
        "**Comandos Membros:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/torneio_equipa_criar <id> <nome> @m1 @m2...`** — Cria equipa\n"
        "**`/torneio_equipa_ver <id>`** — Vê equipas inscritas\n"
        "**`/torneio_bracket <id>`** — Vê árvore do torneio"),

    "ranking": ("📊 Ranking", discord.Color.from_rgb(100, 200, 255),
        "**Ranking por pontos Battle Royale** — Atualizado via API.\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/ranking_guilda`** — Top 10 da guilda\n"
        "• Mostra: posição, nick, pontos BR, patente\n\n"
        "**`/meu_ranking`** — Tua posição exata\n"
        "• Mostra: tua posição, pontos, diferença pro próximo\n\n"
        "**`/atualizar_ranking`** — Força sincronização (admin)\n"
        "• Busca pontos atuais de todos os verificados\n\n"
        "💡 O ranking atualiza automaticamente em background."),

    "economia": ("💰 Economia", discord.Color.from_rgb(255, 215, 0),
        "**Sistema de moedas do servidor** — Configura no `/painel` → Economia.\n\n"
        "**Como funciona:**\n"
        "• Recebes moedas por verificar-te no servidor (`/entrar`)\n"
        "• Ganhas moedas diariamente com `/daily`\n"
        "• Podes enviar e pedir moedas a outros membros\n"
        "• Admin dá/remove moedas via comandos de gestão\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/saldo`** — Mostra o teu saldo\n"
        "• *Parâmetros:* nenhum\n\n"
        "**`/topmoedas`** — Top 10 membros mais ricos\n"
        "• *Parâmetros:* nenhum\n\n"
        "**`/daily`** — Reclama moedas diárias (5-15 por defeito)\n"
        "• 1x por dia por servidor\n\n"
        "**`/pagar @membro <quantidade>`** — Envia moedas\n"
        "• *Exemplo:* `/pagar @User 50`\n\n"
        "**`/transferir`** — Alias de `/pagar`\n\n"
        "**`/pedir_moedas @membro <quantidade>`** — Pede moedas\n"
        "• Envia DM para o destino aprovar/recusar\n"
        "• *Exemplo:* `/pedir_moedas @User 25`\n\n"
        "**Comandos de Gestão:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/add-moedas @membro <quantidade>`** — Adiciona moedas\n"
        "**`/remove-moedas @membro <quantidade>`** — Remove moedas\n"
        "**`/dar-moedas-massa <quantidade> todos`** — Distribui a todos\n\n"
        "**Configuração no `/painel` → Economia:**\n"
        "• Moedas por verificação (`/entrar`)\n"
        "• Moedas por convite (entrada de novos membros)\n"
        "• Moedas por torneio (participar/vencer)\n"
        "• Daily min/max e limite diário\n"
        "• Nome personalizado da moeda\n"
        "• Ligar/Desligar sistema"),

    "warns": ("⚠️ Warns", discord.Color.from_rgb(255, 80, 80),
        "**Sistema de advertências configurável** — Tudo via `/painel`.\n\n"
        "**Como funciona:**\n"
        "• Admin dá warn → membro acumula strikes\n"
        "• No limite → **ban automático**\n"
        "• Warns expiram após X dias (configurável)\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/dar_warn @membro <motivo>`** — Adiciona warn\n"
        "• *Exemplo:* `/dar_warn @User Flood no chat`\n\n"
        "**`/remover_warn @membro <id_warn>`** — Remove warn específico\n"
        "• Usa ID mostrado em `/lista_warns`\n\n"
        "**`/lista_warns @membro`** — Lista warns ativos\n"
        "• Mostra: ID, motivo, data, quem deu\n\n"
        "**Configuração no `/painel` → Warns:**\n"
        "• Limite de warns (padrão: 3 = ban)\n"
        "• Dias para expirar (padrão: 30)\n"
        "• Canal de notificações\n"
        "• Ligar/Desligar sistema"),

    "boas_vindas": ("👋 Boas-Vindas", discord.Color.from_rgb(0, 200, 255),
        "**Embed automática** quando novo membro entra.\n\n"
        "**Configuração no `/painel` → Boas-Vindas:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✏️ **Personalizar** — Título, descrição, cor (hex)\n"
        "📢 **Canal** — Onde enviar\n"
        "🔄 **Toggle** — Ligar/Desligar\n\n"
        "**Variáveis disponíveis:**\n"
        "• `{user}` — Menção do membro\n"
        "• `{membros}` — Total de membros do servidor\n"
        "• `{servidor}` — Nome do servidor\n\n"
        "**Exemplo descrição:**\n"
        "`Olá {user}! Bem-vindo ao {servidor}.\nSomos agora {membros} membros!`"),

    "anti_raid": ("🛡️ Anti-Raid", discord.Color.from_rgb(255, 50, 80),
        "**Proteção contra ataques de join em massa.**\n\n"
        "**Como funciona:**\n"
        "• Monitora joins por minuto\n"
        "• Se passar do limite → **lockdown automático**\n"
        "• Bloqueia @everyone de enviar mensagens\n"
        "• Dura X minutos (configurável)\n\n"
        "**Configuração no `/painel` → Anti-Raid:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ **Limites** — Joins/min + duração do lock\n"
        "🚨 **Canal alertas** — Onde avisar\n"
        "🔄 **Toggle** — Ativar/Desativar\n\n"
        "⚠️ Requer permissão `Gerenciar Cargos` + `Gerenciar Canais` no bot."),

    "notificacoes": ("🔔 Notificações", discord.Color.from_rgb(160, 100, 255),
        "**Alertas automáticos do Free Fire** — Configura no `/painel`.\n\n"
        "**Tipos de notificação:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔄 **Atualizações** — Novas versões/patches do FF\n"
        "👤 **Membros** — Alguém saiu da guilda FF\n"
        "🚪 **Saída Usuário** — Membro saiu do servidor Discord\n"
        "🔗 **Desvinculamento** — Membro usou `/desvincular`\n"
        "📅 **Temporada** — Mudança de rank/season\n\n"
        "**Comando extra:**\n"
        "**`/verificar_membros`** — Verificação manual agora\n"
        "• Checa todos os verificados vs guilda FF\n"
        "• Remove cargo de quem saiu\n\n"
        "**Configuração no `/painel` → Notificações:**\n"
        "Canal para cada tipo + toggle geral"),

    "admin": ("⚙️ Admin / Configuração", discord.Color.from_rgb(43, 45, 49),
        "**Apenas Dono / Administrador / Cargo de Gestão.**\n\n"
        "**Comandos principais:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/configurar @cargo_membros #canal_logs`**\n"
        "• Registo inicial do servidor\n"
        "• Define cargo de verificado + canal de logs\n"
        "• Abre modal: nome, email, ID guilda FF\n\n"
        "**`/painel`** — Painel visual completo (recomendado)\n"
        "• Menu dropdown para navegar categorias\n"
        "• Botões para alterar cada setting\n"
        "• Toggles ON/OFF por sistema\n\n"
        "**`/remover_servidor`** — **APAGA TUDO** do Supabase\n"
        "• Membros, warns, torneios, configs, tudo\n"
        "• **Irreversível** — usa com cuidado\n\n"
        "**O que configuras no painel:**\n"
        "• Guilda FF + Cargo verificado + Canal logs\n"
        "• Cargo de Gestão (quem usa comandos mod)\n"
        "• Warns, Boas-Vindas, Anti-Raid, Notificações\n"
        "• Verificação Automática (diária)"),

    "musica": ("🎵 Música", discord.Color.from_rgb(255, 50, 80),
        "**Sistema de música com DJ e bloqueio de canal.**\n\n"
        "**Como funciona:**\n"
        "• O admin define um **canal de texto** onde os comandos de música funcionam\n"
        "• Quem toca a primeira música vira o **DJ/Líder**\n"
        "• Se o DJ sai mas há gente no VC, a liderança passa para outro\n"
        "• Um **cargo de música** pode controlar a qualquer momento, mesmo se não for DJ\n"
        "• Se ninguém está no VC, o bot desconecta automaticamente\n\n"
        "**Fluxo de uso:**\n"
        "1. Admin: `/painel` → Música → Definir Canal + Cargo DJ\n"
        "2. Qualquer um: `/play` ou `/add_fila` com o nome/link\n"
        "3. DJ controla: `/pular`, `/pause`, `/resume`, `/volume`\n"
        "4. Info: `/np` (agora a tocar), `/fila` (próximas)\n"
        "5. DJ: `/stop` ou `/disconnect` para parar\n\n"
        "**Comandos:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**`/play`** — Toca uma música (troca a atual)\n"
        "**`/add_fila`** — Adiciona à fila sem parar\n"
        "**`/funk`** — Toca funks em loop automático (um após o outro)\n"
        "**`/pular`** — Para a atual, vai para a próxima\n"
        "**`/pause` / `/resume`** — Pausa / retoma\n"
        "**`/volume 0-100`** — Ajusta o volume\n"
        "**`/np`** — Mostra a música atual\n"
        "**`/fila`** — Lista a fila de músicas\n"
        "**`/loop`** — Repete a música atual\n"
        "**`/shuffle`** — Embaralha a fila\n"
        "**`/clear`** — Limpa a fila\n"
        "**`/stop` / `/disconnect`** — Para e desconecta o bot\n\n"
         "⚠️ **Permissões:**\n"
         "• Comandos só funcionam no canal de texto configurado\n"
         "• Controle (pular, stop, etc.) exige ser DJ ou ter o cargo de música\n"
         "• Dono/Admin sempre têm acesso"),

    "palavroes": ("🚫 Palavrões", discord.Color.from_rgb(255, 50, 50),
         "**Auto-moderação de linguagem imprópria** — Configura no `/painel` → Palavrões.\n\n"
         "**Como funciona:**\n"
         "• O bot escaneia todas as mensagens em texto\n"
         "• Se detectar palavrão → **timeout automático** + mensagem apagada\n"
         "• Dono/Admin e cargos isentos nunca levam timeout\n"
         "• Cargos e canais podem ser excluídos da verificação\n\n"
         "**Fluxo de uso:**\n"
         "1. Admin: `/painel` → Palavrões → Ligar/Desligar\n"
         "2. Configura duração do timeout (1s - 3600s)\n"
         "3. Define canal de alertas (onde o bot reporta)\n"
         "4. Seleciona cargos e canais isentos\n\n"
         "**Opções:**\n"
         "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
         "⏱️ **Timeout** — Duração do silenciamento (padrão: 300s = 5min)\n"
         "🗑️ **Deletar Mensagem** — Apaga a mensagem ofensiva (padrão: ON)\n"
         "📢 **Avisar no Canal** — Manda aviso no canal (padrão: OFF)\n"
         "🎖️ **Cargos Isentos** — Quem não leva timeout\n"
         "📵 **Canais Isentos** — Onde o filtro não ativa\n"
          "🔄 **Ligar/Desligar** — Ativa ou desativa o sistema\n\n"
          "**`/mutar @membro [duracao]`** — Silencia membro (padrão: 300s, Cargo Gestão)\n"
          "**`/desmutar @membro`** — Remove timeout (Cargo Gestão)\n"
          "**`/add-palavra <palavra>`** — Adiciona palavra customizada (Cargo Gestão)\n"
          "**`/remover-palavra`** — Remove palavra (autocomplete, Cargo Gestão)\n"
          "**`/listar-palavras`** — Lista palavras customizadas\n\n"
          "⚠️ **Importante:**\n"
          "• O timeout pode ser dobrado para reincidentes."),

    "embeds": ("🎨 Embed Builder", discord.Color.from_rgb(255, 215, 0),
          "**Construtor interativo de embeds personalizados** — Apenas Cargo Gestão e Admin.\n\n"
          "**Como funciona:**\n"
          "• Admin/Gestão usa `/embed-criar` → abre um painel interativo\n"
          "• Edita cada propriedade via botões → modais\n"
          "• Faz preview, envia para um canal ou salva para reutilizar\n\n"
          "**Propriedades editáveis:**\n"
          "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          "🏷️ **Título** — Texto do título\n"
          "📝 **Descrição** — Texto principal (multilinha)\n"
          "🎨 **Cor** — Hex (ex: FFD700)\n"
          "🖼️ **Thumbnail** — Imagem pequena (URL)\n"
          "🖼️ **Imagem** — Imagem grande (URL)\n"
          "🖼️ **Banner/Autor** — Ícone + nome do autor\n"
          "🔖 **Footer** — Texto + ícone\n"
          "📊 **Campos** — Nome/Valor/Inline (até 25)\n"
          "⏱️ **Timestamp** — Mostra data/hora\n\n"
          "**Comandos:**\n"
          "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          "**`/embed-criar`** — Abre o builder interativo\n"
          "**`/embed-listar`** — Lista embeds salvos\n"
          "**`/embed-enviar`** — Envia um embed salvo para um canal\n"
          "**`/embed-apagar`** — Remove um embed salvo\n\n"
          "**Dicas:**\n"
          "• Usa `/imagem` para fazer upload de imagens (ImgBB) e obter URLs\n"
          "• Os embeds salvos ficam disponíveis 24/7\n"
          "• O builder expira após 5 minutos de inatividade"),
}

ORDEM = list(PAGINAS.keys())

def build_ajuda(pagina_key):
    titulo, cor, texto = PAGINAS[pagina_key]
    idx = ORDEM.index(pagina_key)
    embed = discord.Embed(title=titulo, description=texto, color=cor)
    embed.set_footer(text=f"Página {idx+1}/{len(ORDEM)}  •  Usa os botões ◀ 🏠 ▶ ou o menu dropdown")
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
        placeholder="📚 Seleciona uma categoria...",
        options=[discord.SelectOption(label=v[0], value=k, emoji=v[0][0]) for k, v in PAGINAS.items()],
        custom_id="ajuda_select"
    )
    async def select_pagina(self, interaction, select):
        self.pagina = select.values[0]
        embed, view = build_ajuda(self.pagina)
        await interaction.response.edit_message(embed=embed, view=view)


class Ajuda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ajuda", description="Guia completo com exemplos de todos os comandos")
    async def ajuda(self, interaction):
        embed, view = build_ajuda("inicio")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ajuda(bot))