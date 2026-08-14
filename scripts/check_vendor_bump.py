"""INV-SKILL-006 — en vendorad skill ändras bara med deklarerad vendor-bump.

    python scripts/check_vendor_bump.py --base origin/development

PROBLEMET DEN LÖSER, och gränsen för vad den kan lösa:

INV-SKILL-005 gör en skill-ändring synlig (builden fäller tills manifestet
byggs om). SNAJP_SKILL_UNLOCK_KEY gör den ansträngande (nyckeln finns på en
maskin). Ingen av dem säger något om AVSIKTEN — och avsikten är hela
skillnaden mellan de två fallen:

  LEGITIMT:  vi hämtar hem en ny version från uppströms (coreyhaines31/
             marketingskills eller anthropics/knowledge-work-plugins).
  FEL:       någon "nudgar bara en mening" i mk:cold-email för att få
             snyggare output, i stället för att skriva en overlay.

Bytes-diffen ser IDENTISK ut i båda fallen. Inget test kan skilja dem åt.

Vad som däremot går: göra den felaktiga vägen dyr att gå TYST. Den här
grinden kräver en trailer `VENDOR-BUMP: <uppströms-commit-sha>` i något
commitmeddelande så fort agent-core/skills/** ändrats. Effekten är att
"jag nudgade en mening" blir "jag måste skriva att jag re-vendorat från
uppströms och ange vilken commit". Det är en lögn en människa måste skriva
med flit, inte en lint man tystar med en flagga.

Overlays (agent-core/overlays/) och AGENTS.md träffas ALDRIG av grinden —
de är vår egen text och den sanktionerade finjusteringsytan.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKILLS_PREFIX = "agent-core/skills/"
# Sha eller 'n/a' med motivering. 'n/a' finns för egna snajp:-skills som inte
# har något uppströmsrepo — men den kräver fortfarande att någon skriver den.
_TRAILER_RE = re.compile(
    r"^VENDOR-BUMP:\s*(?P<ref>[0-9a-f]{7,40}|n/a\b.*\S)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def requires_vendor_bump(
    changed_files: Sequence[str], commit_messages: Sequence[str]
) -> str | None:
    """Felsträng om skills ändrats utan trailer. None = OK.

    Ren funktion — inga git-anrop, inga filsystemsläsningar — så den kan
    testas mot syntetiska fillistor utan att bygga upp ett repo.
    """
    touched = sorted(
        path for path in changed_files if path.replace("\\", "/").startswith(SKILLS_PREFIX)
    )
    if not touched:
        return None

    if any(_TRAILER_RE.search(message or "") for message in commit_messages):
        return None

    listing = "\n".join(f"  {path}" for path in touched[:20])
    if len(touched) > 20:
        listing += f"\n  ... och {len(touched) - 20} till"
    return (
        f"{len(touched)} fil(er) under {SKILLS_PREFIX} ändrade utan "
        f"VENDOR-BUMP-trailer:\n{listing}\n\n"
        "Om detta är en RE-VENDORING från uppströms, lägg till en rad i\n"
        "commitmeddelandet:\n"
        "    VENDOR-BUMP: <uppströms-commit-sha>\n"
        "(eller 'VENDOR-BUMP: n/a — <motivering>' för egna snajp:-skills)\n\n"
        "Om du bara ville justera agentens OUTPUT: backa ändringen och skriv\n"
        "en overlay i agent-core/overlays/ i stället. Den binds till steget\n"
        "med PlaybookStep(overlay=...), kräver ingen nyckel, och ändrar inte\n"
        "baseline för någon kund. Det är hela poängen med overlay-lagret."
    )


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} misslyckades: {result.stderr.strip()}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/development", help="jämförelsereferens")
    args = parser.parse_args()

    changed = [line for line in _git("diff", "--name-only", f"{args.base}...HEAD").splitlines() if line]
    messages = _git("log", "--format=%B", f"{args.base}..HEAD").split("\x00")
    if not messages or not messages[0].strip():
        messages = [_git("log", "--format=%B", f"{args.base}..HEAD")]

    problem = requires_vendor_bump(changed, messages)
    if problem:
        sys.exit(f"INV-SKILL-006: {problem}")
    print("INV-SKILL-006 OK.")


if __name__ == "__main__":
    main()
