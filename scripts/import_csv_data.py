"""Import exported application CSVs into Supabase without overwriting existing rows."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2
from psycopg2 import sql


CSV_ROOT = Path(r"C:\Users\Admin\Downloads\DATA ON GITHUB STUDENT")
csv.field_size_limit(10_000_000)
TABLE_ORDER = [
    "users",
    "admin_accounts",
    "repos",
    "practice_dimensions",
    "career_suggestions",
    "badges",
    "portfolio_settings",
    "engagement_commits",
    "learning_progress",
    "learning_paths",
    "learning_path_stages",
    "xp_history",
    "login_activity",
    "certificate_records",
    "recommendation_actions",
    "activity_logs",
]


def load_database_url() -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    values: dict[str, str] = {}
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return os.getenv("DATABASE_URL") or values.get("DATABASE_URL", "")


def import_table(cur, table_name: str, csv_path: Path) -> tuple[int, int]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        source_count = 1 + sum(1 for _ in reader)

    staging = f"_csv_import_{table_name}"
    cur.execute(sql.SQL("drop table if exists {} ").format(sql.Identifier(staging)))
    cur.execute(
        sql.SQL("create temporary table {} (like public.{} including defaults) on commit drop")
        .format(sql.Identifier(staging), sql.Identifier(table_name))
    )
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        cur.copy_expert(
            sql.SQL("copy {} ({}) from stdin with (format csv, header true, null '')")
            .format(sql.Identifier(staging), sql.SQL(", ").join(sql.Identifier(c) for c in columns))
            .as_string(cur),
            handle,
        )
    cur.execute(
        sql.SQL("insert into public.{} ({}) select {} from {} on conflict do nothing")
        .format(
            sql.Identifier(table_name),
            sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            sql.Identifier(staging),
        )
    )
    return source_count, cur.rowcount


def main() -> None:
    database_url = load_database_url()
    if not database_url or "<" in database_url or "YOUR_" in database_url:
        raise SystemExit("DATABASE_URL is missing or still a placeholder in backend_repo/.env")
    if not CSV_ROOT.exists():
        raise SystemExit(f"CSV directory not found: {CSV_ROOT}")

    connection = psycopg2.connect(database_url)
    connection.autocommit = False
    try:
        with connection.cursor() as cur:
            for table_name in TABLE_ORDER:
                csv_path = CSV_ROOT / f"{table_name}_rows.csv"
                if not csv_path.exists():
                    print(f"SKIP {table_name}: CSV not found")
                    continue
                source_count, inserted_count = import_table(cur, table_name, csv_path)
                print(f"{table_name}: {inserted_count} inserted, {source_count - 1 - inserted_count} already existed/conflicted")
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
