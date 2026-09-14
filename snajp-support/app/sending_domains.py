"""Tenant-skopad Resend-domän och DNS-onboarding."""
from __future__ import annotations
import base64, hashlib, hmac, json, time
from typing import Any
import httpx
from .config import get_settings

RESEND = "https://api.resend.com"

def _headers():
    return {"Authorization": f"Bearer {get_settings().resend_api_key}", "Content-Type": "application/json"}

async def _request(method: str, path: str, **kwargs) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.request(method, RESEND + path, headers=_headers(), **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"Resend avvisade domänanropet ({r.status_code}): {r.text[:300]}")
    return r.json()

async def get_config(storage, tenant_id: str) -> dict[str, Any] | None:
    if hasattr(storage, "pool"):
        try:
            async with storage._scoped(tenant_id) as conn:
                row = await conn.fetchrow("select * from ss_sending_domains where tenant_id=$1", tenant_id)
        except Exception as error:
            if getattr(error, "sqlstate", None) == "42P01":
                return None
            raise
        return dict(row) if row else None
    return getattr(storage, "_sending_domains", {}).get(tenant_id)

async def save_config(storage, tenant_id: str, data: dict[str, Any]) -> dict[str, Any]:
    if hasattr(storage, "pool"):
        async with storage._scoped(tenant_id) as conn:
            row = await conn.fetchrow("""insert into ss_sending_domains
              (tenant_id,resend_domain_id,sending_domain,from_local_part,from_name,reply_to,status,dns_records)
              values($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
              on conflict(tenant_id) do update set resend_domain_id=excluded.resend_domain_id,
              sending_domain=excluded.sending_domain,from_local_part=excluded.from_local_part,
              from_name=excluded.from_name,reply_to=excluded.reply_to,status=excluded.status,
              dns_records=excluded.dns_records,updated_at=now() returning *""",
              tenant_id,data["resend_domain_id"],data["sending_domain"],data["from_local_part"],
              data["from_name"],data["reply_to"],data["status"],json.dumps(data["dns_records"]))
        return dict(row)
    if not hasattr(storage,"_sending_domains"): storage._sending_domains={}
    storage._sending_domains[tenant_id]={"tenant_id":tenant_id,**data}
    return storage._sending_domains[tenant_id]

async def create_domain(storage, tenant_id: str, *, domain: str, from_local_part: str, from_name: str, reply_to: str) -> dict:
    result=await _request("POST","/domains",json={"name":domain,"region":"eu-west-1","custom_return_path":"outbound"})
    return await save_config(storage,tenant_id,{"resend_domain_id":result["id"],"sending_domain":domain,
      "from_local_part":from_local_part,"from_name":from_name,"reply_to":reply_to,"status":result.get("status","not_started"),
      "dns_records":result.get("records",[])})

async def verify_domain(storage, tenant_id: str) -> dict:
    cfg=await get_config(storage,tenant_id)
    if not cfg: raise ValueError("Ingen sänddomän är skapad.")
    await _request("POST",f"/domains/{cfg['resend_domain_id']}/verify")
    cfg=dict(cfg);cfg["status"]="pending";return await save_config(storage,tenant_id,cfg)

async def apply_domain_event(storage, payload: dict) -> bool:
    data=payload.get("data") or {}; domain_id=data.get("id") or data.get("domain_id")
    if not domain_id:return False
    status=data.get("status") or payload.get("type","").removeprefix("domain.")
    if hasattr(storage,"pool"):
      async with storage.pool.acquire() as conn:
       done=await conn.execute("update ss_sending_domains set status=$1,updated_at=now() where resend_domain_id=$2",status,domain_id)
      return not done.endswith(" 0")
    for cfg in getattr(storage,"_sending_domains",{}).values():
      if cfg.get("resend_domain_id")==domain_id: cfg["status"]=status;return True
    return False

def verify_webhook(raw: bytes, headers: dict[str,str]) -> bool:
    secret=get_settings().resend_webhook_secret.strip()
    if not secret:return False
    try:
      if abs(time.time()-int(headers["svix-timestamp"])) > 300: return False
      msg=f"{headers['svix-id']}.{headers['svix-timestamp']}.".encode()+raw
      key=base64.b64decode(secret.removeprefix("whsec_"))
      expected=base64.b64encode(hmac.new(key,msg,hashlib.sha256).digest()).decode()
      return any(hmac.compare_digest(expected,x.split(",",1)[-1]) for x in headers['svix-signature'].split())
    except KeyError:return False
