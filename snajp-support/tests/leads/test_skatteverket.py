"""Beskattningsengagemang-klienten: identitetsformat, aktivitet och felkoder.

Tyngdpunkten ligger på det som faktiskt går fel i drift, inte på att httpx
fungerar:

  * Ett 200-svar betyder INTE att engagemanget gäller idag. Skatteverket
    returnerar senaste registreringen, som kan vara avslutad eller ha ett
    startdatum i framtiden — och ett null-test hade läst "avregistrerad för
    konkurs" som ett godkänt bolag.
  * Identiteten är tolv siffror med sekelprefix, medan `orgnr.normalisera`
    strippar just det prefixet. Skarven mellan dem är där ett anrop tyst blir
    en 400:a.
  * 404 är ett giltigt svar (aldrig haft engagemanget), inte ett fel.

Inget test öppnar en socket — httpx.AsyncClient byts ut, samma mönster som
test_send_provider.py använder för ResendMailer.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.config import Settings
from app.leads.orgnr import OgiltigtOrgnrError
from app.leads.skatteverket import (
    Engagemang,
    SkatteverketAuktoriseringsfel,
    SkatteverketEngagemang,
    SkatteverketFel,
    SkatteverketTillfalligtFel,
    get_skatteverket_klient,
    paborja_inloggning,
    till_identitet,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


def _klient() -> SkatteverketEngagemang:
    return SkatteverketEngagemang(
        bas_url="https://api.test.skatteverket.se",
        client_id="test-id",
        client_secret="test-hemlighet",
    )


class _Svar:
    def __init__(self, kod: int, kropp: dict | None = None):
        self.status_code = kod
        self._kropp = kropp or {}

    def json(self):
        return self._kropp


def _fejka(monkeypatch, svar: _Svar, spar: dict | None = None):
    """Byter ut httpx.AsyncClient mot en som svarar `svar` och sparar anropet."""

    class _Klient:
        def __init__(self, **kw):
            if spar is not None:
                spar["timeout"] = kw.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            if spar is not None:
                spar["url"] = url
                spar["headers"] = headers
            return svar

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _Klient)


# -- Identitetsformatet -----------------------------------------------------


def test_juridisk_person_far_sekelprefixet_16():
    """Tio siffror in, tolv ut. Utan prefixet svarar Skatteverket 400."""
    assert till_identitet("556824-9022") == "165568249022"
    assert till_identitet("5568249022") == "165568249022"


def test_redan_prefixat_orgnr_dubbelprefixas_inte():
    """`16556824-9022` förekommer i myndighetsregister och ska ge samma sak."""
    assert till_identitet("165568249022") == "165568249022"


def test_enskild_firma_behaller_sitt_sekel():
    """En enskild firmas orgnr ÄR ett personnummer (se orgnr._strip_sekel).

    Formatet är då ÅÅÅÅMMDDNNNN och 19/20-prefixet måste bevaras — hade det
    strippats och ersatts med 16 pekade anropet på en annan identitet.
    """
    assert till_identitet("19850312-1231") == "198503121231"


def test_kontrollsiffran_provas_aven_for_personnummer():
    """Regressionsskydd: den första versionen returnerade ett tolvsiffrigt
    personnummer OGRANSKAT, eftersom sekelprefixet lästes som 'redan rätt
    form'. Ett felskrivet nummer gick då hela vägen till Skatteverket och
    kom tillbaka som en 400:a utan förklaring."""
    with pytest.raises(OgiltigtOrgnrError):
        till_identitet("19850312-1234")  # samma nummer, fel kontrollsiffra


def test_skrapmat_avvisas_med_orgnr_modulens_fel():
    """Formatkontrollen delas med onboardingen — inget eget regelverk här."""
    with pytest.raises(OgiltigtOrgnrError):
        till_identitet("123")


# -- Vad ett 200-svar betyder ----------------------------------------------


def test_avslutat_engagemang_ar_inte_aktivt():
    """DET HÄR ÄR HELA POÄNGEN med ar_aktiv().

    F-skatten drogs in 2019 för konkurs. Skatteverket svarar 200 med posten
    kvar, och ett `is not None`-test hade godkänt bolaget.
    """
    e = Engagemang(
        typ="fskatt",
        startdatum=date(2013, 5, 7),
        slutdatum=date(2019, 3, 1),
        avslutsorsak="Konkurs",
        avslutsorsak_kod=503,
    )
    assert e.ar_aktiv(date(2026, 8, 29)) is False
    assert e.ar_aktiv(date(2015, 1, 1)) is True


def test_framtida_startdatum_ar_inte_aktivt_an():
    e = Engagemang(typ="moms", startdatum=date(2027, 1, 1))
    assert e.ar_aktiv(date(2026, 8, 29)) is False


def test_lopande_engagemang_utan_slutdatum_ar_aktivt():
    e = Engagemang(typ="moms", startdatum=date(1997, 1, 1))
    assert e.ar_aktiv(date(2026, 8, 29)) is True


def test_sista_giltighetsdagen_raknas_som_aktiv():
    """Slutdatum jämförs inklusivt — sista dagen är fortfarande en giltig dag."""
    e = Engagemang(typ="fskatt", startdatum=date(2020, 1, 1), slutdatum=date(2026, 8, 29))
    assert e.ar_aktiv(date(2026, 8, 29)) is True
    assert e.ar_aktiv(date(2026, 8, 30)) is False


def test_utan_startdatum_kan_vi_inte_visa_att_det_galler():
    """Ett oläsligt datum ska falla åt 'vet inte', inte åt 'godkänt'."""
    assert Engagemang(typ="fskatt").ar_aktiv(date(2026, 8, 29)) is False


# -- Anropet ----------------------------------------------------------------


async def test_fskatt_bygger_ratt_url_och_headers(monkeypatch):
    spar: dict = {}
    _fejka(
        monkeypatch,
        _Svar(200, {"startdatum": "2013-05-07", "skatteform": "FA"}),
        spar,
    )

    engagemang = await _klient().fskatt("556824-9022", access_token="token-abc")

    assert spar["url"] == (
        "https://api.test.skatteverket.se"
        "/beskattning/foretag/engagemang/v1/165568249022/fskatt"
    )
    assert spar["headers"]["Authorization"] == "Bearer token-abc"
    assert spar["headers"]["client_id"] == "test-id"
    assert spar["headers"]["Accept"] == "application/json"
    # Skatteverket auditloggar korrelations-id:t i fem år och kräver att det
    # är unikt per anrop. uuid4 är 36 tecken, exakt takets längd.
    assert len(spar["headers"]["skv_client_correlation_id"]) == 36
    assert engagemang.extra["skatteform"] == "FA"
    assert engagemang.startdatum == date(2013, 5, 7)


async def test_korrelationsid_aterananvands_aldrig(monkeypatch):
    """Tjänstebeskrivningen 2.6 är uttrycklig: id:n får inte återanvändas."""
    sedda = set()

    for _ in range(3):
        spar: dict = {}
        _fejka(monkeypatch, _Svar(200, {"startdatum": "2013-05-07"}), spar)
        await _klient().fskatt("556824-9022", access_token="t")
        sedda.add(spar["headers"]["skv_client_correlation_id"])

    assert len(sedda) == 3


async def test_ombud_skickas_bara_nar_det_finns(monkeypatch):
    """`skv_ext_ombud` behövs inte vid inloggning med BankID (5.5)."""
    spar: dict = {}
    _fejka(monkeypatch, _Svar(200, {"startdatum": "2013-05-07"}), spar)
    await _klient().fskatt("556824-9022", access_token="t")
    assert "skv_ext_ombud" not in spar["headers"]

    spar = {}
    _fejka(monkeypatch, _Svar(200, {"startdatum": "2013-05-07"}), spar)
    await _klient().fskatt("556824-9022", access_token="t", ombud="196001011234")
    assert spar["headers"]["skv_ext_ombud"] == "196001011234"


async def test_moms_behaller_alla_extrauppgifter(monkeypatch):
    """momstyp och redovisningsmetod är precis det bookkeeping-agenten
    annars svarar generiskt om — de får inte tappas i mappningen."""
    _fejka(
        monkeypatch,
        _Svar(
            200,
            {
                "startdatum": "1997-01-01",
                "momstyp": "Kvartal den 12:e",
                "momstypKod": 203,
                "redovisningsmetod": "Faktureringsmetod",
                "redovisningsmetodKod": 301,
                "skattskyldigFROM": "1997-01-01",
                "frivilligTidigRedovisning": False,
            },
        ),
    )

    moms = await _klient().moms("556824-9022", access_token="t")

    assert moms.extra["momstyp"] == "Kvartal den 12:e"
    assert moms.extra["redovisningsmetod"] == "Faktureringsmetod"
    assert moms.extra["skattskyldigFROM"] == "1997-01-01"
    assert moms.ar_aktiv(date(2026, 8, 29)) is True


async def test_arbetsgivare_bar_sasongsflaggan(monkeypatch):
    _fejka(
        monkeypatch,
        _Svar(200, {"startdatum": "1997-01-01", "sasongsarbetsgivare": True}),
    )
    ag = await _klient().arbetsgivare("556824-9022", access_token="t")
    assert ag.extra["sasongsarbetsgivare"] is True


# -- Felkoderna -------------------------------------------------------------


async def test_404_ar_inget_fel_utan_aldrig_haft_engagemanget(monkeypatch):
    """'Om personen aldrig haft engagemanget returneras ingenting' (4.2.2)."""
    _fejka(monkeypatch, _Svar(404))
    assert await _klient().fskatt("556824-9022", access_token="t") is None


@pytest.mark.parametrize("kod", [401, 403])
async def test_auktoriseringsfel_far_egen_typ(monkeypatch, kod):
    """Åtgärden är att logga in användaren igen, inte att försöka om."""
    _fejka(monkeypatch, _Svar(kod))
    with pytest.raises(SkatteverketAuktoriseringsfel):
        await _klient().fskatt("556824-9022", access_token="utgangen")


@pytest.mark.parametrize("kod", [429, 500, 503, 504])
async def test_tillfalliga_fel_far_egen_typ(monkeypatch, kod):
    _fejka(monkeypatch, _Svar(kod))
    with pytest.raises(SkatteverketTillfalligtFel) as fel:
        await _klient().fskatt("556824-9022", access_token="t")
    assert "minut" in str(fel.value)


async def test_ovriga_fel_blir_basklassen(monkeypatch):
    _fejka(monkeypatch, _Svar(400))
    with pytest.raises(SkatteverketFel):
        await _klient().fskatt("556824-9022", access_token="t")


async def test_svarskroppen_loggas_aldrig(monkeypatch, caplog):
    """Beskattningsuppgifter för en identifierad näringsidkare — och för en
    enskild firma är identiteten ett personnummer. Bara korrelations-id:t."""
    _fejka(
        monkeypatch,
        _Svar(200, {"startdatum": "2013-05-07", "skatteform": "FA"}),
    )
    with caplog.at_level("DEBUG"):
        await _klient().fskatt("556824-9022", access_token="t")

    loggat = "\n".join(post.getMessage() for post in caplog.records)
    assert "165568249022" not in loggat
    assert "FA" not in loggat
    assert "2013-05-07" not in loggat


# -- Konfigurationen --------------------------------------------------------


def test_utan_nycklar_finns_ingen_klient():
    """Miljön ska starta och fungera utan verifieringen — onboardingen faller
    tillbaka på Luhn-kontrollen, precis som idag."""
    assert get_skatteverket_klient(_settings()) is None


def test_halvsatt_konfiguration_raknas_som_osatt(caplog):
    with caplog.at_level("WARNING"):
        assert get_skatteverket_klient(_settings(skatteverket_client_id="bara-id")) is None
    assert "halvsatt" in caplog.text


def test_med_bada_nycklarna_byggs_klienten():
    klient = get_skatteverket_klient(
        _settings(skatteverket_client_id="id", skatteverket_client_secret="hemlis")
    )
    assert isinstance(klient, SkatteverketEngagemang)
    # Testmiljön är default med flit: en testnyckel mot produktion hade
    # slagit mot riktiga beskattningsuppgifter.
    assert klient.bas_url == "https://api.test.skatteverket.se"


def test_inloggningen_ar_en_arlig_stub():
    """Samma hållning som sources/registry.py: gränsen möts i koden, inte i
    en handoff ingen läser."""
    with pytest.raises(NotImplementedError) as fel:
        paborja_inloggning()
    assert "e-legitimation" in str(fel.value) or "Authorization Code Grant" in str(fel.value)
