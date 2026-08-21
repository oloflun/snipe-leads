#!/usr/bin/env python3
"""Räknar vektorer för kunskapsbasartiklar som saknar dem.

    python scripts/fyll_embeddings.py --env development
    python scripts/fyll_embeddings.py --env development --apply

## Varför den behövs

Embeddings har ALDRIG lyckats i den här kodbasen: Gemini-API:t var inte
aktiverat på Google-projektet, så varje anrop svarade 403 och `embed_text`
returnerade None. Följden är att kolumnen `ss_knowledge_base.embedding` står
tom för varenda artikel — 159 av 159 i development — och att `search_kb`
faller tillbaka på svensk fulltext för alla.

Nyckeln är utbytt och nya artiklar får sin vektor vid skrivning. Men de gamla
får den aldrig: ingen kodväg räknar om en artikel som redan finns. Utan det här
skriptet är semantisk sökning påslagen bara för det som skrivs härnäst, vilket
är den sämsta av tre möjliga situationer — den ser ut att fungera.

## Varför den skriver direkt i databasen

`POST /api/kb` skapar en NY artikel. Det finns ingen endpoint som uppdaterar en
befintlig, och att lägga till en vore att bygga en skrivväg för en engångsjobb.
Uppdateringen rör exakt en kolumn, och den kolumnen är härledd data — ingen
kunds text ändras.

## Takten

Gemini gratisnivå har ett minuttak. Artiklarna körs därför en i taget med en
kort paus, och ett 429 möts med väntan och nytt försök i stället för att fälla
körningen halvvägs. En halvfylld kunskapsbas är svårare att felsöka än en tom:
sökningen blir bra för hälften av frågorna.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "snajp-support"))

import psycopg2  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

PAUS_SEKUNDER = 0.6
MAX_FORSOK = 4


async def _vektor(text: str):
    """Anropar samma väg som produkten. Ingen egen klient, ingen egen modell."""
    from app.agent.embeddings import embed_text

    return await embed_text(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="0 = alla")
    args = ap.parse_args()

    env = env_read()

    # Nyckeln kommer ur backendens .env, som är där produkten läser den.
    # Skriptet sätter den aldrig och skriver aldrig ut den.
    from app.config import get_settings

    settings = get_settings()
    if not (settings.gemini_api_key or settings.embedding_api_key):
        sys.exit(
            "GEMINI_API_KEY saknas i snajp-support/.env — utan den finns ingen "
            "klient, och embed_text returnerar None för varje artikel."
        )

    conn = psycopg2.connect(dsn(env, args.env), connect_timeout=20)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """select id, title, content from public.ss_knowledge_base
                    where embedding is null order by created_at"""
                + (f" limit {int(args.limit)}" if args.limit else "")
            )
            rader = cur.fetchall()

            print(f"miljö: {args.env} · {len(rader)} artiklar utan vektor")
            if not args.apply:
                for _id, titel, _ in rader[:10]:
                    print(f"  × {titel[:60]}")
                if len(rader) > 10:
                    print(f"  … och {len(rader) - 10} till")
                print("\nTorrkörning. Kör om med --apply.")
                return 0

            klara, misslyckade = 0, []
            for _id, titel, innehall in rader:
                vektor = None
                for forsok in range(MAX_FORSOK):
                    vektor = asyncio.run(_vektor(f"{titel}\n{innehall}"))
                    if vektor is not None:
                        break
                    # embed_text sväljer felet med flit (en artikel utan vektor
                    # är bättre än ett avbrutet sparande). Här är det däremot
                    # HELA jobbet, så vi väntar och försöker igen.
                    time.sleep(2 ** forsok)

                if vektor is None:
                    misslyckade.append(titel)
                    print(f"  !  {titel[:56]}")
                    continue

                cur.execute(
                    "update public.ss_knowledge_base set embedding = %s::vector where id = %s",
                    (str(vektor), _id),
                )
                klara += 1
                if klara % 10 == 0:
                    conn.commit()
                    print(f"  … {klara} av {len(rader)}")
                time.sleep(PAUS_SEKUNDER)

        conn.commit()
        print(f"\nKlart: {klara} vektorer skrivna, {len(misslyckade)} misslyckade.")
        if misslyckade:
            print("Kör om skriptet — det tar bara de som fortfarande saknar vektor.")
        return 0 if not misslyckade else 1
    except Exception as fel:  # noqa: BLE001
        conn.rollback()
        sys.exit(f"AVBRYT: {fel}")
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
