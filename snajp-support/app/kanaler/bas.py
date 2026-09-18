"""Det alla kanaladaptrar delar: inkommande meddelande, fel och signaturhjälp."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class KanalFel(RuntimeError):
    """Kanalens API avvisade eller gick inte att nå. Meddelandet är svenskt
    och går till medarbetaren/admin — aldrig till slutkunden."""


@dataclass
class Inkommande:
    """Ett meddelande från en kund i en extern kanal, normaliserat."""

    #: Kanalens eget id för meddelandet — nyckeln i dubblettspärren.
    extern_meddelande_id: str
    #: Vem som skrev (wa_id, PSID, Slack-användare, Teams-användare).
    extern_anvandare: str
    text: str
    visningsnamn: str | None = None
    telefon: str | None = None
    email: str | None = None
    #: Allt som behövs för att svara SENARE (sömlös överlämning): Slack-kanal
    #: och tråd, Teams serviceUrl + konversation. Sparas i ss_channel_contacts.
    adress: dict[str, Any] = field(default_factory=dict)


class Adapter(Protocol):
    kanal: str
    #: Hemligheter anslutningen MÅSTE ha för att kunna ta emot och svara.
    hemligheter_kravs: tuple[str, ...]
    #: Vad `extern_id` betyder för just den här kanalen (visas i portalen).
    extern_id_betyder: str
    #: Längsta textmeddelande kanalen tar emot; längre svar delas upp.
    max_text: int

    def verifiera_prenumeration(self, params: Mapping[str, str], hemligheter: dict[str, str]) -> str | None: ...

    async def verifiera(
        self, raw: bytes, rubriker: Mapping[str, str], hemligheter: dict[str, str], anslutning: dict[str, Any]
    ) -> bool: ...

    def omedelbart_svar(self, payload: dict[str, Any]) -> dict[str, Any] | None: ...

    def tolka(self, payload: dict[str, Any], anslutning: dict[str, Any]) -> list[Inkommande]: ...

    async def skicka(
        self,
        anslutning: dict[str, Any],
        hemligheter: dict[str, str],
        *,
        mottagare: str,
        adress: dict[str, Any],
        text: str,
    ) -> None: ...

    async def kontrollera(self, anslutning: dict[str, Any], hemligheter: dict[str, str]) -> str: ...


def hmac_sha256_hex(nyckel: str, meddelande: bytes) -> str:
    return hmac.new(nyckel.encode("utf-8"), meddelande, hashlib.sha256).hexdigest()


def lika(a: str, b: str) -> bool:
    """Tidskonstant jämförelse — en signaturkontroll ska inte läcka hur många
    tecken som stämde."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def dela_text(text: str, max_langd: int) -> list[str]:
    """Delar ett långt svar vid stycke-, rad- eller meningsgräns.

    Messenger tar 2 000 tecken, WhatsApp 4 096. Ett svar som kapas mitt i en
    mening läses som ett fel; ett svar i två bubblor läses som ett svar.
    """
    text = text.strip()
    if len(text) <= max_langd:
        return [text] if text else []
    delar: list[str] = []
    rest = text
    while len(rest) > max_langd:
        fonster = rest[:max_langd]
        snitt = max(fonster.rfind("\n\n"), fonster.rfind("\n"), fonster.rfind(". "))
        if snitt < max_langd // 2:
            snitt = fonster.rfind(" ")
        if snitt <= 0:
            snitt = max_langd
        else:
            snitt += 1
        delar.append(rest[:snitt].strip())
        rest = rest[snitt:].strip()
    if rest:
        delar.append(rest)
    return [d for d in delar if d]


def rubrik(rubriker: Mapping[str, str], namn: str) -> str:
    """Skiftlägesokänslig rubrikläsning (Starlette är det redan, en dict inte)."""
    namn = namn.lower()
    for k, v in rubriker.items():
        if k.lower() == namn:
            return v
    return ""
