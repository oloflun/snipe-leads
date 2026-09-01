"""Jobbstore för async-mönstret (202 + polling), som i referensarkitekturen.

Multi-tenant: varje jobb märks med tenant_id vid skapandet och API-lagret
verifierar ägarskap vid polling. Redis används om REDIS_URL är satt; annars
in-memory med TTL. Jobb som fastnat längre än 5 minuter auto-failas.
"""

import json
import time
import uuid
from typing import Any

from ..redisnycklar import nyckel

JOB_TIMEOUT_SECONDS = 300
JOB_TTL_SECONDS = 3600

#: Fält som `get()` alltid skriver ut explicit (och som därför inte ska
#: dubbleras av den generiska extra-fält-spridningen nedan). "created" är
#: INTE med — det är den interna timeout-klockan och ska aldrig läcka ut i
#: ett API-svar, bara läsas av lagringslagret självt. "started" är samma
#: sorts intern klocka (satt av start(), se INV-JOB-002) och läcker inte
#: heller.
_BASFALT = {"status", "result", "error", "tenant_id", "created", "started"}


class MemoryJobStore:
    name = "memory"

    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}

    def _sweep(self) -> None:
        now = time.time()
        for job_id in list(self.jobs):
            job = self.jobs[job_id]
            if now - job["created"] > JOB_TTL_SECONDS:
                del self.jobs[job_id]
            # Timeout-klockan räknar från "started" när den finns (satt av
            # start() när arbetet FAKTISKT börjar), annars från "created" —
            # chattjobb skapas som "processing" utan start() och behåller
            # därmed exakt sitt gamla beteende. Ett "queued"-jobb (leads i
            # kö bakom en sekventiell worker, se INV-JOB-002) auto-failas
            # aldrig av att det VÄNTAR — kötid är inte arbetstid.
            elif job["status"] == "processing" and now - job.get(
                "started", job["created"]
            ) > JOB_TIMEOUT_SECONDS:
                job["status"] = "failed"
                job["error"] = "Tidsgräns överskriden (5 min)."

    async def create(self, *, tenant_id: str | None = None, status: str = "processing") -> str:
        self._sweep()
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "status": status,
            "created": time.time(),
            "result": None,
            "tenant_id": tenant_id,
        }
        return job_id

    async def start(self, job_id: str) -> None:
        """Markerar att arbetet FAKTISKT börjar: status processing och en
        egen startklocka för 300-sekundersgränsen. Utan den räknade gränsen
        från köandet — och leads-jobb nr 5+ i en sekventiell batch hann
        auto-failas innan sitt första LLM-anrop (se INV-JOB-002)."""
        if job_id in self.jobs:
            self.jobs[job_id].update(status="processing", started=time.time())

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        if job_id in self.jobs:
            self.jobs[job_id].update(status="completed", result=result)

    async def fail(self, job_id: str, error: str) -> None:
        if job_id in self.jobs:
            self.jobs[job_id].update(status="failed", error=error)

    async def annotate(self, job_id: str, **falt: Any) -> None:
        """Lägger till/uppdaterar godtyckliga fält på en jobbpost UTAN att
        röra status/result/error — t.ex. ticket_id/conversation_id (så en
        återupptagen körning vet vilket ärende den ska fortsätta på) eller
        created (så återtagsvägen kan flytta 300-sekundersklockan, se
        INV-JOB-001 i ARCHITECTURE_INVARIANTS.md)."""
        if job_id in self.jobs:
            self.jobs[job_id].update(falt)

    async def get(self, job_id: str) -> dict[str, Any] | None:
        self._sweep()
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            "status": job["status"],
            "result": job.get("result"),
            "error": job.get("error"),
            "tenant_id": job.get("tenant_id"),
            # Extra fält (ticket_id, conversation_id, ...) satta via annotate()
            # följer med rakt av — se INV-JOB-001. "created" är internt
            # (timeout-klockan) och läcker medvetet inte ut här.
            **{k: v for k, v in job.items() if k not in _BASFALT},
        }


class RedisJobStore:
    name = "redis"

    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    async def connect(cls, redis_url: str) -> "RedisJobStore":
        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        return cls(client)

    def _key(self, job_id: str) -> str:
        return nyckel(f"crm:job:{job_id}")

    async def create(self, *, tenant_id: str | None = None, status: str = "processing") -> str:
        job_id = str(uuid.uuid4())
        await self.client.set(
            self._key(job_id),
            json.dumps({"status": status, "created": time.time(), "tenant_id": tenant_id}),
            ex=JOB_TTL_SECONDS,
        )
        return job_id

    async def start(self, job_id: str) -> None:
        """Se MemoryJobStore.start — samma kontrakt. _merge förnyar dessutom
        TTL:n, så ett jobb som stått länge i kö inte hinner städas bort mitt
        under sin faktiska körning."""
        await self._merge(job_id, {"status": "processing", "started": time.time()})

    async def _merge(self, job_id: str, patch: dict[str, Any]) -> None:
        raw = await self.client.get(self._key(job_id))
        job = json.loads(raw) if raw else {}
        job.update(patch)
        await self.client.set(self._key(job_id), json.dumps(job), ex=JOB_TTL_SECONDS)

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        await self._merge(job_id, {"status": "completed", "result": result})

    async def fail(self, job_id: str, error: str) -> None:
        await self._merge(job_id, {"status": "failed", "error": error})

    async def annotate(self, job_id: str, **falt: Any) -> None:
        """Se MemoryJobStore.annotate — samma kontrakt, via _merge (rör
        aldrig status/result/error)."""
        await self._merge(job_id, falt)

    async def get(self, job_id: str) -> dict[str, Any] | None:
        raw = await self.client.get(self._key(job_id))
        if not raw:
            return None
        job = json.loads(raw)
        # Samma klockregel som MemoryJobStore._sweep: "started" när den
        # finns, annars "created" — och bara för "processing". Kötid
        # ("queued") är inte arbetstid och auto-failas aldrig.
        if job.get("status") == "processing" and time.time() - job.get(
            "started", job.get("created", 0)
        ) > JOB_TIMEOUT_SECONDS:
            await self.fail(job_id, "Tidsgräns överskriden (5 min).")
            job.update(status="failed", error="Tidsgräns överskriden (5 min).")
        return {
            "status": job["status"],
            "result": job.get("result"),
            "error": job.get("error"),
            "tenant_id": job.get("tenant_id"),
            # Se MemoryJobStore.get — extra fält (ticket_id, conversation_id,
            # ...) följer med, "created" görs det uttryckligen inte.
            **{k: v for k, v in job.items() if k not in _BASFALT},
        }
