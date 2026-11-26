"""Webbplatsskanningen ger säljfakta till Iris, inte bara supportartiklar.

Kunddemon 2026-11-24: skanningen av ett tjänstebolag (företagstelefoni) gav
rimliga bitar ur sajten, men allt var skrivet för supportagenten. Samma
LLM-anrop ska därför också ge artiklar i kategorin "salj": tjänster och
nytta, målgrupp, bevis och pris, med samma regler som supportartiklarna
(bara sidtexten, en source_url bland de hämtade sidorna, inga påhittade
siffror). Står inget pris på sajten skrivs ingen prisartikel.

Ingen modell och inget nät: sajten är en fixture och modellen en stubbe.
"""

from __future__ import annotations

import json

import pytest

from app import kb_skanning as ks
from app.config import KB_CATEGORIES

SAJT = "https://www.telekunden-exempel.se"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Minneshamtare:
    def __init__(self, sidor: dict[str, str]) -> None:
        self.sidor = sidor

    def hamta(self, url: str) -> ks.Svar:
        if url.endswith("/robots.txt"):
            return ks.Svar(404, url, "text/plain", "")
        if url not in self.sidor:
            return ks.Svar(404, url, "text/html", "")
        return ks.Svar(200, url, "text/html; charset=utf-8", self.sidor[url])


def _sida(rubrik: str, text: str, lankar: str = "") -> str:
    return f"<html><body><nav>{lankar}</nav><main><h1>{rubrik}</h1><p>{text}</p></main></body></html>"


_MENY = (
    '<a href="/tjanster">Tjänster</a><a href="/referenser">Referenser</a>'
    '<a href="/priser">Priser</a><a href="/kontakt">Kontakt</a>'
)


def _telefonisajt(*, med_pris: bool = True) -> Minneshamtare:
    sidor = {
        SAJT: _sida(
            "Företagstelefoni utan krångel",
            "Vi hjälper små och medelstora företag i Västerbotten att byta till en växel i mobilen.",
            _MENY,
        ),
        SAJT + "/tjanster": _sida(
            "Tjänster",
            "Mobil växel: alla samtal når rätt person, även på språng. "
            "Upphandling av företagstelefoni: vi jämför operatörerna åt er och sköter bytet.",
        ),
        SAJT + "/referenser": _sida(
            "Referenser",
            "Över 300 företag har bytt växel med oss. Byggfirman Norrbygg sänkte sina telefonikostnader med 30 procent.",
        ),
        SAJT + "/kontakt": _sida("Kontakt", "Ring oss på vardagar eller skriv till oss via formuläret."),
    }
    if med_pris:
        sidor[SAJT + "/priser"] = _sida(
            "Priser", "Mobil växel kostar från 149 kr per användare och månad. Ingen startavgift."
        )
    return Minneshamtare(sidor)


def _stubbe(svar: dict, mottagna: list[tuple[str, str]]):
    async def anropa(system: str, meddelande: str) -> str:
        mottagna.append((system, meddelande))
        return json.dumps(svar, ensure_ascii=False)

    return anropa


def _salj(titel: str, innehall: str, kalla: str) -> dict:
    return {"title": titel, "content": innehall, "category": "salj", "source_url": kalla, "confidence": 0.8}


def _hamtade(hamtare: Minneshamtare) -> set[str]:
    return set(hamtare.sidor)


@pytest.mark.anyio
async def test_skanningen_ger_saljfakta_med_kalla_bland_de_hamtade_sidorna():
    hamtare = _telefonisajt()
    svar = {
        "artiklar": [
            {
                "title": "Kontakta oss",
                "content": "Ring oss på vardagar eller skriv via formuläret på kontaktsidan.",
                "category": "ovrigt",
                "source_url": SAJT + "/kontakt",
                "confidence": 0.7,
            },
            _salj(
                "Tjänster och nytta",
                "Mobil växel: alla samtal når rätt person. Upphandling av företagstelefoni: vi jämför operatörerna.",
                SAJT + "/tjanster",
            ),
            _salj("Målgrupp", "Små och medelstora företag i Västerbotten.", SAJT),
            _salj(
                "Bevis och referenser",
                "Över 300 företag har bytt växel. Norrbygg sänkte telefonikostnaderna med 30 procent.",
                SAJT + "/referenser",
            ),
            _salj("Pris", "Mobil växel från 149 kr per användare och månad, ingen startavgift.", SAJT + "/priser"),
        ],
        "saknas": [],
    }
    mottagna: list[tuple[str, str]] = []
    resultat = await ks.skanna(SAJT, "Telekunden", _stubbe(svar, mottagna), hamtare=hamtare, fordrojning=0.0)

    salj = [a for a in resultat["artiklar"] if a["category"] == "salj"]
    assert {a["title"] for a in salj} == {"Tjänster och nytta", "Målgrupp", "Bevis och referenser", "Pris"}
    assert all(a["source_url"] in _hamtade(hamtare) for a in salj)
    # Supportartikeln står kvar som i dag.
    assert any(a["category"] == "ovrigt" and a["title"] == "Kontakta oss" for a in resultat["artiklar"])
    assert "salj" in KB_CATEGORIES


@pytest.mark.anyio
async def test_systemprompten_bestaller_saljfakta_i_samma_anrop():
    mottagna: list[tuple[str, str]] = []
    await ks.skanna(
        SAJT, "Telekunden", _stubbe({"artiklar": [], "saknas": []}, mottagna), hamtare=_telefonisajt(), fordrojning=0.0
    )
    assert len(mottagna) == 1, "säljfakta ska komma ur samma anrop som supportartiklarna"
    system = mottagna[0][0]
    assert "salj" in system
    for ord_ in ("målgrupp", "bevis", "pris"):
        assert ord_ in system.lower()
    assert "Står inget pris" in system


@pytest.mark.anyio
async def test_sajt_utan_pris_ger_ingen_prisartikel():
    hamtare = _telefonisajt(med_pris=False)
    svar = {
        "artiklar": [
            _salj("Pris", "Priset sätts efter en offert som anpassas efter företagets behov.", SAJT + "/tjanster"),
            _salj("Målgrupp", "Små och medelstora företag i Västerbotten.", SAJT),
        ],
        "saknas": [],
    }
    resultat = await ks.skanna(SAJT, "Telekunden", _stubbe(svar, []), hamtare=hamtare, fordrojning=0.0)
    titlar = {a["title"] for a in resultat["artiklar"]}
    assert "Pris" not in titlar
    assert "Målgrupp" in titlar


@pytest.mark.anyio
async def test_saljfakta_med_obelagd_siffra_kasseras():
    """Säljfakta går in i grundningsgrindens underlag (context_pack). En
    påhittad siffra där blir en TILLÅTEN siffra i Iris utkast, så den
    kasseras i stället för att bara varnas för som en supportartikel."""
    hamtare = _telefonisajt()
    svar = {
        "artiklar": [
            _salj("Bevis och referenser", "Över 500 företag har bytt växel med oss.", SAJT + "/referenser"),
            _salj("Målgrupp", "Små och medelstora företag i Västerbotten.", SAJT),
        ],
        "saknas": [],
    }
    resultat = await ks.skanna(SAJT, "Telekunden", _stubbe(svar, []), hamtare=hamtare, fordrojning=0.0)
    salj = [a for a in resultat["artiklar"] if a["category"] == "salj"]
    assert [a["title"] for a in salj] == ["Målgrupp"]
    for artikel in salj:
        assert not ks.obelagda_siffror(artikel["content"], "\n".join(s for s in hamtare.sidor.values()))
