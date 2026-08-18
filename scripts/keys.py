"""Nyckelhantering — ett verktyg, fungerar från vilken katalog som helst.

    python "C:\\Users\\Anton L\\snipe-leads\\scripts\\keys.py"          # sätt + verifiera
    python .../scripts/keys.py --check                                  # bara verifiera
    python .../scripts/keys.py --pull                                   # hämta från Vercel
    python .../scripts/keys.py --push                                   # skicka till Vercel
    python .../scripts/keys.py --new-unlock-key                         # generera skill-låsnyckeln

Sökvägar löses ur __file__, aldrig ur cwd — skriptet kan köras varifrån som
helst. Värden läses med getpass (syns aldrig, hamnar aldrig i shell-historiken)
och skrivs bara till gitignorerade filer.

Nycklarna hamnar ALDRIG i databasen (INV-SEC-006 / plan G5). Se DEPLOY_KEYS.md.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV = ROOT / "snajp-support" / ".env"
FRONTEND_ENV = ROOT / ".env.local"
UNLOCK_HASH = ROOT / "agent-core" / ".unlock-hash"
#: Drift- och speglingsvariabler. Egen fil, inte .env: de här läses av
#: skripten i scripts/, aldrig av appen, och ska inte följa med en env-pull.
DEPLOY_ENV = ROOT / ".env.deploy"


class Key:
    def __init__(self, name, files, blurb, *, required, where, generated=False):
        self.name, self.files, self.blurb = name, files, blurb
        self.required, self.where = required, where
        # generated=True => klistras aldrig in för hand, så cmd_set frågar inte
        # efter den. Den har ett eget kommando som skapar värdet lokalt.
        self.generated = generated


KEYS = [
    Key(
        "DEEPSEEK_API_KEY",
        [BACKEND_ENV],
        "DeepSeek — driver ALLA agentkörningar. Utan denna kan ingenting testas.",
        required=True,
        where="https://platform.deepseek.com/api_keys",
    ),
    Key(
        "SCRAPEGRAPHAI_API_KEY",
        [BACKEND_ENV],
        "ScrapeGraphAI — bara för Fas B-research (prospektskrapning).",
        required=False,
        where="https://dashboard.scrapegraphai.com",
    ),
    Key(
        "GEMINI_API_KEY",
        [BACKEND_ENV],
        "Gemini (gratisnivå) — bildbeskrivning i supportärenden + KB-embeddings. "
        "UTAN denna föll KB-sökningen tillbaka på svensk fulltext i skarpa "
        "tester 2026-08-07 och missade uppenbara träffar (se HANDOFF.md Steg 0) "
        "— sätt den innan nästa testomgång.",
        required=False,
        where="https://aistudio.google.com/apikey",
    ),
    Key(
        "SNAJP_SKILL_UNLOCK_KEY",
        [BACKEND_ENV],
        "Avsiktlighetsgrind för agent-core/skills/ — INTE en säkerhetsmekanism. "
        "Krävs för att regenerera manifestet eller publicera skills till DB:n. "
        "Bara på den här maskinen; aldrig i Render/Vercel/CI.",
        required=False,
        where="genereras lokalt: python scripts/keys.py --new-unlock-key",
        generated=True,
    ),
    Key(
        "PREVIEW_POSTGRES_URL",
        [DEPLOY_ENV],
        "Postgres-anslutning till Supabase-grenen development, som postgres-rollen. "
        "Krävs BARA av scripts/supabase_seed_dev.py (speglingen produktion → "
        "development). Utan den är development-databasen en fryst ögonblicksbild: "
        "konton som skapats i produktionen efteråt kan inte logga in där, och "
        "/admin svarar 404 eftersom platform_admins saknar raden. "
        "OBS: snajp_app- och snajp_web-rollerna DUGER INTE — de saknar "
        "        OBS: snajp_app- och snajp_web-rollerna DUGER INTE — de saknar "
        "rättigheter på auth-schemat, och auth.users är just det som måste kopieras.",
        required=False,
        where=(
            "Supabase → snipra → Branches → development → Database → Reset password, "
            "sedan: python scripts/set_preview_postgres_url.py"
        ),
        # generated=True: värdet klistras aldrig in rått här. Det egna kommandot
        # verifierar anslutningen och bygger DSN:en, så en felstavning fångas
        # innan den skrivs — samma resonemang som SNAJP_SKILL_UNLOCK_KEY.
        generated=True,
    ),
]

FIXED = {BACKEND_ENV: {"LLM_PROVIDER": "deepseek", "MODEL": "deepseek-v4-flash"}}


def looks_placeholder(value: str) -> bool:
    """Samma heuristik som app/config.py:is_simulation()."""
    return len(value) < 20 or "..." in value or "din-" in value


def key_fault(value: str) -> str | None:
    """Varför nyckeln inte GÅR ATT SKICKA, eller None.

    Samma kontroll som Settings.llm_key_fault() i snajp-support/app/config.py,
    fast vid inklistring i stället för vid första agentanropet.

    Ett API-nyckelvärde går i huvudet `Authorization: Bearer <nyckel>`, och
    huvudvärden är per definition ASCII. En nyckel med ett tecken över 127
    kraschar därför inte hos leverantören utan INNE i http-klienten. Det hände
    skarpt: /health/ready svarade "riktig agent aktiv" och första körningen föll
    på `'ascii' codec can't encode character 'à' in position 7` — position 7
    är första tecknet efter "Bearer ".

    Positionen står med i beskedet med flit. Utan den söker den som läser efter
    ett osynligt tecken i en sträng som aldrig får skrivas ut.
    """
    bad = next((i for i, ch in enumerate(value) if ord(ch) > 127), None)
    if bad is not None:
        return (f"innehåller ett tecken utanför ASCII på position {bad} — "
                f"kan inte skickas i ett Authorization-huvud")
    if value != value.strip():
        return "har inledande eller avslutande blanktecken"
    return None


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


def upsert(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def guard_gitignored() -> None:
    for path in (BACKEND_ENV, FRONTEND_ENV):
        relative = path.relative_to(ROOT).as_posix()
        result = subprocess.run(
            ["git", "check-ignore", relative], cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode != 0:
            sys.exit(f"AVBRYTER: {relative} är inte gitignorerad — nycklar kunde committas.")


def cmd_check() -> bool:
    print(f"Repo: {ROOT}\n")
    ok = True
    for key in KEYS:
        value = read_env(key.files[0]).get(key.name, "")
        if not value:
            status = "SAKNAS" if key.required else "tom (valfri)"
            ok = ok and not key.required
        elif key_fault(value):
            # Egen rad, inte samma som PLATSHÅLLARE: den som läser "platshållare"
            # letar efter en saknad variabel, inte efter ett osynligt tecken i
            # den som redan finns.
            status = f"TRASIG — {key_fault(value)}"
            ok = False
        elif looks_placeholder(value):
            status = "PLATSHÅLLARE — tjänsten kör i SIMULERINGSLÄGE"
            ok = False
        elif key.generated:
            # Ingen svans för genererade nycklar — du bad om att aldrig se den.
            status = f"OK (len={len(value)})"
        else:
            status = f"OK (len={len(value)}, ...{value[-4:]})"
        flag = "KRÄVS" if key.required else "valfri"
        print(f"  {key.name:24} [{flag:6}] {status}")

    backend = read_env(BACKEND_ENV)
    print(f"\n  LLM_PROVIDER={backend.get('LLM_PROVIDER', '(saknas)')}  MODEL={backend.get('MODEL', '(saknas)')}")
    print(
        "\nKLART — riktiga agentkörningar möjliga."
        if ok
        else "\nBLOCKERAT — minst DEEPSEEK_API_KEY behövs."
    )
    return ok


def cmd_set() -> None:
    guard_gitignored()
    print(f"Repo: {ROOT}")
    print("Lämna tomt för att hoppa över (befintligt värde behålls).")
    print("Du behöver BARA DeepSeek för att komma igång — de andra kan vänta.\n")

    for key in KEYS:
        if key.generated:
            continue  # eget kommando, klistras aldrig in för hand
        current = read_env(key.files[0]).get(key.name, "")
        marker = " [redan satt]" if current and not looks_placeholder(current) else ""
        print(f"{key.name}{marker}")
        print(f"  {key.blurb}")
        print(f"  Hämtas här: {key.where}")
        value = getpass.getpass("  Klistra in (syns inte): ").strip()
        if not value:
            print("  -> hoppar över\n")
            continue
        if looks_placeholder(value):
            print("  -> VARNING: ser ut som en platshållare, sparar ändå\n")
        for path in key.files:
            upsert(path, key.name, value)
        print(f"  -> sparad i {', '.join(p.name for p in key.files)}\n")

    for path, pairs in FIXED.items():
        for name, value in pairs.items():
            upsert(path, name, value)
    print("Satte LLM_PROVIDER=deepseek, MODEL=deepseek-v4-flash\n")
    cmd_check()


def cmd_new_unlock_key() -> None:
    """Genererar SNAJP_SKILL_UNLOCK_KEY och committar bara dess sha256.

    Nyckeln skrivs ALDRIG till stdout. Den hamnar direkt i den gitignorerade
    snajp-support/.env och existerar därefter bara där. Det är hela poängen:
    en nyckel du har sett är en nyckel som ligger i ett terminaltranskript, och
    repot har redan bränt en Vercel-token på precis det sättet (STATUS.md
    2026-07-30).

    Roterar du nyckeln måste .unlock-hash committas, annars kan ingen annan
    maskin verifiera den.
    """
    guard_gitignored()
    existing = read_env(BACKEND_ENV).get("SNAJP_SKILL_UNLOCK_KEY", "")
    if existing:
        answer = input(
            "SNAJP_SKILL_UNLOCK_KEY finns redan. Rotera den? Den gamla slutar "
            "fungera direkt. [j/N]: "
        ).strip().lower()
        if answer not in ("j", "ja", "y", "yes"):
            print("Avbrutet — nyckeln är oförändrad.")
            return

    key = secrets.token_urlsafe(32)
    upsert(BACKEND_ENV, "SNAJP_SKILL_UNLOCK_KEY", key)

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    UNLOCK_HASH.parent.mkdir(parents=True, exist_ok=True)
    UNLOCK_HASH.write_text(digest + "\n", encoding="utf-8")
    del key  # inget kvar i minnet efter den här punkten som skrivs ut

    print(f"Nyckeln skrevs till {BACKEND_ENV.relative_to(ROOT).as_posix()} (visas inte).")
    print(f"sha256 skrevs till {UNLOCK_HASH.relative_to(ROOT).as_posix()}: {digest}")
    print("\nCOMMITTA agent-core/.unlock-hash. Nyckeln själv committas aldrig.")


def cmd_pull() -> None:
    """Hämtar env från Vercel till .env.local (om de finns där)."""
    guard_gitignored()
    print("Hämtar från Vercel ...")
    result = subprocess.run(
        ["vercel", "env", "pull", str(FRONTEND_ENV), "--yes"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(result.stdout or result.stderr)
    if result.returncode != 0:
        sys.exit("Kunde inte hämta. Kör `vercel login` först, eller sätt nycklarna med --set.")
    cmd_check()


def _vercel() -> str:
    """Sökvägen till Vercel CLI:t.

    På Windows är `vercel` en .cmd-shim, och subprocess utan shell=True hittar
    inte den — den faller på `FileNotFoundError: [WinError 2]`, som inte med ett
    ord nämner vilket program som saknades. shutil.which löser upp shimmen på
    alla tre plattformarna; shell=True hade fungerat men skickar argumenten
    genom en kommandotolk, och ett av argumenten här är en hemlighet.
    """
    found = shutil.which("vercel")
    if not found:
        sys.exit(
            "AVBRYTER: hittar inte Vercel CLI:t i PATH. Installera med "
            "`npm i -g vercel` och logga in med `vercel login`."
        )
    return found


def _shared_environments(name: str, environment: str) -> set[str]:
    """Vilka ANDRA miljöer samma variabelpost gäller för.

    Vercel lagrar en variabel som gäller flera miljöer som EN post. `env rm`
    tar bort posten, inte målet — så att sätta ett preview-värde på en delad
    variabel raderar produktionens. Tom mängd = säkert att skriva över.

    Läser `vercel env ls` och matchar radens miljökolumn. Misslyckas
    uppslaget returneras tomt: spärren ska inte blockera arbete när CLI:t
    krånglar, den ska fånga det kända fallet.
    """
    result = subprocess.run(
        [_vercel(), "env", "ls"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        return set()

    kanda = {"production", "preview", "development"}
    for line in result.stdout.splitlines():
        delar = line.split()
        if not delar or delar[0] != name:
            continue
        miljoer = {d.strip(",").lower() for d in delar[1:]} & kanda
        # Avgörande: bedöm PER RAD. En delad post renderas som EN rad med flera
        # miljöer ("Production, Preview"); två separata poster blir två rader
        # med en miljö var. Att unionera över rader hade gjort det senare —
        # som är helt säkert — omöjligt att skriva till.
        if environment in miljoer and len(miljoer) > 1:
            return miljoer - {environment}
    return set()


def vercel_env_set(name: str, value: str, environment: str) -> bool:
    """Sätter EN variabel i ETT Vercel-scope. Returnerar True vid lyckat.

    Bruten ur cmd_push() för att onboard_tenant.py sätter per-kund-nycklar och
    behöver exakt samma sekvens. Två kopior hade glidit isär, och den här
    hanterar hemligheter.

    `rm` före `add` för att Vercel inte skriver över ett befintligt värde — en
    ren `add` på en variabel som redan finns misslyckas tyst nog för att se ut
    som att den lyckades. Felet ignoreras med flit: variabeln finns oftast inte.
    """
    delade = _shared_environments(name, environment)
    if delade:
        sys.exit(
            f"AVBRYTER: {name} är EN post som gäller {', '.join(sorted(delade | {environment}))}.\n"
            f"`vercel env rm {name} {environment}` tar då bort HELA posten, inte bara "
            f"{environment} — och de andra miljöerna tappar variabeln utan förvarning.\n"
            f"Det hände skarpt 2026-08-15: SNAJP_SUPPORT_URL och SNAJP_INTERNAL_API_KEY "
            f"försvann ur Production när preview-värdena sattes.\n"
            f"Ta bort posten manuellt och lägg till en per miljö först."
        )

    subprocess.run(
        [_vercel(), "env", "rm", name, environment, "--yes"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [_vercel(), "env", "add", name, environment],
        cwd=ROOT,
        input=value + "\n",
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def cmd_push() -> None:
    """Skickar lokala nycklar till Vercel så deployen fungerar.

    Bara nycklar som faktiskt konsumeras av Next-appen (FRONTEND_ENV bland
    dess `files`) är relevanta här. I dagens uppsättning är DEEPSEEK_API_KEY,
    SCRAPEGRAPHAI_API_KEY och GEMINI_API_KEY rena backend/Render-hemligheter
    — de hör inte hemma i Vercel-projektet och pushas därför inte dit.
    """
    vercel_keys = [key for key in KEYS if FRONTEND_ENV in key.files]
    if not vercel_keys:
        print(
            "Inga nycklar är markerade som Vercel-relevanta just nu — alla är "
            "backend/Render-hemligheter. Se tabellen i DEPLOY_KEYS.md för hur de "
            "sätts i Render-dashboarden i stället."
        )
        return

    print("Skickar till Vercel (production + preview). Befintliga värden skrivs över.\n")
    for key in vercel_keys:
        value = read_env(key.files[0]).get(key.name, "")
        if not value or looks_placeholder(value):
            print(f"  {key.name}: hoppar över (saknas lokalt)")
            continue
        for environment in ("production", "preview"):
            ok = vercel_env_set(key.name, value, environment)
            print(f"  {key.name} -> vercel {environment}: {'OK' if ok else 'FEL'}")

    print(
        "\nBackend (Render) sätts separat — Render CLI:t kan inte skriva env utan "
        "en API-token:\n"
        "  Dashboard -> snajp-support -> Environment -> Add Environment Variable\n"
        "  DEEPSEEK_API_KEY, SCRAPEGRAPHAI_API_KEY, LLM_PROVIDER=deepseek, MODEL=deepseek-v4-flash"
    )


#: Nycklar som backend-tjänsten behöver i Railway. Master- och demo-nycklarna
#: står INTE här: de är miljöspecifika med flit och sätts av
#: railway_provision.py, som slumpar en egen per miljö.
RAILWAY_BACKEND_KEYS = ("DEEPSEEK_API_KEY", "GEMINI_API_KEY", "SNAJP_SKILL_UNLOCK_KEY")


def cmd_push_railway() -> None:
    """Skicka backend-nycklarna till BÅDA Railway-miljöerna och verifiera.

    Verifieringen är poängen. En satt variabel bevisar bara att API:t tog emot
    den; att `/health/ready` går från `simulation` till `live` bevisar att
    nyckeln faktiskt går att använda. Skillnaden kostade en hel felsökning.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import json
    import urllib.request

    from railway_provision import (ENVIRONMENTS, env_read, envs_by_name,
                                   services_by_name, set_vars, state, deploy)

    backend = read_env(BACKEND_ENV)
    payload = {}
    for name in RAILWAY_BACKEND_KEYS:
        value = backend.get(name, "")
        if not value:
            print(f"  {name}: saknas lokalt — hoppar över")
            continue
        fault = key_fault(value)
        if fault:
            sys.exit(f"AVBRYTER: {name} {fault}. Sätt om den med `python scripts/keys.py` först.")
        payload[name] = value
    if not payload:
        sys.exit("Inga nycklar att skicka.")
    print(f"skickar: {', '.join(sorted(payload))}")   # namn, aldrig värden

    project = state()
    environments = envs_by_name(project)
    services = services_by_name(project)
    deploys = {}
    for env_name in ENVIRONMENTS:
        if env_name not in environments:
            print(f"  {env_name}: miljön finns inte — hoppar över")
            continue
        env_id = environments[env_name]
        set_vars(services["api"]["id"], env_id, payload)
        deploys[env_name] = deploy(services["api"]["id"], env_id)
        print(f"  {env_name}: satt, deploy {deploys[env_name]}")

    store = env_read()
    print("\nVerifierar mot /health/ready (kan ta en minut per miljö):")
    failed = False
    for env_name in deploys:
        url = store.get(f"RAILWAY_{env_name.upper()}_API_URL")
        if not url:
            print(f"  {env_name}: ingen API-URL i .env.deploy — kan inte verifiera")
            failed = True
            continue
        mode = None
        for _ in range(20):
            try:
                with urllib.request.urlopen(f"{url}/health/ready", timeout=20) as resp:
                    mode = json.load(resp).get("mode")
            except Exception:
                mode = None
            if mode == "live":
                break
        print(f"  {env_name}: mode={mode}")
        if mode != "live":
            failed = True
    if failed:
        sys.exit("Minst en miljö gick inte till live-läge. Se /health/ready för skälet.")
    print("\nBåda miljöerna kör med riktig modell.")


def cmd_set_railway_db() -> None:
    """Railway-motsvarigheten till --set-preview-db. Samma delegering, samma skäl."""
    skript = Path(__file__).resolve().parent / "set_railway_postgres_url.py"
    if not skript.exists():
        sys.exit(f"Hittar inte {skript.name}.")
    raise SystemExit(subprocess.call([sys.executable, str(skript), "--env", "development"]))


def cmd_set_preview_db() -> None:
    """Delegerar till set_preview_postgres_url.py — ingen kopierad logik.

    Skillen (api-key-setup) vill ha EN ingång per projekt, och det är den här
    filen. Men verifieringen mot databasen, valet av sessionsläge framför
    transaktionsläge, och kontrollen att rollen faktiskt får läsa auth.users
    bor i det dedikerade skriptet. Två kopior av den logiken hade glidit isär
    på exakt den punkt där det kostar mest: en anslutning som ser giltig ut men
    fäller speglingen halvvägs.

    Samma tolk används med flit — annars kan psycopg2 saknas i den som startar.
    """
    skript = Path(__file__).resolve().parent / "set_preview_postgres_url.py"
    if not skript.exists():
        sys.exit(f"Hittar inte {skript.name}.")
    raise SystemExit(subprocess.call([sys.executable, str(skript)]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Nyckelhantering för snipra/snajp.")
    parser.add_argument("--check", action="store_true", help="verifiera utan att ändra")
    parser.add_argument("--pull", action="store_true", help="hämta från Vercel")
    parser.add_argument("--push", action="store_true", help="skicka till Vercel")
    parser.add_argument("--push-railway", action="store_true",
                        help="skicka backend-nycklarna till BÅDA Railway-miljöerna och verifiera")
    parser.add_argument(
        "--set-preview-db",
        action="store_true",
        help="sätt PREVIEW_POSTGRES_URL (lösenord via getpass, verifieras mot databasen)",
    )
    parser.add_argument(
        "--set-railway-db",
        action="store_true",
        help="sätt RAILWAY_DEVELOPMENT_PG_* (lösenord via getpass, verifieras mot databasen)",
    )
    parser.add_argument(
        "--new-unlock-key",
        action="store_true",
        help="generera SNAJP_SKILL_UNLOCK_KEY (värdet skrivs aldrig ut)",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if cmd_check() else 1)
    if args.set_preview_db:
        cmd_set_preview_db()
    elif args.set_railway_db:
        cmd_set_railway_db()
    elif args.new_unlock_key:
        cmd_new_unlock_key()
    elif args.pull:
        cmd_pull()
    elif args.push_railway:
        cmd_push_railway()
    elif args.push:
        cmd_push()
    else:
        cmd_set()


if __name__ == "__main__":
    main()
