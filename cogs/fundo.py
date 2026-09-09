# cogs/fundo.py
import io
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
import aiohttp
import config
from datetime import datetime
from cogs.imagem import upload_to_imgbb


def log_sart(mensagem):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] ⚙️ [S.art] {mensagem}")


def remover_fundo(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    if w < 50 or h < 50:
        raise ValueError("Imagem muito pequena")

    pixels = img.load()
    cantos = [
        pixels[0, 0],
        pixels[w - 1, 0],
        pixels[0, h - 1],
        pixels[w - 1, h - 1],
    ]
    r_fundo = sum(c[0] for c in cantos) // len(cantos)
    g_fundo = sum(c[1] for c in cantos) // len(cantos)
    b_fundo = sum(c[2] for c in cantos) // len(cantos)

    threshold = 40
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            dist = ((r - r_fundo) ** 2 + (g - g_fundo) ** 2 + (b - b_fundo) ** 2) ** 0.5
            if dist < threshold:
                pixels[x, y] = (r, g, b, 0)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()


class Fundo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fundo", description="Remove o fundo de uma imagem")
    async def fundo(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if not arquivo.content_type or not arquivo.content_type.startswith("image/"):
            return await interaction.followup.send("❌ O ficheiro anexado não é uma imagem válida.", ephemeral=True)

        try:
            image_bytes = await arquivo.read()
        except Exception:
            return await interaction.followup.send("❌ Erro ao ler o ficheiro anexado.", ephemeral=True)

        try:
            resultado_bytes = remover_fundo(image_bytes)
        except ValueError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except Exception as e:
            log_sart(f"🚨 Erro ao remover fundo: {e}")
            return await interaction.followup.send("❌ Erro ao processar a imagem.", ephemeral=True)

        api_key = getattr(config, "IMGBB_API_KEY", None)
        if not api_key:
            return await interaction.followup.send("⚠️ O serviço de hospedagem de imagens não está configurado.", ephemeral=True)

        try:
            resultado = await upload_to_imgbb(resultado_bytes, api_key)
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
            embed.set_footer(text="S.art Engine • Remoção de Fundo")
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            log_sart(f"✂️ Fundo removido para {interaction.user.name}: {link}")

        except Exception as e:
            log_sart(f"🚨 Erro ao hospedar imagem sem fundo: {e}")
            await interaction.followup.send("❌ Erro ao enviar a imagem para o serviço de hospedagem. Tenta novamente.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Fundo(bot))
