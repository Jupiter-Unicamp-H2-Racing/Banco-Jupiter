-- Indices para extratos de origem e destino, com desempate determinístico por id.
-- DROP torna a migration repetível mesmo se o índice antigo tiver a mesma chave.
DROP INDEX IF EXISTS ix_transaction_source_created_at;
CREATE INDEX IF NOT EXISTS ix_transaction_source_created_at
    ON "transaction" (source_account_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_transaction_destination_created_at
    ON "transaction" (destination_account_id, created_at DESC, id DESC);
