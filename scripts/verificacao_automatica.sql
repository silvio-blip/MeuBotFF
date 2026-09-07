CREATE TABLE IF NOT EXISTS verificacao_automatica_config (
    guilda_id TEXT PRIMARY KEY,
    habilitado BOOLEAN DEFAULT TRUE,
    canal_verificacao_id TEXT,
    ultima_verificacao TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_verificacao_automatica_guilda ON verificacao_automatica_config(guilda_id);

COMMENT ON TABLE verificacao_automatica_config IS 'Configuração da verificação automática de membros na guilda FF';
COMMENT ON COLUMN verificacao_automatica_config.habilitado IS 'Se a verificação automática está ativada';
COMMENT ON COLUMN verificacao_automatica_config.canal_verificacao_id IS 'Canal do Discord onde logs de verificação são enviados';
COMMENT ON COLUMN verificacao_automatica_config.ultima_verificacao IS 'Última vez que a verificação rodou';
