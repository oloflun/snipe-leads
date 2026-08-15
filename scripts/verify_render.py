#!/usr/bin/env python
"""Jämför Renders FAKTISKA tjänster mot snajp-support/render.yaml.

    python scripts/verify_render.py

Varför den här finns: **det finns ingen Render Blueprint.** `/v1/blueprints`
returnerar en tom lista — båda tjänsterna är fristående, skapade i dashboarden
respektive via API:t. `render.yaml` läses alltså inte av någonting, och
INV-DEPLOY-001 vaktar en fil som inte styr driften.

Det är precis den luckan som orsakade två produktionsincidenter: Root
Directory-fältet i dashboarden har återgått till `snajp-support` av sig självt,
vilket fäller Docker-bygget med `"/agent-core": not found`, och grenvalet har
pekat mot `development` medan frontenden deployade från `main`. Inget av det
syns i en diff, eftersom sanningen ligger i Renders databas.

Det här skriptet gör filen till ett kontrakt igen: den beskriver avsikten, och
skriptet kontrollerar att verkligheten stämmer. Kör det efter varje ändring i
Render-dashboarden och som del av driftsättningsrutinen.

Kräver RENDER_API_KEY (env eller .env.deploy).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RENDER_YAML = ROOT / "snajp-support" / "render.yaml"
API = "https://api.render.com/v1"


def api_key() -> str:
    if os.environ.get("RENDER_API_KEY"):
        return os.environ["RENDER_API_KEY"]
    deploy = ROOT / ".env.deploy"
    if deploy.exists():
        for line in deploy.read_text(encoding="utf-8").splitlines():
            if line.startswith("RENDER_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit(
        "AVBRYTER: RENDER_API_KEY saknas. Skapa en i Render → Account Settings → "
        "API Keys och lägg den i .env.deploy (gitignorerad)."
    )


def declared_services() -> list[dict[str, str]]:
    """Tjänsterna som render.yaml deklarerar.

    Handrullad parser av samma skäl som i INV-DEPLOY-001: sviten körs utan
    PyYAML, och filen är vår egen med stabilt format.
    """
    services: list[dict[str, str]] = []
    for line in RENDER_YAML.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or ":" not in stripped:
            continue
        new_service = stripped.startswith("- ") and stripped[2:].startswith("type:")
        key, _, value = stripped.lstrip("- ").strip().partition(":")
        if new_service:
            services.append({})
        if services:
            services[-1].setdefault(key.strip(), value.strip())
    return services


def live_services(key: str) -> dict[str, dict]:
    request = urllib.request.Request(
        f"{API}/services?limit=50",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            rows = json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"AVBRYTER: Render svarade {error.code} — {error.read().decode()[:200]}")
    return {row.get("service", row)["name"]: row.get("service", row) for row in rows}


def normalise_path(value: str | None) -> str:
    """`.` och `''` betyder samma sak för rootDir; `./x` och `x` för filvägar."""
    value = (value or "").strip()
    if value in (".", ""):
        return ""
    return re.sub(r"^\./", "", value)


def main() -> None:
    key = api_key()
    live = live_services(key)
    declared = declared_services()

    if not declared:
        sys.exit("AVBRYTER: render.yaml deklarerar inga tjänster — inget att jämföra.")

    avvikelser = 0
    for service in declared:
        name = service.get("name", "?")
        actual = live.get(name)
        if actual is None:
            print(f"SAKNAS  {name}: deklarerad i render.yaml men finns inte i Render.")
            avvikelser += 1
            continue

        details = actual.get("serviceDetails", {}) or {}
        env_specific = details.get("envSpecificDetails", {}) or {}

        kontroller = [
            ("branch", service.get("branch"), actual.get("branch")),
            ("rootDir", normalise_path(service.get("rootDir")), normalise_path(actual.get("rootDir"))),
            (
                "dockerfilePath",
                normalise_path(service.get("dockerfilePath")),
                normalise_path(env_specific.get("dockerfilePath")),
            ),
            ("healthCheckPath", service.get("healthCheckPath"), details.get("healthCheckPath")),
            ("plan", service.get("plan"), details.get("plan")),
        ]

        fel = [(f, v, a) for f, v, a in kontroller if v and v != a]
        if fel:
            print(f"AVVIKER {name}  ({actual.get('id')})")
            for faltet, deklarerat, verkligt in fel:
                print(f"   {faltet}: render.yaml={deklarerat!r} men Render har {verkligt!r}")
            avvikelser += len(fel)
        else:
            print(f"ok      {name}  gren={actual.get('branch')} rootDir=repo-roten")

    okanda = set(live) - {s.get("name") for s in declared}
    for name in sorted(okanda):
        print(f"EXTRA   {name}: finns i Render men inte i render.yaml.")

    if avvikelser:
        print(
            f"\n{avvikelser} avvikelser. Render styr driften — filen är bara avsikten. "
            "Rätta i Render, eller uppdatera render.yaml om verkligheten har rätt."
        )
        sys.exit(1)
    print("\nRender stämmer med render.yaml.")


if __name__ == "__main__":
    main()
