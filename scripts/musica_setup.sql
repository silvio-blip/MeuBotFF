-- Sistema de Música: canal de comandos, cargo DJ, toggle
CREATE TABLE IF NOT EXISTS musica_config (
  guilda_id TEXT PRIMARY KEY,
  canal_comandos TEXT,
  cargo_musica_id TEXT,
  habilitado BOOLEAN DEFAULT TRUE
);
ALTER TABLE musica_config DISABLE ROW LEVEL SECURITY;
