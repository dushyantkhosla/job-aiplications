#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "lmstudio",
#   "scikit-learn",
#   "pyyaml",
#   "pydantic",
#   "pydantic-ai[openai]",
# ]
# ///
"""
score_all.py — Score the CV against every JD in jd_extracted.db
and print a ranked table.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

# Ensure local modules resolve
sys.path.insert(0, Path(__file__).parent)

from ats_score import parse_cv, score
from jd_extractor import JobRequirements

CV_PATH = Path(__file__).parent.parent / "rendercv_input" / "base-cv" / "base_v4.yml"
DB_PATH = Path(__file__).parent / "jd_extracted.db"


def row_to_job_requirements(row: dict) -> JobRequirements:
    """Reconstruct a JobRequirements from a DB row."""

    def load(val: str) -> list[str]:
        return json.loads(val) if val else []

    return JobRequirements(
        role_summary=row["role_summary"] or "",
        skills_must_have=load(row["skills_must_have"]),
        skills_preferred=load(row["skills_preferred"]),
        keywords_domain=load(row["keywords_domain"]),
        keywords_technology=load(row["keywords_technology"]),
        key_responsibilities=load(row["key_responsibilities"]),
        differentiators=load(row["differentiators"]),
        experience_requirements=load(row["experience_requirements"]),
        education_requirements=load(row["education_requirements"]),
    )


def main() -> None:
    # Load CV
    cv = parse_cv(str(CV_PATH))
    print(f"CV loaded: {cv.years_exp}y exp, {len(cv.skills)} skills\n")

    # Load all JDs from DB
    conn = sqlite3.connect(DB_PATH)
    cols = [d[1] for d in conn.execute("PRAGMA table_info(extractions)").fetchall()]
    rows = conn.execute("SELECT * FROM extractions").fetchall()

    results = []
    for row in rows:
        rec = dict(zip(cols, row))
        jd = row_to_job_requirements(rec)
        s = score(cv, jd)
        results.append(
            {
                "file": rec["source_file"],
                "title": rec["title"],
                "total": s.total,
                "sim": s.semantic_sim,
                "years": s.years_score,
                "passed": s.passed,
                "exp": s.experience_requirements,
                "missing_skills": s.missing_skills,
                "missing_keywords": s.missing_keywords,
            }
        )

    ranked = sorted(results, key=lambda x: x["total"], reverse=True)

    # Print table
    print(f"{'─' * 72}")
    print(f"  {'#':<3} {'Score':<7} {'Pass':<5} {'Sim':<6} {'Yrs':<6}  Title")
    print(f"{'─' * 72}")
    for i, r in enumerate(ranked, 1):
        mark = "✓" if r["passed"] else "✗"
        title = r["title"][:45] if r["title"] else r["file"]
        print(
            f"  {i:<3} {r['total']:.3f}  {mark}   {r['sim']:.3f}  {r['years']:.2f}  {title}"
        )
        if r["exp"]:
            print(f"       exp : {' | '.join(r['exp'][:2])}")
        if r["missing_skills"]:
            print(f"       gaps: {', '.join(r['missing_skills'][:6])}")
    print(f"{'─' * 72}")
    print(f"\n  Best match: {ranked[0]['title']} ({ranked[0]['total']:.3f})")


if __name__ == "__main__":
    main()
