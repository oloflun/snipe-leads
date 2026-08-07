"""Onboarding-status och EFTERHANDSTRIGGER (användarkrav).

Problemet: Fas B/C kräver `context_pack` som förvillkor (INV-SKILL-004).
En kund som aldrig onboardats — eller vars onboarding avbröts halvvägs —
skulle då få MissingRequirementError och pipelinen skulle stanna helt.

Lösningen är INTE att slopa förvillkoret (då försvinner läsgarantin). Den är
att göra kontextpaketet alltid uppfyllbart, men ÄRLIGT: saknas ett dokument
injiceras en explicit markering om vad som saknas och vad agenten därför
inte får anta. Agenten jobbar med det den har, och vet exakt var luckorna är.

Samtidigt returneras `missing`-listan uppåt så att UI:t kan trigga
onboarding i efterhand för precis de delar som saknas.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ordningen speglar Fas A i planen (Del F): produktmarknadsföring först,
# sedan kundresearch, sist retentionsplaybook.
REQUIRED_KINDS = ("product_marketing", "customer_research", "retention_playbook")

_KIND_LABELS = {
    "product_marketing": "Produktmarknadsföring (mk:product-marketing)",
    "customer_research": "Kundresearch (mk:customer-research)",
    "retention_playbook": "Retentionsplaybook (mk:churn-prevention)",
}

_KIND_CONSEQUENCE = {
    "product_marketing": (
        "Du vet INTE vad kunden säljer, till vem, eller vad som skiljer dem från "
        "konkurrenterna. Påstå ingenting om deras erbjudande — fråga eller lämna luckan."
    ),
    "customer_research": (
        "Du vet INTE vilka kundens kunder är eller vilka invändningar som är vanliga. "
        "Generalisera inte från branschen i stort."
    ),
    "retention_playbook": (
        "Du har INGA godkända erbjudanden att luta dig mot. Erbjud därför ingenting "
        "alls — eskalera i stället (INV-AGENT-001)."
    ),
}


@dataclass(frozen=True)
class OnboardingState:
    present: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def started(self) -> bool:
        return bool(self.present)


async def get_onboarding_state(storage, tenant_id: str) -> OnboardingState:
    present, missing = [], []
    for kind in REQUIRED_KINDS:
        doc = await storage.get_latest_context_doc(tenant_id, kind=kind)
        (present if doc and doc.get("content", "").strip() else missing).append(kind)
    return OnboardingState(present=tuple(present), missing=tuple(missing))


def render_gap_notice(state: OnboardingState) -> str:
    """Den explicita luckmarkeringen som injiceras i kontextpaketet. Aldrig
    tyst — agenten ska VETA vad den inte vet."""
    if state.complete:
        return ""
    lines = [
        "### OFULLSTÄNDIG ONBOARDING — läs detta först",
        "Följande underlag saknas för den här kunden. Arbeta med det du har, "
        "men fyll ALDRIG i luckorna med antaganden:",
        "",
    ]
    for kind in state.missing:
        lines.append(f"- **{_KIND_LABELS[kind]} SAKNAS.** {_KIND_CONSEQUENCE[kind]}")
    lines.append("")
    lines.append(
        "Nämn i din utdata (fältet `onboarding_gaps`) vilka luckor som hindrade dig, "
        "så kan onboarding triggas i efterhand för exakt de delarna."
    )
    return "\n".join(lines)
