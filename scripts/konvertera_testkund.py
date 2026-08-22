#!/usr/bin/env python3
"""Testkund → riktig kund: profilen ÖVERSKRIVS, den sammanfogas inte.

    python scripts/konvertera_testkund.py --fran testkund-a1b2c3d4 --till livrustning
    python scripts/konvertera_testkund.py --fran testkund-a1b2c3d4 --till livrustning --apply
    python scripts/konvertera_testkund.py --env development --fran ... --till ...

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

Det som INTE kopieras: ärenden, mail, prospekt, körningar och beslutslogg. Det
är testkundens historik, inte deras konfiguration — och en riktig kunds första
dag ska inte börja med sex påhittade ärenden i inkorgen.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway_provision import env_read  # noqa: E402
from railway_migrate import dsn  # noqa: E402

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fran", required=True, help="testtenantens slug (testkund-…)")
    ap.add_argument("--till", required=True, help="den riktiga kundens slug")
    ap.add_argument("--env", choices=("main", "development"), default="main")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    # Spärr 1 och 2: riktningen går inte att vända av misstag.
    if not args.fran.startswith("testkund-"):
        sys.exit(f"AVBRYT: källan {args.fran!r} är inte en testtenant. Riktningen är envägs.")
    if args.till.startswith("testkund-"):
        sys.exit(f"AVBRYT: målet {args.till!r} är en testtenant. Riktningen är envägs.")

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

        if not args.apply:
            print("\nTorrkörning. Lägg till --apply för att skriva.")
            conn.rollback()
            return 0

        conn.commit()
        print("\nKlart. Målets konfiguration är nu identisk med testytans.")
        print("Ärenden, mail, prospekt och körningar kopierades INTE — det är historik.")
        return 0
    except Exception as fel:  # noqa: BLE001 — en halvskriven konfiguration är värre än ett fel
        conn.rollback()
        sys.exit(f"AVBRYT: {fel}")
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
