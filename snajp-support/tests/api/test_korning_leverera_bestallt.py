"""Körningen ger inte upp under beställt antal i onödan (Anton 2026-10-15).

"Vi slutar inte förrän vi levererat det beställda antalet PROCESSADE leads",
och bolag som redan valts bort ska inte prövas igen av nästa körning förrän
efter en tid, då de blandas in på nytt.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.api import leads as leads_api
from app.leads import korning


def test_en_beställning_på_50_ryms_i_rundorna():
    # Före 2026-10-15: 11 rundor x 8 kandidater = högst 88 bolag för 50 leads.
    assert korning.max_rundor(50) * korning.MAX_PER_RUNDA >= 50 * korning.TAK_FAKTOR
    assert korning.ny_korning(mal=50, scope="research_and_draft", overrides=None, is_test=True)["tak"] >= 500


@pytest.mark.parametrize(
    "post,star",
    [
        ({"steg": "jev", "skal": "Säljer bara till offentlig sektor"}, True),
        ({"steg": "research", "skal": "Ingen belagd koppling"}, True),
        ({"steg": "existens", "skal": "Bolagsnamnet står inte på webbplatsen"}, True),
        ({"steg": "förfilter", "skal": "För stort: 700 anställda"}, True),
        ({"steg": "förfilter", "skal": "Utanför målområdet: postnummer 431 69."}, False),
        ({"steg": "dubblett", "skal": "Finns redan"}, False),
    ],
)
def test_vilka_bortval_som_står_sig(post, star):
    assert leads_api._bortval_som_star_sig(post) is star


class _Lager:
    def __init__(self, rader):
        self.rader = rader

    async def list_leads_korningar(self, tenant_id, *, limit=20):
        return self.rader


@pytest.mark.anyio
async def test_nyligen_bortvalda_utesluts_och_gamla_blandas_in():
    nu = datetime.now(timezone.utc)
    rader = [
        {"job_id": "a", "created_at": nu - timedelta(days=2),
         "korning": {"klar": True, "tratt": [{"namn": "Nylig AB", "steg": "jev"},
                                             {"namn": "Mölndal AB", "steg": "förfilter",
                                              "skal": "Utanför målområdet: postnummer 431 69."}]}},
        {"job_id": "b", "created_at": nu - timedelta(days=leads_api.BORTVAL_DAGAR + 1),
         "korning": {"klar": True, "tratt": [{"namn": "Gammal AB", "steg": "jev"}]}},
        {"job_id": "c", "created_at": nu, "korning": {"klar": False, "tratt": [{"namn": "Pågår AB", "steg": "jev"}]}},
    ]
    ut = await leads_api._nyligen_bortvalda(_Lager(rader), "t", "denna")
    assert ut == {"nylig"}
