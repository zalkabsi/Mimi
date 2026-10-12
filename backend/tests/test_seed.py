from mimi.db import Database
from mimi.seed import DEMO_DIR, seed_demo


def test_seed_loads_recorded_dossiers_once(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    n = seed_demo(db)
    assert n == len(list(DEMO_DIR.glob("*.json"))) and n >= 1
    assert seed_demo(db) == 0  # idempotent
    rows = db.list_reports()
    assert all(r["source"] in ("demo", "eval") for r in rows)
    db.close()
