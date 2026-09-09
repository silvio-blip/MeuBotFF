-- Migração: adicionar coluna moedas na tabela membros_verificados
ALTER TABLE membros_verificados ADD COLUMN IF NOT EXISTS moedas INT DEFAULT 0;
