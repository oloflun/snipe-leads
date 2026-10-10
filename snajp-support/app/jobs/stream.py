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
#: EN post per läsning (2026-10-09). Med 10 tog första workern tio köade
#: jobb och körde dem ett i taget medan de andra stod sysslolösa: en körning
#: som köade 25 researchjobb researchade 2–3 åt gången oavsett antalet
#: workers. Med 1 tar varje worker nästa jobb, och N workers kör N jobb.
READ_COUNT = 1

#: Tak för hur många gånger EN post får levereras (första läsningen +
#: återtag) innan atertag() ger upp och kvitterar den oprövad. Hängslen
#: ovanpå INV-JOB-002-liggaren: skulle vakten i hanteraren någonsin missa
#: blir en post som kraschar sin hanterare på varje försök inte en evig
#: omkörningsmaskin — tre leveranser är två återtag mer än ett friskt jobb
#: någonsin behöver.
MAX_LEVERANSER = 3

#: Hjärtslag medan hanteraren kör: XCLAIM till sig själv nollar postens
#: idle-tid. Utan det mätte MIN_IDLE_MS tid sedan LEVERANSEN, inte sedan
#: senaste livstecknet, och en research som tog mer än 60 s togs över av en
#: syskonprocess (överlappet vid en Railway-deploy) och kördes två gånger
#: parallellt. Dör processen tystnar hjärtslaget och återtaget sker som förut.
#:
#: Hela batchen bär hjärtslag, inte bara posten som körs (2026-10-08): ett
#: varv läser upp till READ_COUNT poster och kör dem en i taget, så post två
#: till tio låg tysta medan den första researchades. Efter MIN_IDLE_MS tog en
#: syskonkonsument över dem och samma lead researchades och fick utkast tre
#: gånger inom fem sekunder (uppmätt i development: 21 jobb, 29 utkast).
HJARTSLAG_S = 20


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
        self,
        client: Any,
        *,
        stream_key: str = STREAM_KEY,
        group: str = GROUP_NAME,
        vid_uppgivet: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.client = client
        # Anropas med postens nyttolast när atertag() ger upp den efter
        # MAX_LEVERANSER, FÖRE kvitteringen. Utan den kvitterades posten tyst
        # och jobbet stod kvar i processing i alla lager som inte har en egen
        # tidsgräns (leads_job_ledger, lead_lists) — för evigt. None = gamla
        # beteendet (chattens jobbpost auto-failar ändå efter 300 s).
        self.vid_uppgivet = vid_uppgivet
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
        namn: str | None = None,
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
        hjartslag = asyncio.create_task(self._hjartslag(msg_id, namn or consumer_name()))
        try:
            await hanterare(payload)
        finally:
            hjartslag.cancel()
        await self.client.xack(self.stream_key, self.group, msg_id)

    async def _hjartslag(self, msg_id: str | set[str], namn: str) -> None:
        """Se HJARTSLAG_S. JUSTID: räknar inte upp leveransräknaren, så
        MAX_LEVERANSER fortsätter räkna riktiga omleveranser. En mängd är
        batchens poster som ännu inte kvitterats; den krymper medan varvet
        kör, och slaget gäller det som är kvar."""
        while True:
            await asyncio.sleep(HJARTSLAG_S)
            ids = sorted(msg_id) if isinstance(msg_id, set) else [msg_id]
            if not ids:
                continue
            try:
                await self.client.xclaim(
                    self.stream_key, self.group, namn, min_idle_time=0,
                    message_ids=ids, justid=True,
                )
            except Exception:  # noqa: BLE001 — ett missat slag ger i värsta fall ett återtag
                logger.warning("Ström %s: hjärtslaget för %s misslyckades.", self.stream_key, ids)

    async def _kor_batch(
        self,
        meddelanden: list,
        hanterare: Callable[[dict[str, Any]], Awaitable[None]],
        namn: str,
    ) -> int:
        """Kör en batch i ordning medan hela resten av batchen hålls vid liv
        (se HJARTSLAG_S). Returnerar antal körda poster."""
        kvar = {msg_id for msg_id, _falt in meddelanden}
        slag = asyncio.create_task(self._hjartslag(kvar, namn))
        antal = 0
        try:
            for msg_id, falt in meddelanden:
                await self._kor_och_kvittera(msg_id, falt, hanterare, namn)
                kvar.discard(msg_id)
                antal += 1
        finally:
            slag.cancel()
        return antal

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
            antal += await self._kor_batch(meddelanden, hanterare, namn)
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
                await self.atertag(hanterare, konsument=namn, max_antal=1)
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

    async def _nasta_post(self, namn: str) -> tuple[str, dict[str, str]] | None:
        """Nästa post för poolen: ett övergivet jobb (XAUTOCLAIM, en post),
        annars ett nytt (XREADGROUP, en post, blockerar högst BLOCK_MS).
        En post som levererats för många gånger ges upp här, som i atertag.
        None = inget att göra just nu."""
        _cursor, meddelanden, *_ = await self.client.xautoclaim(
            self.stream_key, self.group, namn, min_idle_time=MIN_IDLE_MS, start_id="0-0", count=1
        )
        if meddelanden:
            msg_id, falt = meddelanden[0]
            leveranser = await self._leveransantal()
            if leveranser.get(msg_id, 0) > MAX_LEVERANSER:
                logger.warning(
                    "Ström %s: posten %s har levererats %s gånger — ger upp och kvitterar (tak %s).",
                    self.stream_key, msg_id, leveranser[msg_id], MAX_LEVERANSER,
                )
                if self.vid_uppgivet is not None:
                    try:
                        await self.vid_uppgivet(self._packa_upp(falt))
                    except Exception:  # noqa: BLE001 — kvitteringen ska ske ändå
                        logger.exception("Ström %s: vid_uppgivet kastade för %s.", self.stream_key, msg_id)
                await self.client.xack(self.stream_key, self.group, msg_id)
                return None
            return msg_id, falt
        svar = await self.client.xreadgroup(
            self.group, namn, {self.stream_key: ">"}, count=1, block=BLOCK_MS
        )
        for _stream_namn, nya in svar or []:
            for msg_id, falt in nya:
                return msg_id, falt
        return None

    async def worker_pool(
        self, namn: str, hanterare: Callable[[dict[str, Any]], Awaitable[None]], antal: int
    ) -> None:
        """EN läsare och `antal` samtidiga jobb (2026-10-09).

        Med en worker_loop per worker höll varje worker en egen anslutning i
        en blockerande XREADGROUP. Med 10 leadsworkers och 4 chattworkers
        (och två processer under en deploy) slog det i Redis anslutningstak
        ("max number of clients reached") och en körning fälldes. Nu läser en
        enda läsare en post i taget när det finns en ledig plats, och jobben
        körs som egna tasks: en blockerande anslutning per ström och process.
        Hjärtslag, kvittering och uppgivning är desamma som förut."""
        await self._sakerstall_grupp()
        platser = asyncio.Semaphore(max(antal, 1))
        pagaende: set[asyncio.Task] = set()

        async def kor(msg_id: str, falt: dict[str, str]) -> None:
            try:
                await self._kor_och_kvittera(msg_id, falt, hanterare, namn)
            except Exception:  # noqa: BLE001 — posten ligger kvar okvitterad och tas om
                logger.exception("Ström %s: jobbet %s föll — tas om efter MIN_IDLE_MS.", self.stream_key, msg_id)
            finally:
                platser.release()

        try:
            while True:
                await platser.acquire()
                try:
                    post = await self._nasta_post(namn)
                except asyncio.CancelledError:
                    platser.release()
                    raise
                except Exception:  # noqa: BLE001 — läsaren får aldrig dö av en Redis-hicka
                    platser.release()
                    logger.exception("Ström %s: fel i läsaren (%s) — försöker igen om en sekund.", self.stream_key, namn)
                    await asyncio.sleep(1)
                    continue
                if post is None:
                    platser.release()
                    # En kort paus efter en tom läsning: en klient som svarar
                    # utan att släppa händelseslingan (fakeredis) hade annars
                    # svält ut jobben. I drift har läsningen redan väntat BLOCK_MS.
                    await asyncio.sleep(0.05)
                    continue
                task = asyncio.create_task(kor(*post))
                pagaende.add(task)
                task.add_done_callback(pagaende.discard)
        except asyncio.CancelledError:
            for task in pagaende:
                task.cancel()
            raise

    async def _leveransantal(self) -> dict[str, int]:
        """message_id -> times_delivered för gruppens pending-poster.

        Läses via XPENDING (range-varianten) precis före ett återtagsvarv —
        XAUTOCLAIM själv rapporterar inte leveransräknaren. Defensiv: kan
        räknaren inte läsas (äldre fakeredis, Redis-hicka) returneras tomt
        och taket appliceras helt enkelt inte det varvet — hängslen ska
        aldrig fälla själva byxorna."""
        try:
            pending = await self.client.xpending_range(
                self.stream_key, self.group, min="-", max="+", count=MAXLEN_APPROX
            )
        except Exception:  # noqa: BLE001 — se docstringen: taket är frivilligt, körningen inte
            logger.exception("Ström %s: kunde inte läsa XPENDING — hoppar leveranstaket.", self.stream_key)
            return {}
        antal: dict[str, int] = {}
        for post in pending:
            # redis-py returnerar dictar; äldre varianter tuples (id, consumer,
            # idle, deliveries). Båda formerna hanteras.
            if isinstance(post, dict):
                antal[str(post.get("message_id"))] = int(post.get("times_delivered") or 0)
            else:
                antal[str(post[0])] = int(post[3])
        return antal

    async def atertag(
        self,
        hanterare: Callable[[dict[str, Any]], Awaitable[None]],
        *,
        konsument: str | None = None,
        max_antal: int | None = None,
    ) -> int:
        """Tar över poster som legat okvitterade längre än MIN_IDLE_MS
        (XAUTOCLAIM) och kör om dem. Returnerar antal återtagna poster.

        `max_antal` (worker_loop: 1): ta högst så många per svep, så att
        övergivna jobb efter en omstart fördelas över alla workers i stället
        för att en worker tar alla och kör dem i följd.

        `konsument` defaultar till den här processens eget namn — de
        återtagna posterna övergår alltså till "min" identitet i gruppen,
        oavsett vem som ursprungligen läste dem.
        """
        await self._sakerstall_grupp()
        agent = konsument or consumer_name()
        antal = 0
        cursor = "0-0"
        while True:
            extra = {"count": max_antal - antal} if max_antal else {}
            cursor, meddelanden, _borttagna = await self.client.xautoclaim(
                self.stream_key, self.group, agent, min_idle_time=MIN_IDLE_MS, start_id=cursor, **extra
            )
            leveranser = await self._leveransantal() if meddelanden else {}
            att_kora = []
            for msg_id, falt in meddelanden:
                if leveranser.get(msg_id, 0) > MAX_LEVERANSER:
                    logger.warning(
                        "Ström %s: posten %s har levererats %s gånger — ger upp och "
                        "kvitterar utan körning (tak %s).",
                        self.stream_key,
                        msg_id,
                        leveranser[msg_id],
                        MAX_LEVERANSER,
                    )
                    if self.vid_uppgivet is not None:
                        try:
                            await self.vid_uppgivet(self._packa_upp(falt))
                        except Exception:  # noqa: BLE001 — kvitteringen ska ske ändå, annars snurrar posten
                            logger.exception(
                                "Ström %s: vid_uppgivet kastade för posten %s — kvitterar ändå.",
                                self.stream_key,
                                msg_id,
                            )
                    await self.client.xack(self.stream_key, self.group, msg_id)
                    continue
                att_kora.append((msg_id, falt))
            # De återtagna körs i ordning, med hjärtslag för hela svepet: annars
            # tog nästa syskon över dem medan den första kördes.
            antal += await self._kor_batch(att_kora, hanterare, agent)
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
            if cursor == "0-0" or not meddelanden or (max_antal and antal >= max_antal):
                break
        return antal
