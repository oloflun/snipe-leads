#!/usr/bin/env python3
"""Koppla en egen domän till Railways web-tjänst — och säg exakt vad DNS kräver.

    python scripts/railway_doman.py                      # visa nuvarande domäner
    python scripts/railway_doman.py --add www.snajp.se   # lägg till, visa DNS-post
    python scripts/railway_doman.py --env development --add ...

## Varför skriptet finns i stället för en punktlista

Att koppla en domän är två halvor hos två olika leverantörer: Railway måste veta
att den ska svara för värdnamnet, och DNS måste peka dit. Den första halvan går
att automatisera och verifiera; den andra kräver registrarens gränssnitt. Ett
dokument som beskriver båda blir inaktuellt utan att någon märker det — det här
kommandot kan köras om och falsifieras.

## Apex kontra www, och varför skillnaden inte är en detalj

Railway pekas ut med en CNAME. En CNAME får enligt DNS-standarden inte samexistera
med andra poster på samma namn, och apex (`snajp.se`) MÅSTE ha NS- och SOA-poster.
Därför går apex bara att peka med ALIAS/ANAME, som är en leverantörsspecifik
utökning — Loopia, där snajp.se ligger, har den inte.

Följden i praktiken: `www.snajp.se` pekas med CNAME, och apex löses med Loopias
egen webbvidarebefordran till www. Skriptet säger vilket som gäller per domän i
stället för att låta den som kör gissa.

Leakage-spärr: token läses av scripts/railway.py ur .env.deploy och skrivs
aldrig ut. Se den filen.
"""
from __future__ import annotations

import argparse
import sys

from railway import gql

PROJEKT = "brave-passion"


def hitta(env_namn: str) -> tuple[str, str, str]:
    """(projektId, miljöId, webTjänstId) för miljön."""
    # `projects` på toppnivå, INTE `me { projects }`: tokenen i .env.deploy är
    # en projekt-token, och den svarar "Not Authorized" på me-grenen. Samma
    # fråga som scripts/railway.py redan använder.
    data = gql(
        """
        query {
          projects {
            edges { node {
              id name
              environments { edges { node { id name } } }
              services { edges { node { id name } } }
            } }
          }
        }
        """
    )
    for kant in data["projects"]["edges"]:
        p = kant["node"]
        if p["name"] != PROJEKT:
            continue
        miljoer = {e["node"]["name"]: e["node"]["id"] for e in p["environments"]["edges"]}
        tjanster = {e["node"]["name"]: e["node"]["id"] for e in p["services"]["edges"]}
        if env_namn not in miljoer:
            sys.exit(f"Miljön {env_namn!r} finns inte. Finns: {', '.join(sorted(miljoer))}")
        if "web" not in tjanster:
            sys.exit(f"Ingen tjänst 'web'. Finns: {', '.join(sorted(tjanster))}")
        return p["id"], miljoer[env_namn], tjanster["web"]
    sys.exit(f"Projektet {PROJEKT!r} hittades inte på den här tokenen.")


def lista(projekt_id: str, env_id: str, tjanst_id: str) -> dict:
    data = gql(
        """
        query($p:String!,$e:String!,$s:String!) {
          domains(projectId:$p, environmentId:$e, serviceId:$s) {
            customDomains { id domain status { verified verificationDnsHost verificationToken certificateStatus dnsRecords { hostlabel recordType requiredValue currentValue status } } }
            serviceDomains { domain }
          }
        }
        """,
        {"p": projekt_id, "e": env_id, "s": tjanst_id},
    )
    return data["domains"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=("main", "development"), default="main")
    ap.add_argument("--add", metavar="DOMÄN", help="värdnamn att koppla, t.ex. www.snajp.se")
    args = ap.parse_args()

    projekt_id, env_id, tjanst_id = hitta(args.env)

    if args.add:
        namn = args.add.strip().lower().rstrip(".")
        etiketter = namn.split(".")
        if len(etiketter) < 3:
            print(
                f"VARNING: {namn} är en apex-domän. Railway pekas ut med CNAME, och en\n"
                "CNAME får inte ligga på apex (den krockar med NS och SOA). Loopia stödjer\n"
                "inte ALIAS/ANAME. Koppla www i stället, och lägg en webbvidarebefordran\n"
                "från apex till www hos Loopia.\n"
            )
        try:
            gql(
                """
                mutation($i:CustomDomainCreateInput!) {
                  customDomainCreate(input:$i) { id domain }
                }
                """,
                {
                    "i": {
                        "domain": namn,
                        "projectId": projekt_id,
                        "environmentId": env_id,
                        "serviceId": tjanst_id,
                    }
                },
            )
            print(f"lade till {namn}")
        except SystemExit as fel:
            # Redan tillagd är inte ett fel värt att avbryta på — vi vill ändå
            # skriva ut DNS-posten nedan.
            if "already" not in str(fel).lower() and "exist" not in str(fel).lower():
                raise
            print(f"{namn} fanns redan")

    d = lista(projekt_id, env_id, tjanst_id)

    print(f"\nmiljö: {args.env}")
    for sd in d.get("serviceDomains") or []:
        print(f"  railway-adress   {sd['domain']}")

    egna = d.get("customDomains") or []
    if not egna:
        print("  egna domäner     (inga)")
        return 0

    for cd in egna:
        print(f"\n  egen domän       {cd['domain']}")
        st = cd.get("status") or {}
        print(f"    verifierad     {st.get('verified')}")
        cert = str(st.get("certificateStatus") or "").replace("CERTIFICATE_STATUS_TYPE_", "")
        print(f"    certifikat     {cert or '(okand)'}")
        # Agarskapsposten syns INTE i dnsRecords. Utan den utfardas
        # inget certifikat, hur ratt CNAME:n an pekar.
        if st.get("verificationDnsHost") and not st.get("verified"):
            print(f"    KRAVS  TXT    {st['verificationDnsHost']:22} -> {st.get('verificationToken')}")
        for post in (cd.get("status") or {}).get("dnsRecords") or []:
            # Railway svarar med hela enum-namnet, t.ex.
            # DNS_RECORD_STATUS_PROPAGATED. Jamforelsen mot bara "PROPAGATED"
            # matchade aldrig, sa en post som var klar rapporterades som
            # VANTAR - i dagar. endswith i stallet for likhet.
            klar = "OK " if str(post.get("status", "")).endswith("PROPAGATED") else "VÄNTAR"
            vard = post.get("hostlabel") or "@"
            print(f"    {klar}  {post['recordType']:6} {vard:20} -> {post['requiredValue']}")
            nuvarande = post.get("currentValue")
            if nuvarande and nuvarande != post["requiredValue"]:
                print(f"           pekar nu på: {nuvarande}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
