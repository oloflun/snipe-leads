#!/usr/bin/env python3
"""Provisionera Railway-stacken — två miljöer, idempotent.

    python scripts/railway_provision.py                   # visa läget
    python scripts/railway_provision.py --apply           # båda miljöerna
    python scripts/railway_provision.py --apply --env development

Kör om den hur många gånger som helst. Motsvarigheten till render.yaml, fast
som ett kommando som faktiskt går att verifiera i stället för en blueprint som
visade sig inte existera.

Hemligheter läses ur .env.deploy och skrivs ALDRIG ut — varken till terminalen
eller till loggen. Nya hemligheter skrivs tillbaka till .env.deploy.
"""
from __future__ import annotations

import argparse
import base64
import secrets
import sys
from pathlib import Path

from railway import gql, REPO_ROOT

PROJECT_ID = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"
REPO = "oloflun/snipe-leads"
PG_IMAGE = "ghcr.io/railwayapp-templates/postgres-ssl:17"
ENV_DEPLOY = REPO_ROOT / ".env.deploy"

#: Miljö → gren. Grenen står HÄR och inte i en dashboard, av samma skäl som
#: render.yaml fick `branch:` efter två produktionsincidenter: fältet styr vad
#: som körs och syns annars inte i någon diff. INV-DEPLOY-002 vaktar det.
#:
#: `development` deployar sig SJÄLV sedan 2026-08-27 (Vercel är avvecklat, en
#: spegelgren för att trigga Railway är inte längre nödvändig). `main` pekar
#: fortfarande på `railway-main` med flit — samma omläggning för produktion är
#: ett separat, medvetet beslut som inte är taget än. Ändras `main` till att
#: deploya direkt: ta bort den raden i `DEPLOY.md`/`CLAUDE.md` som beskriver
#: den gamla tvåstegspushen dit, i SAMMA ändring som den här raden.
ENVIRONMENTS: dict[str, str] = {
    "main": "railway-main",
    "development": "development",
}

#: Hemligheter som MÅSTE skilja sig mellan miljöerna. En delad post här är tyst
#: korskoppling: samma AUTH_SECRET betyder att en sessionscookie utfärdad i dev
#: är giltig i main, och samma demo-nyckel betyder att en dev-frontend kan tala
#: med main-backenden utan att någon märker det.
#:
#: LLM-nycklarna står med sedan 2026-08-24. De var delade mellan main och
#: development, och delade därför KVOT: ett demo-anrop i dev slog i taket och
#: nästa anrop i produktionen hade fått samma 429. En hemlighet som är gemensam
#: är en felkälla som är gemensam, även när den inte är en behörighetsfråga.
PER_ENV_SECRETS = ("PG_PASSWORD", "APP_PASSWORD", "WEB_PASSWORD",
                   "MASTER_API_KEY", "DEMO_API_KEY", "AUTH_SECRET",
                   "GEMINI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY")

#: Gamla, omiljöade namn i .env.deploy. De tillhör main, som redan kör med dem —
#: att rotera hade tagit ner den tjänst skriptet ska provisionera.
LEGACY_MAIN = {
    "PG_PASSWORD": "RAILWAY_PG_PASSWORD",
    "APP_PASSWORD": "SNAJP_APP_PASSWORD",
    "WEB_PASSWORD": "SNAJP_WEB_PASSWORD",
    "MASTER_API_KEY": "RAILWAY_SNAJP_MASTER_API_KEY",
    "AUTH_SECRET": "RAILWAY_AUTH_SECRET",
}


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


def secret(env_name: str, name: str, generator=None) -> str:
    """Hämta (eller skapa) en miljöspecifik hemlighet.

    För `main` ärvs det gamla omiljöade namnet om det finns — main kör redan med
    det värdet, och en rotation hade tagit ner tjänsten mitt i provisioneringen.
    """
    store = env_read()
    key = f"RAILWAY_{env_name.upper()}_{name}"
    if key in store and store[key]:
        return store[key]
    legacy = LEGACY_MAIN.get(name) if env_name == "main" else None
    if legacy and store.get(legacy):
        env_set(key, store[legacy])
        return store[legacy]
    value = (generator or (lambda: secrets.token_urlsafe(32)))()
    env_set(key, value)
    return value


# --- Railway ----------------------------------------------------------------

STATE = """
query($id: String!) {
  project(id: $id) {
    environments { edges { node { id name } } }
    services { edges { node { id name
      serviceInstances { edges { node {
        environmentId rootDirectory dockerfilePath healthcheckPath
        domains { serviceDomains { domain } }
        latestDeployment { status meta }
        source { image repo }
      } } }
    } } }
    volumes { edges { node { id volumeInstances { edges { node { serviceId environmentId } } } } } }
    deploymentTriggers { edges { node { id branch repository environmentId serviceId } } }
  }
}
"""


def state() -> dict:
    return gql(STATE, {"id": PROJECT_ID})["project"]


def envs_by_name(project: dict) -> dict[str, str]:
    return {e["node"]["name"]: e["node"]["id"] for e in project["environments"]["edges"]}


def services_by_name(project: dict) -> dict[str, dict]:
    return {s["node"]["name"]: s["node"] for s in project["services"]["edges"]}


def instance(service: dict, env_id: str) -> dict | None:
    for i in service["serviceInstances"]["edges"]:
        if i["node"]["environmentId"] == env_id:
            return i["node"]
    return None


def set_vars(service_id: str, env_id: str, variables: dict[str, str]) -> None:
    gql(
        "mutation($in: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $in) }",
        {"in": {"projectId": PROJECT_ID, "environmentId": env_id, "serviceId": service_id,
                "variables": variables, "replace": False}},
    )
    print(f"    variabler: {', '.join(sorted(variables))}")


def instance_update(service_id: str, env_id: str, **fields) -> None:
    gql(
        "mutation($sid: String!, $eid: String!, $in: ServiceInstanceUpdateInput!) {"
        " serviceInstanceUpdate(serviceId: $sid, environmentId: $eid, input: $in) }",
        {"sid": service_id, "eid": env_id, "in": fields},
    )


def deploy(service_id: str, env_id: str) -> str:
    return gql(
        "mutation($sid: String!, $eid: String!) {"
        " serviceInstanceDeployV2(serviceId: $sid, environmentId: $eid) }",
        {"sid": service_id, "eid": env_id},
    )["serviceInstanceDeployV2"]


def ensure_domain(service_id: str, env_id: str, service: dict) -> str:
    inst = instance(service, env_id) or {}
    existing = (inst.get("domains") or {}).get("serviceDomains") or []
    if existing:
        return existing[0]["domain"]
    res = gql(
        "mutation($sid:String!,$eid:String!){ serviceDomainCreate(input:{serviceId:$sid, environmentId:$eid}){ domain } }",
        {"sid": service_id, "eid": env_id},
    )
    return res["serviceDomainCreate"]["domain"]


def read_vars(service_id: str, env_id: str) -> dict[str, str]:
    """Läser ALLA satta variabler för en tjänst i en miljö.

    Samma GraphQL-fråga `private_domain()` redan använde för Postgres — bruten
    ut hit så `provision()` kan läsa `api`s variabler INNAN den skriver i
    stället för att anta att fältet är tomt (snipe-u70).
    """
    return gql(
        "query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }",
        {"p": PROJECT_ID, "e": env_id, "s": service_id},
    )["variables"]


def private_domain(service_id: str, env_id: str) -> str:
    """Postgres privata värdnamn i EN miljö.

    Läses ut och skrivs som ett LITERALT värde i DATABASE_URL. Referensformen
    `${{Postgres.RAILWAY_PRIVATE_DOMAIN}}` löses inte ut i en klonad miljö —
    uppmätt: api startade med `storage: memory`, och omdeploy hjälpte inte.
    """
    host = read_vars(service_id, env_id).get("RAILWAY_PRIVATE_DOMAIN")
    if not host:
        sys.exit("Postgres saknar RAILWAY_PRIVATE_DOMAIN — miljön är inte färdigprovisionerad.")
    return host


def ensure_trigger(project: dict, service_id: str, env_id: str, branch: str) -> None:
    """Gren per miljö. Bärs av deployment-triggern, inte av serviceConnect.

    serviceConnect sätter tjänstens default-gren och gäller ALLA miljöer.
    Triggern är den enda som är miljöspecifik, och det var den som saknades när
    web byggde `development` i tre deployer i rad medan felsökningen letade i
    byggkontexten.
    """
    for t in project["deploymentTriggers"]["edges"]:
        n = t["node"]
        if n["serviceId"] == service_id and n["environmentId"] == env_id:
            if n["branch"] != branch:
                gql(
                    "mutation($id:String!,$in:DeploymentTriggerUpdateInput!){ deploymentTriggerUpdate(id:$id, input:$in){ id branch } }",
                    {"id": n["id"], "in": {"branch": branch}},
                )
                print(f"    gren: {n['branch']} -> {branch}")
            else:
                print(f"    gren: {branch}")
            return
    gql(
        "mutation($in:DeploymentTriggerCreateInput!){ deploymentTriggerCreate(input:$in){ id } }",
        {"in": {"projectId": PROJECT_ID, "environmentId": env_id, "serviceId": service_id,
                "provider": "github", "repository": REPO, "branch": branch}},
    )
    print(f"    gren: {branch} (trigger skapad)")


# --- Provisionering per miljö ------------------------------------------------

def provision(env_name: str, branch: str, apply: bool) -> None:
    print(f"\n=== {env_name}  ({branch})")
    project = state()
    environments = envs_by_name(project)

    if env_name not in environments:
        if not apply:
            print(f"  miljön SAKNAS (kör med --apply)")
            return
        source = environments.get("main")
        if not source:
            sys.exit("Kan inte skapa en miljö utan en källmiljö `main`.")
        res = gql(
            "mutation($in: EnvironmentCreateInput!){ environmentCreate(input:$in){ id name } }",
            {"in": {"projectId": PROJECT_ID, "name": env_name, "sourceEnvironmentId": source,
                    "skipInitialDeploys": True, "stageInitialChanges": False}},
        )
        print(f"  miljön SKAPAD ({res['environmentCreate']['id']})")
        project = state()
        environments = envs_by_name(project)

    env_id = environments[env_name]
    services = services_by_name(project)
    for name in ("Postgres", "api", "web"):
        if name not in services:
            sys.exit(f"Tjänsten {name} saknas i projektet — kör provisioneringen för main först.")

    if not apply:
        for name in ("Postgres", "api", "web"):
            inst = instance(services[name], env_id)
            print(f"  {name}: {'finns' if inst else 'SAKNAS'}")
        return

    pg, api, web = services["Postgres"], services["api"], services["web"]

    # --- Postgres
    print("  Postgres")
    pg_password = secret(env_name, "PG_PASSWORD")
    set_vars(pg["id"], env_id, {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": pg_password,
        "POSTGRES_DB": "railway",
        "PGDATA": "/var/lib/postgresql/data/pgdata",
        "SSL_CERT_DAYS": "820",
    })
    has_volume = any(
        vi["node"]["serviceId"] == pg["id"] and vi["node"].get("environmentId") == env_id
        for v in project["volumes"]["edges"] for vi in v["node"]["volumeInstances"]["edges"]
    )
    if not has_volume:
        gql("mutation($in: VolumeCreateInput!){ volumeCreate(input:$in){ id } }",
            {"in": {"projectId": PROJECT_ID, "environmentId": env_id,
                    "serviceId": pg["id"], "mountPath": "/var/lib/postgresql/data"}})
        print("    volym skapad")

    # TCP-proxy: migrationskedjan och speglingen körs UTIFRÅN, inte inne i
    # containern. Utan den finns ingen väg in till en databas som bara har ett
    # privat värdnamn.
    store = env_read()
    if not store.get(f"RAILWAY_{env_name.upper()}_PG_HOST"):
        # En klonad miljö ärver källans proxy-konfiguration, så en proxy kan redan
        # finnas. Läs den i så fall i stället för att skapa en till (som failar).
        existing = gql(
            "query($s:String!,$e:String!){ tcpProxies(serviceId:$s, environmentId:$e){ domain proxyPort } }",
            {"s": pg["id"], "e": env_id},
        )["tcpProxies"]
        proxy = existing[0] if existing else gql(
            "mutation($sid:String!,$eid:String!){ tcpProxyCreate(input:{serviceId:$sid, environmentId:$eid, applicationPort:5432}){ domain proxyPort } }",
            {"sid": pg["id"], "eid": env_id},
        )["tcpProxyCreate"]
        env_set(f"RAILWAY_{env_name.upper()}_PG_HOST", proxy["domain"].rstrip("."))
        env_set(f"RAILWAY_{env_name.upper()}_PG_PORT", str(proxy["proxyPort"]))

    # --- api
    print("  api")
    ensure_trigger(project, api["id"], env_id, branch)
    instance_update(api["id"], env_id, rootDirectory="/",
                    dockerfilePath="snajp-support/Dockerfile", healthcheckPath="/health/live")
    api_domain = ensure_domain(api["id"], env_id, services["api"])
    app_password = secret(env_name, "APP_PASSWORD")
    pg_host = private_domain(pg["id"], env_id)
    api_vars = {
        "DATABASE_URL": f"postgresql://snajp_app:{app_password}@{pg_host}:5432/railway",
        "SNAJP_MASTER_API_KEY": secret(env_name, "MASTER_API_KEY",
                                       lambda: "snajp_master_" + secrets.token_urlsafe(24)),
        "SNAJP_DEMO_API_KEY": secret(env_name, "DEMO_API_KEY",
                                     lambda: "snajp_demo_" + secrets.token_urlsafe(16)),
        "INBOX_POLL_SECONDS": "0",
        "AUTO_SEND_MIN_CONFIDENCE": "0.75",
    }
    # snipe-u70: LLM_PROVIDER/MODEL skrevs tidigare OVILLKORLIGT här, VARJE
    # körning — även mot en redan provisionerad miljö. Mot main eller
    # development sätter "deepseek" den förbjudna providern (se CLAUDE.md,
    # Settings.llm_provider_fault) och tjänsten vägrar starta. Samma felklass
    # som scripts/keys.py:FIXED (kommentaren där pekar hit): predikatet är
    # satt/osatt, INTE looks_placeholder — ett providernamn är kort per
    # definition ("gemini" är sex tecken), så en längdheuristik hade skrivit
    # över ett redan valt värde också. De två raderna är bara ett startvärde
    # för en NY miljö som saknar provider helt; en befintlig miljös val rörs
    # aldrig.
    befintliga = read_vars(api["id"], env_id)
    for namn, startvarde in (("LLM_PROVIDER", "deepseek"), ("MODEL", "deepseek-v4-flash")):
        if not befintliga.get(namn, "").strip():
            api_vars[namn] = startvarde
    set_vars(api["id"], env_id, api_vars)

    # --- web
    print("  web")
    ensure_trigger(project, web["id"], env_id, branch)
    instance_update(web["id"], env_id, rootDirectory="/", healthcheckPath="/api/health")
    web_domain = ensure_domain(web["id"], env_id, services["web"])
    web_password = secret(env_name, "WEB_PASSWORD")
    set_vars(web["id"], env_id, {
        "AUTH_SECRET": secret(env_name, "AUTH_SECRET",
                              lambda: base64.b64encode(secrets.token_bytes(32)).decode()),
        "AUTH_TRUST_HOST": "true",
        "DATABASE_URL": f"postgresql://snajp_web:{web_password}@{pg_host}:5432/railway",
        # Peer-URL:erna pekar på SAMMA miljös tjänster. En dev-frontend som
        # talar med main-backenden är den sortens tysta korskoppling som gör
        # att "det funkade i dev" slutar betyda något.
        "NEXT_PUBLIC_SITE_URL": f"https://{web_domain}",
        "SNAJP_SUPPORT_URL": f"https://{api_domain}",
        "SNAJP_INTERNAL_API_KEY": secret(env_name, "DEMO_API_KEY"),
        "SNAJP_MASTER_API_KEY": secret(env_name, "MASTER_API_KEY"),
    })

    env_set(f"RAILWAY_{env_name.upper()}_API_URL", f"https://{api_domain}")
    env_set(f"RAILWAY_{env_name.upper()}_WEB_URL", f"https://{web_domain}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--env", choices=sorted(ENVIRONMENTS), help="bara en miljö")
    args = ap.parse_args()

    project = state()
    environments = envs_by_name(project)
    # Miljön hette `production` när det bara fanns en. Namnet `main` speglar
    # grenen den följer, vilket är det enda som gör de två miljöerna åtskiljbara
    # i ett API-svar.
    if "production" in environments and "main" not in environments:
        if args.apply:
            gql("mutation($id:String!,$in:EnvironmentRenameInput!){ environmentRename(id:$id, input:$in){ id name } }",
                {"id": environments["production"], "in": {"name": "main"}})
            print("miljön production -> main")
        else:
            print("miljön `production` skulle byta namn till `main`")

    targets = [args.env] if args.env else list(ENVIRONMENTS)
    for name in targets:
        provision(name, ENVIRONMENTS[name], args.apply)

    if not args.apply:
        print("\nInget ändrat. Kör med --apply.")


if __name__ == "__main__":
    main()
