"""Struktur B: det korta utskicket (Sebbe 2026-11-05, app/leads/utkaststruktur.py).

Sebbes krav, som rutin för varje B-utskick:

1. Utgår från förebilderna, för Iris och för Supportagenten.
2. Samma signatur, logga, disclaimer (lagstadgad fot), typsnitt och färg som
   A: B köas genom exakt samma väg, och svansen efter brödtexten är
   byte-identisk med A:s för samma kund och mottagare.
3. Lika anpassat till mottagaren: researchen och tilltalet följer med.
4. Samma administrativa funktioner: granskningskön, Skapa om utkast (som
   behåller B), godkänn och skicka.
5. A är oförändrad.
"""

import json
from unittest.mock import patch

import pytest

from app.agent.leads_research_v2 import run_outreach_draft_v2
from app.api.schemas import LeadsBatchRequest
from app.leads import erbjudanden, utkaststruktur
from app.leads import stilkontroll as stil
from app.leads.signatur import bygg_html, dela_utkast, normalisera
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"
SIG = {
    "namn": "Sebastian Bergman",
    "titel": "Snajp Support | AI för leads och kundtjänst",
    "telefon": "+46 70 360 05 64",
    "epost": "snajpsupport@gmail.com",
    "ort": "Umeå & Göteborg",
    "webb": "www.snajp.se",
    "bolag": "Snajp AB",
    "logotyp_url": "https://web.example/epost/snajp-logga.png",
}
IRIS = "Iris, leadsagenten"
SUPPORT = "Supportagenten"
UTFALL_IRIS = "40–50 nya företag i veckan som passar er, med ett färdigt första mejl till varje"


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- valet -------------------------------------------------------------------


@pytest.mark.parametrize(("varde", "vantat"), [(None, "a"), ("", "a"), ("A", "a"), ("x", "a"), ("b", "b"), ("B", "b")])
def test_okant_varde_ar_a(varde, vantat):
    assert utkaststruktur.normalisera(varde) == vantat


def test_batchen_tar_emot_strukturen_och_a_ar_standard():
    assert LeadsBatchRequest().struktur == "a"
    assert LeadsBatchRequest(struktur="b").struktur == "b"
    with pytest.raises(ValueError):
        LeadsBatchRequest(struktur="c")


def test_processa_om_utan_val_behaller_forra_strukturen():
    """Skapa om utkast utan val = None, som jobbet läser som leadets förra
    struktur (utkaststruktur.tidigare); ett uttryckligt val gäller."""
    from app.api.schemas import ProcessaOmRequest

    assert ProcessaOmRequest(prospect_ids=["x"], scope="utkast").struktur is None
    assert ProcessaOmRequest(prospect_ids=["x"], scope="utkast", struktur="b").struktur == "b"


def test_varianterna_ar_deterministiska_och_ungefar_rätt_andel():
    erb = [utkaststruktur.med_erbjudande(TENANT, f"p-{i}") for i in range(900)]
    ing = [utkaststruktur.med_ingang(TENANT, f"p-{i}") for i in range(900)]
    assert 0.25 < sum(erb) / 900 < 0.42
    assert 0.40 < sum(ing) / 900 < 0.60
    assert utkaststruktur.med_erbjudande(TENANT, "p-1") == utkaststruktur.med_erbjudande(TENANT, "p-1")


# -- förebilderna ---------------------------------------------------------------


def test_blocket_bar_forebilderna_for_ratt_agent():
    iris = utkaststruktur.block(produkt=IRIS, nytta="hittar kunder", utfall=UTFALL_IRIS, villkor=None, ingang=False)
    sup = utkaststruktur.block(produkt=SUPPORT, nytta="svarar", utfall="", villkor=None, ingang=True)
    assert all(e in iris for e in utkaststruktur.FOREBILDER["leads"])
    assert not any(e in iris for e in utkaststruktur.FOREBILDER["support"])
    assert all(e in sup for e in utkaststruktur.FOREBILDER["support"])
    assert UTFALL_IRIS in iris
    # Utan kort utfall bygger frågan på nyttan.
    assert "svarar" in sup
    # Utan erbjudande: inget villkorsblock, och uttryckligen ingen pilot.
    assert "Villkor för erbjudandet" not in iris and "ingen pilot" in iris
    # En annan kunds produkt får formreglerna men inga Snajp-förebilder.
    annan = utkaststruktur.block(produkt="Takläggning", nytta="tak", utfall="", villkor=None, ingang=False)
    assert "Förebilder" not in annan and "Mejlets struktur: B" in annan


def test_med_erbjudandet_star_villkoren_i_blocket():
    blocket = utkaststruktur.block(produkt=IRIS, nytta="x", utfall="", villkor="Pilot i tre månader.", ingang=False)
    assert "### Villkor för erbjudandet\nPilot i tre månader." in blocket
    assert "ingen pilot" not in blocket


@pytest.mark.parametrize(
    ("produkt", "brodtext"),
    [(IRIS, e) for e in utkaststruktur.FOREBILDER["leads"]]
    + [(SUPPORT, e) for e in utkaststruktur.FOREBILDER["support"]],
)
def test_forebilderna_passerar_b_grinden(produkt, brodtext):
    """Förebilderna är nivån: grinden får inte fälla dem, annars skrivs varje
    B-mejl om bort från dem."""
    mejl = f"Hej,\n\n{brodtext}"
    # Förebilden med piloten prövas mot villkoren, som mejlen med erbjudandet.
    villkor = "Just nu tar vi in 20 företag i en kostnadsfri pilot." if "pilot" in brodtext else None
    fynd = stil.kontrollera(mejl, struktur="b").anmarkningar + stil.erbjudande_fynd(
        mejl, villkor=villkor, produkt=produkt
    )
    assert [a.kod for a in fynd] == []


def test_b_slutar_med_fragan_och_a_gor_det_aldrig():
    fraga = "Hej,\n\nOm vår agent Iris kunde ta fram nya företag åt er, skulle det vara till nytta?"
    inbjudan = "Hej,\n\nVår agent Iris tar fram nya företag åt er. Titta gärna på demon."
    assert "slutar_med_fraga" in [a.kod for a in stil.kontrollera(fraga).anmarkningar]
    assert "slutar_med_fraga" not in [a.kod for a in stil.kontrollera(fraga, struktur="b").anmarkningar]
    assert "b_utan_fraga" in [a.kod for a in stil.kontrollera(inbjudan, struktur="b").anmarkningar]


def test_b_har_eget_ordtak():
    lang = "Hej,\n\n" + "Vår agent Iris hjälper er. " * 14 + "Skulle det vara till nytta?"
    assert "for_langt" in [a.kod for a in stil.kontrollera(lang, struktur="b").anmarkningar]


def test_b_mejlens_gemensamma_fraga_falls_inte_mot_varandra():
    ett = "Hej,\n\nOm vår agent Iris kunde ta fram 40–50 nya företag i veckan som passar er, skulle det hjälpa?"
    tva = "Hej,\n\nOm vår agent Iris kunde ta fram 40–50 nya byggföretag i veckan som passar er, skulle det vara användbart?"
    assert stil.mot_andra(tva, [ett], struktur="b") == []
    # Ordagrant samma ingång fälls fortfarande.
    assert [a.kod for a in stil.mot_andra(ett, [ett], struktur="b")] == ["samma_ingang"]


# -- kundens korta utfall -------------------------------------------------------


def test_kort_utfall_normaliseras_och_kravs_galla_en_produkt():
    val = erbjudanden.validera([], {}, [IRIS, SUPPORT], kort_utfall={"iris, leadsagenten": f"  {UTFALL_IRIS} "})
    assert erbjudanden.kort_utfall_for(val, IRIS) == UTFALL_IRIS
    assert erbjudanden.kort_utfall_for(val, SUPPORT) == ""
    assert "kort_utfall" not in erbjudanden.normalisera({})
    with pytest.raises(ValueError, match="korta utfallet"):
        erbjudanden.validera([], {}, [IRIS], kort_utfall={"Okänd": "x"})


# -- hela kedjan: B går samma väg som A -------------------------------------------

B_SVAR = (
    "Hej,\n\nNi bygger åt bostadsrättsföreningar. Om vår agent Iris kunde ta fram 40–50 nya "
    "företag i veckan som passar er, skulle det vara till nytta?"
)


async def _forbered(storage: MemoryStorage) -> tuple[str, str]:
    from tests.agent.test_leads_v2_wiring import _prepare_outreach

    thread_id = await _prepare_outreach(storage)
    thread = await storage.get_outreach_thread(TENANT, thread_id)
    storage.tenants[TENANT] = {
        **(storage.tenants.get(TENANT) or {}),
        "id": TENANT,
        "name": "Snajp",
        "company_name": "Snajp AB",
        "orgnr": "559000-0000",
        "postal_address": "Storgatan 1, 903 26 Umeå",
        "policy_url": "https://snajp.test/integritet",
    }
    await storage.set_agent_settings(
        TENANT,
        agent_type="leads",
        settings={
            "signatur": dict(SIG),
            "produkter": [{"namn": IRIS, "nytta": "hittar och kvalificerar nya företagskunder"}],
            "erbjudanden": {
                "aktiva": [{"nyckel": "pilot", "vikt": 1}],
                "villkor": {"pilot": {IRIS: "Just nu tar vi in 20 företag i en kostnadsfri pilot av Iris."}},
                "amnen": {IRIS: ["Effektivisering av prospektering"]},
                "kort_utfall": {IRIS: UTFALL_IRIS},
            },
        },
    )
    return thread_id, str(thread["prospect_id"])


async def _skriv(storage, thread_id: str, llm, struktur: str) -> dict:
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        return await run_outreach_draft_v2(
            storage,
            TENANT,
            thread_id=thread_id,
            prospect_email="info@vindshembygg.se",
            tenant_name="Snajp",
            company_name="Vindshem Bygg AB",
            offer_summary=f"{IRIS}: hittar och kvalificerar nya företagskunder",
            context_pack="## Kontextpaket\nICP: byggbolag.",
            brief="",
            research_summary=json.dumps(
                {"vald_produkt": {"namn": IRIS, "nytta": "hittar kunder"}, "citat": ["Vi bygger åt bostadsrättsföreningar"]}
            ),
            research_evidence=("Vi bygger åt bostadsrättsföreningar",),
            is_test=True,
            struktur=struktur,
        )


@pytest.fixture
def miljo(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    monkeypatch.setattr(get_settings(), "publik_bas_url", "https://snajp.test")
    yield
    get_settings.cache_clear()


B_SVAR_PILOT = (
    "Hej,\n\nVår agent Iris hittar nya företagskunder åt er. Just nu tar vi in 20 företag i en "
    "kostnadsfri pilot. Om Iris kunde ta fram 40–50 nya företag i veckan som passar er, vore det intressant?"
)


def _b_llm(prospekt: str):
    """Modellens svar följer mejlets variant, som en riktig modell gör när
    blocket säger det: med erbjudandet i ungefär vart tredje B-mejl."""
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    svar = B_SVAR_PILOT if utkaststruktur.med_erbjudande(TENANT, prospekt) else B_SVAR
    return _FakeLLM(
        {
            "sa:draft-outreach": {"subject": "Nya kunder", "body": svar},
            "snajp:humanizer-svenska": {"final_subject": "Nya kunder", "final_body": svar},
        }
    )


@pytest.fixture(params=[False, True], ids=["utan_erbjudande", "med_erbjudande"])
def variant(request, monkeypatch):
    """Båda B-varianterna i varje körning, inte bara den slumpade prospekt-id:t ger."""
    monkeypatch.setattr(utkaststruktur, "med_erbjudande", lambda *_a: request.param)
    return request.param


@pytest.mark.anyio
async def test_b_koas_med_samma_signatur_logga_och_fot_som_a(miljo, variant):
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    storage_a, storage_b = MemoryStorage(), MemoryStorage()
    trad_a, _ = await _forbered(storage_a)
    trad_b, prospekt_b = await _forbered(storage_b)

    a = await _skriv(storage_a, trad_a, _FakeLLM(), "a")
    llm_b = _b_llm(prospekt_b)
    b = await _skriv(storage_b, trad_b, llm_b, "b")
    assert a["queued"] and b["queued"], (a.get("escalation_reason"), b.get("escalation_reason"))

    kropp_a = storage_a.outreach_messages[TENANT][0]["body"]
    kropp_b = storage_b.outreach_messages[TENANT][0]["body"]
    brod_a, svans_a = dela_utkast(kropp_a, SIG)
    brod_b, svans_b = dela_utkast(kropp_b, SIG)
    # Signaturen och disclaimern: byte-identiska, bara avregistreringstoken
    # är per lagring (samma mottagare, olika MemoryStorage).
    import re

    def utan_token(s: str) -> str:
        return re.sub(r"avregistrera/[\w-]+", "avregistrera/X", s)

    assert utan_token(svans_a) == utan_token(svans_b)
    assert "Sebastian Bergman" in svans_b and "Snajp AB" in svans_b and "559000-0000" in svans_b
    assert "snajp.test" in svans_b
    # Brödtexten är B: frågan sist.
    # Hälsningsfrasen före signaturen läggs på i kod, som i A.
    fraga = brod_b.rstrip().removesuffix("Vänliga hälsningar,").rstrip()
    assert fraga.endswith("?") and "Iris" in fraga
    assert brod_a != brod_b

    # Typsnitt, färg och loggan: samma HTML-rendering för båda.
    sig = normalisera(SIG)
    html_a, html_b = bygg_html(kropp_a, sig), bygg_html(kropp_b, sig)
    assert SIG["logotyp_url"] in html_b
    stil_a = re.findall(r'style="[^"]*"', html_a)
    stil_b = re.findall(r'style="[^"]*"', html_b)
    assert set(stil_b) <= set(stil_a) | set(stil_b) and stil_b, "B saknar stilsättning"
    assert sorted(set(stil_a)) == sorted(set(stil_b))


@pytest.mark.anyio
async def test_b_prompten_bar_strukturen_forebilderna_och_mottagarens_research(miljo, variant):
    storage = MemoryStorage()
    trad, prospekt = await _forbered(storage)
    llm = _b_llm(prospekt)
    resultat = await _skriv(storage, trad, llm, "b")
    assert resultat["queued"]
    utkast = [m for s, m in zip(llm.calls, llm.user_messages) if s == "sa:draft-outreach"]
    assert utkast, llm.calls
    forsta = utkast[0]
    assert "Mejlets struktur: B" in forsta
    assert utkaststruktur.FOREBILDER["leads"][0] in forsta
    assert UTFALL_IRIS in forsta
    # Anpassat till mottagaren: researchen och tilltalet följer med som i A.
    assert "bostadsrättsföreningar" in forsta and "Tilltal i det här mejlet" in forsta
    # A:s form och ingångsform står inte i B.
    assert "### Mejlets form (" not in forsta
    assert "## Ingångens form i det här mejlet\n" not in forsta
    # Erbjudandet (piloten) bara i varianten med det.
    assert ("### Villkor för erbjudandet" in forsta) is variant
    # Personaliseringen av ingången (A:s extra anrop) körs inte, och ett
    # mejl på förebildernas nivå skrivs inte om: ett utkast + en humanizer.
    assert llm.calls.count("sa:draft-outreach") == 1


@pytest.mark.anyio
async def test_a_ar_oforandrad_utan_strukturval(miljo):
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    storage = MemoryStorage()
    trad, _ = await _forbered(storage)
    llm = _FakeLLM()
    await _skriv(storage, trad, llm, "a")
    forsta = next(m for s, m in zip(llm.calls, llm.user_messages) if s == "sa:draft-outreach")
    assert "Mejlets struktur: B" not in forsta and "Förebilder" not in forsta


@pytest.mark.anyio
async def test_skapa_om_utkast_behaller_strukturen(miljo):
    storage = MemoryStorage()
    trad, prospekt = await _forbered(storage)
    assert await utkaststruktur.tidigare(storage, TENANT, prospekt) == "a"
    await _skriv(storage, trad, _b_llm(prospekt), "b")
    assert await utkaststruktur.tidigare(storage, TENANT, prospekt) == "b"


@pytest.mark.anyio
async def test_b_koposten_flaggas_inte_for_sin_fraga(miljo):
    """Köningens stilkontroll prövar B mot B:s regler: annars tvingades varje
    B-mejl till granskning med "slutar med en fråga"."""
    storage = MemoryStorage()
    trad, prospekt = await _forbered(storage)
    await _skriv(storage, trad, _b_llm(prospekt), "b")
    post = storage.send_queue[TENANT][0]
    assert "slutar med en fråga" not in json.dumps(post, ensure_ascii=False, default=str)
