"""Genererar agent-core/manifest.json.

Manifestets sha256 per fil ÄR baseline-versionen (plan Del D) — en ändrad
bokstav i en vendorad skill ger en ny manifest_hash, och därmed en ny
baseline som en pinnad kund inte når förrän den passerat evalgrinden
(Del B). Körs manuellt efter varje vendoring:

    python agent-core/build_manifest.py

Inte en del av verify.yml — manifestet är källdata som checkas in, inte
något CI härleder på nytt (skulle annars falla på varje ordagrann
whitespace-skillnad i en vendorad tredjepartsfil).

KÖRS INTE LÄNGRE DIREKT. `python agent-core/build_manifest.py` kräver sedan
2026-08-14 SNAJP_SKILL_UNLOCK_KEY och hänvisar till scripts/unlock_skills.py,
som visar diffen och kräver en bekräftelse innan den skriver. Skälet: att
regenerera manifestet är att byta baseline för varje kund, och det var
tidigare ett kommando vem som helst kunde köra av misstag mitt i något annat.

Grinden ligger i `__main__`, ALDRIG i `build()` — testerna och
unlock_skills.py måste kunna anropa `build()` fritt för att räkna ut vad som
skulle ändras utan att ha nyckeln.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_ROOT = ROOT / "skills"

# Källa och låst commit per namnrymd (Del D — "Vendoras med låst commit").
SOURCES = {
    "mk": {
        "repo": "https://github.com/coreyhaines31/marketingskills",
        "commit": "7868cb9251fad80a73d26e488a5ad5f6c4a9f335",
    },
    "cs": {
        "repo": "https://github.com/anthropics/knowledge-work-plugins",
        "commit": "5ee4541fa29fc41808ef176cf272ff0ccc921246",
        "subdir": "customer-support/skills",
    },
    "sa": {
        "repo": "https://github.com/anthropics/knowledge-work-plugins",
        "commit": "5ee4541fa29fc41808ef176cf272ff0ccc921246",
        "subdir": "sales/skills",
    },
    "snajp": {
        "repo": "mixed — se per-skill 'source' nedan, egna skills utan uppströmsrepo saknar commit",
        "skills": {
            "humanizer": {
                "repo": "vendorad manuellt, ingen lokal git-historik att peka på",
            },
            "humanizer-svenska": {
                "repo": "https://github.com/nordefors-max/claude-humanizer-svenska",
                "commit": "81a8768e8f32778de3b0f7454fdc0ef0959178ca",
            },
        },
    },
}


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    namespaces = {}
    for namespace_dir in sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir()):
        namespace = namespace_dir.name
        files = {}
        for file in sorted(namespace_dir.rglob("*")):
            if file.is_file():
                rel = str(file.relative_to(namespace_dir)).replace("\\", "/")
                files[rel] = _hash_file(file)
        entry = dict(SOURCES.get(namespace, {}))
        entry["file_count"] = len(files)
        entry["files"] = files
        namespaces[namespace] = entry

    # Ett enda hash över hela trädet — det som faktiskt förändras när NÅGON
    # vendorad fil ändras, oavsett namnrymd. Detta är manifest_hash Del B
    # refererar till för pack-versionering.
    flat = json.dumps(
        {ns: entry["files"] for ns, entry in namespaces.items()}, sort_keys=True
    ).encode("utf-8")
    manifest_hash = hashlib.sha256(flat).hexdigest()

    return {
        "generated_by": "agent-core/build_manifest.py",
        "manifest_hash": manifest_hash,
        "namespaces": namespaces,
    }


if __name__ == "__main__":
    import sys

    # Avsiktlighetsgrind. Ligger här och inte i build() — build() måste
    # förbli fritt anropbar för tester och för unlock_skills.py:s diff.
    sys.path.insert(0, str(ROOT.parent / "snajp-support"))
    from app.agentcore.unlock import SkillLockedError, verify_unlock_key

    try:
        verify_unlock_key()
    except SkillLockedError as error:
        sys.exit(
            f"LÅST: {error}\n\n"
            "Använd scripts/unlock_skills.py — den visar vad som ändrats och "
            "kräver en bekräftelse innan baseline byts:\n"
            "    python scripts/unlock_skills.py --check\n"
            "    python scripts/unlock_skills.py --rebuild-manifest"
        )

    manifest = build()
    out = ROOT / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total_files = sum(ns["file_count"] for ns in manifest["namespaces"].values())
    print(f"manifest_hash={manifest['manifest_hash']}")
    print(f"{total_files} filer över {len(manifest['namespaces'])} namnrymder -> {out}")
