#!/usr/bin/env python3
"""Sätt upp driftjobben som tjänster hos Railway. Går att köra om.

    python scripts/railway_driftjobb.py                      # visa läget och planen, ändra inget
    python scripts/railway_driftjobb.py --apply              # skapa och konfigurera det som saknas
    python scripts/railway_driftjobb.py --apply --bara synk  # ett jobb i taget

## Varför skriptet finns

Synken, migrationerna och övervakningen låg på GitHub Actions. 2026-11-23
slutade GitHub starta jobb för repot, och då stod alla tre still: ingen
spegling till development, inga migrationer vid merge och ingen som larmade
om produktionen gick ner. Planen för flytten fanns redan
(docs/compliance/synkflytt-plan.md) men var en lista handgrepp i runbooken.
Det här är handgreppen som ett kommando (Anton 2026-11-23: "Gör vad som krävs
för att få alla jobben i drift på Railway").

## Jobben

| Tjänst         | Miljö       | Gren        | Körs                     |
|----------------|-------------|-------------|--------------------------|
| `migrera`      | development | development | vid deploy (fanns redan) |
| `migrera-main` | main        | main        | vid deploy               |
| `synk`         | main        | main        | var tionde minut         |
| `overvakning`  | development | development | var femtonde minut       |

Alla bygger `railway/Dockerfile.drift` och startar `scripts/railway_drift.py`.
`migrera-main` är en egen tjänst därför att en tjänst hos Railway bara finns i
miljön den skapades i, samma mönster som `Redis` och `Redis-main`.

## Ordningen per tjänst

1. Tjänsten skapas tom (utan källa), så att inget byggs innan den är inställd.
2. Bygge, startkommando, schema, omstart och region ställs in.
3. Variablerna skrivs. Här skrivs bara referenser till andra tjänsters
   variabler (`${{Postgres.POSTGRES_PASSWORD}}`), aldrig ett hemligt värde.
4. Repot kopplas och grenens trigger skapas. Då byggs och körs tjänsten.

Synkens två anslutningar skrivs inte här: de bär ett nytt lösenord som skapas
och går direkt till databasen och Railway i `scripts/railway_synk_anslut.py`.

`MIGRERA_APPLY` och `SYNK_APPLY` sätts inte heller här. Utan dem torrkör
jobben. De slås på med `--skarp`, efter att torrkörningen är läst.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway import gql  # noqa: E402
from railway_provision import (  # noqa: E402
    PROJECT_ID, REPO, ensure_trigger, envs_by_name, instance, instance_update, read_vars,
    services_by_name, set_vars, state,
)

AVBILD = "railway/Dockerfile.drift"
GEMENSAMT = ["scripts/railway_drift.py", AVBILD]

JOBB: dict[str, dict] = {
    "migrera-main": {
        "miljo": "main", "gren": "main",
        "start": "python scripts/railway_drift.py migrera", "cron": None,
        "bevakar": ["db/migrations/**", "railway/000_auth_compat.sql", "scripts/railway_migrate.py", *GEMENSAMT],
        "variabler": {
            "MIGRERA_PG_URL": "postgresql://postgres:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/railway",
        },
        "skarp": {"MIGRERA_APPLY": "1"},
    },
    "synk": {
        "miljo": "main", "gren": "main",
        "start": "python scripts/railway_drift.py synk", "cron": "*/10 * * * *",
        "bevakar": ["scripts/railway_synk.py", "scripts/begransning_spegel.py", *GEMENSAMT],
        # SYNK_MAIN_PG_URL och SYNK_DEVELOPMENT_PG_URL: scripts/railway_synk_anslut.py.
        "variabler": {},
        "skarp": {"SYNK_APPLY": "1"},
    },
    "overvakning": {
        "miljo": "development", "gren": "development",
        "start": "python scripts/railway_drift.py overvakning", "cron": "*/15 * * * *",
        "bevakar": ["scripts/overvakning.py", *GEMENSAMT],
        "variabler": {
            "RESEND_API_KEY": "${{api.RESEND_API_KEY}}",
            "LARM_FRAN": "${{api.SMTP_FROM}}",
            # Plattformens egen brevlåda för prioriterade mejl (config.py).
            "LARM_TILL": "snajpsupport@gmail.com",
        },
        "skarp": {},
    },
}

LAGE = """query($s:String!,$e:String!){ serviceInstance(serviceId:$s, environmentId:$e){
  startCommand cronSchedule restartPolicyType dockerfilePath rootDirectory watchPatterns
  source { repo } latestDeployment { status createdAt meta } } }"""


def onskat(jobb: dict) -> dict:
    """Ren funktion: instansens inställningar för ett jobb."""
    return {
        "rootDirectory": "/",
        "dockerfilePath": AVBILD,
        "startCommand": jobb["start"],
        "cronSchedule": jobb["cron"],
        "restartPolicyType": "NEVER",
        "watchPatterns": jobb["bevakar"],
    }


def skillnad(nu: dict | None, vill: dict) -> dict:
    """Ren funktion: de inställningar som måste skrivas."""
    nu = nu or {}
    return {k: v for k, v in vill.items() if (nu.get(k) or None) != (v or None)}


def region(projekt: dict, miljo_id: str) -> dict | None:
    """Samma region som api i miljön (Amsterdam), läst ur dess senaste deploy."""
    api = services_by_name(projekt)["api"]
    i = gql(LAGE, {"s": api["id"], "e": miljo_id})["serviceInstance"]
    meta = ((i.get("latestDeployment") or {}).get("meta") or {}).get("serviceManifest") or {}
    return (meta.get("deploy") or {}).get("multiRegionConfig") or None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="skapa och konfigurera (annars visas bara planen)")
    ap.add_argument("--skarp", action="store_true", help="slå på skrivningen (MIGRERA_APPLY, SYNK_APPLY) för valda jobb")
    ap.add_argument("--bara", choices=sorted(JOBB), action="append", help="bara det här jobbet (kan upprepas)")
    args = ap.parse_args()
    valda = args.bara or sorted(JOBB)

    projekt = state()
    miljoer = envs_by_name(projekt)
    for namn in valda:
        jobb = JOBB[namn]
        miljo_id = miljoer[jobb["miljo"]]
        tjanst = services_by_name(projekt).get(namn)
        finns = bool(tjanst and instance(tjanst, miljo_id))
        print(f"\n{namn} ({jobb['miljo']}, gren {jobb['gren']}, {jobb['cron'] or 'vid deploy'})")
        if tjanst and not finns:
            print(f"  STOPP: tjänsten {namn} finns men inte i miljön {jobb['miljo']}. Rör den inte härifrån.")
            continue
        if not finns:
            print("  tjänsten saknas" + (": skapas" if args.apply else " (skulle skapas)"))
            if not args.apply:
                continue
            tjanst = gql(
                "mutation($in: ServiceCreateInput!){ serviceCreate(input:$in){ id name } }",
                {"in": {"projectId": PROJECT_ID, "name": namn, "environmentId": miljo_id}},
            )["serviceCreate"]
            print(f"  skapad: {tjanst['name']}")
        sid = tjanst["id"]

        nu = gql(LAGE, {"s": sid, "e": miljo_id})["serviceInstance"]
        andra = skillnad(nu, onskat(jobb))
        print("  inställningar: " + (", ".join(sorted(andra)) + (" skrivs" if args.apply else " (skulle skrivas)") if andra else "stämmer"))
        if andra and args.apply:
            instance_update(sid, miljo_id, **andra)

        satta = read_vars(sid, miljo_id)
        saknas = {n: v for n, v in jobb["variabler"].items() if not satta.get(n)}
        print("  variabler: " + (", ".join(sorted(saknas)) + (" skrivs" if args.apply else " (skulle skrivas)") if saknas else "stämmer"))
        if saknas and args.apply:
            set_vars(sid, miljo_id, saknas)

        # Grenens trigger räknas också: instansens `source` var tom för
        # overvakning i development fast tjänsten byggde ur repot (2026-11-23).
        kopplad = bool((nu.get("source") or {}).get("repo")) or any(
            t["node"]["serviceId"] == sid and t["node"]["environmentId"] == miljo_id
            for t in projekt["deploymentTriggers"]["edges"]
        )
        print("  källa: " + ("kopplad" if kopplad else "kopplas" if args.apply else "(skulle kopplas)"))
        if args.apply:
            if not kopplad:
                # Regionen sätts före första bygget, så att tjänsten aldrig
                # startar utanför EU.
                reg = region(projekt, miljo_id)
                if reg:
                    instance_update(sid, miljo_id, multiRegionConfig=reg)
                    print(f"  region: {', '.join(reg)}")
                gql(
                    "mutation($id:String!,$in:ServiceConnectInput!){ serviceConnect(id:$id, input:$in){ id } }",
                    {"id": sid, "in": {"repo": REPO, "branch": jobb["gren"]}},
                )
            ensure_trigger(state(), sid, miljo_id, jobb["gren"])

        if args.skarp and jobb["skarp"]:
            fattas = {n: v for n, v in jobb["skarp"].items() if satta.get(n) != v}
            print("  skrivning: " + ("redan på" if not fattas else "slås på" if args.apply else "(skulle slås på)"))
            if fattas and args.apply:
                set_vars(sid, miljo_id, fattas)
        elif jobb["skarp"]:
            pa = all(satta.get(n) == v for n, v in jobb["skarp"].items())
            print("  skrivning: " + ("på" if pa else "av (torrkör)"))

        senaste = (gql(LAGE, {"s": sid, "e": miljo_id})["serviceInstance"].get("latestDeployment") or {})
        if senaste:
            print(f"  senaste körning: {senaste.get('status')} {str(senaste.get('createdAt'))[:16]}")
    if not args.apply:
        print("\nInget ändrat. Kör med --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
