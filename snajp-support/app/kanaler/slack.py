"""Slack via Events API och Web API.

Anslutningen är EN Slack-arbetsyta: `extern_id` = arbetsytans team_id
(T…). Hemligheter:

  bot_token       xoxb-… (scopes: chat:write, im:history, app_mentions:read,
                  och gärna users:read + users:read.email för namn och e-post)
  signing_secret  appens Signing Secret, för signaturkontrollen

Signaturen: `X-Slack-Signature: v0=<hex HMAC-SHA256 över "v0:{ts}:{kropp}">`
med `X-Slack-Request-Timestamp`. En tidsstämpel äldre än fem minuter
avvisas, annars går en uppfångad webhook att spela upp igen.

Inkommande:
  - `url_verification` besvaras direkt med challenge (Slacks uppsättning).
  - `message` i en DM till boten (channel_type "im").
  - `app_mention` i en kanal. Svaret går i tråden, inte i kanalen.
  - Botars egna meddelanden och redigeringar (bot_id, subtype) ignoreras,
    annars svarar agenten på sig själv i en loop.

Slack skickar om en händelse som inte kvitterats inom tre sekunder. Därför
kvitterar webhooken direkt och kör agenten i bakgrunden, och
`event_id` är nyckeln i dubblettspärren.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping
from typing import Any

from ..integrationer import natvakt
from .bas import Inkommande, KanalFel, hmac_sha256_hex, lika, rubrik

SLACK_API = "https://slack.com/api"
MAX_ALDER_SEKUNDER = 300
_OMNAMNANDE = re.compile(r"<@[A-Z0-9]+>")

_FELKODER = {
    "invalid_auth": "Bot-token är ogiltig.",
    "not_authed": "Bot-token saknas.",
    "account_inactive": "Bot-token hör till en app som tagits bort eller inaktiverats.",
    "token_revoked": "Bot-token har dragits tillbaka.",
    "channel_not_found": "Kanalen finns inte, eller så är boten inte medlem i den.",
    "not_in_channel": "Boten är inte medlem i kanalen.",
    "missing_scope": "Appen saknar behörighet (scope) för anropet.",
    "ratelimited": "Slack begränsar anropen just nu. Försök igen om en stund.",
}


class Slack:
    kanal = "slack"
    hemligheter_kravs = ("bot_token", "signing_secret")
    extern_id_betyder = "Arbetsytans team_id (börjar med T)"
    max_text = 3500

    def verifiera_prenumeration(self, params: Mapping[str, str], hemligheter: dict[str, str]) -> str | None:
        return None  # Slack verifierar med url_verification i POST, inte GET

    async def verifiera(
        self, raw: bytes, rubriker: Mapping[str, str], hemligheter: dict[str, str], anslutning: dict[str, Any]
    ) -> bool:
        hemlighet = hemligheter.get("signing_secret") or ""
        tidsstampel = rubrik(rubriker, "x-slack-request-timestamp")
        signatur = rubrik(rubriker, "x-slack-signature")
        if not hemlighet or not tidsstampel or not signatur.startswith("v0="):
            return False
        try:
            if abs(time.time() - int(tidsstampel)) > MAX_ALDER_SEKUNDER:
                return False
        except ValueError:
            return False
        basstrang = b"v0:" + tidsstampel.encode("ascii") + b":" + raw
        return lika(signatur, "v0=" + hmac_sha256_hex(hemlighet, basstrang))

    def omedelbart_svar(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge") or ""}
        return None

    def tolka(self, payload: dict[str, Any], anslutning: dict[str, Any]) -> list[Inkommande]:
        if payload.get("type") != "event_callback":
            return []
        if str(payload.get("team_id") or "") != anslutning["extern_id"]:
            return []
        handelse = payload.get("event") or {}
        typ = handelse.get("type")
        if handelse.get("bot_id") or handelse.get("subtype"):
            return []
        if typ == "message" and handelse.get("channel_type") != "im":
            return []
        if typ not in ("message", "app_mention"):
            return []
        anvandare = str(handelse.get("user") or "")
        kanal = str(handelse.get("channel") or "")
        text = _OMNAMNANDE.sub("", str(handelse.get("text") or "")).strip()
        handelse_id = str(payload.get("event_id") or handelse.get("client_msg_id") or handelse.get("ts") or "")
        if not anvandare or not kanal or not text or not handelse_id:
            return []
        adress: dict[str, Any] = {"kanal": kanal}
        if typ == "app_mention":
            # Svara i tråden: i en kanal är ett svar utanför tråden brus för
            # alla andra i kanalen.
            adress["trad"] = str(handelse.get("thread_ts") or handelse.get("ts") or "")
        return [
            Inkommande(
                extern_meddelande_id=handelse_id,
                extern_anvandare=anvandare,
                text=text,
                adress=adress,
            )
        ]

    async def _api(self, metod: str, token: str, kropp: dict[str, Any]) -> dict[str, Any]:
        if not token:
            raise KanalFel("Bot-token saknas för anslutningen.")
        try:
            svar = await natvakt.anropa(
                "POST",
                f"{SLACK_API}/{metod}",
                rubriker={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                json_kropp=kropp,
                tidsgrans=15.0,
            )
        except natvakt.NatvaktError as fel:
            raise KanalFel(str(fel)) from fel
        except Exception as fel:  # noqa: BLE001
            raise KanalFel(f"Slack gick inte att nå ({type(fel).__name__}).") from fel
        try:
            data = json.loads(svar.text or "{}")
        except json.JSONDecodeError:
            raise KanalFel(f"Slack svarade {svar.status} utan läsbart svar.") from None
        if not data.get("ok"):
            kod = str(data.get("error") or svar.status)
            raise KanalFel(_FELKODER.get(kod, f"Slack avvisade anropet ({kod})."))
        return data

    async def berika(self, hemligheter: dict[str, str], inkommande: Inkommande) -> None:
        """Namn och e-post ur users.info, när appen har behörighet. Misslyckas
        tyst: en kund utan e-post är fortfarande en kund."""
        try:
            data = await self._api("users.info", hemligheter.get("bot_token", ""), {"user": inkommande.extern_anvandare})
        except KanalFel:
            return
        profil = (data.get("user") or {}).get("profile") or {}
        inkommande.visningsnamn = profil.get("real_name") or profil.get("display_name") or inkommande.visningsnamn
        inkommande.email = profil.get("email") or inkommande.email

    async def skicka(
        self,
        anslutning: dict[str, Any],
        hemligheter: dict[str, str],
        *,
        mottagare: str,
        adress: dict[str, Any],
        text: str,
    ) -> None:
        kropp: dict[str, Any] = {"channel": adress.get("kanal") or mottagare, "text": text[: self.max_text]}
        if adress.get("trad"):
            kropp["thread_ts"] = adress["trad"]
        await self._api("chat.postMessage", hemligheter.get("bot_token", ""), kropp)

    async def kontrollera(self, anslutning: dict[str, Any], hemligheter: dict[str, str]) -> str:
        data = await self._api("auth.test", hemligheter.get("bot_token", ""), {})
        if str(data.get("team_id") or "") != anslutning["extern_id"]:
            return (
                f"Token hör till arbetsytan {data.get('team')} ({data.get('team_id')}), "
                f"inte {anslutning['extern_id']}."
            )
        return f"Ansluten till {data.get('team')} som {data.get('user')}."
