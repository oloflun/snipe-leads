"""Mätningen per anrop: Server-Timing med frågor och databastid (app/matning.py)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_varje_svar_bar_server_timing():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.get("/health/live")
    timing = svar.headers["server-timing"]
    assert timing.startswith("db;dur=") and 'desc="0 q"' in timing and "app;dur=" in timing
