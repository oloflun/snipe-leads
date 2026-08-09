"""INV-SKILL-005 — vendorade skills ändras aldrig i tysthet.

Regeln (användarens uttryckliga instruktion 2026-08-10): vi går INTE in och
ändrar i skillsen. Går output fel ska den finjusteras med TILLÄGGS-
instruktioner ovanpå skillen, aldrig genom att redigera skillens innehåll.

Den regeln stod tidigare bara som en fälla i HANDOFF.md, alltså som en
förhoppning om att nästa agent läser rätt rad. Här är den mekanisk i
stället: varje fil under agent-core/skills/ jämförs mot sitt sha256 i
agent-core/manifest.json.

Testet förbjuder inte en ändring — det gör den omöjlig att göra OMÄRKT.
Att ändra en skill kräver att man kör `python agent-core/build_manifest.py`,
vilket ger ny `manifest_hash`, alltså en ny baseline (Del B/D) som syns i
diffen och i varje `pack_version` som loggas till agent_runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "agent-core" / "skills"
MANIFEST = ROOT / "agent-core" / "manifest.json"

_REBUILD_HINT = (
    "\n\nOm ändringen var AVSIKTLIG och absolut nödvändig: kör "
    "`python agent-core/build_manifest.py` och committa manifestet i samma "
    "commit, så att baseline-bytet blir synligt.\n"
    "Om du bara ville justera agentens output: gör det med tilläggs"
    "instruktioner i playbookens task/case_context, INTE i skillen."
)


def _manifest_files() -> dict[str, str]:
    """namnrymd/relativ-sökväg -> sha256, plattat över alla namnrymder."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        f"{namespace}/{rel}": digest
        for namespace, entry in manifest["namespaces"].items()
        for rel, digest in entry["files"].items()
    }


def _disk_files() -> dict[str, str]:
    """Samma vandring som build_manifest.build() — annars jämför vi äpplen
    med päron och testet blir meningslöst."""
    found: dict[str, str] = {}
    for namespace_dir in sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir()):
        for file in sorted(namespace_dir.rglob("*")):
            if file.is_file():
                rel = str(file.relative_to(namespace_dir)).replace("\\", "/")
                found[f"{namespace_dir.name}/{rel}"] = hashlib.sha256(
                    file.read_bytes()
                ).hexdigest()
    return found


def test_no_vendored_skill_file_was_modified():
    expected, actual = _manifest_files(), _disk_files()
    changed = sorted(
        path
        for path in expected.keys() & actual.keys()
        if expected[path] != actual[path]
    )
    assert not changed, f"Ändrade skill-filer: {changed}{_REBUILD_HINT}"


def test_no_skill_file_was_added_or_removed():
    expected, actual = _manifest_files(), _disk_files()
    added = sorted(actual.keys() - expected.keys())
    removed = sorted(expected.keys() - actual.keys())
    assert not added and not removed, (
        f"Tillagda: {added} · Borttagna: {removed}{_REBUILD_HINT}"
    )


def test_manifest_hash_matches_its_own_contents():
    """manifest_hash är det som hamnar i pack_version och därmed i varje
    agent_runs-rad. Är den inte härledd ur filerna pekar revisionsloggen på
    en baseline som aldrig funnits."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    flat = json.dumps(
        {ns: entry["files"] for ns, entry in manifest["namespaces"].items()},
        sort_keys=True,
    ).encode("utf-8")
    assert hashlib.sha256(flat).hexdigest() == manifest["manifest_hash"], (
        "manifest_hash stämmer inte med namespaces.files — manifestet är "
        "handredigerat eller halvt ombyggt." + _REBUILD_HINT
    )
