# cogs/card_utils.py
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import aiohttp


async def download_image(url, session: aiohttp.ClientSession):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        pass
    return None


def carregar_fonte(tamanho=18):
    fontes = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for f in fontes:
        try:
            return ImageFont.truetype(f, tamanho)
        except Exception:
            pass
    return ImageFont.load_default()


def avatar_circular(img, tamanho=100):
    img = img.convert("RGBA").resize((tamanho, tamanho))
    mask = Image.new("L", (tamanho, tamanho), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, tamanho, tamanho), fill=255)
    img.putalpha(mask)
    return img


def gerar_perfil_card(
    nick_ff, uid, nome_guilda, nivel, likes,
    br_pontos, patente_br, cs_pontos, status_veterano,
    moedas, emoji_moeda, data_criacao_jogo,
    discord_avatar_img, ff_avatar_img
):
    LARGURA, ALTURA = 900, 520
    bg_color = (20, 20, 40)
    accent = (0, 217, 255)
    texto_branco = (255, 255, 255)
    texto_cinza = (180, 180, 200)
    dourado = (255, 215, 0)

    canvas = Image.new("RGB", (LARGURA, ALTURA), bg_color)
    draw = ImageDraw.Draw(canvas)

    font_titulo = carregar_fonte(22)
    font_nome = carregar_fonte(20)
    font_grande = carregar_fonte(24)
    font_medio = carregar_fonte(18)
    font_pequeno = carregar_fonte(14)

    draw.rectangle((0, 0, LARGURA, 70), fill=(40, 40, 70))
    draw.text((20, 22), " S.art Engine  Perfil Verificado", fill=accent, font=font_titulo)

    discord_avatar_circ = avatar_circular(discord_avatar_img, 110)
    canvas.paste(discord_avatar_circ, (30, 95), discord_avatar_circ)

    ff_avatar_circ = avatar_circular(ff_avatar_img, 90)
    canvas.paste(ff_avatar_circ, (760, 95), ff_avatar_circ)

    x_info = 170
    y_inicio = 100

    draw.text((x_info, y_inicio), nick_ff, fill=texto_branco, font=font_nome)
    draw.text((x_info, y_inicio + 30), f"UID: {uid}", fill=texto_cinza, font=font_medio)
    draw.text((x_info, y_inicio + 55), f"Guilda: {nome_guilda}", fill=accent, font=font_medio)

    draw.text((x_info, y_inicio + 95), f"Nível: {nivel}", fill=texto_branco, font=font_medio)
    draw.text((x_info + 200, y_inicio + 95), f"Likes: {likes}", fill=texto_branco, font=font_medio)

    draw.text((x_info, y_inicio + 130), f"Patente BR: {patente_br}", fill=dourado, font=font_grande)
    draw.text((x_info + 350, y_inicio + 130), f"BR: {br_pontos} pts", fill=texto_cinza, font=font_medio)

    draw.text((x_info, y_inicio + 175), f"Clash Squad: {cs_pontos} pts", fill=texto_branco, font=font_medio)

    draw.text((x_info, y_inicio + 220), f"Status: {status_veterano}", fill=texto_branco, font=font_medio)

    draw.text((x_info, y_inicio + 260), f"Data de criação do jogo:", fill=texto_cinza, font=font_pequeno)
    draw.text((x_info, y_inicio + 285), f"  {data_criacao_jogo}", fill=texto_branco, font=font_medio)

    y_coins = y_inicio + 325
    draw.rectangle((x_info - 10, y_coins - 5, x_info + 300, y_coins + 45), fill=(40, 40, 70), outline=accent, width=2)
    draw.text((x_info + 15, y_coins + 8), f"{emoji_moeda}  Saldo de moedas: {moedas}", fill=dourado, font=font_grande)

    draw.line((x_info - 10, y_inicio + 360, x_info + 500, y_inicio + 360), fill=(80, 80, 110), width=1)
    draw.text((x_info, y_inicio + 375), "Cartão gerado pelo S.art Engine", fill=(100, 100, 120), font=font_pequeno)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()
