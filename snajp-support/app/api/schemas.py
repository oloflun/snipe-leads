"""Pydantic-scheman för API:t."""

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    data_url: str = Field(..., description="Bild som data-URL (data:image/...;base64,...)")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    subject: str = ""
    channel: str = "web"
    customer_email: str | None = None
    customer_name: str | None = None
    attachments: list[Attachment] = []


class TriageEmail(BaseModel):
    sender: str = Field(..., alias="from")
    subject: str = ""
    body: str = Field(..., min_length=1, max_length=8000)

    model_config = {"populate_by_name": True}


class TriageRequest(BaseModel):
    emails: list[TriageEmail] = Field(..., min_length=1, max_length=20)


class CreateKeyRequest(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=80)
    slug: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")


class KbArticle(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10, max_length=8000)
    category: str = "ovrigt"


class ContextDocRequest(BaseModel):
    """Leads Fas A (Del F): produktmarknadsföring, kundresearch, uppladdat
    material, eller retentionsplaybook. `content` är redan extraherad text —
    fil-till-text-parsning (PDF/DOCX) sker inte här, se app/api/leads.py."""

    kind: str = Field(..., pattern=r"^(product_marketing|customer_research|upload|retention_playbook)$")
    content: str = Field(..., min_length=1, max_length=50000)
    source: str = ""


class OnboardingChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ProspectRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    contact_name: str | None = None
    contact_email: str | None = None


class LeadsConfigRequest(BaseModel):
    """Båda fälten är valfria: UI:t har två separata formulär, och en PUT från
    det ena får inte nolla det andra."""

    autonomy: str | None = Field(default=None, pattern=r"^(draft|first_contact|meeting)$")
    icp: dict | None = None


class LeadsBatchRequest(BaseModel):
    scope: str = Field(default="research", pattern=r"^(research|research_and_draft)$")
    # Taket på 50 är ekonomiskt, inte tekniskt: varje prospekt är åtta
    # LLM-anrop, så en batch på 50 är 400 — exakt tenant-timtaket.
    limit: int = Field(default=10, ge=1, le=50)


class ProspectPatchRequest(BaseModel):
    status: str | None = None
    icp_fit: float | None = Field(default=None, ge=0, le=1)
    qualified: bool | None = None
    disqualifiers: list[str] | None = None


class ProspectSourceRequest(BaseModel):
    source_url: str = Field(..., min_length=4, max_length=2000)
    source_type: str = Field(
        default="company_website",
        pattern=r"^(company_website|public_news|business_register|job_signal|manual_note|enrichment_adapter|linkedin|other)$",
    )
    lawful_basis: str = Field(..., min_length=3, max_length=500)


class ResearchStepRequest(BaseModel):
    prospect_id: str
    brief: str = Field(..., min_length=1, max_length=2000)


class OutreachDraftRequest(BaseModel):
    thread_id: str
    prospect_email: str
    company_name: str = Field(..., min_length=1, max_length=200)
    offer_summary: str = Field(..., min_length=1, max_length=2000)
    brief: str = Field(..., min_length=1, max_length=2000)
    # Fas B:s underlag, vidarebefordrat av anroparen. Utan det har
    # grundningsgrinden ingenting att mäta utkastets påståenden mot — och det
    # var precis därför den påhittade "30 procent"-siffran var ofalsifierbar
    # (fältet research_summary fanns i signaturen men skickades aldrig).
    research_summary: str = Field(default="", max_length=8000)
    research_evidence: list[str] = Field(default_factory=list, max_length=60)


class SoulRequest(BaseModel):
    # Taket verkställs på TVÅ ställen: här vid API-gränsen och i
    # soul.render_soul. Ett dokument som stoppats direkt i databasen ska inte
    # kunna gå förbi bara för att det aldrig passerade den här modellen.
    content: str = Field(default="", max_length=4000)


class KbArticleRequest(BaseModel):
    articles: list[KbArticle] = Field(..., min_length=1, max_length=50)


class IngestAttachment(BaseModel):
    filename: str = "bilaga"
    content_type: str = "application/octet-stream"
    data_url: str | None = None


class IngestEmailRequest(BaseModel):
    """API-first-ingest: externa system (Zendesk, CRM, webhook) postar mail hit."""

    from_email: str = Field(..., alias="from", min_length=3)
    from_name: str | None = None
    subject: str = ""
    body: str = Field(..., min_length=1, max_length=16000)
    provider_message_id: str | None = None
    attachments: list[IngestAttachment] = []

    model_config = {"populate_by_name": True}


class ApproveDraftRequest(BaseModel):
    edited_content: str | None = Field(default=None, max_length=16000)
    note: str | None = None


class RejectDraftRequest(BaseModel):
    note: str | None = None


class CategoryRuleRequest(BaseModel):
    category: str
    mode: str = Field(..., pattern="^(auto|draft|escalate)$")
