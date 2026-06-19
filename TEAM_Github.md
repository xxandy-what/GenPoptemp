# Contributing Guide

## Branching

Branch off `dev` — never commit directly to `main` or `dev`.

```
main          ← stable, SOA-deliverable-ready
dev           ← integration branch

ruby/phase1-ae
eric-ma/panel-data
angela/lit-review
eric-shao/ai-governance
```

Name your branch `yourname/short-description`. Keep it focused on one task per branch

```bash
git checkout dev
git pull origin dev
git checkout -b ruby/modulea
```

---

## Workflow

1. **Pull `dev` first** before starting any new work
2. **Commit often** with clear messages (see below)
3. **Open a PR** into `dev` when your work is ready for review
4. **Haofeng reviews and merges** — don't merge your own PR

---

## Commit Messages

```
# Format: <type>: short description

feat: add A/E ratio calculation by face-amount band
fix: correct CDC mortality age group alignment
data: add 2023 SSA period life table to external/
docs: update methodology section for Phase 1
test: add unit tests for translation_factors.py
```

Types: `feat`, `fix`, `data`, `docs`, `test`, `refactor`, `chore`

---

## Pull Requests

- Title should match your commit style: `feat: XGBoost translation factor model`
- Add a 2–3 line description of what you did and why
- Tag Haofeng as reviewer
- PRs must pass all tests before merge: `uv run pytest`

---

## Code Standards

- **Python:** follow PEP 8; use `ruff` for linting (`uv run ruff check .`)
- **Notebooks:** clear all outputs before committing; number them (`01_eda_ilec.ipynb`)
- **R scripts:** comment all non-obvious steps; use `tidyverse` style
- **No hardcoded paths** — use `config.py` or environment variables
- **No data in commits** — `data/raw/` is gitignored; keep it that way

---

## Data Rules

⛔ **Never commit ILEC data or any raw insured mortality data.**  
`data/raw/` is gitignored. If you're unsure whether a file is sensitive, ask before pushing.

Public data (SSA, CDC, MIM outputs) goes in `data/external/` and is fine to commit.

---

## Questions

Open a GitHub Issue tagged `question`, or message Haofeng directly.
