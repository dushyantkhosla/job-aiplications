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
jd_ranker.py — Score and rank a folder of JD JSONs against a CV.
No hard filters. All JDs scored, ranked by total score descending.

Usage: uv run jd_ranker.py cv.yaml jd_folder/
"""
import json, re, sys
from pathlib import Path
from jd_extractor import extract
from ats_score import parse_cv, score

BOILERPLATE = re.compile(
    r'(why apply through|data privacy notice|show more|show less'
    r'|by submitting your application|we appreciate your interest'
    r'|we use artificial intelligence)',
    re.IGNORECASE
)

def strip_boilerplate(text: str) -> str:
    m = BOILERPLATE.search(text)
    return text[:m.start()] if m else text

def main():
    if len(sys.argv) != 3:
        print("Usage: uv run jd_ranker.py cv.yaml jd_folder/")
        sys.exit(1)

    cv       = parse_cv(sys.argv[1])
    jd_files = sorted(Path(sys.argv[2]).glob("*.json"))

    if not jd_files:
        print("No JD JSON files found.")
        sys.exit(1)

    results = []
    for jd_file in jd_files:
        with open(jd_file) as f:
            raw = json.load(f)
        title = raw.get("Title", jd_file.stem)
        desc  = strip_boilerplate(raw.get("Description", ""))

        print(f"  [{jd_file.name}] extracting + scoring...", flush=True)
        try:
            jd = extract(title, desc)
            s  = score(cv, jd)
        except Exception as e:
            print(f"    ✗ failed: {e}")
            continue

        results.append({
            "file":     jd_file.name,
            "title":    title,
            "score":    s.total,
            "sim":      s.semantic_sim,
            "years":    s.years_score,
            "passed":   s.passed,
            "exp_reqs": s.experience_requirements,
            "missing_skills":   s.missing_skills,
            "missing_keywords": s.missing_keywords,
        })

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    print(f"\n{'─'*72}")
    print(f"  {'#':<3} {'Score':<7} {'Sim':<6} {'Yrs':<6}  Title")
    print(f"{'─'*72}")
    for i, r in enumerate(ranked, 1):
        verdict = "✓" if r["passed"] else "✗"
        print(f"  {i:<3} {r['score']:.3f} {verdict}  {r['sim']:.3f}  {r['years']:.2f}  {r['title'][:42]}")
        if r["exp_reqs"]:
            print(f"       exp : {' | '.join(r['exp_reqs'])}")
        if r["missing_skills"]:
            print(f"       gaps: {', '.join(r['missing_skills'][:8])}")
        if r["missing_keywords"]:
            print(f"       kws : {', '.join(r['missing_keywords'][:8])}")
    print(f"{'─'*72}\n")

if __name__ == "__main__":
    main()
