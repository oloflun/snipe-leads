"""Ett felformat id i sökvägen ska ge 404 — aldrig 500.

Postgres kastar på `'inte-ett-uuid'::uuid`, och utan en kontroll bubblar det
upp som ett ohanterat undantag. Uppmätt mot dev-deployen 2026-08-23:

    /api/tickets/inte-ett-uuid              -> 500
    /api/customers/inte-ett-uuid/history    -> 500
    /api/leads/prospects/inte-ett-uuid      -> 500

medan /api/inbox/{id} och /api/jobs/{id} svarade 404 på samma indata. Det var
alltså inte ett medvetet val utan en lucka i tre av fem.

Varför 500 är fel svar, och inte bara ett fulare 404: det säger att VI gick
sönder när det var anroparen som skrev fel. I webbappen faller det dessutom ur
"finns inte"-grenen och landar i den allmänna felrutan — användaren får
"Kunde inte hämta bolaget (status 500)" i stället för "Bolaget finns inte".

404 och inte 422: ett felformat id och ett id som inte finns ska inte gå att
skilja åt utifrån, annars blir svaret en uppräkningskanal.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api_headers():
    # Demonyckeln, som mappar till default-tenanten. Testerna är hermetiska —
    # conftest tvingar simuleringsläge och tömmer DATABASE_URL.
    return {"X-API-Key": get_settings().snajp_demo_api_key}

#: Sökvägar som tar ett id, och det id-lösa mönstret att fylla i.
#: Håll listan komplett — en ny {id}-endpoint utan rad här är en ny 500.
VAGAR = [
    "/api/tickets/{}",
    "/api/customers/{}/history",
    "/api/leads/prospects/{}",
    "/api/inbox/{}",
]

#: Indata som ALDRIG är ett giltigt uuid.
FELFORMAT = [
    "inte-ett-uuid",
    "123",
    "00000000-0000-0000-0000-00000000000",   # ett tecken för kort
    "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",  # rätt form, ogiltiga tecken
]


@pytest.mark.parametrize("mall", VAGAR)
@pytest.mark.parametrize("id_varde", FELFORMAT)
def test_felformat_id_ger_inte_500(client, api_headers, mall, id_varde):
    svar = client.get(mall.format(id_varde), headers=api_headers)
    assert svar.status_code < 500, (
        f"{mall.format(id_varde)} gav {svar.status_code}. Ett felformat id är "
        "anroparens fel, inte vårt — se modulens docstring."
    )
    assert svar.status_code == 404


#: Sökvägar som hämtar EN resurs. En samling hör inte hemma här — se nedan.
ENSKILDA = [v for v in VAGAR if not v.endswith("/history")]


@pytest.mark.parametrize("mall", ENSKILDA)
def test_okant_men_giltigt_id_ger_ocksa_404(client, api_headers, mall):
    """Samma svar som för ett felformat id, med flit.

    Skiljer de två sig åt kan en utomstående räkna upp vilka id som finns
    genom att jämföra statuskoder.

    `/api/customers/{id}/history` står UTANFÖR den här listan, och det är inte
    en lucka: den hämtar en SAMLING, inte en resurs. En tom lista är rätt svar
    för en samling utan träffar — 404 vore att säga att vägen inte finns.
    Kravet på 404 för ett FELFORMAT id gäller den ändå, eftersom det aldrig
    kan bli en uppslagning över huvud taget.
    """
    svar = client.get(mall.format("00000000-0000-4000-a000-000000000000"), headers=api_headers)
    assert svar.status_code == 404


def test_historiken_ar_en_samling_och_svarar_tomt(client, api_headers):
    """Motstycket till testet ovan: 200 med tom lista, inte 404."""
    svar = client.get(
        "/api/customers/00000000-0000-4000-a000-000000000000/history", headers=api_headers
    )
    assert svar.status_code == 200
    assert svar.json()["tickets"] == []
