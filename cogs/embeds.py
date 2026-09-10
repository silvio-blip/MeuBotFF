# cogs/embeds.py
import re
import json
import uuid
import discord
from discord import app_commands
from discord.ext import commands
import config
from datetime import datetime, timezone
from database import supabase


def log_sart(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 [Embed] {msg}")


def ler_config(guild_id):
    try:
        db = supabase.table("embeds_config").select("*").eq("guilda_id", str(guild_id)).execute()
        return db.data[0] if db.data else {}
    except Exception:
        return {}


def gerar_embed_id():
    return str(uuid.uuid4()).replace("-", "")[:16]


def validar_cor(hex_str):
    if not hex_str:
        return True
    hex_str = hex_str.lstrip("#")
    if not re.match(r'^[0-9A-Fa-f]{6}$', hex_str):
        return False
    return True


async def upload_attachment_to_imgbb(attachment: discord.Attachment) -> str:
    from cogs.imagem import upload_to_imgbb
    image_bytes = await attachment.read()
    result = await upload_to_imgbb(image_bytes, config.IMGBB_API_KEY)
    return result["data"]["url"]


def build_embed(data: dict) -> discord.Embed:
    cor = data.get("cor", "FFD700")
    try:
        color = discord.Color(int(cor, 16)) if validar_cor(cor) else discord.Color.gold()
    except (ValueError, TypeError):
        color = discord.Color.gold()

    titulo = data.get("titulo") or None
    descricao = data.get("descricao") or None
    campos = data.get("campos", []) or []

    has_content = (titulo or descricao or campos
                   or data.get("autor_nome") or data.get("footer_text")
                   or data.get("thumbnail_url") or data.get("imagem_url")
                   or data.get("banner_url") or data.get("autor_icon")
                   or data.get("footer_icon"))
    if not has_content:
        descricao = "📝 **Editor de embeds ativo.** Edita os campos com os botões abaixo."

    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=color
    )

    if data.get("thumbnail_url"):
        embed.set_thumbnail(url=data["thumbnail_url"])
    if data.get("imagem_url"):
        embed.set_image(url=data["imagem_url"])
    if data.get("banner_url"):
        embed.set_author(name=data.get("autor_nome") or "\n", icon_url=data.get("autor_icon"))
    else:
        if data.get("autor_nome"):
            embed.set_author(name=data["autor_nome"], icon_url=data.get("autor_icon") or None)

    if data.get("footer_text"):
        embed.set_footer(text=data["footer_text"], icon_url=data.get("footer_icon") or None)

    for campo in data.get("campos", []):
        try:
            embed.add_field(
                name=campo.get("nome", "Sem nome")[:256],
                value=campo.get("valor", "Sem valor")[:1024],
                inline=campo.get("inline", False)
            )
        except Exception:
            pass

    if data.get("timestamp"):
        embed.timestamp = datetime.now(timezone.utc)

    return embed


class ModalEmbedTexto(discord.ui.Modal, title='Editar Campo de Texto'):
    def __init__(self, campo: str, titulo: str, valor_atual: str = "", *, placeholder: str = "", style: discord.TextStyle = discord.TextStyle.short):
        super().__init__(title=titulo, timeout=300)
        self.campo = campo
        self.input = discord.ui.TextInput(
            label=campo.capitalize(),
            placeholder=placeholder,
            default=valor_atual,
            required=False,
            style=style
        )
        self.add_item(self.input)
        self._builder_view = None

    def set_builder(self, view):
        self._builder_view = view

    async def on_submit(self, interaction: discord.Interaction):
        if self._builder_view:
            self._builder_view.embed_data[self.campo] = self.input.value
            log_sart(f"Atualizado: {self.campo}")
        await interaction.response.edit_message(
            content=f"✅ **{self.campo.capitalize()}** atualizado.",
            embed=build_embed(self._builder_view.embed_data) if self._builder_view else None,
            view=self._builder_view if self._builder_view else None
        )


class ModalEmbedCor(discord.ui.Modal, title='🎨 Escolher Cor do Embed'):
    cor = discord.ui.TextInput(label='Cor (hex)', placeholder='Ex: FFD700', default="FFD700", required=True)

    def __init__(self, builder_view):
        super().__init__(timeout=300)
        self._builder_view = builder_view

    async def on_submit(self, interaction: discord.Interaction):
        valor = self.cor.value.strip().lstrip("#")
        if not validar_cor(valor):
            return await interaction.response.send_message("❌ Cor inválida! Usa formato hex (ex: FFD700).", ephemeral=True)
        self._builder_view.embed_data["cor"] = valor
        await interaction.response.edit_message(
            content="✅ **Cor** atualizada.",
            embed=build_embed(self._builder_view.embed_data),
            view=self._builder_view
        )


class ModalEmbedURL(discord.ui.Modal, title='🔗 URL da Imagem'):
    url = discord.ui.TextInput(label='URL da imagem', placeholder='https://exemplo.com/imagem.png', required=False)

    def __init__(self, campo: str, titulo: str, builder_view):
        super().__init__(title=titulo, timeout=300)
        self.campo = campo
        self._builder_view = builder_view
        self._builder_view.embed_data.setdefault(campo, "")
        self.url.default = self._builder_view.embed_data.get(campo, "")

    async def on_submit(self, interaction: discord.Interaction):
        url = self.url.value.strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            return await interaction.response.send_message("❌ URL inválida! Deve começar com http:// ou https://", ephemeral=True)
        self._builder_view.embed_data[self.campo] = url or None
        await interaction.response.edit_message(
            content=f"✅ **{self.campo.replace('_url', '').capitalize()}** atualizado.",
            embed=build_embed(self._builder_view.embed_data),
            view=self._builder_view
        )


class ModalEmbedAutor(discord.ui.Modal, title='👤 Configurar Autor'):
    nome = discord.ui.TextInput(label='Nome do Autor', placeholder='Ex: S.art Engine', required=True)
    icon_url = discord.ui.TextInput(label='URL do Ícone (opcional)', placeholder='https://...', required=False)

    def __init__(self, builder_view):
        super().__init__(timeout=300)
        self._builder_view = builder_view
        self.nome.default = builder_view.embed_data.get("autor_nome", "") or ""
        self.icon_url.default = builder_view.embed_data.get("autor_icon", "") or ""

    async def on_submit(self, interaction: discord.Interaction):
        self._builder_view.embed_data["autor_nome"] = self.nome.value.strip() or None
        icon = self.icon_url.value.strip()
        if icon and not icon.startswith(("http://", "https://")):
            return await interaction.response.send_message("❌ URL do ícone inválida!", ephemeral=True)
        self._builder_view.embed_data["autor_icon"] = icon or None
        await interaction.response.edit_message(
            content="✅ **Autor** atualizado.",
            embed=build_embed(self._builder_view.embed_data),
            view=self._builder_view
        )


class ModalEmbedFooter(discord.ui.Modal, title='🔖 Configurar Footer'):
    texto = discord.ui.TextInput(label='Texto do footer', placeholder='Ex: S.art Engine', required=True)
    icon_url = discord.ui.TextInput(label='URL do Ícone (opcional)', placeholder='https://...', required=False)

    def __init__(self, builder_view):
        super().__init__(timeout=300)
        self._builder_view = builder_view
        self.texto.default = builder_view.embed_data.get("footer_text", "") or ""
        self.icon_url.default = builder_view.embed_data.get("footer_icon", "") or ""

    async def on_submit(self, interaction: discord.Interaction):
        self._builder_view.embed_data["footer_text"] = self.texto.value.strip() or None
        icon = self.icon_url.value.strip()
        if icon and not icon.startswith(("http://", "https://")):
            return await interaction.response.send_message("❌ URL do ícone inválida!", ephemeral=True)
        self._builder_view.embed_data["footer_icon"] = icon or None
        await interaction.response.edit_message(
            content="✅ **Footer** atualizado.",
            embed=build_embed(self._builder_view.embed_data),
            view=self._builder_view
        )


class ModalCampo(discord.ui.Modal, title='📊 Campo do Embed'):
    nome = discord.ui.TextInput(label='Nome do campo', placeholder='Ex: Informação', required=True)
    valor = discord.ui.TextInput(label='Valor do campo', placeholder='Ex: Detalhes aqui', required=True, style=discord.TextStyle.paragraph)
    inline = discord.ui.TextInput(label='Inline? (true/false)', placeholder='Ex: false', default="false", required=True)

    def __init__(self, field_manager_view, builder_view, indice=None):
        super().__init__(timeout=300)
        self._fm_view = field_manager_view
        self._builder_view = builder_view
        self._indice = indice
        campos = builder_view.embed_data.get("campos", [])
        if indice is not None and indice < len(campos):
            campo = campos[indice]
            self.nome.default = campo.get("nome", "")
            self.valor.default = campo.get("valor", "")
            self.inline.default = str(campo.get("inline", False)).lower()

    async def on_submit(self, interaction: discord.Interaction):
        inline = self.inline.value.strip().lower() in ("true", "1", "yes", "sim")
        novo_campo = {
            "nome": self.nome.value.strip()[:256],
            "valor": self.valor.value.strip()[:1024],
            "inline": inline
        }
        campos = self._builder_view.embed_data.get("campos", [])
        if self._indice is not None and self._indice < len(campos):
            campos[self._indice] = novo_campo
        else:
            campos.append(novo_campo)
        self._builder_view.embed_data["campos"] = campos
        self._fm_view._rebuild()
        await interaction.response.edit_message(
            content=f"📊 **Gerir Campos** ({len(campos)}/25)",
            embed=build_embed(self._builder_view.embed_data),
            view=self._fm_view
        )


class ModalNomeEmbed(discord.ui.Modal, title='💾 Salvar Embed'):
    nome = discord.ui.TextInput(label='Nome do embed', placeholder='Ex: Regra do Servidor', required=True)

    def __init__(self, builder_view, guild_id, bot):
        super().__init__(timeout=300)
        self._builder_view = builder_view
        self._guild_id = guild_id
        self._bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        nome = self.nome.value.strip()
        if not nome:
            return await interaction.response.send_message("❌ O nome é obrigatório.", ephemeral=True)
        embed_id = gerar_embed_id()
        campos_json = json.dumps(self._builder_view.embed_data.get("campos", []))
        dados = self._builder_view.embed_data
        try:
            supabase.table("embed_configs").insert({
                "guilda_id": self._guild_id,
                "embed_id": embed_id,
                "nome": nome,
                "titulo": dados.get("titulo"),
                "descricao": dados.get("descricao"),
                "cor": dados.get("cor", "FFD700"),
                "thumbnail_url": dados.get("thumbnail_url"),
                "imagem_url": dados.get("imagem_url"),
                "banner_url": dados.get("banner_url"),
                "autor_nome": dados.get("autor_nome"),
                "autor_icon": dados.get("autor_icon"),
                "footer_text": dados.get("footer_text"),
                "footer_icon": dados.get("footer_icon"),
                "campos": campos_json,
                "timestamp": dados.get("timestamp", False),
                "criado_por": str(interaction.user.id),
            }).execute()
        except Exception as e:
            log_sart(f"Erro ao salvar embed: {e}")
            return await interaction.response.send_message("❌ Erro ao salvar no banco de dados.", ephemeral=True)

        await interaction.response.send_message(
            f"✅ **Embed salvo como `{nome}`** (ID: `{embed_id}`)", ephemeral=True
        )
        log_sart(f"Embed '{nome}' salvo para guild {self._guild_id}")


class SendEmbedView(discord.ui.View):
    def __init__(self, bot, guild_id: str):
        super().__init__(timeout=300)
        self._bot = bot
        self._guild_id = guild_id
        self._embeds = []
        self._select: discord.ui.Select | None = None

    async def populate(self):
        try:
            db = supabase.table("embed_configs").select("embed_id, nome").eq("guilda_id", self._guild_id).execute()
        except Exception:
            self._embeds = []
            self._select = discord.ui.Select(placeholder="❌ Erro na base de dados", options=[], disabled=True)
            self.add_item(self._select)
            return
        self._embeds = db.data if db.data else []
        self._select = discord.ui.Select(
            placeholder="Selecione um embed...",
            options=[
                discord.SelectOption(label=e.get("nome", "Sem nome")[:100], value=str(e.get("embed_id")), description=f"ID: {e.get('embed_id')}")
                for e in self._embeds
            ] if self._embeds else []
        )
        self._select.callback = self._on_select_embed
        self.add_item(self._select)

    async def _on_select_embed(self, interaction: discord.Interaction):
        embed_id = self._select.values[0] if self._select.values else ""
        if not embed_id:
            await interaction.response.edit_message(content="⚠️ Nenhum embed selecionado.", view=self)
            return
        try:
            db = supabase.table("embed_configs").select("*").eq("guilda_id", self._guild_id).eq("embed_id", embed_id).execute()
        except Exception:
            await interaction.response.edit_message(content="❌ Erro na base de dados.", view=self)
            return
        if not db.data:
            await interaction.response.edit_message(content="❌ Embed não encontrado.", view=self)
            return
        dados = db.data[0]
        embed_data = {
            "titulo": dados.get("titulo"),
            "descricao": dados.get("descricao"),
            "cor": dados.get("cor", "FFD700"),
            "thumbnail_url": dados.get("thumbnail_url"),
            "imagem_url": dados.get("imagem_url"),
            "banner_url": dados.get("banner_url"),
            "autor_nome": dados.get("autor_nome"),
            "autor_icon": dados.get("autor_icon"),
            "footer_text": dados.get("footer_text"),
            "footer_icon": dados.get("footer_icon"),
            "campos": json.loads(dados.get("campos") or "[]"),
            "timestamp": dados.get("timestamp", False),
        }
        embed = build_embed(embed_data)
        guild = self._bot.get_guild(int(self._guild_id))
        channels = [c for c in guild.text_channels] if guild else []
        channel_select = discord.ui.Select(
            placeholder="Selecione o canal...",
            options=[
                discord.SelectOption(label=c.name[:100], value=str(c.id))
                for c in channels[:25]
            ]
        )
        async def send_callback(interaction2: discord.Interaction):
            channel_id = channel_select.values[0] if channel_select.values else ""
            if not channel_id:
                await interaction2.response.send_message("⚠️ Nenhum canal selecionado.", ephemeral=True)
                return
            target = guild.get_channel(int(channel_id))
            if not target:
                await interaction2.response.send_message("❌ Canal não encontrado.", ephemeral=True)
                return
            await interaction2.response.edit_message(content=f"📤 Enviando embed **{dados.get('nome', 'Sem nome')}** para {target.mention}...", embed=None, view=self)
            await target.send(embed=embed)
            log_sart(f"Embed '{dados.get('nome')}' enviado para {target.name}")

        channel_select.callback = send_callback
        select_view = discord.ui.View(timeout=300)
        select_view.add_item(channel_select)
        await interaction.response.send_message(
            f"📤 Enviando o embed **{dados.get('nome', 'Sem nome')}**...",
            embed=embed,
            view=select_view,
            ephemeral=True
        )


class FieldManagerView(discord.ui.View):
    def __init__(self, builder_view, bot=None):
        super().__init__(timeout=300)
        self._builder_view = builder_view
        self._bot = bot
        self._rebuild()

    def _rebuild(self):
        self.clear_items()
        campos = self._builder_view.embed_data.get("campos", [])
        shown = min(len(campos), 4)
        for i in range(shown):
            item = campos[i]
            btn = discord.ui.Button(
                label=item.get('nome', 'Sem nome')[:20],
                style=discord.ButtonStyle.secondary,
                emoji="✏️",
                row=0
            )
            btn.callback = self._make_edit_callback(i)
            self.add_item(btn)
        btn_clear = discord.ui.Button(label="Limpar", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
        btn_clear.callback = self._btn_clear
        self.add_item(btn_clear)
        btn_add = discord.ui.Button(label="Adicionar Campo", style=discord.ButtonStyle.success, emoji="➕", row=1)
        btn_add.callback = self._btn_add
        self.add_item(btn_add)
        btn_back = discord.ui.Button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
        btn_back.callback = self._btn_back
        self.add_item(btn_back)

    def _make_edit_callback(self, idx):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(ModalCampo(self, self._builder_view, indice=idx))
        return callback

    async def _btn_add(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalCampo(self, self._builder_view))

    async def _btn_clear(self, interaction: discord.Interaction):
        self._builder_view.embed_data["campos"] = []
        self._rebuild()
        await interaction.response.edit_message(
            content=f"📊 **Gerir Campos** (0/25)",
            embed=build_embed(self._builder_view.embed_data),
            view=self
        )

    async def _btn_back(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="🎨 **Construtor de Embeds** — Edita os campos abaixo:",
            embed=build_embed(self._builder_view.embed_data),
            view=self._builder_view
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


class EmbedBuilderView(discord.ui.View):
    def __init__(self, guild_id: str, bot):
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._bot = bot
        self.embed_data = {
            "titulo": "",
            "descricao": "",
            "cor": "FFD700",
            "thumbnail_url": None,
            "imagem_url": None,
            "banner_url": None,
            "autor_nome": None,
            "autor_icon": None,
            "footer_text": None,
            "footer_icon": None,
            "campos": [],
            "timestamp": False,
        }
        self._atualizar_campos()

    def _atualizar_campos(self):
        pass

    def _abrir_modal(self, interaction: discord.Interaction, modal_class, *args, **kwargs):
        pass

    @discord.ui.button(label="Título", style=discord.ButtonStyle.secondary, emoji="🏷️", row=0)
    async def btn_titulo(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalEmbedTexto("titulo", "🏷️ Editar Título", self.embed_data.get("titulo") or "",
                                placeholder="Título do embed")
        modal.set_builder(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Descrição", style=discord.ButtonStyle.secondary, emoji="📝", row=0)
    async def btn_descricao(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalEmbedTexto("descricao", "📝 Editar Descrição", self.embed_data.get("descricao") or "",
                                placeholder="Descrição do embed...", style=discord.TextStyle.paragraph)
        modal.set_builder(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cor", style=discord.ButtonStyle.secondary, emoji="🎨", row=0)
    async def btn_cor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEmbedCor(self))

    @discord.ui.button(label="Thumbnail", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def btn_thumbnail(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalEmbedURL("thumbnail_url", "🖼️ URL do Thumbnail", self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Imagem", style=discord.ButtonStyle.secondary, emoji="🖼️", row=1)
    async def btn_imagem(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalEmbedURL("imagem_url", "🖼️ URL da Imagem", self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Banner", style=discord.ButtonStyle.secondary, emoji="🖼️", row=1)
    async def btn_banner(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalEmbedURL("banner_url", "🖼️ URL do Banner (Autor)", self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Autor", style=discord.ButtonStyle.secondary, emoji="👤", row=1)
    async def btn_autor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEmbedAutor(self))

    @discord.ui.button(label="Footer", style=discord.ButtonStyle.secondary, emoji="🔖", row=1)
    async def btn_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEmbedFooter(self))

    @discord.ui.button(label="Timestamp", style=discord.ButtonStyle.secondary, emoji="⏱️", row=2)
    async def btn_timestamp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_data["timestamp"] = not self.embed_data.get("timestamp", False)
        status = "ativado" if self.embed_data["timestamp"] else "desativado"
        await interaction.response.edit_message(
            content=f"✅ **Timestamp** {status}.",
            embed=build_embed(self.embed_data),
            view=self
        )

    @discord.ui.button(label="Campos", style=discord.ButtonStyle.primary, emoji="📊", row=2)
    async def btn_campos(self, interaction: discord.Interaction, button: discord.ui.Button):
        fm_view = FieldManagerView(self, self._bot)
        await interaction.response.edit_message(
            content=f"📊 **Gerir Campos** ({len(self.embed_data.get('campos', []))}/25)",
            embed=build_embed(self.embed_data),
            view=fm_view
        )

    @discord.ui.button(label="Preview", style=discord.ButtonStyle.success, emoji="👁️", row=2)
    async def btn_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_embed(self.embed_data)
        await interaction.response.send_message(content="👁️ **Pré-visualização do embed** (só tu vais ver):", embed=embed, ephemeral=True)

    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.success, emoji="📤", row=3)
    async def btn_enviar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = self._bot.get_guild(int(self._guild_id))
        channels = [c for c in guild.text_channels] if guild else []
        channel_select = discord.ui.Select(
            placeholder="Selecione o canal...",
            options=[
                discord.SelectOption(label=c.name[:100], value=str(c.id))
                for c in channels[:25]
            ]
        )
        async def send_callback(interaction2: discord.Interaction):
            channel_id = channel_select.values[0] if channel_select.values else ""
            if not channel_id:
                await interaction2.response.send_message("⚠️ Nenhum canal selecionado.", ephemeral=True)
                return
            target = guild.get_channel(int(channel_id))
            if not target:
                await interaction2.response.send_message("❌ Canal não encontrado.", ephemeral=True)
                return
            embed = build_embed(self.embed_data)
            await interaction2.response.send_message(
                f"📤 Enviando embed para {target.mention}...",
                ephemeral=True,
            )
            await target.send(embed=embed)
            log_sart(f"Embed enviado para {target.name}")

        channel_select.callback = send_callback
        select_view = discord.ui.View(timeout=300)
        select_view.add_item(channel_select)
        await interaction.response.send_message(
            "📤 Selecione o canal para enviar o embed atual:",
            view=select_view,
            ephemeral=True
        )

    @discord.ui.button(label="Salvar", style=discord.ButtonStyle.primary, emoji="💾", row=3)
    async def btn_salvar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalNomeEmbed(self, self._guild_id, self._bot))

    @discord.ui.button(label="Limpar", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
    async def btn_limpar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_data = {
            "titulo": "",
            "descricao": "",
            "cor": "FFD700",
            "thumbnail_url": None,
            "imagem_url": None,
            "banner_url": None,
            "autor_nome": None,
            "autor_icon": None,
            "footer_text": None,
            "footer_icon": None,
            "campos": [],
            "timestamp": False,
        }
        await interaction.response.edit_message(
            content="🗑️ **Embed limpo!** Começa do zero.",
            embed=None,
            view=self
        )

    async def on_timeout(self):
        try:
            embed = build_embed(self.embed_data)
            for child in self.children:
                child.disabled = True
            msg = await self._bot.get_guild(int(self._guild_id)).get_channel(self._original_channel_id).fetch_message(self._original_message_id)
            await msg.edit(content="⏰ **Sessão de builder expirada.**", embed=embed, view=self)
        except Exception:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from utils import verificar_permissao_gestao
        is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
        is_gestao = await verificar_permissao_gestao(interaction, supabase)
        if not is_admin and not is_gestao:
            await interaction.response.send_message("⛔ Apenas Gestão ou Administradores podem usar o builder.", ephemeral=True)
            return False
        return True


class Embeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _check_gestao(self, interaction: discord.Interaction) -> bool:
        from utils import verificar_permissao_gestao
        is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
        is_gestao = await verificar_permissao_gestao(interaction, supabase)
        return is_admin or is_gestao

    @app_commands.command(name="embed-criar", description="Cria um embed personalizado interativamente (Cargo Gestão)")
    async def embed_criar(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        if not await self._check_gestao(interaction):
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        cfg = ler_config(guild_id)
        if not cfg.get("habilitado", True):
            return await interaction.followup.send("❌ O sistema de embeds está desativado neste servidor.", ephemeral=True)

        view = EmbedBuilderView(guild_id, self.bot)
        embed = build_embed(view.embed_data)
        await interaction.followup.send(
            content="🎨 **Construtor de Embeds** — Usa os botões abaixo para editar:\n"
                    "🏷️ Título | 📝 Descrição | 🎨 Cor | 🖼️ Imagens | 👤 Autor | 🔖 Footer | ⏱️ Timestamp | 📊 Campos\n\n"
                    "👁️ Preview | 📤 Enviar | 💾 Salvar | 🗑️ Limpar",
            embed=embed,
            view=view
        )
        log_sart(f"Builder iniciado por {interaction.user.display_name}")

    @app_commands.command(name="embed-listar", description="Lista os embeds salvos do servidor (Cargo Gestão)")
    async def embed_listar(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await self._check_gestao(interaction):
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        try:
            db = supabase.table("embed_configs").select("*").eq("guilda_id", guild_id).execute()
        except Exception:
            return await interaction.followup.send("❌ Erro ao conectar à base de dados.", ephemeral=True)
        if not db.data:
            return await interaction.followup.send("📭 Nenhum embed salvo.", ephemeral=True)

        embed = discord.Embed(title="💾 Embeds Salvos", color=discord.Color.gold())
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/0/2643.png")
        for row in db.data:
            embed.add_field(
                name=row.get("nome", "Sem nome"),
                value=f"ID: `{row.get('embed_id')}` | Criado por: <@{row.get('criado_por', 0)}>\nSalvo em: {row.get('criado_em', 'N/A')[:10]}",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed-enviar", description="Envia um embed salvo para um canal (Cargo Gestão)")
    async def embed_enviar(self, interaction: discord.Interaction):
        if not await self._check_gestao(interaction):
            return await interaction.response.send_message("⛔ Apenas Gestão ou Administradores.", ephemeral=True)
        await interaction.response.send_message("📤 Carregando embeds...", ephemeral=True)
        view = SendEmbedView(self.bot, str(interaction.guild_id))
        await view.populate()
        await interaction.edit_original_response(
            content="📤 Selecione um embed e um canal para enviar:",
            view=view
        )

    @app_commands.command(name="embed-apagar", description="Apaga um embed salvo (Cargo Gestão)")
    @app_commands.describe(embed_id="ID do embed a apagar")
    async def embed_apagar(self, interaction: discord.Interaction, embed_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await self._check_gestao(interaction):
            return await interaction.followup.send("⛔ Apenas Gestão ou Administradores.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        try:
            db = supabase.table("embed_configs").select("nome").eq("guilda_id", guild_id).eq("embed_id", embed_id).execute()
        except Exception:
            return await interaction.followup.send("❌ Erro na base de dados.", ephemeral=True)
        if not db.data:
            return await interaction.followup.send(f"❌ Embed com ID `{embed_id}` não encontrado.", ephemeral=True)

        supabase.table("embed_configs").delete().eq("guilda_id", guild_id).eq("embed_id", embed_id).execute()
        await interaction.followup.send(f"✅ Embed **{db.data[0].get('nome', 'Sem nome')}** (ID: `{embed_id}`) apagado.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Embeds(bot))
