# AI Finance Controller

AI-Powered Financial Control, Risk Detection & CFO Decision Intelligence

Detect → Reconcile → Investigate → Forecast → Simulate → Decide → Audit

LIVE DEMO
https://finance-controller-ai-production.up.railway.app/

DEMO LOGIN
Email: admin@demo.com
Password: 7cJeyeytqLyo4uv2TUFYuuiKxJUW
https://finance-controller-ai-production.up.railway.app

API DOCUMENTATION
Run the backend locally and open:
http://localhost:8000/docs

#TABLE OF CONTENTS

1.  The Problem
2.  Our Solution
3.  Core Control Loop
4.  What the Platform Does
    4.1 Data Import
    4.2 Reconciliation
    4.3 Risk Detection
    4.4 Anomaly Detection
    4.5 Review Center
    4.6 Audit Trail
    4.7 CFO Command Center
    4.8 Analytics
    4.9 Forecasting
    4.10 Scenario Analysis
    4.11 Financial Summary

5.  AI Approach
6.  Security
7.  System Architecture
8.  Technology Stack
9.  Project Structure
10. API Endpoints
11. Run Locally
12. Testing
13. Performance Approach
14. Current Limitations
15. Roadmap
16. Why Finance Controller AI?
17. The Key Idea
18. Demo Flow
19. Live Demo
20. License
21. Team / Author


1. THE PROBLEM

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


3. CORE CONTROL LOOP

Detect → Investigate → Decide → Audit → Predict




4. WHAT THE PLATFORM DOES

4.1 DATA IMPORT

Upload financial transaction data using CSV files.

The system:

• Reads the uploaded files.
• Normalizes column names.
• Checks required fields.
• Validates transaction values.
• Validates dates and references.
• Detects duplicate transaction references.
• Stores the validated data.

The goal is to convert messy transaction exports into structured financial data that the rest of the system can safely use.


4.2 RECONCILIATION

The reconciliation engine compares financial records and identifies differences.

It can identify:

• MATCHED
• PARTIAL
• MISMATCH
• UNMATCHED
• DUPLICATE

For each result, the system can show the relevant variance and tolerance.

The system first uses strong evidence such as transaction identifiers.

When necessary, it can use additional evidence such as:

• Amount
• Date
• Party / merchant

The system does not treat uncertain matches as confirmed matches.


4.3 RISK DETECTION

Financial exceptions are scored using explainable rules.

The system helps prioritize transactions and cases that require attention.

Risk indicators can include:

• Large transaction amounts
• Reconciliation differences
• Duplicate or repeated transactions
• Unusual transaction patterns
• Concentration patterns
• Other configured financial control rules


4.4 ANOMALY DETECTION

The anomaly engine identifies unusual transaction behavior.

Examples include:

• Amount outliers
• Repeated transactions
• Duplicate records
• Merchant concentration
• Repeated refund patterns
• Unusual financial differences

Reconciliation exceptions and anomalies are treated as separate signals.

A transaction can have a settlement mismatch without being statistically unusual.

Similarly, a transaction can have an unusual amount even when the settlement amount matches.


4.5 REVIEW CENTER

Important cases can be moved into a human review workflow.

An authorized reviewer can:

• Open a case
• Investigate the available information
• Mark it under review
• Approve it
• Reject it
• Escalate it

The system records the action.

The final financial decision remains with the authorized human reviewer.


4.6 AUDIT TRAIL

Every important activity is recorded.

The audit trail helps answer:

• Who performed the action?
• What action was performed?
• When did it happen?
• What decision was made?

This provides traceability from the original financial record to the final review decision.


4.7 CFO COMMAND CENTER

The CFO Command Center brings important financial signals together.

It provides visibility into:

• Reconciliation health
• Risk distribution
• Transaction activity
• Spending trends
• Exceptions
• Forecasts
• Scenario analysis
• Key financial indicators


4.8 ANALYTICS

Analytics helps users understand historical financial activity.

Users can analyze:

• Transaction trends
• Spending patterns
• Risk distribution
• Reconciliation performance
• Financial exceptions
• Historical activity


4.9 FORECASTING

The system provides a baseline forecast using available historical data.

It is designed to give finance teams a simple view of expected future behavior.

Important:

The forecast is a baseline calculation, not a trained machine learning model.


4.10 SCENARIO ANALYSIS

Users can explore financial scenarios using deterministic calculations.

This helps answer questions such as:

"What could happen if transaction activity changes?"

"What happens if financial values increase or decrease?"

Scenario analysis is intended as a planning and decision-support feature.


4.11 FINANCIAL SUMMARY

Financial metrics are derived only from fields that actually exist in the uploaded data.

The system does not invent financial values.

If the uploaded dataset does not contain fields such as:

• Revenue
• Expenses
• Refunds
• Fees
• Profit

the system clearly indicates that these metrics are unavailable.




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


