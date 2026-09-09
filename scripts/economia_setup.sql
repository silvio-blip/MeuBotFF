-- ============================================
-- SISTEMA DE ECONOMIA/MOEDAS POR SERVIDOR
-- ============================================

-- 1. Adiciona coluna de moedas na tabela de membros verificados
ALTER TABLE membros_verificados ADD COLUMN IF NOT EXISTS moedas INT DEFAULT 0;

-- 2. Tabela de configuração de economia por servidor
CREATE TABLE IF NOT EXISTS economia_config (
  guilda_id TEXT PRIMARY KEY,
  moedas_entrada INT DEFAULT 10,
  moedas_convite INT DEFAULT 15,
  moedas_torneio_participar INT DEFAULT 20,
  moedas_torneio_vencer INT DEFAULT 100,
  moedas_daily INT DEFAULT 10,
  moedas_daily_min INT DEFAULT 5,
  moedas_daily_max INT DEFAULT 15,
  nome_moeda TEXT DEFAULT 'moedas',
  habilitado BOOLEAN DEFAULT TRUE
);
ALTER TABLE economia_config DISABLE ROW LEVEL SECURITY;

-- Caso a tabela já exista e não tenha as colunas novas
ALTER TABLE economia_config ADD COLUMN IF NOT EXISTS moedas_daily_min INT DEFAULT 5;
ALTER TABLE economia_config ADD COLUMN IF NOT EXISTS moedas_daily_max INT DEFAULT 15;
ALTER TABLE economia_config ADD COLUMN IF NOT EXISTS nome_moeda TEXT DEFAULT 'moedas';

-- 3. Tabela de cooldown do daily por usuário/servidor/dia
CREATE TABLE IF NOT EXISTS economia_daily (
  user_id TEXT,
  servidor_id TEXT,
  data TEXT,
  usado BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (user_id, servidor_id, data)
);
ALTER TABLE economia_daily DISABLE ROW LEVEL SECURITY;

-- 4. (Opcional) Índice para performance em consultas de moedas
CREATE INDEX IF NOT EXISTS idx_membros_verificados_servidor_moedas ON membros_verificados(id_servidor, moedas DESC);
