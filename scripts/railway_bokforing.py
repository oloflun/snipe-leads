#!/usr/bin/env python3
"""Provisionera tjänsten `bokforing` (bokforing-webb/) i Railway — idempotent.

    python scripts/railway_bokforing.py                        # visa läget
    python scripts/railway_bokforing.py --apply                # development
    python scripts/railway_bokforing.py --env main --apply     # produktion

Samma mönster som railway_provision.py: GraphQL via scripts/railway.py, token
och hemligheter ur .env.deploy, ingenting echas.

Tjänsten är den fristående bokföringsagent-sajten (Next-appen i
bokforing-webb/), byggd ur samma repo med rootDirectory=/bokforing-webb.
Gren per miljö: development bygger `development`, main bygger `main` — en
vanlig push deployar, precis som web och api.

## Två skapelsevägar, av API-nödvändighet

Första miljön skapas med `serviceCreate` (med environmentId — utan den
hamnar instansen i default-miljön, uppmätt). API:t saknar
serviceInstanceCreate, så en instans i YTTERLIGARE en miljö skapas i stället
via `environmentPatchCommit` med tjänstens config-block — samma väg som
dashboardens "New service". Skriptet väljer väg självt.

Sajten har ingen egen kundinloggning än; väggen är /logga-in i appen, styrd
av BOKFORING_EPOST/BOKFORING_LOSEN (förhandsversionens delade uppgifter,
beslutade av Sebbe 2026-09-15). Skriptet sätter också BOKFORING_EXTERN_URL
på web-tjänsten i samma miljö, vilket är det som får /dashboard/bokforing
att skicka inloggade kunder till sajten.
"""
from __future__ import annotations

import argparse
import sys

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

TJANST = "bokforing"
ROT = "/bokforing-webb"

#: Miljö → gren. Samma princip som railway_provision.ENVIRONMENTS: fältet
#: styr vad som körs och ska stå i kod, inte i en dashboard.
MILJOER: dict[str, str] = {
    "development": "development",
    "main": "main",
}

WEB_SERVICE_ID = "0261f633-1247-4d92-b5ab-40c2a1828b90"

#: Förhandsversionens inloggning — Sebbes beslut 2026-09-15, samma uppgifter
#: som QA-adminkontot (redan incheckade i scripts/qa_vyer.mjs, ingen ny
#: hemlighet). Byts när sajten får riktiga konton.
BOKFORING_EPOST = "Snajpsupport@gmail.com"
BOKFORING_LOSEN = "Snajpen123!"


def _skapa_via_patch(svc_id: str, env_id: str, gren: str) -> None:
    """Instans i en YTTERLIGARE miljö: config-patch, dashboardens egen väg.

    Blocket speglar det development-instansen fick av serviceCreate, med
    regionen satt explicit till ams — utan deploy-blocket hamnar en ny
    instans i default-regionen (USA), och resten av stacken kör Amsterdam.
    """
    patch = {
        "services": {
            svc_id: {
                "source": {"repo": REPO, "branch": gren,
                           "rootDirectory": ROT, "checkSuites": False},
                "build": {"builder": "RAILPACK", "buildEnvironment": "V3"},
                "deploy": {"runtime": "V2",
                           "multiRegionConfig": {"ams": {"numReplicas": 1}}},
            }
        }
    }
    # Städning i förbifarten: config-block för tjänster som inte längre finns
    # i projektet (serviceDelete lämnar dem kvar — uppmätt med det första,
    # felskapade bokforing-id:t d709e0c6).
    cfg = gql("query($id:String!){ environment(id:$id){ config } }",
              {"id": env_id})["environment"]["config"]
    levande = {s["node"]["id"] for s in state()["services"]["edges"]}
    for spoke in (cfg.get("services") or {}):
        if spoke not in levande:
            patch["services"][spoke] = None
            print(f"    spökpost i miljökonfigen tas bort: {spoke[:8]}…")
    gql(
        "mutation($e:String!,$p:EnvironmentConfig!,$m:String){"
        " environmentPatchCommit(environmentId:$e, patch:$p, commitMessage:$m) }",
        {"e": env_id, "p": patch, "m": f"bokforing i miljön (gren {gren})"},
    )
    print(f"    instans skapad via config-patch (gren {gren}, region ams)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--env", choices=sorted(MILJOER), default="development")
    args = ap.parse_args()
    gren = MILJOER[args.env]
    prefix = f"RAILWAY_{args.env.upper()}"

    project = state()
    env_id = envs_by_name(project).get(args.env)
    if not env_id:
        sys.exit(f"Miljön {args.env} saknas i projektet.")
    services = services_by_name(project)

    if TJANST not in services:
        if not args.apply:
            print(f"{TJANST}: SAKNAS (kör med --apply)")
            return
        gql(
            "mutation($in: ServiceCreateInput!){ serviceCreate(input:$in){ id name } }",
            # environmentId är INTE valfri kosmetika: utan den lägger Railway
            # instansen i projektets default-miljö — uppmätt.
            {"in": {"projectId": PROJECT_ID, "name": TJANST, "environmentId": env_id,
                    "source": {"repo": REPO}, "branch": gren}},
        )
        print(f"{TJANST}: tjänsten skapad")
        project = state()
        services = services_by_name(project)

    svc = services[TJANST]
    har_instans = instance(svc, env_id) is not None
    if not args.apply:
        print(f"{TJANST}: finns (instans i {args.env}: {'ja' if har_instans else 'nej'})")
        return

    if not har_instans:
        _skapa_via_patch(svc["id"], env_id, gren)
        project = state()
        services = services_by_name(project)
        svc = services[TJANST]

    # Gren per miljö bärs av deployment-triggern (se ensure_trigger i
    # railway_provision.py för varför serviceConnect inte räcker). Andra
    # miljöers triggers lämnas orörda — tjänsten är numera legitim i båda.
    #
    # Config-patchen ovan skapar ibland triggern SJÄLV, men den syns inte
    # direkt i projektläsningen — uppmätt: deploymentTriggerCreate föll på
    # "Only a single deployment trigger is allowed" trots färsk state().
    # Ett omtag med ny läsning hittar den och uppdaterar bara grenen.
    try:
        ensure_trigger(project, svc["id"], env_id, gren)
    except RuntimeError as fel:
        if "single deployment trigger" not in str(fel):
            raise
        import time

        time.sleep(3)
        ensure_trigger(state(), svc["id"], env_id, gren)
    instance_update(svc["id"], env_id, rootDirectory=ROT)
    print(f"    rootDirectory: {ROT}")

    domain = ensure_domain(svc["id"], env_id, svc)
    print(f"    domän: https://{domain}")

    store = env_read()
    api_url = store.get(f"{prefix}_API_URL")
    demo_key = store.get(f"{prefix}_DEMO_API_KEY")
    if not api_url or not demo_key:
        sys.exit(f"{prefix}_API_URL/_DEMO_API_KEY saknas i .env.deploy.")

    set_vars(svc["id"], env_id, {
        # Samma miljös backend — aldrig korskoppling (se provision() i
        # railway_provision.py för varför det är en regel och inte en smak).
        "SNAJP_SUPPORT_URL": api_url,
        "SNAJP_BOOKKEEPING_API_KEY": demo_key,
        "BOKFORING_EPOST": BOKFORING_EPOST,
        "BOKFORING_LOSEN": BOKFORING_LOSEN,
    })
    env_set(f"{prefix}_BOKFORING_URL", f"https://{domain}")
    env_set(f"{prefix}_BOKFORING_LOSEN", BOKFORING_LOSEN)

    # Sajten ska ha en deploy även om patchen inte startade någon själv.
    deploy(svc["id"], env_id)
    print("    deploy startad")

    # Inloggade kunder på webben skickas till sajten: BOKFORING_EXTERN_URL
    # på web-tjänsten i SAMMA miljö. Bara när värdet faktiskt ändras — och
    # då med omdeploy, eftersom processen läser miljön vid start.
    onskat = f"https://{domain}"
    if read_vars(WEB_SERVICE_ID, env_id).get("BOKFORING_EXTERN_URL") != onskat:
        set_vars(WEB_SERVICE_ID, env_id, {"BOKFORING_EXTERN_URL": onskat})
        deploy(WEB_SERVICE_ID, env_id)
        print("    web: BOKFORING_EXTERN_URL satt + omdeploy startad")
    else:
        print("    web: BOKFORING_EXTERN_URL redan rätt")

    print(f"klart — {args.env} bygger; en push till {gren} deployar hädanefter.")


if __name__ == "__main__":
    main()
