import datetime as dt
from collections import defaultdict
from typing import Iterable
import requests

from app.models import EngagementCommit, LearningProgress, Repo, User, XpHistory

GITHUB_API = "https://api.github.com"


def _repo_full_name(user: User, repo: Repo) -> str:
    return f"{user.username}/{repo.name}"


def _github_get(url: str, token: str | None = None) -> requests.Response:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(url, headers=headers, timeout=8)


def fetch_github_commit_activity(user: User, repos: Iterable[Repo]) -> list[int]:
    weekly_totals = None
    for repo in repos:
        full_name = _repo_full_name(user, repo)
        try:
            response = _github_get(f"{GITHUB_API}/repos/{full_name}/stats/participation", user.github_token)
        except requests.RequestException:
            continue
        if response.status_code == 202:
            # GitHub is still computing stats; skip this repo for now.
            continue
        if response.status_code != 200:
            continue
        data = response.json()
        repo_weeks = data.get("all")
        if not isinstance(repo_weeks, list):
            continue
        if weekly_totals is None:
            weekly_totals = [0 for _ in range(len(repo_weeks))]
        for idx, value in enumerate(repo_weeks):
            weekly_totals[idx] += int(value or 0)

    if weekly_totals is None:
        weekly_totals = []
    return weekly_totals


def calculate_weekly_commits(
    user: User, repos: Iterable[Repo]
) -> list[dict]:
    weekly_counts = fetch_github_commit_activity(user, repos)
    if not weekly_counts:
        # Fallback: aggregate the latest known commit counts into the current week.
        total_commits = sum(int(repo.commit_count or 0) for repo in repos)
        return [{"week_start": week_start_for_date(dt.datetime.utcnow()), "commit_count": total_commits}]

    now = dt.datetime.utcnow()
    weeks = []
    total_weeks = len(weekly_counts)
    for idx, count in enumerate(weekly_counts):
        week_delta = total_weeks - 1 - idx
        week_date = now - dt.timedelta(weeks=week_delta)
        week_start = week_start_for_date(week_date)
        weeks.append({"week_start": week_start, "commit_count": int(count)})
    return weeks


def _fetch_new_repo_counts(user: User) -> dict[str, int]:
    try:
        response = _github_get(f"{GITHUB_API}/users/{user.username}/repos", user.github_token)
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}
    repos = response.json()
    if not isinstance(repos, list):
        return {}
    counts: dict[str, int] = defaultdict(int)
    for repo in repos:
        created_at = repo.get("created_at")
        if not created_at:
            continue
        try:
            created_dt = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        week_start = week_start_for_date(created_dt).date().isoformat()
        counts[week_start] += 1
    return counts


def calculate_xp_growth(weekly_commits: list[dict], new_repo_counts: dict[str, int]) -> list[dict]:
    xp_rows = []
    for entry in weekly_commits:
        week_start = entry["week_start"]
        if isinstance(week_start, dt.datetime):
            week_key = week_start.date().isoformat()
        else:
            week_key = str(week_start)
        new_repos = new_repo_counts.get(week_key, 0)
        xp_gained = int(entry["commit_count"]) * 2 + new_repos * 50
        xp_rows.append({"week_start": week_start, "xp_gained": xp_gained})
    return xp_rows


def calculate_learning_progress(progress_rows: list[LearningProgress]) -> list[dict]:
    completed = [row for row in progress_rows if row.status == "done"]
    completed.sort(key=lambda row: row.completed_at or row.created_at or dt.datetime.utcnow())
    return [
        {
            "learning_step": row.learning_step,
            "status": row.status,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in completed
    ]


def compute_engagement_score(
    weekly_commits: list[dict],
    completed_steps: int,
    new_repo_counts: dict[str, int],
    xp_growth: list[dict],
) -> int:
    commits = sum(int(entry["commit_count"]) for entry in weekly_commits[-4:])
    new_repos = sum(new_repo_counts.values())
    xp_gained = sum(int(entry["xp_gained"]) for entry in xp_growth[-4:])
    score = commits * 2 + completed_steps * 10 + new_repos * 5 + (xp_gained / 10)
    score = max(0, min(100, int(round(score))))
    return score


def week_start_for_date(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    start = value - dt.timedelta(days=value.weekday())
    return dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc)


def refresh_engagement(db, user: User):
    repos = db.query(Repo).filter(Repo.user_id == user.id).all()
    try:
        weekly_commits = calculate_weekly_commits(user, repos)
    except Exception:
        weekly_commits = [{"week_start": week_start_for_date(dt.datetime.utcnow()), "commit_count": 0}]
    try:
        new_repo_counts = _fetch_new_repo_counts(user)
    except Exception:
        new_repo_counts = {}
    xp_growth = calculate_xp_growth(weekly_commits, new_repo_counts)

    db.query(EngagementCommit).filter(EngagementCommit.user_id == user.id).delete()
    for entry in weekly_commits:
        db.add(
            EngagementCommit(
                user_id=user.id,
                week_start=entry["week_start"],
                commit_count=int(entry["commit_count"]),
            )
        )

    db.query(XpHistory).filter(XpHistory.user_id == user.id).delete()
    for entry in xp_growth:
        db.add(
            XpHistory(
                user_id=user.id,
                week_start=entry["week_start"],
                xp_gained=int(entry["xp_gained"]),
            )
        )

    db.commit()
    return weekly_commits, new_repo_counts, xp_growth
