from app.services.gamification import compute_xp_and_badges


def test_compute_xp_and_badges_returns_expected_shape():
    repos = [
        {
            "name": "demo",
            "language": "Python",
            "languages": ["Python", "TypeScript"],
            "stars": 3,
            "commit_count": 25,
        }
    ]
    result = compute_xp_and_badges(repos)
    assert result.xp > 0
    assert result.level >= 1
    assert result.next_level_xp >= 500
    assert isinstance(result.badges, list)
    assert len(result.badges) >= 180


def test_badges_include_first_repo():
    repos = [{"name": "demo", "language": "Python", "languages": ["Python"], "stars": 0, "commit_count": 1}]
    result = compute_xp_and_badges(repos)
    labels = {item["label"]: item for item in result.badges}
    assert "First Repo" in labels
    assert labels["First Repo"]["achieved"] is True
