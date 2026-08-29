"""Cache-versionering (Fas R2, INV-CACHE-001).

En cachad svarscachepost matchar bara mot EXAKT (tenant, KB-version,
konfigversion). Versionerna är rena heltalsräknare — läsningen jämför bara
STRÄNGAR, den bryr sig aldrig om VARFÖR ett tal steg. Så fort en KB-artikel
läggs till eller instruktionerna/tonen/SOUL ändras för en tenant, bumpas
räknaren och varenda gammal post blir automatiskt omatchbar — utan att någon
behöver hitta och radera dem.

## Varför en GLOBAL konfigräknare också finns

De flesta skrivvägarna är per tenant (`app/api/kb.py`, tenantprofilen i
`app/api/admin_profil.py`). En är det INTE: `PUT /api/admin/instruktioner`
sätter de GLOBALA agentinstruktionerna, som gäller för alla tenants på en
gång (se `app/agentcore/instruktioner.py`). En bump där måste kunna
osynliggöra cachade svar hos ALLA tenants, utan att gå runt och bumpa var och
en för sig — så `config_version()` slår ihop en global- och en
tenant-räknare till EN sträng. Endera hälften som ändras räcker för att göra
en gammal post omatchbar.

## Ingen TTL på räknarna

En version som fick åldras bort och återgå till 0 hade gjort GAMLA (för höga)
poster matchbara igen mot en återställd, lägre räknare — fel riktning att
degradera åt. Räknarna lever så länge Redis-nyckeln gör.

## Utan Redis

En processlokal räknare. Det räcker: utan Redis finns bara
`MinnesSvarscache` i samma process ändå (se `app/cache/svarscache.py`), och
den töms vid omstart precis som räknaren — de två degraderar tillsammans.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger("snajp-support.cache.versioner")

_KB_PREFIX = "cachev:kb:"
_CFG_PREFIX = "cachev:cfg:"
_CFG_GLOBAL_NYCKEL = "cachev:cfg:global"

_redis: Any = None
_loggat_fel = False

# Processlokala fallback-räknare. Skilda dictar för KB och konfig av samma
# skäl som Redis-nycklarna har olika prefix: en KB-artikel och en
# instruktionsändring bumpar oberoende av varandra.
_minne_kb: dict[str, int] = defaultdict(int)
_minne_cfg: dict[str, int] = defaultdict(int)
_minne_cfg_global = 0


def konfigurera(redis_client: Any | None = None) -> None:
    """Samma modul-nivå-mönster som embeddingcache/svarscache. `None`
    (defaulten) nollställer ALLA processräknare — används av testerna för
    att isolera en körning från den föregående."""
    global _redis, _minne_kb, _minne_cfg, _minne_cfg_global, _loggat_fel
    _redis = redis_client
    _minne_kb = defaultdict(int)
    _minne_cfg = defaultdict(int)
    _minne_cfg_global = 0
    _loggat_fel = False


def _logga_fel(vad: str) -> None:
    global _loggat_fel
    if not _loggat_fel:
        _loggat_fel = True
        logger.warning(
            "Cache-versionering (%s) misslyckades mot Redis — faller tillbaka på "
            "processräknare (fail-safe: gör hellre en cachepost omatchbar för "
            "tidigt än att en gammal version matchar av misstag).",
            vad,
        )


async def kb_version(tenant_id: str) -> str:
    """KB-versionen för en tenant, som sträng (redo att läggas rakt in i en
    cachenyckel/lookup)."""
    nyckel = _KB_PREFIX + tenant_id
    if _redis is not None:
        try:
            raw = await _redis.get(nyckel)
            return str(int(raw) if raw else 0)
        except Exception:  # noqa: BLE001 — se _logga_fel
            _logga_fel(f"GET {nyckel}")
    return str(_minne_kb[tenant_id])


async def config_version(tenant_id: str) -> str:
    """`"<global>:<tenant>"` — se moduldocstringen för varför två räknare."""
    if _redis is not None:
        try:
            raw = await _redis.get(_CFG_GLOBAL_NYCKEL)
            global_v = int(raw) if raw else 0
        except Exception:  # noqa: BLE001 — se _logga_fel
            _logga_fel(f"GET {_CFG_GLOBAL_NYCKEL}")
            global_v = _minne_cfg_global
    else:
        global_v = _minne_cfg_global

    nyckel = _CFG_PREFIX + tenant_id
    if _redis is not None:
        try:
            raw = await _redis.get(nyckel)
            tenant_v = int(raw) if raw else 0
        except Exception:  # noqa: BLE001 — se _logga_fel
            _logga_fel(f"GET {nyckel}")
            tenant_v = _minne_cfg[tenant_id]
    else:
        tenant_v = _minne_cfg[tenant_id]

    return f"{global_v}:{tenant_v}"


async def bumpa_kb(tenant_id: str) -> None:
    """Anropas från KB-skrivvägen (`POST /api/kb`, se `app/api/kb.py`)."""
    nyckel = _KB_PREFIX + tenant_id
    if _redis is not None:
        try:
            await _redis.incr(nyckel)
            return
        except Exception:  # noqa: BLE001 — se _logga_fel
            _logga_fel(f"INCR {nyckel}")
    _minne_kb[tenant_id] += 1


async def bumpa_config(tenant_id: str) -> None:
    """Anropas från tenantprofilens instruktioner/ton/SOUL-skrivväg
    (`PUT /api/admin/tenants/{id}/profil`, se `app/api/admin_profil.py`)."""
    nyckel = _CFG_PREFIX + tenant_id
    if _redis is not None:
        try:
            await _redis.incr(nyckel)
            return
        except Exception:  # noqa: BLE001 — se _logga_fel
            _logga_fel(f"INCR {nyckel}")
    _minne_cfg[tenant_id] += 1


async def bumpa_config_global() -> None:
    """Anropas från de GLOBALA agentinstruktionernas skrivväg
    (`PUT /api/admin/instruktioner`) — se moduldocstringen."""
    global _minne_cfg_global
    if _redis is not None:
        try:
            await _redis.incr(_CFG_GLOBAL_NYCKEL)
            return
        except Exception:  # noqa: BLE001 — se _logga_fel
            _logga_fel(f"INCR {_CFG_GLOBAL_NYCKEL}")
    _minne_cfg_global += 1
