# cogs/fundo.py
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import config
from datetime import datetime
from cogs.imagem import upload_to_imgbb


def log_sart(mensagem):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] ⚙️ [S.art] {mensagem}")


CLIPDROP_API_URL = "https://clipdrop-api.co/remove-background/v1"
HF_API_URL = "https://api-inference.huggingface.co/models/briaai/RIFLE"
API_TIMEOUT = aiohttp.ClientTimeout(total=60)


async def remover_fundo_clipdrop(image_bytes: bytes, api_key: str, session: aiohttp.ClientSession) -> bytes:
    form = aiohttp.FormData()
    form.add_field("image_file", image_bytes, filename="upload.png", content_type="application/octet-stream")
    headers = {"x-api-key": api_key}

    async with session.post(CLIPDROP_API_URL, headers=headers, data=form, timeout=API_TIMEOUT) as resp:
        if resp.status == 402:
            raise RuntimeError("SEM_CRÉDITOS")
        if resp.status == 401:
            raise RuntimeError("API key inválida para o Clipdrop.")
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Clipdrop retornou status {resp.status}: {text}")
        return await resp.read()


async def remover_fundo_hf(image_bytes: bytes, api_key: str, session: aiohttp.ClientSession) -> bytes:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/octet-stream"}

    async with session.post(HF_API_URL, headers=headers, data=image_bytes, timeout=API_TIMEOUT) as resp:
        if resp.status == 503:
            raise RuntimeError("Modelo em carregamento. Tenta de novo.")
        if resp.status == 429:
            raise RuntimeError("Rate limit atingido. Espera um pouco e tenta de novo.")
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Hugging Face retornou status {resp.status}: {text}")

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            data = await resp.json()
            raise RuntimeError(data.get("error", "Erro desconhecido na API Hugging Face"))
        return await resp.read()


async def remover_fundo_com_fallback(image_bytes: bytes, session: aiohttp.ClientSession) -> bytes:
    clipdrop_key = getattr(config, "CLIPDROP_API_KEY", None)
    hf_key = getattr(config, "HF_API_KEY", None)

    if clipdrop_key:
        try:
            log_sart(f"🔄 Tentando Clipdrop...")
            return await remover_fundo_clipdrop(image_bytes, clipdrop_key, session)
        except RuntimeError as e:
            if str(e) == "SEM_CRÉDITOS":
                log_sart("🔄 Clipdrop sem créditos. Fazendo fallback para Hugging Face...")
            elif "503" in str(e) or "429" in str(e):
                log_sart("🔄 Clipdrop indisponível. Fazendo fallback para Hugging Face...")
            else:
                raise e

    if hf_key:
        log_sart("🔄 Tentando Hugging Face...")
        return await remover_fundo_hf(image_bytes, hf_key, session)

    raise RuntimeError("Nenhuma API configurada. Adiciona CLIPDROP_API_KEY ou HF_API_KEY no .env.")


class Fundo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fundo", description="Remove o fundo de uma imagem (Clipdrop + fallback HuggingFace)")
    async def fundo(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if not arquivo.content_type or not arquivo.content_type.startswith("image/"):
            return await interaction.followup.send("❌ O ficheiro anexado não é uma imagem válida.", ephemeral=True)

        try:
            image_bytes = await arquivo.read()
        except Exception:
            return await interaction.followup.send("❌ Erro ao ler o ficheiro anexado.", ephemeral=True)

        await interaction.followup.send("✂️ A remover o fundo... (pode levar alguns segundos)", ephemeral=True)

        session = interaction.client.session
        try:
            resultado_bytes = await remover_fundo_com_fallback(image_bytes, session)
        except RuntimeError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except Exception as e:
            log_sart(f"🚨 Erro ao remover fundo: {e}")
            return await interaction.followup.send("❌ Erro ao processar a imagem. Tenta novamente.", ephemeral=True)

        imgbb_key = getattr(config, "IMGBB_API_KEY", None)
        if not imgbb_key:
            return await interaction.followup.send("⚠️ O serviço de hospedagem de imagens não está configurado.", ephemeral=True)

        try:
            resultado = await upload_to_imgbb(resultado_bytes, imgbb_key)
            dados = resultado.get("data", {})
            link = dados.get("url")
            link_curto = dados.get("url_viewer", link)

            if not link:
                return await interaction.followup.send("❌ O serviço de hospedagem não retornou um link válido.", ephemeral=True)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="🔗 Abrir / Copiar Link", style=discord.ButtonStyle.link, url=link))

            embed = discord.Embed(
                title="✂️ Fundo Removido",
                description=f"**Link direto:** [Abrir imagem]({link})\n**Link visualizador:** [Abrir no ImgBB]({link_curto})",
                color=discord.Color.from_rgb(0, 255, 255),
                timestamp=datetime.now()
            )
            embed.set_image(url=link)
            embed.set_footer(text="S.art Engine • Remoção de Fundo (Clipdrop / HF)")
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            log_sart(f"✂️ Fundo removido para {interaction.user.name}: {link}")

        except Exception as e:
            log_sart(f"🚨 Erro ao hospedar imagem sem fundo: {e}")
            await interaction.followup.send("❌ Erro ao enviar a imagem para o serviço de hospedagem. Tenta novamente.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Fundo(bot))
