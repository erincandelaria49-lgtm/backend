from __future__ import annotations

import base64
from collections import Counter
import datetime as dt
import re
from urllib.parse import quote

import requests

GITHUB_API = "https://api.github.com"

# Broad source-code coverage; binaries are excluded later.
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".cs",
    ".go",
    ".rs",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".h",
    ".hpp",
    ".php",
    ".rb",
    ".swift",
    ".scala",
    ".sql",
    ".r",
    ".ipynb",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".sh",
    ".ps1",
    ".md",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".vue",
    ".svelte",
}

SKIP_PATH_PARTS = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".git",
    ".next",
    ".nuxt",
    ".cache",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}

FRAMEWORK_HINTS = {
    "react": ("react", "next/navigation", "next/link"),
    "vue": ("vue", "nuxt"),
    "angular": ("@angular",),
    "svelte": ("svelte",),
    "fastapi": ("fastapi",),
    "flask": ("flask",),
    "django": ("django",),
    "express": ("express",),
    "nestjs": ("nestjs",),
    "spring": ("springframework", "spring boot"),
    "sqlalchemy": ("sqlalchemy",),
    "typeorm": ("typeorm",),
    "prisma": ("prisma",),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "scikit-learn": ("sklearn", "scikit-learn"),
    "tensorflow": ("tensorflow",),
    "pytorch": ("torch", "pytorch"),
}

TEST_HINTS = {
    "pytest": ("pytest",),
    "jest": ("jest",),
    "vitest": ("vitest",),
    "mocha": ("mocha",),
    "cypress": ("cypress",),
    "playwright": ("playwright",),
}

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
)

DEFAULT_TIMEOUT = 25
DEFAULT_MAX_FILE_BYTES = 750_000
DEFAULT_MAX_FILES = 5_000


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _extension(path: str) -> str:
    path = path.lower()
    dot = path.rfind(".")
    return path[dot:] if dot >= 0 else ""


def _is_scannable_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    parts = [part for part in normalized.split("/") if part]
    if any(part in SKIP_PATH_PARTS for part in parts):
        return False
    return _extension(normalized) in CODE_EXTENSIONS


def _is_probably_binary(raw: bytes) -> bool:
    if not raw:
        return False
    if b"\x00" in raw:
        return True
    sample = raw[:4096]
    try:
        sample.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def _repo_default_branch(full_name: str, token: str | None, timeout: int = DEFAULT_TIMEOUT) -> str:
    response = requests.get(
        f"{GITHUB_API}/repos/{full_name}",
        headers=_headers(token),
        timeout=timeout,
    )
    if response.status_code != 200:
        return "main"
    payload = response.json()
    branch = str(payload.get("default_branch") or "").strip()
    return branch or "main"


def _fetch_tree(full_name: str, branch: str, token: str | None, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    branch_ref = quote(branch, safe="")
    response = requests.get(
        f"{GITHUB_API}/repos/{full_name}/git/trees/{branch_ref}",
        headers=_headers(token),
        params={"recursive": "1"},
        timeout=timeout,
    )
    if response.status_code != 200:
        return []
    payload = response.json()
    tree = payload.get("tree") if isinstance(payload, dict) else []
    return tree if isinstance(tree, list) else []


def _fetch_blob(full_name: str, sha: str, token: str | None, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    response = requests.get(
        f"{GITHUB_API}/repos/{full_name}/git/blobs/{sha}",
        headers=_headers(token),
        timeout=timeout,
    )
    if response.status_code != 200:
        return b""
    payload = response.json()
    content = payload.get("content") if isinstance(payload, dict) else ""
    if not content:
        return b""
    encoding = str(payload.get("encoding") or "").lower()
    if encoding == "base64":
        try:
            return base64.b64decode(content, validate=False)
        except Exception:
            return b""
    return str(content).encode("utf-8", errors="ignore")


def _scan_text(path: str, text: str, stats: dict) -> None:
    lowered = text.lower()
    path_lower = path.lower()
    line_count = text.count("\n") + 1
    stats["total_lines"] += line_count

    if "/test" in path_lower or path_lower.endswith("_test.py") or ".spec." in path_lower:
        stats["has_tests"] = True
        stats["test_files"] += 1

    if path_lower.startswith(".github/workflows/"):
        stats["has_ci"] = True
    if "dockerfile" in path_lower or "compose" in path_lower:
        stats["has_docker"] = True
    if "k8s" in path_lower or "kubernetes" in path_lower or "helm" in path_lower:
        stats["has_k8s"] = True

    if "/routes/" in path_lower:
        stats["architecture"].add("routes")
    if "/controllers/" in path_lower:
        stats["architecture"].add("controllers")
    if "/services/" in path_lower:
        stats["architecture"].add("services")
    if "/models/" in path_lower:
        stats["architecture"].add("models")
    if "/components/" in path_lower:
        stats["architecture"].add("components")

    stats["todo_count"] += lowered.count("todo") + lowered.count("fixme")

    for pattern in SECRET_PATTERNS:
        stats["secret_hits"] += len(pattern.findall(text))

    for framework, needles in FRAMEWORK_HINTS.items():
        if any(needle in lowered for needle in needles):
            stats["frameworks"].add(framework)
    for test_fw, needles in TEST_HINTS.items():
        if any(needle in lowered for needle in needles):
            stats["test_frameworks"].add(test_fw)

    # Lightweight import extraction across common languages.
    import_patterns = (
        re.compile(r"^\s*import\s+([a-zA-Z0-9_\.@/-]+)", re.MULTILINE),
        re.compile(r"^\s*from\s+([a-zA-Z0-9_\.@/-]+)\s+import", re.MULTILINE),
        re.compile(r"require\(['\"]([a-zA-Z0-9_\.@/-]+)['\"]\)"),
    )
    for pattern in import_patterns:
        for match in pattern.findall(text):
            token = str(match).strip().lower()
            if token:
                stats["imports"].add(token)


def scan_repo_code_signals(
    full_name: str,
    token: str | None = None,
    default_branch: str | None = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    request_timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    full_name = (full_name or "").strip()
    if not full_name:
        return {}

    branch = (default_branch or "").strip() or _repo_default_branch(full_name, token, timeout=request_timeout)
    tree = _fetch_tree(full_name, branch, token, timeout=request_timeout)
    if not tree:
        return {
            "scan_status": "empty",
            "repo_full_name": full_name,
            "default_branch": branch,
            "scanned_at": dt.datetime.utcnow().isoformat(),
            "keywords": [],
        }

    source_entries = [
        item
        for item in tree
        if str(item.get("type") or "") == "blob"
        and isinstance(item.get("path"), str)
        and isinstance(item.get("sha"), str)
        and _is_scannable_path(str(item.get("path")))
    ]

    stats = {
        "frameworks": set(),
        "test_frameworks": set(),
        "architecture": set(),
        "imports": set(),
        "extension_counts": Counter(),
        "has_tests": False,
        "has_ci": False,
        "has_docker": False,
        "has_k8s": False,
        "test_files": 0,
        "todo_count": 0,
        "secret_hits": 0,
        "total_lines": 0,
        "scanned_files": 0,
        "skipped_large": 0,
        "skipped_binary": 0,
    }

    files_examined = 0
    consecutive_fetch_failures = 0
    for item in source_entries:
        if files_examined >= max_files:
            break
        path = str(item["path"])
        sha = str(item["sha"])
        raw = _fetch_blob(full_name, sha, token, timeout=request_timeout)
        files_examined += 1
        if not raw:
            consecutive_fetch_failures += 1
            if consecutive_fetch_failures >= 30:
                break
            continue
        consecutive_fetch_failures = 0
        if len(raw) > max_file_bytes:
            stats["skipped_large"] += 1
            continue
        if _is_probably_binary(raw):
            stats["skipped_binary"] += 1
            continue
        text = raw.decode("utf-8", errors="ignore")
        stats["extension_counts"][_extension(path) or "no_ext"] += 1
        stats["scanned_files"] += 1
        _scan_text(path, text, stats)

    keywords = set()
    keywords.update(stats["frameworks"])
    keywords.update(stats["test_frameworks"])
    keywords.update(stats["architecture"])
    if stats["has_tests"]:
        keywords.add("testing")
    if stats["has_ci"]:
        keywords.add("ci")
    if stats["has_docker"]:
        keywords.add("docker")
    if stats["has_k8s"]:
        keywords.add("kubernetes")
    for imp in sorted(stats["imports"]):
        if len(imp) <= 40:
            keywords.add(imp)

    scan_status = "ok" if files_examined == len(source_entries) else "partial"
    return {
        "scan_status": scan_status,
        "repo_full_name": full_name,
        "default_branch": branch,
        "scanned_at": dt.datetime.utcnow().isoformat(),
        "tree_source_files": len(source_entries),
        "files_examined": files_examined,
        "scanned_files": stats["scanned_files"],
        "skipped_large_files": stats["skipped_large"],
        "skipped_binary_files": stats["skipped_binary"],
        "total_code_lines": stats["total_lines"],
        "frameworks": sorted(stats["frameworks"]),
        "testing_frameworks": sorted(stats["test_frameworks"]),
        "architecture": sorted(stats["architecture"]),
        "devops": {
            "has_ci": bool(stats["has_ci"]),
            "has_docker": bool(stats["has_docker"]),
            "has_kubernetes": bool(stats["has_k8s"]),
        },
        "testing": {
            "has_tests": bool(stats["has_tests"]),
            "test_files": int(stats["test_files"]),
        },
        "quality": {
            "todo_hits": int(stats["todo_count"]),
            "possible_hardcoded_secrets": int(stats["secret_hits"]),
        },
        "extension_counts": dict(stats["extension_counts"].most_common(20)),
        "keywords": sorted(keywords)[:120],
    }
