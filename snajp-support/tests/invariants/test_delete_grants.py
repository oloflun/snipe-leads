"""Varje tabell postgres.py raderar i har `grant delete ... to snajp_app` i en migration.

Default privileges (migration 009) ger snajp_app bara select/insert/update, så
varje ny DELETE-väg blir 500 "permission denied" i riktig drift, medan sviten,
som kör mot MemoryStorage, aldrig ser det. Hände med ss_emails (041) och
lead_vyer (087, upptäckt i röktest på development 2026-10-02).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_varje_raderad_tabell_har_delete_grant():
    kod = (ROOT / "snajp-support" / "app" / "storage" / "postgres.py").read_text(encoding="utf-8")
    raderade = set(re.findall(r"delete\s+from\s+(?:public\.)?([a-z_]+)", kod, re.IGNORECASE))
    migrationer = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "supabase" / "migrations").glob("*.sql"))
    beviljade = set(re.findall(r"grant\s+[a-z,\s]*\bdelete\b[a-z,\s]*\s+on\s+(?:table\s+)?(?:public\.)?([a-z_]+)", migrationer, re.IGNORECASE))
    saknas = sorted(raderade - beviljade)
    assert not saknas, f"DELETE utan grant till snajp_app: {saknas}"
