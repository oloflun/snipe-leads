"""Hälsningsraden och namnvettet (app/leads/halsning.py, Sebbe 2026-10-11).

Varje fall nedan är hämtat ur development samma dag: "Kontaktpersoner Lahoud"
som nådde ett skickat mejl, "Verkstad Öppettider" och "Umeå Börje" som
kontakter i kön, utkast utan hälsningsrad, och versalnamn ur registret.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads.halsning import (
    normalisera_utkast,
    rensa_personnamn,
    sakra_halsning,
    snyggt_bolagsnamn,
)
from app.main import app
from app.textkvalitet import kontrollera

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
SIG = {"namn": "Sebastian Bergman", "titel": "Snajp Support", "bolag": "Snajp AB"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Namnvettet ----------------------------------------------------------------


def test_rensa_personnamn_stryker_rubrikord_och_orter():
    assert rensa_personnamn("Kontaktpersoner Lahoud") == "Lahoud"
    assert rensa_personnamn("Umeå Börje") == "Börje"
    assert rensa_personnamn("Verkstad Öppettider") is None
    assert rensa_personnamn("PETER SJÖLIN") == "Peter Sjölin"
    assert rensa_personnamn("Hans-Eric Jacobsson") == "Hans-Eric Jacobsson"
    assert rensa_personnamn("info@bolaget.se") is None
    assert rensa_personnamn(None) is None


def test_snyggt_bolagsnamn_tar_bort_bolagsform_och_rattar_versaler():
    assert snyggt_bolagsnamn("Stöcke Svets Aktiebolag") == "Stöcke Svets"
    assert snyggt_bolagsnamn("AB Consenso") == "Consenso"
    assert snyggt_bolagsnamn("HORTLAX RÖR AB") == "Hortlax Rör"
    assert snyggt_bolagsnamn("HÄRLANDA FOG & BYGGSERVICE AB") == "Härlanda Fog & Byggservice"
    # Ett ensamt versalord kan vara en initialism och lämnas.
    assert snyggt_bolagsnamn("FOPTEC AB") == "FOPTEC"


def test_snyggt_bolagsnamn_tar_bort_ortsled_men_inte_varumarken():
    """Kort form utan ortsled (Sebbe 2026-10-12): "Hej B Flemströms Gräv &
    Last," — inte "… i Luleå,". Bara kommuner vi känner är ortsled;
    väderstreck är varumärke."""
    assert snyggt_bolagsnamn("B Flemströms Gräv & Last i Luleå AB") == "B Flemströms Gräv & Last"
    assert snyggt_bolagsnamn("Nyströms Byggtjänst i Piteå AB") == "Nyströms Byggtjänst"
    assert snyggt_bolagsnamn("Simmis i Göteborg AB") == "Simmis"
    assert snyggt_bolagsnamn("ByggMix i Norr AB") == "ByggMix i Norr"
    assert snyggt_bolagsnamn("Markskydd i Väst AB") == "Markskydd i Väst"


# -- Hälsningsraden ------------------------------------------------------------


def test_utkast_utan_halsning_far_personens_fornamn():
    text = normalisera_utkast(
        "När man driver ett byggföretag vill du växa.", kontakt="PETER SJÖLIN", bolag="X AB"
    )
    assert text.startswith("Hej Peter,\n\n")
    # Namngiven person tilltalas med du — formen rörs inte.
    assert "vill du växa" in text


def test_utkast_utan_halsning_och_utan_person_far_bara_hej_och_ni():
    """Bolagsnamnet skrivs ALDRIG efter "Hej" (Sebbe 2026-10-12): utan en
    namngiven person är hälsningen exakt "Hej," och mejlet säger ni."""
    text = normalisera_utkast(
        "När man driver ett byggföretag vill du växa. Din tid är dyrbar.",
        kontakt="Verkstad Öppettider",
        bolag="HORTLAX RÖR AB",
    )
    assert text.startswith("Hej,\n\n")
    assert "vill ni växa" in text and "Er tid" in text


def test_bolagsnamn_efter_hej_ersatts_aven_nar_det_liknar_ett_personnamn():
    """"Hej Briell Bygg," ser ut som ett personnamn för namnvettet — det är
    bolagsjämförelsen som ska fälla det, i kort- och långform."""
    for halsning in ("Hej Briell Bygg,", "Hej Briell Bygg AB,"):
        text = normalisera_utkast(f"{halsning}\n\nVi hörs du.", kontakt=None, bolag="Briell Bygg AB")
        assert text.startswith("Hej,\n\n"), halsning
    # Äldre köad hälsning med ortsled känns också igen mot kortformen.
    text = normalisera_utkast(
        "Hej B Flemströms Gräv & Last i Luleå,\n\nVi hörs.",
        kontakt=None,
        bolag="B Flemströms Gräv & Last i Luleå AB",
    )
    assert text.startswith("Hej,\n\n")


def test_ogiltig_halsning_ersatts_och_giltig_lamnas():
    assert normalisera_utkast("Hej Verkstad,\n\nVi hörs.", kontakt=None, bolag="Granec Maskin Aktiebolag").startswith(
        "Hej,\n"
    )
    assert normalisera_utkast("Hej Elin!\n\nVi hörs.", kontakt="Elin Ek", bolag="X AB").startswith("Hej Elin!")
    assert normalisera_utkast("Hej igen,\n\nVi hörs.", kontakt=None, bolag="X AB").startswith("Hej igen,")
    assert normalisera_utkast("Hej där,\n\nVi hörs.", kontakt=None, bolag=None).startswith("Hej,\n")


def test_passet_ar_idempotent():
    forsta = normalisera_utkast("Vi hjälper dig.", kontakt=None, bolag="Svartöns Bygg AB")
    assert forsta.startswith("Hej,\n\n")
    assert normalisera_utkast(forsta, kontakt=None, bolag="Svartöns Bygg AB") == forsta


def test_engelsk_halsning():
    text = sakra_halsning("We can help.", kontakt="URBAN SUNDBERG", bolag=None, sprak="en")
    assert text.startswith("Hi Urban,")
    assert sakra_halsning("Dear Sir,\n\nWe help.", kontakt=None, bolag=None, sprak="en").startswith("Hello,")


# -- Grinden i textkvaliteten ---------------------------------------------------


def test_opersonligt_tilltal_ar_en_allvarlig_anmarkning():
    fynd = kontrollera("Hej kontaktpersoner,\n\nVi hjälper er.").allvarliga
    assert any(a.kod == "fel_tilltal" for a in fynd)
    # Längre ned i texten är ordet legitim sakprosa.
    ok = kontrollera("Hej Peter,\n\nVi hjälper er.\n\nTack.\n\nAnge en kontaktperson i formuläret.")
    assert not any(a.kod == "fel_tilltal" for a in ok.allvarliga)


# -- Lata fixen i granskningskön -------------------------------------------------


async def _koa_gammalt_utkast(storage) -> str:
    """Ett utkast som det såg ut FÖRE hälsningspasset och signaturen: ingen
    hälsningsrad, inget signaturblock."""
    storage.agent_settings[(DEFAULT_TENANT_ID, "leads")] = {"signatur": dict(SIG)}
    prospekt = await storage.create_prospect(
        DEFAULT_TENANT_ID,
        company_name="HORTLAX RÖR AB",
        contact_name="Kontaktpersoner Lahoud",
        contact_email="info@hortlaxror.se",
    )
    trad = await storage.ensure_outreach_thread(DEFAULT_TENANT_ID, prospect_id=prospekt["id"])
    ko = await storage.queue_outreach_message(
        DEFAULT_TENANT_ID,
        thread_id=trad["id"],
        subject="Kundfrågor",
        body="När man driver ett VVS-företag som ert blir du lätt avbruten.",
        humanizer_variant="x",
        scheduled_at="2026-10-07T08:00:00+00:00",
        status="awaiting_review",
    )
    return ko["queue_item"]["id"]


@pytest.mark.anyio
async def test_kon_rattar_gamla_utkast_vid_lasning():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        item_id = await _koa_gammalt_utkast(storage)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = (await client.get("/api/leads/queue", headers=DEMO)).json()
            post = next(i for i in svar["items"] if i["id"] == item_id)
        # Hälsningen: kontakten "Kontaktpersoner Lahoud" rensas till Lahoud.
        assert post["brodtext"].startswith("Hej Lahoud,\n\n")
        # Signaturen lades på och visas i svansen.
        assert post["svans"].startswith("Sebastian Bergman")
        # Det LAGRADE utkastet rättades — granskningstexten är utskickstexten.
        lagrat = storage.outreach_messages[DEFAULT_TENANT_ID][-1]["body"]
        assert lagrat.startswith("Hej Lahoud,") and "Sebastian Bergman" in lagrat
        # En andra läsning ändrar ingenting: fixen är idempotent, annars
        # hade varje öppning av kön skrivit en ny rad.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            (await client.get("/api/leads/queue", headers=DEMO)).json()
        assert storage.outreach_messages[DEFAULT_TENANT_ID][-1]["body"] == lagrat


@pytest.mark.anyio
async def test_put_lagger_tillbaka_signaturen_aven_nar_utkastet_saknade_den():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        item_id = await _koa_gammalt_utkast(storage)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Omskrivning sparas UTAN att kön lästs först: det lagrade
            # utkastet saknar signatur, och svansen är tom. Signaturen ska
            # ändå med — det var buggen med Förbättra-knapparna.
            r = await client.put(
                f"/api/leads/queue/{item_id}",
                headers=DEMO,
                json={"subject": "Kundfrågor", "brodtext": "Hej Lahoud,\n\nKort fråga om era kundmejl."},
            )
            assert r.status_code == 200
        lagrat = storage.outreach_messages[DEFAULT_TENANT_ID][-1]["body"]
        assert "Sebastian Bergman" in lagrat
        assert lagrat.count("Sebastian Bergman") == 1
