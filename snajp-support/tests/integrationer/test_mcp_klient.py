"""MCP-klienten mot en RIKTIG MCP-server (SDK:ts FastMCP) i processen.

Servern körs som ASGI-app bakom natvakt.VaktadTransport, så varje förfrågan
SDK:t gör passerar samma vakt som i drift. Det är protokollet som provas, inte
en attrapp av det: initialize, tools/list med annotationer, tools/call.
"""

from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from app.integrationer import mcp_klient, natvakt
from app.integrationer.katalog import mcp_verktyget_skriver, mcp_verktyget_tillats
from app.integrationer.modell import McpKonfig

URL = "https://mcp.example.com/mcp"


def _server() -> FastMCP:
    server = FastMCP(
        "testbutik",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(allowed_hosts=["mcp.example.com"]),
    )

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def orderstatus(ordernummer: str) -> str:
        """Status för en order."""
        return f"Order {ordernummer}: skickad, levereras 2026-09-22"

    @server.tool(annotations=ToolAnnotations(destructiveHint=True))
    def radera_konto(email: str) -> str:
        """Raderar kundens konto."""
        return "raderat"

    @server.tool()
    def avboka(ordernummer: str) -> str:
        """Avbokar en order."""
        return f"Order {ordernummer} avbokad"

    @server.tool()
    def trasig() -> str:
        """Kastar alltid."""
        raise ValueError("databasen är nere")

    return server


@pytest.fixture
async def mcp_server(monkeypatch):
    server = _server()
    app = server.streamable_http_app()
    rubriker: list[dict[str, str]] = []

    async def inspektera(scope, receive, send):
        if scope["type"] == "http":
            rubriker.append({k.decode(): v.decode() for k, v in scope["headers"]})
        await app(scope, receive, send)

    monkeypatch.setattr(natvakt, "inre_transport", lambda: httpx.ASGITransport(app=inspektera))
    async with server.session_manager.run():
        yield rubriker


def _konfig(**extra) -> McpKonfig:
    return McpKonfig.model_validate({"url": URL, "auth_header_name": "X-Api-Key", **extra})


@pytest.mark.anyio
async def test_listar_verktyg_med_annotationer_och_skickar_nyckeln(mcp_server):
    verktyg = await mcp_klient.lista_verktyg(_konfig(), {"auth": "nyckel-123456789"})
    per_namn = {v.namn: v for v in verktyg}
    assert set(per_namn) == {"orderstatus", "radera_konto", "avboka", "trasig"}
    assert per_namn["orderstatus"].skrivskyddat is True
    assert per_namn["radera_konto"].destruktivt is True
    assert per_namn["orderstatus"].schema["properties"]["ordernummer"]["type"] == "string"
    assert all(r.get("x-api-key") == "nyckel-123456789" for r in mcp_server)


@pytest.mark.anyio
async def test_anropar_verktyg(mcp_server):
    resultat = await mcp_klient.anropa_verktyg(
        _konfig(),
        {},
        verktygsnamn="mcp_butik_orderstatus",
        serverns_namn="orderstatus",
        argument={"ordernummer": "A-17"},
        skrivande=False,
    )
    assert resultat.ok, resultat.fel
    assert "Order A-17: skickad" in resultat.data


@pytest.mark.anyio
async def test_verktygsfel_blir_resultat(mcp_server):
    resultat = await mcp_klient.anropa_verktyg(
        _konfig(), {}, verktygsnamn="t", serverns_namn="trasig", argument={}, skrivande=False
    )
    assert not resultat.ok
    assert "databasen är nere" in (resultat.fel or "")


@pytest.mark.anyio
async def test_destruktiva_verktyg_doljs_och_omarkta_raknas_som_lasande(mcp_server):
    konfig = _konfig()
    verktyg = {v.namn: v for v in await mcp_klient.lista_verktyg(konfig, {})}
    assert not mcp_verktyget_tillats(konfig, verktyg["radera_konto"])
    assert mcp_verktyget_tillats(konfig, verktyg["avboka"])
    assert not mcp_verktyget_skriver(konfig, verktyg["avboka"])
    # Admin märker avboka som skrivande -> simuleras i testchatten.
    markt = _konfig(skrivande_verktyg=["avboka"])
    assert mcp_verktyget_skriver(markt, verktyg["avboka"])
    # En uttrycklig tillåtelselista vinner över allt annat.
    snav = _konfig(tillatna_verktyg=["orderstatus"])
    assert [n for n, v in verktyg.items() if mcp_verktyget_tillats(snav, v)] == ["orderstatus"]


@pytest.mark.anyio
async def test_skrivande_verktyg_simuleras_utan_anrop(monkeypatch):
    # Ingen server alls: ett anrop hade fällt testet.
    resultat = await mcp_klient.anropa_verktyg(
        _konfig(), {}, verktygsnamn="t", serverns_namn="avboka", argument={"ordernummer": "1"},
        skrivande=True, simulera=True,
    )
    assert resultat.ok and resultat.simulerad


@pytest.mark.anyio
async def test_intern_adress_nas_aldrig(monkeypatch):
    async def dns(vard, port):
        return ["10.0.0.7"]

    monkeypatch.setattr(natvakt, "upplos", dns)
    with pytest.raises(mcp_klient.McpFel, match="inte tillåten"):
        await mcp_klient.lista_verktyg(_konfig(), {})


@pytest.mark.anyio
async def test_nekad_atkomst_ger_begripligt_besked(monkeypatch):
    def neka(request):
        return httpx.Response(401, json={"error": "unauthorized"})

    monkeypatch.setattr(natvakt, "inre_transport", lambda: httpx.MockTransport(neka))
    with pytest.raises(mcp_klient.McpFel) as fel:
        await mcp_klient.lista_verktyg(_konfig(), {"auth": "fel-nyckel-123"})
    assert "MCP-servern" in str(fel.value)


def test_stdio_och_platshallare_i_adressen_avvisas():
    with pytest.raises(ValueError):
        McpKonfig.model_validate({"url": "https://{{hemlighet.x}}.example.com/mcp"})
    with pytest.raises(ValueError):
        McpKonfig.model_validate({"url": "https://mcp.example.com/mcp", "transport": "stdio"})
