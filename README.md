
# AI Finance Controller

## AI-Powered Financial Control, Risk Detection & CFO Decision Intelligence

Detect → Reconcile → Investigate → Forecast → Simulate → Decide → Audit

# Live Demo

https://finance-controller-ai-production.up.railway.app/

# Demo Login

Email: admin@demo.com
Password: 7cJeyeytqLyo4uv2TUFYuuiKxJUW

https://finance-controller-ai-production.up.railway.app/

# API Documentation

Run the backend locally and open:

http://localhost:8000/docs

# Table of Contents

# Table of Contents

1. [Problem Statement](#problem-statement)
2. [Solution](#solution)
3. [Key Features](#key-features)
4. [Security](#security)
5. [Performance](#performance)
6. [Testing](#testing)
7. [Tech Stack](#tech-stack)
8. [Core Control Loop](#core-control-loop)
9. [Demo Flow](#demo-flow)
10. [Local Setup](#local-setup)
11. [Architecture](#architecture)
12. [Design Philosophy](#design-philosophy)
13. [Why It Matters](#why-it-matters)
14. [Future Improvements](#future-improvements)
15. [Author](#author)


# Problem Statement

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

This creates several challenges:

• Financial data is scattered across different systems
• Reconciliation can require significant manual effort
• Important exceptions can be difficult to prioritize
• Controllers need to switch between multiple tools
• Decisions may not have a clear audit trail
• Management insights may come only after manual investigation

The problem is not the lack of financial data.

The problem is connecting that data into one reliable financial-control workflow.

Our main principle is simple:

The finance engine remains the source of truth.

Financial calculations and control decisions are handled using deterministic and explainable logic.

AI is not given uncontrolled authority over financial data.


# Solution

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

"What happened, what looks wrong, what needs attention, and what should be investigated next?"

The system connects operational finance control with management-level decision support.


# Key Features

## 1. Dynamic Data Ingestion

• CSV upload and validation
• Invalid-row detection
• Duplicate handling
• Persistent storage
• Dynamic downstream data propagation

The system converts transaction exports into structured financial data that can be used across the complete workflow.


## 2. Smart Reconciliation

• Matched / Partial / Unmatched transactions
• Amount and identifier matching
• Variance detection
• Reconciliation exceptions
• Transaction-level investigation

The reconciliation engine identifies where financial records agree and where differences require attention.


## 3. Risk & Anomaly Detection

• Statistical anomaly detection
• Risk prioritization
• Amount outliers
• Repeated transaction patterns
• Merchant concentration
• Risk distribution

The system helps finance teams focus on transactions and exceptions that require investigation.


## 4. Human Review

• Investigation queue
• Transaction investigation
• Authorized review actions
• Approve / Reject / Escalate
• Human-in-the-loop decisions

The system identifies and prioritizes issues, while authorized humans remain responsible for the final financial decision.


## 5. CFO Command Center

• Revenue and expense KPIs
• Risk and reconciliation health
• Financial trends
• Expense analysis
• CFO attention items
• Executive insights

The CFO Command Center provides a high-level view of the financial situation and highlights areas requiring management attention.


## 6. AI Finance Copilot

Grounded AI assistance for financial investigation and decision support.

The Copilot explains available system data and does not directly modify financial records or execute financial actions.

It helps users understand financial information and investigate important exceptions.


## 7. Decision Intelligence

• Financial analytics
• Baseline forecasting
• Scenario simulation
• Financial alerts
• Audit logs

These capabilities help finance teams move from historical reporting toward proactive planning and decision support.


# Security

Security is built into the financial-control workflow.

• JWT authentication
• JWT expiry
• Argon2id password hashing
• Role-Based Access Control
• Backend authorization
• CORS protection
• Environment-based secrets
• Safe API error handling
• AI data minimization

Financial actions remain controlled by authorized users.

The platform is designed to support financial investigation without giving AI uncontrolled access to financial operations.


# Performance

The reconciliation pipeline was optimized using:

• Indexed candidate matching
• Batched database operations
• Reduced N+1 queries
• SQL aggregates
• Reduced per-row database flushes

The system was stress-tested with fixture-derived workloads of up to 200,000 transaction input rows.

This demonstrates that the architecture is designed to handle significantly larger workloads than a basic demonstration dataset.


# Testing

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

Testing helps ensure that financial data flows correctly through the complete control workflow.


# Tech Stack

Frontend:
React, TypeScript, Vite

Backend:
Python, FastAPI, SQLAlchemy

Database:
PostgreSQL

AI:
Grounded Finance Copilot

Security:
JWT, Argon2id, RBAC

Deployment:
Docker, Railway


# Core Control Loop

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

The platform connects operational financial control with management-level planning.


# Demo Flow

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

This demonstrates the complete journey from raw financial data to controlled financial decision-making.


# Local Setup

Requirements:

• Python 3.12+
• Node.js 22+
• PostgreSQL
• Git


## Clone the Repository

git clone https://github.com/vaishnavilandage2006/Finance-Controller-AI.git

cd Finance-Controller-AI


## Backend

cd backend

python -m venv .venv


## Windows

.venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload


## Frontend

Open another terminal:

cd frontend

npm install

npm run dev


Configure environment variables using:

.env.example

Never commit real secrets to GitHub.


# Architecture

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


# Design Philosophy

## Action Over Information

Don't just show financial data.

Help controllers decide what to do next.


## Exceptions Over Noise

Prioritize important financial issues instead of forcing users to manually inspect everything.


## Human-in-the-Loop

AI assists the finance team while authorized humans remain responsible for important decisions.


## Grounded Intelligence

AI insights are based on available system data rather than unsupported assumptions.


## Auditability

Important financial-control actions remain traceable.


# Why It Matters

AI Finance Controller connects:

DATA → CONTROL → RISK → REVIEW → DECISION → AUDIT → PLANNING

The goal is to move finance teams from:

Passive Reporting → Proactive Financial Control

Instead of simply answering:

"What happened?"

The platform helps finance teams answer:

"What happened?"

"Why is it important?"

"What should we investigate?"

"Who needs to review it?"

"What decision was made?"

"Can we trace that decision later?"


# Future Improvements

• Asynchronous large-file processing
• Background reconciliation jobs
• Chunked CSV uploads
• Advanced forecasting
• Explainable risk scoring
• Configurable control policies
• Multi-tenant support
• Advanced approval workflows
• Real-time financial event ingestion
• More advanced CFO decision support


# Author

Vaishnavi Santosh Landage

T.Y. CSE

GitHub:
https://github.com/vaishnavilandage2006/Finance-Controller-AI

Live Demo:
https://finance-controller-ai-production.up.railway.app/


# AI FINANCE CONTROLLER

Detect → Reconcile → Investigate → Forecast → Simulate → Decide → Audit

One connected workflow for modern financial control.
