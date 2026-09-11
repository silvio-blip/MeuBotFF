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

-- Economia do servidor (moedas por ação)
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

-- Cooldown do daily por usuário por servidor por dia
CREATE TABLE IF NOT EXISTS economia_daily (
  user_id TEXT,
  servidor_id TEXT,
  data TEXT,
  usado BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (user_id, servidor_id, data)
);
ALTER TABLE economia_daily DISABLE ROW LEVEL SECURITY;

-- Sistema de música (DJ, canal de comandos, cargo musica)
CREATE TABLE IF NOT EXISTS musica_config (
  guilda_id TEXT PRIMARY KEY,
  canal_comandos TEXT,
  cargo_musica_id TEXT,
  habilitado BOOLEAN DEFAULT TRUE
);
ALTER TABLE musica_config DISABLE ROW LEVEL SECURITY;

-- Sistema de palavrões (timeout por conteúdo impróprio)
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

-- Sistema de embeds personalizados
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
