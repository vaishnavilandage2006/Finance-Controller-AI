# AI Finance Controller 

AI-Powered Financial Control, Risk Detection & CFO Decision Intelligence

Detect → Reconcile → Investigate → Forecast → Simulate → Decide → Audit

# Live Demo
https://finance-controller-ai-production.up.railway.app/

# Demo Login
Email: admin@demo.com
Password: 7cJeyeytqLyo4uv2TUFYuuiKxJUW
https://finance-controller-ai-production.up.railway.app

# API Documentation
Run the backend locally and open:
http://localhost:8000/docs

# Problem Statment

Finance teams already use many systems for transactions, accounting, reconciliation, risk, reporting, and auditing.

The problem is that these systems are often disconnected.

A typical process looks like this:

Transaction Export
        ↓
Manual Reconciliation
        ↓
Spreadsheet Investigation
        ↓
Risk Checking
        ↓
Manual Review
        ↓
Management Reporting
        ↓
Audit

Instead of using separate tools for each step, the controller can work through one connected system.

Our main principle is simple:

The finance engine remains the source of truth.

Financial calculations and control decisions are handled using deterministic and explainable logic.

AI is not given uncontrolled authority over financial data.

## Solution

AI Finance Controller connects the complete financial-control workflow in one platform.

Financial Data
↓
Validation
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
Analytics / Forecast
↓
CFO Insights

Instead of only showing what happened, the platform helps answer:

“What happened, what looks wrong, what needs attention, and what should be investigated next?”

## Key Features

1. Dynamic Data Ingestion
   • CSV upload and validation
   • Invalid-row detection
   • Duplicate handling
   • Persistent storage
   • Dynamic downstream data propagation

2. Smart Reconciliation
   • Matched / Partial / Unmatched transactions
   • Amount and identifier matching
   • Variance detection
   • Reconciliation exceptions

3. Risk & Anomaly Detection
   • Statistical anomaly detection
   • Risk prioritization
   • Amount outliers
   • Repeated transaction patterns
   • Merchant concentration
   • Risk distribution

4. Human Review
   • Investigation queue
   • Transaction investigation
   • Authorized review actions
   • Approve / Reject / Escalate
   • Human-in-the-loop decisions

5. CFO Command Center
   • Revenue and expense KPIs
   • Risk and reconciliation health
   • Financial trends
   • Expense analysis
   • CFO attention items
   • Executive insights

6. AI Finance Copilot

Grounded AI assistance for financial investigation and decision support.

The Copilot explains available system data and does not directly modify financial records or execute financial actions.

7. Decision Intelligence
   • Financial analytics
   • Baseline forecasting
   • Scenario simulation
   • Financial alerts
   • Audit logs

## Security

• JWT authentication
• JWT expiry
• Argon2id password hashing
• RBAC
• Backend authorization
• CORS protection
• Environment-based secrets
• Safe API error handling
• AI data minimization

## Performance

The reconciliation pipeline was optimized using indexed candidate matching, batched database operations, reduced N+1 queries, SQL aggregates, and reduced per-row database flushes.

The system was stress-tested with fixture-derived workloads up to 200,000 transaction input rows.

## Testing

Automated testing covers:

• Authentication
• CSV ingestion
• Reconciliation
• Risk & anomaly detection
• Current-run propagation
• CFO reporting
• AI Copilot
• RBAC
• Performance regression

## Tech Stack

Frontend: React, TypeScript, Vite
Backend: Python, FastAPI, SQLAlchemy
Database: PostgreSQL
AI: Grounded Finance Copilot
Security: JWT, Argon2id, RBAC
Deployment: Docker, Railway

## Core Control Loop

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

## Demo Flow

Login
↓
Upload CSV
↓
Reconciliation
↓
Risk Detection
↓
Review Queue
↓
CFO Dashboard
↓
Forecast / Scenario
↓
AI Copilot
↓
Audit Log

## Local Setup

Requirements:
• Python 3.12+
• Node.js 22+
• PostgreSQL
• Git

Clone the repository:

git clone [https://github.com/vaishnavilandage2006/Finance-Controller-AI.git](https://github.com/vaishnavilandage2006/Finance-Controller-AI.git)

cd Finance-Controller-AI

Backend:

cd backend
python -m venv .venv

Windows:

.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

Frontend:

cd frontend
npm install
npm run dev

Configure environment variables using .env.example.

Never commit real secrets to GitHub.

## Architecture

User
↓
JWT Authentication
↓
React + TypeScript
↓
FastAPI
↓
Financial Data
↓
Validation
↓
PostgreSQL
↓
Financial Control Engine
↓
Reconciliation + Risk/Anomaly
↓
Review Queue
↓
Human Decision
↓
Audit Trail
↓
Analytics / Forecast
↓
CFO Command Center
↓
AI Finance Copilot

## Design Philosophy

Action over Information
Help controllers decide what to do next.

Exceptions over Noise
Prioritize important financial issues.

Human-in-the-Loop
AI assists while authorized humans remain responsible for decisions.

Grounded Intelligence
AI insights are based on available system data.

Auditability
Important financial-control actions remain traceable.

## Why It Matters

AI Finance Controller connects:

DATA → CONTROL → RISK → REVIEW → DECISION → AUDIT → PLANNING

The goal is to move finance teams from passive reporting to proactive financial control.

## Future Improvements

• Asynchronous large-file processing
• Background reconciliation jobs
• Chunked CSV uploads
• Advanced forecasting
• Explainable risk scoring
• Configurable control policies
• Multi-tenant support
• Advanced approval workflows
• Real-time financial event ingestion

## Author

Vaishnavi Santosh Landage
T.Y. CSE

AI Finance Controller — Don't just report the money. Control it.
