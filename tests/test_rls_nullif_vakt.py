"""Varje tenant-policy efter 028 måste bära NULLIF-vakten.

028 skrev om alla policyer som fanns då, men sex senare tabeller fick
villkoret på det gamla sättet och fångades först när kedjan restes från noll
(scripts/lokal_stack.py). Det här testet fångar nästa migration som glömmer
vakten, utan databas: en rå `current_setting('app.tenant_id', ...)` utan
`nullif(` framför i en migration efter 028 fäller testet.
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / "supabase" / "migrations"

# Skrivna utan vakten, rättade av 20260919100000_068_rls_nullif_vakt.sql.
RATTADE_AV_068 = {
    "051_agent_suggestions.sql",
    "052_customer_memory.sql",
    "059_leads_job_ledger.sql",
    "060_leadlists.sql",
    "20260903164000_061_tenant_sending_domains.sql",
    "066_support_samtalslage.sql",
    "067_integrationer_och_kanaler.sql",
}

RA_VILLKOR = re.compile(r"(?<!nullif\()current_setting\(\s*'app\.tenant_id'", re.IGNORECASE)


def _nummer(namn: str) -> int:
    m = re.match(r"(?:\d{14}_)?(\d{3})_", namn)
    return int(m.group(1)) if m else -1


def test_ingen_policy_efter_028_saknar_nullif():
    brott = []
    for fil in sorted(MIGRATIONS.glob("*.sql")):
        if _nummer(fil.name) <= 28 or fil.name in RATTADE_AV_068:
            continue
        text = fil.read_text(encoding="utf-8")
        # Kommentarer får nämna funktionen, bara policyvillkor räknas.
        kod = "\n".join(r.split("--", 1)[0] for r in text.splitlines())
        if RA_VILLKOR.search(kod):
            brott.append(fil.name)
    assert not brott, f"current_setting('app.tenant_id') utan nullif i: {brott}"


def test_068_ratter_alla_elva():
    text = (MIGRATIONS / "20260919100000_068_rls_nullif_vakt.sql").read_text(encoding="utf-8")
    for tabell in ("agent_suggestions", "customer_memory", "leads_job_ledger",
                   "lead_lists", "lead_list_items", "ss_sending_domains"):
        assert f"on public.{tabell} for all" in text, tabell
    for tabell in ("ss_chat_state", "ss_integrations", "ss_channel_connections",
                   "ss_channel_contacts", "ss_channel_inbound_seen"):
        assert f"'{tabell}'" in text, tabell
