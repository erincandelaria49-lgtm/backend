import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db import Base, engine
from app.routers import auth, users, admin, analytics
from app.routers import login_analytics


logger = logging.getLogger(__name__)


def _should_run_runtime_schema_init() -> bool:
    return os.getenv("RUN_RUNTIME_SCHEMA_INIT", "").strip().lower() == "true"


def _ensure_certificate_record_columns():
    try:
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("certificate_records")}
    except SQLAlchemyError as exc:
        logger.warning("Skipping certificate schema sync because the database is unavailable: %s", str(exc)[:240])
        return

    statements: list[str] = []
    if "proof_type" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN proof_type VARCHAR(40)")
    if "certificate_page_url" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN certificate_page_url TEXT")
    if "student_note" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN student_note TEXT")
    if "suggestion_track_id" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN suggestion_track_id VARCHAR(160)")
    if "suggestion_module_url" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN suggestion_module_url TEXT")
    if "completion_locked" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN completion_locked BOOLEAN DEFAULT FALSE")
    if "completion_reward_xp" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN completion_reward_xp INTEGER")
    if "rewarded_at" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN rewarded_at TIMESTAMP")
    if "hidden_from_student" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN hidden_from_student BOOLEAN DEFAULT FALSE")
    if "verified_at" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN verified_at TIMESTAMP")
    if "reviewer_id" not in columns:
        statements.append("ALTER TABLE certificate_records ADD COLUMN reviewer_id INTEGER")
    if not statements:
        return
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    except SQLAlchemyError as exc:
        logger.warning("Skipping certificate schema migration because the database is unavailable: %s", str(exc)[:240])


def _ensure_runtime_schema():
    try:
        if settings.app_env.strip().lower() == "production":
            logger.info("Running runtime schema initialization in production to ensure the database schema exists.")
        Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_repos_user_id ON repos (user_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_certificate_records_suggestion_track_id ON certificate_records (suggestion_track_id)"))
        _ensure_certificate_record_columns()
    except SQLAlchemyError as exc:
        logger.warning("Database initialization skipped during startup: %s", str(exc)[:240])

app = FastAPI(title="LSPU AI-Enhanced Gamified Student Portfolio Platform API")

is_production = settings.app_env.strip().lower() == "production"
frontend_origins = {
    settings.frontend_url.rstrip("/"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_production else sorted(frontend_origins),
    allow_origin_regex=None if is_production else (
        r"^http://(localhost|127\.0\.0\.1)(:\\d+)?$"
        r"|^https://([a-z0-9-]+\.)?vercel\.app$"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(login_analytics.router)


@app.on_event("startup")
def startup_event():
    if settings.app_env.strip().lower() == "production" and not _should_run_runtime_schema_init():
        logger.info("Skipping runtime schema initialization during startup in production.")
        return
    _ensure_runtime_schema()


@app.get("/health")
def health():
    return {"status": "ok"}

# Serve uploaded files from app/static/uploads at /static/uploads
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
