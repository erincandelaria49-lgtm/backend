from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import PortfolioSettings, User
from app.routers.users import delete_project_stage_proof
from app.schemas import ProjectStageProofDeleteIn


def test_delete_final_stage_proof_clears_proof_feedback_thread():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        user = User(
            github_id="gh-1",
            username="student1",
            avatar_url="https://example.com/avatar.png",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        proof_url = "https://example.com/uploads/10_1779554289_example_of_certificate.jpg"
        settings = PortfolioSettings(
            user_id=user.id,
            project_learning_path_baseline={
                "demo-repo": {
                    "repo_name": "demo-repo",
                    "stage_proof_counts": {"Stage 1": 1},
                    "stage_progress_updates": {
                        "Stage 1": {
                            "final_proof_items": [
                                {"name": "Final proof", "url": proof_url, "kind": "image"},
                            ],
                            "admin_feedback_by_proof": {
                                proof_url: {
                                    "proof_url": proof_url,
                                    "proof_name": "Final proof",
                                    "latest_feedback": "Please improve this proof.",
                                    "feedback_by": "admin1",
                                    "updated_at": "2026-05-24T00:00:00+00:00",
                                    "thread": [
                                        {
                                            "feedback": "Please improve this proof.",
                                            "by": "admin1",
                                            "role": "admin",
                                            "updated_at": "2026-05-24T00:00:00+00:00",
                                            "proof_url": proof_url,
                                            "proof_name": "Final proof",
                                        }
                                    ],
                                }
                            },
                        }
                    },
                }
            },
        )
        db.add(settings)
        db.commit()

        result = delete_project_stage_proof(
            ProjectStageProofDeleteIn(repo_name="demo-repo", stage_title="Stage 1", proof_url=proof_url),
            db=db,
            current_user=user,
        )

        db.refresh(settings)
        stage_update = settings.project_learning_path_baseline["demo-repo"]["stage_progress_updates"]["Stage 1"]

        assert result["final_proof_items"] == []
        assert result["admin_feedback_by_proof"] == {}
        assert stage_update["final_proof_items"] == []
        assert stage_update["admin_feedback_by_proof"] == {}
        assert settings.project_learning_path_baseline["demo-repo"]["stage_proof_counts"] == {}
    finally:
        db.close()
