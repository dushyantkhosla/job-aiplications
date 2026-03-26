"""
CV Evaluation Pipeline — 3 parallel HR agents + aggregator
Usage:
    python scripts/evaluate_cv.py \
        --cv rendercv_output/Acme_MLEngineer/Acme_MLEngineer_cv.yml \
        --jd rendercv_input/job_descriptions/Acme_MLEngineer_jd.txt

Models are configured in EVALUATOR_MODELS below. Edit to match your ollama pull list.
"""

import asyncio
import argparse
from pathlib import Path
from datetime import datetime

import yaml
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# Config — edit model names to match what you have pulled in Ollama
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434/v1"

EVALUATOR_MODELS = {
    "technical_screener": "deepseek-r1:8b",   # strong at structured reasoning
    "domain_expert":      "qwen2.5:14b",       # strong at DS/AI domain knowledge
    "hiring_manager":     "qwen2.5:14b",       # leadership / narrative lens
}

AGGREGATOR_MODEL = "qwen2.5:14b"

# Weights for weighted average — domain expert carries most signal
WEIGHTS = {
    "technical_screener": 0.25,
    "domain_expert":      0.45,
    "hiring_manager":     0.30,
}

DIVERGENCE_THRESHOLD = 2.5  # flag if any evaluator deviates > this from weighted mean


# ---------------------------------------------------------------------------
# Pydantic output schemas
# ---------------------------------------------------------------------------

class SectionScores(BaseModel):
    jd_keyword_alignment:       int = Field(ge=1, le=10)
    impact_and_quantification:  int = Field(ge=1, le=10)
    career_progression:         int = Field(ge=1, le=10)
    technical_credibility:      int = Field(ge=1, le=10)
    stakeholder_and_leadership: int = Field(ge=1, le=10)
    structure_and_clarity:      int = Field(ge=1, le=10)

class Issue(BaseModel):
    location: str        # e.g. "Experience > Lavie Beauty > bullet 3"
    problem:  str
    suggested_rewrite: str | None = None

class EvaluatorOutput(BaseModel):
    persona:        str
    overall_score:  int = Field(ge=1, le=10)
    section_scores: SectionScores
    critical_issues:  list[Issue]
    improvements:     list[Issue]
    strengths:        list[str]
    verdict:          str   # Pass / Borderline / Screen Out
    verdict_rationale: str

class AggregatedFeedback(BaseModel):
    role:            str
    company:         str
    evaluated_cv:    str
    timestamp:       str
    weighted_overall_score: float
    section_scores_weighted: dict[str, float]
    divergence_flags: list[str]       # populated if any evaluator is an outlier
    critical_issues:  list[Issue]     # deduplicated union
    improvements:     list[Issue]
    strengths:        list[str]
    verdict:          str             # Pass / Borderline / Screen Out
    summary_for_writer: str           # plain-language brief for the CV writer agent


# ---------------------------------------------------------------------------
# Persona system prompts (loaded from SKILL.md files if present, else inline)
# ---------------------------------------------------------------------------

def load_persona(skill_path: Path, fallback: str) -> str:
    if skill_path.exists():
        return skill_path.read_text()
    return fallback

PERSONA_TECHNICAL = """
You are a senior technical recruiter specialising in data science and AI engineering roles.
Your focus: stack credibility, project depth, quantified outcomes, end-to-end ownership.
You are sceptical of buzzwords without substance. You flag generic skill dumps immediately.
Score strictly — a 7 means genuinely strong, not just adequate.
"""

PERSONA_DOMAIN = """
You are a Principal Data Scientist and hiring advisor with 12 years of experience in ML/AI.
Your focus: methodology rigour, ML maturity, relevance of technical choices to the JD's
domain requirements, evidence of production-grade work (not just notebooks or kaggle).
You understand the difference between a Data Analyst calling themselves an ML Engineer
and the real thing. You weight domain-specific experience heavily.
Score strictly — a 7 means genuinely strong, not just adequate.
"""

PERSONA_MANAGER = """
You are a VP of Data & AI who has built and scaled data science teams at global companies.
Your focus: career narrative, leadership evidence, stakeholder influence, culture fit signals,
and whether this person can operate at the seniority level the JD demands.
You care about what the person built and why it mattered to the business — not just the tech.
Score strictly — a 7 means genuinely strong, not just adequate.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def make_agent(model_name: str, persona: str) -> Agent:
    model = OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url=OLLAMA_BASE_URL),
    )
    return Agent(
        model,
        output_type=EvaluatorOutput,
        system_prompt=persona,
        retries=3,   # local models can mis-format JSON — retry up to 3x
    )


# ---------------------------------------------------------------------------
# Evaluation prompt builder
# ---------------------------------------------------------------------------

def build_eval_prompt(persona_name: str, jd: str, cv_yaml: str) -> str:
    return f"""
You are acting as: {persona_name}

Evaluate the following CV against the job description.
Return your assessment as a structured JSON response matching the required schema exactly.

---
JOB DESCRIPTION:
{jd}

---
TAILORED CV (YAML):
{cv_yaml}

---
Instructions:
- Score each section 1–10. Be strict: 7 = genuinely strong, 10 = exceptional.
- For critical_issues and improvements: always include location, problem, and suggested_rewrite.
- verdict must be exactly one of: "Pass", "Borderline", "Screen Out"
- verdict_rationale: 2–3 sentences max. What is the single most important fix?
"""


# ---------------------------------------------------------------------------
# Weighted aggregation
# ---------------------------------------------------------------------------

def weighted_avg(scores: dict[str, int | float], weights: dict[str, float]) -> float:
    return sum(scores[k] * weights[k] for k in weights) / sum(weights.values())


def aggregate(
    results: dict[str, EvaluatorOutput],
    jd_text: str,
    cv_path: str,
) -> AggregatedFeedback:

    overall_scores = {k: v.overall_score for k, v in results.items()}
    w_overall = round(weighted_avg(overall_scores, WEIGHTS), 2)

    # Per-section weighted average
    section_keys = SectionScores.model_fields.keys()
    section_weighted = {}
    for sk in section_keys:
        raw = {k: getattr(v.section_scores, sk) for k, v in results.items()}
        section_weighted[sk] = round(weighted_avg(raw, WEIGHTS), 2)

    # Divergence flags
    flags = []
    for persona, score in overall_scores.items():
        if abs(score - w_overall) > DIVERGENCE_THRESHOLD:
            flags.append(
                f"{persona} diverges: scored {score} vs weighted mean {w_overall:.1f}. "
                f"Rationale: {results[persona].verdict_rationale}"
            )

    # Union of critical issues (simple concat — aggregator LLM will deduplicate in summary)
    all_critical = [i for r in results.values() for i in r.critical_issues]
    all_improvements = [i for r in results.values() for i in r.improvements]
    all_strengths = list({s for r in results.values() for s in r.strengths})

    # Verdict by weighted majority
    verdicts = [r.verdict for r in results.values()]
    verdict_counts = {v: sum(WEIGHTS[k] for k, rv in zip(results.keys(), verdicts) if rv == v)
                      for v in set(verdicts)}
    final_verdict = max(verdict_counts, key=verdict_counts.get)

    # Plain-language brief for the writer agent
    summary_lines = [
        f"Weighted overall score: {w_overall}/10 — {final_verdict}",
        "",
        "TOP CRITICAL ISSUES (address first):",
    ]
    for i, issue in enumerate(all_critical[:5], 1):
        summary_lines.append(f"  {i}. [{issue.location}] {issue.problem}")
        if issue.suggested_rewrite:
            summary_lines.append(f"     → Suggested: {issue.suggested_rewrite}")
    summary_lines += ["", "TOP IMPROVEMENTS:"]
    for i, issue in enumerate(all_improvements[:5], 1):
        summary_lines.append(f"  {i}. [{issue.location}] {issue.problem}")
        if issue.suggested_rewrite:
            summary_lines.append(f"     → Suggested: {issue.suggested_rewrite}")
    if flags:
        summary_lines += ["", "⚠️  EVALUATOR DIVERGENCE:"] + [f"  - {f}" for f in flags]

    # Parse company/role from JD heuristically (first two lines usually contain them)
    jd_lines = [l.strip() for l in jd_text.strip().splitlines() if l.strip()]
    role    = jd_lines[0] if jd_lines else "Unknown Role"
    company = jd_lines[1] if len(jd_lines) > 1 else "Unknown Company"

    return AggregatedFeedback(
        role=role,
        company=company,
        evaluated_cv=cv_path,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        weighted_overall_score=w_overall,
        section_scores_weighted=section_weighted,
        divergence_flags=flags,
        critical_issues=all_critical,
        improvements=all_improvements,
        strengths=all_strengths,
        verdict=final_verdict,
        summary_for_writer="\n".join(summary_lines),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(cv_path: Path, jd_path: Path) -> None:
    cv_yaml = cv_path.read_text()
    jd_text = jd_path.read_text()

    skill_dir = Path(".github/prompts/hr_skills")
    personas = {
        "technical_screener": load_persona(skill_dir / "technical_screener.md", PERSONA_TECHNICAL),
        "domain_expert":      load_persona(skill_dir / "domain_expert.md",      PERSONA_DOMAIN),
        "hiring_manager":     load_persona(skill_dir / "hiring_manager.md",     PERSONA_MANAGER),
    }

    agents = {
        name: make_agent(EVALUATOR_MODELS[name], persona)
        for name, persona in personas.items()
    }

    print("⏳ Running 3 evaluators in parallel...")
    tasks = {
        name: agent.run(build_eval_prompt(name, jd_text, cv_yaml))
        for name, agent in agents.items()
    }
    raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results: dict[str, EvaluatorOutput] = {}
    for name, result in zip(tasks.keys(), raw_results):
        if isinstance(result, Exception):
            print(f"  ⚠️  {name} failed: {result}")
        else:
            results[name] = result.output
            print(f"  ✅ {name}: {result.output.overall_score}/10 — {result.output.verdict}")

    if not results:
        raise RuntimeError("All evaluators failed. Check Ollama is running and models are pulled.")

    print("\n⏳ Aggregating feedback...")
    feedback = aggregate(results, jd_text, str(cv_path))

    # Write output alongside the CV
    out_dir = cv_path.parent
    out_path = out_dir / "evaluation_feedback.yml"
    with open(out_path, "w") as f:
        yaml.dump(feedback.model_dump(), f, allow_unicode=True, sort_keys=False)

    print(f"\n✅ Feedback written to: {out_path}")
    print(f"\n{'='*60}")
    print(feedback.summary_for_writer)
    print('='*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a tailored CV with 3 HR agents")
    parser.add_argument("--cv",  required=True, help="Path to tailored CV YAML")
    parser.add_argument("--jd",  required=True, help="Path to job description text file")
    args = parser.parse_args()
    asyncio.run(run(Path(args.cv), Path(args.jd)))