# Changelog

All work in this repository was created during the hackathon Submission Period (Aug 26 - Oct 30, 2026). The repository was empty before the first commit on 2026-09-29; no pre-existing code was imported.

## Unreleased

### 2026-09-30 (key check)
- Verified Token Factory inference and Tavily with the owner's keys. Recorded exact Nemotron model IDs and how to turn reasoning off.
- Found that the Sandboxes token has no permissions; recorded as a blocker in `docs/00-constraints-and-open-items.md`. (An initial reading of a short key expiry was wrong: `token_expiration` is a rolling five-minute value. Corrected in the docs.)
- Added the no-attribution-in-commits rule to `CLAUDE.md`.
- Added hands-on entries to `docs/feedback-log.md`.

### 2026-09-30
- Project named Mimi; team confirmed solo; Apache-2.0 chosen.
- Added `LICENSE` (standard Apache-2.0 text), `.gitignore` (keeps `.env` and keys out), README stub, this changelog and `docs/feedback-log.md`.
- Constraints file rebuilt from the official Rules; architecture updated for judge access until Dec 15, hosting, and solo scope.

### 2026-09-29
- Added research, decision and architecture drafts under `docs/`.
