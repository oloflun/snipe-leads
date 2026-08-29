"""Chattströmmen: gör en chattkörning ÖVERLEVANDE en deploy (Fas R1, bd snipe-lr7).

## Problemet

POST /api/chat körde agentkedjan som `asyncio.create_task` i SAMMA process
(se app/api/chat.py). En deploy dödar den processen mitt i körningen —
jobbposten i Redis (app/jobs/store.py) blir kvar som "processing" och
auto-failas efter JOB_TIMEOUT_SECONDS (300 s). Kunden får ett felmeddelande
i stället för sitt svar, trots att arbetet ofta redan var klart eller nästan
klart.

## Lösningen

Ett Redis-stream (`crm:jobb:chatt`) med EN consumer group (`agenter`).
`enqueue` lägger jobbet i strömmen i stället för att köra det i samma
process. `worker_loop` läser strömmen med XREADGROUP — vilken process i
klustret som helst kan ta jobbet, inte bara den som svarade på HTTP-anropet.
Dör en process mitt i ett jobb ligger posten kvar OKVITTERAD i gruppens
pending-lista tills `atertag` (XAUTOCLAIM) tar över den, och en annan
(eller samma, efter omstart) process kör om den.

Idempotensen som gör "kör om" säkert — i stället för att skapa ett andra
ärende av samma chattmeddelande — ligger INTE här. Den ligger i
app/agent/support_agent.py (`aterta`/`vid_arende`) och app/jobs/store.py
(`annotate`). Se INV-JOB-001 i ARCHITECTURE_INVARIANTS.md.

## Varför XAUTOCLAIM och inte XPENDING+XCLAIM

Båda vägarna fungerar mot riktig Redis. XAUTOCLAIM är EN kommando som gör
samma sak som tvåstegsvarianten, och fakeredis (testberoendet — se
requirements.txt) stödjer den direkt, verifierat i tests/test_chatt_strom.py.
Ingen anledning att skriva och underhålla tvåstegsvägen när enkommando-
varianten redan är bevisad att fungera i båda miljöerna.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from collections.abc import Awaitable, Callable
from typing import Any

from ..redisnycklar import nyckel

logger = logging.getLogger("snajp-support.jobs.stream")

STREAM_KEY = "crm:jobb:chatt"
GROUP_NAME = "agenter"

#: Approximativ trimning (XADD ... MAXLEN ~ N): exakt trimning kostar en
#: O(N)-genomsökning per XADD. Några hundra extra poster mellan trimningar
#: är ett billigt pris för att XADD förblir snabbt i en kö som kan ta emot
#: flera chattmeddelanden per sekund.
MAXLEN_APPROX = 1000

#: En post som legat oläst hos sin consument längre än detta räknas som
#: övergiven. 60 s och inte kortare: en agentkedja är sex-åtta LLM-anrop och
#: kan legitimt ta tiotals sekunder — ett för kort fönster hade tagit över
#: en körning som bara var LÅNGSAM, inte död, och kört den en gång till.
MIN_IDLE_MS = 60_000

#: Hur länge XREADGROUP väntar på nya poster innan den återvänder tom, så att
#: worker_loop får en chans att köra sitt periodiska återtagssvep även när
#: strömmen är tyst.
BLOCK_MS = 5_000
READ_COUNT = 10


def consumer_name(suffix: str | int | None = None) -> str:
    """Ett consumentnamn som är stabilt så länge PROCESSEN lever.

    hostname+pid: två processer på samma maskin (eller i samma miljö) får
    olika namn, och namnet ändras inte mellan varv i samma process — det är
    precis vad XAUTOCLAIM behöver för att kunna avgöra att en post legat kvar
    hos en consument som inte längre finns.

    `suffix` särskiljer flera worker-tasks INOM samma process (se
    app/main.py, som startar `chat_workers` stycken) utan att namnet slutar
    vara stabilt för den enskilda worker-tasken — den håller sitt suffix för
    hela sin livstid.
    """
    bas = f"{socket.gethostname()}:{os.getpid()}"
    return bas if suffix is None else f"{bas}:{suffix}"


class ChattStrom:
    """XADD/XREADGROUP-lager ovanpå EN delad `redis.asyncio`-klient.

    Klienten återanvänds från `RedisJobStore` (skapad i lifespan, se
    app/main.py) i stället för att öppna en egen anslutning — en anslutning
    mindre att övervaka i drift, och samma mönster som RedisJobStore redan
    använder.

    `stream_key`/`group` defaultar till chattens värden (STREAM_KEY/
    GROUP_NAME) så att INGET av chattens beteende ändras. Fas R4
    (bd snipe-2xj) återanvänder samma klass för leads-batchens ström
    (`crm:jobb:leads`) genom att skicka in ett annat par — samma XADD/
    XREADGROUP/XAUTOCLAIM-mekanik, två helt separata Redis-strömmar och
    consumer-grupper. Namnet `ChattStrom` behålls medvetet chattspecifikt
    (döps INTE om) så att befintliga importer (app/main.py, testsviten)
    förblir orörda — se modulens docstring om alias framför omdöpning.
    """

    def __init__(
        self, client: Any, *, stream_key: str = STREAM_KEY, group: str = GROUP_NAME
    ) -> None:
        self.client = client
        # Namnrymd per driftsättning. UTAN den stod produktionens och
        # spegelns containrar i SAMMA consumer group, och en grupp delar ut
        # varje post till exakt en konsument — ett kundjobb kunde alltså köras
        # av fel miljö, mot fel databas. Se app/redisnycklar.py.
        self.stream_key = nyckel(stream_key)
        self.group = group
        self._grupp_klar = False

    async def _sakerstall_grupp(self) -> None:
        """Skapar consumer-gruppen idempotent.

        `mkstream=True` eftersom strömmen kan saknas helt (första jobbet i en
        ny miljö). `BUSYGROUP` fångas uttryckligen — att gruppen redan finns
        är det FÖRVÄNTADE utfallet vid varje omstart efter den första, inte
        ett fel.
        """
        if self._grupp_klar:
            return
        try:
            await self.client.xgroup_create(self.stream_key, self.group, id="0", mkstream=True)
        except Exception as error:  # noqa: BLE001 — BUSYGROUP är vägen, inte ett fel
            if "BUSYGROUP" not in str(error):
                raise
        self._grupp_klar = True

    async def enqueue(self, payload: dict[str, Any]) -> str:
        """Lägger ETT jobb i strömmen (chatt- eller leadsjobb — se `stream_key`
        i __init__). Returnerar stream-ID:t."""
        await self._sakerstall_grupp()
        return await self.client.xadd(
            self.stream_key,
            {"payload": json.dumps(payload)},
            maxlen=MAXLEN_APPROX,
            approximate=True,
        )

    @staticmethod
    def _packa_upp(falt: dict[str, Any]) -> dict[str, Any]:
        return json.loads(falt["payload"])

    async def _kor_och_kvittera(
        self,
        msg_id: str,
        falt: dict[str, Any],
        hanterare: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Kör hanteraren och kvitterar (XACK) när den är KLAR.

        Hanteraren (app.api.chat.hantera_strom_jobb) fångar redan varje fel
        internt och märker jobbet failed i stället för att kasta — "ett
        hanterat fel är hanterat", och posten kvitteras då precis som en
        lyckad körning. XACK sker INTE om hanteraren själv kastar (en bugg,
        inte ett väntat agentfel): posten ligger kvar i pending och tas om av
        atertag() vid nästa svep, i stället för att tystas ned.

        Vid en RIKTIG processdöd (SIGKILL mitt i körningen, exakt scenariot
        det här hela modulen finns för) hinner varken hanteraren eller den
        här metoden köra klart alls — processen är helt enkelt borta, och
        posten blir kvar okvitterad av det skälet, inte av någon logik här.
        """
        try:
            payload = self._packa_upp(falt)
        except Exception:  # noqa: BLE001 — en trasig post ska inte fastna för evigt
            logger.exception(
                "Ström %s: kunde inte tolka posten %s — kvitterar ändå.", self.stream_key, msg_id
            )
            await self.client.xack(self.stream_key, self.group, msg_id)
            return
        await hanterare(payload)
        await self.client.xack(self.stream_key, self.group, msg_id)

    async def kor_ett_varv(
        self, namn: str, hanterare: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> int:
        """Läser och kör EN batch (upp till READ_COUNT poster) ur strömmen.

        Bruten ut ur worker_loop så att testsviten kan köra exakt ETT varv
        utan att starta hela evighetsloopen. Returnerar antal körda poster.
        """
        await self._sakerstall_grupp()
        svar = await self.client.xreadgroup(
            self.group, namn, {self.stream_key: ">"}, count=READ_COUNT, block=BLOCK_MS
        )
        if not svar:
            return 0
        antal = 0
        for _stream_namn, meddelanden in svar:
            for msg_id, falt in meddelanden:
                await self._kor_och_kvittera(msg_id, falt, hanterare)
                antal += 1
        return antal

    async def worker_loop(
        self, namn: str, hanterare: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Läser strömmen tills tasken avbryts (`task.cancel()` i teardown).

        Ett återtagssvep körs en gång PER VARV, utöver det engångssvep
        app/main.py kör innan några worker-tasks ens startas — så en process
        som dör mitt i natten återupptas av en levande syskonprocess inom en
        BLOCK_MS-cykel, inte bara vid nästa deploy.
        """
        await self._sakerstall_grupp()
        while True:
            try:
                await self.atertag(hanterare, konsument=namn)
                await self.kor_ett_varv(namn, hanterare)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — worker-loopen får aldrig dö av en enstaka Redis-hicka
                logger.exception(
                    "Ström %s: fel i worker-loopen (%s) — försöker igen om en sekund.",
                    self.stream_key,
                    namn,
                )
                await asyncio.sleep(1)

    async def atertag(
        self,
        hanterare: Callable[[dict[str, Any]], Awaitable[None]],
        *,
        konsument: str | None = None,
    ) -> int:
        """Tar över poster som legat okvitterade längre än MIN_IDLE_MS
        (XAUTOCLAIM) och kör om dem. Returnerar antal återtagna poster.

        `konsument` defaultar till den här processens eget namn — de
        återtagna posterna övergår alltså till "min" identitet i gruppen,
        oavsett vem som ursprungligen läste dem.
        """
        await self._sakerstall_grupp()
        agent = konsument or consumer_name()
        antal = 0
        cursor = "0-0"
        while True:
            cursor, meddelanden, _borttagna = await self.client.xautoclaim(
                self.stream_key, self.group, agent, min_idle_time=MIN_IDLE_MS, start_id=cursor
            )
            for msg_id, falt in meddelanden:
                await self._kor_och_kvittera(msg_id, falt, hanterare)
                antal += 1
            # Slutvillkor, TVÅ ben med flit. "0-0" är riktig Redis egen
            # signal att genomsökningen gått hela varvet — men fakeredis
            # (testberoendet) returnerar den ALDRIG efter en full
            # genomsökning: den fortsätter ge samma icke-"0-0"-cursor med en
            # TOM meddelandelista i evighet. Utan `not meddelanden` snurrar
            # den här loopen för alltid mot fakeredis (verifierat manuellt —
            # exakt det som fällde det första utkastet av det här testet).
            # Ofarligt mot riktig Redis: kommer noll poster tillbaka på ETT
            # varv finns inget AKUT att göra — nästa periodiska anrop (varje
            # varv i worker_loop) tar vid.
            if cursor == "0-0" or not meddelanden:
                break
        return antal
