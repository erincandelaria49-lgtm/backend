from app.models import User
from app.routers.auth import _registration_complete


def test_registration_is_incomplete_until_required_profile_fields_exist():
    user = User(
        github_id="123",
        username="newstudent",
        avatar_url="https://example.com/avatar.png",
    )

    assert _registration_complete(user) is False

    user.display_name = "New Student"
    user.student_id = "2024-0001"
    user.program = "BSCS"
    user.year_level = "1st Year"

    assert _registration_complete(user) is True
