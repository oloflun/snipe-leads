"""INV-DATA-003 — Enda skrivvägen från development till main är
admin_flytt.importera; spegelskriptet pekar aldrig mot main.

Antons beställning 2026-10-01: development är en envägsspegel som inte
skriver tillbaka, och den enda vägen till main är admin-funktionen i Byt kund.
Två saker prövas statiskt, för de syns inte i något körtidstest:

  a) scripts/railway_seed_dev.py: målet är hårdkodat 'development', ingen
     --target-flagga, och källan 'main' — en vändning av riktningen är en
     textändring det här testet fäller.
  b) Mottagaren /importera ligger INTE bakom masternyckeln (den kan inte,
     avsändaren är en annan miljö) utan bakom HMAC och spegelkontrollen, och
     ingen annan modul i app/ skriver 'importerad_fran'.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "snajp-support"


def test_spegelskriptet_pekar_bara_mot_development():
    s = (ROOT / "scripts" / "railway_seed_dev.py").read_text(encoding="utf-8")
    assert re.search(r'^TARGET_ENV = "development"', s, re.MULTILINE)
    assert re.search(r'^SOURCE_ENV = "main"', s, re.MULTILINE)
    assert 'add_argument("--target"' not in s
    assert "--behall-flyttko" in s


def test_importera_bakom_hmac_och_spegelkontroll_inte_masternyckel():
    s = (BACKEND / "app" / "api" / "admin_flytt.py").read_text(encoding="utf-8")
    # Mottagarroutern har ingen masternyckel-dependency.
    assert re.search(r'^mottag = APIRouter\(prefix="/api/admin/flytt"\)\s*$', s, re.MULTILINE)
    assert '@mottag.post("/importera")' in s
    assert "hmac.compare_digest" in s
    assert "spegel_info()" in s and "status_code=409" in s


def test_bara_admin_flytt_skriver_importerad_fran():
    # Lagringslagrens allowlists får känna till fältet; bara admin_flytt SKRIVER det.
    skrivare = []
    for p in (BACKEND / "app").rglob("*.py"):
        if p.parent.name == "storage":
            continue
        if "importerad_fran" in p.read_text(encoding="utf-8"):
            skrivare.append(p.name)
    assert skrivare == ["admin_flytt.py"], skrivare
