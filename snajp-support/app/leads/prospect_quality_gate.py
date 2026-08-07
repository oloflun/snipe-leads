"""mk:prospecting § Quality Checks och compliance-regel 3 blir GRINDAR här,
inte rekommendationer (Del F Fas B: "Båda blir grindar, inte
rekommendationer"). Körs innan ett prospekt markeras redo för outreach.
"""

from __future__ import annotations

from dataclasses import dataclass

_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "live.se", "live.com", "telia.com", "bredband.net", "spray.se",
}


class ProspectQualityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProspectCandidate:
    company_name: str
    contact_email: str | None
    email_verified: bool
    source_count: int
    confidence: str  # "low" | "medium" | "high"
    lawful_basis: str | None = None


def check_not_duplicate(candidate: ProspectCandidate, existing_company_names: set[str]) -> None:
    normalized_existing = {n.strip().lower() for n in existing_company_names}
    if candidate.company_name.strip().lower() in normalized_existing:
        raise ProspectQualityError(f"Dublett: {candidate.company_name!r} finns redan i listan.")


def check_confidence_is_honest(candidate: ProspectCandidate) -> None:
    """'High' kräver minst 2 oberoende källor — inte bara två av samma sökning."""
    if candidate.confidence == "high" and candidate.source_count < 2:
        raise ProspectQualityError(
            f"{candidate.company_name}: confidence='high' kräver minst 2 oberoende "
            f"källor, fick {candidate.source_count}."
        )


def check_contact_channel_is_lawful(candidate: ProspectCandidate) -> None:
    """Compliance-regel 3 (mk:prospecting/references/compliance.md): 'Public
    business contact channels only... Personal/private emails require a
    lawful basis.' En personlig e-postadress utan registrerad laglig grund
    stoppas här — inte upptäcks efter utskick."""
    if not candidate.contact_email:
        return
    domain = candidate.contact_email.rsplit("@", 1)[-1].lower()
    if domain in _PERSONAL_EMAIL_DOMAINS and not candidate.lawful_basis:
        raise ProspectQualityError(
            f"{candidate.company_name}: {candidate.contact_email} är en privat "
            "e-postadress utan registrerad laglig grund (compliance-regel 3)."
        )


def check_ready_for_outreach(candidate: ProspectCandidate) -> None:
    """Samlad grind innan ett prospekt lämnar research och går till Fas C.
    Kör alla delkontroller — en enda saknad kontakt eller overifierad
    e-post ska inte tyst släppas igenom bara för att en annan check klarades."""
    if not candidate.contact_email:
        raise ProspectQualityError(f"{candidate.company_name}: saknar kontakt-e-post.")
    if not candidate.email_verified:
        raise ProspectQualityError(
            f"{candidate.company_name}: e-post ej verifierad — flyttas till "
            "'invalid'-hinken, skickas inte till outreach."
        )
    check_confidence_is_honest(candidate)
    check_contact_channel_is_lawful(candidate)
