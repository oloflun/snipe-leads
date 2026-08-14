"""Namnrymdsregistret för agent-core/skills/ (mk:/cs:/sa:/snajp:).

Namnrymden är inte kosmetisk (plan Del D): mk:customer-research (research om
kundens kunder, körs vid onboarding) och cs:customer-research (research för
ett enskilt supportärende, körs per ärende) är olika skills som råkar dela
namn. Ett oprefixat skill-namn är en bugg, inte en bekvämlighet —
parse_skill_name kastar direkt på det. INV-SKILL-001.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# snajp-support/app/agentcore/registry.py -> repo-root/agent-core
AGENT_CORE_ROOT = Path(__file__).resolve().parents[3] / "agent-core"
SKILLS_ROOT = AGENT_CORE_ROOT / "skills"
NAMESPACES = ("mk", "cs", "sa", "snajp")

_NAME_RE = re.compile(r"^([a-z]+):([a-z0-9][a-z0-9-]*)$")


class SkillRegistryError(ValueError):
    """Basklass — alla registerfel är avsiktliga kontrollerade undantag, inte prompt-önskningar."""


class UnprefixedSkillNameError(SkillRegistryError):
    pass


class UnknownSkillError(SkillRegistryError):
    pass


class UnknownReferenceError(SkillRegistryError):
    pass


class SkillIntegrityError(SkillRegistryError):
    """DB-spegelns rad matchar inte det pinnade manifestet.

    FAIL CLOSED. Ingen fallback till filsystemet, ingen varning-och-fortsätt:
    en manipulerad rad får aldrig tyst ändra agentens beteende, och en tyst
    ändring är exakt vad hela INV-SKILL-005-maskineriet finns för att förhindra.
    """


class SkillMirrorUnavailableError(SkillRegistryError):
    """Ingen spegelrad för den utcheckade manifest_hash. Kör publish_skills.py."""


@dataclass(frozen=True)
class SkillRef:
    namespace: str
    skill_id: str

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}:{self.skill_id}"

    @property
    def dir(self) -> Path:
        return SKILLS_ROOT / self.namespace / self.skill_id


# -- De tre sömmarna mot lagringen -----------------------------------------
#
# Hela ytan mot "var kommer skill-texten ifrån" är: finns SKILL.md, ge mig
# bytes för en sökväg, och lista references/. Tre funktioner, ingen ABC och
# ingen pluginarkitektur — det vore tre lager abstraktion runt en dict-lookup.
#
# Backend väljs av settings.skill_source och defaultar till "filesystem" i
# ALL miljö. Se migration 016 för varför DB-vägen är opt-in.


def _mirror_backend() -> str:
    try:
        from ..config import get_settings

        return get_settings().skill_source
    except Exception:  # noqa: BLE001 — utan config är filsystemet rätt svar
        return "filesystem"


def _skill_md_exists(ref: SkillRef) -> bool:
    if _mirror_backend() == "db":
        from .skill_mirror import mirror_has_skill

        return mirror_has_skill(ref.namespace, f"{ref.skill_id}/SKILL.md")
    return (ref.dir / "SKILL.md").is_file()


def _read_skill_file(ref: SkillRef, relative_path: str) -> str:
    """Bytes för EN fil. Verifieringen mot manifestet sitter inne här, alltså
    FÖRE varje parts.append i load_full_skill — aldrig efter konkateneringen,
    då hade en manipulerad references-fil redan hunnit blandas in i texten."""
    if _mirror_backend() == "db":
        from .skill_mirror import read_mirrored_file

        return read_mirrored_file(ref.namespace, f"{ref.skill_id}/{relative_path}")
    path = ref.dir / relative_path
    if not path.is_file():
        raise UnknownReferenceError(f"Filen '{relative_path}' finns inte i {ref.qualified_name} ({path}).")
    return path.read_text(encoding="utf-8")


def _list_reference_files(ref: SkillRef) -> list[str]:
    """Relativa sökvägar under references/, sorterade — exakt samma ordning
    och samma suffixfilter som det gamla sorted(rglob)."""
    if _mirror_backend() == "db":
        from .skill_mirror import list_mirrored_references

        return list_mirrored_references(ref.namespace, ref.skill_id)
    references_dir = ref.dir / "references"
    if not references_dir.is_dir():
        return []
    return [
        path.relative_to(ref.dir).as_posix()
        for path in sorted(references_dir.rglob("*"))
        if path.is_file() and path.suffix in (".md", ".csv", ".txt")
    ]


def parse_skill_name(name: str) -> SkillRef:
    """'mk:cold-email' -> SkillRef. Kastar på varje namn utan namnrymdsprefix,
    okänd namnrymd, eller en skill som inte finns i registret."""
    match = _NAME_RE.match(name)
    if not match:
        if ":" not in name:
            raise UnprefixedSkillNameError(
                f"Skill-namn måste vara namnrymdsprefixat (t.ex. 'mk:{name}') — fick oprefixat '{name}'."
            )
        raise SkillRegistryError(f"Ogiltigt skill-namnformat: '{name}'.")
    namespace, skill_id = match.groups()
    if namespace not in NAMESPACES:
        raise UnknownSkillError(f"Okänd namnrymd '{namespace}' i '{name}'. Giltiga: {NAMESPACES}.")
    ref = SkillRef(namespace=namespace, skill_id=skill_id)
    if not _skill_md_exists(ref):
        raise UnknownSkillError(f"Skill '{name}' finns inte i registret ({ref.dir}).")
    return ref


def load_skill_md(name: str) -> str:
    """Enbart SKILL.md. De flesta anrop vill load_full_skill (SKILL.md +
    references/) — den här finns för de fall en referens uttryckligen INTE
    ska följa med (t.ex. jämförelsetester i test_registry.py)."""
    ref = parse_skill_name(name)
    return _read_skill_file(ref, "SKILL.md")


def load_full_skill(name: str) -> str:
    """SKILL.md + alla filer under references/, i sorterad ordning. Detta är
    vad 'hel skill' (oskopad laddning) betyder i Del C — planen beskriver
    explicit fall som 'mk:offers + alla 7 references' som en odelad
    injektion, inte SKILL.md ensamt med olänkade referenser modellen aldrig
    kan följa (det var precis problemet med dagens Email Studio, Del C
    punkt 2 — 'förladdning, inte hämtning')."""
    ref = parse_skill_name(name)
    # Verifieringen sker per fil inne i _read_skill_file, alltså före varje
    # append. En manipulerad references-fil får aldrig hinna bli en del av
    # den sammanfogade texten innan felet upptäcks.
    parts = [_read_skill_file(ref, "SKILL.md")]
    for relative in _list_reference_files(ref):
        parts.append(f"#### {relative}\n\n{_read_skill_file(ref, relative)}")
    return "\n\n".join(parts)


def load_reference(name: str, relative_path: str) -> str:
    """name='mk:sales-enablement', relative_path='references/objection-library.md'."""
    ref = parse_skill_name(name)
    return _read_skill_file(ref, relative_path)


def load_section(name: str, heading: str) -> str:
    """Extraherar en enskild `## Rubrik`-sektion ur SKILL.md, från rubriken
    till nästa rubrik på samma nivå (eller filens slut). Det här är vad Del I
    menar med 'mk:sales-enablement § Objection Handling Docs' — en enskild
    sektion inom SKILL.md, skild från references/-filer (load_reference)."""
    ref = parse_skill_name(name)
    text = _read_skill_file(ref, "SKILL.md")
    match = re.search(rf"^(#{{1,6}})\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        raise UnknownReferenceError(f"Sektionen '{heading}' finns inte i {name}/SKILL.md.")
    level = len(match.group(1))
    next_heading = re.search(rf"^#{{1,{level}}}\s+\S", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end].strip()


def skill_exists(name: str) -> bool:
    try:
        parse_skill_name(name)
    except SkillRegistryError:
        return False
    return True
