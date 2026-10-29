"""Sebbes granskning av utskicken 2026-10-29 (docs/BESLUT.md).

1. Ämnesraden handlar om effektiviseringen: prospektering för Iris, support
   för Supportagenten, ur kundens egen lista per produkt (`amnen`), vald i
   kod och i mejlets tilltal.
2. Rabatten är "upp till 50 %": ett mejl som tappar "upp till" lovar mer än
   villkoren, och koden sätter tillbaka det.
3. Ingången klankar inte ner på bolaget ("Era kunder förväntar sig …") och
   frågar inte säljigt hur de ska hinna ("Hur ska ni kunna hantera …").
"""

import json
from collections import Counter
from unittest.mock import patch

import pytest

from app.agent.leads_research_v2 import run_outreach_draft_v2
from app.leads import erbjudanden
from app.leads import stilkontroll as stil
from app.storage.memory import MemoryStorage

LEADS = [
    "Effektivisering av prospektering",
    "Sluta leta efter kunder, låt dem hittas åt dig",
    "Din säljare ska sälja, inte googla bolag",
    "Hur hittar du dina nästa 50 kunder?",
]
SUPPORT = ["Support 24/7 för dina kunder", "Svar till dina kunder, även klockan 03:00"]
PILOT = (
    "Just nu tar vi in 20 företag i en kostnadsfri pilot av Iris i tre månader, med alla funktioner. "
    "Du får upp till 50 % rabatt om du stannar efteråt."
)


# -- 1. Ämnesraderna -------------------------------------------------------


def test_amnena_normaliseras_och_kravs_galla_en_produkt():
    val = erbjudanden.normalisera({"amnen": {"Iris": ["  Effektivisering  av prospektering ", "", "Effektivisering av prospektering"]}})
    assert val["amnen"] == {"Iris": ["Effektivisering av prospektering"]}
    # Utan ämnesrader är formen exakt som förut (inget amnen-fält).
    assert "amnen" not in erbjudanden.normalisera({})
    with pytest.raises(ValueError, match="Ämnesraderna"):
        erbjudanden.validera([], {}, ["Iris"], amnen={"Okänd": ["X"]})
    ok = erbjudanden.validera([], {}, ["Iris", "Supportagenten"], amnen={"iris": LEADS, "Supportagenten": SUPPORT})
    assert erbjudanden.amnen_for(ok["amnen"], "Iris") == LEADS
    assert erbjudanden.amnen_for(ok["amnen"], "supportagenten") == SUPPORT
    assert erbjudanden.amnen_for(ok["amnen"], "Kvittohanteraren") == []


def test_raden_valjs_deterministiskt_och_den_starkaste_oftast():
    valda = Counter(erbjudanden.valj_amne(LEADS, f"t:p-{i}", du=True) for i in range(900))
    assert set(valda) == set(LEADS)
    assert valda.most_common(1)[0][0] == LEADS[0]
    assert erbjudanden.valj_amne(LEADS, "t:p-1", du=True) == erbjudanden.valj_amne(LEADS, "t:p-1", du=True)
    assert erbjudanden.valj_amne([], "t:p-1", du=True) is None


def test_ni_form_utan_namngiven_mottagare():
    assert erbjudanden.till_ni("Support 24/7 för dina kunder") == "Support 24/7 för era kunder"
    assert erbjudanden.till_ni("Din säljare ska sälja, inte googla bolag") == "Er säljare ska sälja, inte googla bolag"
    assert erbjudanden.till_ni("Sluta leta efter kunder, låt dem hittas åt dig") == "Sluta leta efter kunder, låt dem hittas åt er"
    assert erbjudanden.till_ni("Nyanställd säljchef hos din målgrupp? Du vet det först") == (
        "Nyanställd säljchef hos er målgrupp? Ni vet det först"
    )
    assert erbjudanden.till_ni("Effektivisering av prospektering") == "Effektivisering av prospektering"


# -- 2. "Upp till 50 %" ------------------------------------------------------


@pytest.mark.parametrize(
    ("mejl", "vantat"),
    [
        ("Du som vill stanna efteråt får 50 % rabatt.", "Du som vill stanna efteråt får upp till 50 % rabatt."),
        ("Ni får 50% rabatt om ni stannar.", "Ni får upp till 50% rabatt om ni stannar."),
        ("Du får upp till 50 % rabatt om du stannar efteråt.", "Du får upp till 50 % rabatt om du stannar efteråt."),
        ("I tre månader, sedan 150 % mer.", "I tre månader, sedan 150 % mer."),
    ],
)
def test_upp_till_star_kvar(mejl, vantat):
    assert erbjudanden.behall_upp_till(mejl, PILOT) == vantat


def test_utan_upp_till_i_villkoren_rors_mejlet_inte():
    assert erbjudanden.behall_upp_till("Ni får 50 % rabatt.", "Pilot, sedan 50 % rabatt.") == "Ni får 50 % rabatt."


# -- 3. Ingången -------------------------------------------------------------

PRODUKT = "Vår agent Iris hittar nya företagskunder åt dig."
AVSLUT = "Vill du veta mer finns en demo på snajp.se/demo, eller så svarar du på mejlet och vi bokar en genomgång."


def _koder(ingang: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(f"Hej,\n\n{ingang}\n\n{PRODUKT}\n\n{AVSLUT}").anmarkningar}


@pytest.mark.parametrize(
    "ingang",
    [
        "Era kunder förväntar sig snabb och kunnig hjälp med tyger och sybehör, både online och i butiken.",
        "Hur ska ni kunna hantera nya kunder samtidigt som ni har mycket jobb?",
        "Ni hjälper företag med tyger. När mängden frågor växer tar det tid från mer komplexa ärenden.",
    ],
)
def test_sebbes_daliga_ingangar_falls(ingang):
    assert "kritisk_ingang" in _koder(ingang)


def test_sebbes_goda_ingang_passerar():
    ingang = "Att identifiera potentiella köpare och bistå i förhandlingar kräver att du kan fokusera på varje affär."
    assert "kritisk_ingang" not in _koder(ingang)


# -- Hela kedjan: ämnesraden i kön -----------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_kon_far_amnesraden_ur_listan_for_vald_produkt(monkeypatch):
    from app.config import get_settings
    from tests.agent.test_leads_v2_wiring import TENANT, _FakeLLM, _prepare_outreach

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    storage = MemoryStorage()
    thread_id = await _prepare_outreach(storage)
    await storage.set_agent_settings(
        TENANT,
        agent_type="leads",
        settings={
            "erbjudanden": {
                "aktiva": [{"nyckel": "pilot", "vikt": 1}],
                "villkor": {"pilot": {"Supportagenten": PILOT.replace("Iris", "Supportagenten")}},
                "amnen": {"Iris": LEADS, "Supportagenten": SUPPORT},
            }
        },
    )
    with patch("app.agent.step_runner.get_llm_client", return_value=_FakeLLM()):
        result = await run_outreach_draft_v2(
            storage,
            TENANT,
            thread_id=thread_id,
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Supportagenten: svarar på kundmejlen",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            research_summary=json.dumps({"vald_produkt": {"namn": "Supportagenten", "nytta": "svar"}}),
            research_evidence=("Fri retur inom 30 dagar",),
            is_test=True,
        )
    get_settings.cache_clear()
    assert result["queued"] is True
    # Ingen namngiven mottagare: ni-form, och aldrig en Iris-rad i ett supportmejl.
    assert result["subject"] in {erbjudanden.till_ni(r) for r in SUPPORT}
    assert result["subject"] != "Returfrågor"


@pytest.mark.parametrize(
    ("mening", "falls"),
    [
        ("Iris effektiviserar prospekteringen åt dig.", False),
        ("Den effektiviserar er kundhantering, dygnet runt.", False),
        ("Det hjälper er att effektivisera arbetet.", True),
        ("Ni får högre effektivitet.", True),
    ],
)
def test_effektiviserar_ar_tillatet_om_prospekteringen_eller_kundhanteringen(mening, falls):
    koder = {a.kod for a in stil.kontrollera(f"Hej,\n\n{mening}").anmarkningar}
    assert ("effektivisera" in koder) is falls


# -- Ordningen: nyaste utkastet först ----------------------------------------


@pytest.mark.anyio
async def test_granskningskon_kommer_nyaste_utkastet_forst():
    """Sebbe 2026-10-29: de äldsta kom först och gränsen klippte bort en ny
    körnings utkast, som då bara syntes under Körningar."""
    from datetime import UTC, datetime, timedelta

    storage = MemoryStorage()
    t0 = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
    for i, namn in enumerate(["Äldst", "Mitten", "Nyast"]):
        prospekt = await storage.create_prospect("t", company_name=namn)
        trad = await storage.ensure_outreach_thread("t", prospect_id=prospekt["id"])
        svar = await storage.queue_outreach_message(
            "t", thread_id=trad["id"], subject="Ämne", body=f"Hej {namn}", humanizer_variant="v",
            # Det äldsta utkastet har den senaste sändtiden: ordningen följer
            # när utkastet skrevs, inte när det ska gå ut.
            scheduled_at=(t0 - timedelta(hours=i)).isoformat(), status="awaiting_review",
        )
        svar["message"]["created_at"] = (t0 + timedelta(minutes=i)).isoformat()
    ko = await storage.list_review_queue("t", limit=2)
    assert [r["company_name"] for r in ko] == ["Nyast", "Mitten"]


@pytest.mark.anyio
async def test_inkorgen_har_det_senaste_svaret_overst():
    """Sebbe 2026-10-29: "det senaste svaret vi fått in ska vara högst upp".
    Inkorgen var redan sorterad så (received_at desc); testet låser det."""
    storage = MemoryStorage()
    for i, tid in enumerate(["2026-10-27T09:00:00+00:00", "2026-10-29T07:30:00+00:00", "2026-10-28T12:00:00+00:00"]):
        await storage.save_email(
            "t", provider="imap", provider_message_id=f"m-{i}", from_email=f"vd{i}@bolag.se",
            from_name=None, subject=f"Sv: {tid[:10]}", body_text="Låter intressant.", received_at=tid,
        )
    rader = await storage.list_emails("t")
    assert [r["subject"] for r in rader] == ["Sv: 2026-10-29", "Sv: 2026-10-28", "Sv: 2026-10-27"]


# -- Frågans moment i form B följer produkten ----------------------------------


def test_fragan_i_form_b_bar_bara_den_valda_produktens_moment():
    """Omskrivningen 2026-10-29: ett supportmejl frågade "… eller att hitta nya
    kunder?" och lovade att Supportagenten tog hand om båda delarna."""
    eget = erbjudanden.Erbjudande(nyckel="pilot_b", namn="Piloten B", regler="", form="fraga")
    support = erbjudanden.block("pilot_b", PILOT, eget, "Supportagenten")
    iris = erbjudanden.block("pilot_b", PILOT, eget, "Iris, leadsagenten")
    okand = erbjudanden.block("pilot_b", PILOT, eget, "Takläggning")
    assert "supportchattarna" in support and "att hitta nya kunder, inga" not in support
    assert "hitta nya kunder" in iris and "supportchattarna" not in iris
    assert "för en leadsagent" in okand and "för en supportagent" in okand
    assert "{moment}" not in support + iris + okand


@pytest.mark.parametrize(
    ("produkt", "text", "falls"),
    [
        ("Supportagenten", "Hej,\n\nTar det mest tid att hantera förfrågningarna eller att hitta nya kunder?\n\n"
         "Vår Supportagent tar hand om båda delarna.", True),
        ("Supportagenten", "Hej,\n\nTar det mest tid att gå igenom kundmejlen eller att sitta i supportchattarna?\n\n"
         "Vår Supportagent tar hand om båda delarna.", False),
        ("Iris, leadsagenten", "Hej,\n\nTar det mest tid att sitta i supportchattarna eller att hitta nya kunder?\n\n"
         "Vår agent Iris tar hand om båda delarna.", True),
        ("Iris, leadsagenten", "Hej,\n\nTar det mest tid att hantera förfrågningarna eller att hitta nya kunder?\n\n"
         "Vår agent Iris tar hand om båda delarna.", False),
    ],
)
def test_fel_produkts_moment_falls(produkt, text, falls):
    koder = {a.kod for a in stil.erbjudande_fynd(text, villkor=None, produkt=produkt)}
    assert ("fel_moment" in koder) is falls


@pytest.mark.parametrize(
    ("avslut", "falls"),
    [
        ("Vill ni testa Iris direkt i demon på snajp.se/demo, eller svara på mejlet så bokar vi en genomgång.", True),
        ("Vill du testa Iris direkt i demon på snajp.se/demo, eller svara på mejlet så bokar vi en genomgång.", True),
        ("Vill du veta mer eller testa själv kan du titta på demon på snajp.se/demo, eller svara på det här mejlet "
         "så bokar vi en kostnadsfri genomgång.", False),
        ("Vill ni testa själva finns demon på snajp.se/demo, eller så svarar ni på mejlet och vi bokar en genomgång.", False),
    ],
)
def test_halv_inbjudan_falls(avslut, falls):
    """Omskrivningen 2026-10-29: "Vill ni testa …, eller svara …" är en halv mening."""
    koder = {a.kod for a in stil.kontrollera(f"Hej,\n\n{PRODUKT}\n\n{avslut}").anmarkningar}
    assert ("halv_inbjudan" in koder) is falls
