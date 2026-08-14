"""Chat-endpointen: 202 + job_id, bakgrundskörning, polling — som i referensrepot.

Multi-tenant: nyckeln avgör tenant; agentkörningen och jobbresultatet är
skopade till den tenanten.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from .deps import require_tenant
from .schemas import ChatRequest

router = APIRouter()

MAX_ATTACHMENT_BYTES = 6_000_000  # ~4,5 MB bild efter base64-påslag


def _validate_attachments(request: ChatRequest) -> list[str]:
    urls: list[str] = []
    for attachment in request.attachments[:3]:
        data_url = attachment.data_url
        if not data_url.startswith("data:image/"):
            raise HTTPException(status_code=422, detail="Endast bilder (data:image/...) stöds.")
        if len(data_url) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=422, detail="Bilden är för stor (max ~4 MB).")
        urls.append(data_url)
    return urls


async def _process(
    app_state, job_id: str, tenant_id: str, request: ChatRequest, attachments: list[str]
) -> None:
    settings = get_settings()
    storage = app_state.storage
    try:
        # Kvoten kollas INNAN modellen anropas — annars betalar vi för ett svar
        # kunden inte har rätt till, och kunden får ett svar som inte ingår.
        from ..billing.quota import check_quota, quota_exceeded_result

        quota = await check_quota(storage, tenant_id)
        if quota["exceeded"]:
            await app_state.jobs.complete(job_id, quota_exceeded_result(quota))
            return

        if settings.is_simulation():
            from ..simulation.sim_agent import run_sim_agent

            result = await run_sim_agent(
                storage,
                tenant_id,
                message=request.message,
                subject=request.subject,
                channel=request.channel,
                customer_email=request.customer_email,
                customer_name=request.customer_name,
                has_image=bool(attachments),
            )
        else:
            from ..agent.support_agent import run_support_agent

            result = await run_support_agent(
                storage,
                tenant_id,
                message=request.message,
                subject=request.subject,
                channel=request.channel,
                customer_email=request.customer_email,
                customer_name=request.customer_name,
                attachments=attachments,
            )
        # Varningen följer med svaret så UI:t kan visa den utan ett extra anrop.
        if quota.get("warn"):
            result["quota_warning"] = quota
        await app_state.jobs.complete(job_id, result)
    except Exception as error:  # noqa: BLE001 — jobbet får aldrig fastna i processing
        await app_state.jobs.fail(job_id, f"Agentkörningen misslyckades: {error}")


@router.post("/api/chat", status_code=202)
async def chat(
    request: Request, payload: ChatRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    attachments = _validate_attachments(payload)
    job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"])
    asyncio.create_task(
        _process(request.app.state, job_id, tenant["tenant_id"], payload, attachments)
    )
    return {"job_id": job_id, "status": "processing"}


@router.get("/api/jobs/{job_id}")
async def get_job(
    request: Request, job_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    job = await request.app.state.jobs.get(job_id)
    if not job or job.get("tenant_id") != tenant["tenant_id"]:
        raise HTTPException(status_code=404, detail="Jobbet finns inte eller har städats bort.")
    return {"status": job["status"], "result": job.get("result"), "error": job.get("error")}
