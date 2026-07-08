from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

LANGUAGE_ALIAS_MAP = {
    "jupyter notebook": "python",
    "plpgsql": "sql",
    "c#": "csharp",
    "c++": "cpp",
    "objective-c": "objc",
}

RARITY_REWARD_XP = {
    "common": 50,
    "uncommon": 100,
    "rare": 200,
    "epic": 400,
    "legendary": 750,
}

BASE_LEVEL_XP = 500
LEVEL_XP_STEP = 250

CATEGORY_ICON_MAP = {
    "Repository Builder": "📦",
    "Commit Momentum": "⚡",
    "Language Explorer": "🧭",
    "Star Magnet": "⭐",
    "Streak & Consistency": "🔥",
    "Frontend Engineering": "🎨",
    "Backend Systems Engineering": "🧱",
    "Data Science & Intelligence": "🤖",
    "Systems & DevOps Engineering": "⚙️",
    "Database & Information Management": "🗄️",
    "Cybersecurity & Systems Security": "🛡️",
    "Mobile & Cross-Platform Development": "📱",
    "Networking & Web Technologies": "🌐",
    "Software Engineering Principles": "📐",
    "Collaboration & Professional Practice": "🤝",
    "Academic & Curriculum Milestones": "🎓",
    "Algorithms & Computational Thinking": "🧠",
    "Object-Oriented Programming": "🏗️",
    "Software Testing & QA": "✅",
    "Information & Communication Technology": "💻",
    "Intelligent Systems & AI": "🧬",
    "Systems Analysis & Design": "🗺️",
    "Computer Organization & Architecture": "🖥️",
    "Statistics & Quantitative Methods": "📊",
    "Web Development Full Coverage": "🕸️",
    "Research & Capstone": "🔬",
    "Academic Integrity & Ethics": "⚖️",
    "Package & Dependency Management": "📚",
    "Project Management & Documentation": "🗂️",
    "Cloud & Deployment": "☁️",
}

MEDAL_BY_RARITY = {
    "common": ("bronze", "🥉"),
    "uncommon": ("silver", "🥈"),
    "rare": ("gold", "🥇"),
    "epic": ("platinum", "🏆"),
    "legendary": ("legend", "👑"),
}

FRONTEND_LANGS = {"html", "css", "scss", "sass", "less", "javascript", "typescript"}
BACKEND_LANGS = {"python", "javascript", "typescript", "go", "java", "php", "ruby", "csharp"}
MOBILE_LANGS = {"dart", "kotlin", "swift"}
DB_LANGS = {"sql", "plsql", "plpgsql"}
LOW_LEVEL_LANGS = {"c", "cpp", "assembly"}
DEVOPS_LANGS = {"shell", "bash", "hcl", "terraform", "ansible"}


def _norm(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    return LANGUAGE_ALIAS_MAP.get(raw, raw)


def _contains(text: str, keywords: set[str]) -> bool:
    return any(item in text for item in keywords)


def _extract_category_from_description(description: str | None) -> str:
    text = str(description or "")
    match = re.match(r"^\[Category:\s*(.+?)\]\s*", text)
    return (match.group(1).strip() if match else "Achievement") or "Achievement"


def _strip_category(description: str | None) -> str:
    text = str(description or "")
    return re.sub(r"^\[Category:\s*.+?\]\s*", "", text).strip()


@dataclass
class GamificationResult:
    xp: int
    level: int
    next_level_xp: int
    streak_days: int
    badges: list[dict]


def xp_required_for_level(level: int) -> int:
    target_level = max(1, int(level or 1))
    if target_level <= 1:
        return 0
    steps = target_level - 1
    return int((steps * (2 * BASE_LEVEL_XP + (steps - 1) * LEVEL_XP_STEP)) / 2)


def level_from_xp(xp: int) -> int:
    total_xp = max(0, int(xp or 0))
    level = 1
    next_cost = BASE_LEVEL_XP
    remaining = total_xp
    while remaining >= next_cost:
        remaining -= next_cost
        level += 1
        next_cost += LEVEL_XP_STEP
    return level


def next_level_xp_for_total(xp: int) -> int:
    level = level_from_xp(xp)
    return xp_required_for_level(level + 1)


def badge_reward_xp(rarity: str) -> int:
    return RARITY_REWARD_XP.get(str(rarity).lower(), 50)


def badge_visuals(label: str, rarity: str, description: str | None = None) -> dict:
    category = _extract_category_from_description(description)
    match = re.search(r"(\d+)", str(label or ""))
    target = int(match.group(1)) if match else 0
    category_icon = CATEGORY_ICON_MAP.get(category, "🏅")
    medal_tier, medal_icon = MEDAL_BY_RARITY.get(str(rarity).lower(), ("bronze", "🥉"))
    return {
        "category": category,
        "target": target,
        "medal_tier": medal_tier,
        "medal_icon": medal_icon,
        "category_icon": category_icon,
        "icon": f"{category_icon}{target}" if target else category_icon,
    }


def humanize_badge_criteria(criteria: str) -> str:
    raw = " ".join(str(criteria or "").split())
    if not raw:
        return "Complete the requirement for this achievement."

    patterns = [
        (r"^(\d+)\+\s+public repos$", lambda m: f"Create at least {m.group(1)} public repositories."),
        (r"^(\d+)\+\s+repos$", lambda m: f"Create at least {m.group(1)} repositories."),
        (r"^(\d+)\+\s+total commits$", lambda m: f"Reach at least {m.group(1)} total commits across your repositories."),
        (r"^(\d+)\+?\s+stars$", lambda m: f"Earn at least {m.group(1)} GitHub stars."),
        (r"^(\d+)\+?\s+unique languages?$", lambda m: f"Use at least {m.group(1)} different programming languages."),
        (r"^(\d+)-day commit streak$", lambda m: f"Maintain a commit streak for at least {m.group(1)} days."),
        (r"^Submitted (\d+)\+ certificates$", lambda m: f"Submit at least {m.group(1)} certificate or credential proofs."),
        (r"^(\d+)\+ verified certificates$", lambda m: f"Get at least {m.group(1)} certificate submissions verified."),
        (r"^Has scores in (\d+)\+ competency dimensions$", lambda m: f"Earn competency scores in at least {m.group(1)} dimensions."),
        (r"^Has high scores \(>=70\) in (\d+)\+ dimensions$", lambda m: f"Reach scores of 70 or higher in at least {m.group(1)} competency dimensions."),
        (r"^Claimed (\d+)\+ daily quests$", lambda m: f"Claim at least {m.group(1)} daily quests."),
        (r"^Claimed at least (\d+) weekly challenge$", lambda m: f"Claim at least {m.group(1)} weekly challenge."),
        (r"^Claimed (\d+)\+ weekly challenges$", lambda m: f"Claim at least {m.group(1)} weekly challenges."),
    ]
    for pattern, formatter in patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            return formatter(match)

    lowered = raw.lower()
    normalized = raw.replace(">=", "at least ").replace("<=", "at most ").replace("==", "exactly ")
    if lowered.startswith("repo mentions "):
        topic = raw[14:].replace("/", ", ")
        return f"Have a repository that clearly shows work related to {topic}."
    if lowered.startswith("repo name/description has "):
        topic = raw[26:].replace("/", ", ")
        return f"Have a repository name or description that clearly reflects {topic}."
    if lowered.startswith("repo has "):
        topic = raw[9:].replace("/", ", ")
        return f"Have a repository that shows {topic}."
    if lowered.startswith("repo with "):
        topic = raw[10:].replace("/", ", ")
        return f"Have a repository with {topic}."
    if lowered.startswith("any repo with only "):
        return f"Have at least one repository that uses only {raw[19:]}."
    if lowered.startswith("any repo with "):
        return f"Have at least one repository with {raw[14:]}."
    if lowered.startswith("any single repo with "):
        return f"Have at least one repository with {raw[21:]}."
    if lowered.startswith("has at least "):
        sentence = raw[0].upper() + raw[1:]
        if not sentence.endswith("."):
            sentence += "."
        return sentence
    if lowered.startswith("1 backend-language repo"):
        return "Have at least one repository that uses a backend language."
    if lowered.startswith("has both "):
        return f"Have both {raw[9:]}."
    if lowered.startswith("all 4 main dimensions have score >= 60"):
        return "Reach a score of at least 60 in all four main competency dimensions."
    if lowered.startswith("user has portfolio settings"):
        return "Set up your public portfolio profile."
    if lowered.startswith("has certificates + stars >= 10 + repo_count >= 10"):
        return "Have certificate activity, at least 10 GitHub stars, and at least 10 repositories."
    if lowered.startswith("ml signals + stats signals + 5+ python repos"):
        return "Show both machine learning and statistics signals, plus at least 5 Python repositories."
    if lowered.startswith("repo_count"):
        return (
            normalized.replace("repo_count", "repository count")
            .replace("total_commits", "total commits")
            .replace("total_stars", "total stars")
            .replace("_", " ")
            .capitalize()
            + "."
        )
    if " and " in lowered and any(token in lowered for token in ["repo_count", "total_commits", "total_stars"]):
        sentence = (
            normalized.replace("repo_count", "repository count")
            .replace("total_commits", "total commits")
            .replace("total_stars", "total stars")
            .replace("_", " ")
        )
        sentence = sentence[0].upper() + sentence[1:]
        if not sentence.endswith("."):
            sentence += "."
        return sentence

    sentence = (
        normalized.replace("repo_count", "repository count")
        .replace("total_commits", "total commits")
        .replace("total_stars", "total stars")
        .replace("_", " ")
        .replace("/", ", ")
    )
    sentence = sentence[0].upper() + sentence[1:]
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def compute_xp_and_badges(repos: list[dict], context: dict | None = None) -> GamificationResult:
    context = context or {}

    repo_rows: list[dict] = []
    commit_counts: list[int] = []
    all_languages: list[str] = []
    public_repo_count = 0

    for repo in repos:
        commit_count = int(repo.get("commit_count") or 0)
        commit_counts.append(commit_count)

        primary_language = _norm(repo.get("language"))
        languages = {_norm(lang) for lang in (repo.get("languages") or []) if str(lang).strip()}
        language_bytes = repo.get("language_bytes") or {}
        if isinstance(language_bytes, dict):
            languages |= {_norm(lang) for lang in language_bytes.keys() if str(lang).strip()}
        if primary_language:
            languages.add(primary_language)
        all_languages.extend([lang for lang in languages if lang])

        name = str(repo.get("name") or "")
        description = str(repo.get("description") or "")
        topics = [str(topic or "") for topic in (repo.get("topics") or [])]
        text = f"{name} {description} {' '.join(topics)}".lower()
        is_public = bool(repo.get("is_public", True))
        if is_public:
            public_repo_count += 1

        repo_rows.append(
            {
                "name": name,
                "description": description,
                "topics": topics,
                "text": text,
                "primary_language": primary_language,
                "languages": languages,
                "stars": int(repo.get("stars") or 0),
                "commit_count": commit_count,
            }
        )

    total_commits = sum(commit_counts)
    repo_count = len(repos)
    commit_xp = total_commits * 2
    repo_xp = repo_count * 50

    language_counts = Counter(lang for lang in all_languages if lang)
    unique_languages = set(language_counts.keys())
    language_xp = max(0, len(unique_languages) - 1) * 30

    stars_xp = sum(item["stars"] for item in repo_rows)
    xp = commit_xp + repo_xp + language_xp + stars_xp

    level = level_from_xp(xp)
    next_level_xp = next_level_xp_for_total(xp)

    streak_days = int(context.get("streak_days") or 0)

    def repo_any(keywords: set[str], language_set: set[str] | None = None) -> bool:
        for row in repo_rows:
            if language_set and row["languages"].intersection(language_set):
                return True
            if _contains(row["text"], keywords):
                return True
        return False

    def repo_count_match(predicate) -> int:
        return sum(1 for row in repo_rows if predicate(row))

    frontend_kw = {"react", "vue", "angular", "svelte", "frontend", "ui", "ux", "spa", "single page"}
    backend_kw = {"api", "backend", "server", "express", "fastapi", "flask", "django", "spring"}
    db_kw = {"database", " db ", "mysql", "postgres", "mongo", "sql"}
    ml_kw = {"machine learning", " ml ", "sklearn", "tensorflow", "pytorch", "keras", "ai", "llm"}
    devops_kw = {"docker", "container", "ci", "cd", "pipeline", "workflow", "devops", "infra", "terraform", "ansible"}
    mobile_kw = {"flutter", "dart", "react native", "expo", "kotlin", "swift", "mobile", "appstore", "playstore"}
    security_kw = {"auth", "login", "authentication", "jwt", "oauth", "token", "session", "security", "vulnerability", "ctf", "exploit"}
    algo_kw = {"algorithm", "sorting", "searching", "recursion", "fibonacci", "factorial", "big-o", "complexity", "linked list", "tree", "graph", "stack", "queue", "heap"}
    oop_kw = {"class", "object", "oop", "inheritance", "extends", "abstract", "polymorphism", "interface", "override", "solid", "design pattern", "clean architecture"}
    testing_kw = {"test", "testing", "spec", "unit test", "jest", "pytest", "mocha", "jasmine", "tdd", "test driven", "test-driven"}
    ai_kw = {"ai", "artificial intelligence", "chatbot", "llm", "gpt", "prompt", "langchain", "openai", "anthropic", "training", "fine-tune", "finetune", "neural network", "deep learning", "cnn", "rnn", "lstm", "transformer"}
    sad_kw = {"documentation", "docs", "requirements", "use case", "user story", "specification", "uml", "erd", "diagram", "flowchart", "system design", "architecture", "blueprint", "sdlc", "software development lifecycle", "system analysis"}
    stats_kw = {"statistics", "stats", "statistical", "mean", "median", "mode", "average", "summary", "probability", "distribution", "bayesian", "random", "regression", "correlation", "linear model", "logistic"}
    deploy_kw = {"deploy", "deployment", "vercel", "netlify", "heroku", "cloud", "aws", "gcp", "azure", "firebase", "serverless", "lambda", "cloud function", "firebase functions", "production", "live", "launch"}
    ethics_kw = {"license", "mit", "apache", "open source", "credits", "contributors", "acknowledgement", "code of conduct", "contributing", "style guide", "privacy", "gdpr", "data protection", "anonymization", "ethical", "responsible", "bias", "fairness"}
    pm_kw = {"issues", "bug tracker", "task", "milestone", "sprint", "release", "wiki", "documentation", "docs site", "kanban", "project board", "trello", "jira", "agile", "scrum", "standup"}
    research_kw = {"research", "study", "analysis", "survey", "literature", "review", "reference", "citation", "prototype", "proof of concept", "poc", "mvp", "thesis", "capstone", "final project", "research system", "research tool"}
    network_kw = {"http", "api", "rest", "fetch", "axios", "websocket", "socket.io", "real-time", "realtime", "distributed", "cloud-native", "load balancer", "microservice", "api gateway"}
    package_kw = {"dependencies", "packages", "requirements", "npm", "pip", "venv", "virtualenv", "conda", "pipenv", "poetry", "monorepo", "workspace", "lerna", "turborepo", "nx", "library", "sdk", "module", "package"}
    ict_kw = {"integration", "connect", "service", "api gateway", "deployed", "production", "live", "launch"}
    co_kw = {"binary", "bitwise", "bit manipulation", "hex", "memory", "pointer", "malloc", "cpu", "emulator", "computer architecture", "cpu simulator", "operating system", "kernel", "os"}

    def is_frontend_repo(row: dict) -> bool:
        return bool(row["languages"].intersection(FRONTEND_LANGS) or _contains(row["text"], frontend_kw))

    def is_backend_repo(row: dict) -> bool:
        return bool(row["languages"].intersection(BACKEND_LANGS) or _contains(row["text"], backend_kw))

    def is_db_repo(row: dict) -> bool:
        return bool(row["languages"].intersection(DB_LANGS) or _contains(row["text"], db_kw))

    def is_ml_repo(row: dict) -> bool:
        return bool(
            row["primary_language"] in {"python", "r"}
            and _contains(row["text"], {"ml", "ai", "machine learning", "tensorflow", "pytorch", "sklearn", "keras", "model"})
        ) or _contains(row["text"], ml_kw)

    def is_devops_repo(row: dict) -> bool:
        return bool(row["languages"].intersection(DEVOPS_LANGS) or _contains(row["text"], devops_kw))

    def is_mobile_repo(row: dict) -> bool:
        return bool(row["languages"].intersection(MOBILE_LANGS) or _contains(row["text"], mobile_kw))

    def is_network_repo(row: dict) -> bool:
        return _contains(row["text"], network_kw)

    def is_security_repo(row: dict) -> bool:
        return _contains(row["text"], security_kw)

    def is_algo_repo(row: dict) -> bool:
        return _contains(row["text"], algo_kw)

    def is_oop_repo(row: dict) -> bool:
        return bool(row["languages"].intersection({"java", "cpp", "csharp", "python", "kotlin"}) or _contains(row["text"], oop_kw))

    def is_testing_repo(row: dict) -> bool:
        return _contains(row["text"], testing_kw)

    def is_ai_repo(row: dict) -> bool:
        return _contains(row["text"], ai_kw)

    def is_sad_repo(row: dict) -> bool:
        return _contains(row["text"], sad_kw)

    def is_stats_repo(row: dict) -> bool:
        return _contains(row["text"], stats_kw)

    def is_cloud_repo(row: dict) -> bool:
        return _contains(row["text"], deploy_kw)

    def is_ethics_repo(row: dict) -> bool:
        return _contains(row["text"], ethics_kw)

    def is_pm_repo(row: dict) -> bool:
        return _contains(row["text"], pm_kw)

    def is_research_repo(row: dict) -> bool:
        return _contains(row["text"], research_kw)

    def is_co_repo(row: dict) -> bool:
        return bool(row["languages"].intersection(LOW_LEVEL_LANGS) or _contains(row["text"], co_kw))

    frontend_repo_count = repo_count_match(is_frontend_repo)
    backend_repo_count = repo_count_match(is_backend_repo)
    db_repo_count = repo_count_match(is_db_repo)
    ml_repo_count = repo_count_match(is_ml_repo)
    devops_repo_count = repo_count_match(is_devops_repo)
    mobile_repo_count = repo_count_match(is_mobile_repo)
    network_repo_count = repo_count_match(is_network_repo)
    security_repo_count = repo_count_match(is_security_repo)
    algo_repo_count = repo_count_match(is_algo_repo)
    oop_repo_count = repo_count_match(is_oop_repo)
    testing_repo_count = repo_count_match(is_testing_repo)
    ai_repo_count = repo_count_match(is_ai_repo)
    sad_repo_count = repo_count_match(is_sad_repo)
    stats_repo_count = repo_count_match(is_stats_repo)
    cloud_repo_count = repo_count_match(is_cloud_repo)
    ethics_repo_count = repo_count_match(is_ethics_repo)
    pm_repo_count = repo_count_match(is_pm_repo)
    research_repo_count = repo_count_match(is_research_repo)
    co_repo_count = repo_count_match(is_co_repo)

    has_container_signal = repo_any({"docker", "container", "dockerfile"})
    has_ci_signal = repo_any({" ci ", " cd ", "github actions", "pipeline", "workflow"})
    has_deploy_signal = repo_any(deploy_kw)
    has_terraform_signal = repo_any({"terraform", "infrastructure"}, {"terraform", "hcl", "ansible"})
    has_react_framework_signal = repo_any({"react", "vue", "angular", "svelte"})

    dynamic_web_repo_count = repo_count_match(
        lambda row: bool(row["languages"].intersection({"javascript", "typescript"}) and (row["languages"].intersection(BACKEND_LANGS) or _contains(row["text"], backend_kw)))
    )
    full_stack_repo_count = repo_count_match(
        lambda row: is_frontend_repo(row) and is_backend_repo(row) and is_db_repo(row)
    )
    static_site_repo_count = repo_count_match(
        lambda row: row["languages"]
        and row["languages"].issubset({"html", "css", "scss", "sass", "less"})
        and "html" in row["languages"]
    )

    practice_dimensions = context.get("practice_dimensions") or []
    dim_scores = {
        _norm(item.get("label")): int(item.get("confidence") or 0)
        for item in practice_dimensions
        if item.get("label")
    }
    dimension_count = len(dim_scores)
    high_70_count = sum(1 for score in dim_scores.values() if score >= 70)
    main_dimension_checks = {
        "frontend engineering": False,
        "backend systems engineering": False,
        "data science & intelligence": False,
        "systems & devops engineering": False,
    }
    for label, score in dim_scores.items():
        for key in list(main_dimension_checks.keys()):
            if key in label and score >= 60:
                main_dimension_checks[key] = True

    certificate_verified_count = int(context.get("certificate_verified_count") or 0)
    certificate_total_count = int(context.get("certificate_total_count") or 0)
    certificate_reward_claimed_count = int(context.get("certificate_reward_claimed_count") or 0)
    certificate_locked_count = int(context.get("certificate_locked_count") or 0)
    daily_quest_claim_count = int(context.get("daily_quest_claim_count") or 0)
    weekly_challenge_claim_count = int(context.get("weekly_challenge_claim_count") or 0)
    learning_path_completed_count = int(context.get("learning_path_completed_count") or 0)
    learning_path_steps_count = int(context.get("learning_path_steps_count") or 0)
    project_path_started_count = int(context.get("project_path_started_count") or 0)
    project_path_completed_count = int(context.get("project_path_completed_count") or 0)
    project_path_claim_count = int(context.get("project_path_claim_count") or 0)
    project_stage_completed_count = int(context.get("project_stage_completed_count") or 0)
    has_portfolio_settings = bool(context.get("has_portfolio_settings"))

    badges: list[dict] = []
    seen_labels: set[str] = set()

    def add_badge(category: str, label: str, rarity: str, achieved: bool, criteria: str) -> None:
        key = label
        if key in seen_labels:
            key = f"{label} [{category}]"
        seen_labels.add(key)
        badges.append(
            {
                "label": key,
                "description": f"[Category: {category}] {label}",
                "criteria": humanize_badge_criteria(criteria),
                "rarity": rarity,
                "achieved": bool(achieved),
                "claimed": False,
            }
        )

    # 1) Repository Builder
    add_badge("Repository Builder", "First Repo", "common", repo_count >= 1, "1+ repos")
    add_badge("Repository Builder", "Repo Starter", "common", repo_count >= 3, "3+ repos")
    add_badge("Repository Builder", "Project Collector", "uncommon", repo_count >= 7, "7+ repos")
    add_badge("Repository Builder", "Repo Builder", "rare", repo_count >= 15, "15+ repos")
    add_badge("Repository Builder", "Portfolio Architect", "epic", repo_count >= 25, "25+ repos")
    add_badge("Repository Builder", "Open Source Legend", "legendary", public_repo_count >= 50, "50+ public repos")

    # 2) Commit Momentum
    add_badge("Commit Momentum", "First Commit", "common", total_commits >= 1, "1+ total commits")
    add_badge("Commit Momentum", "Getting Started", "common", total_commits >= 25, "25+ total commits")
    add_badge("Commit Momentum", "Code Grinder", "uncommon", total_commits >= 100, "100+ total commits")
    add_badge("Commit Momentum", "Commit Warrior", "rare", total_commits >= 300, "300+ total commits")
    add_badge("Commit Momentum", "Refactor Champion", "epic", total_commits >= 700, "700+ total commits")
    add_badge("Commit Momentum", "Unstoppable Dev", "legendary", total_commits >= 1500, "1500+ total commits")

    # 3) Language Explorer
    add_badge("Language Explorer", "Monolinguist", "common", len(unique_languages) >= 1, "1 unique language")
    add_badge("Language Explorer", "Bilingual Coder", "common", len(unique_languages) >= 2, "2 unique languages")
    add_badge("Language Explorer", "Polyglot Starter", "uncommon", len(unique_languages) >= 4, "4 unique languages")
    add_badge("Language Explorer", "Language Explorer", "rare", len(unique_languages) >= 6, "6 unique languages")
    add_badge("Language Explorer", "Syntax Collector", "epic", len(unique_languages) >= 9, "9 unique languages")
    add_badge("Language Explorer", "Tower of Babel", "legendary", len(unique_languages) >= 12, "12+ unique languages")

    # 4) Star Magnet
    add_badge("Star Magnet", "First Star", "common", stars_xp >= 1, "1+ stars")
    add_badge("Star Magnet", "Rising Project", "common", stars_xp >= 5, "5+ stars")
    add_badge("Star Magnet", "Community Pick", "uncommon", stars_xp >= 15, "15+ stars")
    add_badge("Star Magnet", "Star Magnet", "rare", stars_xp >= 35, "35+ stars")
    add_badge("Star Magnet", "GitHub Famous", "epic", stars_xp >= 75, "75+ stars")
    add_badge("Star Magnet", "Hall of Fame", "legendary", stars_xp >= 150, "150+ stars")

    # 5) Streak & Consistency
    add_badge("Streak & Consistency", "Daily Pusher", "common", streak_days >= 3, "3-day commit streak")
    add_badge("Streak & Consistency", "Weekly Warrior", "uncommon", streak_days >= 7, "7-day commit streak")
    add_badge("Streak & Consistency", "Consistent Coder", "rare", streak_days >= 14, "14-day commit streak")
    add_badge("Streak & Consistency", "Streak Master", "epic", streak_days >= 30, "30-day commit streak")
    add_badge("Streak & Consistency", "Iron Discipline", "legendary", streak_days >= 60, "60-day commit streak")
    add_badge("Streak & Consistency", "Unstoppable", "legendary", streak_days >= 90, "90-day commit streak")

    # 6) Frontend Engineering
    add_badge("Frontend Engineering", "HTML Crafter", "common", repo_any(set(), {"html"}), "Any repo with HTML as language")
    add_badge("Frontend Engineering", "CSS Stylist", "common", repo_any(set(), {"css", "scss"}), "Any repo with CSS/SCSS")
    add_badge("Frontend Engineering", "UI Apprentice", "uncommon", repo_count_match(lambda row: bool(row["primary_language"] in FRONTEND_LANGS)) >= 2, "2+ repos with HTML/CSS/JS/TS primary")
    add_badge("Frontend Engineering", "React Initiate", "rare", has_react_framework_signal, "Repo mentions react/vue/angular/svelte")
    add_badge("Frontend Engineering", "Component Architect", "epic", frontend_repo_count >= 5, "5+ frontend repos")
    add_badge("Frontend Engineering", "UI/UX Visionary", "legendary", frontend_repo_count >= 10 and stars_xp >= 10, "10+ frontend repos and total_stars >= 10")

    # 7) Backend Systems Engineering
    add_badge("Backend Systems Engineering", "API Rookie", "common", repo_any(set(), BACKEND_LANGS), "1 backend-language repo")
    add_badge("Backend Systems Engineering", "Route Builder", "common", repo_any(backend_kw), "Repo mentions API/backend/server frameworks")
    add_badge("Backend Systems Engineering", "DB Handler", "uncommon", repo_any(db_kw), "Repo mentions DB/SQL/Mongo/Postgres/MySQL/SQLite")
    add_badge("Backend Systems Engineering", "REST Architect", "rare", backend_repo_count >= 3, "3+ backend repos")
    add_badge("Backend Systems Engineering", "Microservice Engineer", "epic", backend_repo_count >= 5, "5+ backend repos")
    add_badge("Backend Systems Engineering", "Systems Mastermind", "legendary", backend_repo_count >= 10 and total_commits >= 200, "10+ backend repos and total_commits >= 200")

    # 8) Data Science & Intelligence
    add_badge("Data Science & Intelligence", "Data Curious", "common", repo_count_match(lambda row: row["primary_language"] in {"python", "r"}) >= 1, "1 repo with Python or R primary")
    add_badge("Data Science & Intelligence", "Dataset Wrangler", "uncommon", repo_any({"dataset", "csv", " data ", "pandas", "numpy"}), "Repo mentions dataset/csv/data/pandas/numpy")
    add_badge("Data Science & Intelligence", "Notebook Explorer", "uncommon", repo_any({"notebook", "jupyter", "ipynb", "colab"}), "Repo mentions notebook/jupyter/ipynb/colab")
    add_badge("Data Science & Intelligence", "ML Initiate", "rare", repo_any({"machine learning", " ml ", "sklearn", "tensorflow", "pytorch", "keras"}), "Repo has ML signals")
    add_badge("Data Science & Intelligence", "Model Builder", "epic", ml_repo_count >= 3, "3+ repos with ML/AI signals")
    add_badge("Data Science & Intelligence", "AI Trailblazer", "legendary", ml_repo_count >= 5 and total_commits >= 150, "5+ ML/AI repos and total_commits >= 150")

    # 9) Systems & DevOps Engineering
    add_badge("Systems & DevOps Engineering", "Terminal Novice", "common", repo_any(set(), {"shell", "bash"}), "Any repo with Shell/Bash")
    add_badge("Systems & DevOps Engineering", "Config Keeper", "common", repo_any({"dotfiles", "config", "setup", " env"}), "Repo name/description has config/setup/env")
    add_badge("Systems & DevOps Engineering", "Container Cadet", "uncommon", has_container_signal, "Repo mentions docker/container")
    add_badge("Systems & DevOps Engineering", "CI/CD Initiate", "rare", has_ci_signal, "Repo mentions CI/CD/pipeline/workflow")
    add_badge("Systems & DevOps Engineering", "Pipeline Engineer", "epic", devops_repo_count >= 3, "3+ DevOps repos")
    add_badge("Systems & DevOps Engineering", "Infrastructure Master", "legendary", devops_repo_count >= 5 and has_terraform_signal, "5+ DevOps repos and Terraform/Ansible/HCL signal")

    # 10) Database & Information Management
    add_badge("Database & Information Management", "Schema Starter", "common", repo_any(set(), {"sql"}), "Any repo with SQL")
    add_badge("Database & Information Management", "Query Writer", "common", repo_any({"mysql", "postgres", "database", " db"}), "Repo mentions DB engines")
    add_badge("Database & Information Management", "Data Modeler", "uncommon", db_repo_count >= 2, "2+ repos with DB signals")
    add_badge("Database & Information Management", "Relational Thinker", "rare", repo_any({"erd", "migration", "schema", "entity"}), "Repo mentions ERD/migration/schema/entity")
    add_badge("Database & Information Management", "DB Optimizer", "epic", db_repo_count >= 5, "5+ DB-related repos")
    add_badge("Database & Information Management", "Data Architect", "legendary", full_stack_repo_count >= 1, "At least one full-stack repo with DB signal")

    # 11) Cybersecurity & Systems Security
    add_badge("Cybersecurity & Systems Security", "Security Aware", "common", repo_any({"auth", "login", "authentication"}), "Repo mentions auth/login/authentication")
    add_badge("Cybersecurity & Systems Security", "Input Validator", "common", repo_any({"validation", "sanitize", "form"}), "Repo mentions validation/sanitize/form")
    add_badge("Cybersecurity & Systems Security", "Auth Engineer", "uncommon", repo_any({"jwt", "oauth", "token", "session"}), "Repo mentions JWT/OAuth/token/session")
    add_badge("Cybersecurity & Systems Security", "Secure Coder", "rare", security_repo_count >= 2, "2+ repos with security signals")
    add_badge("Cybersecurity & Systems Security", "Threat Modeler", "epic", repo_any({"pentest", "security", "vulnerability", "exploit", "ctf"}), "Repo mentions pentest/security/vulnerability/exploit/ctf")
    add_badge("Cybersecurity & Systems Security", "Cyber Guardian", "legendary", security_repo_count >= 5, "5+ security repos")

    # 12) Mobile & Cross-Platform Development
    add_badge("Mobile & Cross-Platform Development", "App Curious", "common", repo_any(set(), {"dart", "kotlin", "swift"}), "Repo with Dart/Kotlin/Swift")
    add_badge("Mobile & Cross-Platform Development", "Flutter Starter", "common", repo_any({"flutter", "dart"}), "Repo mentions flutter/dart")
    add_badge("Mobile & Cross-Platform Development", "React Native Cadet", "uncommon", repo_any({"react native", "expo"}), "Repo mentions React Native/Expo")
    add_badge("Mobile & Cross-Platform Development", "Cross-Platform Builder", "rare", mobile_repo_count >= 2, "2+ mobile repos")
    add_badge("Mobile & Cross-Platform Development", "Mobile Engineer", "epic", mobile_repo_count >= 5, "5+ mobile repos")
    add_badge("Mobile & Cross-Platform Development", "App Store Ready", "legendary", repo_any({"published", "playstore", "appstore", "deployed mobile"}), "Repo mentions mobile publishing/deploy")

    # 13) Networking & Web Technologies
    add_badge("Networking & Web Technologies", "Web Aware", "common", repo_count_match(lambda row: row["primary_language"] in {"html", "css", "javascript"}) >= 1, "1+ web repos")
    add_badge("Networking & Web Technologies", "Protocol Learner", "common", repo_any({"http", "api", "rest", "fetch", "axios"}), "Repo mentions HTTP/API/REST/fetch/axios")
    add_badge("Networking & Web Technologies", "Socket Explorer", "uncommon", repo_any({"websocket", "socket.io", "real-time", "realtime"}), "Repo mentions socket/websocket")
    add_badge("Networking & Web Technologies", "Network Builder", "rare", network_repo_count >= 3, "3+ networked app repos")
    add_badge("Networking & Web Technologies", "Web Systems Engineer", "epic", frontend_repo_count > 0 and backend_repo_count > 0, "Has both frontend and backend repos")
    add_badge("Networking & Web Technologies", "Internet Architect", "legendary", repo_any({"microservice", "distributed", "cloud-native", "load balancer"}), "Repo mentions microservice/distributed/cloud-native/load balancer")

    # 14) Software Engineering Principles
    add_badge("Software Engineering Principles", "Clean Coder", "common", any(item["commit_count"] >= 10 for item in repo_rows), "Any single repo with 10+ commits")
    add_badge("Software Engineering Principles", "README Writer", "common", repo_count >= 1, "repo_count >= 1")
    add_badge("Software Engineering Principles", "Version Tracker", "uncommon", total_commits >= 50, "total_commits >= 50")
    add_badge("Software Engineering Principles", "Design Pattern User", "rare", repo_any({"design pattern", "oop", "solid", "mvc", "mvvm"}), "Repo mentions design patterns/OOP/SOLID/MVC/MVVM")
    add_badge("Software Engineering Principles", "Refactor Champion", "epic", total_commits >= 200, "total_commits >= 200")
    add_badge("Software Engineering Principles", "Software Craftsman", "legendary", total_commits >= 500, "total_commits >= 500")

    # 15) Collaboration & Professional Practice
    add_badge("Collaboration & Professional Practice", "Open Source Curious", "common", public_repo_count >= 1, "1+ public repos")
    add_badge("Collaboration & Professional Practice", "Team Player", "common", repo_any({"team", "collaboration", "contributors", "fork"}), "Repo has collaboration/fork signal")
    add_badge("Collaboration & Professional Practice", "Fork & Contribute", "uncommon", repo_any({"fork"}), "Repo has forking signal")
    add_badge("Collaboration & Professional Practice", "Pull Request Pro", "rare", total_commits >= 100 and repo_count >= 5, "total_commits >= 100 and repo_count >= 5")
    add_badge("Collaboration & Professional Practice", "Community Builder", "epic", repo_count_match(lambda row: row["stars"] > 0) >= 5, "5+ repos with stars")
    add_badge("Collaboration & Professional Practice", "Industry Ready", "legendary", certificate_total_count > 0 and stars_xp >= 10 and repo_count >= 10, "Has certificates + stars >= 10 + repo_count >= 10")

    # 16) Academic & Curriculum Milestones
    add_badge("Academic & Curriculum Milestones", "Project Submitter", "common", certificate_verified_count >= 1 or project_stage_completed_count >= 1, "Submit at least one reviewed certificate proof or complete one repo learning-path stage")
    add_badge("Academic & Curriculum Milestones", "Credential Starter", "common", certificate_total_count >= 1, "Submitted 1+ certificates")
    add_badge("Academic & Curriculum Milestones", "Credential Builder", "uncommon", certificate_total_count >= 3 or certificate_locked_count >= 1, "Submit 3+ certificates or lock one final credential reward")
    add_badge("Academic & Curriculum Milestones", "Verified Achiever", "rare", certificate_verified_count >= 2, "2+ verified certificates")
    add_badge("Academic & Curriculum Milestones", "Certified Specialist", "epic", certificate_verified_count >= 5, "5+ verified certificates")
    add_badge("Academic & Curriculum Milestones", "Credential Master", "legendary", certificate_verified_count >= 10, "10+ verified certificates")
    add_badge("Academic & Curriculum Milestones", "Curriculum Aligned", "uncommon", dimension_count >= 2 and learning_path_steps_count >= 1, "Earn scores in 2+ competency dimensions and generate a learning path")
    add_badge("Academic & Curriculum Milestones", "Quest Completer", "uncommon", daily_quest_claim_count >= 1, "Has claimed at least 1 daily quest")
    add_badge("Academic & Curriculum Milestones", "Challenge Champion", "rare", weekly_challenge_claim_count >= 5, "Has claimed 5+ weekly challenges")
    add_badge("Academic & Curriculum Milestones", "Dean's List Coder", "rare", high_70_count >= 3 and (certificate_verified_count >= 1 or project_path_claim_count >= 1), "Reach high scores in 3+ dimensions and verify at least one milestone")
    add_badge("Academic & Curriculum Milestones", "Capstone Contender", "epic", repo_any({"capstone", "thesis", "system", "final project"}) and project_path_started_count >= 1, "Show a capstone-style repository and start at least one repo learning path")
    add_badge("Academic & Curriculum Milestones", "BSCS/BSIT Graduate", "legendary", all(main_dimension_checks.values()) and learning_path_completed_count >= 1 and project_path_completed_count >= 1, "Reach all 4 main dimensions, complete the learning path, and finish at least one repository path")

    # 16B) Connected Journey Progress
    add_badge("Academic & Curriculum Milestones", "Path Starter", "common", learning_path_steps_count >= 1, "Generate your personalized learning path")
    add_badge("Academic & Curriculum Milestones", "Repo Pathfinder", "uncommon", project_path_started_count >= 1, "Start at least 1 repository learning path")
    add_badge("Academic & Curriculum Milestones", "Stage Finisher", "rare", project_stage_completed_count >= 3 or project_path_claim_count >= 1, "Complete 3 repo learning-path stages or claim 1 repo path reward")
    add_badge("Academic & Curriculum Milestones", "Repository Closer", "epic", project_path_completed_count >= 1, "Finish at least 1 full repository learning path")
    add_badge("Academic & Curriculum Milestones", "Learning Path Completer", "epic", learning_path_completed_count >= 1, "Complete the main personalized learning path")
    add_badge("Academic & Curriculum Milestones", "Integrated Achiever", "legendary", learning_path_completed_count >= 1 and project_path_completed_count >= 1 and certificate_reward_claimed_count >= 1, "Complete the learning path, finish 1 repo path, and claim 1 certificate reward")

    # 17) Algorithms & Computational Thinking
    add_badge("Algorithms & Computational Thinking", "Algorithm Apprentice", "common", repo_any({"algorithm", "sorting", "searching"}), "Repo mentions algorithm/sorting/searching")
    add_badge("Algorithms & Computational Thinking", "Recursion Rider", "common", repo_any({"recursion", "recursive", "fibonacci", "factorial"}), "Repo mentions recursion/fibonacci/factorial")
    add_badge("Algorithms & Computational Thinking", "Complexity Aware", "uncommon", repo_any({"big-o", "complexity", "time complexity"}), "Repo mentions complexity")
    add_badge("Algorithms & Computational Thinking", "Data Structure Builder", "rare", repo_any({"linked list", "tree", "graph", "stack", "queue", "heap"}), "Repo mentions data structures")
    add_badge("Algorithms & Computational Thinking", "Problem Solver", "rare", algo_repo_count >= 5, "5+ repos with algorithm signals")
    add_badge("Algorithms & Computational Thinking", "Competitive Coder", "epic", algo_repo_count >= 10, "10+ algorithm repos")
    add_badge("Algorithms & Computational Thinking", "Algorithm Grandmaster", "legendary", algo_repo_count >= 10 and stars_xp >= 5, "10+ algorithm repos and total_stars >= 5")

    # 18) Object-Oriented Programming
    add_badge("Object-Oriented Programming", "Class Creator", "common", repo_any(set(), {"java", "cpp", "csharp", "python", "kotlin"}), "Repo with Java/C++/C#/Python/Kotlin")
    add_badge("Object-Oriented Programming", "Encapsulation Starter", "common", repo_any({"class", "object", "oop"}), "Repo mentions class/object/oop")
    add_badge("Object-Oriented Programming", "Inheritance Explorer", "uncommon", repo_any({"inheritance", "extends", "abstract"}), "Repo mentions inheritance/extends/abstract")
    add_badge("Object-Oriented Programming", "Polymorphism User", "rare", repo_any({"polymorphism", "interface", "override"}), "Repo mentions polymorphism/interface/override")
    add_badge("Object-Oriented Programming", "SOLID Practitioner", "epic", repo_any({"solid", "design pattern", "clean architecture"}), "Repo mentions SOLID/design pattern/clean architecture")
    add_badge("Object-Oriented Programming", "OOP Architect", "legendary", oop_repo_count >= 5 and total_commits >= 100, "5+ OOP repos and total_commits >= 100")

    # 19) Software Testing & QA
    add_badge("Software Testing & QA", "Test Curious", "common", repo_any({"test", "testing", "spec"}), "Repo mentions testing/spec")
    add_badge("Software Testing & QA", "Unit Tester", "common", repo_any({"unit test", "jest", "pytest", "mocha", "jasmine"}), "Repo mentions unit testing tools")
    add_badge("Software Testing & QA", "Test Coverage Starter", "uncommon", testing_repo_count >= 2, "2+ repos with testing signals")
    add_badge("Software Testing & QA", "TDD Practitioner", "rare", repo_any({"tdd", "test driven", "test-driven"}), "Repo mentions TDD")
    add_badge("Software Testing & QA", "QA Engineer", "epic", testing_repo_count >= 5, "5+ repos with testing signals")
    add_badge("Software Testing & QA", "Zero Bug Policy", "legendary", testing_repo_count >= 5 and has_ci_signal, "5+ test repos and any CI/CD signal")

    # 20) Information & Communication Technology
    add_badge("Information & Communication Technology", "ICT Aware", "common", repo_count >= 1, "1+ repos")
    add_badge("Information & Communication Technology", "Digital Citizen", "common", has_portfolio_settings, "User has portfolio settings")
    add_badge("Information & Communication Technology", "Tech Communicator", "uncommon", repo_count >= 3, "repo_count >= 3 and README proxy")
    add_badge("Information & Communication Technology", "Systems Integrator", "rare", repo_any({"integration", "connect", "service", "api gateway"}), "Repo mentions integration/connect/service/api gateway")
    add_badge("Information & Communication Technology", "ICT Solutions Builder", "epic", repo_count >= 5 and len(unique_languages) >= 3, "5+ repos with varied languages")
    add_badge("Information & Communication Technology", "ICT Innovator", "legendary", repo_any({"deployed", "production", "live", "launch"}), "Repo mentions deployed/production/live/launch")

    # 21) Intelligent Systems & AI
    add_badge("Intelligent Systems & AI", "AI Curious", "common", repo_any({"ai", "artificial intelligence", "chatbot", "llm", "gpt"}), "Repo mentions AI/chatbot/LLM")
    add_badge("Intelligent Systems & AI", "Prompt Engineer", "common", repo_any({"prompt", "langchain", "openai", "anthropic", "llm"}), "Repo mentions prompt/langchain/openai/anthropic/llm")
    add_badge("Intelligent Systems & AI", "Model Trainer", "uncommon", repo_any({"training", "fine-tune", "finetune", "model training"}), "Repo mentions model training/fine-tune")
    add_badge("Intelligent Systems & AI", "Neural Network Builder", "rare", repo_any({"neural network", "deep learning", "cnn", "rnn", "lstm", "transformer"}), "Repo mentions neural/deep learning/CNN/RNN/LSTM/transformer")
    add_badge("Intelligent Systems & AI", "AI Systems Designer", "epic", ai_repo_count >= 3, "3+ AI repos")
    add_badge("Intelligent Systems & AI", "Artificial Intelligence Master", "legendary", ai_repo_count >= 5 and has_deploy_signal, "5+ AI repos and deployment signal")

    # 22) Systems Analysis & Design
    add_badge("Systems Analysis & Design", "Requirements Gatherer", "common", repo_any({"documentation", "docs", "requirements"}), "Repo mentions documentation/docs/requirements")
    add_badge("Systems Analysis & Design", "Use Case Writer", "common", repo_any({"use case", "user story", "specification"}), "Repo mentions use case/user story/specification")
    add_badge("Systems Analysis & Design", "System Modeler", "uncommon", repo_any({"uml", "erd", "diagram", "flowchart", "architecture"}), "Repo mentions UML/ERD/diagram/flowchart/architecture")
    add_badge("Systems Analysis & Design", "Process Flow Designer", "rare", repo_any({"system design", "architecture", "blueprint"}), "Repo mentions system design/architecture/blueprint")
    add_badge("Systems Analysis & Design", "SAD Practitioner", "epic", repo_any({"sdlc", "software development lifecycle", "system analysis"}), "Repo mentions SDLC/system analysis")
    add_badge("Systems Analysis & Design", "Systems Analyst", "legendary", sad_repo_count >= 3 and total_commits >= 100, "3+ SAD repos and total_commits >= 100")

    # 23) Computer Organization & Architecture
    add_badge("Computer Organization & Architecture", "Hardware Aware", "common", repo_count_match(lambda row: row["primary_language"] in {"assembly", "c"}) >= 1, "Any repo with Assembly or C as primary language")
    add_badge("Computer Organization & Architecture", "Binary Thinker", "common", repo_any({"binary", "bitwise", "bit manipulation", "hex"}), "Repo mentions binary/bitwise/hex")
    add_badge("Computer Organization & Architecture", "Memory Manager", "uncommon", repo_count_match(lambda row: bool(row["languages"].intersection({"c", "cpp"}) and _contains(row["text"], {"memory", "pointer", "malloc"}))) >= 1, "Repo with C/C++ and memory/pointer/malloc signal")
    add_badge("Computer Organization & Architecture", "Architecture Explorer", "rare", repo_any({"cpu", "memory simulation", "computer architecture", "emulator"}), "Repo mentions CPU/memory simulation/architecture/emulator")
    add_badge("Computer Organization & Architecture", "Low-Level Engineer", "epic", repo_count_match(lambda row: bool(row["languages"].intersection(LOW_LEVEL_LANGS))) >= 3, "3+ repos with C/C++/Assembly")
    add_badge("Computer Organization & Architecture", "Computer Architect", "legendary", repo_any({"cpu simulator", "os", "operating system", "kernel"}), "Repo mentions cpu simulator/os/kernel")

    # 24) Statistics & Quantitative Methods
    add_badge("Statistics & Quantitative Methods", "Stats Starter", "common", repo_any({"statistics", "stats", "statistical"}), "Repo mentions statistics")
    add_badge("Statistics & Quantitative Methods", "Data Summarizer", "common", repo_any({"mean", "median", "mode", "average", "summary"}), "Repo mentions mean/median/mode/average/summary")
    add_badge("Statistics & Quantitative Methods", "Probability Explorer", "uncommon", repo_any({"probability", "distribution", "bayesian", "random"}), "Repo mentions probability/distribution/bayesian/random")
    add_badge("Statistics & Quantitative Methods", "Regression Builder", "rare", repo_any({"regression", "correlation", "linear model", "logistic"}), "Repo mentions regression/correlation/linear/logistic")
    add_badge("Statistics & Quantitative Methods", "Statistical Modeler", "epic", stats_repo_count >= 3, "3+ quantitative/stats repos")
    add_badge("Statistics & Quantitative Methods", "Data Scientist", "legendary", ml_repo_count > 0 and stats_repo_count > 0 and repo_count_match(lambda row: row["primary_language"] == "python") >= 5, "ML signals + stats signals + 5+ Python repos")

    # 25) Web Development Full Coverage
    add_badge("Web Development Full Coverage", "Static Site Builder", "common", static_site_repo_count >= 1, "Any repo with only HTML/CSS languages")
    add_badge("Web Development Full Coverage", "Dynamic Web Dev", "common", dynamic_web_repo_count >= 1, "Any repo with JS/TS + backend language combined")
    add_badge("Web Development Full Coverage", "SPA Developer", "uncommon", repo_any({"spa", "single page", "react app", "vue app"}), "Repo mentions SPA/single page/react app/vue app")
    add_badge("Web Development Full Coverage", "Full Stack Starter", "rare", frontend_repo_count > 0 and backend_repo_count > 0, "Has both frontend and backend repo")
    add_badge("Web Development Full Coverage", "Full Stack Engineer", "epic", full_stack_repo_count >= 3, "3+ full stack repos")
    add_badge("Web Development Full Coverage", "Web Platform Master", "legendary", full_stack_repo_count >= 5 and has_deploy_signal, "5+ full stack repos and deployment signal")

    # 26) Research & Capstone
    add_badge("Research & Capstone", "Research Curious", "common", repo_any({"research", "study", "analysis", "survey"}), "Repo mentions research/study/analysis/survey")
    add_badge("Research & Capstone", "Literature Reviewer", "common", repo_any({"literature", "review", "reference", "citation"}), "Repo mentions literature/review/reference/citation")
    add_badge("Research & Capstone", "Prototype Builder", "uncommon", repo_any({"prototype", "proof of concept", "poc", "mvp"}), "Repo mentions prototype/POC/MVP")
    add_badge("Research & Capstone", "Research Developer", "rare", repo_any({"research system", "research tool", "thesis system"}), "Repo mentions research system/tool/thesis system")
    add_badge("Research & Capstone", "Capstone Engineer", "epic", repo_any({"capstone", "thesis", "final project", " sp "}), "Repo mentions capstone/thesis/final project")
    add_badge("Research & Capstone", "Thesis Defender", "legendary", repo_any({"capstone", "thesis", "final project"}) and has_deploy_signal and total_commits >= 50, "Capstone signal + deployment signal + total_commits >= 50")

    # 27) Academic Integrity & Ethics
    add_badge("Academic Integrity & Ethics", "License Aware", "common", repo_any({"license", "mit", "apache", "open source"}), "Repo mentions license/MIT/apache/open source")
    add_badge("Academic Integrity & Ethics", "Attribution Giver", "common", repo_any({"credits", "contributors", "acknowledgement"}), "Repo mentions credits/contributors/acknowledgement")
    add_badge("Academic Integrity & Ethics", "Ethical Coder", "uncommon", repo_any({"code of conduct", "contributing", "style guide"}), "Repo mentions code of conduct/contributing/style guide")
    add_badge("Academic Integrity & Ethics", "Privacy Implementor", "rare", repo_any({"privacy", "gdpr", "data protection", "anonymization"}), "Repo mentions privacy/GDPR/data protection/anonymization")
    add_badge("Academic Integrity & Ethics", "Responsible Developer", "epic", repo_any({"ethical", "responsible", "bias", "fairness"}), "Repo mentions ethical/responsible/bias/fairness")
    add_badge("Academic Integrity & Ethics", "Digital Ethics Champion", "legendary", ethics_repo_count >= 3, "3+ repos with ethics/privacy/license signals")

    # 28) Package & Dependency Management
    add_badge("Package & Dependency Management", "Package User", "common", repo_any(set(), {"javascript", "typescript", "python"}), "Repo with JS/TS/Python language")
    add_badge("Package & Dependency Management", "Dependency Manager", "common", repo_any({"dependencies", "packages", "requirements", "npm", "pip"}), "Repo mentions dependencies/packages/requirements/npm/pip")
    add_badge("Package & Dependency Management", "Virtual Env User", "uncommon", repo_any({"venv", "virtualenv", "conda", "pipenv", "poetry"}), "Repo mentions venv/virtualenv/conda/pipenv/poetry")
    add_badge("Package & Dependency Management", "Monorepo Explorer", "rare", repo_any({"monorepo", "workspace", "lerna", "turborepo", "nx"}), "Repo mentions monorepo/workspace/lerna/turborepo/nx")
    add_badge("Package & Dependency Management", "Dependency Architect", "epic", repo_any({"library", "sdk", "package", "module"}), "Repo mentions authored library/sdk/package/module")
    add_badge("Package & Dependency Management", "Open Source Publisher", "legendary", repo_count_match(lambda row: row["stars"] >= 10) >= 1, "Any repo with 10+ stars")

    # 29) Project Management & Documentation
    add_badge("Project Management & Documentation", "Issue Tracker", "common", repo_any({"issues", "bug tracker", "task"}), "Repo mentions issues/bug tracker/task")
    add_badge("Project Management & Documentation", "Milestone Setter", "common", repo_any({"milestone", "sprint", "release"}), "Repo mentions milestone/sprint/release")
    add_badge("Project Management & Documentation", "Wiki Writer", "uncommon", repo_any({"wiki", "documentation", "docs site"}), "Repo mentions wiki/documentation/docs site")
    add_badge("Project Management & Documentation", "Project Board User", "rare", repo_any({"kanban", "project board", "trello", "jira"}), "Repo mentions kanban/project board/trello/jira")
    add_badge("Project Management & Documentation", "Agile Practitioner", "epic", repo_any({"agile", "scrum", "sprint", "standup"}), "Repo mentions agile/scrum/sprint/standup")
    add_badge("Project Management & Documentation", "DevProject Manager", "legendary", pm_repo_count >= 3 and total_commits >= 100, "3+ PM repos and total_commits >= 100")

    # 30) Cloud & Deployment
    add_badge("Cloud & Deployment", "Deploy Curious", "common", repo_any({"deploy", "deployment", "vercel", "netlify", "heroku"}), "Repo mentions deploy/deployment/vercel/netlify/heroku")
    add_badge("Cloud & Deployment", "Cloud Starter", "common", repo_any({"cloud", "aws", "gcp", "azure", "firebase"}), "Repo mentions cloud/aws/gcp/azure/firebase")
    add_badge("Cloud & Deployment", "Serverless Explorer", "uncommon", repo_any({"serverless", "lambda", "cloud function", "firebase functions"}), "Repo mentions serverless/lambda/cloud function")
    add_badge("Cloud & Deployment", "Cloud App Builder", "rare", cloud_repo_count >= 2, "2+ repos with cloud/deployment signals")
    add_badge("Cloud & Deployment", "Cloud Engineer", "epic", has_terraform_signal, "Repo with Terraform/HCL/Ansible signal")
    add_badge("Cloud & Deployment", "Cloud Native Master", "legendary", cloud_repo_count >= 5 and (has_container_signal or has_ci_signal), "5+ cloud repos and container/CI signal")

    # 31) Portfolio Presence
    add_badge("Portfolio Presence", "Profile Starter", "common", has_portfolio_settings, "User has portfolio settings")
    add_badge("Portfolio Presence", "Public Showcase", "common", public_repo_count >= 1 and has_portfolio_settings, "Has public repos and portfolio settings")
    add_badge("Portfolio Presence", "Featured Builder", "uncommon", repo_count >= 3 and has_portfolio_settings, "3+ repos and portfolio configured")
    add_badge("Portfolio Presence", "Portfolio Curator", "rare", repo_count >= 5 and len(unique_languages) >= 2 and has_portfolio_settings, "5+ repos, 2+ languages, and portfolio configured")
    add_badge("Portfolio Presence", "Showcase Strategist", "epic", repo_count >= 8 and certificate_total_count >= 1 and has_portfolio_settings, "8+ repos, certificate activity, and portfolio configured")
    add_badge("Portfolio Presence", "Signature Portfolio", "legendary", repo_count >= 12 and certificate_verified_count >= 3 and has_portfolio_settings, "12+ repos, 3+ verified certificates, and portfolio configured")

    # 32) Multi-Language Project Craft
    add_badge("Multi-Language Project Craft", "Dual Stack Repo", "common", repo_count_match(lambda row: len(row["languages"]) >= 2) >= 1, "At least 1 repo uses 2+ languages")
    add_badge("Multi-Language Project Craft", "Tri-Language Repo", "common", repo_count_match(lambda row: len(row["languages"]) >= 3) >= 1, "At least 1 repo uses 3+ languages")
    add_badge("Multi-Language Project Craft", "Hybrid Builder", "uncommon", repo_count_match(lambda row: len(row["languages"]) >= 2) >= 3, "3+ repos use 2+ languages")
    add_badge("Multi-Language Project Craft", "Stack Blender", "rare", repo_count_match(lambda row: len(row["languages"]) >= 3) >= 3, "3+ repos use 3+ languages")
    add_badge("Multi-Language Project Craft", "Polyglot Project Lead", "epic", repo_count_match(lambda row: len(row["languages"]) >= 4) >= 2, "2+ repos use 4+ languages")
    add_badge("Multi-Language Project Craft", "Language Fusion Master", "legendary", repo_count_match(lambda row: len(row["languages"]) >= 5) >= 2, "2+ repos use 5+ languages")

    # 33) Repository Freshness
    add_badge("Repository Freshness", "Fresh Push", "common", repo_count_match(lambda row: row["commit_count"] >= 1) >= 1, "At least 1 repo has commits")
    add_badge("Repository Freshness", "Active Builder", "common", repo_count_match(lambda row: row["commit_count"] >= 10) >= 2, "2+ repos have 10+ commits")
    add_badge("Repository Freshness", "Momentum Maintainer", "uncommon", repo_count_match(lambda row: row["commit_count"] >= 25) >= 2, "2+ repos have 25+ commits")
    add_badge("Repository Freshness", "Deep Work Repo", "rare", repo_count_match(lambda row: row["commit_count"] >= 50) >= 2, "2+ repos have 50+ commits")
    add_badge("Repository Freshness", "Repository Finisher", "epic", repo_count_match(lambda row: row["commit_count"] >= 75) >= 3, "3+ repos have 75+ commits")
    add_badge("Repository Freshness", "Archive of Work", "legendary", repo_count_match(lambda row: row["commit_count"] >= 100) >= 4, "4+ repos have 100+ commits")

    # 34) Full Journey Progress
    add_badge("Full Journey Progress", "Quest Kickoff", "common", daily_quest_claim_count >= 3, "Claimed 3+ daily quests")
    add_badge("Full Journey Progress", "Challenge Tracker", "common", weekly_challenge_claim_count >= 1, "Claimed at least 1 weekly challenge")
    add_badge("Full Journey Progress", "Practice Builder", "uncommon", dimension_count >= 3 or project_path_started_count >= 1, "Build progress in 3+ competency dimensions or begin a repo path")
    add_badge("Full Journey Progress", "High Performer", "rare", high_70_count >= 4 and (project_path_claim_count >= 1 or certificate_reward_claimed_count >= 1), "Reach high scores in 4+ dimensions and complete at least one validated milestone")
    add_badge("Full Journey Progress", "Growth Sprint", "epic", (daily_quest_claim_count >= 10 and weekly_challenge_claim_count >= 3) or (project_path_claim_count >= 2 and certificate_reward_claimed_count >= 1), "Claim 10+ daily quests and 3+ weekly challenges, or complete 2 repo path cycles plus 1 certificate reward")
    add_badge("Full Journey Progress", "Curriculum Marathoner", "legendary", daily_quest_claim_count >= 20 and weekly_challenge_claim_count >= 5 and certificate_verified_count >= 3 and learning_path_completed_count >= 1, "Claim 20+ daily quests, 5+ weekly challenges, verify 3+ certificates, and complete the learning path")

    # 35) Launch & Recognition
    add_badge("Launch & Recognition", "Live Demo Starter", "common", repo_any({"live demo", "demo", "preview", "showcase"}), "Repo mentions live demo/preview/showcase")
    add_badge("Launch & Recognition", "Published Builder", "common", has_deploy_signal, "Repo mentions deployment or live hosting")
    add_badge("Launch & Recognition", "Recognition Earned", "uncommon", stars_xp >= 10 and has_deploy_signal, "10+ stars with at least one deployed project")
    add_badge("Launch & Recognition", "Production Pusher", "rare", repo_count_match(lambda row: row["stars"] >= 1) >= 3 and has_deploy_signal, "3+ repos have stars and at least one deployed project")
    add_badge("Launch & Recognition", "Audience Builder", "epic", stars_xp >= 25 and repo_count >= 5 and has_deploy_signal, "25+ stars, 5+ repos, and deployment signal")
    add_badge("Launch & Recognition", "Campus Tech Standout", "legendary", stars_xp >= 50 and certificate_verified_count >= 2 and has_deploy_signal, "50+ stars, 2+ verified certificates, and deployed work")

    return GamificationResult(
        xp=xp,
        level=level,
        next_level_xp=next_level_xp,
        streak_days=streak_days,
        badges=badges,
    )
