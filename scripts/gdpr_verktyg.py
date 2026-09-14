"""Delad anslutning för dataskyddsskripten (gallra.py, gdpr_radera.py).

Samma miljö- och DSN-upplösning som scripts/admin_cleanup.py, brutet ut i
stället för kopierat: två skript som råkar bygga DSN:en olika är två skript
som kan träffa olika databaser med samma flagga, och den sortens fel upptäcks
efter raderingen.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"
BACKEND_ENV = ROOT / "snajp-support" / ".env"

ENVIRONMENTS = {
    "production": {"url_key": "DATABASE_URL", "env_files": [BACKEND_ENV, DEPLOY_ENV]},
    "preview": {"url_key": "PREVIEW_DATABASE_URL", "env_files": [DEPLOY_ENV]},
    "railway-main": {"railway_prefix": "RAILWAY_MAIN_", "env_files": [DEPLOY_ENV]},
    "railway-development": {
        "railway_prefix": "RAILWAY_DEVELOPMENT_",
        "env_files": [DEPLOY_ENV],
    },
}


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


def env_value(name: str, *paths: Path) -> str:
    if os.environ.get(name):
        return os.environ[name]
    for path in paths:
        value = read_env(path).get(name, "")
        if value:
            return value
    return ""


def dsn_for(env: str) -> str:
    """DSN:en för en miljö. Skriver ALDRIG ut lösenordet — se läckagespärren i
    CLAUDE.md; en `print(dsn)` under felsökning läcker lika mycket som ett echo."""
    if env not in ENVIRONMENTS:
        sys.exit(f"AVBRYTER: okänd miljö '{env}'. Välj: {', '.join(ENVIRONMENTS)}")
    cfg = ENVIRONMENTS[env]

    prefix = cfg.get("railway_prefix")
    if not prefix:
        varde = env_value(cfg["url_key"], *cfg["env_files"])
        if not varde:
            sys.exit(f"AVBRYTER: {cfg['url_key']} saknas. Lägg den i .env.deploy.")
        return varde

    delar = {
        del_: env_value(f"{prefix}PG_{del_}", *cfg["env_files"])
        for del_ in ("PASSWORD", "HOST", "PORT")
    }
    saknas = [f"{prefix}PG_{k}" for k, v in delar.items() if not v]
    if saknas:
        sys.exit("AVBRYTER: " + ", ".join(saknas) + " saknas i .env.deploy.")
    return f"postgresql://postgres:{delar['PASSWORD']}@{delar['HOST']}:{delar['PORT']}/railway"
