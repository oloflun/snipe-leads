"""Webbplatsskanningen till kunskapsbasen (app/kb_skanning.py, POST /api/kb/skanna)
och borttagning av artiklar (DELETE /api/kb/{id}).

Kedjan själv (robots.txt, sidtak, utkast, siffergrind) testas i
tests/test_pilot_kb_utkast.py i repots rot — den är samma kod. Här testas det
som är nytt för appen: den breda genomsökningen, SSRF-spärren och jobbflödet.
Inga nätanrop och ingen modell.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app import kb_skanning as ks
from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
SAJT = "https://www.lingonkudden-exempel.se"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class Minneshamtare:
    def __init__(self, sidor: dict[str, str]) -> None:
        self.sidor = sidor
        self.hamtade: list[str] = []

    def hamta(self, url: str) -> ks.Svar:
        self.hamtade.append(url)
        if url.endswith("/robots.txt"):
            return ks.Svar(404, url, "text/plain", "")
        if url not in self.sidor:
            return ks.Svar(404, url, "text/html", "")
        return ks.Svar(200, url, "text/html; charset=utf-8", self.sidor[url])


def _html(text: str, lankar: str = "") -> str:
    return f"<html><body><nav>{lankar}</nav><main><h1>{text}</h1><p>{text} " * 3 + "</p></main></body></html>"


# --- bred genomsökning --------------------------------------------------------


def _tjanstesajt() -> Minneshamtare:
    start = (
        '<a href="/utbildningar/sakerhetsdag">Säkerhetsdag</a>'
        '<a href="/kontakt">Kontakt</a><a href="/logga-in">Logga in</a>'
    )
    return Minneshamtare(
        {
            SAJT: _html("Vi utbildar i HLR och brand", start),
            SAJT + "/utbildningar/sakerhetsdag": _html(
                "Säkerhetsdag fyra timmar", '<a href="/utbildningar/arkiv">Arkiv</a>'
            ),
            SAJT + "/kontakt": _html("Kontakta oss"),
            SAJT + "/utbildningar/arkiv": _html("Gamla kurser"),
        }
    )


def test_smal_genomsokning_hoppar_over_tjanstesidor():
    resultat = ks.genomsok(SAJT, _tjanstesajt(), fordrojning=0.0)
    assert SAJT + "/utbildningar/sakerhetsdag" not in {s.url for s in resultat.sidor}


def test_bred_genomsokning_tar_startsidans_meny_efter_de_prioriterade():
    hamtare = _tjanstesajt()
    resultat = ks.genomsok(SAJT, hamtare, fordrojning=0.0, bred=True)
    ordning = [s.url for s in resultat.sidor]
    assert ordning == [SAJT, SAJT + "/kontakt", SAJT + "/utbildningar/sakerhetsdag"]
    # Undersidans oprioriterade länk följs inte, och inloggningen aldrig.
    assert SAJT + "/utbildningar/arkiv" not in hamtare.hamtade
    assert not any("logga-in" in u for u in hamtare.hamtade)


# --- SSRF ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5",
        "http://192.168.1.1",
        "http://[::1]",
        "http://0.0.0.0",
    ],
)
def test_interna_adresser_ar_inte_publika(url):
    assert ks.ar_publik_vard(url) is False


def test_publik_ip_ar_publik():
    assert ks.ar_publik_vard("http://8.8.8.8") is True


def test_omdirigering_till_intern_adress_stoppas(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: "169.254" not in url)

    def svar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest"})

    hamtare = ks.PublikHamtare()
    hamtare._klient = httpx.Client(transport=httpx.MockTransport(svar), follow_redirects=False)
    with pytest.raises(ks.HamtningsFel, match="inte publik"):
        hamtare.hamta(SAJT)


def test_omdirigering_inom_sajten_foljs(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: True)

    def svar(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(301, headers={"location": "/sv"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Hej</p>")

    hamtare = ks.PublikHamtare()
    hamtare._klient = httpx.Client(transport=httpx.MockTransport(svar), follow_redirects=False)
    resultat = hamtare.hamta(SAJT + "/")
    assert resultat.status == 200
    assert resultat.url.endswith("/sv")


# --- API ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_skanna_vagrar_intern_adress():
    async with app.router.lifespan_context(app):
        async with _client() as c:
            r = await c.post("/api/kb/skanna", json={"webbplats": "http://169.254.169.254"}, headers=DEMO)
    assert r.status_code == 422


@pytest.mark.anyio
async def test_skanna_vagrar_register():
    async with app.router.lifespan_context(app):
        async with _client() as c:
            r = await c.post("/api/kb/skanna", json={"webbplats": "https://www.allabolag.se/x"}, headers=DEMO)
    assert r.status_code == 422


@pytest.mark.anyio
async def test_skanna_ger_jobb_med_utkast(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: True)

    async def falsk_skanning(webbplats, bolagsnamn, anropa, **_):
        return {
            "webbplats": webbplats,
            "robots": "saknas",
            "sidor": 3,
            "lasbara_sidor": 3,
            "blockerade": 0,
            "artiklar": [
                {
                    "title": "Säkerhetsdag",
                    "content": "Fyra timmar hos er, fyra stationer.",
                    "category": "utbildning",
                    "source_url": webbplats,
                    "confidence": 0.9,
                    "varningar": [],
                }
            ],
            "saknas": [],
            "anrop": 1,
            "fel": [],
        }

    monkeypatch.setattr(ks, "skanna", falsk_skanning)
    monkeypatch.setattr(ks, "bygg_anropare", lambda: None)

    async with app.router.lifespan_context(app):
        async with _client() as c:
            r = await c.post("/api/kb/skanna", json={"webbplats": "lingonkudden.se"}, headers=DEMO)
            assert r.status_code == 202, r.text
            job_id = r.json()["job_id"]
            assert r.json()["webbplats"] == "https://lingonkudden.se"
            for _ in range(50):
                jobb = (await c.get(f"/api/jobs/{job_id}", headers=DEMO)).json()
                if jobb["status"] in ("completed", "failed"):
                    break
                await asyncio.sleep(0.02)
    assert jobb["status"] == "completed", jobb
    assert jobb["result"]["artiklar"][0]["title"] == "Säkerhetsdag"


@pytest.mark.anyio
async def test_alla_modellanrop_fallna_ger_fel_jobb(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: True)

    async def fallen(webbplats, bolagsnamn, anropa, **_):
        return {"artiklar": [], "anrop": 2, "fel": ["429 kvoten slut", "429 kvoten slut"]}

    monkeypatch.setattr(ks, "skanna", fallen)
    monkeypatch.setattr(ks, "bygg_anropare", lambda: None)

    async with app.router.lifespan_context(app):
        async with _client() as c:
            job_id = (
                await c.post("/api/kb/skanna", json={"webbplats": "lingonkudden.se"}, headers=DEMO)
            ).json()["job_id"]
            for _ in range(50):
                jobb = (await c.get(f"/api/jobs/{job_id}", headers=DEMO)).json()
                if jobb["status"] in ("completed", "failed"):
                    break
                await asyncio.sleep(0.02)
    assert jobb["status"] == "failed"


@pytest.mark.anyio
async def test_ta_bort_artikel():
    async with app.router.lifespan_context(app):
        async with _client() as c:
            skapad = await c.post(
                "/api/kb",
                json={"articles": [{"title": "Tillfällig artikel", "content": "Ska tas bort igen snart."}]},
                headers=DEMO,
            )
            artikel_id = skapad.json()["created"][0]["id"]
            r = await c.delete(f"/api/kb/{artikel_id}", headers=DEMO)
            assert r.status_code == 200
            kvar = (await c.get("/api/kb", headers=DEMO)).json()["articles"]
            assert artikel_id not in {a["id"] for a in kvar}
            assert (await c.delete(f"/api/kb/{artikel_id}", headers=DEMO)).status_code == 404
            assert (await c.delete("/api/kb/inte-ett-id", headers=DEMO)).status_code == 404
