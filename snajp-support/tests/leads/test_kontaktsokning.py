"""Kontaktsökningen hittar det som finns (Antons regler 12–14, 2026-10-07).

Körningen 2026-10-07 lade ungefär hälften av 300+ bolag MED webbplats i
listspåret med "Ingen kontaktmejl på webbplatsen". Varje test här är ett av
de belagda felen, matat både med rå HTML och med html_till_text-texten som
direkthämtningen cachar. Inga nätanrop: sidhämtningen mockas.
"""

from __future__ import annotations

import pytest

from app.leads import discovery, sidhamtning
from app.leads.platshallare import avkoda_cfemail, html_till_text

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _cfemail(adress: str, nyckel: int = 0x42) -> str:
    return f"{nyckel:02x}" + "".join(f"{ord(t) ^ nyckel:02x}" for t in adress)


def _bada(html: str) -> list[str]:
    """Rå HTML och texten direkthämtningen sparar i cachen."""
    return [html, html_till_text(html)]


def _sidor(monkeypatch, sidor: dict[str, str | None], *, js_reserv: str | None = None) -> list[tuple[str, dict]]:
    """Mockar sidhamtning.hamta med färdiga sidor (url → html). Returnerar
    anropen, så att testerna kan se vad som hämtades och hur."""
    anrop: list[tuple[str, dict]] = []

    async def _hamta(url, **kw):
        anrop.append((url, kw))
        if kw.get("utan_cache"):
            return js_reserv, None, "scrapegraphai"
        html = sidor.get(url.rstrip("/"))
        return (html_till_text(html) if html else None), None, "direkt"

    monkeypatch.setattr(sidhamtning, "hamta", _hamta)
    return anrop


# -- 1. w-domänen ------------------------------------------------------------


@pytest.mark.parametrize("webb", ["https://wernerbygg.se", "https://www.wernerbygg.se", "wernerbygg.se"])
def test_doman_som_borjar_pa_w_ar_bolagets(webb):
    """lstrip("www.") tog bort tecknen w och punkt: wernerbygg.se blev
    ernerbygg.se och info@ fälldes mot bolagets egen sajt."""
    assert discovery.ar_arbetsmejl("info@wernerbygg.se", webb=webb)
    assert discovery.ar_arbetsmejl("info@www.wernerbygg.se", webb=webb)
    for text in _bada("<footer>Mejla <a href='mailto:info@wernerbygg.se'>oss</a></footer>"):
        assert discovery.bolagsadress_i_text(text, webb) == "info@wernerbygg.se"
    assert discovery.mottagare({"website": webb, "contact_email": "info@wernerbygg.se"}) == "info@wernerbygg.se"


# -- 3. Länkarna: /om, Företaget, Hitta hit ---------------------------------


def test_om_oss_som_pekar_pa_om_rankas():
    html = (
        '<nav><a href="/om">Om oss</a> <a href="/foretaget">Företaget</a> '
        '<a href="/hitta-hit">Hitta hit</a> <a href="/vilka-vi-ar">Vilka vi är</a> '
        '<a href="/kompetens">Kompetens</a> <a href="/omsorg">Omsorg</a></nav>'
    )
    for text in _bada(html):
        lankar = discovery.extrahera_kontaktlankar(text, "https://alfa.se", tak=5)
        assert lankar[0] == "https://alfa.se/hitta-hit"
        assert set(lankar) == {
            "https://alfa.se/om", "https://alfa.se/foretaget", "https://alfa.se/hitta-hit",
            "https://alfa.se/vilka-vi-ar",
        }


# -- 2. VD:s telefon avbryter inte mejlsökningen ------------------------------


async def test_vd_telefon_och_info_pa_samma_sajt_behaller_info(monkeypatch):
    """Förut returnerade första sidan med VD:s nummer direkt, och info@ på
    kontaktsidan kastades. Nu: mejlet från kontaktsidan, telefonen från VD."""
    _sidor(monkeypatch, {
        "https://alfabygg.se": (
            "<h1>Alfa Bygg</h1><p>Test Testsson, VD, 070-123 45 67</p>"
            + "<p>Vi bygger hus i Mölndal.</p>" * 20
            + '<a href="/kontakt">Kontakt</a>'
        ),
        "https://alfabygg.se/kontakt": "<p>Skriv till info@alfabygg.se</p>",
    })
    kontakt = await discovery.hamta_person_kontakt(
        "https://alfabygg.se", "Test Testsson", bolagsadress_racker=True, bolagsnamn="Alfa Bygg AB"
    )
    assert kontakt["contact_email"] == "info@alfabygg.se"
    assert kontakt["contact_phone"] == "070-123 45 67"
    assert (kontakt["contact_name"], kontakt["contact_role"], kontakt["tilltal_namn"]) == (
        "Test Testsson", "VD", "Test Testsson")
    assert kontakt["contact_level"] == "role_address"


def test_beslutet_ar_detsamma_for_ra_html_och_cachad_text():
    sidor = [
        "<p>Test Testsson, VD, 070-123 45 67</p>",
        "<p>Kontakt: <a href='mailto:info@alfabygg.se'>info@alfabygg.se</a></p>",
    ]
    ra = discovery.kontakt_ur_sidor(sidor, "https://alfabygg.se", "Test Testsson", bolagsadress_racker=True)
    text = discovery.kontakt_ur_sidor(
        [html_till_text(s) for s in sidor], "https://alfabygg.se", "Test Testsson", bolagsadress_racker=True
    )
    for k in (ra, text):
        assert (k["contact_email"], k["contact_phone"], k["contact_name"]) == (
            "info@alfabygg.se", "070-123 45 67", "Test Testsson")


# -- 4. Cloudflare och JSON-LD ------------------------------------------------


def test_cloudflare_skyddad_adress_avkodas():
    kod = _cfemail("info@alfa.se")
    element = (
        f'<p>Mejla <a href="/cdn-cgi/l/email-protection" class="__cf_email__" '
        f'data-cfemail="{kod}">[email&#160;protected]</a></p>'
    )
    lank = f'<p><a href="/cdn-cgi/l/email-protection#{kod}">Skicka mejl</a></p>'
    for html in (element, lank):
        assert "info@alfa.se" in avkoda_cfemail(html)
        text = html_till_text(html)
        assert "E-post: info@alfa.se" in text
        for underlag in (html, text):
            assert discovery.bolagsadress_i_text(underlag, "https://alfa.se") == "info@alfa.se"


def test_skyddad_lank_med_fullstandig_adress_avkodas():
    kod = _cfemail("info@alfa.se")
    for href in (f"https://www.alfa.se/cdn-cgi/l/email-protection#{kod}", f"//alfa.se/cdn-cgi/l/email-protection#{kod}"):
        html = f'<p><a href="{href}">Skicka mejl</a></p>'
        assert f'href="mailto:info@alfa.se"' in avkoda_cfemail(html)
        assert "E-post: info@alfa.se" in html_till_text(html)


def test_lang_rad_utan_citattecken_laser_inte_processen():
    """optera.se 2026-10-09: en lång rad utan citattecken eller blanksteg
    (inbäddad base64) gav kvadratisk tid i adresskyddets mönster och låste
    händelseloopen i två minuter. Samma sida ska nu ta bråkdelen av en sekund."""
    import time

    html = '<img src="data:image/png;base64,' + "A" * 200_000 + '"><p>info@alfa.se</p>'
    start = time.monotonic()
    html_till_text(html)
    avkoda_cfemail(html)
    assert time.monotonic() - start < 2.0


def test_namn_intill_skyddad_adress_blir_personlig_kontakt():
    html = f'<p>Eva Ek, VD — <span class="__cf_email__" data-cfemail="{_cfemail("eva@bolaget.se")}">[email protected]</span></p>'
    for underlag in _bada(html):
        traff = discovery.person_kontakt_i_text(underlag, "https://bolaget.se")
        assert (traff["contact_name"], traff["contact_email"], traff["rang"]) == ("Eva Ek", "eva@bolaget.se", 0)


def test_json_ld_bar_epost_och_telefon():
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"LocalBusiness","name":"Alfa Bygg",'
        '"email":"mailto:info@alfa.se","telephone":"+46 31 123 45 67"}'
        "</script></head><body><p>Välkommen till Alfa Bygg.</p></body></html>"
    )
    text = html_till_text(html)
    assert "E-post: info@alfa.se" in text and "Telefon: +46 31 123 45 67" in text
    assert discovery.bolagsadress_i_text(text, "https://alfa.se") == "info@alfa.se"
    assert discovery.bolagstelefon_i_text(text) == "+46 31 123 45 67"


# -- 5. Obfuskering ---------------------------------------------------------


@pytest.mark.parametrize(
    "skrivet",
    [
        "info @ alfa.se",
        "info at alfa dot se",
        "info(a)alfa.se",
        "info[snabel-a]alfa.se",
        "info (at) alfa (punkt) se",
        "info[at]alfa[dot]se",
        "info{at}alfa.se",
    ],
)
def test_obfuskerade_adresser(skrivet):
    for underlag in _bada(f"<footer>Kontakta oss: {skrivet}</footer>"):
        assert discovery.bolagsadress_i_text(underlag, "https://alfa.se") == "info@alfa.se", underlag


def test_lopande_text_med_at_blir_ingen_adress():
    assert discovery.bolagsadress_i_text("Look at our work. Följ oss @ facebook.com", "https://alfa.se") is None


# -- 3. Gissade sökvägar och den betalda reserven ----------------------------


async def test_gissad_kontaktsida_nar_lankar_saknas(monkeypatch):
    anrop = _sidor(monkeypatch, {
        "https://alfa.se": "<p>Alfa Bygg bygger hus.</p>" * 30,
        "https://alfa.se/kontakt": "<p>Mejla hej@alfa.se eller ring 031-12 34 56</p>",
    })
    kontakt = await discovery.hamta_person_kontakt("https://alfa.se", None, bolagsadress_racker=True)
    assert kontakt["contact_email"] == "hej@alfa.se"
    gissningar = [(u, kw) for u, kw in anrop if u != "https://alfa.se"]
    assert gissningar[0][0] == "https://alfa.se/kontakt"
    assert all(kw.get("betald") is False for _, kw in gissningar), "en gissning får aldrig kosta"
    # Mejlet hittat på andra sidan: inga fler gissningar.
    assert len(gissningar) == 1


async def test_ingen_gissning_nar_kontaktlanken_finns(monkeypatch):
    anrop = _sidor(monkeypatch, {
        "https://alfa.se": "<p>Alfa Bygg bygger hus.</p>" * 30 + '<a href="/kontakta-oss">Kontakta oss</a>',
        "https://alfa.se/kontakta-oss": "<p>Inget här.</p>",
    })
    assert await discovery.hamta_person_kontakt("https://alfa.se", None, bolagsadress_racker=True) is None
    assert [u for u, _ in anrop] == ["https://alfa.se", "https://alfa.se/kontakta-oss"]


async def test_kort_startsida_utan_kontakt_far_betald_reserv(monkeypatch):
    """En JS-renderad startsida ger en tunn direkttext. Då, och bara för
    startsidan, får den betalda hämtningen ta vid."""
    anrop = _sidor(
        monkeypatch,
        {"https://spa.se": "<div id='app'>Laddar Spa Bygg</div>"},
        js_reserv="Spa Bygg AB\nKontakt: info@spa.se",
    )
    kontakt = await discovery.hamta_person_kontakt("https://spa.se", None, bolagsadress_racker=True)
    assert kontakt["contact_email"] == "info@spa.se"
    reserv = [kw for _, kw in anrop if kw.get("utan_cache")]
    assert reserv == [{"fas": "webb", "direkt": False, "utan_cache": True}]


async def test_takstopp_markeras(monkeypatch):
    async def _hamta(url, **kw):
        return None, "kredittaket för körningen (60 anrop) är nått", "tak"

    monkeypatch.setattr(sidhamtning, "hamta", _hamta)
    kontakt = await discovery.hamta_person_kontakt("https://alfa.se", None, bolagsadress_racker=True)
    assert kontakt == {"tak": True}


# -- 6. Bolagets telefon ------------------------------------------------------


@pytest.mark.parametrize(
    ("html", "vantat"),
    [
        ("<p>Tel: 031-12 34 56</p>", "031-12 34 56"),
        ("<p>Växel 08-123 456 78</p>", "08-123 456 78"),
        ("<p>Ring oss på 070-123 45 67!</p>", "070-123 45 67"),
        ("<p>Telefonnummer: 0321-123 45</p>", "0321-123 45"),
        ('<a href="tel:+46311234567">Ring</a>', "+46311234567"),
    ],
)
def test_bolagets_telefon_utan_vd(html, vantat):
    for underlag in _bada(html):
        assert discovery.bolagstelefon_i_text(underlag) == vantat


def test_nummer_utan_etikett_raknas_inte():
    assert discovery.bolagstelefon_i_text("<p>Org.nr 556677-8899, bankgiro 123-4567</p>") is None


async def test_sajtens_telefon_foljer_med_utan_mejl(monkeypatch):
    _sidor(monkeypatch, {"https://alfa.se": "<p>Alfa Bygg bygger hus.</p>" * 30 + "<p>Tel: 031-12 34 56</p>"})
    kontakt = await discovery.hamta_person_kontakt("https://alfa.se", None, bolagsadress_racker=True)
    assert (kontakt["contact_email"], kontakt["contact_phone"]) == (None, "031-12 34 56")


# -- 11. HR- och robotadresser: hela lokaldelen ------------------------------


@pytest.mark.parametrize("adress", ["lone.berg@alfa.se", "jobbet.anna@alfa.se", "henrik@alfa.se", "pressinfo@alfa.se"])
def test_saljadress_som_bara_borjar_som_ett_funktionsord(adress):
    assert discovery.ar_saljadress(adress)


@pytest.mark.parametrize(
    "adress",
    ["lon@alfa.se", "lon.goteborg@alfa.se", "jobb@alfa.se", "jobs@alfa.se", "noreply@alfa.se", "no_reply@alfa.se",
     "rekrytering@alfa.se", "faktura2@alfa.se", "hr@alfa.se", "careers@alfa.se"],
)
def test_funktionsadresser_falls_fortfarande(adress):
    assert not discovery.ar_saljadress(adress)


# -- 13. Mottagaren -----------------------------------------------------------


def test_bolagets_publicerade_adress_duger_for_iris_prospekt():
    """Regel 13: en adress bolaget publicerar på sin sajt duger även på gmail
    eller en annan domän — för Iris egna prospekt, vars adress bara kommer ur
    sajten eller registret. För en lista eller import gäller domänen."""
    webb = "https://alfa.se"
    assert discovery.mottagare({"origin": "iris", "website": webb, "contact_email": "alfa.bygg@gmail.com"}) == (
        "alfa.bygg@gmail.com")
    assert discovery.mottagare({"origin": "iris", "website": webb, "contact_email": "info@alfabygg.nu"}) == (
        "info@alfabygg.nu")
    for origin in ("lista", "import", "manual", None):
        assert discovery.mottagare({"origin": origin, "website": webb, "contact_email": "alfa.bygg@gmail.com"}) is None
    for fel in ("rekrytering@gmail.com", "logo@2x.png", "noreply@alfa.se"):
        assert discovery.mottagare({"origin": "iris", "website": webb, "contact_email": fel}) is None, fel


# -- 14. Tilltal ------------------------------------------------------------


def test_tilltal_tva_personer_med_agare():
    sida = (
        "<h2>Om oss</h2><p>Anna Andersson, grundare och ägare. Anna har byggt hus i 20 år.</p>"
        "<p>Per Palm, snickare.</p>"
    )
    for underlag in _bada(sida):
        assert discovery.tilltal_for_sidor([underlag], bolagsnamn="Alfa Bygg AB") == ("Anna Andersson", "grundare")


def test_tilltal_fyra_personer_ger_inget_namn():
    sida = (
        "<p>Anna Andersson, VD</p><p>Per Palm, snickare</p>"
        "<p>Lisa Lind, projektledare</p><p>Olle Ost, elektriker</p>"
    )
    for underlag in _bada(sida):
        assert discovery.tilltal_for_sidor([underlag], bolagsnamn="Alfa Bygg AB") == (None, None)


def test_tilltal_registrets_vd_pa_sajten():
    sida = "<p>Anna Andersson, VD</p><p>Per Palm</p><p>Lisa Lind</p><p>Olle Ost</p><p>Kim Kula</p>"
    assert discovery.tilltal_for_sidor([sida], "Anna Maria Andersson") == ("Anna Maria Andersson", "VD")


def test_tilltal_personlig_adress_ger_personens_namn():
    sidor = [
        "<p>Lisa Lind, säljare — lisa@alfa.se</p><p>Per Palm, snickare</p><p>Olle Ost, elektriker</p>",
        "<p>info@alfa.se</p>",
    ]
    k = discovery.kontakt_ur_sidor(sidor, "https://alfa.se", bolagsadress_racker=True)
    assert (k["contact_email"], k["tilltal_namn"]) == ("lisa@alfa.se", "Lisa Lind")


def test_tilltal_bolagets_namn_ar_ingen_person():
    sida = "<p>Alfa Bygg, ägare av fastigheten. Kontakt: info@alfabygg.se</p>"
    assert discovery.tilltal_for_sidor([sida], bolagsnamn="Alfa Bygg AB") == (None, None)
    k = discovery.kontakt_ur_sidor([sida], "https://alfabygg.se", bolagsadress_racker=True, bolagsnamn="Alfa Bygg AB")
    assert (k["contact_email"], k["contact_name"], k["tilltal_namn"]) == ("info@alfabygg.se", None, None)


# -- 4/8. Sidhämtningen: cacheversion, gratis gissning och eget tak --------


async def test_webbsidornas_tak_ar_skilt_fran_registrets(monkeypatch):
    monkeypatch.setenv("SCRAPEGRAPHAI_API_KEY", "sgai-test")
    from app.config import get_settings

    get_settings.cache_clear()
    anrop: list[str] = []

    async def sg(url):
        anrop.append(url)
        return "innehåll " * 20, None

    async def direkt(url):
        return None, "direkthämtning: HTTP 403"

    monkeypatch.setattr(sidhamtning, "_scrapegraph", sg)
    monkeypatch.setattr("app.agent.research_tools._hamta_direkt", direkt)
    try:
        kontext = sidhamtning.starta(None, "t", tak=1, webb_tak=1)
        assert (await sidhamtning.hamta("https://www.merinfo.se/foretag/a", fas="bolag", direkt=False))[2] == "scrapegraphai"
        assert kontext.slut and not kontext.webb_slut
        # Registrets tak är slut, men bolagets sajt får fortfarande läsas.
        assert (await sidhamtning.hamta("https://alfa.se", fas="webb", direkt=True))[2] == "scrapegraphai"
        assert kontext.webb_slut
        assert (await sidhamtning.hamta("https://beta.se", fas="webb", direkt=True))[2] == "tak"
        # En gissning kostar aldrig, inte ens när taket finns kvar.
        sidhamtning.starta(None, "t", webb_tak=10)
        assert (await sidhamtning.hamta("https://alfa.se/kontakt", fas="webb", direkt=True, betald=False))[0] is None
        assert anrop == ["https://www.merinfo.se/foretag/a", "https://alfa.se"]
    finally:
        get_settings.cache_clear()


async def test_gammal_cachad_webbsida_hamtas_om(monkeypatch):
    """Sidor cachade före kontaktraderna (JSON-LD, mailto, Cloudflare) saknar
    dem; webbsidorna har därför en ny cachenyckel."""
    from app.storage.memory import MemoryStorage

    lager = MemoryStorage()
    await lager.put_sidcache("t", "https://alfa.se", innehall="gammal text utan adress", fel=None)

    async def direkt(url):
        return "Alfa Bygg\nE-post: info@alfa.se" + " text" * 20, None

    monkeypatch.delenv("LEADS_DIREKTHAMTNING", raising=False)
    monkeypatch.setattr("app.agent.research_tools._hamta_direkt", direkt)
    sidhamtning.starta(lager, "t")
    text, _fel, via = await sidhamtning.hamta("https://alfa.se", fas="webb", direkt=True)
    assert via == "direkt" and "info@alfa.se" in text
    # Andra gången ur den nya nyckeln, och registrets sidor har kvar sin.
    assert (await sidhamtning.hamta("https://alfa.se", fas="webb", direkt=True))[2] == "cache"


# -- 10. Researchen fäster bolagets adress på ett lead med namn ------------


async def test_bolagsadressen_fasts_aven_nar_leadet_bar_ett_namn():
    """Resten av den ersatta regel 10a vägrade info@ för att adressen inte bar
    VD:s namn. Regel 10/13: bolagets adress räcker."""
    from app.agent.leads_agent import _uppgradera_kontakt
    from app.storage.memory import MemoryStorage

    lager = MemoryStorage()
    p = await lager.create_prospect(
        "t", company_name="Alfa Bygg AB", contact_name="Test Testsson",
        profil={"website": "https://alfabygg.se", "contact_role": "VD", "contact_level": "named_role_match"},
    )
    await _uppgradera_kontakt(
        lager, "t", p["id"], prospect=await lager.get_prospect("t", p["id"]),
        fynd={}, material="Kontakta oss på info@alfabygg.se. Jobb: rekrytering@alfabygg.se",
    )
    rad = await lager.get_prospect("t", p["id"])
    assert (rad["contact_name"], rad["contact_email"]) == ("Test Testsson", "info@alfabygg.se")


async def test_modellens_namn_skriver_inte_over_tilltalet():
    from app.agent.leads_agent import _uppgradera_kontakt
    from app.storage.memory import MemoryStorage

    lager = MemoryStorage()
    p = await lager.create_prospect(
        "t", company_name="Alfa Bygg AB", contact_email="info@alfabygg.se", origin="iris",
        profil={"website": "https://alfabygg.se", "contact_level": "role_address"},
    )
    await _uppgradera_kontakt(
        lager, "t", p["id"], prospect=await lager.get_prospect("t", p["id"]),
        fynd={"contact_name": "Mikael Modell", "contact_role": "Säljare"}, material="info@alfabygg.se",
    )
    rad = await lager.get_prospect("t", p["id"])
    assert rad["contact_name"] is None, "regel 14: bolagets adress utan styrkt tilltal ger 'Hej,'"
