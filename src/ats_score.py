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
ats_score.py — Score a CV against a JobRequirements object.

Score = cosine(cv_vec, jd_vec) * 0.75 + years_check * 0.25

JD vector is built from extracted JobRequirements fields only — no raw JD text,
no boilerplate. CV vector is built from highlights + skills.

Usage: imported as a module by jd_ranker.py and cv_tailor.py
"""

import os
import re
from dataclasses import dataclass, field
from datetime import date

import lmstudio as lms
import yaml
from sklearn.metrics.pairwise import cosine_similarity

from jd_extractor import JobRequirements

EMBEDDING_MODEL = os.environ.get(
    "LM_STUDIO_EMBEDDING_MODEL", "text-embedding-mxbai-embed-large-v1"
)
PASS_THRESHOLD = 0.55
W = dict(semantic=0.75, years=0.25)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_text(val) -> str:
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return " ".join(_extract_text(v) for v in val.values())
    if isinstance(val, list):
        return " ".join(_extract_text(v) for v in val)
    return ""


def jd_embed_text(jd: JobRequirements) -> str:
    """Signal-only embedding text — no boilerplate, no preferred/differentiators."""
    return " ".join(
        [
            jd.role_summary,
            *jd.skills_must_have,
            *jd.keywords_domain,
            *jd.keywords_technology,
            *jd.key_responsibilities,
        ]
    ).lower()


# ── CV Parser ─────────────────────────────────────────────────────────────────
@dataclass
class CVProfile:
    embed_text: str  # highlights + skills → single CV vector
    years_exp: float
    skills: set[str]  # for skill gap (set diff)
    raw_highlights: list[str]  # for tailor agent context


def parse_cv(path: str) -> CVProfile:
    with open(path) as f:
        raw = yaml.safe_load(f)
    cv = raw.get("cv", raw)
    sections = cv.get("sections", {})

    skills: set[str] = set()
    for item in sections.get("skills", []):
        if isinstance(item, dict) and "details" in item:
            for s in item["details"].split(","):
                skills.add(s.strip().lower())

    def _yr(s) -> float:
        if str(s).lower() in ("present", "now", ""):
            return date.today().year + date.today().month / 12
        parts = str(s).split("-")
        return int(parts[0]) + (int(parts[1]) / 12 if len(parts) > 1 else 0)

    years = 0.0
    for item in sections.get("experience", []):
        if isinstance(item, dict) and "start_date" in item:
            try:
                years += _yr(item.get("end_date", "present")) - _yr(item["start_date"])
            except Exception:
                pass

    highlights, text_parts = [], []
    for section_items in sections.values():
        for item in section_items if isinstance(section_items, list) else []:
            if isinstance(item, dict):
                for h in item.get("highlights", []):
                    t = _extract_text(h)
                    highlights.append(t)
                    text_parts.append(t)
                if item.get("summary"):
                    text_parts.append(_extract_text(item["summary"]))
                if "bullet" in item:
                    text_parts.append(_extract_text(item["bullet"]))

    embed_text = (" ".join(text_parts) + " " + " ".join(skills)).lower()

    return CVProfile(
        embed_text=embed_text,
        years_exp=round(years, 1),
        skills=skills,
        raw_highlights=highlights,
    )


# ── Scoring ───────────────────────────────────────────────────────────────────
@dataclass
class ATSScore:
    total: float
    semantic_sim: float
    years_score: float
    passed: bool
    years_exp: float
    experience_requirements: list[str]  # verbatim, for display
    missing_skills: list[str]  # set diff, for display + tailor
    missing_keywords: list[str]  # domain+tech keywords absent from CV text


def score(cv: CVProfile, jd: JobRequirements) -> ATSScore:
    model = lms.embedding_model(EMBEDDING_MODEL)
    cv_vec, jd_vec = model.embed([cv.embed_text, jd_embed_text(jd)])
    sim = float(cosine_similarity([cv_vec], [jd_vec])[0][0])

    # Years: soft score against max required figure, neutral if none parsed
    req_years = _parse_max_years(jd.experience_requirements)
    if req_years is not None:
        years_score = min(1.0, max(0.0, 0.5 + (cv.years_exp - req_years) / 10))
    else:
        years_score = 0.5  # neutral — not penalised for unparseable JD

    total = W["semantic"] * sim + W["years"] * years_score

    # Gap signals for display and tailor agent
    missing_skills = sorted({s.lower() for s in jd.skills_must_have} - cv.skills)
    all_keywords = [k.lower() for k in jd.keywords_domain + jd.keywords_technology]
    missing_keywords = sorted(k for k in all_keywords if k not in cv.embed_text)

    return ATSScore(
        total=round(total, 3),
        semantic_sim=round(sim, 3),
        years_score=round(years_score, 3),
        passed=total >= PASS_THRESHOLD,
        years_exp=cv.years_exp,
        experience_requirements=jd.experience_requirements,
        missing_skills=missing_skills,
        missing_keywords=missing_keywords,
    )


def _parse_max_years(reqs: list[str]) -> float | None:
    """Extract the largest year figure from verbatim requirement strings."""
    years = []
    for r in reqs:
        for m in re.findall(r"(\d+)\+?\s*years?", r.lower()):
            years.append(float(m))
    return max(years) if years else None
