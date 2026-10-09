-- 1. Status específicos da entidade Cliente

CREATE TABLE customer_status (
    id SERIAL PRIMARY KEY,
    enumerator VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(enumerator)
);

INSERT INTO customer_status (enumerator)
VALUES
    ('pending_kyc'),
    ('active'),
    ('blocked'),
    ('inactive');


-- 2. Tabela de Clientes

CREATE TABLE customer (
    id SERIAL PRIMARY KEY,
    customer_key CHAR(36) NOT NULL,
    status_id INTEGER NOT NULL REFERENCES customer_status(id),

    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    document_number VARCHAR(18) NOT NULL,
    birthdate DATE NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(customer_key),
    UNIQUE(document_number),
    UNIQUE(email)
);


-- 3. Histórico Imutável de Mudanças de Status do Cliente

CREATE TABLE customer_status_event (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    status_id INTEGER NOT NULL REFERENCES customer_status(id),

    event_datetime TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Contas bancarias usadas pelo fluxo de transferencias.
-- Valores monetarios sao armazenados em centavos (BIGINT), nunca em ponto flutuante.
CREATE TABLE account (
    id BIGSERIAL PRIMARY KEY,
    account_key CHAR(36) NOT NULL UNIQUE,
    balance BIGINT NOT NULL DEFAULT 0,
    tier_code VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    monthly_free_transfers_limit INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_account_balance_nonnegative CHECK (balance >= 0),
    CONSTRAINT ck_account_free_limit_nonnegative CHECK (monthly_free_transfers_limit >= 0)
);

-- 5. Transferencias: fee_amount registra a tarifa efetivamente cobrada, inclusive zero.
CREATE TABLE "transaction" (
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

CREATE INDEX ix_transaction_source_created_at
    ON "transaction" (source_account_id, created_at);
