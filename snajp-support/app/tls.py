"""Ett delat TLS-sammanhang för de httpx-klienter som skapas per anrop.

Varje `httpx.AsyncClient()` utan `verify` läser in hela CA-paketet på nytt,
synkront: 0,23 s per klient med händelseloopen stilla (uppmätt 2026-10-09).
En sökrunda öppnar hundratals klienter mot bolagens sajter, och det blev
minuter då api-processen, chatten inräknad, inte svarade. Sammanhanget
skapas en gång per process och delas; det är trådsäkert för läsning.
"""

from __future__ import annotations

import functools
import ssl

import certifi


@functools.cache
def ssl_kontext() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())
