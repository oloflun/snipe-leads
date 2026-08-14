"""INV-SKILL-007 — DB-speglad skill verifieras per fil och felar stängt.

Läsvägen för `skill_source="db"`. Varje rad kontrolleras mot sha256 i det
UTCHECKADE agent-core/manifest.json innan innehållet returneras. Matchar den
inte kastas SkillIntegrityError — ingen fallback, ingen varning-och-fortsätt.

Varför fail closed är hela poängen: spegeln finns för att kunna svara på
"vilken text producerade den här agent_runs-raden?". En spegel som tyst kan
leverera ANNAN text än manifestet säger besvarar inte den frågan — den ljuger
om den, vilket är sämre än att inte finnas.

Versionsskev finns inte som problem: uppslagningen sker alltid på den lokalt
utcheckade manifest_hash. En nyare publicering ligger under ett annat hash och
är osynlig. Det enda felet som kan uppstå är "mina rader saknas", och det har
ett tydligt svar (kör scripts/publish_skills.py).

Uppslagningen är SYNKRON medan storage-lagret är async. Det är avsiktligt:
registry.load_full_skill anropas från PlaybookStep.render(), som körs vid
modulimport när playbooks konstrueras. Att göra hela den kedjan async för en
opt-in-funktion vore fel avvägning. Raderna hämtas därför via en cache som
fylls en gång per process.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from functools import lru_cache
from typing import Any

from .registry import (
    AGENT_CORE_ROOT,
    SkillIntegrityError,
    SkillMirrorUnavailableError,
    UnknownReferenceError,
)

_MANIFEST = AGENT_CORE_ROOT / "manifest.json"

# Processlokal spegel: {(namespace, relativ_sökväg): content}
_ROWS: dict[tuple[str, str], str] = {}
_LOADED = False


@lru_cache(maxsize=1)
def local_manifest_hash() -> str:
    if not _MANIFEST.is_file():
        return ""
    return json.loads(_MANIFEST.read_text(encoding="utf-8")).get("manifest_hash", "")


@lru_cache(maxsize=1)
def _pinned_hashes() -> dict[tuple[str, str], str]:
    """{(namnrymd, relativ_sökväg): sha256} ur det utcheckade manifestet."""
    if not _MANIFEST.is_file():
        return {}
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    return {
        (namespace, rel): digest
        for namespace, entry in manifest.get("namespaces", {}).items()
        for rel, digest in entry.get("files", {}).items()
    }


def load_rows(rows: list[dict[str, Any]]) -> None:
    """Fyller processens spegel. Anropas av uppstartskoden (eller av tester).

    Tar redan hämtade rader i stället för att göra I/O själv, så modulen
    förblir synkron och testbar utan databas."""
    global _LOADED
    _ROWS.clear()
    for row in rows:
        _ROWS[(row["namespace"], row["relative_path"])] = row["content"]
    _LOADED = True


def clear() -> None:
    global _LOADED
    _ROWS.clear()
    _LOADED = False
    local_manifest_hash.cache_clear()
    _pinned_hashes.cache_clear()


def mirror_has_skill(namespace: str, relative_path: str) -> bool:
    """Kastar hellre än returnerar False när spegeln inte är laddad alls.

    Skillnaden är inte akademisk: returnerar den False får anroparen ett
    UnknownSkillError vars felmeddelande innehåller en FILSYSTEMSSÖKVÄG, och
    den som felsöker börjar leta efter en fil som saknas på disk — medan det
    verkliga problemet är att spegeln aldrig publicerades. Repot har redan
    bränt en session på en felsökning som började i fel ände (se HANDOFF.md
    fälla 8), och det är exakt samma felklass."""
    if not _LOADED:
        raise SkillMirrorUnavailableError(
            "skill_source='db' men spegeln är inte laddad. Kör "
            "scripts/publish_skills.py --publish, och se till att "
            "uppstartskoden anropar skill_mirror.load_rows()."
        )
    return (namespace, relative_path) in _ROWS


def list_mirrored_references(namespace: str, skill_id: str) -> list[str]:
    """Samma ordning och samma suffixfilter som filsystemsvägen."""
    prefix = f"{skill_id}/references/"
    return sorted(
        path[len(skill_id) + 1 :]
        for (ns, path) in _ROWS
        if ns == namespace and path.startswith(prefix) and path.endswith((".md", ".csv", ".txt"))
    )


def read_mirrored_file(namespace: str, relative_path: str) -> str:
    expected = _pinned_hashes().get((namespace, relative_path))
    if expected is None:
        raise UnknownReferenceError(
            f"{namespace}/{relative_path} finns inte i agent-core/manifest.json — "
            "spegeln kan bara leverera filer som är pinnade."
        )

    if not _LOADED:
        raise SkillMirrorUnavailableError(
            "Spegeln är inte laddad. Kör scripts/publish_skills.py --publish och "
            "se till att uppstartskoden anropar skill_mirror.load_rows()."
        )

    content = _ROWS.get((namespace, relative_path))
    if content is None:
        raise SkillMirrorUnavailableError(
            f"Ingen spegelrad för manifest_hash={local_manifest_hash()[:12]} "
            f"({namespace}/{relative_path}). Kör scripts/publish_skills.py."
        )

    actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise SkillIntegrityError(
            f"{namespace}/{relative_path}: DB-raden matchar inte manifest.json "
            f"(väntade {expected[:12]}, fick {actual[:12]}). Vägrar köra."
        )
    return content
