"""Jobbstore för async-mönstret (202 + polling), som i referensarkitekturen.

Multi-tenant: varje jobb märks med tenant_id vid skapandet och API-lagret
verifierar ägarskap vid polling. Redis används om REDIS_URL är satt; annars
in-memory med TTL. Jobb som fastnat längre än 5 minuter auto-failas.
"""

import json
import time
import uuid
from typing import Any

JOB_TIMEOUT_SECONDS = 300
JOB_TTL_SECONDS = 3600


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
            elif job["status"] == "processing" and now - job["created"] > JOB_TIMEOUT_SECONDS:
                job["status"] = "failed"
                job["error"] = "Tidsgräns överskriden (5 min)."

    async def create(self, *, tenant_id: str | None = None) -> str:
        self._sweep()
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "status": "processing",
            "created": time.time(),
            "result": None,
            "tenant_id": tenant_id,
        }
        return job_id

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        if job_id in self.jobs:
            self.jobs[job_id].update(status="completed", result=result)

    async def fail(self, job_id: str, error: str) -> None:
        if job_id in self.jobs:
            self.jobs[job_id].update(status="failed", error=error)

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
        }


class RedisJobStore:
    name = "redis"

    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    async def connect(cls, redis_url: str) -> "RedisJobStore":
        import redis.asyncio as redis  # valfritt beroende

        client = redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        return cls(client)

    def _key(self, job_id: str) -> str:
        return f"crm:job:{job_id}"

    async def create(self, *, tenant_id: str | None = None) -> str:
        job_id = str(uuid.uuid4())
        await self.client.set(
            self._key(job_id),
            json.dumps({"status": "processing", "created": time.time(), "tenant_id": tenant_id}),
            ex=JOB_TTL_SECONDS,
        )
        return job_id

    async def _merge(self, job_id: str, patch: dict[str, Any]) -> None:
        raw = await self.client.get(self._key(job_id))
        job = json.loads(raw) if raw else {}
        job.update(patch)
        await self.client.set(self._key(job_id), json.dumps(job), ex=JOB_TTL_SECONDS)

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        await self._merge(job_id, {"status": "completed", "result": result})

    async def fail(self, job_id: str, error: str) -> None:
        await self._merge(job_id, {"status": "failed", "error": error})

    async def get(self, job_id: str) -> dict[str, Any] | None:
        raw = await self.client.get(self._key(job_id))
        if not raw:
            return None
        job = json.loads(raw)
        if job.get("status") == "processing" and time.time() - job.get("created", 0) > JOB_TIMEOUT_SECONDS:
            await self.fail(job_id, "Tidsgräns överskriden (5 min).")
            job.update(status="failed", error="Tidsgräns överskriden (5 min).")
        return {
            "status": job["status"],
            "result": job.get("result"),
            "error": job.get("error"),
            "tenant_id": job.get("tenant_id"),
        }
