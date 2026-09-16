#!/usr/bin/env python3
"""Provisionera agentsajterna `leads` och `support` i Railway — idempotent.

    python scripts/railway_agentsajt.py --tjanst leads                    # läge
    python scripts/railway_agentsajt.py --tjanst leads --apply            # development
    python scripts/railway_agentsajt.py --tjanst support --env main --apply

Systertjänst till scripts/railway_bokforing.py (bokföringen var först och
behåller sina historiska variabelnamn); de två nya sajterna använder de
generaliserade namnen AGENTSAJT_*. Samma GraphQL-mönster: serviceCreate med
environmentId för första miljön, environmentPatchCommit för instans nummer
två (API:t saknar serviceInstanceCreate), region ams explicit.

Skriptet sätter också <TJÄNST>_EXTERN_URL på web-tjänsten i samma miljö —
det är den variabeln som får "Kör Agent"-knappen att synas i flikens vy.
"""
from __future__ import annotations

import argparse
import sys
import time

from railway import gql
from railway_provision import (
    PROJECT_ID,
    REPO,
    deploy,
    ensure_domain,
    ensure_trigger,
    env_read,
    env_set,
    envs_by_name,
    instance,
    instance_update,
    read_vars,
    services_by_name,
    set_vars,
    state,
)

MILJOER: dict[str, str] = {"development": "development", "main": "main"}
WEB_SERVICE_ID = "0261f633-1247-4d92-b5ab-40c2a1828b90"

#: Förhandsversionens delade inloggning — Sebbes beslut 2026-09-15, samma
#: uppgifter som QA-adminkontot (redan incheckade i scripts/qa_vyer.mjs).
LOSEN = "Snajpen123!"
EPOST = "Snajpsupport@gmail.com"

TJANSTER: dict[str, dict[str, str]] = {
    "leads": {"rot": "/leads-webb", "extern_env": "LEADS_EXTERN_URL"},
    "support": {"rot": "/support-webb", "extern_env": "SUPPORT_EXTERN_URL"},
}


def _skapa_via_patch(svc_id: str, env_id: str, gren: str, rot: str) -> None:
    """Instans i en YTTERLIGARE miljö — samma väg och skäl som i
    railway_bokforing._skapa_via_patch (uppmätta fällor dokumenterade där)."""
    patch: dict = {
        "services": {
            svc_id: {
                "source": {"repo": REPO, "branch": gren, "rootDirectory": rot, "checkSuites": False},
                "build": {"builder": "RAILPACK", "buildEnvironment": "V3"},
                "deploy": {"runtime": "V2", "multiRegionConfig": {"ams": {"numReplicas": 1}}},
            }
        }
    }
    cfg = gql("query($id:String!){ environment(id:$id){ config } }", {"id": env_id})["environment"]["config"]
    levande = {s["node"]["id"] for s in state()["services"]["edges"]}
    for spoke in (cfg.get("services") or {}):
        if spoke not in levande:
            patch["services"][spoke] = None
            print(f"    spökpost i miljökonfigen tas bort: {spoke[:8]}…")
    gql(
        "mutation($e:String!,$p:EnvironmentConfig!,$m:String){"
        " environmentPatchCommit(environmentId:$e, patch:$p, commitMessage:$m) }",
        {"e": env_id, "p": patch, "m": f"agentsajt i miljön (gren {gren})"},
    )
    print(f"    instans skapad via config-patch (gren {gren}, region ams)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tjanst", choices=sorted(TJANSTER), required=True)
    ap.add_argument("--env", choices=sorted(MILJOER), default="development")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    tj = TJANSTER[args.tjanst]
    gren = MILJOER[args.env]
    prefix = f"RAILWAY_{args.env.upper()}"

    project = state()
    env_id = envs_by_name(project).get(args.env)
    if not env_id:
        sys.exit(f"Miljön {args.env} saknas i projektet.")
    services = services_by_name(project)

    if args.tjanst not in services:
        if not args.apply:
            print(f"{args.tjanst}: SAKNAS (kör med --apply)")
            return
        gql(
            "mutation($in: ServiceCreateInput!){ serviceCreate(input:$in){ id name } }",
            # environmentId krävs — utan den hamnar instansen i default-miljön.
            {"in": {"projectId": PROJECT_ID, "name": args.tjanst, "environmentId": env_id,
                    "source": {"repo": REPO}, "branch": gren}},
        )
        print(f"{args.tjanst}: tjänsten skapad")
        project = state()
        services = services_by_name(project)

    svc = services[args.tjanst]
    har_instans = instance(svc, env_id) is not None
    if not args.apply:
        print(f"{args.tjanst}: finns (instans i {args.env}: {'ja' if har_instans else 'nej'})")
        return

    if not har_instans:
        _skapa_via_patch(svc["id"], env_id, gren, tj["rot"])
        project = state()
        svc = services_by_name(project)[args.tjanst]

    try:
        ensure_trigger(project, svc["id"], env_id, gren)
    except RuntimeError as fel:
        # Patchen skapar ibland triggern själv men den syns inte direkt —
        # samma uppmätta egenhet som i railway_bokforing.py.
        if "single deployment trigger" not in str(fel):
            raise
        time.sleep(3)
        ensure_trigger(state(), svc["id"], env_id, gren)

    instance_update(svc["id"], env_id, rootDirectory=tj["rot"])
    print(f"    rootDirectory: {tj['rot']}")

    domain = ensure_domain(svc["id"], env_id, svc)
    print(f"    domän: https://{domain}")

    store = env_read()
    api_url = store.get(f"{prefix}_API_URL")
    demo_key = store.get(f"{prefix}_DEMO_API_KEY")
    sso = store.get("RAILWAY_BOKFORING_SSO_SECRET")
    if not api_url or not demo_key or not sso:
        sys.exit(f"{prefix}_API_URL/_DEMO_API_KEY eller RAILWAY_BOKFORING_SSO_SECRET saknas i .env.deploy.")
    main_api = (store.get("RAILWAY_MAIN_API_URL") or "").rstrip("/")
    dev_api = (store.get("RAILWAY_DEVELOPMENT_API_URL") or "").rstrip("/")

    set_vars(svc["id"], env_id, {
        "SNAJP_SUPPORT_URL": api_url,
        "SNAJP_SUPPORT_TILLATNA": f"{main_api},{dev_api}",
        "SNAJP_AGENT_API_KEY": demo_key,
        "AGENTSAJT_SSO_SECRET": sso,
        "AGENTSAJT_LOSEN": LOSEN,
        "AGENTSAJT_EPOST": EPOST,
    })
    env_set(f"{prefix}_{args.tjanst.upper()}_URL", f"https://{domain}")

    deploy(svc["id"], env_id)
    print("    deploy startad")

    onskat = f"https://{domain}"
    if read_vars(WEB_SERVICE_ID, env_id).get(tj["extern_env"]) != onskat:
        set_vars(WEB_SERVICE_ID, env_id, {tj["extern_env"]: onskat})
        deploy(WEB_SERVICE_ID, env_id)
        print(f"    web: {tj['extern_env']} satt + omdeploy startad")
    else:
        print(f"    web: {tj['extern_env']} redan rätt")

    print(f"klart — {args.env} bygger; en push till {gren} deployar hädanefter.")


if __name__ == "__main__":
    main()
