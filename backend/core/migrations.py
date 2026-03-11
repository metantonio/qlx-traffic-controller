import logging
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

logger = logging.getLogger("QLX-TC.Database.Migrations")

def get_current_version(engine: Engine) -> int:
    inspector = inspect(engine)
    if "schema_migrations" not in inspector.get_table_names():
        return 0
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"))
        row = result.fetchone()
        return row[0] if row else 0

def set_version(engine: Engine, version: int):
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": version})
        conn.commit()

def apply_migrations(engine: Engine):
    """
    Applies incremental database migrations.
    """
    # Create migrations table if it doesn't exist
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"))
        conn.commit()

    current_version = get_current_version(engine)
    logger.info(f"Current database schema version: {current_version}")

    # Migration 1: Initial creation (handled by create_all, but we mark it)
    if current_version < 1:
        logger.info("Marking schema version 1 (Initial)")
        set_version(engine, 1)
        current_version = 1

    # Migration 2: Handled by create_all for AllowedDirectories table
    # If we need to add columns to existing tables, we do it here.
    # For now, let's just mark the version after create_all runs.
    if current_version < 2:
        logger.info("Migrating to version 2 (Allowed Directories)")
        # DbAllowedDirectory is a new table, so Base.metadata.create_all handles it.
        set_version(engine, 2)
        current_version = 2

    logger.info(f"Database schema is up to date at version {current_version}")
