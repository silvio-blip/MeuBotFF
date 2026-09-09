# cogs/imagem.py
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import config
from datetime import datetime


def log_sart(mensagem):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] ⚙️ [S.art] {mensagem}")


IMGBB_API_URL = "https://api.imgbb.com/1/upload"


async def upload_to_imgbb(image_bytes: bytes, api_key: str) -> dict:
    data = aiohttp.FormData()
    data.add_field("image", image_bytes, filename="upload.png", content_type="application/octet-stream")
    data.add_field("key", api_key)
    data.add_field("expiration", "3600")

    async with aiohttp.ClientSession() as session:
        async with session.post(IMGBB_API_URL, data=data) as resp:
            if resp.status == 200:
                return await resp.json()
            text = await resp.text()
            raise RuntimeError(f"ImgBB retornou status {resp.status}: {text}")


class Imagem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="imagem", description="Transforma uma imagem em link (ImgBB)")
    async def imagem(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if not arquivo.content_type or not arquivo.content_type.startswith("image/"):
            return await interaction.followup.send("❌ O ficheiro anexado não é uma imagem válida.", ephemeral=True)

        api_key = getattr(config, "IMGBB_API_KEY", None)
        if not api_key:
            return await interaction.followup.send("⚠️ O serviço de hospedagem de imagens não está configurado.", ephemeral=True)

        try:
            image_bytes = await arquivo.read()
        except Exception:
            return await interaction.followup.send("❌ Erro ao ler o ficheiro anexado.", ephemeral=True)

        try:
            resultado = await upload_to_imgbb(image_bytes, api_key)
            dados = resultado.get("data", {})
            link = dados.get("url")
            link_curto = dados.get("url_viewer", link)

            if not link:
                return await interaction.followup.send("❌ O serviço de hospedagem não retornou um link válido.", ephemeral=True)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="🔗 Abrir / Copiar Link", style=discord.ButtonStyle.link, url=link))

            embed = discord.Embed(
                title="🖼️ Imagem Hospedada",
                description=f"**Link direto:** [Abrir imagem]({link})\n**Link visualizador:** [Abrir no ImgBB]({link_curto})",
                color=discord.Color.from_rgb(0, 255, 255),
                timestamp=datetime.now()
            )
            embed.set_image(url=link)
            embed.set_footer(text="S.art Engine • Hospedagem de Imagens")
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            log_sart(f"🖼️ Imagem hospedada para {interaction.user.name}: {link}")

        except Exception as e:
            log_sart(f"🚨 Erro ao hospedar imagem: {e}")
            await interaction.followup.send("❌ Erro ao enviar a imagem para o serviço de hospedagem. Tenta novamente.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Imagem(bot))
