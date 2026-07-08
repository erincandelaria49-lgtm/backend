from __future__ import annotations

import datetime as dt
import requests
from sqlalchemy.orm import Session

from app.models import CertificateRecord, User

FREECODECAMP_CERTIFICATIONS = [
    {
        "title": "Responsive Web Design",
        "slug": "responsive-web-design",
    },
    {
        "title": "JavaScript Algorithms and Data Structures",
        "slug": "javascript-algorithms-and-data-structures-v8",
    },
    {
        "title": "Front End Development Libraries",
        "slug": "front-end-development-libraries",
    },
    {
        "title": "Data Visualization",
        "slug": "data-visualization",
    },
    {
        "title": "Relational Database",
        "slug": "relational-database-v8",
    },
    {
        "title": "Back End Development and APIs",
        "slug": "back-end-development-and-apis",
    },
    {
        "title": "Quality Assurance",
        "slug": "quality-assurance-v7",
    },
    {
        "title": "Scientific Computing with Python",
        "slug": "scientific-computing-with-python-v7",
    },
    {
        "title": "Data Analysis with Python",
        "slug": "data-analysis-with-python-v7",
    },
    {
        "title": "Machine Learning with Python",
        "slug": "machine-learning-with-python-v7",
    },
]


def _certificate_url(username: str, slug: str) -> str:
    return f"https://www.freecodecamp.org/certification/{username}/{slug}"


def _scan_public_freecodecamp_certificates(username: str) -> dict:
    checked = 0
    found = 0
    items: list[dict] = []

    for cert in FREECODECAMP_CERTIFICATIONS:
        title = cert["title"]
        slug = cert["slug"]
        url = _certificate_url(username, slug)
        checked += 1

        exists = False
        try:
            response = requests.get(url, timeout=10)
            content = (response.text or "").lower()
            exists = response.status_code == 200 and "freecodecamp" in content
        except Exception:
            exists = False

        if not exists:
            continue

        found += 1
        items.append(
            {
                "title": f"freeCodeCamp: {title}",
                "raw_title": title,
                "slug": slug,
                "url": url,
            }
        )

    return {
        "checked": checked,
        "found": found,
        "items": items,
    }


def get_freecodecamp_stats(db: Session, user: User, refresh_public: bool = False) -> dict:
    username = (user.freecodecamp_username or "").strip()
    configured = bool(username)

    rows = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.user_id == user.id, CertificateRecord.provider == "freeCodeCamp")
        .all()
    )
    local_total = len(rows)
    local_pending = sum(1 for row in rows if (row.status or "").lower() == "pending")
    local_verified = sum(1 for row in rows if (row.status or "").lower() == "verified")
    local_rejected = sum(1 for row in rows if (row.status or "").lower() == "rejected")

    checked = len(FREECODECAMP_CERTIFICATIONS) if configured else 0
    found_public = local_total
    public_items: list[dict] = []

    if configured and refresh_public:
        scan = _scan_public_freecodecamp_certificates(username)
        checked = scan["checked"]
        found_public = scan["found"]
        public_items = scan["items"]

    completion = int(round((found_public / checked) * 100)) if checked else 0

    return {
        "provider": "freeCodeCamp",
        "username": username or None,
        "configured": configured,
        "checked": checked,
        "found_public": found_public,
        "public_completion_percent": completion,
        "local_total": local_total,
        "local_pending": local_pending,
        "local_verified": local_verified,
        "local_rejected": local_rejected,
        "last_cert_sync_at": user.last_cert_sync_at.isoformat() if user.last_cert_sync_at else None,
        "items": public_items,
    }


def sync_freecodecamp_certificates(db: Session, user: User) -> dict:
    username = (user.freecodecamp_username or "").strip()
    if not username:
        return {
            "provider": "freeCodeCamp",
            "username": None,
            "checked": 0,
            "found": 0,
            "newly_verified": 0,
            "items": [],
        }

    scan = _scan_public_freecodecamp_certificates(username)
    checked = scan["checked"]
    found = scan["found"]
    newly_verified = 0
    items: list[dict] = []

    for cert in scan["items"]:
        title = cert["raw_title"]
        url = cert["url"]
        row = (
            db.query(CertificateRecord)
            .filter(
                CertificateRecord.user_id == user.id,
                CertificateRecord.certificate_url == url,
            )
            .one_or_none()
        )

        if not row:
            row = CertificateRecord(
                user_id=user.id,
                title=f"freeCodeCamp: {title}",
                provider="freeCodeCamp",
                certificate_url=url,
                status="pending",
                reviewer_note="Auto-detected via freeCodeCamp URL. Awaiting faculty verification.",
            )
            db.add(row)
            newly_verified += 1
        else:
            if row.status == "rejected":
                row.status = "pending"
                row.reviewer_note = "Auto-detected via freeCodeCamp URL. Awaiting faculty verification."
                row.verified_at = None
                newly_verified += 1
        items.append({
            "title": f"freeCodeCamp: {title}",
            "url": url,
            "status": "pending",
        })

    user.last_cert_sync_at = dt.datetime.utcnow()
    db.add(user)
    db.commit()

    return {
        "provider": "freeCodeCamp",
        "username": username,
        "checked": checked,
        "found": found,
        "newly_verified": newly_verified,
        "items": items,
    }
