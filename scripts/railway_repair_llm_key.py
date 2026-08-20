#!/usr/bin/env python3
"""Laga en LLM-nyckel som blivit korrumperad vid inklistring — mot leverantören.

    python scripts/railway_repair_llm_key.py --env development
    python scripts/railway_repair_llm_key.py --env development --apply

## Vad som gick sönder

`DEEPSEEK_API_KEY` i Railway är 39 tecken med icke-ASCII på position 0 och 2.
En nyckel går i huvudet `Authorization: Bearer <nyckel>`, och huvudvärden är
ASCII — alltså föll varje agentanrop inne i http-klienten, inte hos DeepSeek.
Backenden upptäcker det vid start (`Settings.llm_key_fault()`) och går i
simuleringsläge i stället för att falla på första anropet.

## Varför den vågar laga i stället för att bara varna

Kandidaten prövas mot leverantören INNAN något skrivs. `GET /models` med
nyckeln i huvudet svarar 200 eller 401, och först på 200 rörs Railway. En
"lagning" som inte testats är en gissning, och en gissning i en nyckel ger ett
fel som ser ut som något helt annat en vecka senare.

Skriptet skriver bara till EN miljö åt gången, angiven med `--env`. Det finns
ingen flagga som tar båda: `main` rörs först när något är verifierat i
previewen, och det beslutet ska inte kunna bli en bieffekt av ett kommando.

## Leakagespärr

Nyckeln läses ur Railway och skrivs tillbaka till Railway. Den passerar aldrig
terminalen — utskrifterna säger längd, form och HTTP-status, aldrig värdet.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from keys import key_fault  # noqa: E402
from railway import gql  # noqa: E402
from railway_provision import (ENVIRONMENTS, PROJECT_ID, deploy, env_read,  # noqa: E402
                               envs_by_name, services_by_name, set_vars, state)

VARS = "query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }"

#: Leverantörens nyckelform och en gratis endpoint som svarar 401 på fel nyckel.
PROVIDERS = {
    "deepseek": {
        "var": "DEEPSEEK_API_KEY",
        "form": re.compile(r"^sk-[A-Za-z0-9]{32}$"),
        "probe": "https://api.deepseek.com/models",
    },
}


def kandidater(raw: str) -> list[tuple[str, str]]:
    """Möjliga rekonstruktioner, i ordning från minst till mest ingripande."""
    ascii_only = "".join(ch for ch in raw if ord(ch) < 128)
    out = [("bara icke-ascii bort", ascii_only)]
    if "sk-" in ascii_only:
        out.append(("från första 'sk-'", ascii_only[ascii_only.index("sk-"):]))
    return [(namn, v) for namn, v in out if v and v != raw]


def probe(url: str, nyckel: str, forsok: int = 3) -> int:
    """HTTP-status från leverantören, eller -1 om den inte gick att nå.

    Skillnaden är hela poängen. Ett 401 är ett SVAR: nyckeln duger inte. Ett
    avbrutet TLS-handslag är INGET svar, och att låta det räknas som 401 hade
    fått skriptet att döma ut en fungerande nyckel — och nästa läsare att sätta
    om en nyckel som aldrig var trasig.
    """
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {nyckel}",
        "User-Agent": "snajp-keycheck/1.0",
    })
    for i in range(forsok):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception as exc:  # TLS-blipp, DNS, proxy — inget svar
            if i == forsok - 1:
                print(f"    nådde inte {url}: {type(exc).__name__}")
                return -1
            time.sleep(2 * (i + 1))
    return -1


def health_mode(url: str) -> str | None:
    try:
        with urllib.request.urlopen(f"{url}/health/ready", timeout=20) as resp:
            return json.load(resp).get("mode")
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True, choices=sorted(ENVIRONMENTS))
    ap.add_argument("--provider", default="deepseek", choices=sorted(PROVIDERS))
    ap.add_argument("--apply", action="store_true", help="skriv tillbaka och deploya om")
    args = ap.parse_args()

    spec = PROVIDERS[args.provider]
    project = state()
    env_id = envs_by_name(project).get(args.env)
    if not env_id:
        sys.exit(f"Miljön {args.env} finns inte i projektet.")
    api = services_by_name(project)["api"]

    raw = (gql(VARS, {"p": PROJECT_ID, "e": env_id, "s": api["id"]})["variables"] or {}).get(spec["var"])
    if not raw:
        sys.exit(f"{spec['var']} är inte satt i {args.env}.")

    fel = key_fault(raw)
    print(f"{args.env}/{spec['var']}: längd={len(raw)}, form={'ok' if spec['form'].match(raw) else 'fel'}")
    if not fel and spec["form"].match(raw):
        print(f"  status {probe(spec['probe'], raw)} — nyckeln är hel, ingenting att laga.")
        return 0
    print(f"  trasig: {fel or 'stämmer inte med leverantörens nyckelform'}")

    lagad = None
    for namn, k in kandidater(raw):
        form_ok = bool(spec["form"].match(k))
        status = probe(spec["probe"], k) if form_ok else None
        print(f"  kandidat {namn!r}: längd={len(k)} form={'ok' if form_ok else 'fel'}"
              + (f" status={status}" if status else " (prövas inte)"))
        if status == 200:
            lagad = k
            break
    if not lagad:
        print("\nIngen kandidat godkändes av leverantören. Nyckeln måste sättas om för hand.")
        return 1

    if not args.apply:
        print("\nEn kandidat GODKÄNDES av leverantören. Kör om med --apply för att skriva den.")
        return 0

    set_vars(api["id"], env_id, {spec["var"]: lagad})
    print(f"  deploy {deploy(api['id'], env_id)}")

    url = env_read().get(f"RAILWAY_{args.env.upper()}_API_URL")
    if not url:
        print("  ingen API-URL i .env.deploy — kan inte verifiera i drift.")
        return 0
    # Verifieringen är poängen: en satt variabel bevisar att API:t tog emot den,
    # inte att processen kör med den. `mode` går från simulation till live först
    # när den nya containern är uppe.
    print("\nVerifierar mot /health/ready (kan ta en minut):")
    for _ in range(30):
        mode = health_mode(url)
        if mode == "live":
            print(f"  mode={mode} — riktig modell aktiv.")
            return 0
    print(f"  mode={health_mode(url)} — inte live än. Se /health/ready för skälet.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
