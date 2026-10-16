# Mimi backend

FastAPI service, CLI, and evidence pipeline for Mimi. For the full setup,
configuration, read-only fixture demo, and security notes, see the
[repository README](../README.md).

This package supports Python 3.12 and 3.13. The bundled sample report is
already-public CVE-2021-44906 and is included as package data for `mimi demo`.

`MIMI_DB_PATH` selects the SQLite file. `MIMI_JUDGE_KEY` enables protected
submissions and reads of non-demo reports. Without it, the API serves only the
bundled, read-only demo. The key is shared across users, so do not use this
configuration to process private reports on a shared deployment.
`MIMI_CORS_ORIGINS` is a comma-separated list of browser origins allowed to
call the API; its default allows the local Vite development server only.
