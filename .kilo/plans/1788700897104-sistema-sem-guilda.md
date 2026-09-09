# 1788700897104-sistema-sem-guilda.md

## Objetivo
Permitir que o bot funcione em servidores que **não têm guilda FF configurada**. O `/entrar` e `/perfil` devem funcionar mesmo sem verificação de guilda.

## Funcionamento
1. No `/configurar`, o admin pode escolher se o servidor exige guilda ou não
2. Se **não exige guilda**, o `/entrar` pula a verificação de clanId e vai direto para o radar
3. O `/perfil` funciona normalmente, mostrando dados do jogo

## Arquivos Afetados
- `cogs/admin.py` — painel, view, toggle, verificação manual e loop automático
- `cogs/perfil.py` ou `cogs/ proximity` — lógica de verificação e remoção
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