# utils.py — Funções partilhadas do bot
import time
from datetime import datetime

IDIOMAS_FF = {
    1: "English", 3: "中文 (繁)", 4: "ไทย", 5: "Tiếng Việt",
    6: "Indonesia", 7: "Português", 8: "Español", 9: "Русский",
    11: "Français", 13: "Türkçe", 14: "हिन्दी", 17: "العربية",
    20: "বাংলা", 21: "Malay"
}

def log_sart(msg):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] ⚙️ [S.art] {msg}")

def calcular_patente(pontos):
    if pontos >= 6000: return "🏆 Elite / Desafiante"
    elif pontos >= 3200: return "🏅 Mestre"
    elif pontos >= 2600: return "💎 Diamante"
    elif pontos >= 2100: return "💠 Platina"
    elif pontos >= 1600: return "🥇 Ouro"
    elif pontos >= 1300: return "🥈 Prata"
    else: return "🥉 Bronze"

def calcular_veterano(data_criacao):
    if data_criacao < 1000000000:
        return "❓ Desconhecido"
    idade_segundos = int(time.time()) - data_criacao
    um_ano = 31536000
    if idade_segundos >= um_ano * 4: return "👑 Lenda Ancestral (4+ Anos)"
    elif idade_segundos >= um_ano * 2: return "🎖️ Veterano Experiente (2+ Anos)"
    elif idade_segundos >= um_ano: return "⚔️ Soldado Frequente (1+ Ano)"
    else: return "🔰 Novato Promissor"

async def verificar_permissao_gestao(interaction, supabase):
    if interaction.user.guild_permissions.administrator:
        return True
    id_servidor = str(interaction.guild_id)
    db_res = supabase.table("servidores").select("cargo_gestao_id").eq("id_discord", id_servidor).execute()
    if db_res.data and db_res.data[0].get("cargo_gestao_id"):
        try:
            cargo_id = int(db_res.data[0]["cargo_gestao_id"])
            cargo_gestao = interaction.guild.get_role(cargo_id)
            if cargo_gestao and cargo_gestao in interaction.user.roles:
                return True
        except (ValueError, TypeError):
            pass
    return False
