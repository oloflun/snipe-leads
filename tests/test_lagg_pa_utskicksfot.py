"""scripts/lagg_pa_utskicksfot.py — sidfoten i efterhand måste klara send_guard.

Skriptet bygger foten ur kundregistrets rader i stället för ur get_tenant, så
kopplingen till spärrarna mäts här: ett utkast som regel 1 stoppade ska efter
skriptet passera alla sex. Körs med backendens venv (send_guard importeras):

    snajp-support/.venv/Scripts/python -m pytest tests/test_lagg_pa_utskicksfot.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "snajp-support"))

import lagg_pa_utskicksfot as skript  # noqa: E402
from app.leads.send_guard import SKICKA, Avsandare, TenantHistorik, Utskick, check_send_guard  # noqa: E402

KUND = {
    "namn": "Exempelbolaget AB",
    "orgnr": "556000-0000",
    "adress": "Exempelgatan 1, 903 26 Umeå",
    "policy_url": "https://exempel.example/integritetspolicy",
}
LANK = skript.fot.avregistreringslank("https://snajp.example", "a" * 32)
BRODTEXT = "Hej,\n\nEtt kort och relevant erbjudande.\n\nVänliga hälsningar\nSara"


def _dom(brodtext: str, *, personlig: bool):
    return check_send_guard(
        avsandare=Avsandare(foretagsnamn=KUND["namn"], orgnr=KUND["orgnr"], postadress=KUND["adress"]),
        utskick=Utskick(
            mottagare="anna.svensson@exempel.se" if personlig else "info@exempel.se",
            amne="En fråga",
            brodtext=brodtext,
            foretagsnyckel="exempel.se",
            personlig_adress=personlig,
        ),
        historik=TenantHistorik(
            skickade_totalt=50,
            skickade_idag=0,
            tenant_alder_dagar=400,
            senaste_kontakt_med_foretaget=None,
            suppressions=frozenset(),
            tidigare_kontaktade=frozenset(),
            egna_kunder=frozenset(),
        ),
        nu=datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),  # tisdag 10:00 svensk tid
    )


def test_utan_fot_stoppar_regel_1():
    assert _dom(BRODTEXT, personlig=False).regel == "1_avsandaridentifikation"


@pytest.mark.parametrize("personlig", [True, False])
def test_med_skriptets_fot_slapps_utkastet_igenom(personlig):
    ny = skript.med_fot(BRODTEXT, kund=KUND, lank=LANK)
    assert ny.startswith(BRODTEXT)
    beslut = _dom(ny, personlig=personlig)
    assert beslut.atgard == SKICKA, beslut.skal


def test_ingen_andra_fot():
    en_gang = skript.med_fot(BRODTEXT, kund=KUND, lank=LANK)
    assert skript.med_fot(en_gang, kund=KUND, lank=LANK) is None


SIG = {"namn": "Sara Ek", "titel": "VD", "telefon": "070-000 00 00", "bolag": "Exempelbolaget AB"}


def test_signaturen_laggs_fore_foten_och_utkastet_slapps_igenom():
    """Sebbe 2026-10-09: alla utkast ska bära signaturen. Den läggs före
    foten, och mejlet klarar fortfarande alla sex spärrar."""
    ny = skript.med_fot(skript.med_signatur(BRODTEXT, sig=SIG, sprak="sv"), kund=KUND, lank=LANK)
    assert ny.index("Sara Ek\nVD") < ny.index("\n--\n")
    assert _dom(ny, personlig=False).atgard == SKICKA


def test_signaturen_laggs_in_fore_en_befintlig_fot_och_bara_en_gang():
    med_fot = skript.med_fot(BRODTEXT, kund=KUND, lank=LANK)
    ny = skript.med_signatur(med_fot, sig=SIG, sprak="sv")
    assert ny.index("Sara Ek\nVD") < ny.index("\n--\n")
    assert skript.med_signatur(ny, sig=SIG, sprak="sv") == ny
    assert _dom(ny, personlig=False).atgard == SKICKA


def test_utan_signaturinstallning_rors_texten_inte():
    assert skript.med_signatur(BRODTEXT, sig=None, sprak="sv") == BRODTEXT


def test_saknade_uppgifter_namnges():
    assert skript.saknade_uppgifter({**KUND, "orgnr": "", "adress": None}) == ["organisationsnummer", "företagsadress"]
    assert skript.saknade_uppgifter(KUND) == []
