# CV Tailoring Agent System

## Purpose

This directory contains a specialized agent system for tailoring CVs to a specific job description. It uses a **panel of four LLM judge evaluators** to independently score the CV against the JD and surface gaps. Each judge produces structured feedback. The agent synthesizes their consensus into a tailoring plan, then works through it **interactively with the user as the human-in-the-loop** — approving each change before it is applied. The workflow concludes with PDF rendering via RenderCV and an optional cover letter.

## Agent Skills

The system is divided into two main skills:

### 1. `cv-tailoring-planner`

- **Purpose**: Orchestrates evaluation and planning phase
- **Steps**: Reads inputs, invokes evaluators, synthesizes consensus, creates tailoring plan
- **Location**: `.agents/skills/cv-tailoring-planner/`

### 2. `cv-tailoring-executor`

- **Purpose**: Executes approval loop and final deliverables
- **Steps**: One-by-one approval, surgical edits, deduplication audit, PDF rendering, cover letter writing
- **Location**: `.agents/skills/cv-tailoring-executor/`

## Supporting Skills

- `cv-evaluator-1` through `cv-evaluator-4`: HR evaluation rubrics
- `rendercv`: RenderCV YAML schema and CLI reference

## Directory Structure

```
.
├── .venv                          # virtual env with rendercv installed
├── .agents
│   └── skills                    # invoke using skills tool via `skill` command
│       ├── cv-tailoring-planner  # Steps 1-2: evaluation & planning
│       ├── cv-tailoring-executor # Steps 3-8: execution & delivery
│       ├── cv-evaluator-1        # HR evaluation rubric (v1)
│       ├── cv-evaluator-2        # HR evaluation rubric (v2)
│       ├── cv-evaluator-3        # HR evaluation rubric (v3)
│       ├── cv-evaluator-4        # HR evaluation rubric (v4)
│       └── rendercv              # RenderCV schema & CLI reference
├── rendercv_input
│   ├── base-cv                   # base CV versions — never modify
│   └── job_descriptions          # JD files stored here
└── rendercv_output               # all generated output
```

## Core Rules

- **NEVER hallucinate facts, locations, metrics, or dates**
- **NEVER modify** files in `rendercv_input/base-cv/`
- **NEVER delete or merge early roles** (gaps are red flags)
- **Change only what the user has explicitly approved**
- **Avoid over-correction** (don't shoehorn JD language)
- **Write shorter sentences** (split long ones)
- **Do not repeat keyword injections** across 2+ bullets

## Usage

1. **Invoke `cv-tailoring-planner`** — pass the job description filename (e.g. `machine_learning_engineer_google.md`). The planner reads the base CV and JD, runs all four evaluators, and outputs a scored tailoring plan.
2. **Review the tailoring plan** — the planner presents aggregated scores, consensus recommendations, and a numbered change list. Read it carefully.
3. **Approve the plan** — reply "approved" (or request changes). The planner will not proceed until you do.
4. **Invoke `cv-tailoring-executor`** — pass the approved plan, job title, company, base CV content, and JD content. The executor works through each change one at a time.
5. **Approve each change** — for every proposed edit, respond Accept / Reject / Modify / Suggest alternative. The executor applies only what you approve.
6. **Approve the final YAML** — after the deduplication audit, the executor presents the complete tailored CV for final sign-off before rendering.
7. **Receive deliverables** — the executor renders the PDF, writes an optional cover letter, and cleans up intermediate files.

Each skill contains detailed instructions for its specific workflow phase.
