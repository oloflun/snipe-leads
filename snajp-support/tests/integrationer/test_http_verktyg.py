"""HTTP-verktyget: Ebbot-kompatibel konfig, säker ifyllnad, tvättade svar."""

from __future__ import annotations

import json

import httpx
import pytest

from app.integrationer import http_verktyg
from app.integrationer.modell import HttpKonfig, KonfigFel, las_konfig, saknade_hemligheter

#: Ebbots eget exempel ur docs.ebbot.ai (AI Tools -> HTTP request), ordagrant.
EBBOT_EXEMPEL = {
    "requests": [
        {
            "name": "Search catalog",
            "description": "Search our product catalog by keyword.",
            "method": "POST",
            "url": "https://api.example.com/catalog/search?limit={{limit}}",
            "headers": {"Authorization": "Bearer {{token}}", "X-Client": "assistant"},
            "body": {"query": "{{query}}", "includeOutOfStock": False},
            "placeholders": [
                {"key": "query", "type": "string", "description": "Search term"},
                {"key": "limit", "type": "number", "default": 10},
                {"key": "token", "type": "string", "description": "API token"},
            ],
            "responsePath": "items",
        }
    ]
}


def _orderuppslag(**extra) -> HttpKonfig:
    return HttpKonfig.model_validate(
        {
            "requests": [
                {
                    "name": "Orderstatus",
                    "description": "Hämtar status för en order.",
                    "method": "GET",
                    "url": "https://shop.example.com/api/orders/{{ordernummer}}?email={{kund.email}}",
                    "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
                    "placeholders": [
                        {"key": "ordernummer", "type": "string", "description": "Kundens ordernummer"}
                    ],
                    "responsePath": "order.{status: status, levereras: eta}",
                    **extra,
                }
            ]
        }
    )


def test_ebbots_exempel_tas_emot_oforandrat():
    konfig = las_konfig("http", EBBOT_EXEMPEL)
    forfragan = konfig.requests[0]
    assert forfragan.verktygsnamn == "request_search_catalog"
    assert forfragan.ar_skrivande  # POST utan uttrycklig markering
    # Utan sparad hemlighet är token ett argument, precis som hos Ebbot ...
    assert set(forfragan.json_schema()["properties"]) == {"query", "limit", "token"}
    # ... men med en sparad hemlighet som heter token ber vi ALDRIG modellen om den.
    schema = forfragan.json_schema({"token"})
    assert set(schema["properties"]) == {"query", "limit"}
    assert schema["required"] == ["query"]  # limit har default


def test_skrivande_kan_stangas_av_for_en_sokande_post():
    konfig = las_konfig("http", {"requests": [{**EBBOT_EXEMPEL["requests"][0], "skrivande": False}]})
    assert konfig.requests[0].ar_skrivande is False


@pytest.mark.parametrize(
    "andring, fel",
    [
        ({"url": "http://api.example.com/x"}, "https"),
        ({"url": "https://{{vard}}.example.com/x"}, "värdnamnet"),
        ({"url": "https://10.0.0.1/x"}, "internt"),
        ({"method": "TRACE"}, "stöds inte"),
        ({"responsePath": "items[?"}, "JMESPath"),
        ({"headers": {"X-A": "rad\nX-B: injicerad"}}, "radbrytning"),
        ({"method": "GET", "body": {"a": 1}}, "GET-förfrågan"),
    ],
)
def test_ogiltig_konfig_ger_svenskt_besked(andring, fel):
    forfragan = {**EBBOT_EXEMPEL["requests"][0], **andring}
    with pytest.raises(KonfigFel, match=fel):
        las_konfig("http", {"requests": [forfragan]})


def test_hemlighet_i_vardnamnet_ar_tillaten_men_inte_argument():
    las_konfig("http", {"requests": [{"name": "Z", "url": "https://{{hemlighet.instans}}.zendesk.com/api/v2/x"}]})


def test_dubbla_verktygsnamn_avvisas():
    r = EBBOT_EXEMPEL["requests"][0]
    with pytest.raises(KonfigFel, match="samma verktygsnamn"):
        las_konfig("http", {"requests": [r, {**r, "name": "search  catalog"}]})


def test_saknade_hemligheter_rapporteras():
    konfig = _orderuppslag()
    assert saknade_hemligheter("http", konfig, set()) == ["token"]
    assert saknade_hemligheter("http", konfig, {"token"}) == []


def test_handelse_maste_kunna_fyllas_i_av_koden():
    with pytest.raises(KonfigFel, match="kan inte fyllas i"):
        las_konfig(
            "http",
            {
                "requests": [
                    {"name": "Skapa", "method": "POST", "url": "https://x.example.com/t", "body": {"a": "{{fritt}}"}}
                ],
                "handelser": {"arende_eskalerat": "Skapa"},
            },
        )
    ok = las_konfig(
        "http",
        {
            "requests": [
                {
                    "name": "Skapa",
                    "method": "POST",
                    "url": "https://x.example.com/t",
                    "body": {"text": "{{handelse.samtal}}", "fran": "{{kund.email}}"},
                }
            ],
            "handelser": {"arende_eskalerat": "Skapa"},
        },
    )
    # Händelsebundna förfrågningar är inte modellens verktyg.
    assert ok.verktygsforfragningar() == []


@pytest.mark.anyio
async def test_argument_urlkodas_och_kan_inte_skapa_nya_parametrar(svara):
    mottagna = svara(lambda r: httpx.Response(200, json={"order": {"status": "skickad", "eta": "2026-09-22"}}))
    resultat = await http_verktyg.kor(
        _orderuppslag().requests[0],
        argument={"ordernummer": "123/../admin?x=1&email=annan@example.com#"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={"kund.email": "kund@example.com"},
    )
    assert resultat.ok, resultat.fel
    url = mottagna[0].url
    ra_sokvag = url.raw_path.decode("ascii").split("?", 1)[0]
    assert ra_sokvag == "/api/orders/123%2F..%2Fadmin%3Fx%3D1%26email%3Dannan%40example.com%23"
    # Kundens e-post kom från KODEN, och ingen extra parameter smet in.
    assert dict(url.params) == {"email": "kund@example.com"}
    assert mottagna[0].headers["authorization"] == "Bearer hemlig-token-123456"
    assert json.loads(resultat.data) == {"status": "skickad", "levereras": "2026-09-22"}


@pytest.mark.anyio
async def test_modellen_kan_inte_skriva_over_kontext_eller_hemlighet(svara):
    """Ett argument som heter som ett kontextvärde avvisas; och även om det
    slapp igenom skulle kodens värde vinna (varden_for)."""
    svara(lambda r: httpx.Response(200, json={}))
    resultat = await http_verktyg.kor(
        _orderuppslag().requests[0],
        argument={"ordernummer": "1", "kund.email": "annan@example.com"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={"kund.email": "kund@example.com"},
    )
    assert not resultat.ok and "kund.email" in resultat.fel
    varden = http_verktyg.varden_for(
        argument={"kund.email": "annan@example.com", "token": "falsk"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={"kund.email": "kund@example.com"},
    )
    assert varden["kund.email"] == "kund@example.com"
    assert varden["token"] == "hemlig-token-123456"


@pytest.mark.anyio
async def test_body_fylls_i_med_ratt_typ(svara):
    mottagna = svara(lambda r: httpx.Response(200, json={"items": [{"id": 1}], "total": 1}))
    konfig = las_konfig("http", EBBOT_EXEMPEL)
    resultat = await http_verktyg.kor(
        konfig.requests[0],
        argument={"query": 'regnjacka "herr"', "limit": "5"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={},
    )
    assert resultat.ok
    kropp = json.loads(mottagna[0].content)
    # Talet förblev ett tal, citattecknet stannade i sin sträng.
    assert kropp == {"query": 'regnjacka "herr"', "includeOutOfStock": False}
    assert mottagna[0].url.params["limit"] == "5"
    assert json.loads(resultat.data) == [{"id": 1}]  # responsePath "items"


@pytest.mark.anyio
async def test_hemligheten_tvattas_ur_svaret(svara):
    svara(lambda r: httpx.Response(401, json={"error": "ogiltig token hemlig-token-123456"}))
    resultat = await http_verktyg.kor(
        _orderuppslag().requests[0],
        argument={"ordernummer": "1"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={"kund.email": "kund@example.com"},
    )
    assert not resultat.ok and resultat.status == 401
    assert "hemlig-token-123456" not in resultat.data
    assert "[hemlighet]" in resultat.data


@pytest.mark.anyio
async def test_saknat_kontextvarde_blir_ett_begripligt_fel_utan_anrop():
    # Ingen transport satt: ett anrop hade fällt testet (conftest).
    resultat = await http_verktyg.kor(
        _orderuppslag().requests[0],
        argument={"ordernummer": "1"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={"kund.email": None},
    )
    assert not resultat.ok and "kund.email" in resultat.fel


@pytest.mark.anyio
async def test_saknat_argument_och_okant_argument():
    forfragan = _orderuppslag().requests[0]
    saknas = await http_verktyg.kor(forfragan, argument={}, hemligheter={"token": "x" * 10}, kontext={})
    assert "ordernummer saknas" in saknas.fel
    okant = await http_verktyg.kor(
        forfragan, argument={"ordernummer": "1", "admin": True}, hemligheter={"token": "x" * 10}, kontext={}
    )
    assert "admin" in okant.fel


@pytest.mark.anyio
async def test_skrivande_anrop_simuleras_i_testlaget():
    konfig = las_konfig("http", EBBOT_EXEMPEL)
    resultat = await http_verktyg.kor(
        konfig.requests[0],
        argument={"query": "jacka"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={},
        simulera=True,
    )
    assert resultat.ok and resultat.simulerad
    assert "hemlig-token-123456" not in resultat.data
    assert resultat.for_modellen()["simulerat"] is True


@pytest.mark.anyio
async def test_natfel_blir_resultat_inte_undantag(svara):
    def hanterare(request):
        raise httpx.ConnectError("nere")

    svara(hanterare)
    resultat = await http_verktyg.kor(
        _orderuppslag().requests[0],
        argument={"ordernummer": "1"},
        hemligheter={"token": "hemlig-token-123456"},
        kontext={"kund.email": "k@example.com"},
    )
    assert not resultat.ok and "ConnectError" in resultat.fel
