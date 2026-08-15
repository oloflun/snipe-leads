"""Del F Fas A + Del C punkt 1: kontextpaketet.

mk:-skills läser `.agents/product-marketing.md` enligt sitt eget kontrakt
("Check for product marketing context first: if .agents/product-marketing.md
exists..."). Vi uppfyller det kontraktet i stället för att slåss mot det
(Del C): innehållet materialiseras BÅDE som en fil på den exakta sökvägen
OCH som textinjektion rubricerad med samma sökväg, så dagens
funktionsanropande agent (utan ett filsystemsverktyg i loopen) ändå möter
kontextet precis där skillen säger att det ska finnas.
"""

from __future__ import annotations

from pathlib import Path

# snajp-support/app/leads/context_pack.py -> snajp-support/var/tenant_context
VAR_ROOT = Path(__file__).resolve().parents[2] / "var" / "tenant_context"
PRODUCT_MARKETING_RELATIVE_PATH = ".agents/product-marketing.md"


def materialize_product_marketing(tenant_id: str, content: str) -> Path:
    """Skriver kontextdokumentet till disk på den sökväg mk:-skills letar
    efter, scopat per tenant (aldrig delat mellan tenants — samma princip
    som databasens tenant_id-isolering, fast på filsystemet). Returnerar
    den skrivna filens sökväg."""
    tenant_dir = VAR_ROOT / tenant_id / ".agents"
    tenant_dir.mkdir(parents=True, exist_ok=True)
    path = tenant_dir / "product-marketing.md"
    path.write_text(content, encoding="utf-8")
    return path


def render_context_pack(
    *,
    product_marketing: str | None,
    customer_research: str | None,
    retention_playbook: str | None = None,
    gap_notice: str = "",
    icp: str = "",
) -> str:
    """Textinjektionen som kompletterar filmaterialiseringen. Rubriceras med
    samma sökväg skillens eget kontrakt refererar till.

    `gap_notice` (från leads/onboarding_state.render_gap_notice) läggs FÖRST
    när onboarding är ofullständig — agenten ska se luckorna innan den ser
    underlaget, inte tvärtom.

    `icp` (från leads/icp.render_icp) läggs ÖVER produktbeskrivningen: frågan
    "ska det här prospektet bearbetas alls" kommer före hur erbjudandet
    formuleras. SOUL styr ton, ICP styr urval."""
    parts = []
    if gap_notice:
        parts.append(gap_notice)
    if icp:
        parts.append(icp)
    parts.append(f"### Kontextpaket: {PRODUCT_MARKETING_RELATIVE_PATH}")
    parts.append(
        product_marketing
        or "(Inget kontextdokument ännu. Fråga kunden sektion för sektion enligt "
        "mk:product-marketing — ställ inte alla frågor på en gång.)"
    )
    if customer_research:
        parts.append("### Kontextpaket: kundresearch (mk:customer-research, senaste körning)")
        parts.append(customer_research)
    if retention_playbook:
        parts.append("### Kontextpaket: retentionsplaybook (mk:churn-prevention)")
        parts.append(retention_playbook)
    return "\n\n".join(parts)


async def build_context_pack(storage, tenant_id: str) -> tuple[str, tuple[str, ...]]:
    """Den enda vägen Fas B/C ska bygga kontextpaketet på. Returnerar
    (renderat paket, saknade onboarding-delar) — paketet är ALLTID
    användbart, så förvillkoret context_pack kan alltid uppfyllas och
    pipelinen aldrig dödlåser sig på utebliven onboarding."""
    from .icp import render_icp
    from .onboarding_state import get_onboarding_state, render_gap_notice

    state = await get_onboarding_state(storage, tenant_id)
    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    docs = {
        kind: await storage.get_latest_context_doc(tenant_id, kind=kind)
        for kind in ("product_marketing", "customer_research", "retention_playbook")
    }
    rendered = render_context_pack(
        product_marketing=docs["product_marketing"]["content"] if docs["product_marketing"] else None,
        customer_research=docs["customer_research"]["content"] if docs["customer_research"] else None,
        retention_playbook=docs["retention_playbook"]["content"] if docs["retention_playbook"] else None,
        gap_notice=render_gap_notice(state),
        icp=render_icp(settings.get("icp")),
    )
    return rendered, state.missing
