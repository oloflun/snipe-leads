#!/usr/bin/env python3
"""Flyttar det som blivit kvar i Supabase till Railway.

    python scripts/flytta_fran_supabase.py --fran export.json               # visa
    python scripts/flytta_fran_supabase.py --fran export.json --apply       # skriv
    python scripts/flytta_fran_supabase.py --fran export.json --env development

## Varför den här och inte scripts/migrera_till_railway.py

Den flyttar en KUNDS agentprofil mellan två BACKENDER via deras API:er, och
kräver en fungerande API-nyckel i båda ändar. Supabase-projektet har ingen
backend längre — det är bara en databas som ligger kvar. Det här skriptet tar
därför en JSON-export och skriver den direkt till Railway-Postgres.

## Varför en JSON-fil och inte en direktkoppling

Supabase-poolern nekar anslutningar från en utvecklingsmaskin (dokumenterat i
migrera_till_railway.py), och tjänstenyckeln för rätt projekt finns inte i
.env.deploy — den som ligger där pekar på ett annat, äldre projekt. Exporten
görs därför med det verktyg som faktiskt når projektet, och skriptet läser
resultatet.

Det gör också bytet GRANSKBART: filen går att läsa innan den skrivs, vilket en
direktkopiering aldrig blir.

## Vad som flyttas, och vad som inte gör det

Flyttas: kunskapsbasartiklar och kontextdokument (SOUL, affärskontext). Alltså
KONFIGURATIONEN — det som avgör hur agenten beter sig.

Flyttas inte:

  * Ärenden, mejl, prospekt och körningar. Det är historik, den hör till den
    miljö den uppstod i, och dubblerad ärendehistorik i två system är sämre än
    en som ligger kvar på ett ställe. Samma regel som migrera_till_railway.py.
  * auth.users. Supabases lösenordshashar är bcrypt (GoTrue) och Railway
    verifierar scrypt (lib/password.ts) — en flyttad rad kan alltså inte logga
    in, och en rad som ser ut som ett konto men inte fungerar är sämre än inget
    konto. Beslut 2026-08-24: kontona återskapas via "glömt lösenord" i stället.
    Alla fem i exporten är dessutom interna, inte kunder.

## Idempotent

Nycklad på (tenant, titel) för artiklar och (tenant, kind, version) för
kontextdokument. Skriptet går att köra om utan att skapa dubbletter, vilket är
skillnaden mellan ett verktyg och en engångsåtgärd man inte vågar upprepa.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402


def far_importeras(mal_senaste: dict | None, kalla: dict) -> tuple[bool, str]:
    """Får det här kontextdokumentet skrivas som MÅLETS nya senaste version?

    ## Felet den här funktionen finns för att omöjliggöra

    Den 2026-08-24 importerades två dokument ur Supabase till development. Båda
    skrevs som `max(version) + 1`, alltså som senaste, och
    `get_latest_context_doc` plockar just den. Följden: Nordlys Handels
    affärskontext gick från kundens egna 726 tecken till en 43 teckens stubbe,
    och röstdokumentet från 1024 till 39. Agenten bytte underlag mitt i drift
    och ingenting felade.

    Den gamla kontrollen jämförde bara på EXAKT innehåll — den upptäckte
    dubbletter, aldrig en försämring.

    ## Regeln, och varför den är så trubbig

    Supabase är den AVVECKLADE stacken. Allt som ligger där är per definition
    äldre än det som står i Railway. Ett dokument därifrån får därför bara
    fylla ett TOMT fack, aldrig ersätta något som redan finns.

    Ingen jämförelse på tidsstämpel eller längd. Båda kan ljuga — en
    ominsättning ger ny tidsstämpel åt gammalt innehåll, och en kortare text
    kan vara en avsiktlig förkortning. Riktningen mellan systemen kan inte
    ljuga, och det är den regeln vilar på.
    """
    if mal_senaste is None:
        return True, "facket är tomt"
    if (mal_senaste.get("content") or "") == kalla["content"]:
        return False, "identiskt innehåll finns redan"
    return False, (
        f"målet har redan ett dokument ({len(mal_senaste.get('content') or '')} tecken, "
        f"v{mal_senaste.get('version')}), och källan är den avvecklade stacken. "
        f"Importen skulle ha blivit ny SENASTE version och tyst bytt agentens underlag."
    )


def _tenant_id(cur, slug: str) -> str | None:
    cur.execute("select id from public.ss_tenants where slug = %s", (slug,))
    rad = cur.fetchone()
    return str(rad[0]) if rad else None


def kor(export: dict, env: str, apply: bool) -> int:
    conn = psycopg2.connect(dsn(env_read(), env), connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()

    saknade_tenants: list[str] = []
    planerat = {"kb": 0, "ctx": 0}
    hoppat = {"kb": 0, "ctx": 0}

    print(f"miljö: {env}\n")

    for artikel in export.get("kb", []):
        tid = _tenant_id(cur, artikel["tenant_slug"])
        if not tid:
            saknade_tenants.append(artikel["tenant_slug"])
            continue
        cur.execute(
            "select 1 from public.ss_knowledge_base where tenant_id = %s and title = %s",
            (tid, artikel["title"]),
        )
        if cur.fetchone():
            hoppat["kb"] += 1
            continue
        planerat["kb"] += 1
        print(f"  + kb   {artikel['tenant_slug']:<16}{artikel['title']}")
        if apply:
            # embedding lämnas NULL med flit. Vektorn hör till målmiljöns
            # embeddings-modell och dimension; en kopierad vektor från en annan
            # modell är tyst fel, och sökningen har en fungerande väg utan den
            # (storage.search_kb faller tillbaka på svensk full-text).
            cur.execute(
                """
                insert into public.ss_knowledge_base (tenant_id, title, content, category)
                values (%s, %s, %s, %s)
                """,
                (tid, artikel["title"], artikel["content"], artikel["category"]),
            )

    for doc in export.get("context_docs", []):
        tid = _tenant_id(cur, doc["tenant_slug"])
        if not tid:
            saknade_tenants.append(doc["tenant_slug"])
            continue
        cur.execute(
            """
            select content, version from public.agent_context_docs
            where tenant_id = %s and kind = %s
            order by version desc limit 1
            """,
            (tid, doc["kind"]),
        )
        rad = cur.fetchone()
        senaste = {"content": rad[0], "version": rad[1]} if rad else None
        tillatet, skal = far_importeras(senaste, doc)
        if not tillatet:
            hoppat["ctx"] += 1
            print(f"  - ctx  {doc['tenant_slug']:<16}{doc['kind']:<20}{skal}")
            continue
        planerat["ctx"] += 1
        print(f"  + ctx  {doc['tenant_slug']:<16}{doc['kind']:<20}{skal}")
        if apply:
            # Versionen räknas om i MÅLET i stället för att kopieras. Målet kan
            # redan ha dokument av samma kind, och en kopierad version krockar
            # då med en befintlig rad — eller, värre, ser äldre ut än den är och
            # blir aldrig den som get_latest_context_doc plockar.
            cur.execute(
                """
                insert into public.agent_context_docs (tenant_id, kind, content, source, version)
                values (%s, %s, %s, %s,
                        coalesce((select max(version) from public.agent_context_docs
                                  where tenant_id = %s and kind = %s), 0) + 1)
                """,
                (tid, doc["kind"], doc["content"], doc.get("source", "supabase-import"), tid, doc["kind"]),
            )

    if saknade_tenants:
        conn.rollback()
        conn.close()
        print(f"\nAVBRUTET: tenants saknas i målet: {sorted(set(saknade_tenants))}")
        print("Skapa dem först (scripts/onboard_tenant.py) — en artikel utan sin kund")
        print("hamnar hos fel kund eller ingen alls.")
        return 1

    if apply:
        conn.commit()
    else:
        conn.rollback()
    conn.close()

    print(
        f"\n{planerat['kb']} artiklar och {planerat['ctx']} kontextdokument "
        f"{'skrevs' if apply else 'skulle skrivas'}. "
        f"Hoppade över {hoppat['kb'] + hoppat['ctx']} som redan finns."
    )
    if not apply:
        print("Kör med --apply.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fran", required=True, help="JSON-export ur Supabase")
    ap.add_argument("--env", choices=("main", "development"), default="main")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    export = json.loads(Path(args.fran).read_text(encoding="utf-8"))
    return kor(export, args.env, args.apply)


def demo() -> None:
    """Kontrollen: exakt det som gick fel 2026-08-24 måste nu vägras."""
    stubbe = {
        "kind": "product_marketing",
        "content": "# Nordlys Handel\nSäljer köksredskap online.",
    }

    # Tomt fack -> importera.
    ok, skal = far_importeras(None, stubbe)
    assert ok, skal

    # DET FAKTISKA FELET: målet har kundens rika dokument, källan en stubbe.
    rikt = {"content": "Vad vi säljer: Inredning och utemiljö för företag." * 14, "version": 4}
    ok, skal = far_importeras(rikt, stubbe)
    assert not ok, "importen som sänkte Nordlys Handel skulle ha vägrats"
    assert "SENASTE" in skal

    # Identiskt innehåll -> hoppa, men av ett annat skäl.
    ok, skal = far_importeras({"content": stubbe["content"], "version": 1}, stubbe)
    assert not ok and "identiskt" in skal

    # Och åt andra hållet: en LÄNGRE källa får inte heller gå in. Riktningen
    # avgör, inte storleken — annars hade regeln gått att kringgå med en
    # utfyllnadsrad.
    lang = {"kind": "soul", "content": "x" * 5000}
    ok, skal = far_importeras({"content": "kort men aktuell", "version": 9}, lang)
    assert not ok, "längden får inte ge företräde"

    print("flytta_fran_supabase: ok")


if __name__ == "__main__":
    # --demo kollas före argparse: självkontrollen ska kunna köras utan att
    # peka ut en exportfil, och utan att röra en databas.
    if "--demo" in sys.argv:
        demo()
        raise SystemExit(0)
    raise SystemExit(main())


