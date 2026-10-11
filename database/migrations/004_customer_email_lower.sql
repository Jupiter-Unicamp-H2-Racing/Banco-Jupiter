-- Garante unicidade de e-mail sem diferenciar maiúsculas/minúsculas.
BEGIN;
DO $$
BEGIN
    IF EXISTS (
        SELECT lower(email) FROM customer GROUP BY lower(email) HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Migração 004 abortada: existem e-mails duplicados por caixa. Normalize/corrija os e-mails antes de repetir.';
    END IF;
END $$;
UPDATE customer SET email = lower(email) WHERE email <> lower(email);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_email_lower ON customer (lower(email));
COMMIT;
