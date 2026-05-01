#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic-ai[openai]",
#   "pydantic",
# ]
# ///
"""
cv_extractor.py — Extract structured skills from a CV using LM Studio.
Extracts in the same format as JobRequirements for consistent gap comparison.
"""

import json
import os
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings


# ── Schema ────────────────────────────────────────────────────────────────────
class CVSkills(BaseModel):
    """
    CV skill extraction — same field names as JD skills_must_have for diff.

    The gap check uses: set(jd.skills_must_have) - set(cv.skills)
    So field names must match what jd_extractor outputs.
    """

    skills_must_have: list[str] = Field(
        default_factory=list,
        description=(
            "Technical competencies and tools. Short noun phrases only. "
            "e.g. 'python', 'docker', 'snowflake', 'airflow', 'sql'. "
            "Extract ALL technical skills from skills section, highlights, job titles."
        ),
    )

    skills_preferred: list[str] = Field(
        default_factory=list,
        description=(
            "Domain expertise and industry knowledge. "
            "e.g. 'marketing mix modeling', 'propensity modeling', 'time series forecasting'. "
            "Extract from job descriptions and achievements."
        ),
    )

    keywords_technology: list[str] = Field(
        default_factory=list,
        description=(
            "Cloud and infrastructure platforms. "
            "e.g. 'aws', 'gcp', 'azure', 'databricks', 'snowflake'. "
            "Match exact tool names from CV."
        ),
    )

    keywords_domain: list[str] = Field(
        default_factory=list,
        description=(
            "Methodologies and frameworks. "
            "e.g. 'agile', 'mlops', 'a/b testing', 'customer segmentation'. "
            "How the candidate works, not what tools they use."
        ),
    )

    differentiators: list[str] = Field(
        default_factory=list,
        description=(
            "Soft skills and leadership. "
            "e.g. 'team leadership', 'stakeholder management', 'cross-functional collaboration'. "
            "Extract from job titles, team size, and achievement language."
        ),
    )


SYSTEM_PROMPT = """
Extract ALL skills from this CV into the schema provided.

Rules:
- skills_must_have: technical skills, tools, programming languages. Short noun phrases.
  WRONG: "10+ years python"  RIGHT: "python"
  WRONG: "proficient in SQL and databases"  RIGHT: "sql"
- skills_preferred: domain expertise. What industry/methodology knowledge.
  RIGHT: "marketing mix modeling", "propensity modeling", "causal inference"
- keywords_technology: exact cloud/platform names. Lowercase.
  RIGHT: "aws", "gcp", "databricks", "snowflake", "airflow"
- keywords_domain: methodologies, ways of working.
  RIGHT: "agile", "mlops", "a/b testing", "statistical inference"
- differentiators: soft skills, leadership, stakeholder work.
  RIGHT: "team leadership", "stakeholder management", "cross-functional collaboration"

Extract EVERYTHING that appears or is implied in the CV:
- Skills section (explicit)
- Highlights/achievements (implied — if they built models, they have modeling skills)
- Job titles and team descriptions
- Certifications and education

Be exhaustive. One skill per list item. Short noun phrases only.
""".strip()


def _yaml_to_text(path: str) -> str:
    """Convert CV YAML to plain text for LLM consumption."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    cv = raw.get("cv", raw)
    sections = cv.get("sections", {})

    lines = []
    lines.append(f"Name: {cv.get('name', 'N/A')}")
    lines.append(f"Headline: {cv.get('headline', '')}")
    lines.append("")

    # Skills section
    skills_section = sections.get("skills", [])
    if skills_section:
        lines.append("=== SKILLS ===")
        for item in skills_section:
            if isinstance(item, dict):
                label = item.get("label", "")
                details = item.get("details", "")
                lines.append(f"{label}: {details}")
        lines.append("")

    # Experience entries
    exp_section = sections.get("experience", [])
    if exp_section:
        lines.append("=== EXPERIENCE ===")
        for exp in exp_section:
            if isinstance(exp, dict):
                company = exp.get("company", "")
                position = exp.get("position", "")
                highlights = exp.get("highlights", [])
                lines.append(f"{company} -- {position}")
                for h in highlights:
                    if isinstance(h, dict):
                        for bullet in h.get("bullet", []):
                            lines.append(f"  - {bullet}")
                    elif isinstance(h, str):
                        lines.append(f"  - {h}")
        lines.append("")

    # Professional summary
    summary = sections.get("professional_summary", [])
    if summary:
        lines.append("=== SUMMARY ===")
        for item in summary:
            if isinstance(item, dict):
                for bullet in item.get("bullet", []):
                    lines.append(f"- {bullet}")
            elif isinstance(item, str):
                lines.append(f"- {item}")
        lines.append("")

    # Certifications
    certs = sections.get("certifications", [])
    if certs:
        lines.append("=== CERTIFICATIONS ===")
        for item in certs:
            if isinstance(item, dict):
                for bullet in item.get("bullet", []):
                    lines.append(f"- {bullet}")
        lines.append("")

    return "\n".join(lines)


def extract(cv_path: str) -> CVSkills:
    """Extract structured skills from a CV YAML file."""
    text = _yaml_to_text(cv_path)

    agent = Agent(
        model=OpenAIChatModel(
            os.environ.get("LOCAL_MODEL_INFERENCE", "qwen3.5-4b-mlx"),
            provider=OpenAIProvider(
                base_url=os.environ["LMSTUDIO_BASE_URL"], api_key="x"
            ),
        ),
        model_settings=ModelSettings(
            thinking=False,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        ),
        retries=3,
        output_type=CVSkills,
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(user_prompt=f"Extract skills from this CV:\n\n{text}")
    return result.output


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) != 2:
        print("Usage: uv run cv_extractor.py base_v4.yml")
        sys.exit(1)

    result = extract(sys.argv[1])
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
