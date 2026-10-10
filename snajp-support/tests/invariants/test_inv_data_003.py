"""INV-DATA-003 — Development och main skrivs bara av synken
(scripts/railway_synk.py, aldrig provkörningar) och admin_flytt.importera.
Ändrad 2026-10-10 (Anton, docs/BESLUT.md): tvåvägssynk i stället för
envägsspegeln.

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


def test_synken_synkar_aldrig_provkorningar():
    """Varje synkad tabell har ett testvillkor, och de som bär is_test eller
    hänger under ett prospekt/en tråd/ett ärende filtrerar på det."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("railway_synk", ROOT / "scripts" / "railway_synk.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    for tabell in ("ss_tickets", "ss_emails", "lead_lists", "leads_job_ledger", "agent_runs"):
        assert "is_test" in modul.SYNK[tabell], tabell
    assert "'test'" in modul.SYNK["prospects"]
    for tabell in ("outreach_threads", "outreach_messages", "send_queue", "prospect_sources"):
        assert "'test'" in modul.SYNK[tabell], tabell


def test_varje_utskick_skickas_fran_en_miljo():
    """Godkända utkast skickas av miljön där de godkändes (skickas_har), både
    i sändaren för godkända och i den autonoma schemaläggaren. Development i
    tvåvägsläge följer aldrig upp och läser aldrig inkorgar."""
    s = (BACKEND / "app" / "leads" / "scheduler.py").read_text(encoding="utf-8")
    assert s.count("skickas_har(item, spegel)") >= 2
    assert "if tvavags(spegel):" in s  # uppföljningssvepet
    assert "tvavags(" in (BACKEND / "app" / "email_pipeline" / "poller.py").read_text(encoding="utf-8")
