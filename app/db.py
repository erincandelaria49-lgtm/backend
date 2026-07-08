from __future__ import annotations

import socket

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
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

engine_url = database_url
if is_postgres:
    try:
        parsed_url = make_url(database_url)
        hostname = parsed_url.host
        if hostname and parsed_url.query.get("hostaddr") is None:
            ipv4_addresses = [
                result[4][0]
                for result in socket.getaddrinfo(hostname, parsed_url.port or 5432, socket.AF_INET, socket.SOCK_STREAM)
            ]
            if ipv4_addresses:
                query = dict(parsed_url.query)
                query["hostaddr"] = ipv4_addresses[0]
                engine_url = str(parsed_url.set(query=query))
    except OSError:
        engine_url = database_url

engine = create_engine(
    engine_url,
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
