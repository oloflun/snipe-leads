"""INV-DATA-005 — gallringen: bara beslutad policy, aldrig spärrlistan eller
bokföringen, högst en gång per dygn, i en spegel bara det synken inte för
över (migration 133; förut aldrig i en spegel), av som standard.

Den statiska halvan. Beteendet prövas mot en riktig Postgres med hela
migrationskedjan i tests/db/test_gallring.py (CI-jobbet "databastester").
Det här testet fäller en ändring som tar bort ett skydd ur källan även där
databastestet inte körs.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIGRATIONER = ROOT / "db" / "migrations"
APP = ROOT / "snajp-support" / "app"


def _utan_kommentarer(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql).lower()


def _gallringsmigrationer() -> list[Path]:
    return [p for p in sorted(MIGRATIONER.glob("*.sql"))
            if "gallra_tenant" in p.read_text(encoding="utf-8")
            or "gallra_alla" in p.read_text(encoding="utf-8")]


def test_gallringen_finns_i_en_migration():
    assert _gallringsmigrationer(), "gallra_tenant/gallra_alla saknas i migrationerna"


def test_sparrlistan_och_bokforingen_raderas_aldrig():
    for fil in _gallringsmigrationer():
        sql = _utan_kommentarer(fil.read_text(encoding="utf-8"))
        for tabell in ("suppressions", "bk_underlag", "bk_verifikat", "bk_verifikat_rad",
                       "kvitto_mejl_lasta"):
            assert not re.search(rf"delete\s+from\s+(public\.)?{tabell}\b", sql), (
                f"{fil.name} raderar ur {tabell}")
        # contacts → suppressions kaskaderar: kopplingen nollas före raderingen.
        nolla = sql.find("update public.suppressions set contact_id = null")
        radera = sql.find("delete from public.contacts")
        assert 0 <= nolla < radera, f"{fil.name}: spärrkopplingen nollas inte före kontakterna"


def test_ingen_policy_ingen_gallring_och_ingen_policy_i_migrationerna():
    for fil in _gallringsmigrationer():
        sql = _utan_kommentarer(fil.read_text(encoding="utf-8"))
        assert "'ingen_policy'" in sql
        assert not re.search(r"insert\s+into\s+(public\.)?ss_gallringspolicy", sql), (
            f"{fil.name} skriver en policy — beslutet är ägarens")


def test_dygnsparr_och_spegel_i_databasen():
    for fil in _gallringsmigrationer():
        sql = _utan_kommentarer(fil.read_text(encoding="utf-8"))
        if "function public.gallra_alla" not in sql:
            continue
        assert "to_regclass('public.mirror_meta')" in sql
        assert "insert into public.ss_gallringskorning" in sql and "on conflict (dag) do nothing" in sql


def test_spegeln_lamnar_det_synkade_at_synken():
    """Migration 133: den senaste gallra_tenant känner igen spegeln och nollar där
    urvalet för de synkade tabellerna. Vilka de är håller tests/test_gallring_spegel.py
    ihop med scripts/railway_synk.py:SYNK."""
    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    assert "v_spegel     boolean := to_regclass('public.mirror_meta') is not null" in sql
    assert sql.count("if v_spegel then") == 2
    for variabel in ("v_mejl", "v_arenden", "v_kunder", "v_prospekt", "v_korningar"):
        assert f"{variabel} := v_tomt_" in sql


def test_jobbet_ar_av_som_standard():
    config = (APP / "config.py").read_text(encoding="utf-8")
    assert re.search(r"^\s*gallring_aktiv:\s*bool\s*=\s*False\s*$", config, re.MULTILINE)
    jobb = (APP / "jobs" / "gallring.py").read_text(encoding="utf-8")
    main = (APP / "main.py").read_text(encoding="utf-8")
    assert "if settings.gallring_aktiv:" in main
    # Appens egen kod raderar aldrig i gallringen; det gör databasfunktionen.
    assert not re.search(r"delete\s+from", jobb, re.IGNORECASE)
