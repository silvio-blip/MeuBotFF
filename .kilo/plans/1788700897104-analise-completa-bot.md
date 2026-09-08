# S.art Engine — Análise Completa do Bot

## Visão Geral
Bot de gestão de guildas Free Fire para Discord, usando `discord.py`, Supabase (PostgreSQL) e API Vercel para dados do jogo.

---

## Stack Tecnológico
- **Python 3** + discord.py 2.3+
- **Supabase** — base de dados (client-side direto com service_role)
- **aiohttp** — sessões HTTP partilhadas para API FF
- **API Vercel** (`fire-id-old.vercel.app`) — dados de jogadores em tempo real
- **Deploy** — Oracle Cloud Always Free (systemd)

---

## Estrutura do Código

```
main.py          — Entry point, classe MeuBot, global_check, eventos globais
config.py        — Variáveis de ambiente (.env) com validação obrigatória
database.py      — Cliente Supabase global (singleton)
utils.py         — Helpers: idiomas FF, patentes, veterano, permissão gestão
cogs/
  admin.py       — /configurar, /painel (UI completo com selects/modals/views)
  ajuda.py       — /ajuda com paginação por categorias
  usuarios.py    — /entrar (radar de idioma), /desvincular, /perfil
  gestao.py      — /dar_cargo, /remover_cargo, /limpar, /limpar_membro
  warns.py       — /dar_warn, /remover_warn, /lista_warns
  ranking.py     — /ranking_guilda, /meu_ranking, /atualizar_ranking
  torneios.py    — Torneios Solo/Duo/Trio/Squad com brackets e auto-advance
  notificacoes.py — /verificar_membros + task 6h para membros que saíram
  boas_vindas.py — Embed automática com {user} e {membros}
  anti_raid.py   — Rate-limit de joins com lock temporário
  pesquisa.py    — /pesquisar com limite 3/dia por user
  convites.py    — Tracking de convites com cache de invites
```

---

## Banco de Dados (Supabase)

### Tabelas principais usadas
- **servidores** — config base: guilda FF, cargo, canal, gestão, email admin
- **membros_verificados** — membros verificados com UID, nick, log_message_id
- **warns_config** — max_warns, dias_expiracao, habilitado, canal_notificacoes
- **warns** — advertências individuais com expiração
- **boas_vindas_config** — título, descrição, cor, canal_id, habilitado
- **anti_raid_config** — limite_joins, duracao_lock, canal_alertas, habilitado
- **notificacoes_config** — canal_atualizacoes, canal_membros, canal_temporada, habilitado
- **torneios** — nome, modo, status, max_participantes, premiacao
- **torneio_equipas** — nome, capitão, status
- **torneio_equipa_membros** — membros, aprovado
- **torneio_partidas** — rodada, jogadores, vencedor, status
- **ranking_cache** — cache de pontos BR por membro
- **convites** — convidador, convidado, data
- **convites_config** — habilitado, canal_notificacoes
- **codigos_seguranca** — códigos temporários para alterar guilda FF
- **pesquisa_diaria** — contador de pesquisas por dia
- **torneios_config** — canal_vitorias

### SQL extra fornecido
- `pesquisa_diaria`, `versao_jogo`, `convites`, `convites_config`

---

## Arquitetura & Fluxos Principais

### Verificação (/entrar)
1. Modal pede UID FF
2. API Vercel valida guilda do jogador
3. Radar: polling a cada 10s por até 5min para detectar mudança de idioma
4. Ao detectar → entrega cargo, guarda dados, envia DM, log no canal
5. Background task com `asyncio.create_task` + `discord.ui.View` persistente

### Global Check
- Verifica se servidor está registado (`/configurar`)
- Verifica se user está verificado ou é dono
- Aplica a TODOS os slash commands (exceto `/configurar`, `/entrar`)

### Painel (/painel)
- Menu principal com `discord.ui.select`
- Submenus: Base, Warns, Boas-Vindas, Anti-Raid, Notificações, Torneios, Ranking, Stats
- Views persistentes com `custom_id` para sobreviver a restarts
- Modais para configurar valores numéricos

### Torneios
1. Admin cria torneio (modal)
2. Capitães criam equipas → DMs com aprovação
3. Admin inicia → valida aprovações + presença no servidor
4. Brackets gerados com `random.shuffle`
5. Admin regista resultado → auto-advance para próxima rodada
6. Campeão → DMs + canal de vitórias → delete de todos os dados

### Anti-Raid
- `defaultdict(list)` para tracking de joins por servidor
- Lock em memória com timestamp de expiração
- Expulsa membros durante lock + alerta no canal

### Notificações Automáticas
- Task `@tasks.loop(hours=6)` verifica todos os servidores com notificações ativadas
- Para cada membro verificado → consulta API Vercel → detecta quem saiu da guilda
- Envia embed no canal configurado

---

## Pontos Positivos
- Cogs bem separados por domínio
- UI rica com Views/Modals persistentes
- Sistema de radar de verificação inovador
- Cache de ranking para evitar rate limits
- Retry logic com backoff exponencial na API
- Deploy documentado com systemd

---

## Problemas Críticos / Riscos

### Segurança
1. **Token exposto no .env** — O `.env` contém tokens reais e está no git (commit history preserva). Precisa de `.gitignore` efetivo + rotatividade de tokens.
2. **Service Role Key no cliente** — O bot usa `SUPABASE_SERVICE_ROLE_KEY` diretamente no cliente. Bypassa RLS completamente. Qualquer XSS ou injeção no Discord pode ler/escrever tudo.
3. **Race condition em pesquisa_diaria** — `select` → `update/insert` não é atómico. Dois users a pesquisar ao mesmo tempo podem duplicar contador.
4. **Rate limit da API Vercel** — Sem cache distribuído, múltiplos servidores com muitos membros vão bater no rate limit. `fetch_api` em `ranking.py` faz requests sequenciais sem paralelização.

### Bugs Potenciais
5. **Anti-raid em memória** — `self.join_tracker` e `self.locked_servers` resetam ao reiniciar o bot. Raids durante restart não são detetadas.
6. **Torunament ID hardcoded delete** — No `torneio_resultado`, quando há campeão, faz `delete` em `torneio_inscritos` que nunca foi criado neste fluxo.
7. **`calcular_patente` duplicado** — Definida em `utils.py`, `usuarios.py`, `ranking.py`, `pesquisa.py`. Manutenibilidade.
8. **`log_sart` duplicado** — Definida em `admin.py`, `usuarios.py`, `anti_raid.py`. Inconsistência de formatação.
9. **Botões DM sem view registada** — `ViewAprovacaoEquipa` no `torneios.py` usa `custom_id` mas não é adicionada via `bot.add_view`. Só funciona se o DM for enviado enquanto o bot está online.
10. **`on_member_remove` vazio** — No `anti_raid.py`, o listener existe mas está `pass`. Não faz nada.
11. **Erro silencioso em `ler_sub`** — `admin.py:ler_sub` tem `except: return {}` que captura tudo, incluindo erros de conexão.
12. **Kick em locked servers sem verificar permissão** — `anti_raid.py:103` faz `member.kick()` sem verificar se o bot tem permissão de kick.
13. **SQL injection potencial** — IDs são convertidos para string mas não sanitizados para SQL. Supabase client usa prepared statements, mas queries dinâmicas em `eq` são seguras apenas se os inputs forem válidos.
14. **`capa do bot.png` no repo** — Ficheiro binário grande no git. Deveria estar no `.gitignore` ou usar Git LFS.

### Performance
15. **N+1 queries em ranking** — Para cada membro, faz uma query à API Vercel sequencialmente. Com 50 membros, demora minutos.
16. **Task de notificações 6h** — Itera todos os membros de todos os servidores sequencialmente. Pode demorar muito e causar timeout na task.
17. **Cache de invites em memória** — `self._invites_cache` perde-se no restart. Convites criados enquanto o bot estava offline não são detectados.
18. **Sem paralelização** — A API Vercel suporta múltiplos requests, mas o bot faz sempre sequencial (`await` em loop).

### Manutenibilidade
19. **Configuração espalhada** — `warns_config` existe tanto em `admin.py` (ler_sub) como em `warns.py`. `boas_vindas_config` tanto em `admin.py` como em `boas_vindas.py`.
20. **Permissão duplicada** — `verificar_permissao_gestao` existe em `utils.py`, `gestao.py`, `warns.py`.
21. **Falta de typing** — Sem type hints na maioria das funções.
22. **Falta de testes** — Nenhum ficheiro de teste.

---

## Recomendações Prioritárias

### Curto Prazo (segurança)
1. Rodar `DISCORD_TOKEN` e `SUPABASE_SERVICE_ROLE_KEY` — tokens foram expostos no `.env` no repositório
2. Adicionar `.env` ao `.gitignore` se não estiver (está, mas o commit inicial pode ter ficado)
3. Usar `supabase.postgrest_client` com RLS ou mover lógica sensível para Edge Functions
4. Adicionar mutex/lock nas operações de `pesquisa_diaria` (ou usar `upsert` com condição)

### Médio Prazo (estabilidade)
5. Adicionar cache persistente para invites (Redis ou tabela no Supabase)
6. Paralelizar requests à API Vercel com `asyncio.gather` + semáforo
7. Persistir estado do anti-raid em vez de memória
8. Adicionar logging estruturado em vez de prints
9. Remover código morto e duplicações (DRY)

### Longo Prazo (escalabilidade)
10. Adicionar testes unitários e de integração
11. Considerar sharding se o bot crescer para 100+ servidores
12. Adicionar métricas e monitorização (Prometheus + Grafana, ou Sentry)
13. Migrar configs para um schema mais consistente (ex: uma tabela `config` JSONB)

---

## Métricas do Código
- **Linhas totais:** ~2.800
- **Ficheiros Python:** 13
- **Cogs:** 11
- **Comandos slash:** ~20
- **Views/Modais:** ~20
- **Dependências externas:** 4 (discord.py, supabase, aiohttp, python-dotenv)

---

## Estado de Deploy
- Repositório: `github.com/silvio-blip/MeuBotFF`
- Infraestrutura: Oracle Cloud Always Free (ARM Ampere A1)
- Process manager: systemd (`meubot.service`)
- Guia de deploy: `DEPLOY.md` (255 linhas, bem documentado)
