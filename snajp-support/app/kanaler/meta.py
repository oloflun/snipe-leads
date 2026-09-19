"""Det WhatsApp Cloud API och Messenger delar: Metas webhookram och Graph-anrop.

Båda kanalerna levereras av samma Meta-app-mekanik:

  - Prenumerationen verifieras med GET `hub.mode=subscribe`,
    `hub.verify_token` och `hub.challenge`. Stämmer token svarar vi med
    challenge i klartext, annars 403.
  - Varje POST signeras med appens hemlighet: `X-Hub-Signature-256:
    sha256=<hex HMAC-SHA256 över råkroppen>`. En osignerad eller felsignerad
    webhook släpps aldrig in. Utan kontrollen kan vem som helst som gissat
    webhookadressen skriva meddelanden i en kunds namn.
  - Svar skickas via Graph API med sidans/numrets åtkomsttoken i
    Authorization-rubriken. Token läggs aldrig i URL:en, där den hamnar i
    åtkomstloggar.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ..integrationer import natvakt
from .bas import KanalFel, hmac_sha256_hex, lika, rubrik

GRAPH = "https://graph.facebook.com"
#: Graph-versionen. Metas versioner stöds i minst två år efter release.
#: Kan sättas per anslutning (konfig.graph_version) när Meta flyttar fram.
STANDARD_GRAPH_VERSION = "v23.0"

#: Metas felkoder med ett begripligt svenskt besked. Resten får Metas text.
_FELKODER = {
    190: "Åtkomsttoken har gått ut eller dragits tillbaka. Skapa en ny i Meta-appen.",
    10: "Appen saknar behörighet för det här anropet.",
    200: "Appen saknar behörighet för det här anropet.",
    131047: (
        "Det har gått mer än 24 timmar sedan kundens senaste meddelande. WhatsApp "
        "tillåter då bara godkända mallmeddelanden, inte fritt svar."
    ),
    131026: "Meddelandet gick inte att leverera till mottagaren.",
    131030: "Mottagarens nummer finns inte på tillåtelselistan (testnummer).",
    10903: "Messenger tillåter inte svar så långt efter kundens senaste meddelande.",
    551: "Mottagaren kan inte ta emot meddelanden från sidan just nu.",
}


def verifiera_prenumeration(params: Mapping[str, str], hemligheter: dict[str, str]) -> str | None:
    """Metas GET-verifiering. Returnerar challenge om token stämmer, annars None."""
    forvantad = hemligheter.get("verify_token") or ""
    if params.get("hub.mode") != "subscribe" or not forvantad:
        return None
    if not lika(params.get("hub.verify_token") or "", forvantad):
        return None
    return params.get("hub.challenge") or ""


def verifiera_signatur(raw: bytes, rubriker: Mapping[str, str], hemligheter: dict[str, str]) -> bool:
    hemlighet = hemligheter.get("app_secret") or ""
    signatur = rubrik(rubriker, "x-hub-signature-256")
    if not hemlighet or not signatur.startswith("sha256="):
        return False
    return lika(signatur.removeprefix("sha256="), hmac_sha256_hex(hemlighet, raw))


def graph_url(anslutning: dict[str, Any], sokvag: str) -> str:
    version = (anslutning.get("konfig") or {}).get("graph_version") or STANDARD_GRAPH_VERSION
    return f"{GRAPH}/{version}/{sokvag.lstrip('/')}"


def _besked(svar: natvakt.Svar) -> str:
    try:
        fel = (json.loads(svar.text) or {}).get("error") or {}
    except (json.JSONDecodeError, AttributeError):
        fel = {}
    kod = fel.get("code")
    underkod = fel.get("error_subcode")
    for k in (underkod, kod):
        if k in _FELKODER:
            return _FELKODER[k]
    text = str(fel.get("message") or svar.text[:200] or svar.status_text)
    return f"Meta svarade {svar.status}: {text}"


async def graph_anrop(
    anslutning: dict[str, Any],
    token: str,
    metod: str,
    sokvag: str,
    *,
    kropp: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not token:
        raise KanalFel("Åtkomsttoken saknas för anslutningen.")
    try:
        svar = await natvakt.anropa(
            metod,
            graph_url(anslutning, sokvag),
            rubriker={"Authorization": f"Bearer {token}"},
            json_kropp=kropp,
            tidsgrans=15.0,
        )
    except natvakt.NatvaktError as fel:
        raise KanalFel(str(fel)) from fel
    except Exception as fel:  # noqa: BLE001 — nätfel blir KanalFel
        raise KanalFel(f"Meta gick inte att nå ({type(fel).__name__}).") from fel
    if not svar.ok:
        raise KanalFel(_besked(svar))
    try:
        return json.loads(svar.text) if svar.text.strip() else {}
    except json.JSONDecodeError:
        return {}
