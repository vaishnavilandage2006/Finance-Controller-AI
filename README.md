# Finance Controller AI

**Detect → Investigate → Decide → Audit → Predict**

Finance Controller AI turns financial transactions into an intelligent control loop: it reconciles records, detects anomalies, scores risk, routes exceptions to human review, keeps every action auditable, and grounds forecasting, scenario simulation, and an AI Copilot in the backend's deterministic finance engine.

This is not just another financial dashboard. It connects financial exceptions to investigation, human decisions, auditability, forecasting, and management insight — modern finance already has automation; the control workflow is what is usually fragmented across systems.

🔗 **Live demo:** https://finance-controller-ai-production.up.railway.app/

---

## Table of contents

- [Problem statement](#problem-statement)
- [What this project implements](#what-this-project-implements)
- [Architecture](#architecture)
- [Data flow: from upload to insight](#data-flow-from-upload-to-insight)
- [Current run and historical runs](#current-run-and-historical-runs)
- [Reconciliation](#reconciliation)
- [Risk vs anomaly vs reconciliation](#risk-vs-anomaly-vs-reconciliation)
- [Forecasting and scenario simulation](#forecasting-and-scenario-simulation)
- [CFO Command Center](#cfo-command-center)
- [AI Copilot](#ai-copilot)
- [Razorpay integration (test mode)](#razorpay-integration-test-mode)
- [Security](#security)
- [Performance](#performance)
- [Testing](#testing)
- [API reference](#api-reference)
- [Repository structure](#repository-structure)
- [Local setup](#local-setup)
- [Environment variables](#environment-variables)
- [Deployment](#deployment)
- [Demo flow](#demo-flow)
- [Current limitations](#current-limitations)
- [Relevance to the Finance Controller challenge](#relevance-to-the-finance-controller-challenge)

---

## Problem statement

Finance teams work across transaction files, spreadsheets, reconciliation systems, reports, and manual review processes. That fragmentation creates a control problem:

- Large transaction datasets are hard to investigate.
- Reconciliation is slow and manual, or happens in a tool disconnected from review.
- Anomalies and high-risk exceptions are hard to find and prioritize.
- Human decisions often lack a traceable audit trail.
- CFO reporting, forecasting, and scenario planning are disconnected from the exceptions that matter.
- A newly uploaded dataset may not propagate to every downstream view, so different screens show different "current" numbers.

The result is a workflow where finance teams spend their time **finding problems instead of acting on them**.

## What this project implements

A single platform that connects ingestion, validation, reconciliation, risk/anomaly detection, human review, audit, analytics, forecasting, scenario simulation, CFO reporting, and a grounded AI Copilot. Every stage is backed by the FastAPI backend; the frontend is a React/TypeScript SPA.

| Feature | What it does | Where |
|---|---|---|
| **CSV ingestion & validation** | Parses uploaded CSVs with schema detection, per-row validation, duplicate-ID rejection, formula-injection guard, 10 MB / 100 k-row caps | `backend/app/services/csv/processor.py`, `POST /api/import` |
| **Single-file reconciliation** | Compares bank/ledger/settlement amount columns within one CSV; emits `MATCHED` / `PARTIAL` / `MISMATCH` / `UNMATCHED` / `DUPLICATE` | `POST /api/reconciliation/single-file` |
| **Multi-file reconciliation** | Matches bank + ledger (+ optional settlement) files by reference with fuzzy amount/date/description scoring | `POST /api/reconciliation/multi-file` |
| **Reconciliation exceptions** | Exceptions (everything not matched) become review items with variance and reason | `ReviewItem`, Review Center |
| **Risk scoring** | Deterministic, materiality-aware scoring of reconciliation exceptions (variance bands + ratio/amount bonuses) | `backend/app/services/risk/engine.py` |
| **Anomaly detection** | Independent statistical engine (robust z-score, repeated amounts, merchant concentration, refund/fee patterns) | `backend/app/services/anomaly/engine.py` |
| **Review Center** | Human-in-the-loop queue: open items, evidence, approve/reject/escalate/resolve actions with RBAC | `PATCH`/`POST /api/review/*` |
| **Audit trail** | Login, imports, reconciliation runs, review actions, Copilot queries | `AuditLog`, `GET /api/audit` |
| **Analytics / Dashboard** | Current-run KPIs, reconciliation health, risk distribution, top exceptions | `GET /api/dashboard`, `GET /api/analytics` |
| **Forecasting** | Deterministic 30-day baseline from the current run's dated transactions (daily average + linear trend); series honestly unavailable when there is no data | `GET /api/forecast` |
| **Scenario simulator** | Deterministic what-if projections (revenue/expense/refund/fee/volume changes); `available: false` when financial dimensions are absent | `POST /api/scenarios` |
| **CFO Command Center** | Executive report: KPIs, cash-flow trend, expense breakdown, anomalies, review workload, alerts, forecast, scenario insights, audit trail, control context | `GET /api/reports/cfo` (role-gated) |
| **Alerts** | Deterministic control alerts (high-risk count, reconciliation rate below 95%) | `GET /api/alerts` |
| **AI Copilot** | Role-scoped, current-run-grounded Q&A; rule-based mock by default with optional OpenAI/Gemini providers and safe fallback | `POST /api/copilot` |
| **Razorpay test-mode adapter** | Fetches test payments, normalizes them into the import contract, pushes through the same pipeline (read-only, test mode only) | `GET/POST /api/razorpay/*` |

## Architecture

```mermaid
flowchart TB
    U[User] --> FE[React + TypeScript SPA]
    FE --> API[FastAPI /api]
    API --> AUTH[Auth: JWT + RBAC]
    AUTH --> ENG[Finance Control Engine]
    ENG --> DB[(PostgreSQL / SQLite)]
    DB --> REC[Reconciliation engine]
    DB --> RSK[Risk engine]
    DB --> ANO[Anomaly engine]
    REC --> RQ[Review queue]
    RQ --> AUD[Audit log]
    ENG --> ANL[Analytics / Forecast / Scenarios]
    ENG --> CFO[CFO Command Center]
    ENG --> COP[AI Copilot]
    COP --> PROV[AI provider: Mock / OpenAI / Gemini]
```

The application is deployed as a single Docker image that serves the built frontend and the FastAPI backend together (see [Deployment](#deployment)).

## Data flow: from upload to insight

The pipeline, as implemented:

```text
CSV upload
  ↓  validate_csv (schema, per-row checks, size caps, injection guard)
  ↓  persistence (Transaction rows)
  ↓  reconciliation run created (run_id: REC-… / IMP-…)
  ↓  exception risk scored (risk engine, run-isolated)
  ↓  statistical anomaly detection (independent engine)
  ↓  review items created for exceptions
  ↓  audit log entries
  ↓  dashboard / transactions / risk / anomalies / review
  ↓  analytics / forecast / scenarios / CFO report / Copilot (all run-scoped)
```

Three entry points create a run:

1. **`POST /api/import`** — validates and stores a finance CSV (requires `transaction_id, date, amount, type, status` columns), classifies each row matched/mismatch/unmatched from `settlement_amount`, runs the independent statistical anomaly engine on the imported rows, and records a run with mode `import`.
2. **`POST /api/reconciliation/single-file`** — detects amount columns (bank/ledger/settlement aliases) inside one file and reconciles them per row, with a monetary tolerance of ₹0.01.
3. **`POST /api/reconciliation/multi-file`** — takes bank + ledger (+ optional settlement) CSVs, detects each file's role from schema signals, reconciles across sources by reference with fuzzy date/description matching.

Every run persists a `ReconciliationRun` row (run_id, mode, filenames, counts, match rate, total variance) plus run-scoped `ReconciliationResult`, `RiskAssessment`, `ReviewItem`, and `Anomaly` rows.

## Current run and historical runs

The single most important data concept in this system is the **current reconciliation run**.

- Every import or reconciliation creates a run with a unique `run_id` (e.g. `REC-20260905015503297149`).
- `current_run()` in `backend/app/services/finance/engine.py` resolves the **latest completed run** — the single authoritative dataset the UI operates on.
- All downstream modules default to that run and never silently mix it with historical rows:
  - `metrics()` (dashboard, analytics, alerts, CFO, Copilot) — reconciliation summary, risk distribution (via the `source_run:<run_id>` risk marker), financial metrics (with honest availability flags), top exceptions, and total counts all come from the current run.
  - `GET /transactions` — limited to the current run's transaction IDs.
  - `GET /reconciliation`, `GET /risk`, `GET /anomalies`, `GET /review` — default to the current run.
  - `GET /forecast` and the CFO report — computed from the current run's dated transactions.
  - `POST /copilot` — context is built from the current run (plus the previous run for "what changed" questions).

- **Historical runs are never deleted.** Each endpoint accepts an optional `run_id` query parameter to view any earlier run. Uploading dataset B after dataset A switches every current-run view to B; A remains accessible by its `run_id`.
- A fresh database with no runs keeps a documented legacy global-aggregation fallback so directly seeded transactions still work.
- Run isolation is enforced with markers: risk rows embed `source_run:<run_id>` in `risk_factors`; anomaly rows embed `Run <run_id>` in their evidence.

Verified end-to-end by `backend/tests/test_current_run_propagation.py` (13 tests): a new upload becomes the current run, dashboard totals match the run (200, not a historical 1301), reconciliation stays at 40 exceptions / ₹3,575 variance / 80% match rate, risk/anomaly/forecast/CFO/Copilot all consume the current run, and historical rows remain intact.

## Reconciliation

Implemented in `backend/app/services/reconciliation/adaptive.py` (production path) with a legacy module `multi_file.py` covered by its own tests.

- **Column detection** — flexible aliases for reference, amounts (bank/ledger/settlement), dates, fees, parties, currency; source-role detection for multi-file uploads. Files that can't be mapped return structured validation errors with `available_columns` and `suggested_columns` hints.
- **Monetary tolerance** — ₹0.01.
- **Statuses** — `MATCHED`, `PARTIAL` (some evidence missing, e.g. no settlement file), `MISMATCH` (amounts differ), `UNMATCHED` (no counterpart), `DUPLICATE` (repeated reference). `match_rate = matched / total`.
- **Variance** — single-file: explicit `amount` vs `settlement_amount`, or spread across bank/ledger/settlement amounts; multi-file: spread across matched sources. Fees, refunds, and adjustments are evidence only and are never auto-deducted to invent an expected settlement.
- **Output** — each record carries status, variance (absolute and signed), expected/actual amounts, variance %, reason, evidence, confidence, and matched sources; summaries include total variance and match rate.
- **Exceptions** — every non-matched record becomes an `OPEN` ReviewItem and is scored by the risk engine for the run.

## Risk vs anomaly vs reconciliation

These three are deliberately independent concepts:

| Signal | Meaning | Engine |
|---|---|---|
| **Reconciliation exception** | A record that did not match cleanly across its sources (`PARTIAL` / `MISMATCH` / `UNMATCHED` / `DUPLICATE`) | reconciliation engine |
| **Risk** | Materiality-aware severity of an exception (variance bands, ratio and amount bonuses → LOW / MEDIUM / HIGH / CRITICAL) | `risk/engine.py: assess_exception` |
| **Anomaly** | Statistical deviation from the dataset's own behavior (robust z-score outliers, repeated amounts, merchant concentration, refund/fee patterns) | `anomaly/engine.py` (independent) |

A transaction can be **matched AND statistically anomalous**, **an exception AND statistically normal**, or both/neither. Reconciliation exceptions are *not* automatically anomalies. One documented coupling exists: HIGH/CRITICAL **exceptions** are also surfaced as anomalies so controllers see them in the anomaly view — the statistical engine itself remains separate and is run independently on every import.

## Forecasting and scenario simulation

**Forecasting** (`GET /forecast`, and the CFO report) is a deterministic baseline: daily revenue/expense/refund/fee totals from the current run's dated transactions, projected over a 30-day horizon using the trailing daily average plus a linear (least-squares) trend. It requires at least 30 dated transactions and never fabricates confidence intervals. Series with no non-zero observations are reported as `available: false` — never as fake ₹0 forecasts.

**Scenario simulation** (`POST /scenarios`) applies user-specified changes (revenue, expenses, refunds, fees, volume) to the current financial position as a deterministic what-if projection. If the current run's schema carries no revenue/expense dimension, the response is `available: false` with an explicit note instead of pretending there is a zero-based P&L to simulate.

## CFO Command Center

`GET /api/reports/cfo` (requires a CFO/manager-tier role) returns a unified executive report:

- **metrics** — the current-run KPIs from `metrics()`.
- **cash_flow_trend** and **expense_breakdown** — run-scoped charts.
- **anomalies** — total, by severity, recent items (run-scoped).
- **review_workload** — open / attention / by-status counts.
- **alerts** — the same deterministic control alerts as `GET /alerts`.
- **forecast** and **scenario_insights** — deterministic outlook plus reference scenarios.
- **audit_trail** — latest 10 control actions.
- **control_context** — run_id, generated timestamp, trace note.

The frontend Command Center renders KPIs with an explicit **Unavailable** state (with reason) when a financial dimension is not present in the current run's schema, so it never displays a misleading ₹0.

## AI Copilot

The Copilot is a **decision-support layer, not the source of truth**. All financial numbers come from the backend's deterministic engines; the AI explains, summarizes, prioritizes, and recommends — it cannot approve, reject, pay, delete, or modify anything.

```mermaid
flowchart LR
    FE[Frontend] -->|POST /api/copilot + JWT| API[FastAPI]
    API --> CTX[Build current-run context<br/>metrics + reconciliation + risk + review + anomalies + previous run]
    CTX --> SCOPE[Server-side role scoping<br/>scope_ai_context]
    SCOPE --> PROV[AI provider]
    PROV --> VAL[Response validation]
    VAL -->|valid| ANS[Grounded answer + disclosure]
    VAL -->|invalid / error / timeout / missing key| FALLBACK[Rule-based Copilot]
```

**Architecture and guarantees:**

- **Backend is the source of truth.** The Copilot receives pre-computed, run-scoped context — never raw database access, SQL, or shell.
- **Role-aware context.** `scope_ai_context` (in `backend/app/services/ai/context.py`) filters context server-side by role tier: `cfo` (full), `manager` (operational), `analyst` (investigation), `reviewer` (decision evidence only), `user` (numeric overview only). Unknown roles map to the least-privileged bucket. Frontend hiding is not the security boundary — this scoping is.
- **Data minimization.** Credentials, password hashes, tokens, and personnel details never enter AI context. For external providers, `_safe_context` keeps only aggregated metrics plus a capped set of control records.
- **Untrusted data.** Merchant names, descriptions, and notes are treated as untrusted content; the provider system prompt instructs the model never to follow instructions found in transaction data, and prompt-injection attempts are handled as data.
- **Providers** — `AIProvider` abstraction with:
  - `MockAIProvider` (default, deterministic rule-based Copilot),
  - `OpenAIProvider` (`gpt-4o-mini` by default),
  - `GeminiProvider` (`gemini-2.0-flash` by default).
- **Fallback** — any provider failure (missing key, HTTP error, timeout, malformed or credential-shaped output) automatically falls back to the rule-based Copilot. `validate_llm_response` rejects empty, oversized, or fabricated credential content before it reaches the user.
- **Conversation** — optional `history` field (backward compatible) enables follow-up questions; history is sanitized server-side (only user/assistant role+content pairs, last 8 turns, truncated).
- **Auditability** — every Copilot query is logged to the audit trail (user, role, tier, question prefix, run) without secrets.
- **API keys** — backend-only, read from environment, never logged, never returned by APIs, never bundled in the frontend.

## Razorpay integration (test mode)

`backend/app/services/razorpay/adapter.py` is a **read-only, test-mode-only** integration:

- `GET /api/razorpay/test-payments` — retrieves up to 100 payments from the Razorpay test API (`v1/payments`) using `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`.
- `POST /api/razorpay/test-payments/import` — normalizes those payments into the standard CSV import contract (id → transaction_id, amount/refund/fee converted from paise to rupees, order_id → settlement_id, etc.) and pushes them through the same `POST /api/import` pipeline.
- The adapter returns **503** when credentials are not configured or `RAZORPAY_MODE` is not `test`. Live-mode payments are not supported.

It does **not** provide real bank reconciliation — it is a convenience for pulling Razorpay *test* payment records into the control pipeline.

## Security

- **Authentication** — JWT (HS256, 8-hour expiry) via `python-jose`; passwords hashed with **Argon2id** via `passlib`.
- **RBAC** — server-side authorization on every protected route. Roles: `Admin`, `CFO / Manager`, `Finance Controller`, `Finance Manager`, `Finance Analyst`, `Reviewer`. Review mutations require Controller/CFO/Admin; the CFO report requires a CFO/manager tier; Copilot context is tier-scoped. Unauthenticated requests to any `/api` route (except login and health) are rejected with 401.
- **Production bootstrap protection** — the demo admin is created from configuration (`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`). In `APP_ENV=production` an unset bootstrap password **disables** admin auto-creation/reset entirely; the clearly-labeled development-only fallback password in `bootstrap.py` is never applied in production. The frontend production bundle contains no demo password.
- **CSV security** — 10 MB / 100 k-row limits, required-column checks, per-row number/date validation, duplicate `transaction_id` rejection, NUL-byte rejection, and spreadsheet formula-injection detection on text cells.
- **AI isolation** — see [AI Copilot](#ai-copilot): server-side context scoping, data minimization, untrusted-data handling, output validation, provider fallback, no credentials to models.
- **API safety** — CORS origins from configuration, no stack traces or secrets in errors, audit logging of control actions.
- **Secrets** — `.env` files are git-ignored (`*.env`, `*.env.*`, with `.env.example` kept); only `.env.example` templates are committed. Secret scans are part of the validation workflow.

## Performance

Performance work is verified by tests, not claims:

- **Optimized paths** — reconciliation uses indexed amount-bucket candidate matching and batched DB lookups (no O(n²) full-group rescans, no N+1 loops in the main paths); run-scoped aggregates are computed in SQL where possible.
- **CI performance gate** — `backend/tests/test_performance_gate.py` runs deterministic datasets of **100 / 200 / 300 / 500 / 1,000 / 5,000 / 10,000 / 50,000 / 100,000** rows through `validate_csv`, `parse_single_file`, `analyze_transactions`, and risk scoring. Bounds are deliberately loose (10–15× headroom) to catch major regressions without failing on CI variance — this is a regression gate, not production load testing.
- **Measured on the development machine** (from the gate's calibration): 100,000 rows validate in ~1.0 s, reconcile in ~3.6 s, anomaly-detect in ~0.7 s, risk-score in ~0.07 s, with roughly linear scaling.

## Testing

**Backend — 239 tests passing** (24 test files, `pytest`):

| Area | Files |
|---|---|
| Reconciliation (single / multi / adaptive / API / dataset) | `test_single_file_reconciliation.py`, `test_multi_file_reconciliation.py`, `test_adaptive_reconciliation.py`, `test_reconciliation_api.py`, `test_reconciliation_dataset.py` |
| CSV validation & security matrix (edge cases, size matrix, pipeline, multi-file) | `test_csv_security.py`, `test_csv_matrix_edge_cases.py`, `test_csv_matrix_datasets.py`, `test_csv_matrix_pipeline.py`, `test_csv_matrix_multi_file.py` |
| Current-run propagation / historical runs | `test_current_run_propagation.py` (13 tests) |
| Risk & review workflow | `test_risk_workflow.py`, `test_finance.py` |
| Anomaly engine | `test_anomaly_engine.py` |
| Forecasting & scenarios | `test_forecast_scenario.py` |
| CFO report | `test_cfo_report.py` |
| AI security / Copilot readiness / LLM layer (fallback, injection, history) | `test_ai_security.py`, `test_copilot_readiness.py`, `test_llm_copilot_layer.py`, `test_optional_integrations.py` |
| Import persistence, admin bootstrap, API smoke | `test_import_persistence.py`, `test_admin_bootstrap.py`, `test_api.py` |
| Performance gate | `test_performance_gate.py` |

Supporting tooling lives in `backend/tests/qa/`: a deterministic dataset generator (`datasets.py`, fixed seed) and an **independent validation oracle** (`oracle.py`) that computes expected reconciliation/risk results from the published spec — not from the application's own engines — so the matrix tests compare independent expectations against application output.

**Frontend — 16 tests passing** (`vitest` + Testing Library): login state, dashboard rendering, current-run display, transaction table, risk/anomaly rendering, CFO "Unavailable" states, and Copilot suggested/custom/follow-up questions. The Vite production build (`vite build`) passes.

Run everything:

```bash
# backend (from backend/, after activating the virtualenv)
DATABASE_URL=sqlite:///./qa.db python -m pytest -q

# performance gate only
DATABASE_URL=sqlite:///./qa_perf.db python -m pytest tests/test_performance_gate.py -q

# frontend (from frontend/)
npm test
npm run build
```

## API reference

All routes are prefixed with `/api` and require a `Bearer` JWT unless noted. OpenAPI docs are available at `/docs` when the backend is running.

| Method | Endpoint | Purpose | Auth / role |
|---|---|---|---|
| `POST` | `/auth/login` | Login, returns JWT + user role | public |
| `GET` | `/health` | Health check (`status`, `ai_provider`) | public |
| `GET` | `/dashboard` | Current-run KPIs, reconciliation summary, risk distribution, top exceptions | any authenticated |
| `GET` | `/analytics` | Dashboard metrics + insight | any authenticated |
| `GET` | `/transactions` | Paginated, run-scoped transactions (optional `run_id`, `page`, `page_size`) | any authenticated |
| `GET` | `/reconciliation` | Current/historical run records with counts, variance, review state (optional `run_id`) | any authenticated |
| `POST` | `/reconciliation/single-file` | Reconcile one CSV against its bank/ledger/settlement amount columns | any authenticated |
| `POST` | `/reconciliation/multi-file` | Reconcile bank + ledger (+ optional settlement) CSVs | any authenticated |
| `GET` | `/risk` | Run-scoped risk assessments (optional `run_id`) | any authenticated |
| `GET` | `/anomalies` | Run-scoped anomalies (optional `run_id`) | any authenticated |
| `GET` | `/review` | Review queue for current/historical run (optional `run_id`) | any authenticated |
| `PATCH` | `/review/{item_id}` | Update review status + note | Controller / CFO / Admin |
| `POST` | `/review/{item_id}/action` | Investigate / approve / reject / escalate / resolve / reopen | Controller / CFO / Admin |
| `POST` | `/import` | Validate & import a finance CSV; creates an import run | any authenticated |
| `GET` | `/forecast` | Deterministic 30-day baseline forecast (current run) | any authenticated |
| `POST` | `/scenarios` | Run a what-if scenario projection | any authenticated |
| `GET` | `/reports/cfo` | Unified CFO executive report | CFO / manager tier |
| `GET` | `/alerts` | Deterministic control alerts | any authenticated |
| `POST` | `/copilot` | Ask the AI Copilot (optional `history` for follow-ups) | any authenticated, role-scoped |
| `GET` | `/audit` | Latest audit log entries | any authenticated |
| `GET` | `/razorpay/test-payments` | Fetch Razorpay test payments | any authenticated, test mode only |
| `POST` | `/razorpay/test-payments/import` | Import Razorpay test payments through the standard pipeline | any authenticated, test mode only |

## Repository structure

```text
Finance-Controller-AI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, static frontend serving
│   │   ├── db.py                    # SQLAlchemy engine/session (SQLite or PostgreSQL)
│   │   ├── api/
│   │   │   ├── routes/auth.py       # POST /api/auth/login
│   │   │   ├── routes/core.py       # all finance/control endpoints (~2,700 lines)
│   │   │   └── dependencies/auth.py # current_user / require_roles guards
│   │   ├── core/
│   │   │   ├── config.py            # pydantic-settings environment config
│   │   │   ├── security.py          # JWT + Argon2id
│   │   │   └── bootstrap.py         # demo admin bootstrap (production-safe)
│   │   ├── models/models.py         # User, Transaction, ReconciliationRun,
│   │   │                            # ReconciliationResult, RiskAssessment,
│   │   │                            # Anomaly, ReviewItem, AuditLog
│   │   └── services/
│   │       ├── finance/engine.py    # current-run resolver + metrics()
│   │       ├── reconciliation/      # adaptive.py (production), multi_file.py
│   │       ├── risk/engine.py       # legacy calculate() + assess_exception()
│   │       ├── anomaly/engine.py    # independent statistical engine
│   │       ├── csv/processor.py     # validate_csv
│   │       ├── ai/                  # context.py (RBAC scoping), providers.py
│   │       └── razorpay/adapter.py  # test-mode payments adapter
│   ├── migrations/                  # Alembic migrations (0001–0007)
│   ├── tests/                       # 24 test files + tests/qa (generator + oracle)
│   ├── seed.py                      # seeds admin + 1,000-row sample dataset
│   ├── requirements.txt
│   ├── Dockerfile                   # multi-stage: frontend build + backend runtime
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # SPA: routing, all views, API client (~8.3 k lines)
│   │   ├── App.test.tsx             # 16 workflow tests
│   │   └── test/setup.ts
│   ├── package.json                 # vite, react, recharts, vitest, testing-library
│   └── vite.config.ts               # vitest config (jsdom)
├── database/sample_data/            # finance_transactions.csv, bank/ledger/settlement_1000.csv
├── scripts/                         # start_backend.sh / start_backend.ps1
├── docs/                            # brief pointers to this README
├── docker-compose.yml               # local backend + frontend compose
├── railway.json                     # Railway build config (Dockerfile + healthcheck)
└── .env.example                     # environment template
```

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 22+ and npm
- PostgreSQL (optional — SQLite is the default for development)

### Backend

```bash
cd backend
python -m venv .venv                # Windows: .venv\Scripts\activate
source .venv/bin/activate           # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                # adjust DATABASE_URL etc. as needed

python seed.py                      # creates tables + demo admin + sample data
uvicorn app.main:app --reload       # http://localhost:8000  (docs at /docs)
```

`scripts/start_backend.sh` (and `.ps1`) automate this: venv → install → seed → uvicorn.

### Frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

The SPA reads `VITE_API_URL` (default: same origin `/api`). In development with Vite on port 5173 and FastAPI on 8000, set `VITE_API_URL=http://localhost:8000` (or use `docker-compose` below).

### Local demo login

The backend creates the demo admin from configuration. In a fresh local database with `APP_ENV=development` and no `BOOTSTRAP_ADMIN_PASSWORD` set, the documented **development-only** fallback password from `backend/app/core/bootstrap.py` applies — treat it as a local-dev convenience, never a production credential. Set `BOOTSTRAP_ADMIN_PASSWORD` (and `APP_ENV=production`) for anything real.

### Docker (local)

```bash
docker-compose up --build
# backend → http://localhost:8000, frontend dev server → http://localhost:5173
```

## Environment variables

Templates: `.env.example` (root, backend) and `frontend/.env.example`. All values below are placeholders — never commit real secrets.

| Variable | Purpose | Required | Example |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy DB URL | dev default: SQLite | `postgresql+psycopg://user:pass@localhost:5432/finance_controller` |
| `SECRET_KEY` | General app secret | production | `change-me-in-development` |
| `JWT_SECRET` | JWT signing secret | production | `change-me-jwt` |
| `AI_PROVIDER` | `mock` \| `openai` \| `gemini` | yes (default `mock`) | `mock` |
| `OPENAI_API_KEY` | OpenAI key (backend-only) | for OpenAI | *(secret)* |
| `OPENAI_MODEL` | OpenAI model | no | `gpt-4o-mini` |
| `GEMINI_API_KEY` | Google Gemini key (backend-only) | for Gemini | *(secret)* |
| `GEMINI_MODEL` | Gemini model | no | `gemini-2.0-flash` |
| `RAZORPAY_MODE` | `test` (only test mode is supported) | no | `test` |
| `RAZORPAY_KEY_ID` | Razorpay test key id | for Razorpay | *(secret)* |
| `RAZORPAY_KEY_SECRET` | Razorpay test key secret | for Razorpay | *(secret)* |
| `CORS_ORIGINS` | Comma-separated allowed origins | dev default | `http://localhost:5173` |
| `APP_ENV` | `development` \| `production` | production | `production` |
| `BOOTSTRAP_ADMIN_EMAIL` | Demo admin email | no | `admin@demo.com` |
| `BOOTSTRAP_ADMIN_PASSWORD` | Demo admin password | **required in production** | *(secret)* |
| `VITE_API_URL` (frontend) | API base for the SPA | no | `http://localhost:8000` |
| `VITE_DEMO_EMAIL` / `VITE_DEMO_PASSWORD` (frontend) | Login-screen prefill only; embedded in the bundle, **not secrets** | no | `admin@demo.com` |

**Development vs production:** the defaults (`SQLite`, `mock` AI, dev CORS) are for local work. Production should set a PostgreSQL `DATABASE_URL`, real `JWT_SECRET`/`SECRET_KEY`, `APP_ENV=production`, `BOOTSTRAP_ADMIN_PASSWORD`, and the desired AI/Razorpay credentials.

## Deployment

The app deploys as a **single Docker image** (Railway service `Finance-Controller-AI`).

- `backend/Dockerfile` is multi-stage: it builds the React frontend (`vite build`) and then runs the FastAPI app with Uvicorn, serving the built frontend from `/app/static`.
- `railway.json` configures the Dockerfile build with healthcheck `GET /api/health` (100 s timeout, restart on failure).
- `docker-compose.yml` provides a local two-container setup (backend + Vite dev server).
- Database: SQLite by default; PostgreSQL via `DATABASE_URL` (psycopg2 included). Alembic migrations under `backend/migrations/` handle schema evolution.

### Railway

1. Push the repository to GitHub and create a Railway project from the repo (Dockerfile build is auto-detected via `railway.json`).
2. Set the [environment variables](#environment-variables) — at minimum `APP_ENV=production`, `BOOTSTRAP_ADMIN_PASSWORD`, `JWT_SECRET`, `SECRET_KEY`, and a PostgreSQL `DATABASE_URL`.
3. Deploy; verify `GET /api/health` returns `{"status":"ok","ai_provider":"mock"}` (or the configured provider) and that protected endpoints return 401 without a token.

## Demo flow

A 3–5 minute walkthrough:

1. **Login** — authenticate; the dashboard loads the current run's KPIs (total, matched, exceptions, variance, match rate, risk distribution).
2. **Upload** — run a single-file reconciliation on `database/sample_data/finance_transactions.csv` (or any valid CSV). The response shows per-record statuses, variance, and the new `run_id`.
3. **Reconcile** — open the Reconciliation page: matched/partial/mismatch/unmatched/duplicate counts, match rate, total variance.
4. **Inspect exceptions** — open the Review Queue: every exception with amount, variance, reason, and risk level.
5. **Risk & anomalies** — the Risk Assessment page shows run-scoped severity (LOW/MEDIUM/HIGH/CRITICAL); Anomaly Detection shows independent statistical signals.
6. **Decide** — take a review action (investigate / approve / reject / escalate); every action is audit-logged.
7. **Audit** — the Audit Logs page shows imports, runs, review actions, and Copilot queries.
8. **Forecast** — see the deterministic 30-day baseline (or an honest "unavailable" state when the schema lacks the data).
9. **Scenario** — run a what-if (e.g. expenses +10%) and see the projected impact.
10. **CFO Command Center** — KPIs, trends, expense breakdown, attention items, outlook — all from the current run.
11. **Copilot** — ask "Summarize the current reconciliation run", "What changed in the latest upload?", or any custom question; the answer is grounded in the run context and role-scoped.

## Current limitations

- **Razorpay is test-mode only** — it retrieves test payments and pushes them into the standard pipeline; it does not provide live-mode or real bank reconciliation.
- **External LLM requires valid credentials and quota** — without a working `OPENAI_API_KEY` / `GEMINI_API_KEY` (or on any provider failure), the Copilot falls back to the deterministic rule-based answer. The deployed application currently runs `AI_PROVIDER=mock` by design.
- **Financial projections depend on the run's schema** — forecast and scenario outputs are only produced when the current run's CSV carries the relevant financial dimensions; otherwise they are reported as unavailable rather than fabricated.
- **Some secondary nav pages are data views** — e.g. the generic Forecasting/Settings pages render structured JSON from the analytics API, while the dedicated CFO Command Center and Scenario Simulator provide the full visual experience.
- **Authenticated live verification** of the deployed instance requires the operator-configured `BOOTSTRAP_ADMIN_PASSWORD`; unauthenticated production behavior (401 on protected routes, health, deployed bundle) is verified, and authenticated behavior is covered by the 239-test suite.
- **Performance gate ≠ production load testing** — the CI gate proves the pipeline stays linear to 100,000 rows on synthetic data; it is not a formal load-testing result.

## Relevance to the Finance Controller challenge

The project targets the finance-controller problem end to end:

- **Financial control** — a run-based pipeline where the latest upload drives every downstream view, and historical runs stay auditable.
- **Reconciliation** — both single-file and multi-file modes with transparent variance and exception generation.
- **Risk & anomalies** — independent, explainable engines with deterministic scoring.
- **Human-in-the-loop** — AI detects and prioritizes; authorized humans decide; every decision is audited.
- **AI-assisted investigation** — a grounded Copilot that explains backend numbers without ever calculating them itself or modifying records.
- **Decision support** — forecasting and scenario simulation that report honest availability instead of fabricated values.

---

*Built by Vaishnavi Santosh Landage — hackathon and educational project. See the repository's commit history for the full development trail.*