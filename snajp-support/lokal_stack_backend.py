"""Backenden mot den LOKALA stacken (scripts/lokal_stack.py), aldrig mot .env:s databas.

`snajp-support/.env` pekar på den gamla Supabase-databasen, som aldrig får skrivas
till (CLAUDE.md). Pydantic-inställningarna låter miljön gå före .env, så det här
skriptet sätter databasen och nycklarna till den lokala stackens värden innan
appen laddas. Lösenordet läses ur lokal_stack.py och skrivs aldrig ut.

    .venv/Scripts/python.exe lokal_stack_backend.py   (cwd: snajp-support)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from lokal_stack import LOSEN_APP  # noqa: E402

os.environ["DATABASE_URL"] = f"postgresql://snajp_app:{LOSEN_APP}@127.0.0.1:5432/railway"
os.environ.setdefault("SNAJP_MASTER_API_KEY", "snajp_master_local_test_key")
os.environ.setdefault("SNAJP_INTERNAL_API_KEY", "snajp_demo_2f8c1a9e4b7d")
os.environ.setdefault("REDIS_URL", "")

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
