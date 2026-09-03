import base64, hashlib, hmac, json, time
from unittest.mock import AsyncMock
import pytest
from app.email_pipeline.sender import skicka_supportsvar
from app.sending_domains import apply_domain_event, get_config, save_config, verify_webhook

class Provider:
    levererar=True
    def __init__(self):self.kw=None
    async def send(self,**kw):self.kw=kw;return 're_msg_1'

@pytest.mark.anyio
async def test_verified_tenant_domain_controls_from_reply_to_and_tags():
    storage=type("S",(),{})();storage._sending_domains={}
    await save_config(storage,'t1',{'resend_domain_id':'d1','sending_domain':'mail.acme.se','from_local_part':'support','from_name':'Acme','reply_to':'help@acme.se','status':'verified','dns_records':[]})
    p=Provider();note=await skicka_supportsvar({'provider':'imap','from_email':'buyer@example.com','subject':'Hi'},content='Svar',tenant_id='t1',storage=storage,provider=p)
    assert p.kw['from_email']=='support@mail.acme.se';assert p.kw['reply_to']=='help@acme.se'
    assert p.kw['tags']==[{'name':'tenant_id','value':'t1'}];assert 'Resend-id: re_msg_1' in note

@pytest.mark.anyio
async def test_unverified_domain_uses_visible_global_fallback():
    storage=type("S",(),{})();storage._sending_domains={}
    await save_config(storage,'t1',{'resend_domain_id':'d1','sending_domain':'mail.acme.se','from_local_part':'support','from_name':'Acme','reply_to':'help@acme.se','status':'pending','dns_records':[]})
    p=Provider();note=await skicka_supportsvar({'provider':'imap','from_email':'buyer@example.com','subject':'Hi'},content='Svar',tenant_id='t1',storage=storage,provider=p)
    assert p.kw['from_email'] is None; assert 'synlig fallback' in note
