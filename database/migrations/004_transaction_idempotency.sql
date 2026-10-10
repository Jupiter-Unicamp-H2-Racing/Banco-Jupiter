BEGIN;

ALTER TABLE public."transaction"
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_transaction_source_idempotency'
          AND conrelid = 'public."transaction"'::regclass
    ) THEN
        ALTER TABLE public."transaction"
            ADD CONSTRAINT uq_transaction_source_idempotency
            UNIQUE (source_account_id, idempotency_key);
    END IF;
END;
$migration$;

COMMIT;