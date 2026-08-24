#!/usr/bin/env python
"""Vilken LLM-provider varje Railway-miljö faktiskt kör — och bytet till OpenAI.

    python scripts/llm_provider.py                       # visa läget, ändra ingenting
    python scripts/llm_provider.py --satt gemini --apply  # byt provider

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

En API-nyckel kräver ett konto och ofta ett betalkort. Det är ett av undantagen
i CLAUDE.md som alltid kräver en människa. Skriptet kan bara VÄXLA providern,
och det vägrar göra det på en tjänst som inte redan har providerns nyckel —
annars hade bytet startat tjänsten utan nyckel, och den hade gått ner i
simuleringsläge i stället för att larma.

## Varför nyckelkontrollen är per PROVIDER och inte bara "finns någon nyckel"

Skriptet skrevs först med `openai` inbakat, och missade därför exakt det fel
det fanns för att fånga: 2026-08-24 sattes LLM_PROVIDER till "gemini" för hand,
ett värde koden då inte kände till, och development gick ner i simuleringsläge
utan att något larmade. Kartan nedan binder ihop provider och nyckelnamn så att
frågan "har den här tjänsten rätt nyckel för det den ska köra?" går att ställa
maskinellt.
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

#: Provider -> vilken nyckel den kräver. MÅSTE spegla `Settings.active_llm_key`
#: och `KANDA_PROVIDERS` i snajp-support/app/config.py. Glider de isär börjar
#: skriptet godkänna en konfiguration som tjänsten sedan vägrar starta med.
NYCKEL_FOR = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

#: Providers som inte får ta emot kunddata. Speglar spärren i config.py.
FORBJUDNA_MOT_KUNDDATA = ("deepseek",)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--satt",
        choices=sorted(NYCKEL_FOR),
        help="Providern att växla till. Utan den bara diagnos.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Genomför bytet. Utan flaggan visas bara vad som skulle hända.",
    )
    args = parser.parse_args()

    if args.satt in FORBJUDNA_MOT_KUNDDATA:
        sys.exit(
            f"AVBRYTER: {args.satt} får inte behandla kunddata. Se CLAUDE.md, "
            f"avsnittet om dataskydd — det är ett avtalsbeslut, inte ett kodbeslut."
        )

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
            provider = v.get("LLM_PROVIDER") or "openai"  # osatt => kodens default

            delar = [f"{k}={v[k]!r}" for k in OPPNA if k in v]
            delar += [f"{k}=<satt, {len(v[k])} tecken>" for k in HEMLIGA if v.get(k)]
            print(f"  {tjanst}: " + "; ".join(delar))

            # Diagnos 1: är providern över huvud taget känd av koden?
            if provider not in NYCKEL_FOR:
                print(
                    f"    FEL: LLM_PROVIDER={provider!r} är inget koden känner till.\n"
                    f"      Tjänsten vägrar starta. Välj: {', '.join(sorted(NYCKEL_FOR))}."
                )
                att_atgarda.append(f"{miljo}/{tjanst}")

            # Diagnos 2: har den nyckeln för det den påstår sig köra? Det här är
            # frågan som inte ställdes 2026-08-24, och svaret var nej.
            elif not v.get(NYCKEL_FOR[provider]):
                print(
                    f"    FEL: kör {provider} men {NYCKEL_FOR[provider]} saknas.\n"
                    f"      Tjänsten startar i SIMULERINGSLÄGE — den svarar kunder med\n"
                    f"      regelmotorn i stället för med agenten, och ingenting larmar."
                )
                att_atgarda.append(f"{miljo}/{tjanst}")

            elif provider in FORBJUDNA_MOT_KUNDDATA:
                print(f"    FEL: {provider} får inte behandla kunddata. Uppstartsspärren fäller.")
                att_atgarda.append(f"{miljo}/{tjanst}")

            if not args.satt or provider == args.satt:
                continue

            # Bytet. Nyckeln för MÅLprovidern måste redan finnas — annars byter
            # vi bara ett fel mot ett tystare.
            if not v.get(NYCKEL_FOR[args.satt]):
                print(
                    f"    VÄGRAR byta till {args.satt}: {NYCKEL_FOR[args.satt]} saknas på\n"
                    f"      {miljo}/{tjanst}. Lägg nyckeln i Railway först."
                )
                att_atgarda.append(f"{miljo}/{tjanst}")
                continue

            if not args.apply:
                print(f"    -> skulle sätta LLM_PROVIDER={args.satt} (kör med --apply)")
                att_atgarda.append(f"{miljo}/{tjanst}")
                continue

            set_vars(service["id"], env_id, {"LLM_PROVIDER": args.satt})
            print(f"    OK: LLM_PROVIDER={args.satt} satt. Deploya om tjänsten.")

    if att_atgarda:
        print("\nKvar att åtgärda: " + ", ".join(sorted(set(att_atgarda))))
    else:
        print("\nVarje tjänst kör en känd provider med rätt nyckel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
