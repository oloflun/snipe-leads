#!/usr/bin/env python
"""Lägg upp en ny kund — allt som går att göra maskinellt, i ett anrop.

    python scripts/onboard_tenant.py --slug bolaget --name "Bolaget AB" --env preview

Före det här skriptet var rutinen elva manuella steg (TENANTS.md), och **två av
dem hade ingen kod alls**: ingenting i kodbasen skrev `workspaces.slug` eller
`ss_tenant_id`, och `scripts/keys.py --push` var i praktiken en no-op eftersom
nyckellistan inte innehöll några Vercel-nycklar. Följden var att en ny kund
kunde se helt korrekt ut i koden och ändå möta 409 eller 503 i drift.

Vad som INTE automatiseras, med flit: research av kundens sajt, kunskapsbasens
innehåll, logotypen och den okulära besiktningen. De kräver ögon, och ett
skript som låtsas göra dem hade producerat en kund som ser klar ut men svarar
fel. Skriptet skriver ut dem som checklista i stället.

Idempotent: `POST /api/keys` upsertar tenanten, workspace-skrivningen är en
upsert på slug, och filgenereringen hoppar över filer som redan finns.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ENV = ROOT / ".env.local"
BACKEND_ENV = ROOT / "snajp-support" / ".env"
DEPLOY_ENV = ROOT / ".env.deploy"

TENANTS_DIR = ROOT / "lib" / "tenants"
KB_DIR = ROOT / "snajp-support" / "app" / "tenants"

#: Vilken miljö kunden läggs upp i. Backend-URL och Vercel-scope följer med.
ENVIRONMENTS = {
    "production": {
        "vercel_scopes": ("production",),
        "backend_env_key": "SNAJP_SUPPORT_URL",
    },
    "preview": {
        # Vercel har både "preview" och "development" som scope. En nyckel som
        # bara finns i preview saknas när någon kör `vercel dev` lokalt, och det
        # felet ser ut som en kodbugg. Sätt båda.
        "vercel_scopes": ("preview", "development"),
        "backend_env_key": "SNAJP_SUPPORT_URL_PREVIEW",
    },
}


# --- Hjälpare som återanvänds ur keys.py --------------------------------
#
# Importeras hellre än kopieras: guard_gitignored() är en säkerhetsspärr, och
# två kopior av en säkerhetsspärr blir förr eller senare en som glömdes bort.

sys.path.insert(0, str(ROOT / "scripts"))
from keys import guard_gitignored, read_env, vercel_env_set  # noqa: E402


def slugify(name: str) -> str:
    """Samma regel som backendens _slugify i app/api/keys.py.

    Måste stämma, annars skapar backenden en tenant med en annan slug än den
    configfilen och workspace-raden pekar på — och felet syns först som en 409
    långt senare.
    """
    lowered = name.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "tenant"


def env_value(name: str, *paths: Path) -> str:
    """Läser en variabel ur miljön först, sedan ur env-filerna i tur och ordning."""
    if os.environ.get(name):
        return os.environ[name]
    for path in paths:
        value = read_env(path).get(name, "")
        if value:
            return value
    return ""


# --- Steg 1: tenant + API-nyckel ----------------------------------------


def create_tenant_and_key(backend_url: str, master_key: str, slug: str, name: str) -> dict:
    """POST /api/keys upsertar tenanten OCH skapar nyckeln i samma anrop.

    Rånyckeln returneras en enda gång och visas aldrig igen — den går direkt
    vidare till Vercel och skrivs aldrig ut.
    """
    payload = json.dumps({"tenant_name": name, "slug": slug}).encode()
    request = urllib.request.Request(
        f"{backend_url.rstrip('/')}/api/keys",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": master_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        sys.exit(f"AVBRYTER: backenden svarade {error.code} på /api/keys — {detail}")
    except urllib.error.URLError as error:
        sys.exit(
            f"AVBRYTER: nådde inte backenden på {backend_url} ({error.reason}). "
            "På Renders gratisplan tar en kallstart ~1 minut — försök igen."
        )


# --- Steg 2: workspace-kopplingen ---------------------------------------


def link_workspace(supabase_url: str, service_key: str, slug: str, name: str, tenant_id: str) -> str:
    """Sätter workspaces.slug + ss_tenant_id.

    DEN HÄR SAKNADES HELT. Ingen kodrad i repot skrev de två kolumnerna — enda
    exemplet var hårdkodat i migration 007. Utan dem kastar requireSnajpTenant()
    409 "Arbetsytan är inte kopplad till någon kund ännu".
    """
    base = f"{supabase_url.rstrip('/')}/rest/v1/workspaces"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        # merge-duplicates: kör skriptet om utan att skapa en andra arbetsyta.
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    body = json.dumps(
        [{"name": name, "slug": slug, "ss_tenant_id": tenant_id, "products": ["support", "leads"]}]
    ).encode()
    request = urllib.request.Request(
        f"{base}?on_conflict=slug", data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            rows = json.loads(response.read())
            return rows[0]["id"] if rows else "(okänt id)"
    except urllib.error.HTTPError as error:
        sys.exit(
            f"AVBRYTER: Supabase svarade {error.code} på workspaces-upserten — "
            f"{error.read().decode(errors='replace')[:300]}"
        )


# --- Steg 3 och 4: filerna ----------------------------------------------


def write_tenant_config(slug: str, name: str) -> Path | None:
    """Genererar lib/tenants/<slug>.ts och registrerar den i index.ts."""
    target = TENANTS_DIR / f"{slug}.ts"
    if target.exists():
        return None

    var = re.sub(r"[^a-z0-9]", "", slug)
    target.write_text(
        f'''import type {{ Tenant }} from "./types";

/**
 * {name} — TODO: en mening om vad kunden gör.
 *
 * Paletten nedan är Snajps default. Den behöver INTE matcha kundens grafiska
 * profil — chatten bär Snajps formspråk med kundens logotyp. Accenten får
 * däremot aldrig kunna förväxlas med --danger (fel) eller --moss (bekräftelse).
 *
 * TODO innan kunden får länken (TENANTS.md steg 7):
 *  - logo.background: kontrollera mot BÅDA bakgrunderna. En vit ordbild
 *    försvinner mot papper — det syns inte i koden, bara på skärmen.
 *  - supportPrompts måste handla om kundens EGEN verksamhet.
 *  - company-uppgifterna hämtas från kundens sajt, inte gissas.
 */
export const {var}: Tenant = {{
  slug: "{slug}",
  name: "{name}",
  tagline: "TODO",
  website: "https://TODO",
  supportKeyEnv: "SNAJP_KEY_{slug.upper().replace("-", "_")}",

  logo: {{
    src: "/tenants/{slug}/logo.png",
    width: 264,
    height: 70,
    alt: "{name}",
    background: "light"
  }},

  palette: {{
    ink: "0.20 0.018 252",
    ink2: "0.28 0.018 252",
    paper: "0.965 0.008 88",
    paper2: "0.93 0.012 88",
    mineral: "0.55 0.015 252",
    seal: "0.42 0.022 252",
    ochre: "0.48 0.105 215",
    moss: "0.42 0.071 142",
    danger: "0.57 0.18 27"
  }},

  company: {{
    legalName: "{name}",
    orgNumber: "TODO",
    addresses: ["TODO"],
    phones: ["TODO"],
    email: "TODO"
  }},

  supportIntro: "Beskriv ditt ärende så hjälper vi dig.",
  supportPrompts: ["TODO", "TODO", "TODO"]
}};
''',
        encoding="utf-8",
    )

    index = TENANTS_DIR / "index.ts"
    text = index.read_text(encoding="utf-8")
    if f'from "./{slug}"' not in text:
        text = text.replace(
            'import { livrustning } from "./livrustning";',
            f'import {{ livrustning }} from "./livrustning";\nimport {{ {var} }} from "./{slug}";',
            1,
        )
        text = text.replace(
            "const tenants: Record<string, Tenant> = {\n  livrustning\n};",
            f"const tenants: Record<string, Tenant> = {{\n  livrustning,\n  {var}\n}};",
            1,
        )
        index.write_text(text, encoding="utf-8")
    return target


def write_kb_module(slug: str, name: str) -> Path | None:
    """Genererar KB-stubben och registrerar den i TENANTS-dicten.

    Namnet MÅSTE stå i registret: create_tenant är en upsert som skriver om
    `name`, så en tenant utan registerrad kan tyst döpas om av nästa seedning.
    """
    module = slug.replace("-", "_")
    target = KB_DIR / f"{module}_kb.py"
    if target.exists():
        return None

    target.write_text(
        f'''"""Kunskapsbas för {name}.

TODO: skriv artiklarna som svar på FAKTISKA kundfrågor, inte som kopierad
webbtext. Se TENANTS.md steg 2.

Två regler som kostat oss förut:
  * Kategorierna måste matcha ss_knowledge_base_category_check i databasen.
    Kontrollera villkoret innan du skriver — det har avvikit från
    migrationerna i repot.
  * Motstridiga eller obekräftade uppgifter kodas som ESKALERING, inte som
    ett svar. En agent som gissar en garantitid åt kundens räkning är värre
    än en som säger "jag kopplar in en kollega".
"""

{module.upper()}_KB: list[dict] = [
    # {{"title": "...", "content": "...", "category": "..."}},
]
''',
        encoding="utf-8",
    )

    init = KB_DIR / "__init__.py"
    text = init.read_text(encoding="utf-8")
    if f"{module}_kb" not in text:
        text = text.replace(
            "TENANTS: dict[str, dict] = {",
            f'from .{module}_kb import {module.upper()}_KB\n\nTENANTS: dict[str, dict] = {{\n'
            f'    "{slug}": {{"name": "{name}", "articles": {module.upper()}_KB}},',
            1,
        )
        init.write_text(text, encoding="utf-8")
    return target


# --- Huvudflödet ---------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Lägg upp en ny kund.")
    parser.add_argument("--name", required=True, help='Kundens namn, t.ex. "Bolaget AB"')
    parser.add_argument("--slug", help="Subdomän. Härleds ur namnet om den utelämnas.")
    parser.add_argument(
        "--env", choices=sorted(ENVIRONMENTS), default="preview",
        help="Miljö att lägga upp kunden i (default: preview)",
    )
    parser.add_argument(
        "--skip-vercel", action="store_true",
        help="Skapa tenant och filer, men rör inte Vercel.",
    )
    args = parser.parse_args()

    slug = args.slug or slugify(args.name)
    if slug != slugify(slug):
        sys.exit(f"AVBRYTER: {slug!r} är inte en giltig slug (a-z, 0-9, bindestreck).")

    # Säkerhetsspärren först: en rånyckel ska aldrig kunna hamna i en fil som
    # går att committa.
    guard_gitignored()

    config = ENVIRONMENTS[args.env]
    backend_url = env_value(config["backend_env_key"], DEPLOY_ENV, FRONTEND_ENV)
    if not backend_url:
        sys.exit(
            f"AVBRYTER: {config['backend_env_key']} är inte satt. Lägg den i "
            f".env.deploy — det är backend-URL:en för miljön {args.env!r}."
        )
    master_key = env_value("SNAJP_MASTER_API_KEY", DEPLOY_ENV, BACKEND_ENV, FRONTEND_ENV)
    if not master_key:
        sys.exit("AVBRYTER: SNAJP_MASTER_API_KEY saknas. Hämta den från Render-tjänsten.")

    supabase_url = env_value("NEXT_PUBLIC_SUPABASE_URL", DEPLOY_ENV, FRONTEND_ENV)
    service_key = env_value("SUPABASE_SERVICE_ROLE_KEY", DEPLOY_ENV, FRONTEND_ENV)

    print(f"Lägger upp {args.name!r} som {slug!r} i {args.env}.\n")

    result = create_tenant_and_key(backend_url, master_key, slug, args.name)
    api_key = result["api_key"]
    tenant_id = result["tenant_id"]
    print(f"  tenant   {tenant_id} ({result.get('tenant_slug', slug)})")
    print(f"  nyckel   {result.get('key_prefix', '?')}… (visas aldrig igen)")

    if supabase_url and service_key:
        workspace_id = link_workspace(supabase_url, service_key, slug, args.name, tenant_id)
        print(f"  workspace {workspace_id} kopplad till tenanten")
    else:
        print("  workspace ÖVERHOPPAD — NEXT_PUBLIC_SUPABASE_URL/SERVICE_ROLE saknas")

    created = write_tenant_config(slug, args.name)
    print(f"  config   {'skapad: ' + created.relative_to(ROOT).as_posix() if created else 'fanns redan'}")
    kb = write_kb_module(slug, args.name)
    print(f"  kb       {'skapad: ' + kb.relative_to(ROOT).as_posix() if kb else 'fanns redan'}")

    env_name = f"SNAJP_KEY_{slug.upper().replace('-', '_')}"
    if args.skip_vercel:
        print(f"  vercel   överhoppad (--skip-vercel). Sätt {env_name} själv.")
    else:
        for scope in config["vercel_scopes"]:
            ok = vercel_env_set(env_name, api_key, scope)
            print(f"  vercel   {env_name} -> {scope}: {'OK' if ok else 'MISSLYCKADES'}")

    print(
        f"""
Kvar, och det kräver ögon (TENANTS.md steg 1 och 7):

  1. Research kundens sajt — varje sida, inte bara startsidan. Policysidor
     ligger ofta bara i sidfoten och innehåller det kunden glömmer nämna.
  2. Fyll {slug}_kb.py med svar på faktiska kundfrågor. Motstridiga uppgifter
     kodas som eskalering, aldrig som ett svar.
  3. Logotyp till public/tenants/{slug}/logo.png — och TITTA på den mot båda
     bakgrunderna innan du sätter logo.background.
  4. Ersätt varje TODO i lib/tenants/{slug}.ts.
  5. Seeda kunskapsbasen: cd snajp-support && python -m app.scripts.seed_kb {slug}
  6. Deploya om så nyckeln får effekt — env-ändringar slår inte igenom på
     befintliga deployments.
  7. Rendera /chat/{slug} och läs sidan. Statuskoder räcker inte."""
    )


if __name__ == "__main__":
    main()
