# AI Finance Controller

Enterprise-style financial intelligence application using React/TypeScript/Vite, FastAPI/Python, SQLAlchemy and PostgreSQL in production. It runs in **Mock AI mode without an API key** and uses local demo transactions only when explicitly seeded.

## Features
Dashboard, transaction search/pagination, reconciliation metrics, anomaly/risk views, review queue with backend authorization, analytics, forecasting baseline, scenario simulator API, CFO report API, alerts, audit logs, CSV import validation, RBAC foundation, Argon2id password hashing, JWT expiry, CORS, safe API errors, and grounded Mock AI Copilot.

## Architecture
CSV -> schema detection -> canonical normalization -> deterministic matching -> PostgreSQL -> UI/AI structured context. Financial source data is treated as untrusted data and never becomes instructions.

## Adaptive reconciliation
Single-file and multi-file reconciliation accept arbitrary `.csv` filenames. Headers are normalized and matched against semantic aliases for identifiers, amounts, fees, refunds, adjustments, dates, parties, currencies, and descriptions; unknown columns are retained in result evidence.

Single-file uploads reconcile the strongest available evidence. When an explicit transaction amount and an explicit settled amount are both present, the engine compares them directly (`variance = amount - settlement_amount`); fees, refunds, and adjustments are reported as context/evidence and are never automatically deducted to form an expected settlement amount. When no explicit settled amount exists, available explicit amounts (bank/ledger/settlement) are still compared directly. Multi-file uploads infer BANK, LEDGER, and SETTLEMENT roles from schema signals, report confidence and assumptions, and match by exact identifiers first, then unique amount/date/party evidence. Settlement files carry explicit amounts that are compared directly against bank/ledger amounts; a settlement file's fee column is evidence only and never auto-deducted. Fuzzy evidence never produces a MATCHED result.

Statuses are `MATCHED`, `PARTIAL`, `MISMATCH`, `UNMATCHED`, and `DUPLICATE`. Monetary variance is computed as `amount - settlement_amount` when both are explicit and is displayed by absolute value for prioritization. The default tolerance is ₹0.01. Every non-matched result is sent to the review queue, and reconciliation audit details include mappings, roles, assumptions, row counts, match rate, variance, and tolerance.

## Prerequisites
Python 3.12+, Node.js 20+, npm.

## Quick start (Windows PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
uvicorn app.main:app --reload
```
In another terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. API docs: http://localhost:8000/docs.

## macOS/Linux
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn app.main:app --reload
```
Then `cd frontend && npm install && npm run dev`.

## Demo login
Email: `admin@demo.com`
Password: `DemoPassword123!`
Development/demo only; change it before any real deployment.

## AI configuration
Default: `AI_PROVIDER=mock`. No key is required. Later, add the provider key in **backend/.env** as `AI_API_KEY=...` and set `AI_PROVIDER=external`. The provider abstraction is in `backend/app/services/ai/providers.py`; the external adapter is intentionally conservative until a specific provider SDK is selected.

## Database / migrations
The application creates missing tables on startup for local compatibility. Production uses the Railway PostgreSQL `DATABASE_URL`; startup does not seed or reset data. Run `python seed.py` separately only for a development/demo database.

## Tests
Backend: `cd backend; pytest`
Frontend: `cd frontend; npm install; npm test`

## Security
Never commit `.env`, API keys, production passwords, database credentials or tokens. Uploaded files are extension/MIME-size/UTF-8/schema/number/date validated and are never executed. Backend authorization protects review approval actions. Audit logs avoid secrets.

## API
Interactive OpenAPI: `/docs`. Main endpoints include `/api/health`, `/api/auth/login`, `/api/dashboard`, `/api/transactions`, `/api/import`, `/api/reconciliation`, `/api/anomalies`, `/api/risk`, `/api/review`, `/api/analytics`, `/api/forecast`, `/api/scenarios`, `/api/reports/cfo`, `/api/alerts`, `/api/copilot`, `/api/audit`.

## Troubleshooting
If login fails, verify the backend is running from `backend` and that its `.env` points to the intended database. If port 8000/5173 is busy, start the corresponding server on another port and update `CORS_ORIGINS`. Do not delete or reset the database; take a backup and diagnose the schema or migration state first.

## Limitations
This is a complete runnable local MVP rather than a production regulated-finance deployment. External AI provider integration is an extension point, not a provider-specific implementation. Full accounting statements, ROA/ROE, liquidity ratios and receivable/payable metrics are only available when the source contains the required accounting fields; the UI/API must not invent them. The current frontend uses compact reusable page rendering for many modules while the backend provides the core working data flows.
