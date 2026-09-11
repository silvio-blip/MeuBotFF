-- Sistema de Palavrões: timeout, alertas, avisos e exceções
CREATE TABLE IF NOT EXISTS palavroes_config (
  guilda_id TEXT PRIMARY KEY,
  duracao_timeout INT DEFAULT 300,
  avisos_antes_timeout INT DEFAULT 0,
  canal_alertas TEXT,
  excluir_cargos TEXT[] DEFAULT '{}',
  excluir_canais TEXT[] DEFAULT '{}',
  palavras_personalizadas TEXT[] DEFAULT '{}',
  deletar_mensagem BOOLEAN DEFAULT TRUE,
  aviso_canal BOOLEAN DEFAULT FALSE,
  habilitado BOOLEAN DEFAULT FALSE
);
ALTER TABLE palavroes_config DISABLE ROW LEVEL SECURITY;

-- Tabela de warnings de palavrões por usuário
CREATE TABLE IF NOT EXISTS palavras_warnings (
  guilda_id TEXT,
  user_id TEXT,
  contador INT DEFAULT 1,
  ultimo_alert TEXT,
  PRIMARY KEY (guilda_id, user_id)
);
ALTER TABLE palavras_warnings DISABLE ROW LEVEL SECURITY;

-- Para servidores já existentes: adiciona colunas faltantes
ALTER TABLE palavroes_config ADD COLUMN IF NOT EXISTS avisos_antes_timeout INT DEFAULT 0;
ALTER TABLE palavroes_config ADD COLUMN IF NOT EXISTS palavras_personalizadas TEXT[] DEFAULT '{}';