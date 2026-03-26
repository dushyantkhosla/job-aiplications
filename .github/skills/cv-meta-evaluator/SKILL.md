---
name: cv-meta-evaluator
description: >
  Use this skill when the user asks to evaluate, score, or get feedback on a tailored CV.
  Triggers include: "evaluate my CV", "run the HR evaluation", "score this CV against the JD",
  "spin up the evaluators", "run evaluate_cv.py", or any request to produce evaluation_feedback.yml.
  This skill runs scripts/evaluate_cv.py which spins up 3 parallel HR evaluator agents via
  PydanticAI + Ollama and produces a structured YAML feedback file for the CV writer agent.
---

# CV HR Evaluator Skill

Runs `scripts/evaluate_cv.py` to evaluate a tailored CV against a job description using
3 parallel HR expert agents (PydanticAI + Ollama), then aggregates their scores and feedback
into `evaluation_feedback.yml` alongside the CV.

## Prerequisites

Before running, verify:

1. **Ollama is running locally:**
   ```bash
   ollama serve   # if not already running
   ollama list    # confirm required models are pulled
   ```
   Required models (configured at the top of `evaluate_cv.py`):
   - `deepseek-r1:8b` — technical screener
   - `qwen2.5:14b` — domain expert + hiring manager

2. **Dependencies are installed** in `.venv`:

Check if the required Python packages are installed. If not, install them using:

   ```bash
   uv add pydantic-ai pyyaml
   ```

3. **Input files exist:**
   - Tailored CV YAML: `rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.yml`
   - Job description: `rendercv_input/job_descriptions/<Company>_<Role>_jd.txt`

---

## Running the Evaluation

```bash
.venv/bin/python scripts/evaluate_cv.py \
  --cv rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.yml \
  --jd rendercv_input/job_descriptions/<Company>_<Role>_jd.txt
```

Substitute `<Company>` and `<Role>` with the actual values. If the user hasn't specified
paths, infer them from context (most recently produced CV, or ask).

Expected output:
```
⏳ Running 3 evaluators in parallel...
  ✅ technical_screener: 7/10 — Borderline
  ✅ domain_expert: 6/10 — Borderline
  ✅ hiring_manager: 8/10 — Pass

⏳ Aggregating feedback...
✅ Feedback written to: rendercv_output/<Company>_<Role>/evaluation_feedback.yml
```

---

## Output: evaluation_feedback.yml

Written to the same directory as the tailored CV. Key fields:

```yaml
weighted_overall_score: 6.85      # float — target ≥ 7.5 before sending
verdict: Borderline               # Pass / Borderline / Screen Out
summary_for_writer: |             # plain-language brief — surface this to the user
  Weighted overall score: 6.85/10 — Borderline
  ...
section_scores_weighted:          # per-rubric-dimension weighted averages
  jd_keyword_alignment: 7.2
  impact_and_quantification: 5.9
  ...
critical_issues:                  # fix ALL before re-rendering
  - location: "Experience > Acme > bullet 2"
    problem: "No outcome stated — reads as a responsibility, not an achievement"
    suggested_rewrite: "Reduced model inference latency by 35% by migrating pipeline to ONNX"
improvements:                     # fix as many as possible
  - ...
strengths:                        # do NOT modify these sections
  - "Clear career progression from IC to lead"
divergence_flags:                 # non-empty = evaluators disagreed significantly
  - "domain_expert diverges: scored 4 vs weighted mean 6.9 ..."
```

---

## Interpreting Results

| Score     | Verdict     | Action                                              |
|-----------|-------------|-----------------------------------------------------|
| ≥ 7.5     | Pass        | Ready to send. Review strengths, fix any quick wins.|
| 5.0–7.4   | Borderline  | Iterate. Address all critical issues first.         |
| < 5.0     | Screen Out  | Significant rework needed. Reassess JD fit.         |

### Divergence Flags
If `divergence_flags` is non-empty, surface them to the user verbatim before proceeding:
> "The domain expert scored this significantly lower than the other evaluators.
> Their concern: [rationale]. Do you want to prioritise their feedback?"

---

## Handling Failures

If one evaluator fails (model timeout, JSON parse error after 3 retries), the script
continues with the remaining evaluators and adjusts weights proportionally.
If **all** evaluators fail:
- Check `ollama serve` is running: `curl http://localhost:11434`
- Confirm models are pulled: `ollama list`
- Check `.venv` has `pydantic-ai` installed: `uv pip list | grep pydantic`

---

## After Evaluation — Handing Off to the CV Writer

Once `evaluation_feedback.yml` exists, tell the user:

> "Evaluation complete. Weighted score: **X.X / 10** — **[Verdict]**.
> Open a new Copilot thread and ask it to iterate on the CV using `evaluation_feedback.yml`.
> The CV writer agent knows how to read this file."

Do **not** attempt to edit the CV yourself in this thread. Evaluation and writing are
intentionally separated across threads to avoid self-grading.

---

## Persona Override (Optional)

The three evaluator personas can be overridden by creating Markdown files at:
```
.github/prompts/hr_skills/technical_screener.md
.github/prompts/hr_skills/domain_expert.md
.github/prompts/hr_skills/hiring_manager.md
```
If these files exist, `evaluate_cv.py` loads them automatically in preference to the
inline defaults. Edit them to tune scoring behaviour without touching the Python.

---

## Model Configuration

Models and weights are set at the top of `scripts/evaluate_cv.py`:

```python
EVALUATOR_MODELS = {
    "technical_screener": "deepseek-r1:8b",
    "domain_expert":      "qwen2.5:14b",
    "hiring_manager":     "qwen2.5:14b",
}
WEIGHTS = {
    "technical_screener": 0.25,
    "domain_expert":      0.45,
    "hiring_manager":     0.30,
}
```

Edit these directly to swap models. Domain expert is weighted highest (0.45) as it
provides the most signal for mid-to-senior DS/AI roles.