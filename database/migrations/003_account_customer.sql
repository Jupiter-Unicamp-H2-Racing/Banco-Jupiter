-- Associa contas a clientes. Migração aditiva e repetível.
-- Estratégia para contas legadas: não atribuímos clientes arbitrariamente.
-- Se houver contas, associe-as manualmente a um customer válido antes de
-- executar esta migração; ela aborta com mensagem clara se houver órfãs.
BEGIN;
ALTER TABLE account ADD COLUMN IF NOT EXISTS customer_id INTEGER;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM account WHERE customer_id IS NULL) THEN
        RAISE EXCEPTION 'Migração 003 abortada: existem contas sem customer_id. Associe cada conta a um customer antes de repetir.';
    END IF;
END $$;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_account_customer_id') THEN
        ALTER TABLE account ADD CONSTRAINT fk_account_customer_id
            FOREIGN KEY (customer_id) REFERENCES customer(id);
    END IF;
END $$;
ALTER TABLE account ALTER COLUMN customer_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_account_customer_id ON account(customer_id);
COMMIT;
