"""Interna mejl — till OSS, aldrig till en kund.

Skilj det här paketet från `app/leads/send_provider.py`. Den senare är
kundvänd sändväg: den skickar från tenantens avsändare, lyder `send_guard`,
bär art. 14-sidfot och avregistreringslänk, och kan i dag bara logga eftersom
per-tenant-SMTP inte finns modellerat.

Det här paketet skickar från ETT konto, till OSS, om att något behöver en
människa. Det har inga tenant-uppgifter, ingen sidfot och ingen kö — och det
får aldrig påverka utfallet av det som föranledde mejlet.

Det är ett MEJL, inte ett larmsystem: ingen sida övervakas, inget
tröskelvärde bevakas, ingen jour väcks. Ämnesraden bär `[PRIORITERAT]` så att
den går att sortera på, och där slutar mekaniken.
"""
