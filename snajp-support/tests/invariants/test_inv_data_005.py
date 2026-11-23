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
    # Jämförelsen i funktionen (en WHEN på hela NEW fäller tabeller med
    # genererade kolumner), med de genererade kolumnerna undantagna.
    assert "if (to_jsonb(new) - v_utom) is distinct from (to_jsonb(old) - v_utom) then" in sql_142
    assert "is_generated = 'always'" in sql_142

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


def test_listraden_skyddar_sitt_prospekt():
    """Migration 143 (Codex runda 11): en omprocessad listrad ändrar inte
    prospektet när kontakten är oförändrad. Prospektets urval räknar därför
    listraderna som pekar på det, och låset tar dem även när de inte själva
    väljs."""
    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    assert re.search(r"select max\(greatest\(i\.created_at, i\.processad_at, i\.behandlad_at\)\)\s*"
                     r"from public\.lead_list_items i where i\.prospect_id = p\.id", sql), (
        f"{senaste.name}: prospektets urval räknar inte sina listrader")
    assert ("perform 1 from public.lead_list_items where id = any(v_listrader) "
            "or prospect_id = any(v_prospekt) for update;") in sql


def test_begransad_behandling_undantas():
    """Migration 144 (Codex runda 12): en aktiv begränsning av behandlingen
    (124, art. 18) betyder att uppgifterna bara får lagras. Den senaste
    gallra_tenant läser begränsningarna i varje varv, låser tabellen före andra
    varvet och undantar varje kategori som bär adressen."""
    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    assert "from public.behandlingsbegransningar where havd_at is null" in sql
    assert "perform pg_advisory_xact_lock_shared(hashtext('snajp.behandlingsbegransning'));" in sql
    sql_144 = _utan_kommentarer(
        (MIGRATIONER / "20261119235000_144_gallring_respekterar_begransning.sql").read_text(encoding="utf-8"))
    assert "perform pg_advisory_xact_lock(hashtext('snajp.behandlingsbegransning'));" in sql_144
    assert "before insert on public.behandlingsbegransningar" in sql_144
    for villkor in ("coalesce(lower(e.from_email), '') <> all(v_begr)",
                    "coalesce(lower(p.contact_email), '') <> all(v_begr)",
                    "coalesce(lower(contact_email), '') <> all(v_begr)",
                    "coalesce(lower(a.email), '') <> all(v_begr)",
                    "coalesce(lower(k.email), '') <> all(v_begr)",
                    "coalesce(lower(kontaktmail), '') <> all(v_begr)",
                    "where i.customer_id = t.customer_id and i.type = 'email'",
                    "where i.customer_id = c.id and i.type = 'email'",
                    "where i.customer_id = customer_memory.customer_id and i.type = 'email'"):
        assert villkor in sql, f"{senaste.name}: undantaget saknas: {villkor}"
    # Loggtabellerna utan adresskolumn prövas på löptexten.
    assert sql.count("gallring_namner_begransad(") >= 8
    # 145 (Codex runda 13): feedbacken följer sin körnings skydd.
    assert re.search(r"from public\.agent_feedback\s.*?where r\.id = agent_feedback\.run_id",
                     sql, re.DOTALL), f"{senaste.name}: feedbacken prövas inte mot sin körning"


def test_spegeln_vantar_pa_begransningarna():
    """Migration 147 (Codex runda 15): spegelns gallring prövar begränsningarna
    mot spegelns egen tabell. gdpr_radera.py skriver samma rad i båda
    miljöerna, synken för över alla rader och stämplar, och den senaste
    gallra_tenant kör inte skarpt i en spegel utan en stämpel från de senaste
    två timmarna."""
    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    sparr = sql.find("if v_spegel and not p_torrkorning then")
    assert sparr >= 0, f"{senaste.name}: spegeln prövar inte begränsningssynken"
    assert "(to_jsonb(m) ->> 'begransningar_synkade_at')::timestamptz" in sql[sparr:sparr + 400]
    assert sparr < sql.index("for v_varv in 1..2 loop"), "spärren prövas efter urvalet"

    skript = ROOT / "scripts"
    synk = (skript / "railway_synk.py").read_text(encoding="utf-8")
    assert synk.index("fel += skriv_begransningar(dc, begransningar)") < synk.index(
        "dc.execute(\"update public.mirror_meta set lage = 'envags', synkad_at = now()\")")
    gdpr = (skript / "gdpr_radera.py").read_text(encoding="utf-8")
    assert "return _spegla_till_development(rad, args.epost)" in gdpr
    assert "synkas inte till development-spegeln" not in gdpr


def test_taket_raknar_kaskaden():
    """Migration 146 (Codex runda 14): taket skyddar mot ett felaktigt
    policyvärde och måste räkna allt som försvinner, även barnen som ON DELETE
    CASCADE tar. Den senaste gallra_tenant räknar kaskaden före takprövningen i
    första varvet och igen efter låsen."""
    senaste = [f for f in _gallringsmigrationer()
               if "function public.gallra_tenant" in f.read_text(encoding="utf-8")][-1]
    sql = _utan_kommentarer(senaste.read_text(encoding="utf-8"))
    anrop = ("v_kaskad := public.gallring_kaskad(v_mejl, v_arenden, v_minne, v_kunder, "
             "v_prospekt, v_genererade);")
    assert sql.count(anrop) == 2, f"{senaste.name}: kaskaden räknas inte i båda varven"
    forsta = sql.index(anrop)
    assert forsta < sql.index("exit when p_torrkorning or (p_tak is not null and v_totalt > p_tak);"), (
        "kaskaden räknas efter takprövningen i första varvet")
    andra = sql.index(anrop, forsta + 1)
    assert andra < sql.index("v_status := 'tak_nadd';"), "kaskaden räknas efter slutprövningen"
    assert sql.count("v_totalt := v_totalt + (select coalesce(sum(value::bigint), 0) "
                     "from jsonb_each_text(v_kaskad));") == 2


def test_jobbet_ar_av_som_standard():
    config = (APP / "config.py").read_text(encoding="utf-8")
    assert re.search(r"^\s*gallring_aktiv:\s*bool\s*=\s*False\s*$", config, re.MULTILINE)
    jobb = (APP / "jobs" / "gallring.py").read_text(encoding="utf-8")
    main = (APP / "main.py").read_text(encoding="utf-8")
    assert "if settings.gallring_aktiv:" in main
    # Appens egen kod raderar aldrig i gallringen; det gör databasfunktionen.
    assert not re.search(r"delete\s+from", jobb, re.IGNORECASE)
