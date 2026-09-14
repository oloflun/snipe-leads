#!/usr/bin/env python3
"""Provisionera tjänsten `bokforing` (bokforing-webb/) i Railway — idempotent.

    python scripts/railway_bokforing.py            # visa läget
    python scripts/railway_bokforing.py --apply    # skapa/rätta allt

Samma mönster som railway_provision.py: GraphQL via scripts/railway.py, token
och hemligheter ur .env.deploy, ingenting echas.

Tjänsten finns BARA i miljön `development`. Den är den fristående
bokföringsagent-sajten (Next-appen i bokforing-webb/), byggd ur samma repo
med rootDirectory=/bokforing-webb och gren `development` — en push dit
deployar den, precis som web och api.

Sajten saknar konton, så den bär en Basic Auth-vägg (bokforing-webb/proxy.ts)
styrd av BOKFORING_LOSEN. Skriptet genererar lösenordet första gången och
skriver det till .env.deploy som RAILWAY_DEVELOPMENT_BOKFORING_LOSEN.
"""
from __future__ import annotations

import argparse
import secrets as pysecrets
import sys

from railway import gql
from railway_provision import (
    PROJECT_ID,
    REPO,
    ensure_domain,
    ensure_trigger,
    env_read,
    env_set,
    envs_by_name,
    instance,
    instance_update,
    services_by_name,
    set_vars,
    state,
)

TJANST = "bokforing"
GREN = "development"
MILJO = "development"
ROT = "/bokforing-webb"


def secret_losen() -> str:
    store = env_read()
    key = "RAILWAY_DEVELOPMENT_BOKFORING_LOSEN"
    if store.get(key):
        return store[key]
    value = pysecrets.token_urlsafe(18)
    env_set(key, value)
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    project = state()
    env_id = envs_by_name(project).get(MILJO)
    if not env_id:
        sys.exit(f"Miljön {MILJO} saknas i projektet.")
    services = services_by_name(project)

    if TJANST not in services:
        if not args.apply:
            print(f"{TJANST}: SAKNAS (kör med --apply)")
            return
        gql(
            "mutation($in: ServiceCreateInput!){ serviceCreate(input:$in){ id name } }",
            # environmentId är INTE valfri kosmetika: utan den lägger Railway
            # instansen i projektets default-miljö (main) — uppmätt, och då
            # finns ingen ServiceInstance i development att sätta domän på.
            {"in": {"projectId": PROJECT_ID, "name": TJANST, "environmentId": env_id,
                    "source": {"repo": REPO}, "branch": GREN}},
        )
        print(f"{TJANST}: tjänsten skapad")
        project = state()
        services = services_by_name(project)

    svc = services[TJANST]
    if not args.apply:
        inst = instance(svc, env_id)
        print(f"{TJANST}: finns (instans i {MILJO}: {'ja' if inst else 'nej'})")
        return

    # Gren per miljö bärs av deployment-triggern (se ensure_trigger i
    # railway_provision.py för varför serviceConnect inte räcker). Triggers i
    # ANDRA miljöer tas bort: tjänsten ska aldrig byggas i main.
    ensure_trigger(project, svc["id"], env_id, GREN)
    for t in project["deploymentTriggers"]["edges"]:
        n = t["node"]
        if n["serviceId"] == svc["id"] and n["environmentId"] != env_id:
            gql("mutation($id:String!){ deploymentTriggerDelete(id:$id) }", {"id": n["id"]})
            print(f"    trigger i främmande miljö borttagen ({n['environmentId']})")

    instance_update(svc["id"], env_id, rootDirectory=ROT)
    print(f"    rootDirectory: {ROT}")

    domain = ensure_domain(svc["id"], env_id, services_by_name(state())[TJANST])
    print(f"    domän: https://{domain}")

    store = env_read()
    api_url = store.get("RAILWAY_DEVELOPMENT_API_URL")
    demo_key = store.get("RAILWAY_DEVELOPMENT_DEMO_API_KEY")
    if not api_url or not demo_key:
        sys.exit("RAILWAY_DEVELOPMENT_API_URL/_DEMO_API_KEY saknas i .env.deploy.")

    set_vars(svc["id"], env_id, {
        # Samma miljös backend — aldrig korskoppling mot main (se provision()).
        "SNAJP_SUPPORT_URL": api_url,
        "SNAJP_BOOKKEEPING_API_KEY": demo_key,
        "BOKFORING_LOSEN": secret_losen(),
    })

    env_set("RAILWAY_DEVELOPMENT_BOKFORING_URL", f"https://{domain}")
    print("klart — en push till development bygger tjänsten.")


if __name__ == "__main__":
    main()
