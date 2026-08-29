#!/usr/bin/env python3
"""Kontrollera vilken region Railways tjänster kör i — EU/EES eller inte.

    python scripts/railway_region.py                 # alla miljöer
    python scripts/railway_region.py --env development

## Varför det här skriptet finns

Samma fråga som `redis_kontroll.py` ställer om jobbkön, fast om själva
appservrarna: **ligger de i EU/EES?** Två skäl, och båda är juridiska snarare
än tekniska:

1. **Kunddata i drift.** Railway-miljön `development` är en spegel av
   produktionen (CLAUDE.md) — riktiga kunders ärenden och mejladresser ligger
   i den databasen och passerar de containrarna. En tjänst i `us-west1` är en
   tredjelandsöverföring, samma resonemang som stängde av DeepSeek.

2. **Skatteverkets API.** De allmänna villkoren för Beskattningsengagemang
   (§5) kräver uttryckligen att uppgifterna tas emot i "en teknisk miljö som
   fysiskt befinner sig inom EU- eller EES-området". Kör `api` utanför EU går
   den integrationen inte att teckna avtal för — oavsett hur färdig koden är.
   Se `app/leads/skatteverket.py` och DEPLOY.md:s Skatteverket-avsnitt.

## Skriptet gissar aldrig

Saknar Railways svar regionfältet skrivs "okänd" ut och det räknas som
OVERIFIERAT, inte som EU. Exit 1 vid varje tjänst som inte bevisligen ligger i
EU — det ska synas som ett fel i terminalen, inte som en rad bland andra i en
logg. Samma hållning som redis_kontroll.py: en gissning i fel riktning är
värre än ett hål i rapporten.

Enbart LÄSANDE mot Railways API. Skriptet ändrar ingenting, och token läses ur
.env.deploy och skrivs aldrig ut (läckagespärren i CLAUDE.md).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway import gql  # noqa: E402  (efter sys.path — samma klient, en token-väg)

#: Railway-projektet `brave-passion`. Samma id som i DEPLOY.md.
PROJECT_ID = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"

FRAGA = """
query($id: String!) {
  project(id: $id) {
    name
    environments { edges { node { id name } } }
    services { edges { node { name
      serviceInstances { edges { node { environmentId region } } }
    } } }
  }
}
"""


def _ar_eu_region(region: str) -> bool:
    """Railway namnger EU-regioner `europe-west4` (Amsterdam) m.fl.

    Samma prefixtest som redis_kontroll._är_eu_region, med flit: tom sträng
    och "okänd" faller igenom som False, alltså overifierat.
    """
    return region.lower().startswith(("eu", "europe"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="", help="Bara den här miljön (t.ex. development).")
    args = parser.parse_args()

    projekt = gql(FRAGA, {"id": PROJECT_ID})["project"]

    miljoer = {
        kant["node"]["id"]: kant["node"]["name"]
        for kant in projekt["environments"]["edges"]
    }

    print(f"Railway — region per tjänst (projekt {projekt['name']})\n")

    avvikande: list[str] = []
    hittade = False

    for kant in projekt["services"]["edges"]:
        tjanst = kant["node"]
        for instans_kant in tjanst["serviceInstances"]["edges"]:
            instans = instans_kant["node"]
            miljo = miljoer.get(instans["environmentId"], "okänd miljö")
            if args.env and miljo != args.env:
                continue
            hittade = True

            # Tomt/saknat fält blir "okänd" och räknas som overifierat —
            # aldrig som EU. Se docstringen.
            region = instans.get("region") or "okänd"
            markor = "EU" if _ar_eu_region(region) else "UTANFÖR EU / OVERIFIERAD"
            print(f"  [{miljo}] {tjanst['name']:<10} region: {region:<20} {markor}")

            if not _ar_eu_region(region):
                avvikande.append(f"[{miljo}] {tjanst['name']}: region={region!r}")

    if not hittade:
        print(f"  Inga tjänster i miljön {args.env!r} — kontrollera namnet.")
        sys.exit(1)

    if avvikande:
        print("\nFEL: följande tjänster ligger UTANFÖR EU (eller har en overifierad region):")
        for rad in avvikande:
            print(f"  - {rad}")
        print(
            "\nTvå följder, båda juridiska:\n"
            "  * development speglar produktionen — riktig kunddata utanför EU kräver\n"
            "    samma SCC-bedömning som DeepSeek-spärren i CLAUDE.md.\n"
            "  * Skatteverkets API (§5 i de allmänna villkoren) kräver att uppgifterna\n"
            "    tas emot inom EU/EES. Integrationen går inte att teckna avtal för\n"
            "    förrän tjänsten ligger rätt."
        )
        sys.exit(1)

    print("\nAlla kontrollerade tjänster ligger i EU.")


if __name__ == "__main__":
    main()
