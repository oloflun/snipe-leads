"""Nyckelhantering — ett verktyg, fungerar från vilken katalog som helst.

    python "C:\\Users\\Anton L\\snipe-leads\\scripts\\keys.py"          # sätt + verifiera
    python .../scripts/keys.py --check                                  # bara verifiera
    python .../scripts/keys.py --pull                                   # hämta från Vercel
    python .../scripts/keys.py --push                                   # skicka till Vercel

Sökvägar löses ur __file__, aldrig ur cwd — skriptet kan köras varifrån som
helst. Värden läses med getpass (syns aldrig, hamnar aldrig i shell-historiken)
och skrivs bara till gitignorerade filer.

Nycklarna hamnar ALDRIG i databasen (INV-SEC-006 / plan G5). Se DEPLOY_KEYS.md.
"""

from __future__ import annotations

import argparse
import getpass
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV = ROOT / "snajp-support" / ".env"
FRONTEND_ENV = ROOT / ".env.local"


class Key:
    def __init__(self, name, files, blurb, *, required, where):
        self.name, self.files, self.blurb = name, files, blurb
        self.required, self.where = required, where


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
            subprocess.run(
                ["vercel", "env", "rm", key.name, environment, "--yes"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                ["vercel", "env", "add", key.name, environment],
                cwd=ROOT,
                input=value + "\n",
                capture_output=True,
                text=True,
            )
            state = "OK" if result.returncode == 0 else f"FEL: {result.stderr.strip()[:80]}"
            print(f"  {key.name} -> vercel {environment}: {state}")

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
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if cmd_check() else 1)
    if args.pull:
        cmd_pull()
    elif args.push:
        cmd_push()
    else:
        cmd_set()


if __name__ == "__main__":
    main()
