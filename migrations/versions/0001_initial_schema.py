"""Create the initial Banco Jupiter schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("customer_status",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enumerator", sa.String(50), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.bulk_insert(sa.table("customer_status", sa.column("enumerator", sa.String())),
        [{"enumerator": name} for name in ("pending_kyc", "active", "blocked", "inactive")])
    op.create_table("customer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_key", sa.CHAR(36), nullable=False, unique=True),
        sa.Column("status_id", sa.Integer(), sa.ForeignKey("customer_status.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("document_number", sa.String(18), nullable=False, unique=True),
        sa.Column("birthdate", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_customer_status_id", "customer", ["status_id"])
    op.create_index("uq_customer_email_lower", "customer", [sa.text("lower(email)")], unique=True)
    op.create_index("ix_customer_created_at_id", "customer", [sa.text("created_at DESC"), sa.text("id DESC")])
    op.create_table("customer_status_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("status_id", sa.Integer(), sa.ForeignKey("customer_status.id"), nullable=False),
        sa.Column("event_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_customer_status_event_customer_id", "customer_status_event", ["customer_id"])
    op.create_table("account",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("account_key", sa.CHAR(36), nullable=False, unique=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("balance", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tier_code", sa.String(20), nullable=False, server_default="STANDARD"),
        sa.Column("monthly_free_transfers_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("balance >= 0", name="ck_account_balance_nonnegative"),
        sa.CheckConstraint("monthly_free_transfers_limit >= 0", name="ck_account_free_limit_nonnegative"))
    op.create_index("ix_account_customer_id", "account", ["customer_id"])
    op.create_table("transaction",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("transaction_key", sa.CHAR(36), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("source_account_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("destination_account_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("fee_amount", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("fee_account_id", sa.BigInteger(), sa.ForeignKey("account.id")),
        sa.Column("kind", sa.String(16), nullable=False, server_default="transfer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source_account_id", "idempotency_key", name="uq_transaction_source_idempotency"),
        sa.CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        sa.CheckConstraint("fee_amount >= 0", name="ck_transaction_fee_nonnegative"),
        sa.CheckConstraint("kind IN ('transfer', 'deposit', 'fee')", name="ck_transaction_kind"),
        sa.CheckConstraint("source_account_id <> destination_account_id", name="ck_transaction_accounts_different"))
    op.create_index("ix_transaction_source_created_at", "transaction", ["source_account_id", sa.text("created_at DESC"), sa.text("id DESC")])
    op.create_index("ix_transaction_destination_created_at", "transaction", ["destination_account_id", sa.text("created_at DESC"), sa.text("id DESC")])
    op.execute("""
        INSERT INTO customer (customer_key, status_id, name, email, document_number, birthdate)
        SELECT '00000000-0000-4000-8000-000000000002', id, 'Sistema - Receita de Tarifas',
               'fee-revenue@system.invalid', 'SYS-FEE-0001', DATE '2000-01-01'
        FROM customer_status WHERE enumerator = 'active'
        ON CONFLICT (customer_key) DO NOTHING
    """)
    op.execute("""
        INSERT INTO account (account_key, customer_id, balance, tier_code, monthly_free_transfers_limit)
        SELECT '00000000-0000-4000-8000-000000000001', id, 0, 'SYSTEM', 0
        FROM customer WHERE customer_key = '00000000-0000-4000-8000-000000000002'
        ON CONFLICT (account_key) DO NOTHING
    """)


def downgrade():
    op.drop_table("transaction")
    op.drop_index("ix_account_customer_id", table_name="account")
    op.drop_table("account")
    op.drop_index("ix_customer_status_event_customer_id", table_name="customer_status_event")
    op.drop_table("customer_status_event")
    op.drop_index("ix_customer_created_at_id", table_name="customer")
    op.drop_index("uq_customer_email_lower", table_name="customer")
    op.drop_index("ix_customer_status_id", table_name="customer")
    op.drop_table("customer")
    op.drop_table("customer_status")
