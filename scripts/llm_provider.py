#!/usr/bin/env python
"""Vilken LLM-provider varje Railway-miljö faktiskt kör — och bytet till OpenAI.

    python scripts/llm_provider.py                 # visa läget, ändra ingenting
    python scripts/llm_provider.py --apply         # byt till openai där det går

## Varför skriptet finns

Uppstartsspärren i `snajp-support/app/config.py` vägrar starta tjänsten med
DeepSeek i en miljö som bär eller speglar riktig kunddata. Spärren säger vad
som är fel men inte VAR — och svaret ligger i Railways variabler, en per
tjänst och miljö, alltså fyra ställen där tre kan vara rätt och ett fel.

Att läsa dem i dashboarden är fyra klickvägar och ett minnesprov.
Här är det ett kommando, och det går att köra om efter bytet för att se att
det tog.

## Läckagespärr

Nyckelvärden skrivs ALDRIG ut — bara namn och längd. `LLM_PROVIDER`,
`PUBLIC_BASE_URL` och `RAILWAY_ENVIRONMENT_NAME` är inte hemligheter och
skrivs i klartext. Regeln gäller även felutskrifter; se
scripts/railway_env_bootstrap.py.

## Varför --apply inte kan sätta nyckeln åt dig

En OpenAI-nyckel kräver ett konto och ett betalkort. Det är ett av undantagen
i CLAUDE.md som alltid kräver en människa. Skriptet kan bara VÄXLA providern,
och det vägrar göra det på en tjänst som inte redan har en `OPENAI_API_KEY` —
annars hade bytet startat tjänsten utan nyckel, och den hade gått ner i
simuleringsläge i stället för att larma. Ett tyst simuleringsläge i produktion
är värre än en tjänst som vägrar starta.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_env_bootstrap import service_vars  # noqa: E402
from railway_provision import (  # noqa: E402
    ENVIRONMENTS,
    envs_by_name,
    services_by_name,
    set_vars,
    state,
)

#: Tjänster som kör Python-backenden. Bara de läser LLM_PROVIDER — `web` är
#: Next-appen och `Postgres` är databasen.
BACKEND = ("api",)

#: Icke-hemliga värden som får skrivas i klartext.
OPPNA = ("LLM_PROVIDER", "PUBLIC_BASE_URL", "ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME")
HEMLIGA = ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GEMINI_API_KEY")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Sätt LLM_PROVIDER=openai där en OPENAI_API_KEY redan finns.",
    )
    args = parser.parse_args()

    projekt = state()
    envs = envs_by_name(projekt)
    svcs = services_by_name(projekt)

    att_atgarda: list[str] = []

    for miljo in ENVIRONMENTS:
        env_id = envs.get(miljo)
        if not env_id:
            print(f"\n{miljo}: miljön finns inte i projektet.")
            continue

        print(f"\n=== {miljo} ===")
        for tjanst in BACKEND:
            service = svcs.get(tjanst)
            if not service:
                print(f"  {tjanst}: tjänsten finns inte.")
                continue

            v = service_vars(service["id"], env_id)
            provider = v.get("LLM_PROVIDER", "(osatt — defaultar till openai)")
            har_openai = bool(v.get("OPENAI_API_KEY"))

            delar = [f"{k}={v[k]!r}" for k in OPPNA if k in v]
            delar += [f"{k}=<satt, {len(v[k])} tecken>" for k in HEMLIGA if v.get(k)]
            print(f"  {tjanst}: " + "; ".join(delar))

            if provider != "deepseek":
                continue

            if not har_openai:
                print(
                    f"    FEL: {miljo}/{tjanst} kör deepseek UTAN att ha en OPENAI_API_KEY.\n"
                    f"      Uppstartsspärren fäller varje deploy här tills nyckeln finns.\n"
                    f"      Lägg nyckeln i Railway först — skriptet byter inte provider\n"
                    f"      till en nyckel som inte finns."
                )
                att_atgarda.append(f"{miljo}/{tjanst}")
                continue

            if not args.apply:
                print(f"    -> skulle sätta LLM_PROVIDER=openai (kör med --apply)")
                att_atgarda.append(f"{miljo}/{tjanst}")
                continue

            set_vars(service["id"], env_id, {"LLM_PROVIDER": "openai"})
            print(f"    OK: LLM_PROVIDER=openai satt. Deploya om tjänsten för att den ska gälla.")

    if att_atgarda and not args.apply:
        print("\nKvar att åtgärda: " + ", ".join(att_atgarda))
    elif not att_atgarda:
        print("\nInget kör deepseek. Uppstartsspärren är nöjd.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
