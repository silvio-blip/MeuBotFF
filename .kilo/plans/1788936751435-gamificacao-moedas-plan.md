da ga# Sistema de Gamificação - Moedas S.art

## Objetivo
Adicionar um sistema de moedas ao bot onde os membros ganham moedas por ações no servidor. Toda a configuração (valores por ação, limite diário, ícone) será feita através do **Painel de Admin**. A moeda usa o ícone fornecido como imagem oficial.

---

## Armazenamento

### Tabela `membros_verificados`
- Adicionar coluna `moedas INT DEFAULT 0`
- Motivo: já tem `id_discord` + `id_servidor`, sem joins extras

### Tabela `economia_config` (configuração por servidor)
```sql
CREATE TABLE economia_config (
  guilda_id TEXT PRIMARY KEY,
  moedas_entrada INT DEFAULT 10,
  moedas_pesquisa INT DEFAULT 5,
  moedas_convite INT DEFAULT 15,
  moedas_torneio_participar INT DEFAULT 20,
  moedas_torneio_vencer INT DEFAULT 100,
  moedas_daily INT DEFAULT 10,
  limite_diario INT DEFAULT 50,
  habilitado BOOLEAN DEFAULT TRUE
);
```

### Tabela `economia_daily` (cooldown do daily por usuário)
```sql
CREATE TABLE economia_daily (
  user_id TEXT,
  servidor_id TEXT,
  data TEXT,
  usado BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (user_id, servidor_id, data)
);
```

---

## Ações que geram moedas (valores padrão, configuráveis no painel)

| Ação | Coluna config | Valor padrão | Onde dispara |
|------|---------------|-------------|--------------|
| Verificação `/entrar` | `moedas_entrada` | 10 | `cogs/usuarios.py` |
| `/pesquisa` | `moedas_pesquisa` | 5 | `cogs/pesquisa.py` |
| Convite válido | `moedas_convite` | 15 | `cogs/convites.py` |
| Participar torneio | `moedas_torneio_participar` | 20 | `cogs/torneios.py` |
| Vencer torneio | `moedas_torneio_vencer` | 100 | `cogs/torneios.py` |
| Daily `/daily` | `moedas_daily` | 10 | `cogs/economia.py` |

**Regra geral:**
- Apenas membros **verificados** ganham moedas
- Se `habilitado = false`, nenhuma ação dá moedas
- Se `limite_diario` for atingido, nenhuma ação dá moedas até o dia seguinte

---

## Comandos públicos (`cogs/economia.py`)

1. `/saldo` — Embed com:
   - Saldo atual do usuário
   - Limite diário restante
   - Últimas 3 transações (opcional)
   - Thumbnail com ícone da moeda

2. `/topmoedas` — Embed com:
   - Top 10 membros verificados com mais moedas
   - Formato: `🥇 Nome — 💰 X moedas`

3. `/daily` — Claim diário:
   - Verifica tabela `economia_daily` para o usuário hoje
   - Se não usado, adiciona `moedas_daily` e marca como usado
   - Cooldown: 24h (reset por data UTC)

---

## Painel Admin (`cogs/admin.py`)

### Alterações no menu principal
Adicionar opção no `ViewMenuPrincipal`:
```python
discord.SelectOption(label="💰 Economia", value="economia", emoji="💰", description="Moedas, recompensas e loja")
```

### Nova categoria `economia`
Função `build_categoria(guild, "economia")` retorna embed + `ViewEconomia`:
- **Título:** 💰 Economia do Servidor
- **Campos:**
  - Status do sistema: ON/OFF
  - Limite diário: X moedas/dia
  - Tabela com valores por ação:
    - Entrada: X
    - Pesquisa: X
    - Convite: X
    - Participar torneio: X
    - Vencer torneio: X
    - Daily: X
- **Footer:** 🔄 Usa o menu abaixo para voltar

### View `ViewEconomia`
Botões organizados em 2 linhas:

**Linha 1:**
- 🔄 Ligar/Desligar — Toggle `habilitado`
- ⚙️ Configurar Valores — Modal `ModalConfigEconomia`
- 📊 Ver Estatísticas — Mostra total de moedas em circulação, top 3

**Linha 2:**
- 🗑️ Reset Diário — Limpa tabela `economia_daily` (opcional, admin only)

### Modal `ModalConfigEconomia`
Campos:
- `moedas_entrada` (number, default 10)
- `moedas_pesquisa` (number, default 5)
- `moedas_convite` (number, default 15)
- `moedas_torneio_participar` (number, default 20)
- `moedas_torneio_vencer` (number, default 100)
- `moedas_daily` (number, default 10)
- `limite_diario` (number, default 50)

Ao submeter: `UPSERT` em `economia_config` com todos os valores + `habilitado = true`

---

## Design visual

- Cor dos embeds: `discord.Color.from_rgb(255, 215, 0)` (dourado)
- Thumbnail: ícone da moeda (`https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/1446515346201776283_1774.png`)
- Formato de moedas: `💰 X moedas`
- Formato de valores no painel: `` `X` `` (code block)

---

## Integração com cogs existentes

### `cogs/usuarios.py` (verificação)
Depois de entregar cargo e enviar embed:
```python
economia = supabase.table("economia_config").select("*").eq("guilda_id", guild_id).execute()
if economia.data and economia.data[0].get("habilitado"):
    moedas = economia.data[0].get("moedas_entrada", 10)
    adicionar_moedas(guild_id, str(user.id), moedas)
```

### `cogs/pesquisa.py` (pesquisa)
Depois de enviar embed de resultado:
```python
economia = supabase.table("economia_config").select("*").eq("guilda_id", interaction.guild_id).execute()
if economia.data and economia.data[0].get("habilitado"):
    moedas = economia.data[0].get("moedas_pesquisa", 5)
    adicionar_moedas(str(interaction.guild_id), str(interaction.user.id), moedas)
```

### `cogs/convites.py` (convite válido)
Quando membro entra e é detectado como convite válido:
```python
economia = supabase.table("economia_config").select("*").eq("guilda_id", guild_id).execute()
if economia.data and economia.data[0].get("habilitado"):
    moedas = economia.data[0].get("moedas_convite", 15)
    adicionar_moedas(guild_id, convidador_id, moedas)
```

### `cogs/torneios.py` (participar/vencer)
- Ao criar equipa: adicionar `moedas_torneio_participar`
- Ao finalizar e declarar vencedor: adicionar `moedas_torneio_vencer`

---

## Validação
- [ ] Banco de dados: coluna `moedas` + tabelas `economia_config` e `economia_daily`
- [ ] `/saldo` retorna saldo correto
- [ ] `/topmoedas` retorna top 10 correto
- [ ] `/daily` funciona com cooldown 24h
- [ ] Painel admin mostra e salva configurações
- [ ] Ganho de moedas funciona em: verificação, pesquisa, convite, torneio
- [ ] Limite diário bloqueia após atingir
- [ ] `habilitado = false` bloqueia todos os ganhos
- [ ] Persistência correta no Supabase

---

## Riscos
- **Spam de comandos** → Limite diário configurável
- **Convites falsos** → Validação existente no cog convites
- **Latência API FF** → Moedas adicionadas após sucesso da ação
- **Race condition no daily** → Usar `upsert` com `PRIMARY KEY (user_id, servidor_id, data)`

---

## Fora do escopo (depois)
- Loja para gastar moedas
- Cargos compráveis
- Apostas/jogos de azar
- Transferência entre usuários
- Histórico completo de transações
