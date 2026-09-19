"""Microsoft Teams via Azure Bot Service (Bot Framework).

Anslutningen är EN bot: `extern_id` = botens Microsoft App ID. Hemligheter:

  app_password   klienthemligheten för botens app-registrering i Entra ID

Konfig:

  app_tenant_id  Entra-tenanten för en single-tenant-bot (standard sedan
                 Microsoft slutade skapa multi-tenant-botar 2025). Tom =
                 "botframework.com", alltså en äldre multi-tenant-bot.

## Inkommande: JWT, inte HMAC

Bot Framework signerar varje aktivitet med en JWT i Authorization-rubriken.
Den valideras här mot Microsofts publicerade nycklar:

  - signatur (RS256) med en nyckel ur Bot Frameworks JWKS,
  - utfärdare https://api.botframework.com, publik = botens App ID,
  - giltighetstid med fem minuters marginal,
  - `serviceurl`-anspråket måste vara aktivitetens serviceUrl. Det är dit
    svaret skickas, och utan kontrollen kunde en förfalskad aktivitet
    peka svaret (med vår token) till en godtycklig server,
  - nyckelns `endorsements` måste omfatta kanalen (msteams) när de finns.

Nycklarna cachas i 24 timmar och hämtas genom nätvakten.

## Utgående

En token för Bot Connector (client credentials mot Entra, scope
https://api.botframework.com/.default, cachad till strax före utgång) och ett
POST till `{serviceUrl}/v3/conversations/{id}/activities`. serviceUrl måste
dessutom ligga på en känd Microsoft-domän. Adressen sparas i
ss_channel_contacts och återanvänds för medarbetarsvar, så den prövas vid
varje sändning, inte bara vid mottagningen.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

import jwt

from ..integrationer import natvakt
from .bas import Inkommande, KanalFel, rubrik

OPENID_KONFIG = "https://login.botframework.com/v1/.well-known/openidconfiguration"
UTFARDARE = "https://api.botframework.com"
SCOPE = "https://api.botframework.com/.default"
NYCKEL_CACHE_SEKUNDER = 24 * 3600

_TILLATNA_TJANSTEDOMANER = (
    ".botframework.com",
    ".trafficmanager.net",
    ".teams.microsoft.com",
    ".teams.microsoft.us",
    ".botframework.us",
    ".botframework.azure.us",
)
_OMNAMNANDE = re.compile(r"<at>.*?</at>", re.IGNORECASE | re.DOTALL)
_TAGGAR = re.compile(r"<[^>]+>")

_nycklar: dict[str, Any] = {"hamtad": 0.0, "nycklar": {}}
_tokens: dict[str, tuple[float, str]] = {}


def tom_cache() -> None:
    _nycklar.update({"hamtad": 0.0, "nycklar": {}})
    _tokens.clear()


def tjanste_url_tillaten(service_url: str) -> bool:
    try:
        delar = urlsplit(service_url)
    except ValueError:
        return False
    vard = (delar.hostname or "").lower()
    return delar.scheme == "https" and any(vard.endswith(d) or vard == d.lstrip(".") for d in _TILLATNA_TJANSTEDOMANER)


async def _hamta_json(url: str) -> dict[str, Any]:
    svar = await natvakt.anropa("GET", url, tidsgrans=10.0)
    if not svar.ok:
        raise KanalFel(f"Microsoft svarade {svar.status} på {url}.")
    return json.loads(svar.text or "{}")


async def _signaturnycklar(tvinga: bool = False) -> dict[str, dict[str, Any]]:
    if not tvinga and _nycklar["nycklar"] and time.monotonic() - _nycklar["hamtad"] < NYCKEL_CACHE_SEKUNDER:
        return _nycklar["nycklar"]
    konfig = await _hamta_json(OPENID_KONFIG)
    jwks = await _hamta_json(str(konfig.get("jwks_uri") or ""))
    nycklar = {str(k.get("kid")): k for k in jwks.get("keys") or [] if k.get("kid")}
    _nycklar.update({"hamtad": time.monotonic(), "nycklar": nycklar})
    return nycklar


async def validera_token(auth: str, *, app_id: str, service_url: str, kanal_id: str) -> dict[str, Any]:
    """Kastar KanalFel om token inte bevisar att aktiviteten kommer från Bot Framework."""
    if not auth.lower().startswith("bearer "):
        raise KanalFel("Aktiviteten saknar Bearer-token.")
    token = auth[7:].strip()
    try:
        huvud = jwt.get_unverified_header(token)
    except jwt.PyJWTError as fel:
        raise KanalFel("Ogiltig token.") from fel
    kid = str(huvud.get("kid") or "")
    nycklar = await _signaturnycklar()
    if kid not in nycklar:
        # Microsoft roterar nycklar; en okänd kid kan vara en ny nyckel.
        nycklar = await _signaturnycklar(tvinga=True)
    jwk = nycklar.get(kid)
    if jwk is None:
        raise KanalFel("Token är signerad med en okänd nyckel.")
    endorsements = jwk.get("endorsements")
    if endorsements and kanal_id not in endorsements:
        raise KanalFel(f"Nyckeln är inte godkänd för kanalen {kanal_id!r}.")
    try:
        nyckel = jwt.PyJWK(jwk).key
        ansprak = jwt.decode(
            token,
            nyckel,
            algorithms=["RS256"],
            audience=app_id,
            issuer=UTFARDARE,
            leeway=300,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as fel:
        raise KanalFel(f"Token godtogs inte: {type(fel).__name__}.") from fel
    if str(ansprak.get("serviceurl") or "").rstrip("/") != service_url.rstrip("/"):
        raise KanalFel("Token gäller en annan serviceUrl än aktiviteten.")
    return ansprak


class Teams:
    kanal = "teams"
    hemligheter_kravs = ("app_password",)
    extern_id_betyder = "Botens Microsoft App ID"
    max_text = 20000

    def verifiera_prenumeration(self, params: Mapping[str, str], hemligheter: dict[str, str]) -> str | None:
        return None

    async def verifiera(
        self, raw: bytes, rubriker: Mapping[str, str], hemligheter: dict[str, str], anslutning: dict[str, Any]
    ) -> bool:
        try:
            aktivitet = json.loads(raw or b"{}")
            service_url = str(aktivitet.get("serviceUrl") or "")
            if not tjanste_url_tillaten(service_url):
                return False
            await validera_token(
                rubrik(rubriker, "authorization"),
                app_id=anslutning["extern_id"],
                service_url=service_url,
                kanal_id=str(aktivitet.get("channelId") or ""),
            )
        except (KanalFel, ValueError):
            return False
        return True

    def omedelbart_svar(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def tolka(self, payload: dict[str, Any], anslutning: dict[str, Any]) -> list[Inkommande]:
        if payload.get("type") != "message":
            return []
        fran = payload.get("from") or {}
        konversation = payload.get("conversation") or {}
        anvandare = str(fran.get("aadObjectId") or fran.get("id") or "")
        text = _OMNAMNANDE.sub("", str(payload.get("text") or ""))
        text = _TAGGAR.sub("", text).strip()
        mid = str(payload.get("id") or "")
        if not anvandare or not text or not mid or not konversation.get("id"):
            return []
        return [
            Inkommande(
                extern_meddelande_id=mid,
                extern_anvandare=anvandare,
                text=text,
                visningsnamn=fran.get("name") or None,
                adress={
                    "service_url": str(payload.get("serviceUrl") or ""),
                    "konversation": str(konversation["id"]),
                    "anvandar_id": str(fran.get("id") or ""),
                    "tenant": str(konversation.get("tenantId") or ""),
                },
            )
        ]

    async def _token(self, anslutning: dict[str, Any], hemligheter: dict[str, str]) -> str:
        app_id = anslutning["extern_id"]
        entra = (anslutning.get("konfig") or {}).get("app_tenant_id") or "botframework.com"
        nyckel = f"{app_id}:{entra}"
        cachad = _tokens.get(nyckel)
        if cachad and cachad[0] > time.time() + 60:
            return cachad[1]
        losen = hemligheter.get("app_password") or ""
        if not losen:
            raise KanalFel("Botens klienthemlighet saknas.")
        try:
            svar = await natvakt.anropa(
                "POST",
                f"https://login.microsoftonline.com/{quote(entra, safe='')}/oauth2/v2.0/token",
                rubriker={"Content-Type": "application/x-www-form-urlencoded"},
                innehall=urlencode(
                    {
                        "grant_type": "client_credentials",
                        "client_id": app_id,
                        "client_secret": losen,
                        "scope": SCOPE,
                    }
                ).encode("ascii"),
                tidsgrans=15.0,
            )
        except natvakt.NatvaktError as fel:
            raise KanalFel(str(fel)) from fel
        data: dict[str, Any] = {}
        try:
            data = json.loads(svar.text or "{}")
        except json.JSONDecodeError:
            pass
        if not svar.ok or not data.get("access_token"):
            beskrivning = str(data.get("error_description") or data.get("error") or svar.status)
            raise KanalFel(f"Microsoft gav ingen token för boten: {beskrivning.splitlines()[0][:200]}")
        _tokens[nyckel] = (time.time() + float(data.get("expires_in") or 3600), data["access_token"])
        return data["access_token"]

    async def skicka(
        self,
        anslutning: dict[str, Any],
        hemligheter: dict[str, str],
        *,
        mottagare: str,
        adress: dict[str, Any],
        text: str,
    ) -> None:
        service_url = str(adress.get("service_url") or "")
        konversation = str(adress.get("konversation") or "")
        if not tjanste_url_tillaten(service_url) or not konversation:
            raise KanalFel("Kontakten saknar en giltig Teams-adress. Kunden behöver skriva till boten först.")
        token = await self._token(anslutning, hemligheter)
        url = f"{service_url.rstrip('/')}/v3/conversations/{quote(konversation, safe='')}/activities"
        try:
            svar = await natvakt.anropa(
                "POST",
                url,
                rubriker={"Authorization": f"Bearer {token}"},
                json_kropp={"type": "message", "text": text[: self.max_text], "textFormat": "plain"},
                tidsgrans=15.0,
            )
        except natvakt.NatvaktError as fel:
            raise KanalFel(str(fel)) from fel
        except Exception as fel:  # noqa: BLE001
            raise KanalFel(f"Teams gick inte att nå ({type(fel).__name__}).") from fel
        if svar.status in (401, 403):
            _tokens.pop(f"{anslutning['extern_id']}:{(anslutning.get('konfig') or {}).get('app_tenant_id') or 'botframework.com'}", None)
            raise KanalFel("Teams nekade boten att skriva i konversationen.")
        if not svar.ok:
            raise KanalFel(f"Teams svarade {svar.status}.")

    async def kontrollera(self, anslutning: dict[str, Any], hemligheter: dict[str, str]) -> str:
        await self._token(anslutning, hemligheter)
        return "Botens app-ID och klienthemlighet godkändes av Microsoft Entra."
