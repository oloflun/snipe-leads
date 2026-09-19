"""Nätvakten: vart en kundkonfigurerad adress får nå, och hur mycket den får läsa."""

from __future__ import annotations

import httpx
import pytest

from app.integrationer import natvakt
from app.integrationer.natvakt import NatvaktError, kontrollera_url


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com/x",  # inte https
        "https://localhost/x",
        "https://127.0.0.1/x",
        "https://10.0.0.5/x",
        "https://169.254.169.254/latest/meta-data",  # molnets metadatatjänst
        "https://[::1]/x",
        "https://[::ffff:10.0.0.1]/x",  # IPv4-mappad privat adress
        "https://100.64.0.1/x",  # CGNAT
        "https://intern/x",  # enkelledat värdnamn
        "https://skrivare.local/x",
        "https://db.railway.internal/x",
        "https://user:pass@api.example.com/x",
        "https:///x",
    ],
)
def test_otillatna_adresser_avvisas_utan_natverk(url):
    with pytest.raises(NatvaktError):
        kontrollera_url(url)


def test_publik_https_adress_godkanns():
    assert kontrollera_url("https://API.Example.com:8443/v1?q=1") == "api.example.com"


@pytest.mark.anyio
async def test_namn_som_loser_upp_till_privat_ip_avvisas(monkeypatch):
    async def dns(vard, port):
        return ["93.184.216.34", "10.1.2.3"]  # en publik, en privat

    monkeypatch.setattr(natvakt, "upplos", dns)
    with pytest.raises(NatvaktError, match="internt nät"):
        await natvakt.kontrollera_vard("https://blandat.example.com/")


@pytest.mark.anyio
async def test_anrop_foljer_omdirigering_och_provar_varje_hopp(svara):
    def hanterare(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://api.example.com/mal"})
        return httpx.Response(200, json={"ok": True})

    mottagna = svara(hanterare)
    svar = await natvakt.anropa("GET", "https://api.example.com/start", rubriker={"Authorization": "Bearer x"})
    assert svar.status == 200 and svar.text == '{"ok":true}'
    assert [str(r.url) for r in mottagna] == ["https://api.example.com/start", "https://api.example.com/mal"]
    # Samma värd: rubrikerna följer med.
    assert mottagna[1].headers.get("authorization") == "Bearer x"


@pytest.mark.anyio
async def test_omdirigering_till_annan_vard_tappar_rubrikerna(svara):
    def hanterare(request):
        if request.url.host == "api.example.com":
            return httpx.Response(307, headers={"location": "https://annan.example.org/in"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/plain"})

    mottagna = svara(hanterare)
    await natvakt.anropa(
        "POST", "https://api.example.com/", rubriker={"Authorization": "Bearer hemlig"}, json_kropp={"a": 1}
    )
    assert mottagna[1].url.host == "annan.example.org"
    assert "authorization" not in mottagna[1].headers
    # 307 behåller metod och kropp.
    assert mottagna[1].method == "POST" and mottagna[1].content == b'{"a":1}'


@pytest.mark.anyio
async def test_omdirigering_till_intern_adress_stoppas(svara):
    def hanterare(request):
        return httpx.Response(302, headers={"location": "https://169.254.169.254/latest/meta-data"})

    svara(hanterare)
    with pytest.raises(NatvaktError):
        await natvakt.anropa("GET", "https://api.example.com/")


@pytest.mark.anyio
async def test_for_manga_omdirigeringar(svara):
    svara(lambda r: httpx.Response(302, headers={"location": "https://api.example.com/igen"}))
    with pytest.raises(NatvaktError, match="omdirigeringar"):
        await natvakt.anropa("GET", "https://api.example.com/")


@pytest.mark.anyio
async def test_for_stort_svar_avbryts(svara):
    svara(lambda r: httpx.Response(200, content=b"x" * 2000, headers={"content-type": "text/plain"}))
    with pytest.raises(NatvaktError, match="större än"):
        await natvakt.anropa("GET", "https://api.example.com/", max_storlek=1000)


@pytest.mark.anyio
async def test_binart_svar_lases_inte_in(svara):
    svara(lambda r: httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"}))
    with pytest.raises(NatvaktError, match="image/png"):
        await natvakt.anropa("GET", "https://api.example.com/bild")


@pytest.mark.anyio
async def test_vaktad_klient_provar_aven_anrop_den_inte_byggt_sjalv():
    """MCP-SDK:t gör egna förfrågningar genom klienten — vakten måste sitta i
    transporten, inte bara i anropa()."""
    async with natvakt.vaktad_klient() as klient:
        with pytest.raises(NatvaktError):
            await klient.get("https://127.0.0.1/admin")
