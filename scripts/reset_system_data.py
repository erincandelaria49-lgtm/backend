from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_backend_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_backend_env()

from app.db import SessionLocal
from app.models import (
    ActivityLog,
    AdminNote,
    Badge,
    CareerSuggestion,
    CertificateRecord,
    DailyQuestClaim,
    EngagementCommit,
    FccModuleProgress,
    LearningProgress,
    LoginActivity,
    PortfolioReview,
    PortfolioSettings,
    StudentGoal,
    PracticeDimension,
    ProjectValidation,
    RecommendationAction,
    Repo,
    SusSurveyResponse,
    User,
    WeeklyChallengeClaim,
    XpHistory,
    InterventionPlan,
)


STUDENT_ROLE_VALUES = ("student", "", None)


def main() -> None:
    session = SessionLocal()
    try:
        students = (
            session.query(User)
            .filter((User.role == "student") | (User.role == "") | (User.role.is_(None)))
            .all()
        )
        student_ids = [student.id for student in students]

        deleted: list[str] = []

        if student_ids:
            session.query(AdminNote).filter(AdminNote.student_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("admin_notes")
            session.query(ProjectValidation).filter(ProjectValidation.student_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("project_validations")
            session.query(PortfolioReview).filter(PortfolioReview.student_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("portfolio_reviews")
            session.query(InterventionPlan).filter(InterventionPlan.student_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("intervention_plans")
            session.query(CertificateRecord).filter(CertificateRecord.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("certificate_records")
            session.query(FccModuleProgress).filter(FccModuleProgress.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("fcc_module_progress")
            session.query(RecommendationAction).filter(RecommendationAction.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("recommendation_actions")
            session.query(EngagementCommit).filter(EngagementCommit.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("engagement_commits")
            session.query(LearningProgress).filter(LearningProgress.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("learning_progress")
            session.query(DailyQuestClaim).filter(DailyQuestClaim.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("daily_quest_claims")
            session.query(WeeklyChallengeClaim).filter(WeeklyChallengeClaim.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("weekly_challenge_claims")
            session.query(XpHistory).filter(XpHistory.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("xp_history")
            session.query(LoginActivity).filter(LoginActivity.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("login_activity")
            session.query(ActivityLog).filter(ActivityLog.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("activity_logs")
            session.query(Repo).filter(Repo.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("repos")
            session.query(Badge).filter(Badge.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("badges")
            session.query(PracticeDimension).filter(PracticeDimension.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("practice_dimensions")
            session.query(CareerSuggestion).filter(CareerSuggestion.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("career_suggestions")
            session.query(SusSurveyResponse).filter(SusSurveyResponse.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("sus_survey_responses")
            session.query(StudentGoal).filter(StudentGoal.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("student_goals")
            session.query(PortfolioSettings).filter(PortfolioSettings.user_id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("portfolio_settings")

            # Commit dependent-row cleanup first so parent user deletion is never blocked by stale references.
            session.commit()

            session.query(User).filter(User.id.in_(student_ids)).delete(synchronize_session=False)
            deleted.append("users")

        session.commit()
    finally:
        session.close()

    print("RESET_OK")
    print(f"students_deleted={len(student_ids)}")
    for name in deleted:
        print(name)


if __name__ == "__main__":
    main()
