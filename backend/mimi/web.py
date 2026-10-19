"""Serve the live frontend and API from one judge-service origin.

The image builds the frontend with an empty API base and hash routing. API
routes remain registered before the static mount, including their access checks.
"""

from __future__ import annotations

import os

from fastapi.staticfiles import StaticFiles

from .api import app


app.mount(
    "/",
    StaticFiles(directory=os.environ.get("MIMI_STATIC_DIR", "/app/frontend"), html=True),
    name="frontend",
)
