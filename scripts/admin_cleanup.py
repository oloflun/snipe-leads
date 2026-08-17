#!/usr/bin/env python
"""Rensa plattformsadmin — snajpsupport@gmail.com är den ENDA adminen.

    python scripts/admin_cleanup.py --env preview
    python scripts/admin_cleanup.py --env production

Gör fem saker, idempotent, mot EN miljö i taget:

  1. Säkerställer att `snajpsupport@gmail.com` finns i auth.users. Saknas den
     skapas den med en scrypt-hash (samma format som lib/password.ts) — lösenordet
     läses ur SNAJP_ADMIN_PASSWORD (eller via getpass), aldrig ur shell-historiken.
  2. Raderar alla platform_admins-rader utom snajpsupport (t.ex. Sebastians konto).
  3. Sätter snajpsupport i platform_admins.
  4. Sätter display-namnet "Snajp Admin" i både auth.users och profiles.
  5. Säkerställer att workspacen har products = ['leads','support'].

Varför ett skript och inte en migration: att RÖRA en annan admin är en
dataåtgärd mot produktionen, och lösenordet ska aldrig stå i en migration som
committas. Det här körs mot en riktig databas via psycopg2 (auth-schemat nås
inte via Supabases REST-API).

Idempotent: varje steg är en upsert/delete med villkor, så det går att köra om.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"
BACKEND_ENV = ROOT / "snajp-support" / ".env"

ADMIN_EMAIL = "snajpsupport@gmail.com"
ADMIN_NAME = "Snajp Admin"

#: Vilken DATABASE_URL varje miljö använder. Produktionen läser snajp-support/.env
#: (backendens egen anslutning), preview läser .env.deploy (PREVIEW_DATABASE_URL).
ENVIRONMENTS = {
    "production": {"url_key": "DATABASE_URL", "env_files": [BACKEND_ENV, DEPLOY_ENV]},
    "preview": {"url_key": "PREVIEW_DATABASE_URL", "env_files": [DEPLOY_ENV]},
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
    """Läser en variabel ur miljön först, sedan ur env-filerna i tur och ordning."""
    if os.environ.get(name):
        return os.environ[name]
    for path in paths:
        value = read_env(path).get(name, "")
        if value:
            return value
    return ""


def scrypt_hash(password: str) -> str:
    """Samma format som lib/password.ts: scrypt$<N>$<salt>$<hash>.

    `1` i formatet är en format-version; Node använder sina defaultparametrar
    n=16384, r=8, p=1, dklen=64 — och det gör vi här också, annars kan inte
    verifyPassword() i lib/password.ts läsa hashen.
    """
    salt = os.urandom(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
    return f"scrypt$1${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Rensa plattformsadmin.")
    parser.add_argument(
        "--env", choices=sorted(ENVIRONMENTS), default="preview",
        help="Miljö att rensa (default: preview)",
    )
    args = parser.parse_args()

    cfg = ENVIRONMENTS[args.env]
    dsn = env_value(cfg["url_key"], *cfg["env_files"])
    if not dsn:
        sys.exit(f"AVBRYTER: {cfg['url_key']} saknas. Lägg den i .env.deploy / snajp-support/.env.")

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Hitta eller skapa kontot.
    cur.execute("select id from auth.users where lower(email) = lower(%s)", (ADMIN_EMAIL,))
    row = cur.fetchone()
    if row:
        user_id = row[0]
        print(f"  konto {ADMIN_EMAIL} finns redan ({user_id})")
    else:
        password = os.environ.get("SNAJP_ADMIN_PASSWORD") or getpass.getpass(
            f"Lösenord för {ADMIN_EMAIL} (nytt konto, syns aldrig): "
        )
        if not password:
            sys.exit("AVBRYTER: SNAJP_ADMIN_PASSWORD saknas och inget lösenord gavs.")
        # Inserten fyrar on_auth_user_created — triggern skapar workspace + profil.
        cur.execute(
            "insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at) "
            "values (%s, %s, jsonb_build_object('full_name', %s::text), now()) "
            "returning id",
            (ADMIN_EMAIL, scrypt_hash(password), ADMIN_NAME),
        )
        user_id = cur.fetchone()[0]
        print(f"  konto {ADMIN_EMAIL} skapades ({user_id})")

    # 2. Radera alla andra admins — det här är själva "koppla bort Sebbe"-steget.
    cur.execute("delete from public.platform_admins where user_id <> %s", (user_id,))
    if cur.rowcount:
        print(f"  raderade {cur.rowcount} övriga platform_admins")

    # 3. Säkerställ snajpsupport som admin.
    cur.execute(
        "insert into public.platform_admins (user_id) values (%s) on conflict (user_id) do nothing",
        (user_id,),
    )
    print(f"  {ADMIN_EMAIL} är platform_admin")

    # 4. Display-namnet — i både auth.users (sessionen) och profiles (arbetsytan).
    cur.execute(
        "update auth.users set raw_user_meta_data = raw_user_meta_data || "
        "jsonb_build_object('full_name', %s::text) where id = %s",
        (ADMIN_NAME, user_id),
    )
    cur.execute("update public.profiles set full_name = %s where id = %s", (ADMIN_NAME, user_id))
    print(f"  display-namn: {ADMIN_NAME}")

    # 5. Produkterna — admin ska kunna köra Snajps egen agent och support-inkorgen.
    cur.execute(
        "update public.workspaces set products = array['leads','support']::text[] "
        "from public.profiles p where workspaces.id = p.workspace_id and p.id = %s",
        (user_id,),
    )
    print("  workspace-produkter: leads, support")

    conn.close()
    print("Klart.")


if __name__ == "__main__":
    main()
