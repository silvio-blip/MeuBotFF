# cogs/fundo.py
import io
import json
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


HF_API_URL = "https://api-inference.huggingface.co/models/briaai/RIFLE"
HF_TIMEOUT = aiohttp.ClientTimeout(total=60)


async def remover_fundo_hf(image_bytes: bytes, hf_api_key: str, session: aiohttp.ClientSession) -> bytes:
    headers = {"Authorization": f"Bearer {hf_api_key}", "Content-Type": "application/octet-stream"}
    try:
        async with session.post(
            HF_API_URL,
            headers=headers,
            data=image_bytes,
            timeout=HF_TIMEOUT,
        ) as resp:
            if resp.status == 503:
                msg = await resp.text()
                raise RuntimeError(f"Modelo em carregamento. Tenta de novo em 1 minuto. ({msg})")
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
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Erro de rede ao contactar Hugging Face: {e}")


class Fundo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fundo", description="Remove o fundo de uma imagem usando Hugging Face")
    async def fundo(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if not arquivo.content_type or not arquivo.content_type.startswith("image/"):
            return await interaction.followup.send("❌ O ficheiro anexado não é uma imagem válida.", ephemeral=True)

        hf_api_key = getattr(config, "HF_API_KEY", None)
        if not hf_api_key:
            return await interaction.followup.send("⚠️ A API do Hugging Face não está configurada (`HF_API_KEY`).", ephemeral=True)

        try:
            image_bytes = await arquivo.read()
        except Exception:
            return await interaction.followup.send("❌ Erro ao ler o ficheiro anexado.", ephemeral=True)

        await interaction.followup.send("✂️ A remover o fundo... (pode levar alguns segundos)", ephemeral=True)

        session = interaction.client.session
        try:
            resultado_bytes = await remover_fundo_hf(image_bytes, hf_api_key, session)
        except RuntimeError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except Exception as e:
            log_sart(f"🚨 Erro ao remover fundo via HF: {e}")
            return await interaction.followup.send("❌ Erro ao processar a imagem via Hugging Face.", ephemeral=True)

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
            embed.set_footer(text="S.art Engine • Remoção de Fundo (Hugging Face)")
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            log_sart(f"✂️ Fundo removido via HF para {interaction.user.name}: {link}")

        except Exception as e:
            log_sart(f"🚨 Erro ao hospedar imagem sem fundo: {e}")
            await interaction.followup.send("❌ Erro ao enviar a imagem para o serviço de hospedagem. Tenta novamente.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Fundo(bot))
