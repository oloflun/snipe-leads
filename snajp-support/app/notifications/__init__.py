"""Interna notiser — larm till OSS, aldrig till en kund.

Skilj det här paketet från `app/leads/send_provider.py`. Den senare är
kundvänd sändväg: den skickar från tenantens avsändare, lyder `send_guard`,
bär art. 14-sidfot och avregistreringslänk, och kan i dag bara logga eftersom
per-tenant-SMTP inte finns modellerat.

Det här paketet skickar från ETT konto, till OSS, om att något behöver en
människa. Det har inga tenant-uppgifter, ingen sidfot och ingen kö — och det
får aldrig påverka utfallet av det som larmas om.
"""
