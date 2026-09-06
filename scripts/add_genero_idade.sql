-- Adicionar colunas de gênero e idade à tabela de membros verificados
ALTER TABLE membros_verificados 
ADD COLUMN IF NOT EXISTS genero TEXT DEFAULT 'Prefiro não dizer',
ADD COLUMN IF NOT EXISTS idade INTEGER DEFAULT 0;

-- Índice opcional para consultas frequentes por gênero
CREATE INDEX IF NOT EXISTS idx_membros_verificados_genero ON membros_verificados(genero);

-- Comentários para documentação
COMMENT ON COLUMN membros_verificados.genero IS 'Gênero do membro: Masculino, Feminino, Outro ou Prefiro não dizer';
COMMENT ON COLUMN membros_verificados.idade IS 'Idade do membro em anos';
