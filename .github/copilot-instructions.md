# CV Tailoring Agent — Copilot Instructions

## Purpose
This repo is used to tailor a base CV (YAML, RenderCV schema) to a specific job description, then produce:
1. A tailored CV as a **PDF** (via RenderCV)
2. A **cover letter** as Markdown (`.md`) and plain text (`.txt`)

---

## Repo Structure
```
.
├── rendercv_input
│   ├── base-cv
│   │   ├── base_v1.yml       # base CV versions — never modify these
│   │   └── base_v2.yml
│   └── job_descriptions      # store JD files here (optional)
└── rendercv_output           # all generated output goes here
```

- Base CVs live in `rendercv_input/base-cv/`. Unless the user specifies, use the **highest-versioned file** as the base.
- Job descriptions can be pasted inline, or saved to `rendercv_input/job_descriptions/` and referenced by filename.
- All output (tailored YAML, CV PDF, cover letter) goes into `rendercv_output/`.

---

## Workflow — Follow These Steps in Order

### Step 1 — Parse Inputs

- Identify which base CV to use (default: highest version in `rendercv_input/base-cv/`)
- Read the job description provided by the user (pasted text, file path, or URL)
- Extract from the JD:
  - Role title and seniority level
  - Company name and industry
  - Hard skills explicitly mentioned
  - Soft skills and culture signals
  - Key responsibilities (ranked by prominence/repetition)
  - Any red-flag requirements the CV cannot satisfy — flag these explicitly to the user

### Step 2 — Tailoring Strategy

Tailoring level: **Moderate to Aggressive**

Apply the following to the YAML:
- **Reorder** sections and bullet points to surface the most JD-relevant content first
- **Rephrase** bullet points to mirror JD language and keywords (without fabricating experience)
- **Drop** items that are irrelevant to this role
- **Amplify** items that directly match key JD requirements — add metrics or specificity where the base CV is vague, if the user can plausibly support it

**IMPORTANT — Show Before You Apply:**
For every non-trivial change (rewrites, drops, reorders), present a diff-style comparison:

```
ORIGINAL: Developed internal dashboards for operations team.
PROPOSED: Built real-time operational dashboards adopted by 3 business units, reducing reporting lag by 40%.
ACTION: [Rephrase + amplify]
```

Group changes by CV section. Ask the user to **accept / reject / modify** each group before writing the final YAML. Do not render the PDF until the user has signed off on the tailored YAML.

### Step 3 — Produce Tailored CV PDF
Once the user approves the YAML:

1. Write the tailored YAML to:
   ```
   rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.yml
   ```

IMPORTANT!

> If the company name is too long, truncate it to a recognizable short form (e.g. "JP Morgan Chase" → "JPMC"). Use `PascalCase` for both company and role, no spaces. Same applies to Role.


2. Run RenderCV using the project's `.venv`:
   ```bash
   .venv/bin/rendercv render rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.yml \
     --pdf-path <Company>_<Role>_cv.pdf \
     --markdown-path <Company>_<Role>_cv.md \
    -nohtml \
    -nopng
   # Remove stray subdirectories created by RenderCV (Typst intermediates)
   find rendercv_output/<Company>_<Role> -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
   ```
   > `--pdf-path` and `--markdown-path` are relative to the **input file's directory**, not the working directory. This places outputs alongside the YAML in `rendercv_output/<Company>_<Role>/`. Do not use `--output-folder` or `--output-folder-name` — both create unwanted nested subdirectories. Always suppress PNG and HTML to avoid stray folders. Do **not** suppress Typst (`--dont-generate-typst`) — PDF generation depends on it; Typst intermediates are cleaned up by the `find` command instead.

3. Confirm the output PDF path to the user.

### Step 4 — Write Cover Letter

Draft a cover letter using this structure:
- **Para 1** — Hook: why this company and this role specifically (use JD signals)
- **Para 2** — Evidence: 2–3 most relevant achievements from the tailored CV
- **Para 3** — Forward-looking: what the candidate brings and what they want to build
- **Sign-off** — Professional, not sycophantic

Tone: confident, direct, specific. No generic filler ("I am excited to apply..."). Mirror the company's communication style if detectable from the JD.

Present the draft to the user for review. Iterate until approved.

### Step 5 — Save Cover Letter

Write the approved cover letter to both:
```
rendercv_output/<Company>_<Role>/cover_letter.md
rendercv_output/<Company>_<Role>/cover_letter.txt
```

---

## File Naming Convention
```
rendercv_input/base-cv/base_vN.yml                          # base CVs — read only
rendercv_input/job_descriptions/<Company>_<Role>_jd.txt    # optional JD storage

rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.yml   # tailored YAML
rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.pdf   # rendered CV PDF
rendercv_output/<Company>_<Role>/cover_letter.md            # cover letter (Markdown)
rendercv_output/<Company>_<Role>/cover_letter.txt           # cover letter (plain text)
```
Use `PascalCase` for `<Company>` and `<Role>`, no spaces.

---

## Constraints — Never Violate These
- Do **not** modify any file in `rendercv_input/base-cv/`
- Do **not** fabricate experience, qualifications, or employers
- Do **not** render the PDF until the user has approved the tailored YAML
- If a JD requirement cannot be addressed by the base CV, flag it explicitly rather than papering over it

---

## RenderCV Notes
- RenderCV is installed in the project `.venv` via `uv` — always invoke as `.venv/bin/rendercv`
- YAML schema: `cv.sections.<section_name>` containing lists of entries
- Themes: `classic`, `harvard`, `moderncv`, `sb2nov`, `engineeringresumes`, `engineeringclassic` — use whatever is set in the base YAML; ask if unset
- Do not `pip install rendercv` — the environment is already configured
- **YAML quoting rule:** Any string value containing `: ` (colon + space) must be wrapped in single quotes, e.g. `- 'Building data literacy: delivering programmes...'`. Unquoted colon-space is a YAML mapping indicator and will cause a validation error.

## Custom Prompts
Two slash-command prompts are available in `.github/prompts/`:
- `/HR-Expert-Evaluator` — simulates a senior HR evaluator scoring the tailored CV against the JD. Run this after Step 3 to catch issues before sending. Input: the JD + tailored YAML.
- `/rendercv` — full RenderCV v2.8 schema reference and CLI guide. Use when debugging YAML structure, design customization, or render options.

---

## Session Start Checklist
When the user starts a new session, confirm:
1. Which base CV to use (default: highest version in `rendercv_input/base-cv/`)
2. Job description (pasted inline, or filename in `rendercv_input/job_descriptions/`)
3. Any sections of the CV that are **off-limits** for modification

---

## Iteration Protocol (Step 3 — Receiving HR Feedback)

When the user starts a session with HR evaluator feedback, the session type is **iteration**, not a fresh tailoring run. Treat it differently:

### Inputs for an Iteration Session
- Original base CV (same as before) 
- Previously tailored YAML (`rendercv_output/<Company>_<Role>/<Company>_<Role>_cv.yml`)
- HR evaluator feedback (pasted by the user)
- The original JD

### How to Process Feedback
1. Parse the HR feedback into three tiers: Critical Issues → Improvements → (Strengths, leave alone)
2. Address **Critical Issues first**, in order of severity
3. For each fix, show a diff-style before/after and get user sign-off — same approval gate as the initial tailoring pass
4. Then address **Improvements**, same process
5. Do **not** touch sections marked as Strengths unless the user asks
6. Do **not** introduce content not present in the base CV — if the HR feedback requests something the base CV cannot support, flag it to the user rather than fabricating it

### Output
- Write revised YAML to `rendercv_output/<Company>_<Role>/<Company>_<Role>_cv_v2.yml` (increment version suffix for each iteration)
- Re-render PDF with `.venv/bin/rendercv render ...`
- Summarise what changed vs. the previous version in a short changelog