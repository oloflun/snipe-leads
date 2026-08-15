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
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV = ROOT / "snajp-support" / ".env"
FRONTEND_ENV = ROOT / ".env.local"
UNLOCK_HASH = ROOT / "agent-core" / ".unlock-hash"


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
]

FIXED = {BACKEND_ENV: {"LLM_PROVIDER": "deepseek", "MODEL": "deepseek-v4-flash"}}


def looks_placeholder(value: str) -> bool:
    """Samma heuristik som app/config.py:is_simulation()."""
    return len(value) < 20 or "..." in value or "din-" in value


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


def vercel_env_set(name: str, value: str, environment: str) -> bool:
    """Sätter EN variabel i ETT Vercel-scope. Returnerar True vid lyckat.

    Bruten ur cmd_push() för att onboard_tenant.py sätter per-kund-nycklar och
    behöver exakt samma sekvens. Två kopior hade glidit isär, och den här
    hanterar hemligheter.

    `rm` före `add` för att Vercel inte skriver över ett befintligt värde — en
    ren `add` på en variabel som redan finns misslyckas tyst nog för att se ut
    som att den lyckades. Felet ignoreras med flit: variabeln finns oftast inte.
    """
    subprocess.run(
        ["vercel", "env", "rm", name, environment, "--yes"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["vercel", "env", "add", name, environment],
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Nyckelhantering för snipra/snajp.")
    parser.add_argument("--check", action="store_true", help="verifiera utan att ändra")
    parser.add_argument("--pull", action="store_true", help="hämta från Vercel")
    parser.add_argument("--push", action="store_true", help="skicka till Vercel")
    parser.add_argument(
        "--new-unlock-key",
        action="store_true",
        help="generera SNAJP_SKILL_UNLOCK_KEY (värdet skrivs aldrig ut)",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if cmd_check() else 1)
    if args.new_unlock_key:
        cmd_new_unlock_key()
    elif args.pull:
        cmd_pull()
    elif args.push:
        cmd_push()
    else:
        cmd_set()


if __name__ == "__main__":
    main()
