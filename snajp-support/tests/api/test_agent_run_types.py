"""Regression: värdemängden för agent_runs.agent_type ska vara densamma i
minnet som i Postgres.

Buggen den här stänger: `leads_agent.py` skrev "leads_research" och
"leads_outreach", check-villkoret tillät bara 'support' och 'leads', och
MemoryStorage hade inget villkor alls. Testerna körde mot minnet och var
gröna medan produktionen kastade check-violation på varje leads-körning.
Ingen sådan körning har någonsin sparats.

Testet nedan kontrollerar två saker som tillsammans stänger fällan: att de
värden koden FAKTISKT skriver är tillåtna, och att ett otillåtet värde
faktiskt kastar i minnet också.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.storage.base import AGENT_RUN_TYPES
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _log(storage: MemoryStorage, agent_type: str):
    return await storage.log_agent_run(
        "tenant-a",
        agent_type=agent_type,
        pack_version="v1",
        skills_used=[],
        input_text="in",
        output_text="ut",
        step_log=[],
        tokens_in=0,
        tokens_out=0,
        latency_ms=1,
    )


@pytest.mark.parametrize("agent_type", AGENT_RUN_TYPES)
async def test_varje_tillaten_typ_gar_att_logga(agent_type):
    run = await _log(MemoryStorage(), agent_type)
    assert run["agent_type"] == agent_type


async def test_otillaten_typ_kastar_aven_i_minnet():
    """Utan det här hade minnet tagit emot tyst och Postgres kastat i drift —
    alltså exakt den asymmetri som gömde buggen."""
    with pytest.raises(ValueError, match="check-villkoret"):
        await _log(MemoryStorage(), "leads_prospecting")


def test_koden_skriver_bara_typer_som_finns_i_villkoret():
    """Läser de faktiska anropen i agentkoden i stället för att lita på att
    någon uppdaterar listan när ett nytt agent_type införs.

    Två mönster, inte ett. `agent_type="..."` fångar det direkta anropet, men
    bokföringsagenten skickar `agent_type=AGENT_TYPE` med värdet i en
    modulkonstant — och då hade det första mönstret inte sett någonting alls.
    Vaktposten hade slutat vakta för just den agenten, tyst, medan testet
    fortsatte vara grönt. Samma klass av fel som den bugg testet finns för.
    """
    written: set[str] = set()
    for source in (BACKEND / "app" / "agent").glob("*.py"):
        text = source.read_text(encoding="utf-8")
        written.update(re.findall(r'agent_type=["\']([a-z_]+)["\']', text))
        written.update(
            re.findall(r'^AGENT_TYPE(?:\s*:\s*str)?\s*=\s*["\']([a-z_]+)["\']', text, re.MULTILINE)
        )

    assert written, "Hittade inga agent_type-skrivningar — testet mäter ingenting."
    okant = written - set(AGENT_RUN_TYPES)
    assert not okant, (
        f"Agentkoden skriver {sorted(okant)}, som inte finns i check-villkoret. "
        f"Mot Postgres kastar det check-violation och körningen sparas aldrig. "
        f"Lägg till värdet i AGENT_RUN_TYPES och i en migration — båda."
    )
