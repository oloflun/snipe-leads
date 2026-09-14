"""Fas 3.4/3.5: --prospekt-flaggan i scripts/konvertera_testkund.py.

`avgor_atgard()` är bruten ut till en ren funktion specifikt för att vara
testbar utan en riktig Postgres-anslutning — se skriptets egen docstring vid
`avgor_atgard` och `PROSPEKT_KOLUMNER`. Testerna här mäter DEN funktionen och
`_parsa_id_lista()`, inte hela skriptet: `main()` kräver DATABASE_URL,
`RAILWAY_*`-miljövariabler och en riktig tenant, vilket den här sviten
medvetet inte har (samma hermetik-princip som snajp-support/tests/conftest.py).

Ligger i repo-rotens svit, inte backendens, av samma skäl som
test_leads_ui_endpoints.py: skriptet bor i scripts/, inte i snajp-support/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import konvertera_testkund as kt  # noqa: E402

GILTIGT_ORGNR = "5568249022"  # samma nummer som snajp-support/tests/leads/test_orgnr.py


def test_krock_vinner_over_allt_annat():
    """Fälla 1 (planen §4): en foretagsnyckel-krock hoppas över ÄVEN om raden
    annars hade klarat valideringen — kopiering hade annars kringgått
    90-dagarskarensen i send-guardens regel 5."""
    rad = {
        "origin": "test",
        "orgnr": GILTIGT_ORGNR,
        "website": "https://exempel-ab.se",
        "contact_email": "info@exempel-ab.se",
    }
    atgard, detalj = kt.avgor_atgard(rad, finns_i_malet=True)
    assert atgard == "krock"
    assert detalj == []


def test_example_utan_giltiga_falt_ger_valideringsfel_med_bristlista():
    """Fälla 2: exempelbolag.py bygger org.nr Luhn-ogiltigt med flit och
    webbplatsen under .example — en sådan rad ska INTE gå att kopiera."""
    rad = {"origin": "example", "orgnr": None, "website": None, "contact_email": None}
    atgard, detalj = kt.avgor_atgard(rad, finns_i_malet=False)
    assert atgard == "valideringsfel"
    assert len(detalj) == 3


def test_example_med_giltiga_falt_far_kopieras():
    rad = {
        "origin": "example",
        "orgnr": GILTIGT_ORGNR,
        "website": "https://exempel-ab.se",
        "contact_email": "info@exempel-ab.se",
    }
    atgard, detalj = kt.avgor_atgard(rad, finns_i_malet=False)
    assert atgard == "kopiera"
    assert detalj == []


def test_test_origin_kraver_ingen_validering():
    """Skiljer sig medvetet från 'example': en testkörnings prospekt bär
    RIKTIGA researchresultat (skriptets docstring, Fas 3.5) och ska därför
    INTE tvingas genom samma kontroll som ett påhittat exempelbolag."""
    rad = {"origin": "test", "orgnr": None, "website": None, "contact_email": None}
    atgard, detalj = kt.avgor_atgard(rad, finns_i_malet=False)
    assert atgard == "kopiera"
    assert detalj == []


@pytest.mark.parametrize("origin", ["manual", "import"])
def test_redan_riktiga_ursprung_kraver_ingen_validering(origin):
    atgard, _ = kt.avgor_atgard({"origin": origin}, finns_i_malet=False)
    assert atgard == "kopiera"


def test_parsa_id_lista_stadar_mellanslag_och_tomma_bitar():
    assert kt._parsa_id_lista(
        " 3fae21e0-0000-0000-0000-000000000001 ,, 9b110c44-0000-0000-0000-000000000002"
    ) == [
        "3fae21e0-0000-0000-0000-000000000001",
        "9b110c44-0000-0000-0000-000000000002",
    ]


def test_parsa_id_lista_tom_strang_ger_tom_lista():
    assert kt._parsa_id_lista("") == []


def test_parsa_id_lista_kraschar_hardvilligt_pa_ogiltigt_uuid():
    with pytest.raises(SystemExit):
        kt._parsa_id_lista("inte-ett-uuid")


def test_prospekt_kolumner_utesluter_de_genererade_och_styrda_falten():
    """id/tenant_id/origin/foretagsnyckel/created_at ska INTE stå i listan:
    origin sätts explicit till 'manual' i INSERT-satsen (kopiera_prospekt),
    foretagsnyckel är GENERATED STORED och kan inte skrivas (migration 031),
    och en kopia är en NY rad som får sin egen created_at."""
    for falt in ("id", "tenant_id", "origin", "foretagsnyckel", "created_at"):
        assert falt not in kt.PROSPEKT_KOLUMNER


def test_hamta_prospekt_med_tom_lista_gor_ingen_fraga():
    """Ingen cur.execute alls när ider är tom — annars kraschar
    `= any(%s::uuid[])` på en tom array-parameter i onödan."""

    class _KraschandeCursor:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("hamta_prospekt körde en fråga trots tom id-lista")

    assert kt.hamta_prospekt(_KraschandeCursor(), "nagon-tenant", []) == {}
