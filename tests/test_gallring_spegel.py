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


FORALDRALOSA = ROT / "db" / "migrations" / "20261119140000_134_spegelns_foraldralosa.sql"


def _kaskadbarn_till_synkade(synkade: set[str]) -> set[tuple[str, str]]:
    """(barn, förälder) för varje tabell utanför SYNK vars främmande nyckel
    kaskaderar från en tabell i SYNK, ur hela migrationskedjan."""
    text = "\n".join(
        p.read_text(encoding="utf-8")
        for katalog in (ROT / "db" / "migrations", ROT / "railway")
        for p in sorted(katalog.glob("*.sql"))
    )
    par: set[tuple[str, str]] = set()
    for tabell in re.finditer(
        r"create table (?:if not exists )?(?:public\.)?(\w+)\s*\((.*?)\n\);", text, re.S | re.I
    ):
        for ref in re.finditer(r"references (?:public\.)?(\w+)[^,\n]*on delete cascade", tabell.group(2), re.I):
            par.add((tabell.group(1), ref.group(1)))
    for ref in re.finditer(
        r"alter table (?:if exists )?(?:only )?(?:public\.)?(\w+)[^;]*?references (?:public\.)?(\w+)[^;]*?on delete cascade",
        text, re.I | re.S,
    ):
        par.add((ref.group(1), ref.group(2)))
    return {(barn, foralder) for barn, foralder in par if foralder in synkade and barn not in synkade}


def test_varje_kaskadbarn_till_en_synkad_tabell_stadas_i_spegeln():
    """Migration 134 (Codex runda 4): synken raderar i replica-läge, där
    kaskaderna inte körs. Ett barn utanför SYNK till en förälder i SYNK blir
    då föräldralöst i spegeln och måste raderas av gallra_spegelns_foraldralosa."""
    synkade = set(_synk())
    barn = _kaskadbarn_till_synkade(synkade)
    assert ("ss_channel_contacts", "ss_customers") in barn, "skanningen hittar inte det kända fallet"
    sql = FORALDRALOSA.read_text(encoding="utf-8")
    for tabell, foralder in sorted(barn):
        assert re.search(
            rf"delete from public\.{tabell} \w+\s+where not exists \(select 1 from public\.{foralder} ", sql
        ), f"{tabell} kaskaderar från {foralder} (synkad) men städas inte i spegeln"
