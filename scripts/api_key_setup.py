#!/usr/bin/env python3
"""Lägg in en API-nyckel ur .env.deploy på rätt Railway-miljöer — och mät
FÖRST att den duger.

    python scripts/api_key_setup.py                      # torrkörning, visar läget
    python scripts/api_key_setup.py --apply              # skriver till Railway
    python scripts/api_key_setup.py --apply --env main   # bara en miljö
    python scripts/api_key_setup.py --namn OPENAI_API_KEY --apply

Nyckeln läses ur `.env.deploy` (gitignorerad) och skrivs ALDRIG ut — varken i
terminalen, i loggen eller i ett felmeddelande. Bara längd och en kort sha256
visas, vilket räcker för att se om två miljöer råkar dela nyckel.

Rader att fylla i (skriptet skapar dem tomma om de saknas):

    RAILWAY_DEVELOPMENT_GEMINI_API_KEY=
    RAILWAY_MAIN_GEMINI_API_KEY=

## Varför skriptet finns

`railway_llm_provider.py` gör en angränsande sak: byter provider och läser
nyckeln med getpass. Det här skriptet finns för det andra fallet — nyckeln
kommer klistrad ur en konsol och ska in i en fil, inte skrivas i en prompt —
och för två kontroller den saknar, som båda kostat tid i det här projektet:

  * **Kvotnivån.** En Gemini-nyckel som svarar 200 på ett modelluppslag kan
    ändå ligga på FRITT tier. Uppmätt 2026-08-29: `gemini-3.6-flash` ger då
    5 requests/minut, och en chatt gör 6 LLM-anrop i snitt (5–7, n=8 riktiga
    körningar). En sådan nyckel är alltså trasig i drift men ser hel ut i
    varje hälsokontroll — tjänsten svarar `mode: live` och kunden får
    "Svaret gick inte att ta fram den här gången." Skriptet skickar därför
    en skarp liten skur och läser Googles egen kvotmätare: nämner den
    `free_tier` vägrar skriptet utan `--tillat-fri-kvot`.

  * **Delad nyckel mellan miljöer.** `GEMINI_API_KEY` står i
    `PER_ENV_SECRETS` i `railway_provision.py` sedan 2026-08-24, med
    motiveringen att en delad nyckel är en delad KVOT: ett demo-anrop i
    development slog i taket och nästa anrop i produktionen fick samma 429.
    Uppmätt 2026-08-30: miljöerna delade nyckel igen. Skriptet jämför de två
    värdena och vägrar utan `--tillat-delad`.

Ingenting skrivs förrän båda kontrollerna passerat för ALLA valda miljöer.
En dålig nyckel ska falla i din terminal, inte i produktionen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from railway import REPO_ROOT, gql

PROJECT_ID = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"
API_SERVICE_ID = "5828c279-ad8f-429b-b5e1-969372db8a0a"
ENV_DEPLOY = REPO_ROOT / ".env.deploy"

#: Miljönamn -> Railway-miljöns id. Samma två som resten av skripten känner.
MILJOER = {
    "development": "02c39616-1b8e-47b7-beea-d8c6cfba1acd",
    "main": "47bc7047-a458-404b-a1de-ccec612cb96e",
}

#: Nyckelnamn -> (bas-URL, standardmodell). Speglar PROVIDERS i
#: railway_llm_provider.py, som i sin tur speglar app/agent/llm.py.
NYCKLAR = {
    "GEMINI_API_KEY": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.6-flash"),
    "OPENAI_API_KEY": ("https://api.openai.com/v1", "gpt-4o-mini"),
}

#: Värden som betyder "inte ifylld". En platshållare som tyst skrivs till
#: Railway är värre än en tom rad: tjänsten startar och svarar `live`.
PLATSHALLARE = {"", "andra-mig", "change_me", "din-nyckel", "sk-...", "xxx", "TODO"}

#: Så många snabba anrop kvotprovet skickar. Fritt tier för gemini-flash
#: ligger på 5/minut, så sex räcker för att skilja fritt från betalt utan att
#: kosta något att tala om.
PROV_ANTAL = 6


def fingeravtryck(varde: str) -> str:
    """Allt vi någonsin visar av en nyckel."""
    return f"len={len(varde)} sha={hashlib.sha256(varde.encode()).hexdigest()[:10]}"


def las_env_deploy() -> dict[str, str]:
    if not ENV_DEPLOY.exists():
        sys.exit(f"AVBRYTER: {ENV_DEPLOY} finns inte.")
    ut: dict[str, str] = {}
    for rad in ENV_DEPLOY.read_text(encoding="utf-8").splitlines():
        if "=" in rad and not rad.lstrip().startswith("#"):
            nyckel, _, varde = rad.partition("=")
            ut[nyckel.strip()] = varde.strip()
    return ut


def sakerstall_rader(namn: str, miljoer: list[str]) -> list[str]:
    """Skapar tomma rader i .env.deploy för de miljöer som saknar dem.

    Att skriva raden åt användaren är hela poängen: annars är första svaret
    på "var lägger jag nyckeln?" en instruktion i stället för en fil att
    klistra in i.
    """
    text = ENV_DEPLOY.read_text(encoding="utf-8")
    tillagda = []
    for miljo in miljoer:
        radnamn = f"RAILWAY_{miljo.upper()}_{namn}"
        if f"{radnamn}=" not in text:
            if not text.endswith("\n"):
                text += "\n"
            text += f"{radnamn}=\n"
            tillagda.append(radnamn)
    if tillagda:
        ENV_DEPLOY.write_text(text, encoding="utf-8")
    return tillagda


def railway_variabler(env_id: str) -> dict[str, str]:
    return gql(
        "query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }",
        {"p": PROJECT_ID, "e": env_id, "s": API_SERVICE_ID},
    )["variables"]


def satt_variabel(env_id: str, namn: str, varde: str) -> None:
    gql(
        "mutation($in: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $in) }",
        {
            "in": {
                "projectId": PROJECT_ID,
                "environmentId": env_id,
                "serviceId": API_SERVICE_ID,
                "variables": {namn: varde},
                # replace:false — vi rör EN variabel, inte hela uppsättningen.
                "replace": False,
            }
        },
    )


def verifiera_nyckel(bas_url: str, nyckel: str, model: str) -> str | None:
    """Nyckeln OCH modellen mot leverantörens API. Returnerar felsträng eller None."""
    req = urllib.request.Request(
        f"{bas_url}/models/{model}", headers={"Authorization": f"Bearer {nyckel}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as svar:
            json.load(svar)
        return None
    except urllib.error.HTTPError as fel:
        if fel.code in (401, 403):
            return "leverantören avvisade nyckeln (401/403)"
        if fel.code == 404:
            return f"modellen {model!r} finns inte för den här nyckeln (404)"
        return f"uppslaget av modellen svarade {fel.code}"
    except urllib.error.URLError as fel:
        return f"kunde inte nå {bas_url} ({fel.reason})"


def kvotprov(bas_url: str, nyckel: str, model: str) -> tuple[str, str]:
    """Skarp skur mot modellen. Returnerar (niva, beskrivning).

    niva är en av: "betald", "fri", "slut", "okand".

    Vi läser Googles egen kvotmätare i 429-kroppen i stället för att gissa ur
    antalet svar. Nämner den `free_tier` är det ett besked från leverantören,
    inte en slutsats av oss.
    """
    ok = 0
    fri = False
    kvotfel = 0
    for _ in range(PROV_ANTAL):
        kropp = json.dumps(
            {
                "model": model,
                "max_tokens": 4,
                "messages": [{"role": "user", "content": "Svara med ordet ok."}],
            }
        ).encode()
        req = urllib.request.Request(
            f"{bas_url}/chat/completions",
            data=kropp,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {nyckel}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as svar:
                svar.read()
                ok += 1
        except urllib.error.HTTPError as fel:
            text = fel.read().decode("utf-8", "replace")
            if fel.code == 429:
                kvotfel += 1
                if "free_tier" in text or "FreeTier" in text:
                    fri = True
            else:
                return "okand", f"{fel.code} från modellanropet"
        except urllib.error.URLError as fel:
            return "okand", f"kunde inte nå {bas_url} ({fel.reason})"
        time.sleep(0.2)

    if fri and ok == 0:
        return "slut", f"{kvotfel}/{PROV_ANTAL} avvisade, kvotmätaren säger FRITT tier och inget kom igenom"
    if fri:
        return "fri", f"{ok}/{PROV_ANTAL} kom igenom, kvotmätaren säger FRITT tier"
    if ok == PROV_ANTAL:
        return "betald", f"{PROV_ANTAL}/{PROV_ANTAL} kom igenom utan kvotfel"
    if kvotfel:
        return "okand", f"{ok}/{PROV_ANTAL} kom igenom, {kvotfel} kvotfel utan tier-uppgift"
    return "okand", f"{ok}/{PROV_ANTAL} kom igenom"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--namn", default="GEMINI_API_KEY", choices=sorted(NYCKLAR),
                   help="vilken nyckel som sätts (default: GEMINI_API_KEY)")
    p.add_argument("--env", choices=sorted(MILJOER) + ["alla"], default="alla")
    p.add_argument("--apply", action="store_true", help="skriv till Railway (annars torrkörning)")
    p.add_argument("--tillat-fri-kvot", action="store_true",
                   help="skriv nyckeln även om provet säger fritt tier")
    p.add_argument("--tillat-delad", action="store_true",
                   help="skriv även om miljöerna får samma nyckel")
    p.add_argument("--hoppa-prov", action="store_true", help="hoppa över kvotprovet")
    args = p.parse_args()

    bas_url, standardmodell = NYCKLAR[args.namn]
    miljoer = sorted(MILJOER) if args.env == "alla" else [args.env]

    tillagda = sakerstall_rader(args.namn, sorted(MILJOER))
    if tillagda:
        print(f"Lade till tomma rader i .env.deploy: {', '.join(tillagda)}")
        print("Fyll i dem och kör om.\n")

    env = las_env_deploy()

    # --- Fas 1: samla in och kontrollera. Ingenting skrivs här. -------------
    kandidater: dict[str, str] = {}
    for miljo in miljoer:
        radnamn = f"RAILWAY_{miljo.upper()}_{args.namn}"
        varde = env.get(radnamn, "")
        if varde in PLATSHALLARE:
            print(f"{miljo:12} {radnamn} är tom — hoppar över.")
            continue
        kandidater[miljo] = varde

    if not kandidater:
        print(f"\nIngen ifylld nyckel att sätta. Klistra in den i {ENV_DEPLOY} och kör om.")
        return 1

    fel: list[str] = []

    # Delad nyckel mellan miljöer — se PER_ENV_SECRETS i railway_provision.py.
    if len(kandidater) > 1 and len(set(kandidater.values())) == 1 and not args.tillat_delad:
        fel.append(
            "samma nyckel för flera miljöer. En delad nyckel är en delad KVOT — ett "
            "anrop i development kan ge produktionen 429. Kör med --tillat-delad om "
            "det ändå är avsikten."
        )

    for miljo, nyckel in kandidater.items():
        variabler = railway_variabler(MILJOER[miljo])
        model = variabler.get("MODEL") or standardmodell
        nuvarande = variabler.get(args.namn, "")
        oforandrad = " (oförändrad)" if nuvarande == nyckel else ""
        print(f"\n{miljo}")
        print(f"  nyckel ur .env.deploy : {fingeravtryck(nyckel)}{oforandrad}")
        print(f"  modell i Railway      : {model}")

        problem = verifiera_nyckel(bas_url, nyckel, model)
        if problem:
            fel.append(f"{miljo}: {problem}")
            print(f"  verifiering           : FEL — {problem}")
            continue
        print(f"  verifiering           : modellen är åtkomlig")

        if args.hoppa_prov:
            print("  kvotprov              : överhoppat (--hoppa-prov)")
            continue

        niva, beskrivning = kvotprov(bas_url, nyckel, model)
        print(f"  kvotprov              : {niva.upper()} — {beskrivning}")
        if niva in ("fri", "slut") and not args.tillat_fri_kvot:
            fel.append(
                f"{miljo}: nyckeln ligger på fritt tier. En chatt gör 6 LLM-anrop i "
                f"snitt och fritt tier ger 5/minut — den räcker inte i drift. Slå på "
                f"fakturering för Google-projektet som nyckeln tillhör, eller kör med "
                f"--tillat-fri-kvot om du vet vad du gör."
            )

    if fel:
        print("\nAVBRYTER — ingenting skrivet:")
        for rad in fel:
            print(f"  * {rad}")
        return 1

    if not args.apply:
        print(f"\nTorrkörning. Kör om med --apply för att skriva {args.namn} till Railway.")
        return 0

    # --- Fas 2: skriv, och läs tillbaka. ------------------------------------
    print()
    for miljo, nyckel in kandidater.items():
        satt_variabel(MILJOER[miljo], args.namn, nyckel)
        tillbakalast = railway_variabler(MILJOER[miljo]).get(args.namn, "")
        if tillbakalast != nyckel:
            print(f"{miljo:12} SKREV MEN VERIFIERINGEN FALLERADE — värdet stämmer inte.")
            return 1
        print(f"{miljo:12} {args.namn} satt och tillbakaläst ({fingeravtryck(nyckel)})")

    print(
        "\nRailway startar om tjänsten av sig själv när en variabel ändras.\n"
        "Verifiera i drift, inte i den här utskriften:\n"
        "  /health/ready ska svara mode: live\n"
        "  ett riktigt chattanrop ska nå completed, inte failed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
