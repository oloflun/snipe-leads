"""Gallringen (migration 119) mot en riktig Postgres med hela migrationskedjan.

Raderingslogik får inte gå ut otestad, och minneslagret gallrar inte (det
hade testat en annan implementation än den som raderar i drift). Därför körs
de här testerna mot en TOM databas där kedjan rests från noll — i CI jobbet
"databastester" i .github/workflows/verify.yml (Postgres 17 med pgvector).

Kräver två anslutningar:
  GALLRING_TEST_DSN      ägarrollen (postgres), för att lägga in syntetiska rader
  GALLRING_TEST_APP_DSN  snajp_app, rollen api-tjänsten kör som

Hoppas över utan dem. Vägrar köra mot något annat än en lokal databas: testet
lägger in och raderar rader och sätter gallringspolicyer, och det får aldrig
nå en databas med riktig kunddata.

Alla rader är syntetiska: påhittade bolag, adresser på example.com.
"""

from __future__ import annotations

import json
import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")

pytestmark = pytest.mark.skipif(
    not (DSN and APP_DSN),
    reason="Kräver GALLRING_TEST_DSN och GALLRING_TEST_APP_DSN mot en tom testdatabas.",
)

@pytest.fixture
def anyio_backend():
    return "asyncio"


_LOKALA = {"localhost", "127.0.0.1", "::1"}

GAMMAL = "now() - interval '1000 days'"
NY = "now() - interval '10 days'"
POLICY_DAGAR = 731


async def _anslut(dsn: str) -> asyncpg.Connection:
    assert urlsplit(dsn).hostname in _LOKALA, "Gallringstestet körs bara mot en lokal databas."
    conn = await asyncpg.connect(dsn)
    spegel = await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    assert not spegel, "Databasen bär en spegelmarkör — det här är inte en testdatabas."
    return conn


def _json(varde):
    return json.loads(varde) if isinstance(varde, str) else varde


async def _ny_tenant(conn, namn: str, *, policy: int | None) -> dict:
    """En kund med arbetsyta, och policy om `policy` anges."""
    tid = uuid.uuid4()
    await conn.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, $3)",
        tid, f"gallring-{namn}-{tid.hex[:8]}", f"Testbolag {namn}",
    )
    ws = await conn.fetchval(
        "insert into workspaces (name, ss_tenant_id) values ($1, $2) returning id",
        f"Testyta {namn}", tid,
    )
    if policy is not None:
        await conn.execute(
            "insert into ss_gallringspolicy (tenant_id, dagar, beslutad_av) values ($1, $2, 'test')",
            tid, policy,
        )
    return {"id": tid, "ws": ws, "namn": namn}


async def _seeda(conn, t: dict) -> dict:
    """Gamla och nya rader i varje kategori. Returnerar id:n att kontrollera."""
    tid, ws, n = t["id"], t["ws"], t["namn"]
    ids: dict = {}

    async def val(sql: str, *args):
        return await conn.fetchval(sql, *args)

    # -- Supportmejl (med utkast) -------------------------------------------
    for alder, tid_sql in (("gammal", GAMMAL), ("ny", NY)):
        mejl = await val(
            f"""insert into ss_emails (tenant_id, provider_message_id, from_email, from_name,
                     body_text, created_at, received_at, updated_at)
                values ($1, $2, $3, 'Test Person', 'Hej, mitt ordernummer är 123.',
                        {tid_sql}, {tid_sql}, {tid_sql}) returning id""",
            tid, f"{n}-{alder}-{uuid.uuid4().hex}", f"{alder}.{n}@example.com",
        )
        await conn.execute(
            f"""insert into ss_drafts (tenant_id, email_id, content, created_at, updated_at)
                values ($1, $2, 'Hej Test Person', {tid_sql}, {tid_sql})""",
            tid, mejl,
        )
        ids[f"mejl_{alder}"] = mejl

    # -- Chattar: en gammal kund, en ny, och en gammal kund med ett nytt ärende
    async def kund(namn: str, kund_sql: str, arenden: list[str]) -> tuple:
        cid = await val(
            f"insert into ss_customers (tenant_id, name, created_at) values ($1, $2, {kund_sql}) returning id",
            tid, f"Chattkund {namn}",
        )
        await conn.execute(
            f"""insert into ss_customer_identifiers (tenant_id, customer_id, type, value, created_at)
                values ($1, $2, 'email', $3, {kund_sql})""",
            tid, cid, f"chatt.{namn}.{n}.{uuid.uuid4().hex[:6]}@example.com",
        )
        await conn.execute(
            f"insert into ss_chat_state (tenant_id, customer_id, updated_at) values ($1, $2, {kund_sql})",
            tid, cid,
        )
        await conn.execute(
            f"""insert into customer_memory (tenant_id, customer_id, fakta, created_at)
                values ($1, $2, 'Kunden heter Test och bor i Testby.', {kund_sql})""",
            tid, cid,
        )
        biljetter = []
        for a_sql in arenden:
            aid = await val(
                f"""insert into ss_tickets (tenant_id, customer_id, subject, created_at, updated_at)
                    values ($1, $2, 'Fråga', {a_sql}, {a_sql}) returning id""",
                tid, cid,
            )
            kid = await val(
                f"insert into ss_conversations (tenant_id, ticket_id, created_at) values ($1, $2, {a_sql}) returning id",
                tid, aid,
            )
            await conn.execute(
                f"""insert into ss_messages (tenant_id, conversation_id, direction, content, created_at)
                    values ($1, $2, 'inbound', 'Jag heter Test Person.', {a_sql})""",
                tid, kid,
            )
            biljetter.append(aid)
        return cid, biljetter

    ids["kund_gammal"], ids["arenden_gammal"] = await kund("gammal", GAMMAL, [GAMMAL])
    ids["kund_ny"], ids["arenden_ny"] = await kund("ny", NY, [NY])
    ids["kund_blandad"], ids["arenden_blandad"] = await kund("blandad", GAMMAL, [GAMMAL, NY])

    # -- Leads: gammalt prospekt, gammalt prospekt med nytt utskick, nytt ----
    async def prospekt(namn: str, skapad: str, skickad: str) -> uuid.UUID:
        epost = f"vd.{namn}.{n}@example.com"
        pid = await val(
            f"""insert into prospects (tenant_id, company_name, contact_name, contact_email, created_at)
                values ($1, $2, 'Test Testsson', $3, {skapad}) returning id""",
            tid, f"Påhittat AB {namn}", epost,
        )
        trad = await val(
            f"insert into outreach_threads (tenant_id, prospect_id, created_at) values ($1, $2, {skapad}) returning id",
            tid, pid,
        )
        await conn.execute(
            f"""insert into outreach_messages (tenant_id, thread_id, direction, body, sent_at, created_at)
                values ($1, $2, 'outbound', 'Hej Test', {skickad}, {skickad})""",
            tid, trad,
        )
        await conn.execute(
            f"""insert into lead_samtal (tenant_id, prospect_id, utfall, anteckning, created_at)
                values ($1, $2, 'ej_svar', 'Ringde Test', {skapad})""",
            tid, pid,
        )
        await conn.execute(
            f"""insert into ss_avregistreringslankar (token, tenant_id, email, created_at)
                values ($1, $2, $3, {skapad})""",
            f"tok-{uuid.uuid4().hex}", tid, epost,
        )
        return pid

    ids["prospekt_gammal"] = await prospekt("gammal", GAMMAL, GAMMAL)
    ids["prospekt_aktiv"] = await prospekt("aktiv", GAMMAL, NY)
    ids["prospekt_ny"] = await prospekt("ny", NY, NY)

    # -- Listor ---------------------------------------------------------------
    for alder, tid_sql in (("gammal", GAMMAL), ("ny", NY)):
        lista = await val(
            f"""insert into lead_lists (tenant_id, titel, antal, status, created_at, completed_at)
                values ($1, 'Testlista', 1, 'klar', {tid_sql}, {tid_sql}) returning id""",
            tid,
        )
        await conn.execute(
            f"""insert into lead_list_items (list_id, tenant_id, company_name, contact_email, created_at)
                values ($1, $2, 'Listbolag AB', $3, {tid_sql})""",
            lista, tid, f"lista.{alder}.{n}@example.com",
        )
        ids[f"lista_{alder}"] = lista

    # -- Jobbliggaren: ett gammalt avslutat, ett gammalt pågående, ett nytt ----
    for namn, status, tid_sql in (("gammal", "completed", GAMMAL), ("pagar", "processing", GAMMAL),
                                  ("ny", "completed", NY)):
        jobb = f"jobb-{namn}-{uuid.uuid4().hex}"
        await conn.execute(
            f"""insert into leads_job_ledger (job_id, tenant_id, scope, status, created_at, updated_at, completed_at)
                values ($1, $2, 'test', $3, {tid_sql}, {tid_sql}, {tid_sql})""",
            jobb, tid, status,
        )
        ids[f"jobb_{namn}"] = jobb

    # -- Gamla kampanjmodellen: kontakter, genererade mejl, spärr på kontakten
    bolag = await val(
        "insert into companies (workspace_id, name, industry, location) values ($1, 'Kampanjbolag AB', 'test', 'Testby') returning id",
        ws,
    )
    for alder, tid_sql in (("gammal", GAMMAL), ("ny", NY)):
        kontakt = await val(
            f"""insert into contacts (workspace_id, company_id, full_name, role, email, created_at)
                values ($1, $2, 'Kontakt Testsson', 'VD', $3, {tid_sql}) returning id""",
            ws, bolag, f"kontakt.{alder}.{n}@example.com",
        )
        await conn.execute(
            f"""insert into generated_emails (workspace_id, contact_id, subject, body, variant_length,
                     variant_type, sent_at, created_at)
                values ($1, $2, 'Hej', 'Hej Kontakt', 'kort', 'a', {tid_sql}, {tid_sql})""",
            ws, kontakt,
        )
        ids[f"kontakt_{alder}"] = kontakt
    ids["sparr_kontakt"] = await val(
        f"""insert into suppressions (workspace_id, tenant_id, contact_id, email, reason, created_at)
            values ($1, $2, $3, $4, 'avregistrerad', {GAMMAL}) returning id""",
        ws, tid, ids["kontakt_gammal"], f"kontakt.gammal.{n}@example.com",
    )
    ids["sparr_fri"] = await val(
        f"""insert into suppressions (workspace_id, tenant_id, email, reason, created_at)
            values ($1, $2, $3, 'avregistrerad', {GAMMAL}) returning id""",
        ws, tid, f"sparrad.{n}@example.com",
    )

    for alder, tid_sql in (("gammal", GAMMAL), ("ny", NY)):
        ids[f"salj_{alder}"] = await val(
            f"""insert into saljlista (workspace_id, foretagsnamn, kontaktperson, created_at, updated_at)
                values ($1, 'Säljbolag AB', 'Test Person', {tid_sql}, {tid_sql}) returning id""",
            ws,
        )

    # -- Agentloggar ------------------------------------------------------------
    for alder, tid_sql in (("gammal", GAMMAL), ("ny", NY)):
        kor = await val(
            f"""insert into agent_runs (tenant_id, agent_type, pack_version, input, output, step_log,
                     tokens_in, tokens_out, cost_usd, prospect_id, created_at)
                values ($1, 'support', 'test', 'Mejl från Test Person', 'Hej Test Person',
                        '[{{"steg": "test"}}]'::jsonb, 100, 50, 0.01, $2, {tid_sql}) returning id""",
            tid, ids["prospekt_ny"],
        )
        await conn.execute(
            f"""insert into agent_feedback (tenant_id, run_id, verdict, comment, corrected_output, created_at)
                values ($1, $2, 'bad', 'Test Person blev fel', 'Hej Test', {tid_sql})""",
            tid, kor,
        )
        await conn.execute(
            f"""insert into agent_evals (tenant_id, agent_type, input, expected_traits, created_at)
                values ($1, 'support', 'Mejl från Test Person', 'artig', {tid_sql})""",
            tid,
        )
        await conn.execute(
            f"""insert into agent_suggestions (tenant_id, agent_type, kind, title, dedupe_key, created_at)
                values ($1, 'support', 'kb_article', 'Förslag', $2, {tid_sql})""",
            tid, f"{alder}-{uuid.uuid4().hex}",
        )
        await conn.execute(
            f"""insert into platform_events (tenant_id, level, source, message, created_at)
                values ($1, 'info', 'test', 'Händelse om Test Person', {tid_sql})""",
            tid,
        )
        await conn.execute(
            f"""insert into leads_sidcache (tenant_id, url, innehall, hamtad_at)
                values ($1, $2, 'Kontakt: Test Person', {tid_sql})""",
            tid, f"https://{alder}.example.com/{uuid.uuid4().hex}",
        )
        ids[f"korning_{alder}"] = kor

    # -- Bokföringsunderlag: ska aldrig röras ----------------------------------
    ids["underlag"] = await val(
        f"""insert into bk_underlag (tenant_id, sha256, filnamn, mimetyp, status, datum, created_at)
            values ($1, $2, 'kvitto.pdf', 'application/pdf', 'klar', (now() - interval '1000 days')::date, {GAMMAL})
            returning id""",
        tid, uuid.uuid4().hex,
    )
    return ids


#: Tabeller med tenant_id (direkt eller via arbetsytan) som ögonblicksbilden räknar.
_TABELLER_TENANT = [
    "ss_emails", "ss_drafts", "ss_customers", "ss_customer_identifiers", "ss_tickets",
    "ss_conversations", "ss_messages", "customer_memory", "ss_chat_state", "prospects",
    "outreach_threads", "outreach_messages", "lead_samtal", "ss_avregistreringslankar",
    "lead_lists", "lead_list_items", "leads_job_ledger", "suppressions", "agent_runs",
    "agent_feedback", "agent_evals", "agent_suggestions", "platform_events", "leads_sidcache",
    "bk_underlag",
]
_TABELLER_YTA = ["contacts", "generated_emails", "saljlista", "companies"]


async def _bild(conn, t: dict) -> dict:
    """Ögonblicksbild av kundens rader: antal per tabell plus agentloggarnas text."""
    bild = {}
    for tabell in _TABELLER_TENANT:
        bild[tabell] = await conn.fetchval(f"select count(*) from {tabell} where tenant_id = $1", t["id"])
    for tabell in _TABELLER_YTA:
        bild[tabell] = await conn.fetchval(f"select count(*) from {tabell} where workspace_id = $1", t["ws"])
    bild["agent_runs_text"] = await conn.fetchval(
        "select count(*) from agent_runs where tenant_id = $1 and input is not null", t["id"]
    )
    bild["suppressions_kopplade"] = await conn.fetchval(
        "select count(*) from suppressions where tenant_id = $1 and contact_id is not null", t["id"]
    )
    return bild


async def _finns(conn, tabell: str, id_) -> bool:
    nyckel = {"ss_avregistreringslankar": "token", "leads_job_ledger": "job_id"}.get(tabell, "id")
    return bool(await conn.fetchval(f"select count(*) from {tabell} where {nyckel} = $1", id_))


@pytest.mark.anyio
async def test_gallringen_tar_det_gamla_i_varje_kategori_och_bara_det():
    conn = await _anslut(DSN)
    try:
        a = await _ny_tenant(conn, "a", policy=POLICY_DAGAR)
        b = await _ny_tenant(conn, "b", policy=None)
        ids_a = await _seeda(conn, a)
        await _seeda(conn, b)
        fore_b = await _bild(conn, b)
        fore_a = await _bild(conn, a)

        # Torrkörningen räknar och loggar men ändrar ingenting.
        torr = _json(await conn.fetchval("select gallra_tenant($1, true)", a["id"]))
        assert torr["status"] == "torrkorning"
        assert await _bild(conn, a) == fore_a, "torrkörningen ändrade något"
        print("\nTORRKÖRNING", json.dumps(torr["antal"], ensure_ascii=False))

        svar = _json(await conn.fetchval("select gallra_tenant($1, false)", a["id"]))
        assert svar["status"] == "klar"
        antal = {k: v["antal"] for k, v in svar["antal"].items()}
        print("SKARP", json.dumps(antal, ensure_ascii=False))
        # Torrkörningen räknade exakt det som sedan gjordes.
        assert {k: v["antal"] for k, v in torr["antal"].items()} == antal
        assert antal == {
            "ss_emails": 1, "ss_tickets": 2, "customer_memory": 2, "ss_customers": 1,
            "prospects": 1, "lead_list_items": 1, "lead_lists": 1, "leads_job_ledger": 1,
            "ss_avregistreringslankar": 1, "generated_emails": 1, "contacts": 1, "saljlista": 1,
            "agent_runs": 1, "agent_feedback": 1, "agent_evals": 1, "agent_suggestions": 1,
            "platform_events": 1, "leads_sidcache": 1, "ss_channel_inbound_seen": 0,
            "suppressions": 1,
        }

        # Gamla rader borta i varje kategori ...
        assert not await _finns(conn, "ss_emails", ids_a["mejl_gammal"])
        assert not await _finns(conn, "ss_customers", ids_a["kund_gammal"])
        assert not await _finns(conn, "ss_tickets", ids_a["arenden_gammal"][0])
        assert not await _finns(conn, "ss_tickets", ids_a["arenden_blandad"][0])
        assert not await _finns(conn, "prospects", ids_a["prospekt_gammal"])
        assert not await _finns(conn, "lead_lists", ids_a["lista_gammal"])
        assert not await _finns(conn, "leads_job_ledger", ids_a["jobb_gammal"])
        assert not await _finns(conn, "contacts", ids_a["kontakt_gammal"])
        assert not await _finns(conn, "saljlista", ids_a["salj_gammal"])
        # ... och kaskaden tog barnen.
        assert not await conn.fetchval(
            "select count(*) from ss_drafts where email_id = $1", ids_a["mejl_gammal"])
        assert not await conn.fetchval(
            "select count(*) from outreach_threads where prospect_id = $1", ids_a["prospekt_gammal"])

        # Nya rader, och gamla som hänger på ny aktivitet, står kvar.
        for tabell, nyckel in (
            ("ss_emails", "mejl_ny"), ("ss_customers", "kund_ny"), ("ss_customers", "kund_blandad"),
            ("prospects", "prospekt_ny"), ("prospects", "prospekt_aktiv"), ("lead_lists", "lista_ny"),
            ("leads_job_ledger", "jobb_ny"), ("leads_job_ledger", "jobb_pagar"),
            ("contacts", "kontakt_ny"), ("saljlista", "salj_ny"), ("agent_runs", "korning_ny"),
        ):
            assert await _finns(conn, tabell, ids_a[nyckel]), f"{tabell}/{nyckel} försvann"
        assert await _finns(conn, "ss_tickets", ids_a["arenden_blandad"][1])
        assert await conn.fetchval(
            "select count(*) from ss_avregistreringslankar a join prospects p "
            "on lower(p.contact_email) = lower(a.email) where p.id = $1", ids_a["prospekt_aktiv"]) == 1

        # Agentloggen: texten nollad, siffrorna kvar, kopplingen borta.
        rad = await conn.fetchrow("select * from agent_runs where id = $1", ids_a["korning_gammal"])
        assert rad is not None
        assert rad["input"] is None and rad["output"] is None and rad["grounding"] is None
        assert _json(rad["step_log"]) == [] and rad["prospect_id"] is None
        assert rad["tokens_in"] == 100 and float(rad["cost_usd"]) == 0.01
        ny_rad = await conn.fetchrow("select * from agent_runs where id = $1", ids_a["korning_ny"])
        assert ny_rad["input"] == "Mejl från Test Person"
        assert not await conn.fetchval(
            "select count(*) from agent_feedback where run_id = $1 and comment is not null",
            ids_a["korning_gammal"])

        # Spärrlistan och bokföringsunderlaget är orörda.
        assert await _finns(conn, "suppressions", ids_a["sparr_kontakt"])
        assert await _finns(conn, "suppressions", ids_a["sparr_fri"])
        assert await conn.fetchval(
            "select contact_id from suppressions where id = $1", ids_a["sparr_kontakt"]) is None
        assert await _finns(conn, "bk_underlag", ids_a["underlag"])
        efter_a = await _bild(conn, a)
        assert efter_a["suppressions"] == fore_a["suppressions"]
        assert efter_a["bk_underlag"] == fore_a["bk_underlag"]

        # Den andra kunden (utan policy) är orörd, också när den själv körs.
        assert await _bild(conn, b) == fore_b
        utan = _json(await conn.fetchval("select gallra_tenant($1, false)", b["id"]))
        assert utan["status"] == "ingen_policy"
        assert await _bild(conn, b) == fore_b

        # En andra körning har ingenting kvar att göra.
        igen = _json(await conn.fetchval("select gallra_tenant($1, false)", a["id"]))
        assert igen["totalt"] == 0, igen["antal"]

        # Loggen bär torrkörningen och de två skarpa körningarna.
        logg = await conn.fetch(
            "select status, torrkorning, totalt from ss_gallringslogg where tenant_id = $1 order by id",
            a["id"])
        assert [(r["status"], r["torrkorning"]) for r in logg] == [
            ("torrkorning", True), ("klar", False), ("klar", False)]
        assert logg[1]["totalt"] == sum(v for k, v in antal.items() if k != "suppressions")
        print("RESULTAT kategorier gallrade, ny data kvar, kund B orörd, spärr och underlag orörda")
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_spegeln_gallrar_det_synken_inte_for_over():
    """Migration 133 (Codex runda 3, 2026-11-19): i en spegel nollas urvalet för
    tabellerna synken för över, och resten gallras som i main. Feedbacktexten,
    de genererade mejlen, kontakterna, säljlistan, händelserna och sidcachen
    försvinner; supportmejl, ärenden, prospekt och agentloggar står kvar åt
    synken."""
    conn = await _anslut(DSN)
    try:
        t = await _ny_tenant(conn, "spegel", policy=POLICY_DAGAR)
        ids = await _seeda(conn, t)
        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute("create table public.mirror_meta (environment text)")
            svar = _json(await conn.fetchval("select gallra_tenant($1, false)", t["id"]))
            assert svar["status"] == "klar" and svar["spegel"] is True
            antal = {k: v["antal"] for k, v in svar["antal"].items()}
            print("\nSPEGEL", json.dumps(antal, ensure_ascii=False))
            assert antal == {
                "ss_emails": 0, "ss_tickets": 0, "customer_memory": 0, "ss_customers": 0,
                "prospects": 0, "lead_list_items": 0, "lead_lists": 0, "leads_job_ledger": 0,
                "ss_avregistreringslankar": 0, "generated_emails": 1, "contacts": 1, "saljlista": 1,
                "agent_runs": 0, "agent_feedback": 1, "agent_evals": 1, "agent_suggestions": 0,
                "platform_events": 1, "leads_sidcache": 1, "ss_channel_inbound_seen": 0,
                "suppressions": 1,
            }
            # Det osynkade är borta eller anonymiserat ...
            assert not await _finns(conn, "contacts", ids["kontakt_gammal"])
            assert not await _finns(conn, "saljlista", ids["salj_gammal"])
            assert not await conn.fetchval(
                "select count(*) from agent_feedback where run_id = $1 and comment is not null",
                ids["korning_gammal"])
            assert not await conn.fetchval(
                "select count(*) from generated_emails where contact_id = $1", ids["kontakt_gammal"])
            # ... och det synkade står kvar åt synken.
            assert await _finns(conn, "ss_emails", ids["mejl_gammal"])
            assert await _finns(conn, "ss_customers", ids["kund_gammal"])
            assert await _finns(conn, "prospects", ids["prospekt_gammal"])
            rad = await conn.fetchrow("select input from agent_runs where id = $1", ids["korning_gammal"])
            assert rad["input"] == "Mejl från Test Person"
            # Spärren står kvar, frikopplad från den raderade kontakten.
            assert await _finns(conn, "suppressions", ids["sparr_kontakt"])
        finally:
            await tx.rollback()
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_spegeln_raderar_barn_som_synken_lamnat_foraldralosa():
    """Migration 134 (Codex runda 4, 2026-11-19): synken raderar kunden i
    replica-läge, där kaskaden inte körs. Kanalkontakten och chattläget blir
    kvar utan förälder; spegelns gallring tar dem, oberoende av policy."""
    conn = await _anslut(DSN)
    try:
        t = await _ny_tenant(conn, "foraldralos", policy=None)
        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute("create table public.mirror_meta (environment text)")
            kund = await conn.fetchval(
                "insert into ss_customers (tenant_id, name) values ($1, 'Kanal Kund') returning id", t["id"])
            await conn.execute(
                "insert into ss_chat_state (tenant_id, customer_id) values ($1, $2)", t["id"], kund)
            anslutning = await conn.fetchval(
                "insert into ss_channel_connections (tenant_id, kanal, extern_id) values ($1, 'whatsapp', $2)"
                " returning id",
                t["id"], f"test-{uuid.uuid4().hex}")
            await conn.execute(
                """insert into ss_channel_contacts (tenant_id, anslutning_id, customer_id, extern_anvandare,
                       visningsnamn) values ($1, $2, $3, '46700000000', 'Kanal Kund')""",
                t["id"], anslutning, kund)
            kvar_kund = await conn.fetchval(
                "insert into ss_customers (tenant_id, name) values ($1, 'Kvar Kund') returning id", t["id"])
            await conn.execute(
                "insert into ss_chat_state (tenant_id, customer_id) values ($1, $2)", t["id"], kvar_kund)

            # Som synken: radera föräldern i replica-läge.
            await conn.execute("set local session_replication_role = replica")
            await conn.execute("delete from ss_customers where id = $1", kund)
            await conn.execute("set local session_replication_role = origin")
            assert await conn.fetchval("select count(*) from ss_channel_contacts where customer_id = $1", kund) == 1

            await conn.execute("delete from ss_gallringskorning")
            svar = _json(await conn.fetchval("select gallra_alla(5)"))
            assert svar["spegel"] is True
            assert svar["foraldralosa"]["ss_channel_contacts"] == 1
            assert svar["foraldralosa"]["ss_chat_state"] == 1
            assert not await conn.fetchval("select count(*) from ss_channel_contacts where customer_id = $1", kund)
            assert not await conn.fetchval("select count(*) from ss_chat_state where customer_id = $1", kund)
            assert await conn.fetchval("select count(*) from ss_chat_state where customer_id = $1", kvar_kund) == 1
        finally:
            await tx.rollback()
        # Utanför en spegel gör funktionen ingenting.
        assert _json(await conn.fetchval("select gallra_spegelns_foraldralosa()")) == {"spegel": False}
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_schemalagda_korningen_tak_dygnsspärr_och_spegel():
    """gallra_alla som snajp_app: bara kunder med policy, taket håller, och en
    andra körning samma dygn gör ingenting."""
    agare = await _anslut(DSN)
    app = await _anslut(APP_DSN)
    try:
        # Testdatabasen är tom på riktiga kunder; andra testers policyer och
        # dygnets spärr nollas så att körningen bara ser det här testets kunder.
        await agare.execute("delete from ss_gallringspolicy")
        await agare.execute("delete from ss_gallringskorning")

        liten = await _ny_tenant(agare, "liten", policy=POLICY_DAGAR)
        stor = await _ny_tenant(agare, "stor", policy=30)  # ett "felaktigt" policyvärde
        utan = await _ny_tenant(agare, "utan", policy=None)
        for t, antal_gamla in ((liten, 1), (stor, 6), (utan, 6)):
            for _ in range(antal_gamla):
                await agare.execute(
                    f"insert into platform_events (tenant_id, level, source, message, created_at) "
                    f"values ($1, 'info', 'test', 'gammal', {GAMMAL})", t["id"])
            await agare.execute(
                f"insert into platform_events (tenant_id, level, source, message, created_at) "
                f"values ($1, 'info', 'test', 'ny', {NY})", t["id"])

        async def handelser(t):
            return await agare.fetchval("select count(*) from platform_events where tenant_id = $1", t["id"])

        # Appens roll får inte sätta en policy: det beslutet är ägarens.
        with pytest.raises(asyncpg.PostgresError):
            await app.execute(
                "insert into ss_gallringspolicy (tenant_id, dagar, beslutad_av) values ($1, 999, 'app')",
                utan["id"])
        # ... och inte anropa per-kund-funktionen med egna parametrar.
        with pytest.raises(asyncpg.PostgresError):
            await app.fetchval("select gallra_tenant($1, false)", liten["id"])

        svar = _json(await app.fetchval("select gallra_alla(5)"))
        print("\nSCHEMALAGD", json.dumps(svar, ensure_ascii=False, default=str)[:600])
        assert svar["status"] == "kord"
        per_kund = {k["tenant_id"]: k for k in svar["kunder"]}
        assert set(per_kund) == {str(liten["id"]), str(stor["id"])}, "kund utan policy kördes"
        assert per_kund[str(liten["id"])]["status"] == "klar"
        assert per_kund[str(stor["id"])]["status"] == "tak_nadd"
        assert await handelser(liten) == 1
        assert await handelser(stor) == 7, "taket höll inte"
        assert await handelser(utan) == 7, "kund utan policy gallrades"

        korning = await agare.fetchrow("select * from ss_gallringskorning")
        assert korning["klar_at"] is not None and korning["tak_nadda"] == 1

        # Andra körningen samma dygn gör ingenting, även med nytt gammalt innehåll.
        await agare.execute(
            f"insert into platform_events (tenant_id, level, source, message, created_at) "
            f"values ($1, 'info', 'test', 'gammal igen', {GAMMAL})", liten["id"])
        igen = _json(await app.fetchval("select gallra_alla(5)"))
        assert igen["status"] == "redan_kord"
        assert await handelser(liten) == 2

        # En spegel kör också (migration 133). Händelserna synkas inte, så
        # spegeln gallrar dem själv; det synkade lämnas åt synken (nästa test).
        tx = agare.transaction()
        await tx.start()
        try:
            await agare.execute("create table public.mirror_meta (environment text)")
            await agare.execute("delete from ss_gallringskorning")
            spegel = _json(await agare.fetchval("select gallra_alla(5)"))
            assert spegel["status"] == "kord" and spegel["spegel"] is True
            assert await handelser(liten) == 1
        finally:
            await tx.rollback()

        # Insynen: appens roll läser loggen genom lagringen, som adminvägen gör.
        from app.storage.postgres import PostgresStorage

        lagring = await PostgresStorage.connect(APP_DSN)
        try:
            logg = await lagring.list_gallringslogg(tenant_id=str(stor["id"]))
            assert logg and logg[0]["status"] == "tak_nadd"
            assert isinstance(logg[0]["antal"], dict)
            policyer = {p["tenant_id"]: p for p in await lagring.list_gallringspolicyer()}
            assert policyer[str(utan["id"])]["dagar"] is None
            assert policyer[str(liten["id"])]["dagar"] == POLICY_DAGAR
            assert (await lagring.gallra_dygnet(tak=5))["status"] == "redan_kord"
            assert (await lagring.list_gallringskorningar())[0]["tak_nadda"] == 1
        finally:
            await lagring.pool.close()
        print("RESULTAT bara kunder med policy, taket höll, andra körningen samma dygn gjorde inget, spegeln gallrade det osynkade")
    finally:
        await agare.execute("delete from ss_gallringspolicy")
        await app.close()
        await agare.close()
