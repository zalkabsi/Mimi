PYTHON ?= python3

.PHONY: setup demo backend browser verify submission

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e './backend[dev]'
	cd frontend && npm ci

demo:
	cd frontend && npm run demo

backend:
	.venv/bin/python -m uvicorn mimi.api:app --host 127.0.0.1 --port 8000

browser:
	cd frontend && npx playwright install chromium

verify:
	.venv/bin/python -m pytest backend/tests -q
	cd frontend && npm run build && npm run test:e2e && npm audit

submission:
	cd frontend && npm run build:demo
	$(PYTHON) scripts/prepare_submission.py
