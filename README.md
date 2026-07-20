# S.art Engine — Bot Discord Free Fire

Bot de gestão de guildas Free Fire para Discord. Verifica jogadores, gere torneios, rankings, warns e muito mais.

---

## Início Rápido

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Preencher o .env com os teus tokens

# Correr o bot
python main.py
```

### Variáveis de Ambiente (.env)

| Variável | Descrição |
|---|---|
| `DISCORD_TOKEN` | Token do bot Discord |
| `API_VERCEL_URL` | URL da API Vercel para dados FF |
| `API_VERCEL_KEY` | Chave de API da Vercel |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave service role do Supabase |

---

## Comandos

### Admin

| Comando | Descrição | Permissão |
|---|---|---|
| `/configurar` | Registra o servidor pela primeira vez | Dono do servidor |
| `/painel` | Abre o Painel de Controlo completo | Dono do servidor |

---

### Verificação

| Comando | Descrição | Permissão |
|---|---|---|
| `/entrar` | Inicia verificação de identidade FF | Qualquer membro |
| `/desvincular` | Remove o teu registo e cargo | Qualquer membro verificado |

**Como funciona o `/entrar`:**
1. Entras o teu UID do Free Fire
2. O bot verifica se pertences à guilda registada
3. Mudas o idioma da assinatura no jogo (o bot deteta)
4. Recebes o cargo automaticamente
5. Tens 5 minutos para completar

---

### Perfil

| Comando | Descrição | Permissão |
|---|---|---|
| `/perfil` | Mostra o teu perfil completo | Membro verificado |
| `/perfil @membro` | Mostra o perfil de outro membro | Membro verificado |

**Dados mostrados:** Nick FF, UID, Guilda, Nível, Likes, Patente BR, Clash Squad, Veterano, Data de criação.

---

### Gestão (Moderação)

| Comando | Descrição | Permissão |
|---|---|---|
| `/dar_cargo @membro cargo` | Atribui um cargo a um membro | Gestão |
| `/remover_cargo @membro cargo` | Remove um cargo de um membro | Gestão |
| `/limpar quantidade` | Apaga até 100 mensagens | Gestão |
| `/limpar_membro @membro quantidade` | Apaga mensagens de um membro específico | Gestão |
| `/gestao_info` | Mostra info dos comandos de gestão | Qualquer um |

---

### Torneios

| Comando | Descrição | Permissão |
|---|---|---|
| `/torneio_criar` | Cria um novo torneio (Solo/Duo/Trio/Squad) | Admin |
| `/torneio_equipa_criar id nome @m1 @m2...` | Cria uma equipa no torneio | Qualquer um |
| `/torneio_equipa_ver id` | Mostra as equipas inscritas | Qualquer um |
| `/torneio_iniciar id` | Inicia o torneio e gera brackets | Admin |
| `/torneio_brackets id` | Mostra os brackets do torneio | Qualquer um |
| `/torneio_resultado id @vencedor` | Regista o vencedor de uma partida | Admin |
| `/torneio_finalizar id` | Finaliza e limpa dados do torneio | Admin |

**Como funcionam os torneios:**
1. Admin cria torneio com modo (Solo, Duo, Trio ou Squad)
2. Capitão cria equipa com os membros
3. Cada membro recebe DM com botão Aprovar/Rejeitar
4. Ao iniciar, equipas não aprovadas são eliminadas
5. Brackets são gerados automaticamente com fases
6. Ao finalizar: DM ao campeão + mensagem no canal de vitórias

---

### Ranking

| Comando | Descrição | Permissão |
|---|---|---|
| `/ranking_guilda` | Top 10 membros por pontos BR | Qualquer um |
| `/meu_ranking` | A tua posição no ranking | Membro verificado |
| `/atualizar_ranking` | Força atualização dos dados | Admin |

---

### Warns (Advertências)

| Comando | Descrição | Permissão |
|---|---|---|
| `/dar_warn @membro` | Adverte um membro | Gestão |
| `/remover_warn @membro id` | Remove uma advertência | Gestão |
| `/lista_warns @membro` | Lista advertências de um membro | Gestão |

**Configuração (via `/painel`):**
- Limite de warns antes do ban (padrão: 3)
- Dias para expirar (padrão: 30)
- Canal de notificações de warns
- Liga/desliga o sistema

---

### Pesquisa

| Comando | Descrição | Permissão |
|---|---|---|
| `/pesquisar nome ou uid` | Pesquisa um jogador pelo nome ou UID | Qualquer um |

- Limite: **3 pesquisas por dia** por utilizador
- Aceita nome ou UID numérico

---

### Convites

| Comando | Descrição | Permissão |
|---|---|---|
| `/convites` | Mostra as tuas estatísticas de convites | Qualquer um |
| `/convites @membro` | Mostra convites de outro membro | Qualquer um |

O bot rastreia automaticamente quem convidou quem.

---

### Notificações

| Comando | Descrição | Permissão |
|---|---|---|
| `/verificar_membros` | Verifica se membros ainda estão na guilda FF | Admin |

**Tipos de notificação (configuráveis via `/painel`):**
- Atualizações do jogo
- Membros que saíram da guilda FF
- Mudanças de temporada
- Verificação automática a cada 6 horas

---

### Boas-Vindas

Sistema automático de embed quando novos membros entram.

**Configuração (via `/painel`):**
- Título da embed
- Descrição (variáveis: `{user}` = menção, `{membros}` = total)
- Cor da embed (hex)
- Canal de destino
- Liga/desliga o sistema

---

### Anti-Raid

Proteção contra ataques de raid (spam de joins).

**Configuração (via `/painel`):**
- Limite de joins por minuto (padrão: 5)
- Duração do bloqueio em minutos (padrão: 5)
- Canal de alertas
- Liga/desliga o sistema

Quando deteta raid, bloqueia o servidor temporariamente e expulsa novos membros.

---

## Painel de Controlo (`/painel`)

O painel é um menu interativo com botões para configurar tudo:

- **Configuração Base** — Guilda FF, Cargo, Canal de Logs, Cargo de Gestão
- **Warns** — Limites, expiração, canal, toggle
- **Boas-Vindas** — Mensagem, canal, toggle
- **Anti-Raid** — Limites, canal de alertas, toggle
- **Notificações** — Canais de atualizações, membros, temporada, toggle
- **Torneios** — Canal de vitórias
- **Ranking** — Top 5 e comandos
- **Estatísticas** — Resumo do servidor

---

## Estrutura do Projeto

```
MeuBotFF/
├── main.py              # Entry point do bot
├── config.py            # Variáveis de ambiente
├── database.py          # Conexão Supabase
├── utils.py             # Funções utilitárias
├── requirements.txt     # Dependências Python
├── database_tables.sql  # Schema SQL
├── capa do bot.png      # Logo do bot
├── .env.example         # Template de variáveis
└── cogs/
    ├── admin.py         # Configurar, Painel
    ├── usuarios.py      # Entrar, Desvincular, Perfil
    ├── gestao.py        # Dar/remover cargo, Limpar chat
    ├── warns.py         # Advertências
    ├── ranking.py       # Ranking BR
    ├── torneios.py      # Torneios com equipas
    ├── notificacoes.py  # Alertas FF
    ├── boas_vindas.py   # Mensagem automática
    ├── anti_raid.py     # Proteção raid
    ├── pesquisa.py      # Pesquisar jogadores
    ├── convites.py      # Sistema de convites
    └── ajuda.py         # Comando /ajuda
```

---

## Tecnologias

- **Python** + discord.py
- **Supabase** (PostgreSQL) — base de dados
- **API Vercel** — dados em tempo real do Free Fire
