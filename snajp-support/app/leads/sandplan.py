"""När varje godkänt utkast går ut (Sebbe 2026-11-16).

## Varför

Listan sa "Godkänt – skickas 08:00" om vart och ett av 3 868 godkända utkast,
fast sändaren skickar högst dagens tak om dagen, äldst först. Kvällens
körningar såg ut att ligga och vänta, och det gick inte att se när de
faktiskt skulle gå. Planen här lägger kön på dagarna så som sändaren
(`scheduler.process_godkanda`) tar den: äldst först, ett mejl i minuten från
08:00, dagens tak med upptrappningen (`send_guard.dagens_tak`), bara på
vardagar i kallmejlsfönstret.

Det är en uppskattning: ett utkast som stoppas av en spärr (karens,
suppression) eller ett svar som skickas emellan flyttar resten en plats.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .send_guard import TAK_PER_DAG, UPPTRAPPNING_STEG, UPPVARMNING_DAGAR, UPPVARMNING_TAK_PER_DAG
from .timing_gate import COLD_OUTREACH_END_HOUR, STOCKHOLM, WINDOW_START_HOUR, is_blocked_day

#: Sändarens takt: ett mejl per kund och varv (scheduler.TAKT_SEKUNDER, varvet
#: är en minut).
MINUTER_PER_MEJL = 1

#: Planen räknas högst så här många sändardagar fram; resten får ingen tid.
MAX_DAGAR = 400


def _tak(storsta: int, alder_dagar: int) -> int:
    if alder_dagar < UPPVARMNING_DAGAR:
        return UPPVARMNING_TAK_PER_DAG
    return min(TAK_PER_DAG, max(UPPVARMNING_TAK_PER_DAG, storsta + UPPTRAPPNING_STEG))


def _tid(varde: Any) -> datetime | None:
    from .utkaststatus import _tid as tolka

    return tolka(varde)


def planera(
    ko: list[dict[str, Any]],
    *,
    now: datetime,
    skickade_idag: int,
    storsta_dagsvolym: int,
    alder_dagar: int,
) -> dict[str, str]:
    """{köpostens id: planerad sändtid (ISO)} för kön i sändordning.

    `ko` är de godkända köposterna (`id`, `scheduled_at`) äldst först, som
    `storage.godkand_ko_ordning` ger dem."""
    plan: dict[str, str] = {}
    if not ko:
        return plan
    lokal = now.astimezone(STOCKHOLM)
    dag = lokal.replace(hour=WINDOW_START_HOUR, minute=0, second=0, microsecond=0)
    storsta = storsta_dagsvolym
    alder = alder_dagar
    skickade = skickade_idag
    start = max(dag, lokal.replace(second=0, microsecond=0) + timedelta(minutes=1))
    i = 0
    for _ in range(MAX_DAGAR):
        stang = dag.replace(hour=COLD_OUTREACH_END_HOUR)
        if not is_blocked_day(dag) and start < stang:
            tak = _tak(storsta, alder)
            platser = min(max(0, tak - skickade), int((stang - start).total_seconds() // 60) // MINUTER_PER_MEJL)
            tid = start
            for _ in range(platser):
                if i >= len(ko):
                    return plan
                post = ko[i]
                tidigast = _tid(post.get("scheduled_at"))
                nar = tid
                if tidigast is not None and tidigast.astimezone(STOCKHOLM) > nar:
                    nar = tidigast.astimezone(STOCKHOLM)
                plan[str(post["id"])] = nar.isoformat()
                i += 1
                skickade += 1
                tid += timedelta(minutes=MINUTER_PER_MEJL)
            # En full dag höjer nästa dags tak (största dagsvolymen i fönstret).
            storsta = max(storsta, skickade)
        dag = (dag + timedelta(days=1)).replace(hour=WINDOW_START_HOUR)
        alder += 1
        skickade = 0
        start = dag
    return plan


async def for_kund(storage, tenant_id: str, *, now: datetime) -> dict[str, str]:
    """Planen för kundens kö. Tom vid fel: listan ska visas ändå, och
    utkaststatus faller då tillbaka på nästa sändfönster."""
    import logging

    from .scheduler import kundens_historik

    try:
        ko = await storage.godkand_ko_ordning(tenant_id)
        if not ko:
            return {}
        historik = await kundens_historik(storage, tenant_id, now=now)
    except Exception:  # noqa: BLE001
        logging.getLogger("snajp-support.sandplan").exception("Sändplanen kunde inte räknas för %s.", tenant_id)
        return {}
    return planera(
        ko,
        now=now,
        skickade_idag=historik.skickade_idag,
        storsta_dagsvolym=historik.storsta_dagsvolym,
        alder_dagar=historik.tenant_alder_dagar,
    )
