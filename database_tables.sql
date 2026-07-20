-- Tabela de limite de pesquisas diárias
CREATE TABLE IF NOT EXISTS pesquisa_diaria (
  user_id TEXT,
  data TEXT,
  contador INT DEFAULT 0,
  PRIMARY KEY (user_id, data)
);
ALTER TABLE pesquisa_diaria DISABLE ROW LEVEL SECURITY;

-- Tabela de versão do jogo
CREATE TABLE IF NOT EXISTS versao_jogo (
  guilda_id TEXT PRIMARY KEY,
  versao TEXT,
  canal_notificacoes TEXT
);
ALTER TABLE versao_jogo DISABLE ROW LEVEL SECURITY;

-- Tabela de convites
CREATE TABLE IF NOT EXISTS convites (
  id SERIAL PRIMARY KEY,
  convidador_id TEXT NOT NULL,
  convidado_id TEXT NOT NULL,
  guilda_id TEXT NOT NULL,
  data TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE convites DISABLE ROW LEVEL SECURITY;

-- Tabela de config de convites
CREATE TABLE IF NOT EXISTS convites_config (
  guilda_id TEXT PRIMARY KEY,
  canal_notificacoes TEXT,
  habilitado BOOLEAN DEFAULT TRUE
);
ALTER TABLE convites_config DISABLE ROW LEVEL SECURITY;
