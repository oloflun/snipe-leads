"""Lokal backend för Kvittohanteraren i MINNESLÄGE på port 8000.

Samma grepp som lokal_iris.py: DATABASE_URL/REDIS_URL blankas innan settings
byggs — .env:ens DATABASE_URL pekar på en fjärrdatabas och en lokal
utvecklingsserver får aldrig peka dit (CLAUDE.md). Utan URL väljer appen
MemoryStorage — tomt, syntetiskt, ofarligt.

Kvittoläget: mock-inkorgen (påhittade mejl, kvitton/mejl.py) och den
deterministiska läsaren. LLM-nycklarna blankas så att även chatten kör
svarsmotorn utan modell — förutsägbart och gratis. Vill du köra chatten mot
riktig modell: kommentera ut GEMINI_API_KEY-raden och sätt MODEL till en
modell som finns (2026-09-16 svarade gemini-2.5-flash 404 lokalt —
leverantören hänvisar nya konton till gemini-3.6-flash).

Körs via .claude/launch.json ("kvitton-backend") eller för hand:
    .venv/Scripts/python.exe lokal_kvitton.py
"""

import os

os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["KVITTO_MEJL_LEVERANTOR"] = "mock"
os.environ["KVITTO_TOLKNING"] = "deterministisk"

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
