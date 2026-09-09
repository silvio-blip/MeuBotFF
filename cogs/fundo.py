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
CLIPDROP_TIMEOUT = aiohttp.ClientTimeout(total=60)


async def remover_fundo_clipdrop(image_bytes: bytes, api_key: str, session: aiohttp.ClientSession) -> bytes:
    fname = "upload"
    form = aiohttp.FormData()
    form.add_field("image_file", image_bytes, filename=fname, content_type="image/png")

    headers = {"x-api-key": api_key}

    async with session.post(
        CLIPDROP_API_URL,
        headers=headers,
        data=form,
        timeout=CLIPDROP_TIMEOUT,
    ) as resp:
        if resp.status == 401:
            raise RuntimeError("API key inválida para o Clipdrop.")
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Clipdrop retornou status {resp.status}: {text}")
        return await resp.read()


class Fundo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fundo", description="Remove o fundo de uma imagem usando Clipdrop")
    async def fundo(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if not arquivo.content_type or not arquivo.content_type.startswith("image/"):
            return await interaction.followup.send("❌ O ficheiro anexado não é uma imagem válida.", ephemeral=True)

        api_key = getattr(config, "CLIPDROP_API_KEY", None)
        if not api_key:
            return await interaction.followup.send("⚠️ A API do Clipdrop não está configurada (`CLIPDROP_API_KEY`).", ephemeral=True)

        try:
            image_bytes = await arquivo.read()
        except Exception:
            return await interaction.followup.send("❌ Erro ao ler o ficheiro anexado.", ephemeral=True)

        await interaction.followup.send("✂️ A remover o fundo... (pode levar alguns segundos)", ephemeral=True)

        session = interaction.client.session
        try:
            resultado_bytes = await remover_fundo_clipdrop(image_bytes, api_key, session)
        except RuntimeError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except Exception as e:
            log_sart(f"🚨 Erro ao remover fundo via Clipdrop: {e}")
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
            embed.set_footer(text="S.art Engine • Remoção de Fundo (Clipdrop)")
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            log_sart(f"✂️ Fundo removido via Clipdrop para {interaction.user.name}: {link}")

        except Exception as e:
            log_sart(f"🚨 Erro ao hospedar imagem sem fundo: {e}")
            await interaction.followup.send("❌ Erro ao enviar a imagem para o serviço de hospedagem. Tenta novamente.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Fundo(bot))
