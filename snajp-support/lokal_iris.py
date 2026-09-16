"""Lokal backend för Iris-ytan (leads-webb) i MINNESLÄGE på port 8010.

Blankar DATABASE_URL/REDIS_URL innan settings byggs, samma grepp som
scripts/run_live_tests.py: .env:ens DATABASE_URL pekar på en fjärrdatabas,
och en lokal utvecklingsserver får aldrig peka dit (CLAUDE.md). Utan URL
väljer appen MemoryStorage och in-memory-kön — tomt, syntetiskt, ofarligt.

Körs via .claude/launch.json ("iris-backend") eller för hand:
    .venv/Scripts/python.exe lokal_iris.py
"""

import os

os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8010)
