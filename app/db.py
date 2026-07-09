from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

connect_args = {}
database_url = str(settings.database_url or "")
is_postgres = database_url.startswith(("postgresql://", "postgresql+psycopg2://", "postgres://"))
if is_postgres and settings.database_sslmode:
    connect_args["sslmode"] = settings.database_sslmode
if is_postgres:
    connect_args["connect_timeout"] = 5
if is_postgres and settings.database_statement_timeout_ms:
    connect_args["options"] = f"-c statement_timeout={settings.database_statement_timeout_ms}"

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
    hide_parameters=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
