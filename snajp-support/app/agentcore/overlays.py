"""Instruktionslagret: global AGENTS.md + per-steg overlays.

DEN SANKTIONERADE FINJUSTERINGSYTAN. INV-SKILL-005 säger "justera output med
tilläggsinstruktioner ovanpå skillen, aldrig i skillen" — men fram till nu
fanns ingen anvisad plats för de tilläggsinstruktionerna, så de hamnade som
f-strängar mitt i leads_agent.py där ingen hittade dem och ingen versionerade
dem. Det här är platsen.

Tre lager av VÅR text, med olika räckvidd:

  agent-core/AGENTS.md          gäller varje steg, varje playbook, varje kund.
                                OPINNAD — ändras den slår den igenom överallt
                                direkt. Därför bara policy (sanning, säkerhet),
                                aldrig ton eller stil.

  agent-core/overlays/<n>.md    binds till enskilda steg via
                                PlaybookStep(overlay="..."). Pinnad via
                                overlay_hash i pack_version.

  (kundens SOUL)                se app/leads/soul.py — KUNDSKRIVEN text, och
                                därför i USER-position, aldrig här.

Overlays nycklas på SYFTE, inte på skill: samma overlay ("inget LinkedIn, ren
text, språkläget") gäller alla fyra stegen i OUTREACH_V1. Skill-nyckling hade
tvingat fram duplicering, och duplicerad tuning divergerar.

Katalogen ligger under agent-core/ (så "redigerade du skillen eller la du till
en overlay?" är en enda blick i diffen) men UTANFÖR skills/ — build_manifest.py
rör den inte, INV-SKILL-005 gäller den inte, ingen nyckel krävs.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from .registry import AGENT_CORE_ROOT, SkillRegistryError

OVERLAYS_ROOT = AGENT_CORE_ROOT / "overlays"
AGENTS_MD = AGENT_CORE_ROOT / "AGENTS.md"

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)?$")


class UnknownOverlayError(SkillRegistryError):
    """Overlay-namnet finns inte. Kastas vid PlaybookStep-konstruktion, alltså
    vid modulimport, alltså i CI — aldrig först i produktion."""


def parse_overlay_name(name: str) -> Path:
    if not _NAME_RE.match(name):
        raise UnknownOverlayError(
            f"Ogiltigt overlay-namn {name!r}. Tillåtet: gemener, siffror, "
            "bindestreck, valfritt ett '/' för gruppering."
        )
    path = OVERLAYS_ROOT / f"{name}.md"
    if not path.is_file():
        raise UnknownOverlayError(f"Overlayen {name!r} finns inte ({path}).")
    return path


def load_overlay(name: str) -> str:
    return parse_overlay_name(name).read_text(encoding="utf-8")


def load_global_instructions() -> str:
    """agent-core/AGENTS.md, eller tom sträng om filen saknas.

    Medvetet tolerant: ett saknat globalt policylager ska inte döda varje
    agentanrop. Skills är motsatsen — de MÅSTE finnas, eftersom ett steg utan
    sin skill inte utför det steget alls."""
    if not AGENTS_MD.is_file():
        return ""
    return AGENTS_MD.read_text(encoding="utf-8")


def _hash_tree(paths: list[Path], root: Path) -> str:
    """Samma konstruktion som build_manifest: sha256 över {relsökväg: sha256}."""
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def overlay_hash() -> str:
    """Beräknas ur DISK vid körning, inte ur en incheckad manifestfil.

    Overlays är fritt redigerbara och få. Ett byggsteg hade varit friktion
    utan nytta, och ett manifest som kan bli inaktuellt är sämre än inget
    manifest — det påstår något som inte är sant."""
    if not OVERLAYS_ROOT.is_dir():
        return hashlib.sha256(b"{}").hexdigest()
    return _hash_tree([p for p in OVERLAYS_ROOT.rglob("*.md") if p.is_file()], OVERLAYS_ROOT)


@lru_cache(maxsize=1)
def global_hash() -> str:
    if not AGENTS_MD.is_file():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(AGENTS_MD.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def manifest_hash() -> str:
    """agent-core/manifest.json:s manifest_hash — den vendorade baselinen."""
    path = AGENT_CORE_ROOT / "manifest.json"
    if not path.is_file():
        return ""
    return json.loads(path.read_text(encoding="utf-8")).get("manifest_hash", "")


def pack_version(playbook_name: str) -> str:
    """'<manifest[:12]>+<overlay[:8]>+<global[:8]>:<playbook>'

    Alla tre hasharna måste med. Den vendorade baselinen är låst, men tuning-
    och policylagren är fritt redigerbara — utan dem i pack_version går en
    körning inte att reproducera, och agent_runs pekar på en baseline som inte
    ensam förklarar vad modellen faktiskt läste (INV-AUDIT-001)."""
    return f"{manifest_hash()[:12]}+{overlay_hash()[:8]}+{global_hash()[:8]}:{playbook_name}"


def cache_clear() -> None:
    """För tester som skriver overlay-filer och behöver hasharna omräknade."""
    overlay_hash.cache_clear()
    global_hash.cache_clear()
    manifest_hash.cache_clear()
