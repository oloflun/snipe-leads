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
        if "function public.gallra_tenant" not in sql:
            continue  # t.ex. 134, som bara byter gallra_alla
        # contacts → suppressions kaskaderar: kopplingen nollas före raderingen.
        nolla = sql.find("update public.suppressions set contact_id = null")
        radera = sql.find("delete from public.contacts")
        assert 0 <= nolla < radera, f"{fil.name}: spärrkopplingen nollas inte före kontakterna"


def test_ingen_policy_ingen_gallring_och_ingen_policy_i_migrationerna():
    for fil in _gallringsmigrationer():
        sql = _utan_kommentarer(fil.read_text(encoding="utf-8"))
        if "function public.gallra_tenant" in sql:
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
    """Migration 133 och 139: den senaste gallra_tenant känner igen spegeln och
    väljer där i de synkade tabellerna bara lokala provrader (synkens villkor).
    Villkoren håller tests/test_gallring_spegel.py lika med
    scripts/railway_synk.py:SYNK."""
    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    assert "v_spegel     boolean := to_regclass('public.mirror_meta') is not null" in sql
    assert "and (not v_spegel or (e.is_test))" in sql
    assert "and (not v_spegel or (t.is_test))" in sql
    assert "and (not v_spegel or (false))" in sql  # kunderna synkas alla
    assert not re.search(r"v_\w+ := v_tomt_\w+;", sql), "en synkad kategori nollas helt i spegeln"


#: Varje tabell gallringen läser aktivitet ur eller väljer som kandidat och som
#: kan uppdateras (migration 142). Loggtabeller som bara får nya rader står utanför.
_BEHANDLADE = (
    "ss_emails", "ss_drafts", "ss_tickets", "ss_conversations", "ss_customers", "ss_chat_state",
    "ss_channel_contacts", "customer_memory", "prospects", "outreach_threads", "outreach_messages",
    "send_queue", "ss_demolankar", "lead_samtal", "lead_anteckningar", "lead_uppgifter",
    "prospect_sources", "lead_list_items", "lead_lists", "leads_job_ledger",
    "ss_avregistreringslankar", "generated_emails", "contacts", "meetings", "saljlista",
)


def test_varje_andring_raknas_som_behandling():
    """Migration 141 och 142 (Codex runda 9 och 10): en ändring som inte rör
    någon av urvalets tider (ett redigerat utkast, en återöppnad uppgift) fick
    ett levande prospekt gallrat. Triggern gallring_behandlad sätter
    behandlad_at vid varje faktisk ändring i varje tabell urvalet läser, och
    den senaste gallra_tenant räknar den överallt."""
    fil = MIGRATIONER / "20261119220000_142_varje_andring_ar_behandling.sql"
    sql_142 = _utan_kommentarer(fil.read_text(encoding="utf-8"))
    for tabell in _BEHANDLADE:
        assert f"'{tabell}'" in sql_142, f"{tabell} saknar triggern gallring_behandlad"
    assert "when (to_jsonb(old) is distinct from to_jsonb(new))" in sql_142

    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    for alias in ("e", "d", "t", "c", "s", "k", "m", "p", "q", "a", "u", "l", "g"):
        assert f"{alias}.behandlad_at" in sql, f"{senaste.name}: {alias}.behandlad_at saknas i urvalet"
    # Varje greatest() i urvalen bär behandlad_at, utom de som bara läser
    # loggtabeller (identifierare, demolänkarnas händelser, statusloggen).
    for rad in re.findall(r"greatest\([^;]*?\)\s*<\s*v_grans", sql, re.DOTALL):
        assert "behandlad_at" in rad, f"{senaste.name}: ett urval räknar inte behandlad_at:\n{rad}"
    assert "and (prospect_id is null or prospect_id = any(v_prospekt))" in sql


def test_jobbet_ar_av_som_standard():
    config = (APP / "config.py").read_text(encoding="utf-8")
    assert re.search(r"^\s*gallring_aktiv:\s*bool\s*=\s*False\s*$", config, re.MULTILINE)
    jobb = (APP / "jobs" / "gallring.py").read_text(encoding="utf-8")
    main = (APP / "main.py").read_text(encoding="utf-8")
    assert "if settings.gallring_aktiv:" in main
    # Appens egen kod raderar aldrig i gallringen; det gör databasfunktionen.
    assert not re.search(r"delete\s+from", jobb, re.IGNORECASE)
