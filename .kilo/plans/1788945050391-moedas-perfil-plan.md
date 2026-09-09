# Plano: Remoção de fundo via Hugging Face (/fundo)

## Objetivo
Comando `/fundo` que remove fundo de imagem usando a Hugging Face Inference API e devolve link via ImgBB.

## Decisões
- **API**: Hugging Face Inference API
- **Modelo**: `briaai/RIFLE` (especializado em remoção de fundo)
- **Autenticação**: `Authorization: Bearer HF_API_KEY`
- **Reutilização**: `upload_to_imgbb()` de `cogs/imagem.py` para hospedar resultado
- **Async**: usa a sessão compartilhada `interaction.client.session`

## Alterações necessárias

### `config.py`
Adicionar `HF_API_KEY = os.getenv("HF_API_KEY")` como opcional.

### `.env.example`
Adicionar `HF_API_KEY=`.

### `requirements.txt`
Remover `Pillow` (não necessário com API).

### `cogs/fundo.py` (novo)
Criar cog com:
1. Função `remover_fundo_hf(image_bytes, hf_api_key, session)`:
   - POST multipart para `https://api-inference.huggingface.co/models/briaai/RIFLE`
   - Trata 503 (modelo carregando), 429 (rate limit), 422 (formato inválido)
   - Retorna bytes PNG com transparência
2. Comando `/fundo`:
   - `arquivo: discord.Attachment`
   - Valida tipo imagem
   - Mostra mensagem "✂️ A remover o fundo..." antes de processar
   - Faz upload para ImgBB
   - Devolve embed com imagem + botão link

### `main.py`
Adicionar `await self.load_extension('cogs.fundo')`.

## Pré-condições
- `aiohttp` já existe
- `IMGBB_API_KEY` e `HF_API_KEY` configurados no `.env`

## Validação
- `/fundo` com HF_API_KEY configurado → fundo removido via API
- `/fundo` sem HF_API_KEY → erro amigável
- Modelo em carregamento (503) → mensagem de espera
- Rate limit (429) → mensagem de espera

## Implementado
- [x] config.py
- [x] .env.example
- [x] requirements.txt (Pillow removido)
- [x] cogs/fundo.py
- [x] main.py
- [x] git commit 2c6bc1e
