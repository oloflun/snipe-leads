"""INV-SKILL-006 — vendorad skill ändras bara med deklarerad vendor-bump.

Testar den rena funktionen `requires_vendor_bump` mot syntetiska fillistor
och commitmeddelanden. Git-anropet ligger i skriptets `__main__` och testas
inte här — det är I/O, och funktionen är regeln.

Notera vad testet INTE påstår: att grinden skiljer en legitim re-vendoring
från en smygjustering. Det kan den inte, bytes-diffen är identisk. Den kräver
bara att någon SKRIVER vilket det var.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_vendor_bump import requires_vendor_bump  # noqa: E402

SKILL = "agent-core/skills/mk/cold-email/SKILL.md"
OVERLAY = "agent-core/overlays/leads-hard-rules.md"


def test_changed_skill_without_trailer_is_refused():
    problem = requires_vendor_bump([SKILL], ["fixa tonen i kalla mejl"])
    assert problem is not None
    assert SKILL in problem
    # Felmeddelandet måste peka på overlay-vägen, annars är grinden bara
    # ett hinder och inte en vägvisare.
    assert "agent-core/overlays/" in problem


def test_changed_skill_with_sha_trailer_is_allowed():
    message = "re-vendora mk från uppströms\n\nVENDOR-BUMP: 7868cb9251fad80a73d26e488a5ad5f6c4a9f335"
    assert requires_vendor_bump([SKILL], [message]) is None


def test_short_sha_is_accepted():
    assert requires_vendor_bump([SKILL], ["bump\n\nVENDOR-BUMP: 7868cb9"]) is None


def test_na_requires_a_motivation():
    """'n/a' finns för egna snajp:-skills utan uppströmsrepo, men ett naket
    'n/a' är en tom deklaration — då är grinden bara en tangenttryckning."""
    assert requires_vendor_bump([SKILL], ["bump\n\nVENDOR-BUMP: n/a"]) is not None
    assert (
        requires_vendor_bump(
            [SKILL], ["bump\n\nVENDOR-BUMP: n/a — egen snajp-skill, inget uppströmsrepo"]
        )
        is None
    )


def test_trailer_may_live_in_any_commit_of_the_branch():
    messages = ["wip", "re-vendora\n\nVENDOR-BUMP: 5ee4541", "städa"]
    assert requires_vendor_bump([SKILL], messages) is None


def test_overlay_changes_never_require_a_bump():
    """Overlay-lagret ÄR den sanktionerade finjusteringsytan. Att kräva en
    vendor-bump där hade gjort den lika dyr som att redigera skillen, alltså
    tagit bort hela skälet att använda den."""
    assert requires_vendor_bump([OVERLAY], ["justera tonen"]) is None
    assert requires_vendor_bump(["agent-core/AGENTS.md"], ["skärp policyn"]) is None


def test_unrelated_changes_are_ignored():
    assert requires_vendor_bump(["snajp-support/app/main.py"], ["fix"]) is None
    assert requires_vendor_bump([], []) is None


def test_manifest_alone_does_not_trigger():
    """manifest.json ligger utanför skills/ — den ändras som FÖLJD av en
    skill-ändring, och skill-filen i samma commit är det som utlöser grinden."""
    assert requires_vendor_bump(["agent-core/manifest.json"], ["rebuild"]) is None


def test_windows_path_separators_are_handled():
    """git diff --name-only ger POSIX-separatorer, men en anropare som
    matar in os.path-vägar på Windows ska inte tyst slippa förbi grinden."""
    assert requires_vendor_bump([SKILL.replace("/", "\\")], ["nudge"]) is not None
