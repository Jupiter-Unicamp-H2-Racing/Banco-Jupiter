-- Migration aditiva para ambientes que ja possuem o schema inicial.
-- Valores monetarios sao centavos inteiros (BIGINT).
CREATE TABLE IF NOT EXISTS account (
    id BIGSERIAL PRIMARY KEY,
    account_key CHAR(36) NOT NULL UNIQUE,
    balance BIGINT NOT NULL DEFAULT 0,
    tier_code VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    monthly_free_transfers_limit INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_account_balance_nonnegative CHECK (balance >= 0),
    CONSTRAINT ck_account_free_limit_nonnegative CHECK (monthly_free_transfers_limit >= 0)
);

CREATE TABLE IF NOT EXISTS "transaction" (
    id BIGSERIAL PRIMARY KEY,
    transaction_key CHAR(36) NOT NULL UNIQUE,
    source_account_id BIGINT NOT NULL REFERENCES account(id),
    destination_account_id BIGINT NOT NULL REFERENCES account(id),
    amount BIGINT NOT NULL,
    fee_amount BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_transaction_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_transaction_fee_nonnegative CHECK (fee_amount >= 0),
    CONSTRAINT ck_transaction_accounts_different CHECK (source_account_id <> destination_account_id)
);

CREATE INDEX IF NOT EXISTS ix_transaction_source_created_at
    ON "transaction" (source_account_id, created_at);
