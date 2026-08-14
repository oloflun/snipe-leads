"""Publicerar agent-core/skills/ till DB-spegeln (INV-SKILL-007).

    python scripts/publish_skills.py --check      # torrkörning
    python scripts/publish_skills.py --publish    # kräver SNAJP_SKILL_UNLOCK_KEY

Git är källa till sanning. Spegeln är en frågbar post över exakt vilken text
en agent_runs-rad producerades ur — inte en uppdateringskanal. Se migration
016 för hela resonemanget.

KODNINGSFÄLLAN, som skriptet vägrar gå i:

build_manifest.py hashar `path.read_bytes()`. Databasen lagrar `text`.
`sha256(content.encode("utf-8"))` är lika med filhashen BARA om filen är
UTF-8 utan BOM och med oförändrade radslut. Det stämmer i dag (verifierat:
414/414 filer är LF/UTF-8/utan BOM, och .gitattributes håller dem så) — men
en klon utan .gitattributes på en maskin med core.autocrlf=true bryter det
för SAMTLIGA rader samtidigt. Utan round-trip-kontrollen nedan får du då 414
rader som alla failar SkillIntegrityError i produktion, med ett felmeddelande
som pekar på fel sak.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "snajp-support"))

from app.agentcore.unlock import SkillLockedError, verify_unlock_key  # noqa: E402
from app.config import get_settings  # noqa: E402

SKILLS_ROOT = ROOT / "agent-core" / "skills"


def collect_rows() -> tuple[list[dict], list[str]]:
    """(rader, problem). Ett problem är alltid blockerande."""
    rows: list[dict] = []
    problems: list[str] = []
    for namespace_dir in sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir()):
        for path in sorted(namespace_dir.rglob("*")):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            relative = str(path.relative_to(namespace_dir)).replace("\\", "/")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                problems.append(f"{namespace_dir.name}/{relative}: inte giltig UTF-8")
                continue
            if text.encode("utf-8") != raw:
                problems.append(
                    f"{namespace_dir.name}/{relative}: round-trippar inte genom "
                    "text/UTF-8 (BOM eller radslut) — spegeln skulle bli overifierbar"
                )
                continue
            rows.append(
                {
                    "namespace": namespace_dir.name,
                    "relative_path": relative,
                    "content": text,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_size": len(raw),
                }
            )
    return rows, problems


def _manifest_is_clean() -> str | None:
    """Publicera aldrig en spegel av ett träd som avviker från sitt eget
    manifest — då hade spegeln varit garanterat overifierbar från start."""
    sys.path.insert(0, str(ROOT / "tests" / "invariants"))
    import test_inv_skill_005 as inv  # noqa: PLC0415

    try:
        inv.test_no_vendored_skill_file_was_modified()
        inv.test_no_skill_file_was_added_or_removed()
        inv.test_manifest_hash_matches_its_own_contents()
    except AssertionError as error:
        return str(error).split("\n")[0]
    return None


async def _publish(rows: list[dict], manifest_hash: str) -> int:
    from app.storage.postgres import PostgresStorage

    database_url = get_settings().database_url
    if not database_url:
        sys.exit("DATABASE_URL är inte satt — spegeln kan bara publiceras mot en riktig databas.")
    storage = await PostgresStorage.connect(database_url)
    try:
        return await storage.publish_skill_files(
            manifest_hash=manifest_hash, rows=rows, published_by="publish_skills.py"
        )
    finally:
        await storage.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="torrkörning")
    parser.add_argument("--publish", action="store_true", help="skriv till DB (kräver nyckel)")
    args = parser.parse_args()

    from app.agentcore.skill_mirror import local_manifest_hash

    manifest_hash = local_manifest_hash()
    rows, problems = collect_rows()

    print(f"manifest_hash={manifest_hash[:16]}...  filer={len(rows)}")
    if problems:
        print("\nBLOCKERANDE PROBLEM:")
        for problem in problems:
            print(f"  {problem}")
        sys.exit(1)

    drift = _manifest_is_clean()
    if drift:
        sys.exit(f"\nAVBRYTER: trädet avviker från manifest.json — {drift}")

    if not args.publish:
        print("Torrkörning OK. Kör med --publish för att skriva.")
        return

    try:
        verify_unlock_key()
    except SkillLockedError as error:
        sys.exit(f"LÅST: {error}")

    added = asyncio.run(_publish(rows, manifest_hash))
    print(f"Publicerat: {added} nya rader (befintliga rader lämnas orörda).")


if __name__ == "__main__":
    main()
