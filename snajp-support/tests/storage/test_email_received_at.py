from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.email_pipeline.ingest import ingest_email
from app.email_pipeline.models import InboundEmail


@pytest.mark.anyio
async def test_ingest_normalizes_iso_received_at_before_storage():
    storage = AsyncMock()
    storage.save_email.return_value = None
    inbound = InboundEmail(
        provider="imap", provider_message_id="m1", from_email="a@example.com",
        from_name=None, subject="s", body_text="b",
        received_at="2026-08-28T21:13:28+00:00",
    )

    await ingest_email(storage, "00000000-0000-4000-a000-000000000001", inbound)

    value = storage.save_email.call_args.kwargs["received_at"]
    assert isinstance(value, datetime)
    assert value.isoformat() == "2026-08-28T21:13:28+00:00"
