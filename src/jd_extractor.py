#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic-ai[openai]",
#   "pydantic",
# ]
# ///
"""
jd_extractor.py — Extract structured requirements from a JD via LM Studio.
Usage: uv run jd_extractor.py jd.json
"""

import json
import os
import sys

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings


# ── Schema ────────────────────────────────────────────────────────────────────
class JobRequirements(BaseModel):
    """
    Structured JD extraction — only fields consumed by the scorer or tailor agent.

    Embedding text:  role_summary + skills_must_have + keywords_domain
                     + keywords_technology + key_responsibilities
    Skill gap:       skills_must_have (set diff vs CV)
    Missing keywords: keywords_domain + keywords_technology (substring check vs CV)
    Tailor context:  everything + skills_preferred + differentiators
    Display only:    experience_requirements, education_requirements
    """

    role_summary: str = Field(
        default="",
        description=(
            "2-3 sentence summary of what this role is fundamentally about. "
            "Focus on purpose, scope, and primary impact — not requirements."
        ),
    )
    skills_must_have: list[str] = Field(
        default_factory=list,
        description=(
            "Specific competencies and domain knowledge explicitly required. "
            "Short noun phrases only — e.g. 'data modelling', 'people leadership', 'KPI framework design'. "
            "Do NOT include experience year statements — those go in experience_requirements."
        ),
    )
    skills_preferred: list[str] = Field(
        default_factory=list,
        description=(
            "Nice-to-have or implied competencies. "
            "Same format as skills_must_have. Only include if clearly marked as preferred/bonus."
        ),
    )
    keywords_domain: list[str] = Field(
        default_factory=list,
        description=(
            "Domain and sector concepts central to this role. "
            "e.g. 'incrementality measurement', 'brand equity', 'crypto exchanges', 'B2C growth'. "
            "No tools or technologies here."
        ),
    )
    keywords_technology: list[str] = Field(
        default_factory=list,
        description=(
            "Specific tools, platforms, and technologies mentioned. "
            "e.g. 'Python', 'dbt', 'Snowflake', 'Airflow'. "
            "Return [] if none are explicitly stated — do not infer."
        ),
    )
    key_responsibilities: list[str] = Field(
        default_factory=list,
        description=(
            "Core responsibilities as flat strings. "
            "Each item should be one concrete responsibility. "
            "Aim for 5-8 items covering the full scope of the role."
        ),
    )
    differentiators: list[str] = Field(
        default_factory=list,
        description=(
            "What separates a strong candidate from a baseline one for this specific role. "
            "Infer from emphasis, repeated themes, and explicit 'we value' signals in the JD."
        ),
    )
    experience_requirements: list[str] = Field(
        default_factory=list,
        description=(
            "Verbatim or lightly cleaned experience requirement strings. "
            "Capture each distinct requirement separately. "
            "e.g. ['10+ years in data-related roles', '3+ years in senior leadership']. "
            "Preserve the nuance — do not collapse into a single number."
        ),
    )
    education_requirements: list[str] = Field(
        default_factory=list,
        description=(
            "Verbatim education requirement strings if stated. "
            "Return [] if not mentioned — do not infer."
        ),
    )


# ── Agent ─────────────────────────────────────────────────────────────────────
LM_STUDIO_MODEL = os.environ.get("LOCAL_MODEL_INFERENCE", "qwen3.5-4b-mlx")

SYSTEM_PROMPT = """
You are a senior technical recruiter. Extract structured requirements from job descriptions into the exact schema provided.

Rules:
- skills_must_have: competencies only, not experience durations. Short noun phrases.
  WRONG: "10+ years in data roles"  RIGHT: "data modelling", "people leadership"
- keywords_technology: explicit tools only. If none mentioned, return [].
- keywords_domain: sector/domain concepts. No tools or technologies.
- experience_requirements: verbatim strings, one per distinct requirement.
- education_requirements: verbatim only, return [] if not stated.
- differentiators: what makes a strong candidate stand out for THIS role specifically.
- Extract only what is stated or very clearly implied. Do not infer or fabricate.
""".strip()


def extract(title: str, description: str) -> JobRequirements:
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
        output_type=JobRequirements,
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(
        user_prompt=f"Job title: {title}\n\nJob description:\n{description}"
    )
    return result.output


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) != 2:
        print("Usage: uv run jd_extractor.py jd.json")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        jd = json.load(f)
    result = extract(jd.get("Title", ""), jd.get("Description", ""))
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
