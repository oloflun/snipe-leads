"""Dubblettskyddet mellan kundens körningar läser bara bolagens identiteter.

2026-11-25: _andra_korningars_bolag läste varje annan pågående körnings hela
arbetsminne i varje sökrunda. En vilande körning (regel 23) står kvar i
'processing' med varje bolag den prövat, och avkodades därför i sin helhet i
varje runda hos kundens övriga körningar. Nu hämtas bara namn och org.nr
(storage.list_andra_korningars_bolag), och utan cache: det en annan aktiv
körning tar mitt under jobbet syns i nästa runda, som förut.
"""
from __future__ import annotations

import pytest

from app.api import leads as leads_api
from app.leads import upptagna
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-0000-0000-000000000001"


async def _korning(s: MemoryStorage, job_id: str, korning: dict) -> None:
    await s.set_leads_job_status(TENANT, job_id=job_id, status="processing", scope="batch", korning=korning)


def _rakna_tunga_lasningar(s: MemoryStorage) -> list[str]:
    """Spionerar på de läsningar som bär arbetsminnet."""
    tunga: list[str] = []
    lista, en = s.list_leads_korningar, s.get_leads_korning

    async def lista_spion(tenant_id, **kw):
        if kw.get("arbetsminne"):
            tunga.append("list_leads_korningar")
        return await lista(tenant_id, **kw)

    async def en_spion(tenant_id, job_id, **kw):
        if kw.get("arbetsminne", True):
            tunga.append("get_leads_korning")
        return await en(tenant_id, job_id, **kw)

    s.list_leads_korningar = lista_spion  # type: ignore[method-assign]
    s.get_leads_korning = en_spion  # type: ignore[method-assign]
    return tunga


@pytest.mark.anyio
async def test_andra_korningars_tunga_lasningar_vaxer_inte_med_rundorna():
    s = MemoryStorage()
    await _korning(s, "egen", {"mal": 10, "tratt": [], "kandidater": []})
    await _korning(s, "annan", {
        "mal": 200, "tratt": [{"namn": f"Prövat {i} AB", "steg": "jev"} for i in range(500)],
        "kandidater": [{"company_name": "Kandidat AB", "orgnr": "556000-0001"}],
        "listspar": [{"company_name": "Listspar AB"}],
        "webbpool": {"stor": "x" * 10_000}, "utslag": list(range(1000)),
    })
    tunga = _rakna_tunga_lasningar(s)
    for antal in (1, 10):
        tunga.clear()
        for _ in range(antal):
            ut = await leads_api._andra_korningars_bolag(s, TENANT, "egen")
        assert tunga == [], f"{antal} rundor gav tunga läsningar: {tunga}"
    assert upptagna.upptagen(ut, "Kandidat AB") and upptagna.upptagen(ut, None, "5560000001")
    assert upptagna.upptagen(ut, "Listspar AB") and upptagna.upptagen(ut, "Prövat 499 AB")
    # Den egna körningen räknas aldrig.
    assert all(r["job_id"] != "egen" for r in await s.list_andra_korningars_bolag(TENANT, utom="egen"))


@pytest.mark.anyio
async def test_andra_korning_som_tar_ett_bolag_mitt_i_jobbet_utesluts_i_nasta_runda():
    s = MemoryStorage()
    await _korning(s, "egen", {"mal": 10, "tratt": [], "kandidater": []})
    await _korning(s, "annan", {"mal": 10, "tratt": [], "kandidater": []})

    forsta = await leads_api._andra_korningars_bolag(s, TENANT, "egen")
    assert not upptagna.upptagen(forsta, "Nytaget AB")

    # Den andra körningen sparar sitt tillstånd efter en egen runda.
    await _korning(s, "annan", {
        "mal": 10, "tratt": [{"namn": "Prövat Nu AB", "steg": "jev"}],
        "kandidater": [{"company_name": "Nytaget AB", "orgnr": "5561112223"}],
        "listspar": [{"company_name": "Ringbolag AB"}],
    })
    andra = await leads_api._andra_korningars_bolag(s, TENANT, "egen")
    assert upptagna.upptagen(andra, "Nytaget AB")
    assert upptagna.upptagen(andra, "Annat Namn", "556111-2223")
    assert upptagna.upptagen(andra, "Prövat Nu AB") and upptagna.upptagen(andra, "Ringbolag AB")

    # En körning som blivit klar håller inga bolag längre.
    await _korning(s, "annan", {"mal": 10, "klar": True, "kandidater": [{"company_name": "Nytaget AB"}]})
    assert await leads_api._andra_korningars_bolag(s, TENANT, "egen") == set()


@pytest.mark.anyio
async def test_vilande_andra_korning_haller_bara_sina_kandidater():
    s = MemoryStorage()
    await _korning(s, "egen", {"mal": 10, "tratt": [], "kandidater": []})
    await _korning(s, "vilande", {
        "mal": 200, "vilande": {"sedan": "2026-11-24T10:00:00+00:00", "skal": "registret"},
        "kandidater": [{"company_name": "Kandidat AB"}],
        "tratt": [{"namn": f"Prövat {i} AB"} for i in range(500)],
        "listspar": [{"company_name": "Listspar AB"}],
    })
    await _korning(s, "aktiv", {"mal": 10, "tratt": [{"namn": "Aktiv Tratt AB"}], "kandidater": []})

    rader = {r["job_id"]: r for r in await s.list_andra_korningars_bolag(TENANT, utom="egen")}
    # Den vilande körningens tratt (varje bolag den prövat) lämnar inte lagringen.
    assert rader["vilande"] == {
        "job_id": "vilande", "vilande": True, "kandidater": [{"company_name": "Kandidat AB", "orgnr": None}],
        "listspar": [], "tratt": [],
    }
    ut = await leads_api._andra_korningars_bolag(s, TENANT, "egen")
    assert upptagna.upptagen(ut, "Kandidat AB") and upptagna.upptagen(ut, "Aktiv Tratt AB")
    assert not upptagna.upptagen(ut, "Prövat 3 AB") and not upptagna.upptagen(ut, "Listspar AB")
