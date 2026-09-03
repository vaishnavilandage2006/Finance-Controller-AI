#!/usr/bin/env bash
cd "$(dirname "$0")/../backend"; python3 -m venv .venv; source .venv/bin/activate; pip install -r requirements.txt; python seed.py; uvicorn app.main:app --reload