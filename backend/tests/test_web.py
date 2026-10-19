"""The combined judge image must keep static files separate from API access."""

from __future__ import annotations

import os
import subprocess
import sys


def test_hosted_frontend_preserves_api_routes_and_access_checks(tmp_path):
    static = tmp_path / "frontend"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>Mimi judge</title>")
    (static / "app.js").write_text("console.log('judge frontend')")
    # Isolate the web module's static mount and import-time DB from API tests.
    env = {
        **os.environ,
        "MIMI_STATIC_DIR": str(static),
        "MIMI_DB_PATH": str(tmp_path / "web-test.db"),
        "MIMI_JUDGE_KEY": "test-judge-key",
        "PYTHON_DOTENV_DISABLED": "1",
    }
    for key in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID", "TAVILY_API_KEY"):
        env.pop(key, None)
    result = subprocess.run(
        [sys.executable, "-c", """
from fastapi.testclient import TestClient
from mimi.web import app
with TestClient(app) as client:
    root = client.get('/')
    assert root.status_code == 200 and '<title>Mimi judge</title>' in root.text
    assert client.get('/app.js').status_code == 200
    assert client.get('/missing.js').status_code == 404
    assert client.get('/api/health').json() == {'ok': True, 'service': 'mimi'}
    assert client.get('/api/reports/mock0000demo').status_code == 200
    assert client.get('/api/reports/private-report').status_code == 401
    denied = client.post('/api/reports', json={
        'package_spec': 'lodash@4.17.20', 'report_text': 'A public test report'
    })
    assert denied.status_code == 402
"""],
        env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
