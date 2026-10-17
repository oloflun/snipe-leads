"""Registret får inte fälla en körning (development 2026-10-06).

463a9087: kundens bransch "e-utbildning & möblerfirmor för företagskontor"
matchade ingen merinfo-bransch som fras, och profilens "B2B/B2C" blev den
påhittade sluggen /b2b-b2c/ med 404 på varje sida. Tre rundor, 0 bolag.
Samma kväll kastade registret DiscoveryError vid 429 och tog med sig hela
sökrundan, fast sökkedjan ska fylla på (regel 11, 2026-10-07)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.leads import discovery
from app.leads.discovery import DiscoveryError
from app.leads.sources import merinfo

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_en_fras_delas_i_sina_branscher():
    valda = merinfo.valj_branscher(["e-utbildning & möblerfirmor för företagskontor"])
    assert "utbildningar-skolor" in valda
    assert any("mobler" in s for s in valda)


@pytest.mark.parametrize("term", ["B2B/B2C", "B2B", "b2c", "Företag"])
def test_kundtyp_blir_aldrig_en_bransch(term):
    assert merinfo.valj_branscher([term]) == []


def test_ett_branschord_provas_fortfarande_som_egen_slugg():
    assert merinfo.valj_branscher(["golvläggare"]) == ["golvlaggare"]


async def test_registret_som_inte_gar_att_lasa_lamnar_over_till_sokningen():
    svar = '[{"company_name": "Norrlands Kontor AB", "website": "https://norrlandskontor.se"}]'
    with (
        patch.object(merinfo, "aktiv", return_value=True),
        patch.object(merinfo, "sok", new=AsyncMock(side_effect=DiscoveryError("429"))),
        patch.object(discovery, "_gemini_med_sokning", new=AsyncMock(return_value=svar)) as sok,
        patch("app.leads.platshallare.utan_platshallare", new=AsyncMock(side_effect=lambda r: r)),
    ):
        fynd = await discovery.hitta_bolag({"industries": ["kontorsmöbler"]}, 2, profil={"branscher": ["kontorsmöbler"]})
    assert sok.await_count == 1
    assert [f["company_name"] for f in fynd] == ["Norrlands Kontor AB"]
