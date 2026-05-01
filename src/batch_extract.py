#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic-ai[openai]",
#   "pydantic",
#   "ruff",
# ]
# ///
"""
batch_extract.py — Extract JobRequirements for 25 randomly selected JDs and
store them in src/jd_extracted.db.

DB schema
─────────
CREATE TABLE extractions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file     TEXT    NOT NULL,
    title           TEXT,
    extracted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    role_summary    TEXT,

    skills_must_have         TEXT,   -- JSON list
    skills_preferred         TEXT,   -- JSON list
    keywords_domain          TEXT,   -- JSON list
    keywords_technology      TEXT,   -- JSON list
    key_responsibilities     TEXT,   -- JSON list
    differentiators          TEXT,   -- JSON list
    experience_requirements   TEXT,  -- JSON list
    education_requirements    TEXT   -- JSON list
);
"""

import json
import os
import random
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import jd_extractor

DB_PATH = Path(__file__).parent / "jd_extracted.db"
JD_FOLDER = Path(__file__).parent.parent / "rendercv_input" / "job_descriptions"
N = 25

# ── DB helpers ────────────────────────────────────────────────────────────────

BOILERPLATE_RE = re.compile(
    r"(why apply through|data privacy notice|show more|show less"
    r"|by submitting your application|we appreciate your interest"
    r"|we use artificial intelligence)",
    re.IGNORECASE,
)


def strip_boilerplate(text: str) -> str:
    m = BOILERPLATE_RE.search(text)
    return text[: m.start()] if m else text


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extractions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file     TEXT    NOT NULL,
            title           TEXT,
            extracted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            role_summary    TEXT,

            skills_must_have        TEXT,
            skills_preferred        TEXT,
            keywords_domain         TEXT,
            keywords_technology     TEXT,
            key_responsibilities    TEXT,
            differentiators         TEXT,
            experience_requirements TEXT,
            education_requirements  TEXT
        )
    """)
    conn.commit()
    return conn


def upsert(
    conn: sqlite3.Connection,
    source_file: str,
    title: str,
    req: jd_extractor.JobRequirements,
) -> None:
    """Replace any existing record for the same source_file."""
    import json as _json

    def _j(val: list) -> str:
        return _json.dumps(val, ensure_ascii=False)

    conn.execute(
        """
        INSERT OR REPLACE INTO extractions (
            source_file, title, extracted_at,
            role_summary,
            skills_must_have, skills_preferred,
            keywords_domain, keywords_technology,
            key_responsibilities, differentiators,
            experience_requirements, education_requirements
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            source_file,
            title,
            datetime.now(timezone.utc).isoformat(),
            req.role_summary,
            _j(req.skills_must_have),
            _j(req.skills_preferred),
            _j(req.keywords_domain),
            _j(req.keywords_technology),
            _j(req.key_responsibilities),
            _j(req.differentiators),
            _j(req.experience_requirements),
            _j(req.education_requirements),
        ),
    )
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    json_files = list(JD_FOLDER.glob("*.json"))
    if not json_files:
        print(f"No .json files found in {JD_FOLDER}")
        raise SystemExit(1)

    selected = random.sample(json_files, min(N, len(json_files)))
    print(f"Selected {len(selected)} JDs from {JD_FOLDER}\n")

    conn = init_db()

    for i, jd_path in enumerate(selected, 1):
        print(f"[{i:02d}/{len(selected)}] {jd_path.name} ... ", end="", flush=True)

        # Skip already-extracted JDs (idempotent)
        if conn.execute(
            "SELECT id FROM extractions WHERE source_file = ?", (jd_path.name,)
        ).fetchone():
            print("skip (already done)", flush=True)
            continue

        with open(jd_path) as f:
            raw = json.load(f)

        title = raw.get("Title", "")
        desc = strip_boilerplate(raw.get("Description", ""))

        try:
            req = jd_extractor.extract(title, desc)
            upsert(conn, jd_path.name, title, req)
            print("✓", flush=True)
        except Exception as exc:
            print(f"✗ {exc}", flush=True)
            continue

    print(f"\nDone — {DB_PATH}")


if __name__ == "__main__":
    main()
