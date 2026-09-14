"""INV-REDIS-001 — varje Redis-nyckel bär driftsättningens namnrymd.

Uppmätt 2026-08-29: `main` och `development` delade en Redis-instans (samma
`REDIS_URL`, verifierat mot Railways API) och ingen nyckel bar miljö. Följden
var inte teoretisk — en enda consumer group `agenter` på `crm:jobb:chatt` hade
konsumenter från nio containrar, och en grupp delar ut varje post till exakt
EN konsument. Ett kundjobb från produktionen kunde alltså köras av en
development-container mot spegeldatabasen. Svarscachen och arbetsminnet
delades av samma skäl, och development speglar produktionen med IDENTISKA
tenant-id:n.

Filen finns för att den fixen inte ska gå att montera ned av misstag. Två
saker bevisas, och det andra är det som faktiskt räknar:

(a) Varje nyckelfamilj bär namnrymden.
(b) Två driftsättningar som skiljer sig ENBART på lösenordet får olika
    namnrymd. Det är exakt det fall som fällde det första utkastet: inne i
    Railway kör båda miljöerna mot `postgres.railway.internal:5432/railway`
    med användaren `snajp_app`, så en namnrymd på värd + databasnamn hade
    varit identisk i produktion och spegel — och sett helt korrekt ut.

Testerna rör ALDRIG miljövariabler eller laddar om moduler. Ett tidigare
utkast gjorde det, och sviten hängde: efterföljande tester ärvde en
DATABASE_URL som pekade på en värd som inte svarar. Uträkningen är därför en
ren funktion (`_namnrymd_av`) som går att fråga direkt.
"""

from __future__ import annotations

import app.cache.embeddingcache as embeddingcache
import app.cache.svarscache as svarscache
import app.cache.versioner as versioner
import app.jobs.store as store
import app.jobs.stream as stream
import app.minne.arbetsminne as arbetsminne
from app.redisnycklar import _namnrymd_av, namnrymd

# Två DSN:er som skiljer sig ENBART på lösenordet — Railways verkliga form.
DSN_MAIN = "postgresql://snajp_app:losen-main@postgres.railway.internal:5432/railway"
DSN_DEV = "postgresql://snajp_app:losen-dev@postgres.railway.internal:5432/railway"


def test_alla_nyckelfamiljer_bar_namnrymden():
    """Nio ytor, ett prefix. En ny nyckelfamilj utan `nyckel()` delar rymd med
    produktionen — lägg till den här när du lägger till den där."""
    prefix = f"ns{namnrymd()}:"

    familjer = {
        "jobbpost": store.RedisJobStore(None)._key("abc"),
        "chattström": stream.ChattStrom(None).stream_key,
        "leadsström": stream.ChattStrom(None, stream_key="crm:jobb:leads").stream_key,
        "embeddingcache": embeddingcache._nyckel("hej"),
        "kb-version": versioner._KB_PREFIX,
        "cfg-version": versioner._CFG_PREFIX,
        "arbetsminne": arbetsminne._nyckel("tenant", "kund"),
        "svarscache-nyckel": svarscache.RedisSvarscache(None).PREFIX,
        # Indexet är lika viktigt som nycklarna: ett delat FT-index gör
        # posterna sökbara över miljögränsen även med skilda nyckelnamn.
        "svarscache-index": svarscache.RedisSvarscache(None).INDEX,
    }

    for namn, vardet in familjer.items():
        assert vardet.startswith(prefix), (
            f"{namn} saknar namnrymden ({vardet!r}) — den ytan delas då mellan "
            f"produktionen och spegeln. Bygg nyckeln med redisnycklar.nyckel()."
        )


def test_olika_losenord_ger_olika_namnrymd():
    """Regressionen som fällde första utkastet.

    Värd, port, databas och användare är IDENTISKA mellan Railways miljöer.
    Skiljer namnrymden inte på lösenordet skyddar den ingenting.
    """
    assert _namnrymd_av(DSN_MAIN, "main") != _namnrymd_av(DSN_DEV, "development"), (
        "main och development fick SAMMA namnrymd. Fixen är verkningslös: "
        "jobbströmmen, svarscachen och arbetsminnet delas igen."
    )


def test_enbart_miljonamnet_racker_ocksa():
    """Andra halvan av fröet, prövad för sig: skulle två miljöer en dag dela
    databasuppgifter håller namnrymden ändå."""
    assert _namnrymd_av(DSN_MAIN, "main") != _namnrymd_av(DSN_MAIN, "development")


def test_samma_driftsattning_ger_samma_namnrymd():
    """Motsatsen måste också hålla — annars vore cachen aldrig en cache, och
    två repliker av samma tjänst hade inte kunnat dela en jobbström."""
    assert _namnrymd_av(DSN_DEV, "development") == _namnrymd_av(DSN_DEV, "development")


def test_utan_databas_faller_den_pa_miljonamnet():
    """Lokalt och i testsviten finns ingen DATABASE_URL. Namnrymden måste ändå
    vara stabil — annars byter varje processtart nyckelrymd och cachen är död."""
    assert _namnrymd_av("", "lokal") == _namnrymd_av("", "lokal")
    assert _namnrymd_av("", "") == _namnrymd_av("", "")
