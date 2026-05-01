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
cv_tailor.py — Produce a structured CV edit plan for a given JD.

Inputs to the tailor agent:
  1. Skill gap      : skills_must_have - cv.skills  (set diff)
  2. Missing keywords: domain + tech keywords absent from CV text (substring)
  3. Responsibilities + CV highlights  (LLM compares directly — no embeddings)
  4. Differentiators + experience requirements (tailor context)

Usage: uv run cv_tailor.py cv.yaml jd.json
"""

import json
import os
import re
import sys

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from ats_score import CVProfile, parse_cv, score
from jd_extractor import JobRequirements, extract

LM_STUDIO_MODEL = os.environ.get("LOCAL_MODEL_INFERENCE", "qwen3.5-4b-mlx")

BOILERPLATE = re.compile(
    r"(why apply through|data privacy notice|show more|show less"
    r"|by submitting your application|we appreciate your interest"
    r"|we use artificial intelligence)",
    re.IGNORECASE,
)


def strip_boilerplate(text: str) -> str:
    m = BOILERPLATE.search(text)
    return text[: m.start()] if m else text


# ── Edit plan schema ──────────────────────────────────────────────────────────
class KeywordInjection(BaseModel):
    keyword: str = Field(description="Missing skill or keyword to inject")
    location: str = Field(description="Which CV role or section to add it to")
    rationale: str = Field(description="Why this keyword matters for this JD")


class HighlightRephrase(BaseModel):
    original: str = Field(description="Verbatim existing CV highlight")
    suggested: str = Field(
        description="Rephrased version using JD language — preserve the achievement, adapt the framing"
    )
    covers: str = Field(
        description="Which JD responsibility or keyword this now addresses"
    )


class NewBullet(BaseModel):
    suggested: str = Field(
        description="New highlight bullet — must be grounded in existing CV evidence, no fabrication"
    )
    location: str = Field(description="Which CV role or section to add it under")
    evidences: str = Field(
        description="Which JD differentiator or responsibility this surfaces"
    )


class EditPlan(BaseModel):
    summary: str = Field(
        description="2-3 sentence fit assessment and tailoring priority"
    )
    keyword_injections: list[KeywordInjection]
    highlight_rephrases: list[HighlightRephrase]
    new_bullets: list[NewBullet]
    strong_fits: list[str] = Field(
        description="CV highlights that already align well — leave untouched"
    )


# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert CV editor helping a candidate tailor their CV for a specific role.

You will receive:
- Structured JD requirements (role, skills, responsibilities, differentiators)
- Skill gaps: required skills absent from the CV
- Missing keywords: domain and technology terms not present in the CV
- The candidate's existing CV highlights (verbatim)

Produce a precise, actionable EditPlan. Rules:
- keyword_injections: only suggest skills the candidate plausibly has based on their highlights. Never fabricate.
- highlight_rephrases: reframe existing bullets using JD language. Preserve the underlying achievement — change the framing and vocabulary.
- new_bullets: only where there is latent evidence in the CV. Surface it, do not invent it.
- strong_fits: highlights that already align well and need no changes.
- Quote actual CV text verbatim in all 'original' fields.
- Write production-ready copy in all 'suggested' fields — confident, evidence-anchored, no overclaiming.
""".strip()


# ── Context builder ───────────────────────────────────────────────────────────
def build_context(
    cv: CVProfile,
    jd: JobRequirements,
    missing_skills: list[str],
    missing_keywords: list[str],
) -> str:
    nl = "\n"
    return f"""
ROLE: {jd.role_summary}

MUST-HAVE SKILLS   : {", ".join(jd.skills_must_have)}
PREFERRED SKILLS   : {", ".join(jd.skills_preferred)}
DOMAIN KEYWORDS    : {", ".join(jd.keywords_domain)}
TECHNOLOGY KEYWORDS: {", ".join(jd.keywords_technology)}
DIFFERENTIATORS    : {", ".join(jd.differentiators)}
EXPERIENCE REQUIRED: {" | ".join(jd.experience_requirements)}

KEY RESPONSIBILITIES:
{nl.join(f"- {r}" for r in jd.key_responsibilities)}

SKILL GAPS (required, missing from CV):
{", ".join(missing_skills) or "none"}

MISSING KEYWORDS (not present in CV text):
{", ".join(missing_keywords) or "none"}

CANDIDATE CV HIGHLIGHTS:
{nl.join(f"- {h}" for h in cv.raw_highlights)}
""".strip()


# ── Tailor agent ──────────────────────────────────────────────────────────────
def generate_edit_plan(
    cv: CVProfile,
    jd: JobRequirements,
    missing_skills: list[str],
    missing_keywords: list[str],
) -> EditPlan:
    agent = Agent(
        model=OpenAIChatModel(
            LM_STUDIO_MODEL,
            provider=OpenAIProvider(
                base_url=os.environ["LMSTUDIO_BASE_URL"], api_key="x"
            ),
        ),
        model_settings=ModelSettings(
            thinking=False,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        ),
        retries=3,
        output_type=EditPlan,
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(
        user_prompt=build_context(cv, jd, missing_skills, missing_keywords)
    )
    return result.output


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) != 3:
        print("Usage: uv run cv_tailor.py cv.yaml jd.json")
        sys.exit(1)

    with open(sys.argv[2]) as f:
        raw = json.load(f)
    title = raw.get("Title", "")
    desc = strip_boilerplate(raw.get("Description", ""))

    print("[ 1/4 ] Parsing CV ...", flush=True)
    cv = parse_cv(sys.argv[1])

    print("[ 2/4 ] Extracting JD ...", flush=True)
    jd = extract(title, desc)

    print("[ 3/4 ] Computing gaps ...", flush=True)
    s = score(cv, jd)

    print("[ 4/4 ] Generating edit plan ...", flush=True)
    plan = generate_edit_plan(cv, jd, s.missing_skills, s.missing_keywords)

    # ── Output ────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 62}")
    print(f"  CV EDIT PLAN — {title[:46]}")
    print(
        f"  Score: {s.total:.3f} ({'PASS ✓' if s.passed else 'REJECT ✗'})"
        f"  |  sim {s.semantic_sim:.3f}  |  {cv.years_exp}y exp"
    )
    print(f"{'═' * 62}")
    print(f"\n  {plan.summary}\n")

    if plan.keyword_injections:
        print(f"  ── Keyword injections ({len(plan.keyword_injections)}) ──")
        for ki in plan.keyword_injections:
            print(f"  + {ki.keyword:<28} → {ki.location}")
            print(f"    {ki.rationale}\n")

    if plan.highlight_rephrases:
        print(f"  ── Rephrases ({len(plan.highlight_rephrases)}) ──")
        for hr in plan.highlight_rephrases:
            print(f"  covers : {hr.covers}")
            print(f"  BEFORE : {hr.original}")
            print(f"  AFTER  : {hr.suggested}\n")

    if plan.new_bullets:
        print(f"  ── New bullets ({len(plan.new_bullets)}) ──")
        for nb in plan.new_bullets:
            print(f"  [{nb.location}] ← evidences '{nb.evidences}'")
            print(f"  • {nb.suggested}\n")

    if plan.strong_fits:
        print(f"  ── Leave untouched ({len(plan.strong_fits)}) ──")
        for h in plan.strong_fits:
            print(f"  ✓ {h}")

    print(f"\n{'═' * 62}\n")


if __name__ == "__main__":
    main()
