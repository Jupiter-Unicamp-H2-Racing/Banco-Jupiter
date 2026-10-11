
from models import Base


def test_customer_email_has_only_case_insensitive_unique_index():
    customer = Base.metadata.tables["customer"]
    assert not customer.c.email.unique
    indexes = {index.name: index for index in customer.indexes}
    assert "uq_customer_email_lower" in indexes
    assert "lower(email)" in str(indexes["uq_customer_email_lower"].expressions[0]).lower()


def test_t9_required_indexes_are_in_model_metadata():
    expected = {
        "ix_customer_status_id",
        "ix_customer_created_at_id",
        "ix_customer_status_event_customer_id",
    }
    actual = {index.name for table in Base.metadata.tables.values() for index in table.indexes}
    assert expected <= actual


def test_alembic_initial_migration_exists():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    versions = root / "migrations" / "versions"
    assert versions.is_dir() and any(versions.glob("*.py"))


def test_actual_database_schema_matches_model_metadata():
    import os
    import pytest
    from sqlalchemy import create_engine, inspect

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("Defina DATABASE_URL para comparar o schema real com os models.")
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        model_tables = set(Base.metadata.tables)
        actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert actual_tables == model_tables
        for table_name, table in Base.metadata.tables.items():
            actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert actual_columns == set(table.columns.keys()), table_name
            actual_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            expected_indexes = {index.name for index in table.indexes if index.name}
            assert expected_indexes <= actual_indexes, table_name
    finally:
        engine.dispose()
