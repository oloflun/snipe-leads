"""Kunskapsbasen: uppslag, ordgränser och samspelet med INV-BOOK-003.

Tre frågor prövas:

  1. Hittar `sok_amne` rätt ämne — och ingenting när ämnet inte finns?
  2. Håller ordgränserna, så att "bil" inte träffar "biljett" och en
     specifik fras inte stjäls av ett tidigare ämnes prefix?
  3. Räknas talen i en uppslagen text som HÄMTADE under INV-BOOK-003, så att
     ett svar som citerar 300 kr-taket inte fälls?

Verktyget testas via `_sla_upp_kunskap_impl`, samma val som test_chatt.py.
"""

from __future__ import annotations

import json

import pytest

from app.agent.bookkeeping_chat_tools import BokforingChattContext, _sla_upp_kunskap_impl
from app.bookkeeping.beloppsgrind import check_belopp
from app.bookkeeping.kunskap import KUNSKAP, sok_amne
from app.storage.memory import MemoryStorage


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- 1. Uppslaget ----------------------------------------------------------


def test_exakt_id_traffar():
    assert sok_amne("representation").id == "representation"
    assert sok_amne("momssatser").id == "momssatser"


def test_fraga_i_lopande_text_traffar():
    assert sok_amne("Vad gäller för representation vid en kundmiddag?").id == "representation"
    assert sok_amne("När ska jag deklarera momsen?").id == "momsdeklaration"
    assert sok_amne("Hur funkar omvänd byggmoms?").id == "omvand_byggmoms"
    assert sok_amne("Vad är skillnaden mellan K2 och K3?").id == "k_regelverk"


def test_okant_amne_ger_none_inte_narmaste():
    assert sok_amne("rymdfärja") is None
    assert sok_amne("") is None


def test_alla_amnen_har_rubrik_och_text():
    for amne_id, amne in KUNSKAP.items():
        assert amne.id == amne_id
        assert amne.rubrik.strip()
        assert len(amne.text) > 100, f"{amne_id} har en text som inte förklarar något"
        assert amne.nyckelord, f"{amne_id} går inte att hitta utan nyckelord"


# -- 2. Ordgränserna -------------------------------------------------------


def test_kort_nyckelord_matchar_bara_hela_ord():
    """"bil" är tre tecken och får inte prefixmatcha — annars hade "biljett"
    blivit en bilfråga."""
    assert sok_amne("vad kostar en biljett").id == "resor_och_traktamente"
    assert sok_amne("firmans bil").id == "telefon_och_bil"


def test_bojningsform_traffar_via_prefix():
    assert sok_amne("mobilen jag köpte till firman").id == "telefon_och_bil"


def test_specifikt_amne_stjals_inte_av_tidigare_prefix():
    """"momsdeklaration" ska nå sitt eget ämne, inte fastna i "momssatser" för
    att "moms" råkar vara ett prefix av ordet. Det är hela skälet till att
    sökningen går i två pass."""
    assert sok_amne("momsdeklarationen i januari").id == "momsdeklaration"


# -- 3. Verktyget och INV-BOOK-003 -----------------------------------------


@pytest.mark.anyio
async def test_verktyget_svarar_ur_texten_och_sparar_i_kontexten():
    ctx = BokforingChattContext(storage=MemoryStorage(), tenant_id="tenant-a")
    svar = json.loads(await _sla_upp_kunskap_impl(ctx, "representation"))
    assert svar["amne"] == "representation"
    assert "300 kr" in svar["text"]
    # Resultatet ligger i kontexten — det är hela indata till INV-BOOK-003.
    assert len(ctx.resultat) == 1


@pytest.mark.anyio
async def test_tal_ur_kunskapen_raknas_som_hamtade():
    """Ett svar som citerar 300 kr-taket ur en uppslagen text ska passera
    beloppsgrinden — talet ÄR hämtat, ur ett verktygsresultat."""
    ctx = BokforingChattContext(storage=MemoryStorage(), tenant_id="tenant-a")
    await _sla_upp_kunskap_impl(ctx, "representation")
    verdikt = check_belopp(
        "Momsen får dras av på ett underlag upp till 300 kr exklusive moms per person.",
        ctx.resultat,
    )
    assert verdikt.ok


@pytest.mark.anyio
async def test_okant_amne_ger_de_kanda_amnena():
    ctx = BokforingChattContext(storage=MemoryStorage(), tenant_id="tenant-a")
    svar = json.loads(await _sla_upp_kunskap_impl(ctx, "rymdfärja"))
    assert svar["hittades"] is False
    assert svar["kanda_amnen"] == sorted(KUNSKAP)


@pytest.mark.anyio
async def test_verktyget_laser_ingen_kunddata():
    """Kunskapen är delad text, inte tenantens siffror: två tenanter får
    exakt samma svar, och ingenting ur lagringen följer med."""
    storage = MemoryStorage()
    svar_a = json.loads(
        await _sla_upp_kunskap_impl(
            BokforingChattContext(storage=storage, tenant_id="tenant-a"), "moms"
        )
    )
    svar_b = json.loads(
        await _sla_upp_kunskap_impl(
            BokforingChattContext(storage=storage, tenant_id="tenant-b"), "moms"
        )
    )
    assert svar_a == svar_b
