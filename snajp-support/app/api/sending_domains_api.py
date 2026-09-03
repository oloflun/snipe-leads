from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from ..sending_domains import apply_domain_event, create_domain, get_config, verify_domain, verify_webhook
from .deps import require_tenant
router=APIRouter()
class DomainCreate(BaseModel):
    domain:str=Field(pattern=r"^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$")
    from_local_part:str=Field(default="support",pattern=r"^[a-z0-9._+-]+$")
    from_name:str=Field(default="")
    reply_to:str
@router.post('/api/sending-domain')
async def create(payload:DomainCreate,request:Request,tenant:dict=Depends(require_tenant)):
    try:return await create_domain(request.app.state.storage,tenant['tenant_id'],**payload.model_dump())
    except RuntimeError as e:raise HTTPException(502,str(e)) from e
@router.get('/api/sending-domain')
async def get(request:Request,tenant:dict=Depends(require_tenant)):
    return {'domain':await get_config(request.app.state.storage,tenant['tenant_id'])}
@router.post('/api/sending-domain/verify')
async def verify(request:Request,tenant:dict=Depends(require_tenant)):
    try:return await verify_domain(request.app.state.storage,tenant['tenant_id'])
    except ValueError as e:raise HTTPException(404,str(e)) from e
@router.post('/api/webhooks/resend/domains')
async def webhook(request:Request):
    raw=await request.body(); headers={k.lower():v for k,v in request.headers.items()}
    if not verify_webhook(raw,headers):raise HTTPException(401,'Ogiltig webhook-signatur.')
    return {'applied':await apply_domain_event(request.app.state.storage,await request.json())}
