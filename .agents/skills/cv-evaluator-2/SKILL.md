---
name: cv-evaluator-2
description: Evaluates a CV against a job description for mid-to-senior AI/Data roles. Produces a score (1-10) and actionable feedback based on ATS alignment, recruiter screening, and modern CV best practices.
license: MIT
---

# CV Evaluator for AI / Data Roles (2026 Standard)

## Purpose

Evaluate a candidate CV against a given Job Description (JD) for mid-to-senior AI, Data Science, and AI Product roles. Simulate three lenses: ATS screening (keyword + structure match), recruiter 6–10 second scan, and hiring manager evaluation.

---

## Inputs

- `cv`: Candidate CV — provided as YAML (RenderCV schema). Read `cv.sections` for structured content.
- `jd`: Job description (text).

---

## Output Schema

Return exactly this YAML block. No text outside it.

```yaml
score: <1-10>
ats_score: <0-100%>
verdict: <hire | consider | reject>
strengths:
    - ...
gaps:
    - ...
must_fix:
    - ...
nice_to_improve:
    - ...
rewrite_suggestions:
    - before: "..."
      after: "..."
```

---

## Evaluation Framework

### 1. Must-Haves (Weight: 50%)

Score each criterion from 1–10:

1. **Impact-driven bullets** — uses metrics (%, €, $, scale); shows outcomes not responsibilities.
    - Good: "Improved ROI by 5% through optimization model"
    - Bad: "Responsible for building models"

2. **AI + Human Readability** — ATS keyword alignment with JD; natural language, not keyword stuffing. Check for: AI products, stakeholders, ROI/business value, adoption, ML lifecycle/MLOps.

3. **Strong Top Section** — clear positioning in first 5–6 lines. Must answer: Who are you? What do you specialize in? What impact do you drive?

4. **Clear Specialization** — candidate is positioned as one of: AI Product Leader, Data Science Leader, or ML Engineering Leader. Not a generic generalist.

5. **Skills in Context** — skills reinforced in experience bullets; tools tied to outcomes.

### 2. Good-to-Haves (Weight: 30%)

1. **AI Fluency** — GenAI, LLMs, MLOps, production systems.
2. **Business Impact Framing** — revenue, ROI, efficiency, decision-making explicitly referenced.
3. **Tailoring to JD** — keywords and phrasing match role; relevant experience prioritized.
4. **Clean Formatting (ATS-safe)** — simple structure, no visual/formatting complexity.
5. **Proof of Work** — GitHub, portfolio, or deployed systems.

### 3. Must-Avoids (Penalty: up to -3 points)

Apply -1 to -2 per violation:

- Responsibility-based bullets ("Responsible for…", "Worked on…")
- Generic summary ("Looking for a challenging role…")
- Weak verbs overused ("Supported", "Assisted", "Helped")
- Keyword stuffing — skill lists with no context
- Overly vague statements — no metrics, no outcomes

---

## Scoring Formula

```
final_score = (must_have_avg * 0.5) + (good_to_have_avg * 0.3) - penalties
```

Normalize to minimum 1, maximum 10.

**ATS Score:** Evaluate keyword match vs. JD, role alignment, and structure clarity.

**Verdict:**

- `hire` — clear positioning, strong impact, direct relevance
- `consider` — some relevance, weak differentiation
- `reject` — generic, no clear fit, no impact

---

## Feedback Generation Rules

- **Strengths:** What clearly aligns with the JD; what stands out positively.
- **Gaps:** Missing keywords, weak positioning, lack of metrics or ownership.
- **Must Fix:** Things blocking interviews — ATS failures, positioning issues.
- **Nice to Improve:** Differentiators and enhancements.
- **Rewrite Suggestions:** Provide 2–5 concrete before/after rewrites. Example:

```yaml
- before: "Led analytics projects"
  after: "Led analytics initiatives improving marketing ROI by 5% across global campaigns"
```
