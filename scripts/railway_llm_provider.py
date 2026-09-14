#!/usr/bin/env python3
"""Byt LLM-provider på en Railway-miljö — nyckeln verifieras INNAN den skrivs.

    python scripts/railway_llm_provider.py --env development --provider openai
    python scripts/railway_llm_provider.py --env main --provider openai --model gpt-4o-mini

Nyckeln läses med getpass: den syns aldrig på skärmen, hamnar aldrig i
skalhistoriken och passerar aldrig en chattkanal. Har miljön redan en giltig
nyckel för providern går det att behålla den med --behall-nyckel.

## Varför skriptet finns

Att byta provider är tre variabler som måste stämma med varandra, och varje
kombination som inte stämmer har redan kostat en eftermiddag i det här
projektet:

  * `LLM_PROVIDER` utan nyckel  -> `is_simulation()` blir sann och tjänsten
    svarar kunder med REGELMOTORN. Inget larmar. Uppmätt i main 2026-08-25:
    `LLM_PROVIDER=openai` var satt utan `OPENAI_API_KEY`, och
    /health/ready svarade `mode: simulation`.
  * `MODEL` från fel familj -> 404 på varje anrop medan hälsokontrollen säger
    `live`. Det är vad `MODELLFAMILJER` i config.py finns för att fånga, och
    skriptet gör samma kontroll här så felet aldrig hinner deployas.
  * En nyckel som inte fungerar -> samma sak som ingen nyckel alls.

Därför verifieras nyckeln mot leverantörens eget API, och modellen slås upp
hos leverantören, FÖRE någonting skrivs till Railway. En dålig nyckel ska falla
i din terminal, inte i produktionen.

Efter skrivningen görs en redeploy och /health/ready pollas tills tjänsten
svarar `mode: live` — beviset är tjänstens eget svar, inte att mutationen gick
igenom.

DeepSeek går inte att sätta på en miljö med riktig kunddata; spärren sitter i
`Settings.llm_provider_fault()` och skriptet vägrar redan här, så att felet
inte upptäcks först som ett dött bygge.
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway import gql  # noqa: E402
from railway_env_bootstrap import service_vars  # noqa: E402
from railway_provision import (  # noqa: E402
    deploy,
    env_read,
    envs_by_name,
    services_by_name,
    set_vars,
    state,
)

#: Providernamn -> (env-variabel för nyckeln, bas-URL, standardmodell).
#: Speglar _resolve_base_url och active_llm_key i snajp-support/app/agent/llm.py
#: respektive config.py. Håll dem lika.
PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-4o-mini"),
    "gemini": (
        "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-3.6-flash",
    ),
}

#: Miljöer som bär eller speglar riktig kunddata. Samma lista som
#: MILJOER_MED_KUNDDATA i config.py — development är en SPEGEL av produktionen.
MILJOER_MED_KUNDDATA = {"main", "development"}


def modellfamilj(model: str) -> str | None:
    """Samma karta som MODELLFAMILJER i config.py."""
    namn = (model or "").strip().lower()
    for prefix, provider in {
        "gpt-": "openai", "o1-": "openai", "o3-": "openai", "o4-": "openai",
        "deepseek": "deepseek", "gemini": "gemini",
    }.items():
        if namn.startswith(prefix):
            return provider
    return None


def verifiera_nyckel(bas_url: str, nyckel: str, model: str) -> None:
    """Nyckeln OCH modellen, mot leverantörens eget API. Avbryter vid fel."""
    req = urllib.request.Request(
        f"{bas_url}/models/{model}", headers={"Authorization": f"Bearer {nyckel}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as svar:
            json.load(svar)
    except urllib.error.HTTPError as fel:
        if fel.code in (401, 403):
            sys.exit("AVBRYTER: leverantören avvisade nyckeln (401/403). Inget skrivet.")
        if fel.code == 404:
            sys.exit(
                f"AVBRYTER: modellen {model!r} finns inte för den här nyckeln (404). "
                "Inget skrivet — det är precis det felet som annars ger 404 på "
                "varje anrop medan hälsokontrollen säger 'live'."
            )
        sys.exit(f"AVBRYTER: uppslaget av modellen svarade {fel.code}. Inget skrivet.")
    except urllib.error.URLError as fel:
        sys.exit(f"AVBRYTER: kunde inte nå {bas_url} ({fel.reason}). Inget skrivet.")
    print(f"  nyckeln verifierad mot {bas_url} — modellen {model} är åtkomlig")


def vanta_pa_live(api_url: str, minuter: int = 5) -> bool:
    """Pollar /health/ready tills tjänsten svarar mode: live."""
    slut = time.time() + minuter * 60
    senaste = None
    while time.time() < slut:
        try:
            with urllib.request.urlopen(api_url + "/health/ready", timeout=20) as svar:
                kropp = json.load(svar)
            senaste = kropp.get("mode")
            if senaste == "live":
                print(f"  /health/ready: mode={senaste}, storage={kropp.get('storage')}")
                return True
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            senaste = "(svarar inte — deployar troligen)"
        time.sleep(10)
    print(f"  /health/ready: mode={senaste} efter {minuter} min")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["development", "main"], required=True)
    ap.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    ap.add_argument("--model", help="standard: providerns default (se PROVIDERS)")
    ap.add_argument(
        "--behall-nyckel",
        action="store_true",
        help="skriv inte om nyckeln — miljön har redan en som fungerar",
    )
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    nyckel_var, bas_url, standardmodell = PROVIDERS[args.provider]
    model = args.model or standardmodell

    familj = modellfamilj(model)
    if familj is not None and familj != args.provider:
        sys.exit(
            f"AVBRYTER: {model!r} är en {familj}-modell men providern är "
            f"{args.provider!r}. Anropet hade gått till {args.provider}s endpoint "
            f"med ett modellnamn som inte finns där — 404 på varje förfrågan, "
            f"medan hälsokontrollen rapporterar 'live'."
        )

    store = env_read()
    api_url = store.get(f"RAILWAY_{args.env.upper()}_API_URL")
    if not api_url:
        sys.exit(f"AVBRYTER: RAILWAY_{args.env.upper()}_API_URL saknas i .env.deploy.")

    project = state()
    env_id = envs_by_name(project).get(args.env)
    if not env_id:
        sys.exit(f"AVBRYTER: miljön {args.env} finns inte i Railway-projektet.")
    api = services_by_name(project).get("api")
    if not api:
        sys.exit("AVBRYTER: tjänsten api finns inte i projektet.")

    befintliga = service_vars(api["id"], env_id)
    har_nyckel = len(befintliga.get(nyckel_var) or "") >= 20

    print(f"Miljö: {args.env}  Backend: {api_url}")
    print(f"  nu:    LLM_PROVIDER={befintliga.get('LLM_PROVIDER')}  MODEL={befintliga.get('MODEL')}")
    print(f"  efter: LLM_PROVIDER={args.provider}  MODEL={model}")
    print(f"  {nyckel_var}: {'finns (>=20 tecken)' if har_nyckel else 'SAKNAS eller för kort'}")

    if args.behall_nyckel and not har_nyckel:
        sys.exit(
            f"AVBRYTER: --behall-nyckel angavs men {nyckel_var} saknas i {args.env}. "
            f"Utan nyckel går tjänsten ner i simuleringsläge och svarar kunder "
            f"med regelmotorn, utan att något larmar."
        )

    if not args.apply:
        print("\nTORRKÖRNING — inget skrivet. Lägg till --apply.")
        return 0

    variabler = {"LLM_PROVIDER": args.provider, "MODEL": model}
    if not args.behall_nyckel:
        nyckel = getpass.getpass(f"  {nyckel_var} (syns inte): ").strip()
        if len(nyckel) < 20:
            sys.exit("AVBRYTER: nyckeln är kortare än 20 tecken — det räknas som ingen nyckel.")
        if any(ord(c) > 127 for c in nyckel):
            sys.exit(
                "AVBRYTER: nyckeln innehåller ett tecken utanför ASCII och kan inte "
                "skickas i ett Authorization-huvud (se llm_key_fault i config.py)."
            )
        verifiera_nyckel(bas_url, nyckel, model)
        variabler[nyckel_var] = nyckel
    else:
        print("  behåller befintlig nyckel (ej verifierad — den ligger krypterad hos Railway)")

    set_vars(api["id"], env_id, variabler)
    deploy(api["id"], env_id)
    print(f"  api ({args.env}) redeployar")

    if vanta_pa_live(api_url):
        print("\nKlart. Tjänsten kör mot riktig modell.")
        return 0
    print(
        "\nVARNING: tjänsten rapporterar inte mode: live än. Deployen kan fortfarande "
        "pågå — kolla om en stund. Rapporterar den 'simulation' saknas nyckeln."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
