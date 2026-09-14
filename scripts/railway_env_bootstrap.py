#!/usr/bin/env python3
"""Återskapa .env.deploy ur Railway — en token in, hela nyckelknippan ut.

    python scripts/railway_env_bootstrap.py                    # visa vad som saknas
    python scripts/railway_env_bootstrap.py --apply            # skriv .env.deploy
    python scripts/railway_env_bootstrap.py --apply --env development

## Varför den finns

`.env.deploy` är gitignorerad, alltså följer den inte med en klon. En agent
eller en ny maskin som checkar ut repot har därför INGA av de sex värden per
miljö som `railway_migrate.py`, `admin_cleanup.py`, `railway_seed_dev.py` och
`verify_railway.py` läser — och varenda ett av dem finns redan i Railway.

Fällan den stänger: `railway_provision.py --apply` GENERERAR en ny hemlighet
när den inte hittar den i `.env.deploy` (`secret()`), och skriver den till
tjänsten. Kört från en maskin utan filen roterar den alltså Postgres-lösenordet
under en levande stack. Det här skriptet läser i stället, och skriver bara till
filen.

Riktningen är envägs med flit: Railway → .env.deploy. Ingenting härifrån ändrar
något i Railway.

## Leakagespärr

Värdena passerar aldrig terminalen. `env_set()` skriver namnet och längden,
aldrig innehållet, och den regeln gäller även felutskrifter: en hemlighet som
läcker i ett felmeddelande är lika läckt som en som echades.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway import gql  # noqa: E402
from railway_provision import (  # noqa: E402
    ENVIRONMENTS,
    PROJECT_ID,
    env_read,
    env_set,
    envs_by_name,
    instance,
    services_by_name,
    state,
)

VARS = "query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }"
PROXIES = "query($s:String!,$e:String!){ tcpProxies(serviceId:$s, environmentId:$e){ domain proxyPort } }"


def service_vars(service_id: str, env_id: str) -> dict[str, str]:
    return gql(VARS, {"p": PROJECT_ID, "e": env_id, "s": service_id})["variables"] or {}


def password_of(dsn: str) -> str | None:
    """Lösenordet ur en postgresql://-URL, procent-avkodat."""
    if not dsn:
        return None
    pw = urlsplit(dsn).password
    return unquote(pw) if pw else None


def collect(env_name: str, project: dict) -> dict[str, str]:
    """Alla .env.deploy-värden för en miljö, lästa ur Railway."""
    env_id = envs_by_name(project).get(env_name)
    if not env_id:
        sys.exit(f"Miljön {env_name} finns inte i projektet.")
    services = services_by_name(project)
    for name in ("Postgres", "api", "web"):
        if name not in services:
            sys.exit(f"Tjänsten {name} saknas i projektet.")

    pg_vars = service_vars(services["Postgres"]["id"], env_id)
    api_vars = service_vars(services["api"]["id"], env_id)
    web_vars = service_vars(services["web"]["id"], env_id)

    p = f"RAILWAY_{env_name.upper()}_"
    found: dict[str, str] = {}

    if pg_vars.get("POSTGRES_PASSWORD"):
        found[f"{p}PG_PASSWORD"] = pg_vars["POSTGRES_PASSWORD"]

    # TCP-proxyn är den enda vägen in utifrån: den privata domänen går inte att
    # nå från en migrationskörning som inte kör inne i containern.
    proxies = gql(PROXIES, {"s": services["Postgres"]["id"], "e": env_id})["tcpProxies"] or []
    if proxies:
        found[f"{p}PG_HOST"] = proxies[0]["domain"].rstrip(".")
        found[f"{p}PG_PORT"] = str(proxies[0]["proxyPort"])

    # Approllernas lösenord bor inte som egna variabler — de är inbakade i
    # tjänsternas DATABASE_URL. Att läsa dem därifrån är att läsa det värde som
    # faktiskt används, inte ett som borde stämma.
    if app_pw := password_of(api_vars.get("DATABASE_URL", "")):
        found[f"{p}APP_PASSWORD"] = app_pw
    if web_pw := password_of(web_vars.get("DATABASE_URL", "")):
        found[f"{p}WEB_PASSWORD"] = web_pw

    if api_vars.get("SNAJP_MASTER_API_KEY"):
        found[f"{p}MASTER_API_KEY"] = api_vars["SNAJP_MASTER_API_KEY"]
    if api_vars.get("SNAJP_DEMO_API_KEY"):
        found[f"{p}DEMO_API_KEY"] = api_vars["SNAJP_DEMO_API_KEY"]
    if web_vars.get("AUTH_SECRET"):
        found[f"{p}AUTH_SECRET"] = web_vars["AUTH_SECRET"]

    for key, service in ((f"{p}API_URL", "api"), (f"{p}WEB_URL", "web")):
        inst = instance(services[service], env_id)
        domains = (inst or {}).get("domains", {}).get("serviceDomains") or []
        if domains:
            found[key] = f"https://{domains[0]['domain']}"

    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="skriv till .env.deploy")
    ap.add_argument("--env", choices=sorted(ENVIRONMENTS), help="bara en miljö")
    args = ap.parse_args()

    project = state()
    store = env_read()
    names = [args.env] if args.env else sorted(ENVIRONMENTS)
    saknas = 0

    for env_name in names:
        print(f"\n{env_name}")
        found = collect(env_name, project)
        for key in sorted(found):
            har = bool(store.get(key))
            lika = har and store[key] == found[key]
            if args.apply and not lika:
                env_set(key, found[key])
            else:
                märke = "=" if lika else ("~" if har else "+")
                print(f"  {märke} {key}")
        # Ett värde som Railway inte kan svara på är inte ett fel här — det är
        # ett värde som aldrig sattes. Säg vilket, så slipper nästa läsare gissa.
        for key in (f"RAILWAY_{env_name.upper()}_{n}" for n in
                    ("PG_PASSWORD", "PG_HOST", "PG_PORT", "APP_PASSWORD", "WEB_PASSWORD",
                     "MASTER_API_KEY", "DEMO_API_KEY", "AUTH_SECRET")):
            if key not in found:
                saknas += 1
                print(f"  ! {key} — finns inte i Railway")

    if not args.apply:
        print("\n  = oförändrad, ~ skiljer sig, + ny. Kör om med --apply för att skriva.")
    return 1 if saknas else 0


if __name__ == "__main__":
    raise SystemExit(main())
