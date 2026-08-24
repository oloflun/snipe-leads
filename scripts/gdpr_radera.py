#!/usr/bin/env python
"""Rättighetsflödet: hitta och radera allt om EN person.

    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --export
    python scripts/gdpr_radera.py --env railway-main --epost anna@exempel.se --radera

## Varför ett skript och inte en instruktion i ett dokument

Artikel 15 (tillgång) och artikel 17 (radering) har en tidsfrist på en månad.
En punktlista som säger "sök i ss_emails, sedan i contacts, sedan i..." kommer
att köras fel den dag det brådskar, och den som kör den kan inte i efterhand
visa vad som gjordes. Ett skript går att köra om, verifiera och falsifiera —
samma princip som redan gäller i CLAUDE.md.

## Tre lägen, i den ordning man använder dem

1. Utan flagga: SÖK. Visar var adressen förekommer, per tabell och kund.
   Det här är också svaret på en tillgångsbegäran i första ledet.
2. `--export`: skriver ut allt som finns om personen som JSON. Det är den
   handling som lämnas ut vid en begäran om registerutdrag.
3. `--radera`: raderar. Kräver att man skrivit adressen en gång till, för
   hand — se `_bekrafta`.

## Vad som INTE raderas, och varför

En rad i `suppressions` är kvar. Den innehåller adressen, men den finns just
för att adressen ALDRIG ska kontaktas igen — raderar man den försvinner
skyddet, och nästa körning kallmejlar samma person. Det är den ena
undantagssituation där ett berättigat intresse väger tyngre än radering, och
den ska kunna förklaras för den som frågar. Skriptet säger det uttryckligen i
utskriften i stället för att tiga om det.
"""

from __future__ import annotations

import argparse
import json
import sys

import psycopg2

from gdpr_verktyg import dsn_for

#: Var en e-postadress kan förekomma. Kolumnnamnet är inte samma överallt,
#: därför en explicit karta i stället för en gissning.
#:
#: LISTAN MÅSTE VÄXA MED SCHEMAT. Läggs en tabell till som bär en
#: mejladress och den inte står här, så raderar det här skriptet inte allt —
#: och rapporterar ändå "klart". Se docs/registerforteckning.md, som ska hållas
#: i synk med den här listan.
TABELLER = [
    ("ss_emails", "from_email", "Inkommande kundmejl (bilagor, klassificeringar och utkast följer med i kaskaden)."),
    ("contacts", "email", "Kontaktperson i leads-databasen."),
    ("outreach_threads", "prospect_email", "Utgående mejltråd."),
    ("ss_avregistreringslankar", "email", "Avregistreringslänk."),
]

#: Raderas ALDRIG. Se docstringen.
BEHALLS = [("suppressions", "email", "Spärrlistan — raderas den kontaktas personen igen.")]


def _sok(cur, epost: str) -> dict[str, int]:
    fynd: dict[str, int] = {}
    for tabell, kolumn, _ in TABELLER + BEHALLS:
        try:
            cur.execute(
                f"select count(*) from {tabell} where lower({kolumn}) = lower(%s)", (epost,)
            )
            fynd[tabell] = cur.fetchone()[0]
        except psycopg2.Error:
            # En tabell som inte finns i den här miljön är inte ett fel — men
            # den ska synas som okänd och inte som noll. Skillnaden mellan
            # "inget hittat" och "kunde inte titta" är hela svaret.
            cur.connection.rollback()
            fynd[tabell] = -1
    return fynd


def _export(cur, epost: str) -> dict:
    ut: dict[str, list] = {}
    for tabell, kolumn, _ in TABELLER + BEHALLS:
        try:
            cur.execute(
                f"select to_jsonb(t) from {tabell} t where lower(t.{kolumn}) = lower(%s)",
                (epost,),
            )
            ut[tabell] = [rad[0] for rad in cur.fetchall()]
        except psycopg2.Error:
            cur.connection.rollback()
    return ut


def _bekrafta(epost: str) -> None:
    """Adressen skrivs en gång till, för hand.

    Inte en `--force`-flagga: en flagga sitter kvar i shell-historiken och
    körs om av misstag. Att skriva adressen igen tvingar fram att man tittar
    på VILKEN adress som raderas, vilket är det enda felet som inte går att
    ångra här."""
    svar = input(f"Skriv adressen igen för att bekräfta radering ({epost}): ").strip()
    if svar.lower() != epost.lower():
        sys.exit("AVBRYTER: adresserna stämmer inte överens. Ingenting raderades.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True)
    parser.add_argument("--epost", required=True)
    parser.add_argument("--export", action="store_true", help="Skriv ut allt som JSON.")
    parser.add_argument("--radera", action="store_true", help="Radera. Kräver bekräftelse.")
    args = parser.parse_args()

    with psycopg2.connect(dsn_for(args.env)) as conn, conn.cursor() as cur:
        fynd = _sok(cur, args.epost)

        print(f"\n{args.epost} i miljön {args.env}:\n")
        for tabell, _, beskrivning in TABELLER + BEHALLS:
            antal = fynd.get(tabell, -1)
            markering = "okänd tabell" if antal < 0 else f"{antal} rader"
            print(f"  {tabell:<28} {markering:<16} {beskrivning}")

        if args.export:
            print("\n--- REGISTERUTDRAG (JSON) ---")
            print(json.dumps(_export(cur, args.epost), indent=2, ensure_ascii=False, default=str))

        if not args.radera:
            print("\nIngenting raderades. Lägg till --radera för att göra det.")
            return 0

        _bekrafta(args.epost)

        totalt = 0
        for tabell, kolumn, _ in TABELLER:
            if fynd.get(tabell, -1) <= 0:
                continue
            cur.execute(f"delete from {tabell} where lower({kolumn}) = lower(%s)", (args.epost,))
            print(f"  {tabell}: raderade {cur.rowcount} rader")
            totalt += cur.rowcount

        print(f"\nKlart. {totalt} rader raderade.")
        print(
            "Kvar med flit: raden i suppressions. Den bär adressen, men den är "
            "skyddet mot att personen kontaktas igen — raderas den försvinner "
            "skyddet. Det ska stå i svaret till den registrerade."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
