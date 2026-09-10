# cogs/palavroes.py
import re
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from database import supabase
from utils import verificar_permissao_gestao

PALAVRAS_PROIBIDAS = [
    "porra", "caralho", "cabra", "foda", "fodido", "fodete", "foder",
    "puta", "puto", "travesti", "vagabundo", "vagabunda",
    "tomar no cu", "te foder",
    "filho da puta", "filha da puta", "sua puta", "sua caralho", "teu merda",
    "sua merda", "mierda", "merda", "puta que pariu",
    "otário", "otaria", "boceta", "buceta", "bucetinha",
    "xota", "xote", "boiola", "viado", "viada",
    "pau no pinto", "pau no saco", "pau na sopa",
    "foda-se", "fodase", "fds",
    "cagão", "cagao", "cagar", "cagou",
    "piroca", "pirote", "piralejo",
    "escort", "escorts", "prostituta", "prostituto",
    "parilha", "parilhas", "cabreado", "chateado",
    "corno", "corna", "cornudo", "cornuda",
    "dedo no cu", "macaco velho", "babaca",
    "fdp", "f.d.p", "filho da poha", "filha da poha",
    "fudido", "fudida", "pqra", "máfia", "mafia",
    "vai tomar", "vete", "vaza", "porcaria",
]

EXCECOES = {
    "formigueiro", "formiga", "formigas", "formigueira",
    "merdah", "cachoeira", "bacana", "bacanas",
}

LEET_MAP = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '7': 't', '@': 'a', '$': 's', '!': 'i',
    '8': 'b', '2': 'z', '6': 'g', '9': 'g',
})

_COMPILED_PATTERNS = []


def _compile_patterns():
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS:
        return
    patterns = []
    for palavra in PALAVRAS_PROIBIDAS:
        norm = re.sub(r'[^a-z\s]', '', palavra.lower())
        if len(norm) < 3:
            continue
        patterns.append(re.compile(
            re.escape(norm).replace(r'\ ', r'\W*'),
            re.IGNORECASE
        ))
    _COMPILED_PATTERNS = patterns


def contains_profanity(text, custom_words=None):
    _compile_patterns()
    if not text:
        return False, None
    normalized = text.lower().translate(LEET_MAP)
    normalized = re.sub(r'[^a-z\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return True, match.group()
    if custom_words:
        for palavra in custom_words:
            norm = palavra.lower().strip()
            if len(norm) < 2:
                continue
            if re.search(r'\b' + re.escape(norm) + r'\b', normalized):
                return True, norm
    return False, None


def ler_config(guild_id):
    try:
        db = supabase.table("palavroes_config").select("*").eq("guilda_id", str(guild_id)).execute()
        return db.data[0] if db.data else {}
    except Exception:
        return {}


class Palavroes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._config_cache = {}

    def _get_config(self, guild_id):
        if guild_id not in self._config_cache:
            self._config_cache[guild_id] = ler_config(guild_id)
        return self._config_cache[guild_id]

    def _clear_cache(self, guild_id):
        self._config_cache.pop(guild_id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            if not message.guild:
                return

            guild_id = message.guild.id
            cfg = self._get_config(guild_id)
            if not cfg or not cfg.get("habilitado", False):
                return

            excluir_cargos = set(str(c) for c in cfg.get("excluir_cargos", []) or [])
            excluir_canais = set(str(c) for c in cfg.get("excluir_canais", []) or [])

            member = message.author
            if isinstance(member, discord.Member):
                if member.guild_permissions.administrator or member.id == message.guild.owner_id:
                    return
                member_role_ids = {str(r.id) for r in member.roles}
                if excluir_cargos & member_role_ids:
                    return

            if str(message.channel_id) in excluir_canais:
                return

            palavras_personalizadas = cfg.get("palavras_personalizadas", []) or []
            detected, palavra = contains_profanity(message.content, palavras_personalizadas)
            if not detected:
                return

            if cfg.get("deletar_mensagem", True):
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass

            duracao = cfg.get("duracao_timeout", 300)
            try:
                await member.timeout(
                    until=discord.utils.utcnow() + timedelta(seconds=duracao),
                    reason=f"Palavrão detectado: '{palavra}'"
                )
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"[PALAVROES] Não consegui timeout em {message.guild.name}: {e}")

            nome_membro = getattr(member, 'display_name', str(member))
            embed = discord.Embed(
                title="🚫 Conteúdo Inapropriado",
                description=(
                    f"**{nome_membro}** foi silenciado por usar linguagem imprópria.\n"
                    f"Duração: `{duracao}s`"
                ),
                color=discord.Color.red()
            )
            embed.add_field(name="⚠️ Palavra detectada", value=f"`{palavra}`", inline=False)
            embed.set_footer(text="Novo palavrão = timeout dobrado.")

            if cfg.get("aviso_canal", False):
                try:
                    await message.channel.send(embed=embed, delete_after=15)
                except (discord.Forbidden, discord.HTTPException):
                    pass

            canal_alertas_id = cfg.get("canal_alertas")
            if canal_alertas_id and str(canal_alertas_id).isdigit():
                canal_alertas = message.guild.get_channel(int(canal_alertas_id))
                if canal_alertas:
                    alerta = discord.Embed(
                        title="🚨 Palavrão Detectado",
                        description=(
                            f"**Membro:** {member.mention}\n"
                            f"**Canal:** {message.channel.mention}\n"
                            f"**Duração:** `{duracao}s`\n"
                            f"**Conteúdo:** {message.content[:200]}"
                        ),
                        color=discord.Color.dark_red(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    try:
                        await canal_alertas.send(embed=alerta)
                    except (discord.Forbidden, discord.HTTPException):
                        pass

            print(f"[PALAVROES] {nome_membro} ({member.id}) timeout por '{palavra}' em {message.guild.name}")
        except Exception as e:
            print(f"[PALAVROES] Erro no on_message: {e}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self._clear_cache(guild.id)

    # --- COMANDOS (/) ---

    @app_commands.command(name="desmutar", description="Remove o timeout de um membro (Cargo Gestão)")
    @app_commands.describe(membro="O membro a desmutar")
    async def desmutar_cmd(self, interaction: discord.Interaction, membro: discord.Member):
        await interaction.response.defer(ephemeral=True)

        is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
        is_gestao = await verificar_permissao_gestao(interaction, supabase)
        if not is_admin and not is_gestao:
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores podem usar este comando.", ephemeral=True)

        if not membro.is_timed_out():
            return await interaction.followup.send(f"✅ **{membro.display_name}** não está silenciado.", ephemeral=True)

        try:
            await membro.timeout(until=None, reason=f"Timeout removido por {interaction.user.display_name}")
            embed = discord.Embed(
                title="🔓 Timeout Removido",
                description=f"**{membro.mention}** teve o silenciamento removido por {interaction.user.mention}.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            print(f"[PALAVROES] {interaction.user.display_name} removeu timeout de {membro.display_name} em {interaction.guild.name}")
        except discord.Forbidden:
            await interaction.followup.send("❌ Não tenho permissão para remover o timeout.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Erro ao remover timeout: {e}", ephemeral=True)

    @app_commands.command(name="add-palavra", description="Adiciona uma palavra à lista de palavrões (Cargo Gestão)")
    @app_commands.describe(palavra="A palavra a adicionar")
    async def add_palavra_cmd(self, interaction: discord.Interaction, palavra: str):
        await interaction.response.defer(ephemeral=True)

        is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
        is_gestao = await verificar_permissao_gestao(interaction, supabase)
        if not is_admin and not is_gestao:
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores podem usar este comando.", ephemeral=True)

        palavra = palavra.strip().lower()
        if len(palavra) < 2:
            return await interaction.followup.send("❌ A palavra precisa ter pelo menos 2 caracteres.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        cfg = ler_config(guild_id)
        palavras = cfg.get("palavras_personalizadas", []) or []

        if palavra in palavras:
            return await interaction.followup.send(f"⚠️ **{palavra}** já está na lista de palavrões.", ephemeral=True)

        palavras.append(palavra)
        try:
            supabase.table("palavroes_config").upsert({
                "guilda_id": guild_id,
                "palavras_personalizadas": palavras,
                "habilitado": True
            }).execute()
        except Exception as e:
            print(f"[PALAVROES] Erro ao salvar: {e}")
            return await interaction.followup.send(
                f"❌ Erro no banco de dados. Contacta um administrador.\nDetalhe: {str(e)[:200]}", ephemeral=True
            )
        self._clear_cache(guild_id)

        embed = discord.Embed(
            title="✅ Palavra Adicionada",
            description=f"**{palavra}** foi adicionada à lista de palavrões do servidor.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="remover-palavra", description="Remove uma palavra da lista de palavrões (Cargo Gestão)")
    @app_commands.describe(palavra="A palavra a remover")
    async def remover_palavra_cmd(self, interaction: discord.Interaction, palavra: str):
        await interaction.response.defer(ephemeral=True)

        is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
        is_gestao = await verificar_permissao_gestao(interaction, supabase)
        if not is_admin and not is_gestao:
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores podem usar este comando.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        cfg = ler_config(guild_id)
        palavras = cfg.get("palavras_personalizadas", []) or []

        if palavra not in palavras:
            return await interaction.followup.send(f"⚠️ **{palavra}** não está na lista de palavrões.", ephemeral=True)

        palavras.remove(palavra)
        try:
            supabase.table("palavroes_config").upsert({
                "guilda_id": guild_id,
                "palavras_personalizadas": palavras,
                "habilitado": True
            }).execute()
        except Exception as e:
            print(f"[PALAVROES] Erro ao remover: {e}")
            return await interaction.followup.send(
                f"❌ Erro no banco de dados. Contacta um administrador.\nDetalhe: {str(e)[:200]}", ephemeral=True
            )
        self._clear_cache(guild_id)

        embed = discord.Embed(
            title="✅ Palavra Removida",
            description=f"**{palavra}** foi removida da lista de palavrões.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    @remover_palavra_cmd.autocomplete("palavra")
    async def palavras_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = str(interaction.guild_id)
        cfg = ler_config(guild_id)
        palavras = cfg.get("palavras_personalizadas", []) or []
        return [
            app_commands.Choice(name=p, value=p)
            for p in palavras
            if current.lower() in p.lower()
        ]

    @app_commands.command(name="listar-palavras", description="Lista as palavras customizadas de palavrões")
    async def listar_palavras_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        cfg = ler_config(guild_id)
        palavras = cfg.get("palavras_personalizadas", []) or []

        if not palavras:
            return await interaction.followup.send("📭 Nenhuma palavra customizada adicionada.", ephemeral=True)

        lista = "\n".join(f"• `{p}`" for p in palavras)
        embed = discord.Embed(
            title="📋 Palavras de Palavrões Customizadas",
            description=lista,
            color=discord.Color.gold()
        )
        await interaction.followup.send(embed=embed, ephemeral=False)


async def setup(bot):
    _compile_patterns()
    await bot.add_cog(Palavroes(bot))
