# Plano: Módulo de Música — Sistema DJ, Bloqueio de Canal e Integração ao Painel

## Contexto

**Arquivo:** `cogs/player/__init__.py` (package)
**Cog:** `Musica` (carregada em `main.py:40` via `await self.load_extension('cogs.player')`)
**Arquitetura atual:** yt-dlp (sync via `run_in_executor`) + `discord.FFmpegPCMAudio` + `PCMVolumeTransformer`
**Comandos atuais:** `/play`, `/add_fila`, `/funk`, `/pular`, `/stop`, `/fila`

**Padrões do projeto observados:**
- Todo cog: `class X(commands.Cog)` + `async def setup(bot): await bot.add_cog(X(bot))`
- Slash commands com `@app_commands.command`; padrão `defer()` → `followup.send()`
- Permissões: `cargo_gestao_id` via Supabase (ver `utils.verificar_permissao_gestao`, `gestao.py`, `warns.py`)
- Embeds com `discord.Color.from_rgb(...)`, footer `"S.art Engine • ..."`
- Painel de admin em `cogs/admin.py`: dropdown (`ViewMenuPrincipal`) + `build_categoria(guild, cat)` + views por categoria
- Helpers reutilizáveis em `admin.py`: `ler_sub()`, `toggle_config()`, `safe_channel()`, `safe_role()`, `on_off()`, `SelectCanalComUpdate(...)`, `SelectCargoGestaoComUpdate(...)`
- `global_check` em `main.py:53` exige servidor registrado + cargo gestão/admin ou membro verificado (comandos de música herdam isso)

## Objetivo

Ajustar o módulo `cogs/player` para:
1. Permitir que o admin defina um **canal de texto** onde os comandos de música só funcionam e onde o bot posta as respostas
2. Integrar tudo ao **painel de admin** (`/painel`)
3. Implementar um sistema de **DJ/Líder**: quem tocar música vira líder; se sair e tiver gente no canal, liderança passa para outro; se o bot estiver inativo, quem tocar vira líder
4. Ter um **cargo de gestão de música** que controla os comandos a qualquer momento, mesmo se outro for líder
5. Fixar os bugs críticos e adicionar comandos básicos que faltam

## Decisões de Projeto

| Decisão | Detalhe |
|---------|---------|
| Arquitetura | Mantém yt-dlp + FFmpegPCMAudio (NÃO migra para wavelink/Lavalink) |
| Tabela | Nova tabela `musica_config` no Supabase |
| Bloqueio de canal | Comandos só funcionam no `canal_comandos` (quando configurado). Admin/owner/cargo-musica fazem bypass. Não configurado = libre. |
| Output do bot | Posta respostas na `canal_comandos`. Não configurado = responde no canal onde o comando foi usado. |
| DJ/Líder | Quem roda `/play` vira DJ. `/play` quando já tocando exige DJ ou cargo-música. Comandos de controle exigem DJ/cargo-música/admin/owner. |
| Transferência DJ | Quando DJ sai do VC com outros presentes → 1º humano restante vira DJ. VC vazio → bot desconecta + limpa. |
| Cargo música | `cargo_musica_id` sempre sobrepõe DJ (pode controlar a qualquer momento). |
| Volume | Remove filtro ffmpeg `volume=1.0`; usa só `PCMVolumeTransformer(player.volume)`. |
| Race condition | Remove flag `is_replaying`; `/play` limpa a fila para trocar a faixa limpa. |
| FFmpeg check | `shutil.which("ffmpeg")` no startup; aviso se ausente. |
| Timeout yt-dlp | `socket_timeout: 15` em `BASE_YDL_OPTIONS`. |

## Camada de Dados

Arquivo: `scripts/musica_setup.sql`

```sql
CREATE TABLE IF NOT EXISTS musica_config (
  guilda_id TEXT PRIMARY KEY,
  canal_comandos TEXT,
  cargo_musica_id TEXT,
  habilitado BOOLEAN DEFAULT TRUE
);
ALTER TABLE musica_config DISABLE ROW LEVEL SECURITY;
```

## Integração ao Painel (`cogs/admin.py`)

### 1. Dropdown (`ViewMenuPrincipal`)
Adicionar opção:
```python
discord.SelectOption(label="Música", value="musica", emoji="🎵", description="DJ, canal e permissões de música")
```

### 2. `build_categoria(guild, cat)` — nova categoria `elif cat == "musica"`
- Lê `musica_config` via `ler_sub("musica_config", guild_id)`
- Mostra: Status ON/OFF, Canal de Comandos (mention ou "Não definido"), Cargo Música (mention ou "Não definido")
- Lista comandos ativos e ações disponíveis
- Retorna `ViewMusica()`

### 3. `ViewMusica`
- `musica_back` (select) → volta para `main`
- Botão "Definir Canal" → `SelectCanalComUpdate(guild_id, bot, "musica_config", "canal_comandos", "musica")`
- Botão "Cargo DJ" → `SelectCargoMusicaComUpdate(guild_id, bot)` (novo — atualiza `musica_config.cargo_musica_id`)
- Botão "Ligar/Desligar" → `toggle_config("musica_config", guild_id)`

### 4. `SelectCargoMusicaComUpdate`
Novo view (espelha `SelectCargoGestaoComUpdate` mas atualiza `musica_config.cargo_musica_id` em vez de `servidores.cargo_gestao_id`).

## Reescrita do Cog (`cogs/player/__init__.py`)

### Helpers / funções

| Helper | Responsabilidade |
|--------|-----------------|
| `check_ffmpeg()` | `shutil.which("ffmpeg")`; log de aviso se ausente |
| `_ler_config(guild_id)` | lê `musica_config` (igual `ler_sub` do admin) |
| `_music_channel(interaction)` | `discord.TextChannel` de `canal_comandos` ou fallback no canal atual |
| `_check_canal(interaction)` | True se dentro do canal-música ou bypass (admin/owner/cargo-musica). Else rejeita efêmero. |
| `_check_dj(interaction)` | True se user == DJ ou cargo-música ou admin/owner |
| `_responder(interaction, embed, view=None)` | posta no canal-música (ou actual); se fora do canal por cargo-música, aviso efêmero + posta no canal-música |

### `MusicPlayer` — campos adicionados
- `dj_id: int = None` — usuário que controla
- `loop_current: bool = False` — repetir faixa atual
- `volume: float = 1.0` (default full)

### `Musica` cog — listeners
- `on_voice_state_update(member, before, after)`:
  - Bot saiu/movido → `voice_client = None`, para play, limpa
  - DJ saiu, outros presentes → transfere DJ para 1º humano
  - VC sem humanos → disconnect + limpa + `dj_id = None`

### Comandos (com gate de canal `canal_comandos` + DJ)

| Comando | Público | Gate | Comportamento chave |
|---------|---------|------|---------------------|
| `/play` | Canal música | DJ se já tocando | Conecta/vira DJ; limpa fila, troca faixa |
| `/add_fila` | Canal música | Nenhum | Adiciona à fila; toca se vazia |
| `/funk` | Canal música | DJ se já tocando | Random funk; vira DJ |
| `/pular` | — | DJ/cargo-música | Para faixa → próxima |
| `/pause` | — | DJ/cargo-música | `vc.pause()` |
| `/resume` | — | DJ/cargo-música | `vc.resume()` |
| `/stop` | — | DJ/cargo-música | Para + limpa fila + desconecta |
| `/np` | Público | Nenhum | Embed faixa atual + progresso |
| `/fila` | Público | Nenhum | Lista fila |
| `/volume` | — | DJ/cargo-música | 1–100; atualiza `PCMVolumeTransformer` |
| `/disconnect` | — | DJ/cargo-música | Desconecta + limpa |
| `/clear` | — | DJ/cargo-música | Limpa só a fila |
| `/loop` | — | DJ/cargo-música | Alterna `loop_current` |
| `/shuffle` | — | DJ/cargo-música | Embaralha fila |

### Correções de bugs incluídas no rewrite
- `start_playing`: remove `is_replaying`; remove filtro `volume=1.0`; usa `player.volume`
- `play_cmd`: `player.clear()` antes de trocar a faixa (semântica "troca a atual")
- `after_playing`: chama `on_track_end` → `play_next`; se `loop_current` e sem next → re-toca `current_track`; se VC sem humanos → disconnect

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Bot posta resposta no canal-música de outro servidor | `_check_canal` usa `interaction.guild_id` isolado; `safe_channel` valida existência |
| ffmpeg ausente no deploy | `check_ffmpeg()` loga aviso no startup |
| stream URL do yt-dlp expira | re-extrai em cada `start_playing` (mantido) |
| `on_voice_state_update` vê membros sem `members` intent | `intents.members = True` já está em `main.py:14` |
| Race condition transferência DJ | usar `asyncio.create_task` para verificar membros do VC no momento do leave |

## Validação

- [ ] `python -m py_compile cogs/player/__init__.py` — compila
- [ ] `python -m py_compile cogs/admin.py` — compila
- [ ] `check_ffmpeg()` roda no startup sem crash
- [ ] `/play` fora do canal configurado → rejeição efêmera (exceção: cargo-música)
- [ ] `/pular` por não-DJ → recusa efêmera
- [ ] `/play` por cargo-música quando DJ ativo → funciona
- [ ] DJ sai VC, outro humano presente → líder transfere + aviso no canal
- [ ] Bot sozinho no VC → disconnect + limpa
- [ ] `/volume 80` → áudio reflete aumento
- [ ] `/loop` → repete faixa; `/pular` sai do loop para próxima
- [ ] `/np` mostra faixa atual + duração + progresso
- [ ] `/stop` limpa playlist + desconecta
- [ ] Painel `/painel` → Música mostra status + botões funcionam

## Fora do Escopo

- Migração para wavelink (infra Lavalink separada)
- Playlist persistente entre reinícios (in-memory, igual hoje)
- `/seek` (avançar posição) — complexo com FFmpegPCMAudio puro
