#!/usr/bin/env python3
"""En egen Railway-miljö för grenen `crm`, så att Snajp CRM går att se utan att
`development` rörs (Antons beställning 2026-11-28).

Miljön heter `crm` och bär EN tjänst, `crm-web`, som bygger webben ur grenen
`crm`. Den har ingen databas, ingen backend och inga nycklar: det som går att
se är förhandsvisningen under `/forhandsvisning/crm`, där anropen besvaras i
webbläsaren med påhittad data. Inloggning och `/crm` med riktig data kräver en
databas och en `api`-tjänst, och det byggs först när Anton säger till.

Varför en TOM miljö och inte en kopia av `development`: en kopia tar med sig
variablerna, alltså adressen till development-databasen, som är en spegel av
produktionen. Den här miljön ska inte kunna nå en enda kundrad.

Körbart om och om igen. Utan `--apply` visas bara vad som skulle göras.

    python scripts/railway_crm_miljo.py            # planen
    python scripts/railway_crm_miljo.py --apply    # skapa, koppla, bygg

Läckagespärr: `AUTH_SECRET` slumpas här och skrivs aldrig ut.
"""
from __future__ import annotations

import argparse
import secrets
import sys

from railway import gql
from railway_driftjobb import region
from railway_provision import (
    PROJECT_ID,
    REPO,
    ensure_trigger,
    envs_by_name,
    instance,
    instance_update,
    read_vars,
    services_by_name,
    set_vars,
    state,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MILJO = "crm"
TJANST = "crm-web"
GREN = "crm"
#: Regionen läses ur api i den här miljön, så att bygget hamnar i EU som resten.
REGIONKALLA = "development"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="skapa och bygg (annars visas bara planen)")
    args = ap.parse_args()
    gor = args.apply

    projekt = state()
    miljoer = envs_by_name(projekt)
    miljo_id = miljoer.get(MILJO)
    print(f"miljön {MILJO}: " + ("finns" if miljo_id else "skapas" if gor else "(skulle skapas, tom)"))
    if not miljo_id:
        if not gor:
            print(f"tjänsten {TJANST}: (skulle skapas, gren {GREN}, utan databas och utan nycklar)")
            return 0
        # Ingen sourceEnvironmentId: miljön blir tom och ärver inga variabler.
        miljo_id = gql(
            "mutation($in: EnvironmentCreateInput!){ environmentCreate(input:$in){ id name } }",
            {"in": {"projectId": PROJECT_ID, "name": MILJO, "skipInitialDeploys": True}},
        )["environmentCreate"]["id"]
        projekt = state()

    # Spärr: miljön ska vara tom på allt utom den här tjänsten. Skulle Railway
    # ha lagt in andra tjänster (en kopia i stället för en tom miljö) stannar vi.
    andra = [
        namn
        for namn, t in services_by_name(projekt).items()
        if namn != TJANST and instance(t, miljo_id)
    ]
    if andra:
        print(f"STOPP: miljön {MILJO} bär redan {', '.join(sorted(andra))}. Den skulle vara tom. Rör den inte härifrån.")
        return 1

    tjanst = services_by_name(projekt).get(TJANST)
    finns = bool(tjanst and instance(tjanst, miljo_id))
    if tjanst and not finns:
        print(f"STOPP: tjänsten {TJANST} finns men inte i miljön {MILJO}.")
        return 1
    print(f"tjänsten {TJANST}: " + ("finns" if finns else "skapas" if gor else "(skulle skapas)"))
    if not finns:
        if not gor:
            return 0
        tjanst = gql(
            "mutation($in: ServiceCreateInput!){ serviceCreate(input:$in){ id name } }",
            # environmentId krävs: utan den hamnar instansen i default-miljön.
            {"in": {"projectId": PROJECT_ID, "name": TJANST, "environmentId": miljo_id}},
        )["serviceCreate"]
    sid = tjanst["id"]

    # Adressen först: webben vill veta sin egen adress vid bygget.
    doman = None
    for d in gql(
        "query($p:String!,$e:String!,$s:String!){ domains(projectId:$p, environmentId:$e, serviceId:$s){ serviceDomains{ domain } } }",
        {"p": PROJECT_ID, "e": miljo_id, "s": sid},
    )["domains"]["serviceDomains"]:
        doman = d["domain"]
    if not doman and gor:
        doman = gql(
            "mutation($sid:String!,$eid:String!){ serviceDomainCreate(input:{serviceId:$sid, environmentId:$eid}){ domain } }",
            {"sid": sid, "eid": miljo_id},
        )["serviceDomainCreate"]["domain"]
    print("adress: " + (f"https://{doman}" if doman else "(skulle skapas)"))

    satta = read_vars(sid, miljo_id)
    onskade = {
        "AUTH_TRUST_HOST": "true",
        "NEXT_PUBLIC_SITE_URL": f"https://{doman}" if doman else "",
        "SITE_URL": f"https://{doman}" if doman else "",
    }
    saknas = {n: v for n, v in onskade.items() if v and satta.get(n) != v}
    if not satta.get("AUTH_SECRET"):
        saknas["AUTH_SECRET"] = secrets.token_urlsafe(48)
    print("variabler: " + (", ".join(sorted(saknas)) + (" skrivs" if gor else " (skulle skrivas)") if saknas else "stämmer"))
    if saknas and gor:
        set_vars(sid, miljo_id, saknas)
    forbjudna = sorted(n for n in satta if n.startswith(("DATABASE", "SNAJP_KEY", "SNAJP_MASTER", "SNAJP_INTERNAL")))
    if forbjudna:
        print(f"VARNING: miljön bär {', '.join(forbjudna)}. Den skulle sakna databas och nycklar.")

    lage = gql(
        "query($s:String!,$e:String!){ serviceInstance(serviceId:$s, environmentId:$e){ source{ repo } latestDeployment{ id status } } }",
        {"s": sid, "e": miljo_id},
    )["serviceInstance"]
    kopplad = bool((lage.get("source") or {}).get("repo")) or any(
        t["node"]["serviceId"] == sid and t["node"]["environmentId"] == miljo_id
        for t in state()["deploymentTriggers"]["edges"]
    )
    print("källa: " + (f"kopplad till {GREN}" if kopplad else "kopplas" if gor else "(skulle kopplas)"))
    if gor:
        if not kopplad:
            reg = region(projekt, miljoer[REGIONKALLA])
            if reg:
                instance_update(sid, miljo_id, multiRegionConfig=reg)
                print(f"region: {', '.join(reg)}")
            gql(
                "mutation($id:String!,$in:ServiceConnectInput!){ serviceConnect(id:$id, input:$in){ id } }",
                {"id": sid, "in": {"repo": REPO, "branch": GREN}},
            )
        ensure_trigger(state(), sid, miljo_id, GREN)
    senaste = lage.get("latestDeployment") or {}
    print("senaste bygge: " + (f"{senaste.get('status')} ({senaste.get('id')})" if senaste else "inget än"))
    if doman:
        print(f"\nSe den på https://{doman}/forhandsvisning/crm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
