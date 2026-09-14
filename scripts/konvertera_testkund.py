#!/usr/bin/env python3
"""Testkund → riktig kund: profilen ÖVERSKRIVS, den sammanfogas inte.

    python scripts/konvertera_testkund.py --fran testkund-a1b2c3d4 --till livrustning
    python scripts/konvertera_testkund.py --fran testkund-a1b2c3d4 --till livrustning --apply
    python scripts/konvertera_testkund.py --env development --fran ... --till ...

## Steget för demo → riktigt konto (Fas 3.5)

`--prospekt <id,id,...>` är opt-in-undantaget till "prospekt kopieras inte"
nedan: de specifika prospekt kunden själv pekar ut under en demo (testkörda
bolag med RIKTIGA researchresultat, inte påhittade) kan flyttas med över,
märkta `origin='manual'`, med sina `prospect_sources`-rader. Kör alltid UTAN
`--apply` först — torrkörningen listar exakt vad som skulle kopieras
(bolagsnamn, orgnr, e-post, antal källrader) och vad som hoppas över och
varför, innan något skrivs:

    python scripts/konvertera_testkund.py --fran testkund-a1b2c3d4 --till livrustning --prospekt 3fae21e0-...,9b110c44-...
    python scripts/konvertera_testkund.py --fran testkund-a1b2c3d4 --till livrustning --prospekt 3fae21e0-...,9b110c44-... --apply

## Varför skriptet finns

En testkund som blir kund byter tenant: testytan har en egen tenant skapad i
drift (migration 040), den riktiga kunden får en genom `onboard_tenant.py`. Utan
det här steget står den nya tenanten tom, och allt kunden ställde in under
testet — kunskapsbasen, rösten, målgruppen, reglerna per fack — ligger kvar i
testtenanten.

Följden är den värsta sorten: agenten betedde sig på ett sätt under testet och
på ett annat i drift, och skillnaden märks först när ett svar blir fel.

## Varför ÖVERSKRIVNING och inte sammanfogning

En sammanfogning ger en tredje konfiguration som ingen har provkört. Det som
såldes in var testets beteende; det som ska köras i drift är därför exakt
testets konfiguration, inte en blandning av den och tomma defaultvärden.

Målets befintliga rader raderas alltså först. Det är avsiktligt destruktivt, och
därför kräver skriptet `--apply` och skriver ut vad som kommer att försvinna.

## Riktningen

    testkund-<ws>  ──>  kundens tenant

Aldrig tillbaka. Två spärrar:

  * källan MÅSTE ha en slug som börjar på `testkund-`
  * målet får INTE ha det

Det som INTE kopieras som standard: ärenden, mail, prospekt, körningar och
beslutslogg. Det är testkundens historik, inte deras konfiguration — och en
riktig kunds första dag ska inte börja med sex påhittade ärenden i inkorgen.

`--prospekt` (Fas 3.5, ovan) är det enda undantaget, och bara för de rader
kunden själv pekar ut. `agent_runs` följer INTE med ens då — se
`kopiera_prospekt()`.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "snajp-support"))

import psycopg2  # noqa: E402

from railway_provision import env_read  # noqa: E402
from railway_migrate import dsn  # noqa: E402

# Ren funktion, ingen databas (app/leads/orgnr.py importerar bara `re`) — samma
# kontroll som POST /api/leads/prospects/{id}/befordra (app/api/leads.py) kör.
# Se app/leads/befordran.py:s docstring för varför den bor på ETT ställe.
from app.leads.befordran import saknade_falt  # noqa: E402
from app.tenants.konvertera import kontrollera_riktning  # noqa: E402

#: (tabell, kolumner) — allt som utgör kundens KONFIGURATION.
#: Ordningen spelar ingen roll: inga främmande nycklar mellan dem.
TABELLER: list[tuple[str, tuple[str, ...]]] = [
    # `embedding` följer med. Utan den måste den nya tenanten embeddas om, och
    # tills det gjorts söker agenten med fulltext i stället för vektorer — alltså
    # sämre träffar än under testet, vilket är precis skillnaden vi undviker.
    ("ss_knowledge_base", ("title", "content", "category", "embedding")),
    ("ss_category_rules", ("category", "mode")),
    # `settings` (jsonb, migration 023) bär BÅDE ICP och autonominivån.
    ("agent_configs", ("agent_type", "settings", "instructions_md", "tone", "taxonomy")),
    # Röstdokumentet (SOUL) och produktkontexten. `version` följer med så att
    # historiken inte börjar om på 1 i den nya tenanten.
    ("agent_context_docs", ("kind", "content", "source", "version")),
]


def tenant_id(cur, slug: str) -> str:
    cur.execute("select id from public.ss_tenants where slug = %s", (slug,))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYT: ingen tenant med slug {slug!r}.")
    return rad[0]


def rakna(cur, tabell: str, tid: str) -> int:
    cur.execute(f"select count(*) from public.{tabell} where tenant_id = %s", (tid,))
    return cur.fetchone()[0]


# -- Fas 3.4/3.5: --prospekt, det opt-in-undantag §4 i planen beskriver -----

#: Allt utom `id`, `tenant_id`, `origin` (sätts explicit till 'manual') och
#: `foretagsnyckel` (GENERATED, se fällan i kopiera_prospekt) och `created_at`
#: (den nya raden får sin egen — den är en NY rad, inte samma rad flyttad).
PROSPEKT_KOLUMNER: tuple[str, ...] = (
    "company_name", "contact_name", "contact_email", "language_state", "status",
    "icp_fit", "qualified", "disqualifiers",
    "orgnr", "ort", "postnr", "sni", "website", "anstallda", "omsattning",
    "score_breakdown", "score_total",
)

#: psycopg2 läser `jsonb` tillbaka som Python-`str` (ingen adapter registrerad
#: här, till skillnad från backendens asyncpg-lager). Skickas den strängen
#: tillbaka OTYPAD som VALUES-parameter till en jsonb-kolumn litar man på att
#: Postgres gissar rätt på ett "unknown"-literal — `::jsonb` här tar bort
#: gissningen. `disqualifiers` (text[]) behöver ingen cast (psycopg2 adapterar
#: Python-listor till ARRAY-literal automatiskt), men står med för tydlighetens skull.
_EXPLICIT_CAST: dict[str, str] = {
    "score_breakdown": "jsonb",
    "disqualifiers": "text[]",
}


def _platshallare(kolumn: str) -> str:
    typ = _EXPLICIT_CAST.get(kolumn)
    return f"%s::{typ}" if typ else "%s"


def _parsa_id_lista(rå: str) -> list[str]:
    """'a,b, c' -> ['a','b','c']. Kraschar HÄRDVILLIGT på ett ogiltigt uuid —
    hellre det än ett `= any(%s::uuid[])` som failar djupt inne i psycopg2 med
    ett meddelande som inte säger vilket id som var fel."""
    ider = [bit.strip() for bit in rå.split(",") if bit.strip()]
    for id_sträng in ider:
        try:
            uuid.UUID(id_sträng)
        except ValueError:
            sys.exit(f"AVBRYT: {id_sträng!r} (--prospekt) är inte ett giltigt uuid.")
    return ider


def hamta_prospekt(cur, kalla: str, ider: list[str]) -> dict[str, dict]:
    """De efterfrågade raderna, nycklade på id (som sträng). Id:n som inte
    finns hos källan saknas helt enkelt i returvärdet — anroparen skiljer
    "hittades inte" från "hittades" genom en vanlig `.get()`."""
    if not ider:
        return {}
    cur.execute(
        f"""select id, origin, foretagsnyckel, {", ".join(PROSPEKT_KOLUMNER)}
              from public.prospects
             where tenant_id = %s and id = any(%s::uuid[])""",
        (kalla, ider),
    )
    kolumnnamn = [beskrivning[0] for beskrivning in cur.description]
    return {str(rad[0]): dict(zip(kolumnnamn, rad)) for rad in cur.fetchall()}


def avgor_atgard(rad: dict, *, finns_i_malet: bool) -> tuple[str, list[str]]:
    """Ren beslutsfunktion för EN kandidatrad — ingen databas, bara dicten och
    en redan uträknad kollisionsflagga. Utbruten hit specifikt för att vara
    testbar utan en riktig Postgres-anslutning (se tests/test_konvertera_testkund.py).

    Returnerar (åtgärd, detalj):
      * "krock"          — foretagsnyckel finns redan hos måltenanten. Fälla 1:
                            kopiering hade kringgått 90-dagarskarensen i
                            send-guardens regel 5.
      * "valideringsfel"  — origin='example' och bolaget klarar inte SAMMA
                            kontroll som /befordra (Fas 3.2). Fälla 2.
                            `detalj` är bristlistan, på svenska.
      * "kopiera"         — inget i vägen.
    """
    if finns_i_malet:
        return "krock", []
    if rad.get("origin") == "example":
        brister = saknade_falt(
            orgnr=rad.get("orgnr"),
            website=rad.get("website"),
            contact_email=rad.get("contact_email"),
        )
        if brister:
            return "valideringsfel", brister
    return "kopiera", []


def kopiera_prospekt(cur, kalla: str, mal: str, ider: list[str], *, apply: bool) -> None:
    """--prospekt: kopierar de utpekade raderna (nya id:n, origin='manual')
    plus deras prospect_sources. Skriver bara vid apply=True — annars bara
    torrkörningens utskrift, som ska räcka för att avgöra om listan stämmer
    INNAN något skrivs."""
    if not ider:
        return

    hittade = hamta_prospekt(cur, kalla, ider)

    print("\nProspekt att flytta över (--prospekt):")
    for id_sträng in ider:
        rad = hittade.get(id_sträng)
        if rad is None:
            print(f"  {id_sträng}: finns inte hos källan {kalla}, hoppar över.")
            continue

        cur.execute(
            "select count(*) from public.prospect_sources"
            " where tenant_id = %s and prospect_id = %s",
            (kalla, id_sträng),
        )
        antal_kallor = cur.fetchone()[0]

        nyckel = rad.get("foretagsnyckel")
        finns_i_malet = False
        if nyckel:
            cur.execute(
                "select 1 from public.prospects where tenant_id = %s and foretagsnyckel = %s",
                (mal, nyckel),
            )
            finns_i_malet = cur.fetchone() is not None

        print(
            f"  {rad['company_name']!r} (origin={rad['origin']}): "
            f"orgnr {rad['orgnr'] or 'saknas'}, e-post {rad['contact_email'] or 'saknas'}, "
            f"{antal_kallor} källrader."
        )

        atgard, detalj = avgor_atgard(rad, finns_i_malet=finns_i_malet)

        if atgard == "krock":
            print(
                f"    VARNAR: måltenanten har redan ett bolag med samma "
                f"företagsnyckel ({nyckel}). Hoppar över — annars kringgås "
                f"90 dagarskarensen i send-guardens regel 5."
            )
            continue
        if atgard == "valideringsfel":
            print(
                "    ÖVERHOPPAD (origin='example', klarar inte samma validering "
                f"som /befordra): {' '.join(detalj)}"
            )
            continue

        if not apply:
            continue

        värden = [rad[kolumn] for kolumn in PROSPEKT_KOLUMNER]
        platshållare = ", ".join(_platshallare(kolumn) for kolumn in PROSPEKT_KOLUMNER)
        cur.execute(
            f"""insert into public.prospects (tenant_id, origin, {", ".join(PROSPEKT_KOLUMNER)})
                values (%s, 'manual', {platshållare})
                returning id""",
            (mal, *värden),
        )
        ny_id = cur.fetchone()[0]
        cur.execute(
            """insert into public.prospect_sources
                 (tenant_id, prospect_id, source_url, source_type, lawful_basis, retrieved_at)
               select %s, %s, source_url, source_type, lawful_basis, retrieved_at
                 from public.prospect_sources
                where tenant_id = %s and prospect_id = %s""",
            (mal, ny_id, kalla, id_sträng),
        )

    # Fälla 3: uttalat, inte tyst. agent_runs har en FK mot prospect_id, och
    # nya id:n föräldralöser historiken oavsett — det är okej (historiken hör
    # till TESTET, inte till bolaget), men det ska stå här varje gång, inte
    # bara i skriptets docstring.
    print(
        "\nOBS: agent_runs (körningshistoriken) kopieras INTE. Det är "
        "testkörningens historik, inte prospektets — ett uttalat val."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fran", required=True, help="testtenantens slug (testkund-…)")
    ap.add_argument("--till", required=True, help="den riktiga kundens slug")
    ap.add_argument("--env", choices=("main", "development"), default="main")
    ap.add_argument("--apply", action="store_true")
    # Fas 3.4/3.5: demo -> riktigt konto. Opt-in-undantaget till att prospekt
    # normalt INTE kopieras — se docstringen ovan och kopiera_prospekt().
    ap.add_argument(
        "--prospekt",
        default="",
        help="kommaseparerad lista med prospekt-id ur KÄLLAN att kopiera som origin='manual'",
    )
    args = ap.parse_args()

    # Spärr 1 och 2: riktningen går inte att vända av misstag.
    riktning = kontrollera_riktning(args.fran, args.till)
    if riktning:
        sys.exit(f"AVBRYT: {riktning}")

    prospekt_ider = _parsa_id_lista(args.prospekt)

    env = env_read()
    conn = psycopg2.connect(dsn(env, args.env), connect_timeout=20)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            kalla = tenant_id(cur, args.fran)
            mal = tenant_id(cur, args.till)

            print(f"Miljö: {args.env}")
            print(f"Källa: {args.fran} ({kalla})")
            print(f"Mål:   {args.till} ({mal})\n")

            for tabell, kolumner in TABELLER:
                fran_antal = rakna(cur, tabell, kalla)
                till_antal = rakna(cur, tabell, mal)
                print(f"  {tabell:22} {till_antal:>4} rader i målet raderas → {fran_antal:>4} kopieras")

                if not args.apply:
                    continue

                cur.execute(f"delete from public.{tabell} where tenant_id = %s", (mal,))
                kol = ", ".join(kolumner)
                cur.execute(
                    f"""insert into public.{tabell} (tenant_id, {kol})
                        select %s, {kol} from public.{tabell} where tenant_id = %s""",
                    (mal, kalla),
                )

            kopiera_prospekt(cur, kalla, mal, prospekt_ider, apply=args.apply)

        if not args.apply:
            print("\nTorrkörning. Lägg till --apply för att skriva.")
            conn.rollback()
            return 0

        conn.commit()
        print("\nKlart. Målets konfiguration är nu identisk med testytans.")
        if prospekt_ider:
            print("Ärenden, mail och körningar kopierades INTE — det är historik.")
            print("Prospekten i --prospekt kopierades enligt listan ovan.")
        else:
            print("Ärenden, mail, prospekt och körningar kopierades INTE — det är historik.")
        return 0
    except Exception as fel:  # noqa: BLE001 — en halvskriven konfiguration är värre än ett fel
        conn.rollback()
        sys.exit(f"AVBRYT: {fel}")
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
