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
