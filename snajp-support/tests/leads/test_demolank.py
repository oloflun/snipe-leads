"""Demolänken i utkasten och A/B-mätningen av svar och klick (Anton 2026-11-15).

app/leads/demolank.py, migration 116, svar.py:s nya klass 'aterkom' och
erbjudanden.sammanstall. Allt i minne, inget LLM utom den fejkade kedjan.
"""

import pytest

from app.leads import demolank, erbjudanden
from app.leads.signatur import dela_utkast
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"


@pytest.fixture
def anyio_backend():
    return "asyncio"


URL = "https://snajp.test/prova/abcDEF12345"
RAD_DU = f"{demolank.RAD['du']} {URL}"


# -- Placeringen ------------------------------------------------------------


def test_raden_star_i_eget_stycke_fore_halsningsfrasen_och_signaturen():
    text = (
        "Hej Anna,\n\nNi bygger åt bostadsrättsföreningar. Iris hittar fler sådana.\n\n"
        "Vill du veta mer bokar vi en genomgång.\n\nVänliga hälsningar,\nAnton Lundin\nSnajp\n\n--\nFot"
    )
    ny = demolank.med_demolank(text, RAD_DU, svans_start=text.index("Anton Lundin"))
    assert ny.index(RAD_DU) < ny.index("Vänliga hälsningar,") < ny.index("Anton Lundin") < ny.index("--\nFot")
    assert f"genomgång.\n\n{RAD_DU}\n\nVänliga hälsningar," in ny
    # Idempotent: en andra körning lägger inte till en rad till.
    assert demolank.med_demolank(ny, RAD_DU) == ny


def test_utan_halsningsfras_hamnar_raden_sist_i_brodtexten():
    assert demolank.med_demolank("Hej,\n\nText.", RAD_DU) == f"Hej,\n\nText.\n\n{RAD_DU}"


def test_modellens_nakna_demoadress_blir_en_hanvisning_till_lanken():
    demo = ["https://www.snajp.se/demo/leads"]
    sv = demolank.utan_bar_demo(
        "Titta gärna på demon på snajp.se/demo, eller svara så bokar vi en genomgång.", demo, sprak="sv"
    )
    assert sv == "Titta gärna på demon via länken nedan, eller svara så bokar vi en genomgång."
    assert demolank.utan_bar_demo("Gå in på https://www.snajp.se/demo/leads.", demo, sprak="sv") == (
        "Gå in via länken nedan."
    )
    en = demolank.utan_bar_demo("See the demo at snajp.se/demo.", demo, sprak="en")
    assert en == "See the demo via the link below."
    # Bolagets namn och andra adresser rörs inte.
    assert demolank.utan_bar_demo("Snajp (snajp.se) svarar.", demo, sprak="sv") == "Snajp (snajp.se) svarar."


def test_tilltalet_och_spraket_foljer_mejlet():
    assert demolank.rad(URL, sprak="sv", du=False).startswith("Länk till vår demo, där ni kan se")
    assert demolank.rad(URL, sprak="sv", du=True).startswith("Länk till vår demo, där du kan se")
    assert "testa mot ert företag: " + URL in demolank.rad(URL, sprak="sv", du=True)
    assert demolank.rad(URL, sprak="en", du=True).startswith("Here is a link to our demo")


# -- Kundens val --------------------------------------------------------------


def test_demolanken_ar_en_url_for_alla_eller_en_per_produkt():
    assert demolank.normalisera("snajp.se/demo") == "https://snajp.se/demo"
    assert demolank.normalisera({"Iris": "https://snajp.se/demo/leads", "X": "inte en url"}) == {
        "Iris": "https://snajp.se/demo/leads"
    }
    assert demolank.demo_for({"Iris": "a", "Supportagent": "b"}, "supportagent") == "b"
    # Okänd produkt: den första, hellre en demo än ingen.
    assert demolank.demo_for({"Iris": "a", "Supportagent": "b"}, None) == "a"
    with pytest.raises(ValueError, match="inte finns bland era produkter"):
        demolank.validera({"Okänd": "https://x.se"}, ["Iris"])
    with pytest.raises(ValueError, match="webbadress"):
        demolank.validera("inte en adress med mellanslag", [])
    assert demolank.validera("", []) is None


def test_erbjudandevalet_bar_demolanken():
    val = erbjudanden.validera([], {}, ["Iris"], demo={"Iris": "https://snajp.se/demo/leads"})
    assert val["demo"] == {"Iris": "https://snajp.se/demo/leads"}
    assert "demo" not in erbjudanden.normalisera({})


# -- Hela vägen: utkastet köas med en spårad länk -----------------------------


@pytest.mark.anyio
async def test_utkastet_koas_med_spårad_demolank_och_strukturen_sparas(monkeypatch):
    from tests.agent.test_leads_v2_wiring import _FakeLLM
    from tests.leads.test_utkaststruktur_b import IRIS, SIG, _forbered, _skriv

    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    try:
        monkeypatch.setattr(get_settings(), "publik_bas_url", "https://snajp.test")
        storage = MemoryStorage()
        thread_id, _ = await _forbered(storage)
        installningar = await storage.get_agent_settings(TENANT, agent_type="leads")
        installningar["erbjudanden"]["demo"] = {IRIS: "https://snajp.test/demo/leads"}
        await storage.set_agent_settings(TENANT, agent_type="leads", settings=installningar)

        svar = await _skriv(storage, thread_id, _FakeLLM(), "a")
        assert svar["queued"], svar.get("escalation_reason")
        kropp = storage.outreach_messages[TENANT][0]["body"]
        token = next(iter(storage.demolankar))
        assert f"https://snajp.test/prova/{token}" in kropp
        brodtext, svans = dela_utkast(kropp, SIG)
        # Raden i brödtexten, efter texten och före hälsningsfrasen och signaturen.
        assert "Länk till vår demo" in brodtext and "Länk till vår demo" not in svans
        assert brodtext.index("Länk till vår demo") < brodtext.rindex("Vänliga hälsningar")
        assert storage.demolankar[token]["mal_url"] == "https://snajp.test/demo/leads"
        assert (await storage.get_outreach_thread(TENANT, thread_id))["struktur"] == "a"
    finally:
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_utan_demolank_i_installningarna_ror_koden_ingenting(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "publik_bas_url", "https://snajp.test")
    storage = MemoryStorage()
    text = "Hej,\n\nText."
    assert await demolank.lagg_till(storage, TENANT, "t1", text, sprak="sv", installningar={}) == text
    assert storage.demolankar == {}


# -- Mätningen ------------------------------------------------------------------


async def _skickad_trad(storage, namn: str, *, nyckel: str, struktur: str) -> str:
    prospekt = await storage.create_prospect(TENANT, company_name=namn, contact_name="Anna")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
    await storage.tilldela_erbjudande(TENANT, trad["id"], nyckel=nyckel)
    await storage.satt_trad_struktur(TENANT, trad["id"], struktur)
    koat = await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body="Hej", subject="Ä", humanizer_variant="snajp:humanizer-svenska",
        scheduled_at=None, status="awaiting_review",
    )
    await storage.mark_outreach_message_sent(TENANT, koat["message"]["id"], "2026-11-15T09:00:00+00:00")
    return trad["id"]


@pytest.mark.anyio
async def test_ja_nej_kanske_och_klick_raknas_per_erbjudande_och_struktur():
    storage = MemoryStorage()
    ja = await _skickad_trad(storage, "Ja AB", nyckel="pilot", struktur="a")
    nej = await _skickad_trad(storage, "Nej AB", nyckel="pilot", struktur="a")
    kanske = await _skickad_trad(storage, "Kanske AB", nyckel="pilot", struktur="b")
    tyst = await _skickad_trad(storage, "Tyst AB", nyckel="pilot", struktur="b")
    await storage.satt_svarsklass(TENANT, ja, "positivt")
    await storage.satt_svarsklass(TENANT, nej, "avregistrering")
    await storage.satt_svarsklass(TENANT, kanske, "aterkom")

    # Ja AB besöker demon; Tyst AB:s e-postskydd klickar bara.
    t_ja = await storage.demolanktoken(TENANT, thread_id=ja, mal_url="https://snajp.test/demo")
    assert await storage.registrera_demolank(t_ja, typ="klick", user_agent="Mozilla/5.0 Chrome") == (
        "https://snajp.test/demo"
    )
    assert await storage.registrera_demolank(t_ja, typ="besok") == "ok"
    t_tyst = await storage.demolanktoken(TENANT, thread_id=tyst, mal_url="https://snajp.test/demo")
    await storage.registrera_demolank(t_tyst, typ="klick", user_agent="Microsoft SafeLinks preview")
    assert await storage.registrera_demolank("okand", typ="klick") is None
    # Samma tråd ger samma token, med ny mål-URL.
    assert await storage.demolanktoken(TENANT, thread_id=ja, mal_url="https://snajp.test/demo/leads") == t_ja

    rad = {r["nyckel"]: r for r in await storage.erbjudande_utfall(TENANT)}["pilot"]
    assert {k: rad[k] for k in ("skickade", "svar", "ja", "nej", "kanske", "fragor", "klick", "besok")} == {
        "skickade": 4, "svar": 3, "ja": 1, "nej": 1, "kanske": 1, "fragor": 0, "klick": 1, "besok": 1,
    }
    strukturer = {r["nyckel"]: r for r in await storage.struktur_utfall(TENANT)}
    assert (strukturer["a"]["ja"], strukturer["a"]["nej"], strukturer["a"]["klick"]) == (1, 1, 1)
    assert (strukturer["b"]["kanske"], strukturer["b"]["klick"]) == (1, 0)

    samman = erbjudanden.sammanstall(
        await storage.erbjudande_utfall(TENANT),
        erbjudanden.normalisera({}),
        await storage.struktur_utfall(TENANT),
    )
    pilot = next(a for a in samman["armar"] if a["nyckel"] == "pilot")
    assert pilot["svarsfrekvens"] == 0.75 and pilot["kanske_andel"] == round(1 / 3, 4)
    assert pilot["klick_andel"] == 0.25 and pilot["besok_andel"] == 0.25
    assert [s["nyckel"] for s in samman["strukturer"]] == ["a", "b"]
    assert samman["struktur_ledare"] is None  # för få skickade

    besokare = await storage.demobesok(TENANT)
    assert {b["foretag"] for b in besokare} == {"Ja AB", "Tyst AB"}
    per = {b["foretag"]: b for b in besokare}
    assert per["Ja AB"]["besok"] == 1 and per["Ja AB"]["klick"] == 1
    assert per["Tyst AB"]["klick"] == 0 and per["Tyst AB"]["skanner_klick"] == 1
    assert await storage.demolank_totalt(TENANT) == {"lankar": 2, "klickade": 1, "besokta": 1}


@pytest.mark.anyio
async def test_aterkom_stoppar_kon_aviserar_och_sparar_klassen():
    from tests.leads.test_svar import TENANT as SVAR_TENANT, _kor, _tradd_med_skickat

    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, anrop, mejl = await _kor(storage, thread_id, "Inte just nu, hör av er i vår!", {
        "sa:call-summary": {"klass": "aterkom", "motivering": "Vill bli kontaktade i vår."},
    })
    assert resultat["klass"] == "aterkom"
    assert resultat["cancelled_sends"] == 1 and resultat["handoff"] is True
    assert anrop == ["sa:call-summary"]  # inget utkast skrivs
    assert mejl.await_count == 1
    thread = await storage.get_outreach_thread(SVAR_TENANT, thread_id)
    assert thread["svarsklass"] == "aterkom"


@pytest.mark.anyio
async def test_autosvar_skriver_ingen_svarsklass():
    from tests.leads.test_svar import TENANT as SVAR_TENANT, _kor, _tradd_med_skickat

    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    await _kor(storage, thread_id, "Jag är på semester.", {"sa:call-summary": {"klass": "autosvar"}})
    assert (await storage.get_outreach_thread(SVAR_TENANT, thread_id)).get("svarsklass") is None


def test_skannerns_user_agent_kanns_igen():
    assert demolank.ser_ut_som_skanner("")
    assert demolank.ser_ut_som_skanner("Mozilla/5.0 (compatible; Proofpoint URL Defense)")
    assert not demolank.ser_ut_som_skanner("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0")


def test_stilgrinden_raknar_demoraden_som_kodens_tillagg():
    """Demoraden får inte bli utkastets "sista mening": då tystnar kontrollen
    mot samma uppmaning i körningens andra mejl, och ordtaket räknar den."""
    from app.leads import stilkontroll

    utan = "Hej Anna,\n\nNi bygger hus åt föreningar.\n\nVill du veta mer bokar vi en genomgång."
    med = demolank.med_demolank(f"{utan}\n\nVänliga hälsningar,\nAnton", RAD_DU)
    assert RAD_DU in med
    assert stilkontroll.uppmaning(med) == stilkontroll.uppmaning(utan) != ""
    annat = "Hej Per,\n\nNi lägger golv åt fastighetsbolag.\n\nVill du veta mer bokar vi en genomgång."
    assert [a.kod for a in stilkontroll.mot_andra(annat, [med])] == ["samma_uppmaning"]
