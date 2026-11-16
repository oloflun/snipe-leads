"""Sändplanen (Sebbe 2026-11-16): listan visar när varje godkänt utkast går ut
enligt kön, i stället för "skickas 08:00" om alla tusentals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.leads import sandplan, utkaststatus
from app.leads.sandplan import planera
from app.leads.timing_gate import STOCKHOLM
from app.storage.memory import MemoryStorage
from tests.leads.test_scheduler import TENANT, _seed

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _ko(antal: int, *, sedan: datetime) -> list[dict]:
    return [{"id": f"q{i}", "scheduled_at": sedan + timedelta(minutes=i)} for i in range(antal)]


def _lokal(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(STOCKHOLM)


# Måndag 2026-11-16, svensk tid.
MANDAG_0727 = datetime(2026, 11, 16, 6, 27, tzinfo=timezone.utc)
MANDAG_2100 = datetime(2026, 11, 16, 20, 0, tzinfo=timezone.utc)
FREDAG_1700 = datetime(2026, 11, 20, 16, 0, tzinfo=timezone.utc)


def test_aldst_forst_ett_i_minuten_fran_0800_med_upptrappningen():
    ko = _ko(55 + 60 + 1, sedan=MANDAG_0727 - timedelta(days=20))
    plan = planera(ko, now=MANDAG_0727, skickade_idag=0, storsta_dagsvolym=50, alder_dagar=365)
    forsta, femtiofemte, nasta = _lokal(plan["q0"]), _lokal(plan["q54"]), _lokal(plan["q55"])
    assert (forsta.date().isoformat(), forsta.strftime("%H:%M")) == ("2026-11-16", "08:00")
    assert femtiofemte.strftime("%H:%M") == "08:54"  # dagens tak 55, ett i minuten
    assert (nasta.date().isoformat(), nasta.strftime("%H:%M")) == ("2026-11-17", "08:00")
    # Tisdagens tak är 60 (fem fler än måndagens 55).
    assert _lokal(plan["q114"]).date().isoformat() == "2026-11-17"
    assert _lokal(plan["q115"]).date().isoformat() == "2026-11-18"


def test_kvallens_godkannanden_gar_nasta_vardag_och_helgen_hoppas_over():
    assert _lokal(planera(_ko(1, sedan=MANDAG_2100), now=MANDAG_2100, skickade_idag=50,
                          storsta_dagsvolym=50, alder_dagar=365)["q0"]).strftime("%Y-%m-%d %H:%M") == "2026-11-17 08:00"
    assert _lokal(planera(_ko(1, sedan=FREDAG_1700), now=FREDAG_1700, skickade_idag=0,
                          storsta_dagsvolym=50, alder_dagar=365)["q0"]).strftime("%Y-%m-%d %H:%M") == "2026-11-23 08:00"


def test_taket_stannar_vid_100():
    ko = _ko(2000, sedan=MANDAG_0727 - timedelta(days=30))
    plan = planera(ko, now=MANDAG_0727, skickade_idag=0, storsta_dagsvolym=95, alder_dagar=365)
    per_dag: dict[str, int] = {}
    for iso in plan.values():
        dag = _lokal(iso).date().isoformat()
        per_dag[dag] = per_dag.get(dag, 0) + 1
    assert list(per_dag.values())[:3] == [100, 100, 100]
    assert len(plan) == 2000


def test_redan_skickat_i_dag_raknas_av():
    plan = planera(_ko(3, sedan=MANDAG_0727), now=datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc),
                   skickade_idag=54, storsta_dagsvolym=50, alder_dagar=365)
    assert _lokal(plan["q0"]).strftime("%Y-%m-%d %H:%M") == "2026-11-16 10:01"
    assert _lokal(plan["q1"]).date().isoformat() == "2026-11-17"


def test_ett_utkast_schemalagt_senare_far_sin_egen_tid():
    ko = [{"id": "q0", "scheduled_at": datetime(2026, 11, 19, 9, 30, tzinfo=timezone.utc)}]
    plan = planera(ko, now=MANDAG_0727, skickade_idag=0, storsta_dagsvolym=50, alder_dagar=365)
    assert _lokal(plan["q0"]).strftime("%Y-%m-%d %H:%M") == "2026-11-19 10:30"


async def test_listan_visar_planens_tid_for_ett_godkant_utkast():
    storage = MemoryStorage()
    item_id, _, _ = _seed(storage, scheduled_at=MANDAG_0727 - timedelta(days=5))
    post = storage.send_queue[TENANT][-1]
    post["gate_checks"] = {"approved_by": "human"}
    plan = await sandplan.for_kund(storage, TENANT, now=MANDAG_2100)
    assert list(plan) == [item_id]
    lage = {"ko_status": "queued", "queue_item_id": item_id, "gate_checks": post["gate_checks"],
            "scheduled_at": post["scheduled_at"].isoformat()}
    ut = utkaststatus.harled(lage, now=MANDAG_2100, plan=plan)
    assert ut["utkast_status"] == "godkant"
    assert _lokal(ut["skickas_tidigast"]).strftime("%Y-%m-%d %H:%M") == "2026-11-17 08:00"
