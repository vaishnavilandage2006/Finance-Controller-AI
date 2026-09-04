# AI Finance Controller 

### AI-Powered Financial Control, Risk Detection & CFO Decision Intelligence

> **Detect → Reconcile → Investigate → Forecast → Simulate → Decide → Audit**

Finance Controller AI is an intelligent financial control platform that transforms raw transaction data into an actionable finance-control workflow.

Instead of stopping at dashboards and reports, the system continuously connects **transaction ingestion, validation, reconciliation, anomaly detection, risk prioritization, human review, forecasting, scenario simulation, CFO insights, and auditability**.

🔗 **Live Demo:** https://finance-controller-ai-production.up.railway.app/

---

## 🚀 What Makes Finance Controller AI Different?

Traditional financial dashboards mainly answer:

> **"What happened?"**

Finance Controller AI is designed to answer:

> **"What happened, what looks wrong, what needs attention, and what should the finance controller investigate next?"**

The platform creates a complete financial control loop:

```text
Financial Data
      ↓
Validation
      ↓
Persistence
      ↓
Reconciliation
      ↓
Risk & Anomaly Detection
      ↓
Human Review
      ↓
Decision
      ↓
Audit Trail
      ↓
CFO Insights
      ↓
Forecasting / Scenario Simulation
```

### Core principle

> **Don't just report the money. Control it.**

---

# 🎯 Problem Statement

Finance teams often operate across transaction files, spreadsheets, reconciliation systems, reports, and manual review processes.

This creates several problems:

* Large transaction datasets are difficult to investigate.
* Reconciliation can become slow and manual.
* Financial anomalies may remain hidden.
* High-risk transactions require manual identification.
* Unresolved exceptions are difficult to prioritize.
* CFO reporting takes time to prepare.
* Financial decisions may lack a clear audit trail.
* Newly uploaded data may not automatically propagate across downstream financial views.

The result is a fragmented workflow where finance teams spend significant time **finding problems instead of acting on them**.

---

# 💡 Purposed Solution

Finance Controller AI brings these activities into a single control platform.

```text
                    ┌──────────────────────┐
                    │   Financial Data     │
                    │ CSV / Transactions   │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │    Validation        │
                    │ Schema + Data Checks │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │     PostgreSQL       │
                    │    Persistence       │
                    └──────────┬───────────┘
                               ↓
              ┌────────────────────────────────┐
              │     Financial Control Engine   │
              ├───────────────┬────────────────┤
              │ Reconciliation│ Risk / Anomaly │
              └───────────────┴────────────────┘
                               ↓
                    ┌──────────────────────┐
                    │    Review Queue      │
                    │ Human Investigation  │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │    Controller        │
                    │      Decision        │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │     Audit Trail      │
                    └──────────┬───────────┘
                               ↓
       ┌───────────────────────┼───────────────────────┐
       ↓                       ↓                       ↓
 Forecasting            Scenario Simulator        CFO Insights
       └───────────────────────┼───────────────────────┘
                               ↓
                    ┌──────────────────────┐
                    │   AI Finance Copilot │
                    └──────────────────────┘
```

---
🏗️ System Architecture
<img width="1536" height="1024" alt="Final System Architecture" src="https://github.com/user-attachments/assets/171bac59-60d8-4d01-b17e-83008c41be39" />


# ✨ Key Features

## 1. 📥 Dynamic Financial Data Ingestion

Upload new transaction CSV files and automatically integrate them into the financial control pipeline.

### Includes

* CSV upload
* Data validation
* Invalid-row detection
* Persistent database storage
* Import audit logging
* Dynamic downstream updates
* Duplicate handling

Newly uploaded transactions propagate into:

**Transactions → Dashboard → Reconciliation → Risk → Analytics → CFO Report → Audit**

---

# 2. 🔎 Transaction Intelligence

A searchable transaction workspace for investigating financial activity.

### Capabilities

* Transaction search
* Pagination
* Transaction details
* Financial type classification
* Transaction status
* Amount and date information
* Risk-related information
* Persistent transaction history

This allows finance controllers to move from aggregate numbers directly to individual transactions.

---

# 3. 🔄 Smart Reconciliation

The reconciliation engine compares financial records and identifies discrepancies.

### Reconciliation states

🟢 **Matched**

🟡 **Partial**

🔴 **Unmatched**

### The engine considers financial matching information such as:

* Transaction identifiers
* Amounts
* Source records
* Transaction relationships
* Variance

The objective is to automatically identify which transactions agree and which require investigation.

---

# 4. 🚨 Risk & Anomaly Detection

The system identifies potentially problematic financial activity and prioritizes exceptions.

Risk signals are surfaced directly inside the finance-control workflow.

Instead of forcing the controller to inspect thousands of transactions manually:

```text
Transactions
      ↓
Risk Detection
      ↓
Prioritized Exceptions
      ↓
Human Review
```

This converts anomaly detection into an actionable workflow.

---

# 5. 👨‍💼 Human Review Queue

AI-assisted detection does not automatically make the final financial decision.

High-risk and unresolved items can be routed to a human review queue.

Controllers can:

* Investigate transactions
* Review reconciliation differences
* Inspect risk information
* Take authorized review actions
* Record decisions

This creates a **human-in-the-loop financial control system**.

---

# 6. 📊 CFO Command Center

The traditional report has been transformed into a **visual-first executive dashboard**.

The goal:

> **Understand the financial situation in 5–10 seconds.**

### Executive KPIs

* Revenue
* Expenses
* Net financial position
* Risk status
* Reconciliation health

### Visual analytics

* Revenue vs Expense trend
* Cash-flow trend
* Risk distribution
* Reconciliation health
* Expense breakdown

### CFO Attention

The system highlights the most important issues requiring attention.

Examples:

```text
🔴 High-risk financial exposure

🟠 Significant expense increase

🟡 Unresolved reconciliation items

🟢 Positive revenue movement
```

Each actionable item can lead directly to the relevant investigation screen.

---

# 7. 🤖 AI CFO Takeaway

Instead of generating long theoretical explanations, the CFO interface provides a compact executive interpretation.

Example structure:

```text
CFO TAKEAWAY

Revenue: ↑
Expenses: ↑
Risk: HIGH
Unresolved Items: 23

DECISION

Prioritize high-risk transactions and investigate
the increase in operating expenses.
```

The AI output is grounded in available system data.

The system avoids inventing unsupported financial facts.

---

# 8. 🧠 AI Finance Copilot

The Finance Copilot provides grounded assistance for financial investigation.

It is designed to help answer questions around the available financial data and system insights.

The Copilot follows an important principle:

> **Explain what the system knows — do not fabricate what it does not know.**

---

# 9. 📈 Financial Analytics

The analytics layer provides deeper visibility into financial activity.

It supports analysis of:

* Revenue
* Expenses
* Transaction activity
* Reconciliation
* Risk
* Financial trends
* Expense types

The analytics layer provides the evidence behind the executive-level CFO view.

---

# 10. 🔮 Forecasting

Finance Controller AI includes a baseline forecasting capability using historical transaction information.

The objective is to provide an initial view of potential future financial movement.

Forecasting is intentionally positioned as a baseline rather than an unsupported prediction engine.

---

# 11. 🎛️ Scenario Simulator

The scenario simulator allows finance teams to evaluate hypothetical financial situations.

Examples:

```text
What if expenses increase?

What if revenue decreases?

What if operating costs change?

What happens to the projected financial position?
```

This moves the system beyond historical reporting toward **decision support**.

---

# 12. 🔔 Alerts

Important financial-control conditions can generate alerts.

Examples include:

* High-risk activity
* Reconciliation exceptions
* Unresolved transactions
* Important financial changes

Alerts help controllers focus on exceptions instead of scanning the entire dataset.

---

# 13. 🧾 Audit Logs

Important system actions are recorded through an audit trail.

Examples include:

* CSV imports
* Review actions
* Important controller activity

This provides traceability for financial-control operations.

---

# 🔐 Security

Finance-related systems require more than authentication.

Finance Controller AI includes a security foundation containing:

### Authentication

* JWT authentication
* JWT expiry
* Secure password hashing

### Authorization

* RBAC foundation
* Backend authorization for protected review operations

### Password Security

Passwords are protected using:

**Argon2id**

### API Security

* CORS configuration
* Safe API error handling
* Environment-based secrets
* Protected backend operations

### Auditability

Important financial-control actions are recorded through audit logs.

---

# ⚡ Performance Engineering

Performance was treated as a core engineering requirement rather than an afterthought.

The reconciliation and financial-control paths were profiled and optimized.

## Major optimizations

### Before

The reconciliation fallback could perform repeated full-group scans:

```text
O(n²)
```

This becomes increasingly expensive as transaction volume grows.

### After

The matching path uses indexed amount-bucket candidates and more efficient lookups.

The resulting behavior is approximately:

```text
O(n)
```

for the relevant matching paths.

---

## Database Optimization

The system also reduces unnecessary database work through:

* Batched transaction prefetching
* Reduced N+1 queries
* Batched reconciliation lookups
* SQL aggregate calculations
* Reduced per-row flush operations
* Direct insertion for run-unique records

---

## Stress Testing

The pipeline was stress-tested using fixture-derived multi-file workloads up to:

### **200,000 transaction input rows**

The test verified:

* No processing errors
* No accidental duplicate logical reconciliation results
* Correct transaction persistence
* Correct reconciliation persistence
* Correct risk/anomaly behavior
* Correct audit behavior

> Note: the 200,000-row workload was generated from the project's real CSV fixtures through fixture-derived partitions/repetitions. It was not 200 physically distinct source files.

---

# 🧪 Testing

The project includes backend and frontend regression testing.

### Backend

The full backend test suite currently passes.

```text
66 passed
```

### Frontend

Frontend tests pass.

```text
1 passed
```

### Production build

The React/Vite production build passes successfully.

### Additional validation

* CSV persistence regression
* CFO report update regression
* New CSV propagation validation
* Query-count regression
* Diagnostics
* `git diff --check`

The CSV regression specifically verifies that newly uploaded data updates downstream CFO information.

---


# 🔁 End-to-End Control Flow

The complete user journey is:
Login
   ↓
Financial CSV Upload
   ↓
┌─────────────────────────────┐
│ Choose Upload Type          │
│                             │
│  Single CSV  │  Multiple CSV│
└──────┬──────┴───────┬──────┘
       ↓              ↓
 Single CSV       Multiple CSVs
       │              │
       └──────┬───────┘
              ↓
        Validate Data
              ↓
      Persist Transactions
              ↓
        Reconciliation
              ↓
      Risk & Anomaly Detection
              ↓
        Review Exceptions
              ↓
      Human Decision
       ├── Approve
       ├── Reject
       └── Escalate
              ↓
          Audit Logs
              ↓
     Analytics & Metrics
              ↓
         Forecasting
              ↓
    Scenario Simulation
              ↓
     CFO Command Center

This creates a continuous financial control loop instead of isolated features.

---

# 🖥️ Product Screens

Add your screenshots here after placing them inside `/screenshots`.

## CFO Command Center

![CFO Command Center](screenshots/cfo-command-center.png)

The CFO Command Center provides a visual executive overview of financial performance, risk, reconciliation health, and priority actions.

---

## Dashboard

![Dashboard](screenshots/dashboard.png)

Central overview of financial activity and system health.

---

## Reconciliation

![Reconciliation](screenshots/reconciliation.png)

Transaction matching and reconciliation exceptions.

---

## Risk & Anomaly Detection

![Risk Analysis](screenshots/risk-analysis.png)

Prioritized financial risk and anomaly information.

---

## Review Queue

![Review Queue](screenshots/review-queue.png)

Human-in-the-loop investigation and decision workflow.

---

## Analytics

![Analytics](screenshots/analytics.png)

Detailed financial trends and analytical insights.

---

# 🏗️ Technology Stack

## Frontend

* React
* TypeScript
* Vite
* CSS

## Backend

* Python
* FastAPI
* SQLAlchemy

## Database

* PostgreSQL

## Authentication & Security

* JWT
* Argon2id
* RBAC

## AI / Intelligence

* Grounded Finance Copilot
* Risk & anomaly detection
* Financial analytics
* Forecasting baseline
* Scenario simulation

## Deployment

* Docker
* Railway
* PostgreSQL

---

# 📁 Project Structure

```text
Finance-Controller-AI/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── reconciliation/
│   │   │   ├── risk/
│   │   │   ├── finance/
│   │   │   └── ai/
│   │   ├── core/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── ...
│
├── database/
│   └── ...
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── security.md
│   ├── ai-design.md
│   ├── performance.md
│   └── demo-flow.md
│
├── screenshots/
│   ├── dashboard.png
│   ├── cfo-command-center.png
│   ├── reconciliation.png
│   ├── risk-analysis.png
│   ├── review-queue.png
│   └── analytics.png
│
├── sample-data/
│   ├── transactions.csv
│   ├── bank_1000.csv
│   ├── ledger_1000.csv
│   └── settlement_1000.csv
│
├── .env.example
├── .gitignore
├── Dockerfile
├── railway.json
├── LICENSE
└── README.md
```

---

# ⚙️ Local Setup

## Prerequisites

Make sure you have:

* Python 3.12+
* Node.js 22+
* PostgreSQL
* Git

---

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Finance-Controller-AI
```

---

# 2. Backend Setup

```bash
cd backend
```

Create and activate a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 3. Configure Environment Variables

Create your environment configuration using:

```text
.env.example
```

Example:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_controller
JWT_SECRET=your-secret-key
CORS_ORIGINS=http://localhost:5173
AI_PROVIDER=mock
```

Never commit real secrets to GitHub.

---

# 4. Start Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The backend will run on:

```text
http://localhost:8000
```

---

# 5. Start Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will normally run on:

```text
http://localhost:5173
```

---

# 🌐 Production Deployment

The application is deployed as a single Railway service.

```text
                    Railway
                       │
        ┌──────────────┴──────────────┐
        │                             │
     Frontend                       Backend
      React                          FastAPI
        │                             │
        └──────────────┬──────────────┘
                       │
                   PostgreSQL
```

The Docker build:

1. Builds the React frontend.
2. Installs Python dependencies.
3. Copies the backend.
4. Serves the application through FastAPI/Uvicorn.
5. Connects to PostgreSQL.

### Live Application

🔗 **https://finance-controller-ai-production.up.railway.app/**

---

# 🔑 Demo Credentials

For the demonstration environment:

```text
Email:
admin@demo.com

Password:
DemoPassword123!
```

> These credentials are intended for the demo environment only. Do not reuse demo credentials in a production financial system.

---

# 🎬 Recommended Demo Flow

For the strongest demonstration, follow this sequence:

### 1. Login

Show authenticated access.

### 2. Dashboard

Briefly show the overall financial state.

### 3. Upload a New CSV

Demonstrate that the system accepts new financial data dynamically.

### 4. Reconciliation

Show matched, partial, and unmatched transactions.

### 5. Risk Detection

Open high-risk/anomalous transactions.

### 6. Review Queue

Demonstrate human investigation and authorization.

### 7. CFO Command Center

Show:

* KPIs
* Revenue vs Expense
* Cash Flow
* Risk
* Reconciliation
* Expense breakdown
* CFO Attention

### 8. Forecast

Show the financial baseline forecast.

### 9. Scenario Simulation

Demonstrate a hypothetical financial change.

### 10. AI Finance Copilot

Ask a grounded financial question.

### 11. Audit Log

Show that important actions are traceable.

---

# 🎯 Design Philosophy

Finance Controller AI is built around five principles:

### 1. Action over information

A dashboard should help the controller decide what to do next.

### 2. Exceptions over noise

Controllers should investigate important exceptions rather than manually inspect everything.

### 3. Human-in-the-loop

AI assists financial control; authorized humans remain responsible for decisions.

### 4. Grounded intelligence

AI insights should be based on available system data rather than fabricated financial facts.

### 5. Auditability

Important actions should remain traceable.

---

# 🧩 Financial Control Loop

The core concept behind the platform is:

```text
        ┌───────────────┐
        │ Financial Data│
        └───────┬───────┘
                ↓
        ┌───────────────┐
        │    Detect     │
        └───────┬───────┘
                ↓
        ┌───────────────┐
        │  Investigate  │
        └───────┬───────┘
                ↓
        ┌───────────────┐
        │    Decide     │
        └───────┬───────┘
                ↓
        ┌───────────────┐
        │     Audit     │
        └───────┬───────┘
                ↓
        ┌───────────────┐
        │ Learn / Plan  │
        └───────┬───────┘
                │
                └──────────────→ New Financial Decisions
```

This is the central idea behind Finance Controller AI.

---

# 🏆 Why This Matters

The project does not treat finance as a collection of independent screens.

Instead, it connects:

```text
DATA
 ↓
CONTROL
 ↓
RISK
 ↓
REVIEW
 ↓
DECISION
 ↓
AUDIT
 ↓
PLANNING
```

The result is an integrated finance-control workflow designed to help finance teams move from **passive reporting to proactive financial control**.

---

# 🔮 Future Improvements

Potential next-stage improvements include:

* Asynchronous large-file processing
* Background reconciliation jobs
* Chunked CSV uploads
* Streaming ingestion
* More advanced forecasting models
* Explainable risk scoring
* Configurable financial control policies
* Multi-tenant organization support
* Approval workflows
* Real-time financial event ingestion
* More advanced scenario modeling
* Production-grade AI model integration
* Role-specific CFO/controller dashboards

---

# 👥 Author:

Vaishnavi Santosh Landage.
T.Y.CSE



# 📜 License

This project is currently intended for hackathon and educational purposes.

See `LICENSE` for details.

---

# ⭐ Final Summary

Finance Controller AI transforms raw financial transactions into an intelligent financial-control loop:

```text
Upload
  ↓
Validate
  ↓
Reconcile
  ↓
Detect Risk
  ↓
Review
  ↓
Decide
  ↓
Audit
  ↓
Forecast
  ↓
Simulate
  ↓
Understand
```

### The goal is simple:

> **Detect financial problems early, focus human attention where it matters, and turn financial data into better decisions.**

**Finance Controller AI — Don't just report the money. Control it.**
