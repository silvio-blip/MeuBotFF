# 1788700897104-remocao-automatica-cargo-sistema.md

## Objetivo
Criar sistema automático que remove o cargo de registro de usuários que saíram da guilda FF, com controle no painel admin.

## Funcionamento
1. Bot roda a cada 24h (horário de Portugal)
2. Pega todos os UIDs FF registrados no servidor
3. Verifica se esses UIDs ainda estão na guilda FF configurada
4. Se não estiverem, remove apenas o cargo de registro do usuário no Discord
5. Admin pode ativar/desativar isso no painel admin

## Arquivos Afetados
- `cogs/usuarios.py` — lógica de verificação e remoção
- `cogs/admin.py` ou novo cog `cogs/verificacao_automatica.py` — painel e task
- `database.py` ou SQL — nova tabela/configuração

## Tarefas

### 1. Banco de dados
Criar tabela `servidores_verificacao` com:
- `guilda_id` (PK)
- `canal_verificacao_id` (opcional, para logs)
- `habilitado` (boolean, default true)
- `ultima_verificacao` (timestamp)

### 2. Painel admin
Adicionar no `/painel` uma seção "Verificação Automática" com:
- Toggle ativar/desativar
- Selecionar canal de logs (opcional)
- Botão "Verificar Agora" (manual)

### 3. Lógica de verificação
- Task `@tasks.loop(hours=24)` 
- Para cada servidor com verificação ativada:
  - Buscar todos membros verificados
  - Para cada membro, consultar API FF
  - Se `clanId` != guilda configurada → remover cargo
  - Log no canal configurado

### 4. Cargo a remover
Usar o `cargo_id` já existente na tabela `servidores` (é o cargo de registro).

## Validação
- Testar com servidor de teste
- Confirmar que apenas remove cargo, não deleta dados
- Confirmar que respeita o toggle do painel
