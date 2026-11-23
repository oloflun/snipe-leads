#!/usr/bin/env python
"""Lägger PAGESPEED_API_KEY på api i development och main, efter ett prov mot PageSpeed.

    python scripts/satt_pagespeed_nyckel.py

Nyckeln klistras in dolt (getpass) och skrivs aldrig ut, loggas aldrig och
läggs aldrig i ett kommandoargument. Skapad 2026-11-22 i kreditprojektet
(rock-sentinel-515323-r8, "Snajp PageSpeed", begränsad till PageSpeed
Insights API). Skälet: utan nyckel svarar PageSpeed 429, och sidbedömningens
gratisreserv (webbrevision.revidera) behöver den (docs/BESLUT.md 2026-11-22).
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway import gql  # noqa: E402

P = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"
API = "5828c279-ad8f-429b-b5e1-969372db8a0a"
MILJOER = {"development": "02c39616-1b8e-47b7-beea-d8c6cfba1acd", "main": "47bc7047-a458-404b-a1de-ccec612cb96e"}


def main() -> None:
    nyckel = getpass.getpass("Klistra in PageSpeed-nyckeln (syns inte): ").strip()
    if not nyckel:
        sys.exit("Ingen nyckel angiven.")
    svar = requests.get(
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
        params={"url": "https://www.snajp.se", "strategy": "desktop", "key": nyckel}, timeout=120,
    )
    if svar.status_code != 200:
        sys.exit(f"PageSpeed svarade {svar.status_code}; nyckeln sattes inte. Vänta en minut och försök igen.")
    print("PageSpeed svarade 200 med nyckeln.")
    for namn, miljo in MILJOER.items():
        gql("mutation($i:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$i)}",
            {"i": {"projectId": P, "environmentId": miljo, "serviceId": API,
                   "variables": {"PAGESPEED_API_KEY": nyckel}, "replace": False}})
        v = gql("query($p:String!,$e:String!,$s:String!){variables(projectId:$p,environmentId:$e,serviceId:$s)}",
                {"p": P, "e": miljo, "s": API})["variables"]
        print(f"{namn}/api: PAGESPEED_API_KEY {'satt' if v.get('PAGESPEED_API_KEY') == nyckel else 'SAKNAS'}")


if __name__ == "__main__":
    main()
