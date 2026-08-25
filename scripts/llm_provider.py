#!/usr/bin/env python
"""Vilken LLM-provider varje Railway-miljö faktiskt kör — och bytet till OpenAI.

    python scripts/llm_provider.py                        # visa läget, ändra ingenting
    python scripts/llm_provider.py --env development      # bara en miljö
    python scripts/llm_provider.py --satt gemini --apply  # byt provider OCH modell
    python scripts/llm_provider.py --env main --pausa --apply  # till simuleringsläge

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

#: Vad `--pausa` sätter. En KÄND provider utan nyckel ger simuleringsläge:
#: agenten svarar med den deterministiska regelmotorn i stället för med AI,
#: och ingenting skickas till någon leverantör.
#:
#: `openai` och `gpt-4o-mini` är valda för att de hör ihop — uppstartsspärren
#: fäller ett modellnamn som tillhör en annan provider än den konfigurerade,
#: så det räcker inte att byta det ena.
#:
#: GEMINI_API_KEY LÄMNAS ORÖRD med flit: den driver även embeddings och
#: bildbeskrivning, som inte är chattanrop och inte omfattas av samma
#: dygnskvot. Att blanka den hade tagit ner KB-sökningen på köpet.
PAUSLAGE = {"LLM_PROVIDER": "openai", "MODEL": "gpt-4o-mini"}

#: Provider -> modellen vi kör som standard. Speglar `_default_model_for_provider`
#: i config.py. Gemini-namnet är detsamma som vision-sidovagnen redan använder
#: mot samma endpoint, alltså ett namn som är prövat i den här kodbasen.
STANDARDMODELL = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-v4-flash",
    "gemini": "gemini-3.6-flash",
}

#: Entydiga modellprefix -> provider. Speglar MODELLFAMILJER i config.py.
MODELLFAMILJER = {
    "gpt-": "openai",
    "o1-": "openai",
    "o3-": "openai",
    "o4-": "openai",
    "deepseek": "deepseek",
    "gemini": "gemini",
}


def provider_for_model(model: str) -> str | None:
    namn = (model or "").strip().lower()
    for prefix, provider in MODELLFAMILJER.items():
        if namn.startswith(prefix):
            return provider
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        choices=sorted(ENVIRONMENTS),
        help="Bara den här miljön. Utan flaggan gås alla igenom.",
    )
    parser.add_argument(
        "--satt",
        choices=sorted(NYCKEL_FOR),
        help="Providern att växla till. Sätter även MODEL. Utan den bara diagnos.",
    )
    parser.add_argument(
        "--pausa",
        action="store_true",
        help=(
            "Sätt miljön i SIMULERINGSLÄGE: agenten svarar med regelmotorn och "
            "ingenting skickas till någon leverantör. Används när providern inte "
            "får eller inte kan ta emot trafik."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Genomför bytet. Utan flaggan visas bara vad som skulle hända.",
    )
    args = parser.parse_args()

    if args.pausa and args.satt:
        sys.exit("AVBRYTER: --pausa och --satt gör olika saker. Välj en.")

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
        if args.env and miljo != args.env:
            continue
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

            # Diagnos 3: hör modellnamnet till providern? Det här är felet som
            # gav 404 på VARJE anrop medan hälsokontrollen sa "live" — en
            # nyckel fanns, men modellen fanns inte hos den leverantören.
            modell = v.get("MODEL", "")
            modellens = provider_for_model(modell)
            if modell and modellens and modellens != provider:
                print(
                    f"    FEL: MODEL={modell!r} är en {modellens}-modell men providern "
                    f"är {provider}.\n"
                    f"      Varje anrop svarar 404 medan hälsokontrollen rapporterar 'live'."
                )
                att_atgarda.append(f"{miljo}/{tjanst}")

            # Modellen räknas som en del av bytet: en provider utan en modell
            # den känner till är inte ett halvfärdigt byte, det är ett trasigt.
            behover_modell = bool(modell) and provider_for_model(modell) != args.satt
            if args.pausa:
                if not args.apply:
                    print(
                        "    -> skulle sätta "
                        + ", ".join(f"{k}={v2}" for k, v2 in PAUSLAGE.items())
                        + " => SIMULERINGSLÄGE (kör med --apply)"
                    )
                    att_atgarda.append(f"{miljo}/{tjanst}")
                    continue
                set_vars(service["id"], env_id, dict(PAUSLAGE))
                print(
                    f"    OK: {miljo}/{tjanst} pausad. Agenten svarar med regelmotorn,\n"
                    f"      ingenting går till någon leverantör. Ångra med\n"
                    f"      --satt <provider> --apply när nyckeln är på plats."
                )
                continue

            if not args.satt or (provider == args.satt and not behover_modell):
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

            nya = {"LLM_PROVIDER": args.satt, "MODEL": STANDARDMODELL[args.satt]}

            if not args.apply:
                print(
                    "    -> skulle sätta "
                    + ", ".join(f"{k}={v2}" for k, v2 in nya.items())
                    + " (kör med --apply)"
                )
                att_atgarda.append(f"{miljo}/{tjanst}")
                continue

            set_vars(service["id"], env_id, nya)
            print(f"    OK: {miljo}/{tjanst} satt till {args.satt}. Deploya om tjänsten.")

    if att_atgarda:
        print("\nKvar att åtgärda: " + ", ".join(sorted(set(att_atgarda))))
    else:
        print("\nVarje tjänst kör en känd provider med rätt nyckel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
