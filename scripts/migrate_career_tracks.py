"""Rebuild personalized career suggestions for existing students once.

The migration is dry-run by default. Pass --apply only after reviewing the
preview and confirming that DATABASE_URL points at the intended Supabase DB.
"""

from __future__ import annotations

import argparse

from app.db import SessionLocal
from app.models import ActivityLog, CareerSuggestion, PracticeDimension, Repo, User
from app.services.inference import _fallback_practice_and_careers


MIGRATION_EVENT = "career_tracks_v2_migrated"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write the migration to the database")
    args = parser.parse_args()

    db = SessionLocal()
    changed = 0
    try:
        students = db.query(User).filter(User.role == "student").order_by(User.id.asc()).all()
        for student in students:
            already_migrated = (
                db.query(ActivityLog)
                .filter(
                    ActivityLog.user_id == student.id,
                    ActivityLog.event == MIGRATION_EVENT,
                )
                .first()
                is not None
            )
            if already_migrated:
                continue

            repos = db.query(Repo).filter(Repo.user_id == student.id).all()
            summaries = [
                {
                    "name": repo.name,
                    "description": repo.description,
                    "language": repo.language,
                    "languages": repo.languages,
                    "topics": repo.topics,
                    "code_signals": repo.code_signals or {},
                    "commit_count": repo.commit_count,
                }
                for repo in repos
            ]
            result = _fallback_practice_and_careers(summaries)
            suggestions = result.get("career_suggestions", [])
            print(f"{student.id}: {student.username} -> {[item['title'] for item in suggestions[:5]]}")

            if not args.apply:
                continue

            db.query(PracticeDimension).filter(PracticeDimension.user_id == student.id).delete()
            db.query(CareerSuggestion).filter(CareerSuggestion.user_id == student.id).delete()
            for item in result.get("practice_dimensions", []):
                db.add(
                    PracticeDimension(
                        user_id=student.id,
                        label=item["label"],
                        confidence=item["confidence"],
                        evidence=item.get("evidence", []),
                    )
                )
            for item in suggestions:
                db.add(
                    CareerSuggestion(
                        user_id=student.id,
                        title=item["title"],
                        confidence=item["confidence"],
                        reasoning=item["reasoning"],
                    )
                )
            db.add(
                ActivityLog(
                    user_id=student.id,
                    event=MIGRATION_EVENT,
                    meta={"version": 2, "suggestion_count": len(suggestions)},
                )
            )
            changed += 1

        if args.apply:
            db.commit()
            print(f"Applied career track migration to {changed} students.")
        else:
            db.rollback()
            print("Dry run only. Re-run with --apply to write these results.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
