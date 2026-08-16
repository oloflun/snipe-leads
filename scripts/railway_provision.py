#!/usr/bin/env python3
"""Provisionera Railway-stacken: Postgres + api + web, idempotent.

Kör om den hur många gånger som helst — den skapar bara det som saknas och
uppdaterar det som skiljer sig. Motsvarigheten till render.yaml, fast som ett
kommando som faktiskt går att verifiera i stället för en blueprint som visade
sig inte existera.

    python scripts/railway_provision.py              # visa vad som finns
    python scripts/railway_provision.py --apply      # skapa/uppdatera

Hemligheter läses ur .env.deploy och skrivs aldrig ut. Nya hemligheter (t.ex.
Postgres-lösenordet) skrivs TILLBAKA till .env.deploy, inte till terminalen.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from railway import gql, REPO_ROOT

PROJECT_ID = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"
ENV_ID = "47bc7047-a458-404b-a1de-ccec612cb96e"
BRANCH = "feature/railway-stack"
REPO = "oloflun/snipe-leads"
PG_IMAGE = "ghcr.io/railwayapp-templates/postgres-ssl:17"
ENV_DEPLOY = REPO_ROOT / ".env.deploy"


# --- .env.deploy -------------------------------------------------------------

def env_read() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_DEPLOY.exists():
        for line in ENV_DEPLOY.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def env_set(key: str, value: str) -> None:
    """Skriv en hemlighet till .env.deploy utan att echa den."""
    lines = ENV_DEPLOY.read_text(encoding="utf-8").splitlines() if ENV_DEPLOY.exists() else []
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    ENV_DEPLOY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  .env.deploy: {key} satt ({len(value)} tecken)")


# --- Railway ----------------------------------------------------------------

STATE = """
query($id: String!) {
  project(id: $id) {
    services { edges { node { id name
      serviceInstances { edges { node {
        environmentId rootDirectory dockerfilePath healthcheckPath startCommand
        source { image repo }
      } } }
    } } }
    volumes { edges { node { id name volumeInstances { edges { node { serviceId mountPath } } } } } }
  }
}
"""


def state() -> tuple[dict[str, dict], set[str]]:
    """Returnerar (tjänster per namn, service-id:n som redan har en volym)."""
    data = gql(STATE, {"id": PROJECT_ID})
    services = {e["node"]["name"]: e["node"] for e in data["project"]["services"]["edges"]}
    with_volume = {
        vi["node"]["serviceId"]
        for v in data["project"]["volumes"]["edges"]
        for vi in v["node"]["volumeInstances"]["edges"]
        if vi["node"].get("serviceId")
    }
    return services, with_volume


def ensure_service(services: dict, name: str, source: dict, apply: bool) -> str | None:
    if name in services:
        print(f"  {name}: finns ({services[name]['id']})")
        return services[name]["id"]
    if not apply:
        print(f"  {name}: SAKNAS (kör med --apply)")
        return None
    res = gql(
        "mutation($in: ServiceCreateInput!) { serviceCreate(input: $in) { id name } }",
        {"in": {"projectId": PROJECT_ID, "environmentId": ENV_ID, "name": name, "source": source}},
    )
    sid = res["serviceCreate"]["id"]
    print(f"  {name}: SKAPAD ({sid})")
    return sid


def set_vars(service_id: str, variables: dict[str, str]) -> None:
    gql(
        "mutation($in: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $in) }",
        {"in": {
            "projectId": PROJECT_ID,
            "environmentId": ENV_ID,
            "serviceId": service_id,
            "variables": variables,
            "replace": False,
        }},
    )
    print(f"  variabler satta: {', '.join(sorted(variables))}")


def instance_update(service_id: str, **fields) -> None:
    gql(
        "mutation($sid: String!, $eid: String!, $in: ServiceInstanceUpdateInput!) {"
        " serviceInstanceUpdate(serviceId: $sid, environmentId: $eid, input: $in) }",
        {"sid": service_id, "eid": ENV_ID, "in": fields},
    )


def deploy(service_id: str) -> str:
    res = gql(
        "mutation($sid: String!, $eid: String!) {"
        " serviceInstanceDeployV2(serviceId: $sid, environmentId: $eid) }",
        {"sid": service_id, "eid": ENV_ID},
    )
    return res["serviceInstanceDeployV2"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    env = env_read()
    services, with_volume = state()

    print("Postgres")
    pg_id = ensure_service(services, "Postgres", {"image": PG_IMAGE}, args.apply)
    if pg_id and args.apply:
        pw = env.get("RAILWAY_PG_PASSWORD") or secrets.token_urlsafe(32)
        if "RAILWAY_PG_PASSWORD" not in env:
            env_set("RAILWAY_PG_PASSWORD", pw)
        set_vars(pg_id, {
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": pw,
            "POSTGRES_DB": "railway",
            "PGDATA": "/var/lib/postgresql/data/pgdata",
            "SSL_CERT_DAYS": "820",
        })
        if pg_id not in with_volume:
            gql(
                "mutation($in: VolumeCreateInput!) { volumeCreate(input: $in) { id } }",
                {"in": {"projectId": PROJECT_ID, "environmentId": ENV_ID,
                        "serviceId": pg_id, "mountPath": "/var/lib/postgresql/data"}},
            )
            print("  volym skapad: /var/lib/postgresql/data")

    print("api")
    api_id = ensure_service(services, "api", {"repo": REPO}, args.apply)
    if api_id and args.apply:
        instance_update(api_id, rootDirectory="/", dockerfilePath="snajp-support/Dockerfile",
                        healthcheckPath="/health/live")
        print("  byggkontext: repo-roten, Dockerfile snajp-support/Dockerfile")

    print("web")
    web_id = ensure_service(services, "web", {"repo": REPO}, args.apply)
    if web_id and args.apply:
        # web byggs med railpack, INTE Docker: .dockerignore i repo-roten är en
        # allowlist som bara släpper in agent-core och snajp-support/app — ett
        # Docker-bygge från roten hade uteslutit hela Next-appen.
        instance_update(web_id, rootDirectory="/", healthcheckPath="/api/health")
        print("  byggkontext: repo-roten, railpack (ingen Dockerfile)")

    if not args.apply:
        print("\nInget ändrat. Kör med --apply.")


if __name__ == "__main__":
    sys.exit(main())
