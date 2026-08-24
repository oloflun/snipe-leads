"""Leverantörens kvot är inte en krasch, och ska inte se ut som en.

Ett 429 från modelleverantören renderades som "Något gick fel på vår sida.
Felet är loggat" — exakt samma svar som ett nullpointerfel. Den som felsökte
gick till loggen och hittade en stack som slutade i http-klienten; att frågan
egentligen var "kvoten är slut, kolla planen" tog en halvtimme att komma fram
till.

Det är samma klass av fel som resten av kodbasen redan jagat: ett tillstånd
som HAR en begriplig orsak, presenterat som ett okänt haveri.
"""

import pytest

from app.api.events import _ar_kvotfel


class _FejkatKvotfel(Exception):
    """Speglar openai.RateLimitError utan att importera biblioteket."""

    status_code = 429


class RateLimitError(Exception):
    """Namnet är det leverantörens klass heter."""


class ResourceExhausted(Exception):
    """Googles namn på samma sak."""


@pytest.mark.parametrize(
    "fel",
    [
        _FejkatKvotfel("nope"),
        RateLimitError("nope"),
        ResourceExhausted("nope"),
        Exception(
            "Error code: 429 - [{'error': {'code': 429, 'message': 'You exceeded "
            "your current quota, please check your plan and billing details.'}}]"
        ),
    ],
)
def test_kvotfel_kanns_igen(fel):
    assert _ar_kvotfel(fel)


@pytest.mark.parametrize(
    "fel",
    [
        ValueError("något helt annat"),
        Exception("Error code: 500 - internal"),
        Exception("429 kr exklusive moms"),  # ett belopp, inte en statuskod
        TypeError("NoneType is not subscriptable"),
    ],
)
def test_riktiga_fel_maskeras_inte_som_kvot(fel):
    """Det farliga är åt andra hållet: ett riktigt fel som rapporteras som
    'kvoten är slut' skickar felsökaren till leverantörens fakturasida i
    stället för till buggen."""
    assert not _ar_kvotfel(fel)
