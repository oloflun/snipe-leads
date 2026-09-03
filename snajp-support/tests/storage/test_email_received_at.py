from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.storage.postgres import PostgresStorage


class Scoped:
    def __init__(self, conn): self.conn = conn
    async def __aenter__(self): return self.conn
    async def __aexit__(self, *_): return None


@pytest.mark.anyio
async def test_save_email_normalizes_iso_received_at_before_asyncpg():
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    storage = object.__new__(PostgresStorage)
    storage._scoped = lambda _: Scoped(conn)
    await storage.save_email(
        "00000000-0000-4000-a000-000000000001", provider="imap",
        provider_message_id="m1", from_email="a@example.com", from_name=None,
        subject="s", body_text="b", received_at="2026-08-28T21:13:28+00:00",
    )
    assert isinstance(conn.fetchrow.call_args.args[-2], datetime)
    assert conn.fetchrow.call_args.args[-2].isoformat() == "2026-08-28T21:13:28+00:00"
