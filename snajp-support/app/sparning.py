"""Spårning: ett id per anrop, i loggen, i svaret och i felposten.

Före 2026-11-09 (Fas 0-fyndet H12) gick ett fel inte att följa. Kunden såg
"Något gick fel", loggen hade en stack, händelsetabellen hade en annan rad,
och inget band ihop dem: den som felsökte fick gissa på klockslag och väg.

Nu får varje HTTP-anrop ett id (`X-Request-Id`):

  * det sätts på svaret, så att webbläsarens nätverkspanel och webbens proxy
    har det;
  * det står på varje loggrad som skrivs under anropet;
  * 500-svaret bär det som `referens`, och samma värde ligger i
    platform_events — det kunden citerar är det vi söker på.

Ett inkommande `X-Request-Id` återanvänds om det ser ut som ett id, så att
webbens proxy kan sätta det och samma värde gäller hela vägen.

Loggformatet är text som förut, med id:t tillagt. `LOG_FORMAT=json` ger en
JSON-rad per händelse (Railway läser `level` och `message` ur den) för den
som vill söka och larma på fält i stället för på text.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

_anrop: ContextVar[str | None] = ContextVar("snajp_anrop", default=None)

#: Vad som godtas utifrån. Allt annat ersätts: ett id som hamnar i loggar och
#: svarshuvuden får inte kunna bära radbrytningar eller en halv logg.
_GILTIGT = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def anrops_id() -> str | None:
    """Id:t för det pågående anropet, eller None utanför ett anrop."""
    return _anrop.get()


def nytt_id() -> str:
    return uuid.uuid4().hex[:16]


#: Var id:t ligger i ASGI-scopet. Den globala felhanteraren körs av Starlettes
#: yttersta lager, UTANFÖR mellanlagren: när den anropas har kontextvariabeln
#: redan återställts och svaret passerar inte `Sparning`. Scopet följer med
#: hela vägen, så felhanteraren läser id:t där (api/events.py).
SCOPE_NYCKEL = "snajp_anrop"


@contextmanager
def inom(anrop: str | None):
    """Sätter id:t för ett kodblock som körs utanför mellanlagret."""
    token = _anrop.set(anrop)
    try:
        yield
    finally:
        _anrop.reset(token)


class Sparning:
    """Rent ASGI-mellanlager, som app/matning.py och av samma skäl."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        inkommande = ""
        for namn, varde in scope.get("headers") or []:
            if namn == b"x-request-id":
                inkommande = varde.decode("latin-1", "replace").strip()
                break
        anrop = inkommande if _GILTIGT.match(inkommande) else nytt_id()
        scope[SCOPE_NYCKEL] = anrop
        token = _anrop.set(anrop)

        async def skicka(message: dict) -> None:
            if message["type"] == "http.response.start":
                huvuden = [h for h in message.get("headers", []) if h[0] != b"x-request-id"]
                huvuden.append((b"x-request-id", anrop.encode("ascii")))
                message = {**message, "headers": huvuden}
            await send(message)

        try:
            await self.app(scope, receive, skicka)
        finally:
            _anrop.reset(token)


class _Anropsfilter(logging.Filter):
    """Lägger `anrop` på varje loggpost: id:t, eller "-" utanför ett anrop."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.anrop = _anrop.get() or "-"
        return True


class _JsonFormat(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        post: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        anrop = getattr(record, "anrop", "-")
        if anrop and anrop != "-":
            post["anrop"] = anrop
        if record.exc_info:
            post["exception"] = self.formatException(record.exc_info)
        return json.dumps(post, ensure_ascii=False)


TEXTFORMAT = "%(asctime)s %(name)s %(levelname)s [%(anrop)s] %(message)s"


def installera_loggning(niva: int = logging.INFO) -> None:
    """Sätter rotloggarens format. Kan anropas flera gånger (testerna importerar
    appen många gånger); filtret och formatet läggs då inte på dubbelt."""
    rot = logging.getLogger()
    if not rot.handlers:
        logging.basicConfig(level=niva)
    rot.setLevel(niva)
    som_json = os.environ.get("LOG_FORMAT", "").strip().lower() == "json"
    for hanterare in rot.handlers:
        if not any(isinstance(f, _Anropsfilter) for f in hanterare.filters):
            hanterare.addFilter(_Anropsfilter())
        hanterare.setFormatter(_JsonFormat() if som_json else logging.Formatter(TEXTFORMAT))
