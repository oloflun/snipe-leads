"""Mejlsignaturen (app/leads/signatur.py): textblocket som köas och granskas,
HTML-renderingen med logotypen, och köningsvägen som lägger på den."""

import pytest

from app.agent.leads_context import OutreachContext
from app.agent.leads_tools import _queue_outreach_draft_impl
from app.leads.signatur import (
    bygg_html,
    bygg_signaturtext,
    dela_utkast,
    med_signatur,
    normalisera,
    sla_ihop,
)
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


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- normalisera ------------------------------------------------------------


def test_normalisera_slappar_igenom_komplett_signatur():
    sig = normalisera(SIG)
    assert sig is not None
    assert sig["namn"] == "Sebastian Bergman"
    assert sig["logotyp_url"] == SIG["logotyp_url"]


@pytest.mark.parametrize(
    "val",
    [
        None,
        "en sträng",
        {},
        {"titel": "Utan namn"},
        {**SIG, "aktiv": False},
    ],
)
def test_normalisera_ger_none_utan_anvandbar_signatur(val):
    assert normalisera(val) is None


def test_normalisera_tappar_logotyp_som_inte_ar_https():
    sig = normalisera({**SIG, "logotyp_url": "http://web.example/logga.png"})
    assert sig is not None
    assert "logotyp_url" not in sig


def test_normalisera_sanerar_radbrytningar_i_falt():
    # En radbrytning i ett fält hade förskjutit blocket bygg_html letar efter.
    sig = normalisera({**SIG, "titel": "Rad ett\nRad två"})
    assert sig["titel"] == "Rad ett Rad två"


# -- textblocket ------------------------------------------------------------


def test_bygg_signaturtext_tre_grupper_med_blankrad():
    assert bygg_signaturtext(normalisera(SIG)) == (
        "Sebastian Bergman\n"
        "Snajp Support | AI för leads och kundtjänst\n"
        "+46 70 360 05 64\n"
        "snajpsupport@gmail.com\n"
        "\n"
        "Umeå & Göteborg\n"
        "www.snajp.se\n"
        "\n"
        "Snajp AB"
    )


def test_med_signatur_laggs_pa_efter_blankrad_och_ar_idempotent():
    sig = normalisera(SIG)
    en_gang = med_signatur("Hej!\nEn idé till er.", sig)
    assert en_gang.endswith("En idé till er.\n\n" + bygg_signaturtext(sig))
    assert med_signatur(en_gang, sig) == en_gang


def test_med_signatur_fullbordar_hangande_halsningsfras():
    # Samma defekt som leads_agent.sign_off lagar: "Med vänliga hälsningar,"
    # utan namn. Signaturens namnrad ska stå DIREKT under frasen.
    resultat = med_signatur("Hej!\n\nMed vänliga hälsningar,", normalisera(SIG))
    assert "Med vänliga hälsningar,\nSebastian Bergman\n" in resultat


def test_med_signatur_ersatter_ensam_namnrad():
    # sign_off kan redan ha satt dit ett namn — det ska inte stå kvar två
    # rader ovanför signaturens egen namnrad.
    resultat = med_signatur("Hej!\n\nMed vänliga hälsningar,\nSebastian", normalisera(SIG))
    assert resultat.count("Sebastian") == 1
    assert "Med vänliga hälsningar,\nSebastian Bergman\n" in resultat


# -- HTML-delen -------------------------------------------------------------


def test_bygg_html_bar_logotypen_och_escapar_brodtexten():
    sig = normalisera(SIG)
    brodtext = med_signatur("Hej!\n\nVi bygger <AI> för er.", sig)
    html = bygg_html(brodtext, sig)
    assert f'<img src="{SIG["logotyp_url"]}"' in html
    assert "&lt;AI&gt;" in html and "<AI>" not in html
    # Textblockets rader finns kvar som synlig HTML-text.
    assert "Sebastian Bergman" in html
    assert "Umeå &amp; Göteborg" in html


def test_bygg_html_utan_blocket_visar_ingen_logga():
    # Ett äldre köat utkast utan signaturblock: HTML-delen får aldrig visa
    # något som inte granskats — texten renderas som den är, utan logga.
    sig = normalisera(SIG)
    html = bygg_html("Hej! En text utan signatur.", sig)
    assert "<img" not in html
    assert "En text utan signatur." in html


def test_bygg_html_signaturen_star_fore_den_lagstadgade_foten():
    sig = normalisera(SIG)
    brodtext = med_signatur("Hej!", sig) + "\n\n--\nBolaget AB, org.nr 556000-0000"
    html = bygg_html(brodtext, sig)
    assert html.index("<img") < html.index("556000-0000")


# -- köningsvägen -----------------------------------------------------------


@pytest.mark.anyio
async def test_queue_outreach_draft_lagger_pa_signaturen_fore_foten():
    storage = MemoryStorage()
    storage.agent_settings[(TENANT, "leads")] = {"signatur": dict(SIG)}
    ctx = OutreachContext(
        storage=storage, tenant_id=TENANT, thread_id="thread-1", prospect_email="p@example.se"
    )

    await _queue_outreach_draft_impl(
        ctx,
        subject="En idé till er",
        body="Hej! Vi hjälper er spara tid.\n\nMed vänliga hälsningar,",
        language_state="sv",
        humanizer_variant="snajp:humanizer-svenska",
    )

    body = storage.outreach_messages[TENANT][0]["body"]
    assert "Med vänliga hälsningar,\nSebastian Bergman\n" in body
    assert "Snajp AB" in body


@pytest.mark.anyio
async def test_queue_outreach_draft_utan_signatur_lamnar_brodtexten_ifred():
    storage = MemoryStorage()
    ctx = OutreachContext(
        storage=storage, tenant_id=TENANT, thread_id="thread-1", prospect_email="p@example.se"
    )

    await _queue_outreach_draft_impl(
        ctx,
        subject="En idé till er",
        body="Hej! Vi hjälper er spara tid.",
        language_state="sv",
        humanizer_variant="snajp:humanizer-svenska",
    )

    assert "Sebastian" not in storage.outreach_messages[TENANT][0]["body"]


# -- granskningsvyns delning (brödtext / svans) ------------------------------

FOT = "--\nBolaget AB, org.nr 556000-0000\n\nVill du inte få fler mejl från oss: https://x.se/avregistrera/abc"


def test_dela_utkast_skiljer_brodtext_fran_signatur_och_fot():
    sig = normalisera(SIG)
    body = med_signatur("Hej!\n\nMed vänliga hälsningar,", sig) + "\n\n" + FOT
    brodtext, svans = dela_utkast(body, sig)
    assert brodtext == "Hej!\n\nMed vänliga hälsningar,"
    assert svans.startswith("Sebastian Bergman\n") and svans.endswith("abc")
    assert sla_ihop(brodtext, svans, sig) == body


@pytest.mark.parametrize(
    "brodtext, vantat",
    [
        ("Hej!\n\nHör av dig.", "Hör av dig.\n\nVänliga hälsningar,\nSebastian Bergman\n"),
        ("Hej!\n\nHör av dig.\n\nVänliga hälsningar", "Vänliga hälsningar\nSebastian Bergman\n"),
        ("Hej!\n\nHör av dig.\n\nMvh", "Mvh\nSebastian Bergman\n"),
    ],
)
def test_med_signatur_lagger_pa_halsningsfras_bara_nar_den_saknas(brodtext, vantat):
    resultat = med_signatur(brodtext, normalisera(SIG), halsning="Vänliga hälsningar,")
    assert vantat in resultat
    assert resultat.count("hälsningar") <= 1


def test_dela_utkast_utan_signatur_tar_bara_foten():
    brodtext, svans = dela_utkast("Hej!\n\n" + FOT, None)
    assert brodtext == "Hej!"
    assert svans == FOT


def test_dela_utkast_utan_svans_lamnar_texten():
    assert dela_utkast("Hej!\n", normalisera(SIG)) == ("Hej!", "")


def test_sla_ihop_efter_omskrivning_behaller_signatur_och_fot():
    """Förbättra skrev om brödtexten och avslutade själv med förnamnet —
    signaturens namnrad tar över raden, och logga + fot står kvar."""
    sig = normalisera(SIG)
    _, svans = dela_utkast(med_signatur("Hej!", sig) + "\n\n" + FOT, sig)
    ihop = sla_ihop("Hej igen, kort fråga.\n\nVänliga hälsningar,\nSebastian", svans, sig)
    assert ihop.startswith("Hej igen, kort fråga.\n\nVänliga hälsningar,\nSebastian Bergman\n")
    assert ihop.endswith(FOT)
    assert "<img" in bygg_html(ihop, sig)


def test_arbetsytans_namn_efter_halsningen_ger_inte_dubbel_avslutning():
    """sign_off satte "Snajp" efter modellens hälsningsfras, och signaturen
    fick en hälsningsfras till: "Vänliga hälsningar,\nSnajp\n\nVänliga
    hälsningar,\nSebastian Bergman" (4 av 6 utkast, development 2026-10-09)."""
    ut = med_signatur("Hej,\n\nText.\n\nVänliga hälsningar,\nSnajp", SIG, halsning="Vänliga hälsningar,")
    assert ut.count("Vänliga hälsningar") == 1
    assert ut.endswith(bygg_signaturtext(SIG))
    assert "\nSnajp\n" not in ut.split("Sebastian Bergman")[0]
    # En vanlig mening sist rörs inte.
    ut2 = med_signatur("Hej,\n\nVänliga hälsningar,\nHör av dig.", SIG, halsning="Vänliga hälsningar,")
    assert "Hör av dig." in ut2
