"""Enda sanktionerade vägen att regenerera agent-core/manifest.json.

    python scripts/unlock_skills.py --check              # vad har ändrats?
    python scripts/unlock_skills.py --rebuild-manifest   # kräver nyckeln

VARFÖR DET HÄR SKRIPTET FINNS I STÄLLET FÖR `python agent-core/build_manifest.py`:

INV-SKILL-005 gör en tyst skill-ändring SYNLIG — den fäller builden. Men den
gör den inte SVÅR. Vem som helst (inklusive en agent mitt i en lång körning)
kunde köra build_manifest.py, få grönt, och ha ändrat baseline för varje kund
utan att någon fattat ett beslut.

Grinden här kräver SNAJP_SKILL_UNLOCK_KEY, som bara finns i snajp-support/.env
på en enda maskin. Det är ingen säkerhetsmekanism — det är en AVSIKTLIGHETS-
grind. Se app/agentcore/unlock.py.

Behöver du bara justera agentens OUTPUT: rör inte skillsen. Skriv en overlay i
agent-core/overlays/ och bind den till steget med `PlaybookStep(overlay=...)`.
Det är den sanktionerade finjusteringsytan, den kräver ingen nyckel, och den
ändrar inte baseline för någon kund.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "snajp-support"))
sys.path.insert(0, str(ROOT / "agent-core"))

from app.agentcore.unlock import SkillLockedError, verify_unlock_key  # noqa: E402

import build_manifest  # noqa: E402  (agent-core/build_manifest.py)

MANIFEST = ROOT / "agent-core" / "manifest.json"


def _current_manifest() -> dict:
    if not MANIFEST.is_file():
        return {"manifest_hash": "", "namespaces": {}}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _flat(manifest: dict) -> dict[str, str]:
    return {
        f"{namespace}/{rel}": digest
        for namespace, entry in manifest.get("namespaces", {}).items()
        for rel, digest in entry.get("files", {}).items()
    }


def _diff() -> tuple[dict, list[str], list[str], list[str]]:
    """(nytt manifest, ändrade, tillagda, borttagna) relativt det incheckade."""
    fresh = build_manifest.build()
    before, after = _flat(_current_manifest()), _flat(fresh)
    changed = sorted(p for p in before.keys() & after.keys() if before[p] != after[p])
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    return fresh, changed, added, removed


def _report(fresh: dict, changed: list[str], added: list[str], removed: list[str]) -> bool:
    old_hash = _current_manifest().get("manifest_hash", "")
    if not (changed or added or removed):
        print("Inga skillnader mot det incheckade manifestet.")
        print(f"manifest_hash={old_hash}")
        return False
    for label, paths in (("ÄNDRADE", changed), ("TILLAGDA", added), ("BORTTAGNA", removed)):
        if paths:
            print(f"\n{label} ({len(paths)}):")
            for path in paths[:40]:
                print(f"  {path}")
            if len(paths) > 40:
                print(f"  ... och {len(paths) - 40} till")
    print(f"\nmanifest_hash  {old_hash[:16] or '(inget)'} -> {fresh['manifest_hash'][:16]}")
    print(
        "\nVARNING: en ny manifest_hash är en NY BASELINE. Den går in i varje\n"
        "pack_version som loggas till agent_runs, och en pinnad kund når den\n"
        "inte förrän någon flyttar pinnen (INV-AGENT-002)."
    )
    return True


def cmd_check() -> int:
    fresh, changed, added, removed = _diff()
    dirty = _report(fresh, changed, added, removed)
    if dirty:
        print(
            "\nÄr det här en RE-VENDORING från uppströms? Då krävs också en\n"
            "'VENDOR-BUMP: <uppströms-commit>'-trailer i commitmeddelandet\n"
            "(INV-SKILL-006), annars fäller CI:t på pull requesten."
        )
    return 0


def cmd_rebuild() -> int:
    try:
        verify_unlock_key()
    except SkillLockedError as error:
        print(f"LÅST: {error}", file=sys.stderr)
        return 1

    fresh, changed, added, removed = _diff()
    if not _report(fresh, changed, added, removed):
        return 0

    answer = input("\nSkriv nytt manifest? [j/N]: ").strip().lower()
    if answer not in ("j", "ja", "y", "yes"):
        print("Avbrutet — manifestet är oförändrat.")
        return 1

    MANIFEST.write_text(
        json.dumps(fresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    total = sum(ns["file_count"] for ns in fresh["namespaces"].values())
    print(f"\nSkrev {MANIFEST.relative_to(ROOT).as_posix()} ({total} filer).")
    print("Committa manifestet i SAMMA commit som skill-ändringen.")
    if changed or added or removed:
        print("Glöm inte 'VENDOR-BUMP: <uppströms-commit>' i commitmeddelandet.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="visa diff utan att skriva")
    parser.add_argument(
        "--rebuild-manifest", action="store_true", help="skriv nytt manifest (kräver nyckel)"
    )
    args = parser.parse_args()
    if args.rebuild_manifest:
        sys.exit(cmd_rebuild())
    sys.exit(cmd_check())


if __name__ == "__main__":
    main()
