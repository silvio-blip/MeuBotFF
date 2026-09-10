# Plano: Sistema de Embed Builder (`/embed` + `/painel`)

## Objetivo
Criar um sistema interativo para construir embeds personalizados no servidor, com gerenciamento de palavras, imagens (URL ou anexo), cores, campos, etc. Apenas cargo Gestão / Admin podem usar.

## Decisões de Design

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Storage | Supabase `embed_configs` | Consistente com todos os outros sistemas |
| UI | View interativa → botões → modais | UX completa: add/remove/edit cada propriedade |
| Imagens | URL texto input + upload ImgBB | Reutiliza `cogs/imagem.py` (ImgBB já integrado) |
| Permissão | `verificar_permissao_gestao` | Igual a `/add-moedas`, `/desmutar`, etc. |
| Comandos | Nomes flat (`/embed-criar`, `/embed-salvar`, etc.) | Segue padrão existente (`torneio_criar`, etc.) |
| Fields | JSON no Supabase | Supabase TEXT col ou JSON |

## Arquivos

### Novos
- `cogs/embeds.py` — Cog principal
- `scripts/embeds_setup.sql` — Migration da tabela

### Modificados
- `database_tables.sql` — Adicionar tabela `embed_configs`
- `cogs/admin.py` — Dropdown, `build_categoria` branch, `ViewEmbeds`, cleanup
- `cogs/ajuda.py` — Página "🎨 Embed Builder"
- `main.py` — Registrar `cogs.embeds`

## Tarefa 1: Tabela `embed_configs`

```sql
CREATE TABLE IF NOT EXISTS embed_configs (
  guilda_id TEXT,
  embed_id TEXT,
  nome TEXT,
  titulo TEXT,
  descricao TEXT,
  cor TEXT DEFAULT 'FFD700',
  thumbnail_url TEXT,
  imagem_url TEXT,
  banner_url TEXT,
  autor_nome TEXT,
  autor_icon TEXT,
  footer_text TEXT,
  footer_icon TEXT,
  campos TEXT,
  timestamp BOOLEAN DEFAULT FALSE,
  criado_por TEXT,
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (guilda_id, embed_id)
);
ALTER TABLE embed_configs DISABLE ROW LEVEL SECURITY;
```

`campos` armazenado como JSON: `[{"nome":"...", "valor":"...", "inline":true}, ...]`

## Tarefa 2: Cog `cogs/embeds.py`

### Permission helper
```python
async def _check_gestao(interaction):
    from utils import verificar_permissao_gestao
    is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
    is_gestao = await verificar_permissao_gestao(interaction, supabase)
    return is_admin or is_gestao
```

### Comandos
| Comando | Descrição |
|---------|-----------|
| `/embed-criar` | Inicia builder interativo → abre `EmbedBuilderView` |
| `/embed-listar` | Lista embeds salvos (dropdown) |
| `/embed-enviar @canal @embed_id` | Envia embed salvo |
| `/embed-salvar nome` | Salva o embed atualmente em construção |
| `/embed-apagar @embed_id` | Deleta embed salvo (autocomplete) |

### `EmbedBuilderView` (View interativa)
Mantém estado em `self.embed_data` (dict). Botões:

| Botão | Ação |
|-------|------|
| 🏷️ Título | Modal `ModalTexto` (titulo) |
| 📝 Descrição | Modal `ModalTexto` (descricao, paragraph) |
| 🎨 Cor | Modal `ModalTexto` (cor hex, padrão FFD700) |
| 🖼️ Thumbnail | Modal `ModalTexto` (url) + botão upload attachment → ImgBB |
| 🖼️ Imagem | Igual ao thumbnail |
| 📊 Campos | Abre `FieldManagerView` |
| 👤 Autor | Modal (nome + icon_url) |
| 🔖 Footer | Modal (texto + icon_url) |
| ⏱️ Timestamp | Toggle boolean |
| 👁️ Preview | Envia embed preview como DM ou canal |
| 📤 Enviar | Modal para selecionar canal + enviar |
| 💾 Salvar | Modal para nome + salva no DB |
| 🗑️ Limpar | Reseta tudo |

### `FieldManagerView` (gerencia campos)
- Lista campos existentes como buttons (Nome → valor, inline)
- ➕ "Adicionar Campo" → `ModalCampo` (nome, valor, inline)
- Para cada campo: ✏️ Editar, 🗑️ Remover

### Upload de imagem (reutiliza `imagem.py`)
```python
async def _upload_attachment(attachment: discord.Attachment) -> str:
    from cogs.imagem import upload_to_imgbb
    image_bytes = await attachment.read()
    result = await upload_to_imgbb(image_bytes, config.IMGBB_API_KEY)
    return result["data"]["url"]
```

### `ModalCampo`
- `nome` (TextInput)
- `valor` (TextInput)
- `inline` (TextInput "true/false")

## Tarefa 3: Integração Admin Panel

### Dropdown (`ViewMenuPrincipal.select_cat`)
```python
discord.SelectOption(label="Embeds", value="embeds", emoji="🎨", description="Criar e gerir embeds personalizados"),
```

### `build_categoria` branch
```python
elif cat == "embeds":
    embeds_cfg = ler_sub("embeds_config", guild_id)  # toggle table
    embed_count = supabase.table("embed_configs").select("embed_id").eq("guilda_id", guild_id).execute()
    embed = discord.Embed(...)
    return embed, ViewEmbeds()
```

### `ViewEmbeds`
- 📊 Status (on/off do sistema)
- ➕ Criar Embed (abre builder)
- 📋 Listar Embeds
- 🔄 Ligar/Desligar

### `embeds_config` tabela (toggle)
Adicionar coluna `habilitado` — mesma pattern de `toggle_config`.

### Cleanup (`remover_servidor`)
Adicionar:
```python
("embed_configs", "guilda_id"),
("embeds_config", "guilda_id"),
```

## Tarefa 4: Help (`cogs/ajuda.py`)

### Inicio page
```
"🎨 **Embed Builder** — Cria embeds personalizados no servidor\n"
```

### Nova página "embeds"
Documentar todos os comandos, o builder interativo, e o painel.

## Tarefa 5: `main.py`
```python
await self.load_extension('cogs.embeds')
```

## Riscos e Considerações

1. **Attachments expiram** — Discord attachment URLs expiram. Usar ImgBB (já integrado) para persistência.
2. **Limite de campos** — Discord permite máximo 25 campos por embed. Validar.
3. **Limite de caracteres** — title 256, description 4096, field name 256, field value 1024. Validar no preview.
4. **Cache de embeds** — Cachear resultados do DB na view para evitar lookups repetidos durante o builder.
5. **Timeout da view** — Usar `timeout=300` (5 min) para o builder.
6. **Embed data size** — JSON dos campos pode ficar grande; usar Supabase TEXT para flexibilidade.
7. **Permission race** — Verificar permissão no momento do envio (not só na criação).

## Validação
1. `python3 -m py_compile cogs/embeds.py` — syntax OK
2. Teste criar embed → preview no DM
3. Teste salvar → listar → enviar
4. Teste permissoes: usuário sem cargo gestão não consegue criar
5. Teste upload de imagem via attachment → ImgBB
6. Teste admin panel: dropdown, view, toggle
