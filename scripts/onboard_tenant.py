#!/usr/bin/env python
"""Lägg upp en ny NAMNGIVEN kund mot Railway-driften. Torrkörning som standard.

    python scripts/onboard_tenant.py --slug bolaget --name "Bolaget AB"            # visar planen
    python scripts/onboard_tenant.py --slug bolaget --name "Bolaget AB" --apply    # development
    python scripts/onboard_tenant.py --slug bolaget --name "Bolaget AB" \\
        --env main --jag-menar-produktion --apply

## Vad skriptet gör, och mot vad

Utan `--apply` skrivs ingenting: inget anrop mot backenden, ingen fil, ingen
variabel. Skriptet visar planen och de steg som kräver en människa.

Med `--apply`:

  1. Tenant + API-nyckel: `POST /api/keys` mot miljöns backend
     (`RAILWAY_<ENV>_API_URL`, masternyckeln `RAILWAY_<ENV>_MASTER_API_KEY` ur
     `.env.deploy`), med `kraver_avtal: true` så att kunden inte får någon
     trafik förrän avtalet är registrerat (INV-AVTAL-001). Upsert på slug.
  2. Nyckeln sparas som `RAILWAY_<ENV>_KEY_<SLUG>` i `.env.deploy` och sätts som
     `SNAJP_KEY_<SLUG>` på Railway-tjänsten `web` i samma miljö, följt av en
     redeploy och en kontroll mot `/api/kb` med den nya nyckeln. Samma väg som
     `scripts/railway_tenantnyckel.py`, med dess hjälpfunktioner.
     `--utan-web` hoppar över Railway-delen (nyckeln sparas ändå).
  3. Configfilen `lib/tenants/<slug>.ts`, registrerad i `lib/tenants/index.ts`.
  4. KB-stubben `snajp-support/app/tenants/<slug>_kb.py`, registrerad i
     `TENANTS`.

## Vad skriptet med flit INTE gör

* **Kopplar ingen arbetsyta.** Den gamla versionen skrev `workspaces` direkt
  i den gamla databasen. I dag kopplas en kund som registrerar sig själv
  automatiskt till en egen `kund-<8>`-tenant (`lib/snajp/provisionering.ts`,
  `link_workspace_tenant`, migration 061), och den funktionen tar bara
  `kund-`-slugar. Att koppla en kunds arbetsyta till en NAMNGIVEN tenant har
  inget skript i dag; `railway_link_admin_workspace.py` kopplar bara
  plattformsadminens egen arbetsyta. Skriptet skriver ut det som ett manuellt
  steg i stället för att gissa vilken arbetsyta som är kundens.
* Research av kundens sajt, kunskapsbasens innehåll, logotypen och den okulära
  besiktningen. De kräver ögon och skrivs ut som checklista.
* De juridiska stegen (docs/pilot_onboarding.md, "Avtal och dataskydd före
  första trafik"). De skrivs ut i ordning.

Läckagespärr: rånyckeln går från HTTP-svaret till `.env.deploy` och Railway.
Den skrivs aldrig ut, bara namn och längd.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TENANTS_DIR = ROOT / "lib" / "tenants"
KB_DIR = ROOT / "snajp-support" / "app" / "tenants"

#: Railway-miljöerna, samma namn som railway_provision.ENVIRONMENTS och de
#: andra Railway-skripten. `development` speglar produktionen och bär riktig
#: kunddata (CLAUDE.md), så den är ingen sandlåda.
MILJOER = ("development", "main")

# --- Hjälpare som återanvänds ------------------------------------------------
#
# Importeras hellre än kopieras: guard_gitignored() är en säkerhetsspärr, och
# två kopior av en säkerhetsspärr blir förr eller senare en som glömdes bort.

sys.path.insert(0, str(ROOT / "scripts"))
from keys import guard_gitignored  # noqa: E402
from railway_provision import (  # noqa: E402
    deploy,
    env_read,
    env_set,
    envs_by_name,
    services_by_name,
    set_vars,
    state,
)


def slugify(name: str) -> str:
    """Samma regel som backendens _slugify i app/api/keys.py.

    Måste stämma, annars skapar backenden en tenant med en annan slug än den
    configfilen pekar på — och felet syns först som en 409 långt senare.
    """
    lowered = name.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "tenant"


def nyckelnamn(slug: str) -> str:
    """`SNAJP_KEY_<SLUG>` — samma härledning som lib/tenants/*.ts och railway_tenant_keys.py."""
    return f"SNAJP_KEY_{slug.upper().replace('-', '_')}"


# --- Steg 1: tenant + API-nyckel ----------------------------------------


def create_tenant_and_key(backend_url: str, master_key: str, slug: str, name: str) -> dict:
    """POST /api/keys upsertar tenanten OCH skapar nyckeln i samma anrop.

    Rånyckeln returneras en enda gång och visas aldrig igen — den går direkt
    vidare till .env.deploy och Railway och skrivs aldrig ut.
    """
    # kraver_avtal uttryckligen: en riktig kund får ingen trafik förrän
    # biträdesavtalet är registrerat (INV-AVTAL-001). Gäller bara en ny
    # tenant; ett omtag ändrar aldrig en befintlig kunds grind.
    payload = json.dumps({"tenant_name": name, "slug": slug, "kraver_avtal": True}).encode()
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
            "Kontrollera att api-tjänsten i Railway-miljön är uppe och försök igen."
        )


# --- Steg 3 och 4: filerna ----------------------------------------------
#
# Läses och skrivs som bytes: Path.write_text på Windows gör om varje \n till
# \r\n, och en omskriven index.ts hade blivit en diff över hela filen.


def _las(path: Path) -> tuple[str, str]:
    """Texten med \\n som radslut, och filens eget radslut att skriva tillbaka med."""
    raw = path.read_bytes().decode("utf-8")
    radslut = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), radslut


def _skriv(path: Path, text: str, radslut: str = "\n") -> None:
    path.write_bytes(text.replace("\n", radslut).encode("utf-8"))


def write_tenant_config(slug: str, name: str) -> Path | None:
    """Genererar lib/tenants/<slug>.ts och registrerar den i index.ts."""
    target = TENANTS_DIR / f"{slug}.ts"
    if target.exists():
        return None

    var = re.sub(r"[^a-z0-9]", "", slug)
    _skriv(
        target,
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
  supportKeyEnv: "{nyckelnamn(slug)}",

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
    )

    index = TENANTS_DIR / "index.ts"
    text, radslut = _las(index)
    if f'from "./{slug}"' not in text:
        import_ankare = 'import { livrustning } from "./livrustning";'
        # Registret har fått kommentarer och fler kunder sedan skriptet skrevs;
        # därför ankras raden på dictens öppning och inte på hela innehållet.
        register_ankare = "const tenants: Record<string, Tenant> = {\n"
        if import_ankare in text and register_ankare in text:
            text = text.replace(
                import_ankare, f'{import_ankare}\nimport {{ {var} }} from "./{slug}";', 1
            )
            text = text.replace(register_ankare, f"{register_ankare}  {var},\n", 1)
            _skriv(index, text, radslut)
        else:
            print(
                f"  VARNING: hittade inte ankarraderna i lib/tenants/index.ts. "
                f"Registrera {var} där för hand."
            )
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

    _skriv(
        target,
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
    )

    init = KB_DIR / "__init__.py"
    text, radslut = _las(init)
    if f"{module}_kb" not in text:
        ankare = "TENANTS: dict[str, dict] = {"
        if ankare in text:
            text = text.replace(
                ankare,
                f'from .{module}_kb import {module.upper()}_KB\n\n{ankare}\n'
                f'    "{slug}": {{"name": "{name}", "articles": {module.upper()}_KB}},',
                1,
            )
            _skriv(init, text, radslut)
        else:
            print(f"  VARNING: hittade inte TENANTS i {init.name}. Registrera {slug} för hand.")
    return target


# --- Utskrifterna ------------------------------------------------------------


def manuella_steg(slug: str, env: str) -> str:
    """Det som kräver ögon eller uppgifter skriptet inte har."""
    prefix = f"RAILWAY_{env.upper()}"
    return f"""
Kvar, och det kräver ögon (TENANTS.md steg 1 och 7):

  1. Research kundens sajt — varje sida, inte bara startsidan. Policysidor
     ligger ofta bara i sidfoten och innehåller det kunden glömmer nämna.
  2. Kunskapsbasen: kör scripts/pilot_kb_utkast.py (docs/pilot_onboarding.md)
     och skicka in de godkända artiklarna med --apply. Nyckeln står som
     {prefix}_KEY_{slug.upper().replace('-', '_')} i .env.deploy; skriptet läser
     SNAJP_PILOT_TENANT_KEY. Motstridiga uppgifter kodas som eskalering.
  3. Logotyp till public/tenants/{slug}/logo.png — och TITTA på den mot båda
     bakgrunderna innan du sätter logo.background.
  4. Ersätt varje TODO i lib/tenants/{slug}.ts, committa till development och
     pusha. Configfilen når web först med en deploy av koden.
  5. Arbetsytan kopplas INTE av det här skriptet. Ska kunden logga in måste
     en arbetsyta bära sluggen {slug!r}: link_workspace_tenant (migration 061)
     tar bara kund-<8>-slugar, och scripts/railway_link_admin_workspace.py
     kopplar bara plattformsadminens egen arbetsyta. Det finns inget skript
     för en kunds arbetsyta i dag; fråga Anton innan något kopplas för hand.
  6. Rendera /chat/{slug} på webben i miljön {env} och läs sidan.
     Statuskoder räcker inte."""


def juridiska_steg(slug: str, env: str) -> str:
    """Stegen i docs/pilot_onboarding.md, "Avtal och dataskydd före första trafik"."""
    db_env = f"railway-{env}"
    prod = " --jag-menar-produktion" if env == "main" else ""
    return f"""
Avtal och dataskydd före första trafik — i den här ordningen, se
docs/pilot_onboarding.md ("Avtal och dataskydd före första trafik").
Ingen riktig kundtrafik innan alla sju är gjorda.

  1. Personuppgiftsbiträdesavtalet undertecknat, med Bilaga 3 ifylld
     (docs/pub-avtal.md, granskat av jurist).
  2. Kundens org.nr och postadress i kundregistret (företagsnamnet är
     tenantens namn): admin › Kunder & Data › kunden, eller
     python scripts/fyll_kundregister.py --slug {slug} --env {env}{prod} \\
         --orgnr ... --foretagsadress ... --apply
  3. Avtalsdatumet: avtalsgrinden är redan på (kraver_avtal: true ovan).
     En människa som sett avtalet sätter Avtal signerat (datum) i
     admin › Kunder & Data › kunden. Skriptet kan med flit inte sätta det.
  4. Art. 13-texten: skicka docs/kundmall_informationstext.md till kunden,
     som lägger in den på sin kontaktsida och i sin integritetspolicy. Sätt
     sedan policy_url (Kunder & Data, eller fyll_kundregister.py --policy-url).
  5. Gallringsperioden, beslutad med kunden och angiven i integritetspolicyn:
     python scripts/gallra.py --env {db_env} --tenant {slug} --satt-policy <dagar> --beslutad-av "<namn>"
  6. Autonominivån per ärendekategori genomgången med kunden (/settings/regler).
  7. Varje kanal och integration kunden slår på står i det undertecknade avtalet."""


# --- Huvudflödet ---------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lägg upp en ny namngiven kund i Railway-driften.")
    parser.add_argument("--name", required=True, help='Kundens namn, t.ex. "Bolaget AB"')
    parser.add_argument("--slug", help="Subdomän. Härleds ur namnet om den utelämnas.")
    parser.add_argument(
        "--env", choices=MILJOER, default="development",
        help="Railway-miljö (default: development, som speglar produktionen).",
    )
    parser.add_argument("--apply", action="store_true", help="Skriv på riktigt. Utan flaggan visas planen.")
    parser.add_argument("--jag-menar-produktion", action="store_true")
    parser.add_argument(
        "--utan-web", action="store_true",
        help="Sätt inte SNAJP_KEY_<SLUG> på Railway-tjänsten web (nyckeln sparas ändå i .env.deploy).",
    )
    args = parser.parse_args(argv)

    slug = args.slug or slugify(args.name)
    if slug != slugify(slug):
        sys.exit(f"AVBRYTER: {slug!r} är inte en giltig slug (a-z, 0-9, bindestreck).")
    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    # Säkerhetsspärren först: en rånyckel ska aldrig kunna hamna i en fil som
    # går att committa.
    guard_gitignored()

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    api_url = store.get(f"{prefix}_API_URL", "").rstrip("/")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not api_url or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL / {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    env_var = nyckelnamn(slug)
    lagrad = f"{prefix}_KEY_{slug.upper().replace('-', '_')}"

    print(f"Lägger upp {args.name!r} som {slug!r} i Railway-miljön {args.env} ({api_url}).\n")

    if not args.apply:
        print("TORRKÖRNING — ingenting skrivs. Med --apply:")
        print(f"  1. POST {api_url}/api/keys  (tenant {slug}, kraver_avtal: true)")
        print(f"  2. nyckeln sparas som {lagrad} i .env.deploy")
        if args.utan_web:
            print(f"     {env_var} sätts INTE på web (--utan-web)")
        else:
            print(f"     och sätts som {env_var} på web ({args.env}) + redeploy + kontroll mot /api/kb")
        print(f"  3. lib/tenants/{slug}.ts + registrering i index.ts")
        print(f"  4. snajp-support/app/tenants/{slug.replace('-', '_')}_kb.py + registrering i TENANTS")
        print(manuella_steg(slug, args.env))
        print(juridiska_steg(slug, args.env))
        print("\nInget gjort. Kör med --apply.")
        return 0

    result = create_tenant_and_key(api_url, master, slug, args.name)
    api_key = result.get("api_key")
    tenant_id = result.get("tenant_id")
    if not api_key or not tenant_id:
        sys.exit(f"AVBRYTER: /api/keys gav inget nyckelfält. Svarsnycklar: {sorted(result)}")
    print(f"  tenant   {tenant_id} ({result.get('tenant_slug', slug)})")
    print(f"  nyckel   {result.get('key_prefix', '?')}… (visas aldrig igen)")
    if result.get("kraver_avtal", True):
        print(
            "  avtal    grinden PÅ: chatt, inkommande mejl och kanaler vägras tills "
            "biträdesavtalet är registrerat.\n"
            "           Nästa steg: admin › Kunder & Data › kunden › Avtal signerat (datum)."
        )
    else:
        print("  avtal    grinden AV för den här tenanten (fanns redan, rördes inte).")

    env_set(lagrad, api_key)

    if args.utan_web:
        print(f"  web      överhoppad (--utan-web). {env_var} är inte satt på web.")
    else:
        project = state()
        env_id = envs_by_name(project).get(args.env)
        web = services_by_name(project).get("web")
        if not env_id or not web:
            sys.exit(f"AVBRYTER: miljön {args.env} eller tjänsten web finns inte i Railway-projektet.")
        set_vars(web["id"], env_id, {env_var: api_key})
        # Variabeln når inte den körande processen utan en ny deploy.
        deploy(web["id"], env_id)
        print(f"  web      ({args.env}) redeployar med {env_var}")
        from railway_tenantnyckel import verifiera

        verifiera(api_url, api_key)

    created = write_tenant_config(slug, args.name)
    print(f"  config   {'skapad: ' + created.relative_to(ROOT).as_posix() if created else 'fanns redan'}")
    kb = write_kb_module(slug, args.name)
    print(f"  kb       {'skapad: ' + kb.relative_to(ROOT).as_posix() if kb else 'fanns redan'}")

    print(manuella_steg(slug, args.env))
    print(juridiska_steg(slug, args.env))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
