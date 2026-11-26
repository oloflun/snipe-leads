"""INV-LEADS-N-001 (omskriven 2026-11-24): en Iris-körning levererar
beställt antal, eller vilar och letar vidare. Den blir aldrig "klar, under
målet".

Antons regel 2026-11-24, ordagrant: "Iris får aldrig, under inga
omständigheter leverera under beställt antal, i värsta fall får man ta ett av
de (mest kvalificerade) bortsorterade bolagen för att fylla ut kvoten, om inga
fullt kvalificerade hittas."

Testet kör den riktiga motorn (`_run_batch` → `_fyll_pa` → prospektjobb →
`_rapportera_till_korning`) mot MemoryStorage med en fejkad sökning och en
fejkad research, som i test_inv_leads_n_001.py. Påfyllnadsstegens rena
funktioner prövas i tests/leads/test_pafyllnad.py.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.api import leads as leads_api
from app.jobs.store import MemoryJobStore
from app.leads import korning as korningsmodul
from app.leads import listvy
from app.leads.scoring import MISS, TRAFF
from app.storage.memory import MemoryStorage
from tests.orgnr_fixtur import orgnr_for

pytestmark = pytest.mark.anyio
TENANT = {"tenant_id": "00000000-0000-0000-0000-00000000a1a2", "tenant_name": "Testbyrån"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _bolag(namn: str) -> dict:
    slug = namn.lower().replace(" ", "")
    return {
        "company_name": namn,
        "website": f"https://{slug}.se",
        "orgnr": orgnr_for(namn),
        "ort": "Göteborg",
        "postnr": "421 32",
        "contact_email": f"info@{slug}.se",
        "contact_level": "role_address",
        "contact_name": "Test Testsson",
        "contact_role": "VD",
        "anstallda": None,
    }


def _rad(nyckel: str, utfall: str, *, belagg: bool = False) -> dict:
    return {"nyckel": nyckel, "etikett": nyckel, "vikt": 1, "utfall": utfall, "motivering": "m",
            "hart": True, "belagg": [{"url": "u", "citat": "c"}] if belagg else []}


def _installera(monkeypatch, pool: list[dict], bra: set[str], *, lage_for_daliga: bool = True) -> list[str]:
    """Sökningen ger poolen en gång; researchen godkänner bara `bra`. De
    underkända får en riktig bedömning sparad (kp okänd, k1 ja), som en
    riktig research gör, och en lägesbeskrivning när `lage_for_daliga`."""
    researchade: list[str] = []

    async def _hitta(icp, antal, *, uteslut_namn=None, **_k):
        uteslut = {n.casefold() for n in (uteslut_namn or set())}
        return [b for b in pool if b["company_name"].casefold() not in uteslut][:antal]

    async def _research(storage, tenant_id, *, prospect_id, **_k):
        rad = await storage.get_prospect(tenant_id, prospect_id)
        researchade.append(rad["company_name"])
        ok = rad["company_name"] in bra
        if not ok:
            await storage.spara_bedomning(tenant_id, prospect_id, bedomning={
                "niva": "C", "score_total": 30, "icp_fit": 0.3,
                "score_breakdown": [_rad("kp", MISS), _rad("k1", TRAFF, belagg=True)],
                "disqualifiers": ["Ingen belagd koppling till det kunden säljer: m"],
            })
        return {
            "qualified": ok,
            "icp_fit": 0.85 if ok else 0.3,
            "score_total": 85 if ok else 30,
            "disqualifiers": [] if ok else ["Ingen belagd koppling till det kunden säljer: m"],
            "stopped_early": None if ok else "ej_kvalificerad",
            "lagesbeskrivning": "Bolaget bygger i Göteborg enligt sajten." if ok or lage_for_daliga else None,
        }

    async def _utkast(*_a, **_k):
        return {"subject": "Hej", "queued": True}

    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (_research, _utkast))
    return researchade


async def _kor(mal: int) -> tuple[dict, SimpleNamespace, str]:
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=MemoryStorage(), leadsstrom=None)
    job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")
    await leads_api._run_batch(
        app_state,
        {
            "kind": "batch", "job_id": job_id, **TENANT, "scope": "research",
            "overrides": {"industries": ["Redovisning"]}, "is_test": True, "limit": mal, "company_names": [],
        },
    )
    k: dict = {}
    for _ in range(300):
        post = await app_state.jobs.get(job_id)
        k = (post.get("result") or {}).get("korning") or {}
        if k.get("klar") or (k.get("vilande") and not k.get("pagaende")):
            return k, app_state, job_id
        await asyncio.sleep(0.02)
    raise AssertionError(f"körningen blev aldrig klar eller vilande: {k}")


async def test_en_snal_pool_ger_ändå_beställt_antal(monkeypatch):
    """Bara ett av tre bolag klarar grindarna; körningen fyller på med det
    mest kvalificerade bortvalet i stället för att sluta på 1 av 2."""
    pool = [_bolag(n) for n in ("Dålig Ett", "Bra Ett", "Dålig Två")]
    _installera(monkeypatch, pool, bra={"Bra Ett"})
    k, app_state, _ = await _kor(2)
    assert k["levererade"] == 2 == k["mal"], k
    assert k["klar"] and k["slut_orsak"] == "klar"
    # Stegen kom i bestämd ordning och slutade när målet nåddes: steg 3 tog
    # ett av de två bortvalen och står inte som klart, eftersom ett är kvar.
    assert k["pafyllnad"]["klara"] == ["omforsok", "prova_om"]
    assert len(k["pafyllnad"]["anvanda"]) == 1
    # Det påfyllda leadet behåller sin riktiga bedömning och bär märkningen.
    prospekt = await app_state.storage.list_prospects(TENANT["tenant_id"])
    pafyllda = [p for p in prospekt if p.get("pafylld")]
    assert len(pafyllda) == 1
    assert pafyllda[0]["niva"] == "C" and pafyllda[0]["pafylld_skal"]
    # …och syns i leadslistan, medan det andra bortvalet fortfarande är dolt.
    synliga = listvy.synliga(prospekt, tenant_id=TENANT["tenant_id"], kopplade=set())
    namn = {p["company_name"] for p in synliga}
    assert pafyllda[0]["company_name"] in namn and "Bra Ett" in namn
    assert len(synliga) == 2


async def test_ett_tomt_register_ger_vilande_aldrig_klar_under_malet(monkeypatch):
    """Inget bortval går att leverera (ingen lägesbeskrivning): körningen
    vilar och letar vidare, med skälet. Den blir aldrig klar under målet."""
    pool = [_bolag(n) for n in ("Dålig Ett", "Bra Ett")]
    _installera(monkeypatch, pool, bra={"Bra Ett"}, lage_for_daliga=False)
    k, app_state, job_id = await _kor(3)
    assert not k["klar"] and k.get("slut_orsak") is None
    assert k["vilande"]["skal"] == "registret"
    assert k["levererade"] == 1
    # Alla steg prövades, i ordning, innan körningen lade sig att vila.
    assert k["pafyllnad"]["klara"] == list(korningsmodul.PAFYLLNADSSTEG)
    rad = await app_state.storage.get_leads_korning(TENANT["tenant_id"], job_id)
    assert rad["status"] == "processing"
    # Det misslyckade påfyllnadsförsöket bär ingen märkning.
    prospekt = await app_state.storage.list_prospects(TENANT["tenant_id"])
    assert not any(p.get("pafylld") for p in prospekt)


async def test_en_vilande_korning_fälls_inte_av_städaren(monkeypatch):
    pool = [_bolag("Dålig Ett")]
    _installera(monkeypatch, pool, bra=set(), lage_for_daliga=False)
    k, app_state, job_id = await _kor(1)
    assert k.get("vilande")
    rad = app_state.storage.leads_job_ledger[job_id]
    rad["updated_at"] = "2026-01-01T00:00:00+00:00"
    stadade = await app_state.storage.stada_hangande_leadsjobb(TENANT["tenant_id"], aldre_an_minuter=60)
    assert job_id not in stadade and rad["status"] == "processing"


# --- Stegen genom motorn (granskningen 2026-11-25) ---------------------------


async def test_steg_1_ett_tjanstefel_researchas_om_och_levereras(monkeypatch):
    """Researchen föll på "Inget källmaterial" första gången. Steg 1 köar
    bolaget igen; andra försöket lyckas och levereras som ett vanligt lead."""
    pool = [_bolag("Fel Ett")]
    _installera(monkeypatch, pool, bra=set())
    researchade: list[str] = []

    async def _research(storage, tenant_id, *, prospect_id, **_k):
        rad = await storage.get_prospect(tenant_id, prospect_id)
        researchade.append(rad["company_name"])
        if len(researchade) == 1:
            return {"qualified": False, "icp_fit": None, "score_total": 0,
                    "disqualifiers": ["Inget källmaterial: bolagets sidor gick inte att hämta."],
                    "stopped_early": "inget_kallmaterial", "lagesbeskrivning": None}
        return {"qualified": True, "icp_fit": 0.85, "score_total": 85, "disqualifiers": [],
                "stopped_early": None, "lagesbeskrivning": "Bolaget bygger i Göteborg enligt sajten."}

    async def _utkast(*_a, **_k):
        return {"subject": "Hej", "queued": True}

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (_research, _utkast))
    k, app_state, _ = await _kor(1)
    assert k["levererade"] == 1 and k["klar"], k
    assert researchade == ["Fel Ett", "Fel Ett"]
    assert k["pafyllnad"]["klara"] == ["omforsok"]
    prospekt = await app_state.storage.list_prospects(TENANT["tenant_id"])
    assert not any(p.get("pafylld") for p in prospekt)


async def test_steg_2_en_sajt_utan_kontakt_provas_om_och_blir_iris(monkeypatch):
    """Sökningen lade bolaget i listspåret ("prova_om"). Steg 2 prövar sajten
    igen; kontaktsökningen hittar en mejladress, bolaget blir en
    Iris-kandidat, lämnar listspåret och levereras."""
    from app.leads import omprova

    rad = {"company_name": "Omprov Ett", "website": "https://omprovett.se", "orgnr": orgnr_for("Omprov Ett"),
           "ort": "Göteborg", "spar": "prova_om", "signal_detalj": "Sajt utan hittad kontakt", "tak": False}
    anrop = {"n": 0}

    async def _hitta(icp, antal, *, listspar=None, **_k):
        anrop["n"] += 1
        if anrop["n"] == 1 and listspar is not None:
            listspar.append(dict(rad))
        return []

    async def _sok_alla(par, **_k):
        return [(omprova.kandidat_ur_rad(r, b), {"contact_email": "info@omprovett.se",
                                                 "contact_level": "role_address"}) for r, b in par]

    _installera(monkeypatch, [], bra={"Omprov Ett"})
    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    monkeypatch.setattr(omprova, "sok_alla", _sok_alla)
    k, app_state, _ = await _kor(1)
    assert k["levererade"] == 1 and k["klar"], k
    assert k["pafyllnad"]["klara"] == ["omforsok", "prova_om"]
    assert not any(r.get("company_name") == "Omprov Ett" for r in k.get("listspar") or [])
    prospekt = await app_state.storage.list_prospects(TENANT["tenant_id"])
    assert [p["company_name"] for p in prospekt] == ["Omprov Ett"]
    assert not prospekt[0].get("pafylld")


async def test_steg_4_storleken_vidgas_och_bolaget_bar_markningen(monkeypatch):
    """Registret fällde bolaget på storleken ("55 anställda, högst 49"). Steg 4
    vidgar gränsen 25 % (49 → 62), sökningen hittar bolaget igen, och det
    levereras som påfyllt med skälets kod."""
    stor = {**_bolag("Stor Ett"), "anstallda": 55}
    sett: list[int | None] = []

    async def _hitta(icp, antal, *, uteslut_namn=None, profil=None, bortval=None, **_k):
        hi = (profil or {}).get("anstallda_max")
        sett.append(hi)
        if len(sett) == 1 and bortval is not None:
            bortval.append({"company_name": "Stor Ett", "orgnr": stor["orgnr"],
                            "skal": "För stort: 55 anställda (högst 49)."})
            return []
        uteslut = {n.casefold() for n in (uteslut_namn or set())}
        if hi is not None and hi >= 55 and "stor ett" not in uteslut:
            return [dict(stor)]
        return []

    _installera(monkeypatch, [], bra={"Stor Ett"})
    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)

    async def _kor_med_grans(mal: int):
        app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=MemoryStorage(), leadsstrom=None)
        job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")
        await leads_api._run_batch(app_state, {
            "kind": "batch", "job_id": job_id, **TENANT, "scope": "research",
            "overrides": {"industries": ["Redovisning"], "anstallda_max": 49},
            "is_test": True, "limit": mal, "company_names": [],
        })
        for _ in range(300):
            post = await app_state.jobs.get(job_id)
            k = (post.get("result") or {}).get("korning") or {}
            if k.get("klar") or (k.get("vilande") and not k.get("pagaende")):
                return k, app_state
            await asyncio.sleep(0.02)
        raise AssertionError("körningen blev aldrig klar eller vilande")

    k, app_state = await _kor_med_grans(1)
    assert sett[0] == 49, sett
    assert k["levererade"] == 1 and k["klar"], k
    assert k["pafyllnad"]["vidgad"] == {"anstallda_max": 62}
    assert "storlek_25" in k["pafyllnad"]["klara"] and "storlek_50" not in k["pafyllnad"]["klara"]
    # Researchens storleksrad ser samma vidgning.
    assert k["overrides"]["anstallda_max"] == 62
    prospekt = await app_state.storage.list_prospects(TENANT["tenant_id"])
    assert len(prospekt) == 1 and prospekt[0]["pafylld"] is True
    assert prospekt[0]["pafylld_skal"] == "storlek:anstallda:max:55:49"


async def test_en_vilande_korning_haller_bara_sina_kandidater():
    """Granskningen 2026-11-25: en vilande körning står i processing, och dess
    tratt och listspår räknades som upptagna för kundens andra körningar så
    länge den vilade."""

    # Det riktiga minneslagret, inte en fejk: sedan 2026-11-25 väljer lagringen
    # själv ut vad en vilande körning håller (list_andra_korningars_bolag), så
    # regeln måste prövas där den sitter. Samma fall körs mot Postgres i
    # tests/db/test_demorattningar_db.py.
    lager = MemoryStorage()
    grund = {"tenant_id": TENANT["tenant_id"], "scope": "batch", "status": "processing",
             "is_test": False, "created_at": "2026-11-25T08:00:00+00:00"}
    lager.leads_job_ledger["vilande"] = {**grund, "job_id": "vilande", "korning": {
        "vilande": {"skal": "registret"}, "kandidater": [{"company_name": "Kandidat AB"}],
        "tratt": [{"namn": "Tratt AB"}], "listspar": [{"company_name": "Listspar AB"}],
    }}
    lager.leads_job_ledger["aktiv"] = {**grund, "job_id": "aktiv", "korning": {
        "kandidater": [], "tratt": [{"namn": "Aktiv Tratt AB"}], "listspar": [],
    }}

    ut = await leads_api._andra_korningars_bolag(lager, TENANT["tenant_id"], "egen")
    assert "kandidat" in ut and "aktiv tratt" in ut
    assert "tratt" not in ut and "listspar" not in ut


def test_leverbarhet_slapper_ett_pafyllt_lead_men_inte_ett_vanligt_c():
    from app.leads import eskalering

    regler = eskalering.normalisera({"kvalificeringstroskel": 50})
    rad = {"contact_email": "info@alfa.se", "website": "https://alfa.se", "lagesbeskrivning": "Sparad."}
    underkand = {"qualified": False, "icp_fit": 0.3, "disqualifiers": ["Ingen belagd koppling"]}
    assert leads_api._leverbarhet(rad, underkand, regler) == "Ingen belagd koppling"
    assert leads_api._leverbarhet({**rad, "pafylld": True}, underkand, regler) is None
    # Mottagaren och lägesbeskrivningen gäller även ett påfyllt lead.
    assert leads_api._leverbarhet({**rad, "pafylld": True, "contact_email": None}, underkand, regler)
    assert leads_api._leverbarhet({**rad, "pafylld": True, "lagesbeskrivning": None}, underkand, regler)


async def test_ett_pafyllt_lead_passerar_sandsparren_men_inte_ett_vanligt_c():
    from tests.leads.test_scheduler import (
        TENANT as S_TENANT,
        WITHIN_WINDOW_UTC,
        _FakeSendProvider,
        _seed,
    )
    from app.leads.scheduler import process_due_item

    storage = MemoryStorage()
    provider = _FakeSendProvider()

    async def _prova(pafylld: bool) -> str:
        item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
        p = await storage.create_prospect(S_TENANT, company_name=f"Bolag {pafylld} AB", origin="iris")
        await storage.spara_bedomning(S_TENANT, p["id"], bedomning={
            "niva": "C", "score_total": 30, "pafylld": pafylld, "pafylld_skal": "ovrigt" if pafylld else None,
        })
        storage.outreach_threads[S_TENANT][thread_id]["prospect_id"] = p["id"]
        await process_due_item(storage, S_TENANT, {"id": item_id, "thread_id": thread_id}, provider,
                               now=WITHIN_WINDOW_UTC)
        return str(next(i for i in storage.send_queue[S_TENANT] if i["id"] == item_id)["gate_checks"])

    assert "ej_styrkt" in await _prova(False)
    assert "ej_styrkt" not in await _prova(True)
