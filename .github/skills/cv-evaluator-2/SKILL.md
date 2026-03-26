---
name: cv-evaluator-2
description: Evaluates a CV against a job description for mid-to-senior AI/Data roles. Produces a score (1-10) and actionable feedback based on ATS alignment, recruiter screening, and modern CV best practices.
license: MIT
---

# CV Evaluator for AI / Data Roles (2026 Standard)

## 🎯 Purpose

This skill evaluates a candidate CV against a given Job Description (JD) for **mid-to-senior AI, Data Science, and AI Product roles**.

It simulates:
1. **ATS screening (keyword + structure match)**
2. **Recruiter 6–10 second scan**
3. **Hiring manager evaluation**

---

## 📥 Input

Provide:
- `cv`: Candidate CV (plain text or structured)
- `jd`: Job description

---

## 📤 Output

Return:

```yaml
score: <1-10>
ats_score: <0-100%>
verdict: <hire | maybe | reject>
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

🧠 Evaluation Framework

🔴 1. MUST HAVES (Weight: 50%)

Score each from 1–10:

1. Impact-driven bullets
Uses metrics (%, €, $, scale)
Shows outcomes, not responsibilities

Good: Improved ROI by 5% through optimization model
Bad: Responsible for building models

2. AI + Human Readability
- ATS keyword alignment with JD
- Natural language, not keyword stuffing

Check for:

- AI products
- Stakeholders
- ROI / business value
- Adoption
- ML lifecycle / MLOps

3. Strong Top Section
- Clear positioning in first 5–6 lines
- Answers:
  - Who are you?
  - What do you specialize in?
  - What impact do you drive?

4. Clear Specialization
- Candidate is positioned as ONE of:
  - AI Product Leader
  - Data Science Leader
  - ML Engineering Leader

NOT a generic generalist

5. Skills in Context

- Skills reinforced in experience bullets
- Tools tied to outcomes

---

🟡 2. GOOD TO HAVES (Weight: 30%)

1. AI Fluency
- GenAI, LLMs, MLOps, production systems

2. Business Impact Framing
- Talks about:
  - Revenue
  - ROI
  - Efficiency
  - Decision-making

3. Tailoring to JD
- Keywords and phrasing match role
- Relevant experience prioritized

4. Clean Formatting (ATS-safe)
- Simple structure
- No visual/formatting complexity

5. Proof of Work
- GitHub, portfolio, deployed systems

--- 

3. MUST AVOID (Penalty: up to -3 points)

Apply penalties:

-1 to -2 each:

- Responsibility-based bullets
  - “Responsible for…”
  - “Worked on…”
- Generic summary
  - “Looking for a challenging role…”
- Weak verbs
  - “Supported”, “Assisted”, “Helped” (overused)
- Keyword stuffing
  - Skill lists with no context
- Overly vague statements
  - No metrics, no outcomes

---

⚙️ SCORING LOGIC

Step 1: Compute scores
- Must Have average → weight 50%
- Good to Have average → weight 30%
- Penalties → subtract directly

Step 2: Final Score
`final_score = (must_have * 0.5) + (good_to_have * 0.3) - penalties`

Normalize to:

- Minimum: 1
- Maximum: 10

---

🧪 SIMULATION LOGIC

1. ATS Score (0–100%)

Evaluate:
- Keyword match vs JD
- Role alignment
- Structure clarity

2. Recruiter Verdict

Based on:
HIRE
- Clear positioning
- Strong impact
- Direct relevance

MAYBE
- Some relevance
- Weak differentiation

REJECT
- Generic
- No clear fit
- No impact

---

🧾 FEEDBACK GENERATION RULES

Strengths
- What clearly aligns with JD
- What stands out positively

Gaps
- Missing keywords
- Weak positioning
- Lack of metrics or ownership

Must Fix (High Priority)
- Things blocking interviews
- ATS failures
- Positioning issues

Nice to Improve
- Differentiators
- Enhancements
- Rewrite Suggestions

Provide 2–5 concrete rewrites:

```yaml
- before: "Led analytics projects"
  after: "Led analytics initiatives improving marketing ROI by 5% across global campaigns"
```

FINAL OUTPUT EXAMPLE

```yaml
score: 8.9
ats_score: 88%
verdict: hire

strengths:
  - Strong AI product positioning
  - Clear business impact with metrics
  - Good alignment with stakeholder requirements

gaps:
  - Limited mention of change management
  - Weak proof of adoption in some roles

must_fix:
  - Add explicit adoption / business usage signals
  - Strengthen stakeholder ownership language

nice_to_improve:
  - Add portfolio or GitHub examples
  - Include more AI lifecycle details

rewrite_suggestions:
  - before: "Worked on ML models"
    after: "Developed and deployed ML models improving forecast accuracy by 18%"
```