"""Beskedet när en uppladdad fil inte sparas (hittat av evalsviten, 2026-11-10).

En faktura som företaget självt skickat till en kund, uppladdad med den
vanliga knappen, avvisades med "Filen ser inte ut att vara ett kvitto eller en
faktura". Det är en faktura, och det som saknades i beskedet var vägen
framåt: knappen för kundfakturor.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.api.kvitton as kvitton_api
from app.bookkeeping.underlag import UnderlagsfelError
from app.storage.memory import MemoryStorage
from evals.bedomning import enkel_pdf

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def _inget_underlag(monkeypatch):
    async def _hantera(*_a, **_k):
        return SimpleNamespace(resultat={"underlag": [], "klass": "EJ_UNDERLAG"})

    monkeypatch.setattr(kvitton_api, "hantera", _hantera)


async def _ladda_upp(riktning):
    pdf = enkel_pdf("Faktura 1042\nEvalbolaget AB\nTill: Solrosen AB\nAtt betala 2 240,00 kr")
    with pytest.raises(UnderlagsfelError) as fangad:
        await kvitton_api.ta_emot_kvittofil(MemoryStorage(), "t1", pdf, "application/pdf", "faktura.pdf", riktning=riktning)
    return str(fangad.value)


async def test_beskedet_pekar_pa_knappen_for_kundfakturor(_inget_underlag):
    text = await _ladda_upp(None)

    assert "sparades inte" in text
    assert "Ladda upp kundfaktura" in text


async def test_den_som_redan_valt_kundfaktura_far_inte_radet_igen(_inget_underlag):
    text = await _ladda_upp("intakt")

    assert "sparades inte" in text
    assert "Ladda upp kundfaktura" not in text
