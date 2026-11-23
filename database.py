
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./attendpro.db",
)

# Render PostgreSQL compatibility with psycopg 3
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

engine_options = {
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {
        "check_same_thread": False
    }

engine = create_engine(
    DATABASE_URL,
    **engine_options,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import all models before creating database tables.
    import models
    import users
    import audit

    # Create tables that do not exist yet.
    Base.metadata.create_all(bind=engine)

    # Safely add Telegram account linking column to existing users table.
    inspector = inspect(engine)

    if "users" not in inspector.get_table_names():
        raise RuntimeError("Users table was not created")

    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    with engine.begin() as connection:
        if "telegram_user_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN telegram_user_id VARCHAR(40)"
                )
            )

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ix_users_telegram_user_id "
                "ON users (telegram_user_id)"
            )
        )
