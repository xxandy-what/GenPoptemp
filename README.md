# SOA-Pop2Insured-Mortality
RFP by SOA - Population to Insured Mortality Translation

# SOA Population-to-Insured Mortality Translation

> SOA Research Institute funded project | Lead: Haofeng Yu, FSA, MAAA (FolioX)  
> Proposal due: Aug 3, 2026 | Delivery: Aug 2027

## What This Is

Actuaries routinely use general population mortality data (SSA/CDC) to inform insured mortality assumptions — but there is no systematic, defensible methodology for doing so. This project builds one.

We derive empirical translation factors from SOA ILEC intercompany data, develop a MIM-anchored mortality improvement translation methodology, and package everything into an open-source Python tool with an AI explanation layer. Final deliverables are published under SOA Research Institute auspices.

**RFP:** https://www.soa.org/research/opportunities/2026/pop-insured-mort-trans-req/

---

## Research Phases

| Phase | Focus | Methods |
|-------|-------|---------|
| 1 | Population-to-insured translation factors | A/E analysis, log-linear regression, XGBoost, SHAP |
| 2 | Mortality improvement translation | LASSO lag analysis, MIM integration, Lee-Carter, CBD |
| 3 | Decision-support tool + AI layer | Python inference pipeline, Excel front-end, RAG-based narrative generation |

---

## Tech Stack - Tentative

| Layer | Tools                                                  |
|-------|--------------------------------------------------------|
| Data & A/E analysis | Python (pandas, numpy), SQL                            |
| ML models | scikit-learn, XGBoost, LightGBM, SHAP                  |
| Statistical modeling | statsmodels, scipy                                     |
| Mortality improvement | R (Lee-Carter, CBD, MIM workbook)                      |
| RAG / AI layer | LLM prompt chains, vector store, LangChain             |
| Tool packaging | Python + openpyxl / xlwings (Excel front-end) |
| Dashboards | Streamlit                                              |
| Environment | uv + Python 3.12                                       |
| Version control | Git / GitHub                                           |

---

## Repo Structure

```
soa-pop-insured-mortality/
├── data/
│   ├── raw/            # ⛔ gitignored — sensitive ILEC data never committed
│   ├── processed/
│   └── external/       # Public: SSA, CDC WONDER, MIM outputs
├── Scripts/          # Exploratory analysis by phase
├── src/
│   ├── data/           # Ingestion, cleaning, credibility filters
│   ├── phase1/         # A/E analysis, translation factors, ML models
│   ├── phase2/         # MIM integration, lag analysis, credibility blending
│   ├── phase3/         # Inference pipeline, Excel front-end, RAG layer
│   └── utils/
├── r/                  # R scripts: Lee-Carter, CBD, MIM workbook
├── tool/               # Packaged deliverable (Excel + Python backend)
├── reports/            # Markdown drafts: lit review, phase findings
├── tests/
└── docs/               # Methodology, AI governance, user guide
```

---

## Setup

**Requirements:** Python 3.12, uv, R 4.x (for Phase 2 scripts)

```bash
# Clone
git clone https://github.com/[username]/soa-pop-insured-mortality.git
cd soa-pop-insured-mortality

# Create environment and install dependencies
uv sync

# Activate
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
```

In PyCharm: point the interpreter to `.venv/bin/python` (macOS/Linux) or `.venv\Scripts\python.exe` (Windows).

---

## Team

| Name                             | Role                                                             |
|----------------------------------|------------------------------------------------------------------|
| Haofeng Yu, FSA, MAAA            | Lead researcher — methodology, ILEC access, MIM advisory board   |
| Ruby Xi, MS Actuarial Science    | Associate researcher — A/E analysis, ML models, tool development |
| tbd | Collaborator                                                     |
|                           | Research assistant — panel data analysis, R/MIM workbook         |
|                   | Research assistant — literature review, practitioner guide       |
|                         | Research assistant — AI governance, auditability documentation   |

---

## Data

ILEC intercompany data is accessed through the lead researcher's SOA committee role and is **never committed to this repository**. `data/raw/` is gitignored. Public data sources (SSA, CDC WONDER, MIM) are stored in `data/external/`.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, PR process, and code standards.

---

## License

MIT License — see [LICENSE](LICENSE). Research report and deliverables © SOA Research Institute.
