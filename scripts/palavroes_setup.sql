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
