-- Sistema de Embeds Personalizados
CREATE TABLE IF NOT EXISTS embeds_config (
  guilda_id TEXT PRIMARY KEY,
  habilitado BOOLEAN DEFAULT FALSE
);
ALTER TABLE embeds_config DISABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS embed_configs (
  guilda_id TEXT,
  embed_id TEXT,
  nome TEXT,
  titulo TEXT,
  descricao TEXT,
  cor TEXT DEFAULT 'FFD700',
  thumbnail_url TEXT,
  imagem_url TEXT,
  banner_url TEXT,
  autor_nome TEXT,
  autor_icon TEXT,
  footer_text TEXT,
  footer_icon TEXT,
  campos TEXT,
  timestamp BOOLEAN DEFAULT FALSE,
  criado_por TEXT,
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (guilda_id, embed_id)
);
ALTER TABLE embed_configs DISABLE ROW LEVEL SECURITY;
