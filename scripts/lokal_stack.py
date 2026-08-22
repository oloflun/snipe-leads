#!/usr/bin/env python3
"""Hela stacken lokalt — den PENGAFRIA vägen att prova produkten.

    python scripts/lokal_stack.py --kontrollera    # vad saknas innan något körs?
    python scripts/lokal_stack.py --apply          # databas, schema, admin, demodata
    python scripts/lokal_stack.py --apply --nollstall   # RIV databasen först

## Varför skriptet finns

Railway-deployen är inte den enda vägen till en körbar produkt, och den ska
inte vara det. Den 2026-08-19 låg `railway-development` på rätt commit i över
en timme utan att någon deploy startade — tjänsterna levde vidare på gammal
kod. Det som gick att göra ändå var att resa HELA stacken lokalt och prova
varenda vy där: samma migrationskedja, samma roller, samma auth, samma backend.

Det är den vägen det här skriptet automatiserar. Den kostar ingenting och
kräver ingen molnleverantör.

## Vad den mäter, och vad den inte gör

Den ger dig en databas med schemat rest FRÅN NOLL genom hela kedjan — vilket i
sig är testet av att kedjan går att resa, samma påstående som
`railway_migrate.py` gör mot Railway. Ordningen importeras därifrån
(`planned()`), inte kopierad hit: två listor över migrationer i två filer är
exakt den dubbla bokföring som fällde liggaren en gång.

Den installerar INTE Postgres, Node eller Python åt dig. Ett skript som
försöker paketera om en systeminstallation blir en sämre paketerare och en
sämre felsökare. `--kontrollera` säger vad som fattas, med kommandot som fixar
det, och stannar där.

## Demodata

`--apply` seedar körningar och plattformshändelser så att adminvyerna har något
att rendera. Utan dem ser en fungerande adminyta identisk ut med en trasig:
tomma tabeller överallt. Raderna är uppenbart syntetiska och rör bara
tenants som migration 011/012 redan skapat.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = REPO_ROOT / ".env.local"

#: Lösenorden är AVSIKTLIGT triviala och hårdkodade. Databasen finns bara på
#: den här maskinen, den innehåller bara syntetiska rader, och en hemlighet som
#: måste hittas på innan man kan prova produkten är en tröskel utan skyddsvärde.
#: Det som INTE får hamna här är riktiga nycklar — se `.env.deploy`.
DSN_SUPER = os.environ.get("LOKAL_DSN", "postgresql://postgres:localdev@127.0.0.1:5432/railway")
LOSEN_WEB = "localweb"
LOSEN_APP = "localapp"

ADMIN_EMAIL = "snajpsupport@gmail.com"
ADMIN_LOSEN = os.environ.get("SNAJP_ADMIN_PASSWORD", "Snajpen123!")


def _dsn_utan_db(dsn: str) -> tuple[str, str]:
    """Delar upp DSN:en i (server-DSN mot 'postgres', databasnamn)."""
    bas, _, namn = dsn.rpartition("/")
    return f"{bas}/postgres", namn


def skriv(rad: str) -> None:
    print(rad, flush=True)


# -- Kontroller ------------------------------------------------------------


def kontrollera() -> list[str]:
    """Returnerar en lista med brister. Tom lista = allt på plats."""
    brister: list[str] = []

    try:
        conn = psycopg2.connect(_dsn_utan_db(DSN_SUPER)[0], connect_timeout=5)
        conn.close()
        skriv(f"  ok   Postgres svarar på {DSN_SUPER.split('@')[-1]}")
    except Exception as exc:
        brister.append(
            f"Postgres nås inte ({str(exc).strip().splitlines()[0]}).\n"
            "       Ubuntu/Debian: sudo apt-get install -y postgresql-16 && sudo service postgresql start\n"
            "       macOS:         brew install postgresql@16 && brew services start postgresql@16\n"
            "       Sätt sedan lösenordet: sudo -u postgres psql -c \"alter role postgres password 'localdev'\""
        )
        return brister  # allt nedanför kräver en anslutning

    conn = psycopg2.connect(_dsn_utan_db(DSN_SUPER)[0], connect_timeout=5)
    cur = conn.cursor()
    cur.execute("select 1 from pg_available_extensions where name = 'vector'")
    if cur.fetchone():
        skriv("  ok   pgvector finns tillgängligt")
    else:
        brister.append(
            "pgvector saknas. 002_snajp_support.sql skapar `extension vector` och\n"
            "       faller utan den — vilket sedan tar ss_customers och ss_tickets med sig.\n"
            "       Ubuntu/Debian: sudo apt-get install -y postgresql-16-pgvector\n"
            "       macOS:         brew install pgvector"
        )
    conn.close()

    if (REPO_ROOT / "node_modules").is_dir():
        skriv("  ok   node_modules finns")
    else:
        brister.append("node_modules saknas. Kör: npm ci")

    return brister


# -- Schema ----------------------------------------------------------------


def nollstall() -> None:
    server, namn = _dsn_utan_db(DSN_SUPER)
    conn = psycopg2.connect(server, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    # Anslutningar från en tidigare `next start` håller databasen låst, och
    # felmeddelandet ("is being accessed by other users") säger inte vilken
    # process det är. Att stänga dem här är rätt: databasen är per definition
    # en engångsdatabas.
    cur.execute(
        "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s", (namn,)
    )
    cur.execute(f'drop database if exists "{namn}"')
    cur.execute(f'create database "{namn}"')
    conn.close()
    skriv(f"  ~    databasen {namn} nollställd")

    # Tenant-nycklarna i .env.local hörde till den databas som just revs. En
    # nyckel som pekar på en borttagen rad ger 401 från backenden, och felet
    # läses som "adminytan är trasig" i stället för "nyckeln är gammal".
    if ENV_LOCAL.exists():
        rader = ENV_LOCAL.read_text(encoding="utf-8").splitlines(keepends=True)
        kvar = [r for r in rader if not r.startswith("SNAJP_KEY_")]
        if len(kvar) != len(rader):
            ENV_LOCAL.write_text("".join(kvar), encoding="utf-8")
            skriv(f"  ~    {len(rader) - len(kvar)} gamla SNAJP_KEY_* strukna ur .env.local")


def kor_kedjan() -> int:
    """Kör migrationskedjan i railway_migrate.py:s ordning. Returnerar antal fel."""
    import railway_migrate as rm  # importeras här: den läser .env.deploy först i dsn()

    server, namn = _dsn_utan_db(DSN_SUPER)
    conn = psycopg2.connect(server, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("select 1 from pg_database where datname = %s", (namn,))
    if not cur.fetchone():
        cur.execute(f'create database "{namn}"')
        skriv(f"  +    databasen {namn} skapad")
    conn.close()

    conn = psycopg2.connect(DSN_SUPER, connect_timeout=10)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(rm.LEDGER)
    conn.commit()
    cur.execute("select version from supabase_migrations.schema_migrations")
    klara = {r[0] for r in cur.fetchall()}

    fel = 0
    kord = 0
    for version, path in rm.planned():
        if version in klara:
            continue
        sql = path.read_text(encoding="utf-8")
        if not rm._has_sql(sql):
            cur.execute(
                "insert into supabase_migrations.schema_migrations (version, name) values (%s, %s)",
                (version, path.name),
            )
            conn.commit()
            continue
        try:
            cur.execute(sql)
            cur.execute(
                "insert into supabase_migrations.schema_migrations (version, name) values (%s, %s)",
                (version, path.name),
            )
            conn.commit()
            kord += 1
        except Exception as exc:
            conn.rollback()
            skriv(f"  !    {version} FÖLL: {str(exc).strip().splitlines()[0][:180]}")
            fel += 1
            break  # första felet är det enda som betyder något

    if fel == 0:
        skriv(f"  +    migrationskedjan: {kord} körda, {len(klara)} redan på plats")

    # Approllernas lösenord. De skapas utan login-lösenord av 009/030, och
    # utan dem kan varken web eller api ansluta som rätt roll — vilket är hela
    # poängen: RLS ska evalueras här precis som i drift.
    cur.execute(f"alter role snajp_web with password '{LOSEN_WEB}'")
    cur.execute(f"alter role snajp_app with password '{LOSEN_APP}'")
    conn.commit()

    # Kontrollen 028 skrev in i sin egen fil. Den hör hemma här också: en
    # oskyddad policy syns inte förrän en oskopad fråga kastar i drift.
    cur.execute(
        "select count(*) from pg_policies where schemaname='public' "
        "and qual like '%%app.tenant_id%%' and qual not like '%%NULLIF%%'"
    )
    oskyddade = cur.fetchone()[0]
    if oskyddade:
        skriv(f"  !    {oskyddade} RLS-policyer saknar NULLIF-vakten (se 028)")
        fel += 1
    else:
        skriv("  ok   alla tenant-policyer har NULLIF-vakten")

    conn.close()
    return fel


# -- Admin och demodata ----------------------------------------------------


def satt_admin() -> None:
    """Kör admin_cleanup.py mot den lokala databasen.

    Samma kod som mot Railway och Supabase, inte en egen variant: vem som är
    plattformsadmin ska ha EN implementation. `--env production` läser
    DATABASE_URL ur miljön (env_value kollar os.environ först), vilket är
    varför den raden räcker för att peka om den hit.
    """
    import admin_cleanup

    os.environ["DATABASE_URL"] = DSN_SUPER
    os.environ.setdefault("SNAJP_ADMIN_PASSWORD", ADMIN_LOSEN)
    argv = sys.argv
    sys.argv = ["admin_cleanup.py", "--env", "production"]
    try:
        admin_cleanup.main()
    finally:
        sys.argv = argv


#: Ett testkonto som INTE är plattformsadmin. Behövs för att kunna svara på den
#: fråga som räknar mest i grinden: syns adminytan för någon som inte ska se
#: den? Med bara ett adminkonto går den inte att ställa, och det var precis den
#: luckan som lät /admin renderas fel för alla utan att någon märkte det.
KUND_EPOST = "kund@example.com"
KUND_LOSEN = "Kundtest123!"


def satt_testkund() -> None:
    import admin_cleanup  # scrypt-hashen bor där; en andra kopia hade kunnat drifta

    conn = psycopg2.connect(DSN_SUPER, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("select id from auth.users where lower(email) = lower(%s)", (KUND_EPOST,))
    rad = cur.fetchone()
    if rad:
        skriv(f"  =    testkunden {KUND_EPOST} finns redan")
        conn.close()
        return
    # Inserten fyrar on_auth_user_created, som skapar workspace och profil.
    cur.execute(
        "insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at) "
        "values (%s, %s, jsonb_build_object('full_name', 'Kund Test'), now()) returning id",
        (KUND_EPOST, admin_cleanup.scrypt_hash(KUND_LOSEN)),
    )
    kund_id = cur.fetchone()[0]
    # Kontot flyttas till den REDAN seedade livrustning-arbetsytan i stället
    # för att döpa om sin egen. `workspaces.slug` är unik, och migration
    # 007/012 har redan lagt en rad med slug='livrustning' — att sätta samma
    # slug på en andra arbetsyta faller på workspaces_slug_key.
    #
    # Det är dessutom den riktiga modellen: en användare TILLHÖR en kunds
    # arbetsyta, den skapar inte en till med samma namn.
    cur.execute("select id from public.workspaces where slug = 'livrustning'")
    rad = cur.fetchone()
    if rad:
        kund_ws = rad[0]
        cur.execute("select workspace_id from public.profiles where id = %s", (kund_id,))
        egen_ws = cur.fetchone()[0]
        cur.execute(
            "update public.profiles set workspace_id = %s where id = %s", (kund_ws, kund_id)
        )
        if egen_ws and egen_ws != kund_ws:
            # Den tomma arbetsytan triggern skapade. Lämnas den kvar dyker den
            # upp som en extra kund i adminvyn utan att någon äger den.
            cur.execute("delete from public.workspaces where id = %s", (egen_ws,))
    else:
        cur.execute("select workspace_id from public.profiles where id = %s", (kund_id,))
        kund_ws = cur.fetchone()[0]

    # Affärskontext, annars fastnar kontot på /onboarding och arbetsytans vyer
    # går inte att besiktiga alls.
    cur.execute(
        """
        insert into public.business_contexts
              (workspace_id, product, target_audience, industries, geography, tone, offer, cta, contact_roles)
        values (%s, 'leads', 'SME i Norden som säljer B2B',
                array['SaaS','E-handel'], array['Sverige'], 'Rak och konkret',
                'AI som skriver säljmejlen och svarar på kundmejlen', 'Boka 20 minuter',
                array['VD','Säljchef'])
        on conflict (workspace_id) do nothing
        """,
        (kund_ws,),
    )
    conn.close()
    skriv(f"  +    testkund {KUND_EPOST} skapad (inte admin, kopplad till livrustning)")


SEED = """
-- Demodata. Uppenbart syntetisk, och bara mot tenants som 011/012 skapat.
insert into agent_runs (tenant_id, agent_type, pack_version, skills_used, input, output,
                        tokens_in, tokens_out, latency_ms, created_at, is_test, step_log)
select t.id,
       (array['support','leads_research','leads_outreach','support','demo'])[1 + (g % 5)],
       '1ec41e2d0551+0b8e2ff0+74754af9:support/v1',
       array['snajp/support-triage'],
       'Kundfråga ' || g || ': Hej, jag har inte fått min order.',
       'Svar ' || g || ': Hej! Vi beklagar dröjsmålet — ordern är på väg.',
       30000 + g * 517, 900 + g * 31, 12000 + g * 431,
       now() - (g || ' hours')::interval,
       (g % 7 = 0),
       jsonb_build_array(jsonb_build_object(
         'skill','snajp/support-triage','attempts',1,'escalated',false,'escalation_reason',null,
         'latency_ms', 4200 + g, 'tokens_in', 12000 + g, 'tokens_out', 300 + g,
         'reasoning_tokens', 0, 'thinking_mode','off','overlay',null,
         'sources_used', jsonb_build_array('kb:leveranstider'),
         'context_refs', jsonb_build_array('ticket:'||g),
         'system_prompt','Du är Snajps kundtjänstagent...',
         'user_message','Hej, jag har inte fått min order.',
         'raw_output','Hej! Vi beklagar dröjsmålet.'))
from ss_tenants t, generate_series(1, 6) g
where t.slug in ('livrustning','nordlys-handel','snajp')
  and not exists (select 1 from agent_runs);

insert into platform_events (tenant_id, level, source, message, detail, created_at)
select t.id,
       (array['error','warning','info'])[1 + (g % 3)],
       'api',
       (array['TimeoutError: backend svarade inte inom 30s',
              'Låg marginal på tenant',
              'Körning klar'])[1 + (g % 3)],
       jsonb_build_object('path','/api/admin/runs','method','GET'),
       now() - (g || ' hours')::interval
from ss_tenants t, generate_series(1, 3) g
where t.slug in ('livrustning','nordlys-handel')
  and not exists (select 1 from platform_events);
"""


def seeda() -> None:
    conn = psycopg2.connect(DSN_SUPER, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(SEED)
    cur.execute("select count(*) from agent_runs")
    korningar = cur.fetchone()[0]
    cur.execute("select count(*) from platform_events")
    handelser = cur.fetchone()[0]

    # Adminens egen arbetsyta kopplas till snajp-tenanten. Utan kopplingen
    # svarar requireSnajpTenant() 503 och /admin/support + /admin/leads/kontroll
    # visar ett felmeddelande i stället för produkten.
    cur.execute(
        """
        update public.workspaces w
           set name = 'Snajp', slug = 'snajp',
               ss_tenant_id = (select id from ss_tenants where slug = 'snajp')
          from public.profiles p
          join auth.users u on u.id = p.id
         where p.workspace_id = w.id and lower(u.email) = lower(%s)
           and w.slug is distinct from 'snajp'
        """,
        (ADMIN_EMAIL,),
    )
    conn.close()
    skriv(f"  +    demodata: {korningar} körningar, {handelser} händelser")


# -- .env.local ------------------------------------------------------------


def skriv_env_local() -> None:
    if ENV_LOCAL.exists():
        skriv("  =    .env.local finns redan — rörs inte")
        return
    ENV_LOCAL.write_text(
        "# Skriven av scripts/lokal_stack.py. Gitignorerad.\n"
        f"DATABASE_URL=postgresql://snajp_web:{LOSEN_WEB}@127.0.0.1:5432/railway\n"
        "AUTH_SECRET=local-dev-secret-0123456789abcdef0123456789abcdef\n"
        "NEXT_PUBLIC_SITE_URL=http://localhost:3000\n"
        "AUTH_URL=http://localhost:3000\n"
        "SNAJP_SUPPORT_URL=http://127.0.0.1:8000\n"
        "SNAJP_INTERNAL_API_KEY=snajp_demo_2f8c1a9e4b7d\n"
        "SNAJP_MASTER_API_KEY=snajp_master_local_test_key\n",
        encoding="utf-8",
    )
    skriv("  +    .env.local skriven")


def utfardas_tenantnyckel() -> None:
    """Hämtar en API-nyckel för snajp-tenanten från en LOKALT körande backend.

    Hoppas över tyst om backenden inte är igång — nyckeln behövs bara för
    /admin/support och /admin/leads/kontroll, och de säger själva ifrån.
    """
    import json
    import urllib.error
    import urllib.request

    innehall = ENV_LOCAL.read_text(encoding="utf-8")
    # En nyckel per tenant, precis som i drift: nyckeln avgör vilken tenant
    # backenden skriver till, och en delad nyckel skriver i fel kunds data.
    for env_namn, tenant_namn, slug in (
        ("SNAJP_KEY_SNAJP", "Snajp", "snajp"),
        ("SNAJP_KEY_LIVRUSTNING", "Livrustning AB", "livrustning"),
    ):
        if f"{env_namn}=" in innehall:
            continue
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/keys",
            data=json.dumps({"tenant_name": tenant_namn, "slug": slug}).encode(),
            headers={"Content-Type": "application/json", "X-API-Key": "snajp_master_local_test_key"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as svar:
                nyckel = json.load(svar)["api_key"]
        except (urllib.error.URLError, OSError, KeyError):
            skriv(f"  -    backenden svarar inte — hoppar över {env_namn} (kör om skriptet senare)")
            return
        with ENV_LOCAL.open("a", encoding="utf-8") as fh:
            fh.write(f"{env_namn}={nyckel}\n")
        skriv(f"  +    {env_namn} utfärdad mot den lokala backenden")


# -- CLI -------------------------------------------------------------------


NASTA_STEG = """
Kvar att starta, i två terminaler:

  1. Backenden (behöver snajp-support/requirements.txt installerat):
       cd snajp-support
       DATABASE_URL=postgresql://snajp_app:{app}@127.0.0.1:5432/railway \\
       SNAJP_MASTER_API_KEY=snajp_master_local_test_key \\
       python -m uvicorn app.main:app --port 8000

  2. Webben:
       npm run build && npm start        # produktionsläge, som Railway
       # eller: npm run dev

Logga sedan in på http://localhost:3000/login:
  {email} / {losen}   — plattformsadmin, ska landa på /admin
  {kund} / {kundlosen}          — vanlig kund, ska landa på /dashboard och få 404 på /admin

Besiktiga alla vyer i båda rollerna:
  npm i --no-save playwright && npx playwright install chromium
  node scripts/qa_vyer.mjs

Kör skriptet en gång till efter att backenden startat — då utfärdas
SNAJP_KEY_SNAJP och SNAJP_KEY_LIVRUSTNING, som kundtjänstvyerna behöver.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Res hela stacken lokalt.")
    ap.add_argument("--kontrollera", action="store_true", help="Visa vad som saknas, ändra inget.")
    ap.add_argument("--apply", action="store_true", help="Kör schema, admin och demodata.")
    ap.add_argument("--nollstall", action="store_true", help="RIV databasen först. Kräver --apply.")
    args = ap.parse_args()

    if not (args.kontrollera or args.apply):
        ap.print_help()
        return 0

    skriv(f"databas: {DSN_SUPER.split('@')[-1]}")
    brister = kontrollera()
    if brister:
        skriv("")
        for b in brister:
            skriv(f"  SAKNAS: {b}")
        return 1
    if args.kontrollera:
        skriv("\nAllt på plats. Kör med --apply.")
        return 0

    if args.nollstall:
        nollstall()

    if kor_kedjan():
        skriv("\nMigrationskedjan föll. Inget mer kördes.")
        return 1

    satt_admin()
    satt_testkund()
    seeda()
    skriv_env_local()
    utfardas_tenantnyckel()

    skriv(NASTA_STEG.format(app=LOSEN_APP, email=ADMIN_EMAIL, losen=ADMIN_LOSEN,
                            kund=KUND_EPOST, kundlosen=KUND_LOSEN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
