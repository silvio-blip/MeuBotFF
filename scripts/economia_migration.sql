-- Migração: sistema de economia/moedas por servidor
-- Adiciona coluna moedas na tabela membros_verificados
ALTER TABLE membros_verificados ADD COLUMN IF NOT EXISTS moedas INT DEFAULT 0;

-- Configuração de economia por servidor
CREATE TABLE IF NOT EXISTS economia_config (
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
ALTER TABLE economia_config DISABLE ROW LEVEL SECURITY;

-- Cooldown do daily por usuário por servidor por dia
CREATE TABLE IF NOT EXISTS economia_daily (
  user_id TEXT,
  servidor_id TEXT,
  data TEXT,
  usado BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (user_id, servidor_id, data)
);
ALTER TABLE economia_daily DISABLE ROW LEVEL SECURITY;
