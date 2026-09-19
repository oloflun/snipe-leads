"""Kundens hemligheter (API-nycklar, MCP-tokens, kanalnycklar), krypterade i vila.

## Varför de inte ligger i klartext i konfigurationen

Konfigurationen (`konfig`, jsonb) läses av portalen, loggas i felspår och
visas i adminvyer. En Zendesk-token i den kolumnen är en token i varje
skärmdump och varje databasexport. Hemligheterna ligger därför i en EGEN
kolumn, krypterade med Fernet (AES-128-CBC + HMAC-SHA256), och lämnar bara
den här modulen som klartext i det ögonblick ett anrop byggs.

Modellen ser dem aldrig. De sätts in av koden i url/rubriker/brödtext via
`{{hemlighet.<namn>}}`, och varje svar som kommer tillbaka tvättas från dem
(`tvatta`) innan det når prompten eller loggen — ett API som ekar tillbaka
en nyckel i ett felmeddelande ska inte kunna läcka den vidare.

## Nyckeln

`INTEGRATION_NYCKEL`, kommaseparerad för rotation: den första krypterar,
alla dekrypterar (MultiFernet).

Saknas nyckeln i en miljö med riktig kunddata (`har_riktig_kunddata`) går
det inte att SPARA en hemlighet — `IngenNyckelError` blir ett 503 med ett
begripligt besked i API:t. Tjänsten startar ändå: integrationer utan
hemligheter fungerar, och ett startfel för en funktion som ingen kund ännu
använt vore att fälla hela supporten för fel sak.

Lokalt och i testsviten används en fast utvecklingsnyckel. Den är publik
(den står här) och får därför aldrig skydda riktig data — därav villkoret.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from ..config import get_settings

#: Härledd ur en publik sträng — skyddar INGENTING. Bara för lokal körning
#: och testsviten, där datan är syntetisk.
_UTVECKLINGSNYCKEL = base64.urlsafe_b64encode(
    hashlib.sha256(b"snajp-integrationer-lokal-utveckling").digest()
)

#: Ett tvättat värde ersätts med den här markören. Kort och tydlig i en
#: logg: det ska synas att något tvättades bort, inte bara att det saknas.
MASKERAT = "[hemlighet]"

#: Kortare värden tvättas inte ur svar: en hemlighet på tre tecken ("abc")
#: hade maskat vanliga ord i varje API-svar. Riktiga nycklar är längre.
_MIN_TVATTLANGD = 6


class IngenNyckelError(RuntimeError):
    """INTEGRATION_NYCKEL saknas i en miljö där hemligheter skyddar riktig data."""


class OlasbarHemlighetError(RuntimeError):
    """Hemligheten gick inte att dekryptera — fel nyckel, eller roterad bort."""


def _nycklar() -> list[bytes]:
    settings = get_settings()
    ratt = [n.strip() for n in (settings.integration_nyckel or "").split(",") if n.strip()]
    if ratt:
        return [n.encode("ascii") for n in ratt]
    if settings.har_riktig_kunddata():
        raise IngenNyckelError(
            "INTEGRATION_NYCKEL saknas i den här miljön. Kundens API-nycklar kan "
            "inte sparas utan den — sätt variabeln (Fernet-nyckel) på tjänsten."
        )
    return [_UTVECKLINGSNYCKEL]


def _fernet() -> MultiFernet:
    return MultiFernet([Fernet(n) for n in _nycklar()])


def kryptera(hemligheter: dict[str, str]) -> str | None:
    """dict -> Fernet-token (text). Tom dict -> None, så kolumnen blir NULL."""
    rena = {str(k): str(v) for k, v in (hemligheter or {}).items() if str(v)}
    if not rena:
        return None
    return _fernet().encrypt(json.dumps(rena, ensure_ascii=False).encode("utf-8")).decode("ascii")


def dekryptera(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    try:
        data = _fernet().decrypt(token.encode("ascii"))
    except InvalidToken as fel:
        raise OlasbarHemlighetError(
            "Hemligheterna gick inte att läsa med nuvarande INTEGRATION_NYCKEL. "
            "Har nyckeln bytts utan att den gamla ligger kvar i listan?"
        ) from fel
    varde = json.loads(data.decode("utf-8"))
    return {str(k): str(v) for k, v in varde.items()} if isinstance(varde, dict) else {}


def maskera_namn(hemligheter: dict[str, str]) -> dict[str, str]:
    """Det portalen får se: VILKA hemligheter som finns, aldrig värdet."""
    return {namn: MASKERAT for namn in sorted(hemligheter)}


def tvatta(text: str, hemligheter: dict[str, str] | list[str]) -> str:
    """Ersätter varje hemlighetsvärde i `text` med MASKERAT.

    Längsta värdet först: är en nyckel en delsträng av en annan ska den
    längre maskas hel, inte i två halvor.
    """
    if not text:
        return text
    varden = hemligheter.values() if isinstance(hemligheter, dict) else hemligheter
    for varde in sorted({v for v in varden if v and len(v) >= _MIN_TVATTLANGD}, key=len, reverse=True):
        text = text.replace(varde, MASKERAT)
    return text


def tvatta_djupt(varde: Any, hemligheter: dict[str, str]) -> Any:
    """`tvatta` över en JSON-struktur (loggposter, testresultat)."""
    if isinstance(varde, str):
        return tvatta(varde, hemligheter)
    if isinstance(varde, dict):
        return {tvatta(str(k), hemligheter): tvatta_djupt(v, hemligheter) for k, v in varde.items()}
    if isinstance(varde, list):
        return [tvatta_djupt(v, hemligheter) for v in varde]
    return varde
