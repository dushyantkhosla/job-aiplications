#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "lmstudio",
#   "scikit-learn",
#   "pyyaml",
#   "pydantic",
# ]
# ///
"""
test_score.py — Smoke test: load one JD from jd_extracted.db, reconstruct a
JobRequirements, parse the CV, and run score().
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ats_score import parse_cv, score
from jd_extractor import JobRequirements

CV_PATH = Path(__file__).parent.parent / "rendercv_input" / "base-cv" / "base_v4.yml"
DB_PATH = Path(__file__).parent / "jd_extracted.db"


def row_to_job_requirements(row: dict) -> JobRequirements:
    """Convert a DB row (column names match JobRequirements field names) to an instance."""
    return JobRequirements(
        role_summary=row["role_summary"] or "",
        skills_must_have=json.loads(row["skills_must_have"] or "[]"),
        skills_preferred=json.loads(row["skills_preferred"] or "[]"),
        keywords_domain=json.loads(row["keywords_domain"] or "[]"),
        keywords_technology=json.loads(row["keywords_technology"] or "[]"),
        key_responsibilities=json.loads(row["key_responsibilities"] or "[]"),
        differentiators=json.loads(row["differentiators"] or "[]"),
        experience_requirements=json.loads(row["experience_requirements"] or "[]"),
        education_requirements=json.loads(row["education_requirements"] or "[]"),
    )


def main() -> None:
    # Load one JD from DB
    conn = sqlite3.connect(DB_PATH)
    cols = [d[1] for d in conn.execute("PRAGMA table_info(extractions)").fetchall()]
    row = dict(zip(cols, conn.execute("SELECT * FROM extractions LIMIT 1").fetchone()))

    jd = row_to_job_requirements(row)
    print(f"JD title : {row['title']}")
    print(f"JD file  : {row['source_file']}")
    print()

    # Parse CV
    cv = parse_cv(str(CV_PATH))
    print(f"CV years exp : {cv.years_exp}")
    print(f"CV skills    : {sorted(cv.skills)[:8]}...")
    print()

    # Score
    result = score(cv, jd)
    print(f"─── ATSScore ───────────────────")
    print(f"  Total          : {result.total}")
    print(f"  Semantic sim   : {result.semantic_sim}")
    print(f"  Years score    : {result.years_score}")
    print(f"  Passed         : {result.passed}")
    print(f"  CV years vs JD : {result.years_exp}y")
    print()
    print(f"  Experience requirements : {result.experience_requirements}")
    print(
        f"  Missing skills ({len(result.missing_skills)})   : {result.missing_skills[:8]}"
    )
    print(
        f"  Missing keywords ({len(result.missing_keywords)}): {result.missing_keywords[:8]}"
    )


if __name__ == "__main__":
    main()
