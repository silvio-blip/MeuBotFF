import os
from dotenv import load_dotenv

caminho_atual = os.path.dirname(__file__)
load_dotenv(os.path.join(caminho_atual, '.env'))

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_VERCEL_URL = os.getenv("API_VERCEL_URL")
API_VERCEL_KEY = os.getenv("API_VERCEL_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

missing = [k for k, v in {
    "DISCORD_TOKEN": DISCORD_TOKEN,
    "API_VERCEL_URL": API_VERCEL_URL,
    "API_VERCEL_KEY": API_VERCEL_KEY,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
}.items() if not v]

if missing:
    print(f"🚨 ERRO: Variáveis de ambiente em falta no .env: {', '.join(missing)}")
    exit(1)