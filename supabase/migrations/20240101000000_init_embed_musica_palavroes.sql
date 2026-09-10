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
-- Sistema de Música: canal de comandos, cargo DJ, toggle
CREATE TABLE IF NOT EXISTS musica_config (
  guilda_id TEXT PRIMARY KEY,
  canal_comandos TEXT,
  cargo_musica_id TEXT,
  habilitado BOOLEAN DEFAULT TRUE
);
ALTER TABLE musica_config DISABLE ROW LEVEL SECURITY;
-- Sistema de Palavrões: timeout, alertas e exceções
CREATE TABLE IF NOT EXISTS palavroes_config (
  guilda_id TEXT PRIMARY KEY,
  duracao_timeout INT DEFAULT 300,
  canal_alertas TEXT,
  excluir_cargos TEXT[] DEFAULT '{}',
  excluir_canais TEXT[] DEFAULT '{}',
  palavras_personalizadas TEXT[] DEFAULT '{}',
  deletar_mensagem BOOLEAN DEFAULT TRUE,
  aviso_canal BOOLEAN DEFAULT FALSE,
  habilitado BOOLEAN DEFAULT FALSE
);
ALTER TABLE palavroes_config DISABLE ROW LEVEL SECURITY;
