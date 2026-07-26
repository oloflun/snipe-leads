"""Interna modeller för email-pipelinen."""

from dataclasses import dataclass, field


@dataclass
class InboundAttachment:
    filename: str
    content_type: str
    data_url: str | None  # data:...;base64,... — None om för stor/ej lagrad
    is_image: bool
    size_bytes: int = 0


@dataclass
class InboundEmail:
    provider: str
    provider_message_id: str
    from_email: str
    from_name: str | None
    subject: str
    body_text: str
    received_at: str | None = None
    attachments: list[InboundAttachment] = field(default_factory=list)
