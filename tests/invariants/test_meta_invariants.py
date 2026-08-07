"""Meta-test: en invariant utan test är ingen invariant.

Läser ARCHITECTURE_INVARIANTS.md, kräver att varje ### INV-...-post i
Active-avsnittet pekar på ett existerande testfilnamn, och läser waivers.yml
för att fälla builden på en utgången waiver. Se ARCHITECTURE_INVARIANTS.md
för formatet och Del L4 i plan-dokumentet för waiver-kontraktet.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
INVARIANTS_FILE = ROOT / "ARCHITECTURE_INVARIANTS.md"
WAIVERS_FILE = ROOT / "waivers.yml"

_ENTRY_RE = re.compile(r"^### (INV-[A-Z]+-\d+) — ", re.MULTILINE)
_TEST_LINE_RE = re.compile(r"^Test:\s*(\S+)\s*$", re.MULTILINE)


def _active_section() -> str:
    text = INVARIANTS_FILE.read_text(encoding="utf-8")
    start = text.index("## Active")
    end = text.index("## Roadmap")
    return text[start:end]


def _parse_active_entries() -> dict[str, str]:
    """id -> declared test path, for every entry under ## Active."""
    section = _active_section()
    entries: dict[str, str] = {}
    matches = list(_ENTRY_RE.finditer(section))
    for i, match in enumerate(matches):
        entry_id = match.group(1)
        entry_start = match.end()
        entry_end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        block = section[entry_start:entry_end]
        test_match = _TEST_LINE_RE.search(block)
        assert test_match, f"{entry_id} saknar en 'Test:'-rad i ARCHITECTURE_INVARIANTS.md"
        entries[entry_id] = test_match.group(1)
    return entries


def test_every_active_invariant_has_an_existing_test():
    entries = _parse_active_entries()
    missing = {
        entry_id: test_path
        for entry_id, test_path in entries.items()
        if not (ROOT / test_path).is_file()
    }
    assert not missing, f"Invarianter utan existerande testfil: {missing}"


def test_no_waiver_has_expired():
    raw = WAIVERS_FILE.read_text(encoding="utf-8")
    waivers = yaml.safe_load(raw) or []
    today = datetime.date.today()
    expired = []
    for waiver in waivers:
        expires = waiver["expires"]
        if isinstance(expires, str):
            expires = datetime.date.fromisoformat(expires)
        if expires < today:
            expired.append(waiver["id"])
    assert not expired, f"Utgångna waivers i waivers.yml: {expired}"


def test_every_waiver_targets_a_roadmap_or_active_id():
    raw = WAIVERS_FILE.read_text(encoding="utf-8")
    waivers = yaml.safe_load(raw) or []
    text = INVARIANTS_FILE.read_text(encoding="utf-8")
    for waiver in waivers:
        assert waiver["id"] in text, f"Waiver för okänt id: {waiver['id']}"
        for field in ("reason", "owner", "expires"):
            assert waiver.get(field), f"Waiver {waiver['id']} saknar fältet '{field}'"
