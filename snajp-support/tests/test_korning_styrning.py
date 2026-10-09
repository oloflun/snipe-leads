"""Paus, avbrott och deploysäkerhet för Iris-körningar (2026-10-05).

  a) paus köar inget nytt, städaren rör inte pausen, återupptagning når målet,
  b) avbrott: köade barn hoppar över sin research och körningen slutar 'avbruten',
  c) motorns helskrivning av tillståndet nollar aldrig styrningen,
  d) ett barn som rapporterar två gånger (återtag efter deploy) räknas en gång,
  e) ett återtaget barn som redan står completed väcker körningen,
  f) städaren mäter tystnad (updated_at), inte ålder,
  g) hjärtslaget hindrar en syskonprocess från att ta över en levande post.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import fakeredis.aioredis as fakeredis_aio
import pytest

from app.api import leads as leads_api
from app.jobs import stream as stream_mod
from app.jobs.store import MemoryJobStore
from app.jobs.stream import ChattStrom
from app.leads import korning as korningsmodul
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio
TENANT = {"tenant_id": "00000000-0000-0000-0000-00000000c3c3", "tenant_name": "Styrbyrån"}
TID = TENANT["tenant_id"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _bolag(namn: str) -> dict:
    from tests.orgnr_fixtur import orgnr_for

    slug = namn.lower().replace(" ", "")
    return {
        "company_name": namn, "website": f"https://{slug}.se", "orgnr": orgnr_for(namn),
        "ort": "Göteborg", "postnr": "421 32", "contact_email": f"info@{slug}.se",
        "contact_level": "role_address", "contact_name": "Test Testsson", "contact_role": "VD",
        "anstallda": None,
    }


def _installera(monkeypatch) -> None:
    async def _research(storage, tenant_id, *, prospect_id, **_k):
        return {"qualified": True, "icp_fit": 0.9, "score_total": 90, "disqualifiers": [],
                "stopped_early": None, "lagesbeskrivning": "Bolaget växer enligt sajten."}

    async def _utkast(*_a, **_k):
        return {"subject": "Hej"}

    async def _hitta(*_a, **_k):
        return []

    monkeypatch.setattr(korningsmodul, "hitta_bolag", _hitta)
    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (_research, _utkast))


class _Kö:
    """Leadsström som bara samlar posterna, så testet styr när barnen körs."""

    def __init__(self) -> None:
        self.poster: list[dict] = []

    async def enqueue(self, payload: dict) -> str:
        self.poster.append(payload)
        return str(len(self.poster))


async def _ny_korning(storage: MemoryStorage, namn: list[str]) -> str:
    job_id = f"batch-{len(storage.leads_job_ledger)}"
    k = korningsmodul.ny_korning(mal=len(namn), scope="research", overrides=None, is_test=True)
    k["kandidater"] = [_bolag(n) for n in namn]
    await storage.set_leads_job_status(TID, job_id=job_id, status="processing", scope="batch", korning=k, is_test=True)
    return job_id


async def _k(storage: MemoryStorage, job_id: str) -> dict:
    return (await storage.get_leads_korning(TID, job_id))["korning"]


async def _kor_barn(app_state, post: dict) -> None:
    await leads_api._run_batch_prospect(
        app_state, post["job_id"], TENANT, prospect_id=post["prospect_id"], scope=post["scope"],
        is_test=True, batch_id=post["batch_id"],
    )


async def test_paus_koar_inget_och_overlever_stadaren(monkeypatch):
    _installera(monkeypatch)
    storage, ko = MemoryStorage(), _Kö()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=ko)
    job_id = await _ny_korning(storage, ["Ett AB", "Två AB"])

    assert await storage.set_korning_styrning(TID, job_id, "paus")
    await leads_api._fyll_pa(app_state, TENANT, job_id)
    k = await _k(storage, job_id)
    assert ko.poster == [] and k["jobs"] == [] and not k["klar"]

    # Städaren (tröskel 0 min = allt är "gammalt") lämnar pausen orörd.
    assert job_id not in await storage.stada_hangande_leadsjobb(TID, aldre_an_minuter=0)

    assert await storage.set_korning_styrning(TID, job_id, None)
    await leads_api._fyll_pa(app_state, TENANT, job_id)
    assert len(ko.poster) == 2
    for post in list(ko.poster):
        await _kor_barn(app_state, post)
    rad = await storage.get_leads_korning(TID, job_id)
    assert rad["status"] == "completed"
    assert rad["korning"]["levererade"] == 2 and rad["korning"]["slut_orsak"] == "klar"


async def test_avbrott_hoppar_over_koade_barn(monkeypatch):
    _installera(monkeypatch)
    storage, ko = MemoryStorage(), _Kö()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=ko)
    job_id = await _ny_korning(storage, ["Ett AB", "Två AB", "Tre AB"])
    await leads_api._fyll_pa(app_state, TENANT, job_id)
    assert len(ko.poster) == 3

    assert await storage.set_korning_styrning(TID, job_id, "avbruten")
    for post in list(ko.poster):
        await _kor_barn(app_state, post)
        assert await storage.get_leads_job_status(TID, post["job_id"]) == "failed"

    rad = await storage.get_leads_korning(TID, job_id)
    assert rad["status"] == "completed"
    k = rad["korning"]
    assert k["klar"] and k["slut_orsak"] == "avbruten"
    assert k["undersokta"] == 0 and k["pagaende"] == 0 and k["levererade"] == 0
    # En avslutad körning går inte att styra längre (endpointens 409).
    assert not await storage.set_korning_styrning(TID, job_id, None)


async def test_helskrivning_nollar_inte_styrningen():
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await _ny_korning(storage, ["Ett AB"])
    gammal = await _k(storage, job_id)  # läst FÖRE pausen, som motorn gör
    gammal.pop("styrning", None)
    assert await storage.set_korning_styrning(TID, job_id, "paus")
    await leads_api._spara_korning(app_state, TID, job_id, gammal)
    assert (await _k(storage, job_id))["styrning"] == "paus"


async def test_dubbel_rapport_raknas_en_gang():
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await _ny_korning(storage, [])
    k = await _k(storage, job_id)
    k.update(pagaende=2, mal=5)
    await storage.set_leads_job_status(TID, job_id=job_id, status="processing", scope="batch", korning=k)
    for _ in range(2):
        await leads_api._rapportera_till_korning(
            app_state, TENANT, job_id, job_id="barn-1", namn="Ett AB", leverbar=True, skal=None, fyll=False
        )
    k = await _k(storage, job_id)
    assert k["pagaende"] == 1 and k["undersokta"] == 1 and k["levererade"] == 1


async def test_atertaget_completed_barn_vacker_korningen(monkeypatch):
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    await storage.set_leads_job_status(TID, job_id="barn-1", status="completed", scope="research", prospect_id="p1")
    vackta: list[str] = []

    async def _vacka(_state, _tenant, batch_id):
        vackta.append(batch_id)

    monkeypatch.setattr(leads_api, "_vacka_korning", _vacka)
    await leads_api.hantera_leads_jobb(
        app_state,
        {"job_id": "barn-1", **TENANT, "prospect_id": "p1", "scope": "research", "batch_id": "batch-x"},
    )
    assert vackta == ["batch-x"]


async def test_stadaren_mater_tystnad_inte_alder():
    storage = MemoryStorage()
    await storage.set_leads_job_status(TID, job_id="gammal-men-levande", status="processing", scope="batch")
    rad = storage.leads_job_ledger["gammal-men-levande"]
    rad["created_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    assert await storage.stada_hangande_leadsjobb(TID, aldre_an_minuter=60) == []
    rad["updated_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assert await storage.stada_hangande_leadsjobb(TID, aldre_an_minuter=60) == ["gammal-men-levande"]


async def test_hjartslaget_hindrar_overtag(monkeypatch):
    monkeypatch.setattr(stream_mod, "HJARTSLAG_S", 0.05)
    monkeypatch.setattr(stream_mod, "MIN_IDLE_MS", 150)
    client = fakeredis_aio.FakeRedis(decode_responses=True)
    strom = ChattStrom(client, stream_key="test:hjartslag")
    await strom.enqueue({"job_id": "j1"})
    korda: list[str] = []

    async def _langsam(payload):
        korda.append("a")
        await asyncio.sleep(0.5)

    async def _syskon(payload):
        korda.append("b")

    forsta = asyncio.create_task(strom.kor_ett_varv("process-a", _langsam))
    for _ in range(6):
        await asyncio.sleep(0.08)
        assert await strom.atertag(_syskon, konsument="process-b") == 0
    await forsta
    assert korda == ["a"]
    await client.aclose()


async def test_hjartslaget_haller_hela_batchen_vid_liv(monkeypatch):
    """Ett varv läser flera poster och kör dem en i taget. De som väntar på
    sin tur fick förut inget hjärtslag och togs över av ett syskon: samma
    lead researchades och fick utkast tre gånger (development 2026-10-08)."""
    monkeypatch.setattr(stream_mod, "READ_COUNT", 3)  # flera poster per läsning
    monkeypatch.setattr(stream_mod, "HJARTSLAG_S", 0.05)
    monkeypatch.setattr(stream_mod, "MIN_IDLE_MS", 150)
    client = fakeredis_aio.FakeRedis(decode_responses=True)
    strom = ChattStrom(client, stream_key="test:hjartslag-batch")
    for jobb in ("j1", "j2", "j3"):
        await strom.enqueue({"job_id": jobb})
    korda: list[str] = []

    async def _langsam(payload):
        korda.append(f"a:{payload['job_id']}")
        await asyncio.sleep(0.3)

    async def _syskon(payload):
        korda.append(f"b:{payload['job_id']}")

    forsta = asyncio.create_task(strom.kor_ett_varv("process-a", _langsam))
    for _ in range(10):
        await asyncio.sleep(0.08)
        assert await strom.atertag(_syskon, konsument="process-b") == 0
    await forsta
    assert korda == ["a:j1", "a:j2", "a:j3"]
    await client.aclose()


async def test_ett_klart_bolag_rapporterar_medan_sokrundan_pagar(monkeypatch):
    """Sökrundan höll körningens lås i minuter, och varje bolag som blev klart
    under tiden fastnade på rapporten: dess worker stod still och körningen
    tog en kvart (development 2026-10-09). Rundan körs nu utanför låset."""
    _installera(monkeypatch)
    rundan_startad = asyncio.Event()
    slapp_rundan = asyncio.Event()

    async def _langsam_runda(*_a, **_k):
        rundan_startad.set()
        await slapp_rundan.wait()
        return [_bolag("Nytt Från Rundan AB")]

    monkeypatch.setattr(korningsmodul, "hitta_bolag", _langsam_runda)
    monkeypatch.setattr(korningsmodul, "har_malgrupp", lambda *_a: True)
    storage, ko = MemoryStorage(), _Kö()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=ko)
    job_id = await _ny_korning(storage, ["Ett AB"])
    k = await _k(storage, job_id)
    k["mal"] = 3  # ett i poolen, två till ska sökas fram
    await storage.set_leads_job_status(TID, job_id=job_id, status="processing", scope="batch", korning=k, is_test=True)

    fyll = asyncio.create_task(leads_api._fyll_pa(app_state, TENANT, job_id))
    await asyncio.wait_for(rundan_startad.wait(), timeout=2)
    assert len(ko.poster) == 1 and (await _k(storage, job_id)).get("soker_sedan")

    # Barnet blir klart medan rundan pågår: rapporten får inte vänta ut den.
    await asyncio.wait_for(_kor_barn(app_state, ko.poster[0]), timeout=2)
    assert (await _k(storage, job_id))["levererade"] == 1

    slapp_rundan.set()
    await asyncio.wait_for(fyll, timeout=5)
    k = await _k(storage, job_id)
    assert "soker_sedan" not in k and k["rundor"] >= 1
    assert any(p.get("prospect_id") for p in ko.poster[1:]), "rundans fynd köades efter inslagningen"


async def test_varje_worker_tar_ett_jobb_i_taget(monkeypatch):
    """Med READ_COUNT 10 tog första workern tio köade jobb och körde dem i
    följd medan de andra stod still (development 2026-10-09: 25 köade
    researchjobb, 2–3 åt gången). Två workers ska köra två jobb samtidigt."""
    client = fakeredis_aio.FakeRedis(decode_responses=True)
    strom = ChattStrom(client, stream_key="test:ett-i-taget")
    for jobb in ("j1", "j2", "j3", "j4"):
        await strom.enqueue({"job_id": jobb})
    samtidigt = 0
    toppen = 0

    async def _jobb(payload):
        nonlocal samtidigt, toppen
        samtidigt += 1
        toppen = max(toppen, samtidigt)
        await asyncio.sleep(0.1)
        samtidigt -= 1

    await asyncio.gather(*(strom.kor_ett_varv(f"w{i}", _jobb) for i in range(4)))
    assert toppen == 4
    await client.aclose()


async def test_en_igangvarande_korning_falls_inte_nar_dess_post_ges_upp(monkeypatch):
    """Tre deployer under en lång sökrunda gav körningsposten tre leveranser,
    och hela körningen märktes misslyckad medan 20 av dess bolag fortfarande
    researchades (development 2026-10-09)."""
    _installera(monkeypatch)
    storage, ko = MemoryStorage(), _Kö()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=ko)
    job_id = await _ny_korning(storage, ["Ett AB", "Två AB"])
    await leads_api._fyll_pa(app_state, TENANT, job_id)
    assert len(ko.poster) == 2

    await leads_api.ge_upp_leadsjobb(app_state, {"job_id": job_id, "tenant_id": TID, "kind": "batch"})
    rad = await storage.get_leads_korning(TID, job_id)
    assert rad["status"] == "processing" and not rad.get("error")
    for post in list(ko.poster):
        await _kor_barn(app_state, post)
    rad = await storage.get_leads_korning(TID, job_id)
    assert rad["status"] == "completed" and rad["korning"]["levererade"] == 2


async def test_sokmarke_fran_en_dod_process_galler_inte():
    k = {"soker_sedan": datetime.now(timezone.utc).isoformat(), "soker_process": "annan-vard:123"}
    assert leads_api._soker(k) is False
    from app.jobs.stream import consumer_name

    assert leads_api._soker({**k, "soker_process": consumer_name()}) is True


async def test_stillastaende_korning_vacks(monkeypatch):
    """En körning vars sökrunda dog med processen (en deploy mitt i en
    återupptagning) stod i Pågår tills städaren fällde den (2026-10-09).
    Väckaren puttar på den, och en färdig körning avslutas."""
    _installera(monkeypatch)
    storage, ko = MemoryStorage(), _Kö()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=ko)
    storage.tenants[TID] = {"id": TID, "name": "Testbolaget"}
    job_id = await _ny_korning(storage, ["Ett AB"])
    k = await _k(storage, job_id)
    k["soker_sedan"] = datetime.now(timezone.utc).isoformat()
    k["soker_process"] = "dod-process:1"
    await storage.set_leads_job_status(TID, job_id=job_id, status="processing", scope="batch", korning=k, is_test=True)

    assert await leads_api.vack_stillastaende_korningar(app_state) == 1
    for _ in range(20):
        await asyncio.sleep(0)
    assert len(ko.poster) == 1, "väckningen köade körningens kandidat"
    # Medan bolaget researchas finns inget att väcka.
    assert await leads_api.vack_stillastaende_korningar(app_state) == 0


async def test_poolen_kor_parallellt_med_en_lasare(monkeypatch):
    """En läsare och en pool (2026-10-09): tio blockerande läsare slog i
    Redis anslutningstak. Poolen ska ändå köra jobben samtidigt, och ett
    jobb som faller ska ligga kvar för återtag i stället för att fälla poolen."""
    monkeypatch.setattr(stream_mod, "BLOCK_MS", 20)  # fakeredis blockerar slingan under BLOCK
    client = fakeredis_aio.FakeRedis(decode_responses=True)
    strom = ChattStrom(client, stream_key="test:pool")
    for jobb in ("j1", "j2", "j3", "j4", "trasig"):
        await strom.enqueue({"job_id": jobb})
    samtidigt = toppen = 0
    klara: list[str] = []
    fallit = asyncio.Event()

    async def _jobb(payload):
        nonlocal samtidigt, toppen
        if payload["job_id"] == "trasig":
            fallit.set()
            raise RuntimeError("fel")
        samtidigt += 1
        toppen = max(toppen, samtidigt)
        await asyncio.sleep(0.2)
        samtidigt -= 1
        klara.append(payload["job_id"])

    pool = asyncio.create_task(strom.worker_pool("pool-a", _jobb, 4))
    for _ in range(40):
        await asyncio.sleep(0.05)
        if len(klara) == 4 and fallit.is_set():
            break
    await asyncio.sleep(0.05)  # låt det trasiga jobbets task avsluta
    pool.cancel()
    try:
        await pool
    except asyncio.CancelledError:
        pass
    assert sorted(klara) == ["j1", "j2", "j3", "j4"] and toppen == 4
    pending = await client.xpending(strom.stream_key, strom.group)
    assert pending["pending"] == 1, "det trasiga jobbet ligger kvar för återtag"
    await client.aclose()
