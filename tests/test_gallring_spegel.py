"""Gallringen i development-spegeln (migration 133) och synken hör ihop.

I en spegel nollar gallra_tenant urvalet för de tabeller synken för över
(main:s raderingar når spegeln genom synk_raderingar) och gallrar resten
själv. Listan står i SQL och synkens tabeller i scripts/railway_synk.py:SYNK.
Glider de isär blir antingen en tabell aldrig gallrad i spegeln (den lades
till i SYNK men nollas inte, eller togs ur SYNK men nollas fortfarande) eller
gallrad två gånger. Det här testet läser båda och kräver att de stämmer.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
MIGRATION = ROT / "db" / "migrations" / "20261119130000_133_gallring_i_spegeln.sql"


def _synk() -> dict[str, str]:
    sys.path.insert(0, str(ROT / "scripts"))
    spec = importlib.util.spec_from_file_location("railway_synk", ROT / "scripts" / "railway_synk.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul.SYNK


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_spegelns_nollade_urval_ar_exakt_synkens_tabeller():
    sql = _sql()
    # Kategori → variabel, ur sammanställningen gallringen loggar.
    kategori = dict(
        re.findall(r"'(\w+)',\s+jsonb_build_object\('atgard', '\w+', 'antal', cardinality\((v_\w+)\)\)", sql)
    )
    assert len(kategori) >= 18, kategori
    nollade = set(re.findall(r"(v_\w+) := v_tomt_\w+;", sql))
    nollade_tabeller = {t for t, v in kategori.items() if v in nollade}
    synkade = set(_synk())
    assert nollade_tabeller == {t for t in kategori if t in synkade}, (
        "Spegelns gallring och SYNK har glidit isär: "
        f"nollas men synkas inte {sorted(nollade_tabeller - synkade)}, "
        f"synkas men nollas inte {sorted({t for t in kategori if t in synkade} - nollade_tabeller)}"
    )


def test_spegeln_gallrar_de_osynkade_tabellerna():
    sql = _sql()
    synkade = set(_synk())
    for tabell in ("agent_feedback", "generated_emails", "contacts", "leads_sidcache", "platform_events"):
        assert tabell not in synkade, f"{tabell} synkas nu; spegelns gallring ska då lämna den åt synken"
        assert tabell in sql


def test_gallra_alla_avbryter_inte_langre_i_en_spegel():
    alla = _sql().split("create or replace function public.gallra_alla(", 1)[1]
    assert "'status', 'spegel'" not in alla
    assert "return jsonb_build_object('status', 'kord'" in alla
