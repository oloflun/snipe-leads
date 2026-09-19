"""Facebook Messenger via Metas Send API.

Anslutningen är EN Facebook-sida: `extern_id` = sidans id. Hemligheter:

  access_token   sidans åtkomsttoken (pages_messaging)
  app_secret     Meta-appens hemlighet, för signaturkontrollen
  verify_token   kundens egen sträng för GET-verifieringen

Inkommande: `messaging`-poster under `object: page`. Egna ekon
(`is_echo`), leverans- och läskvitton ignoreras. En knapptryckning
(postback) blir knappens titel som text.

Utgående: `messaging_type: RESPONSE`, alltså ett svar inom Metas
24-timmarsfönster. Messenger tar 2 000 tecken per meddelande, så längre svar
delas vid en meningsgräns.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import meta
from .bas import Inkommande, dela_text


class Messenger:
    kanal = "messenger"
    hemligheter_kravs = ("access_token", "app_secret", "verify_token")
    extern_id_betyder = "Facebook-sidans id"
    max_text = 2000

    def verifiera_prenumeration(self, params: Mapping[str, str], hemligheter: dict[str, str]) -> str | None:
        return meta.verifiera_prenumeration(params, hemligheter)

    async def verifiera(
        self, raw: bytes, rubriker: Mapping[str, str], hemligheter: dict[str, str], anslutning: dict[str, Any]
    ) -> bool:
        return meta.verifiera_signatur(raw, rubriker, hemligheter)

    def omedelbart_svar(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def tolka(self, payload: dict[str, Any], anslutning: dict[str, Any]) -> list[Inkommande]:
        if payload.get("object") != "page":
            return []
        ut: list[Inkommande] = []
        for entry in payload.get("entry") or []:
            if str(entry.get("id") or "") != anslutning["extern_id"]:
                continue
            for handelse in entry.get("messaging") or []:
                avsandare = str((handelse.get("sender") or {}).get("id") or "")
                if not avsandare or avsandare == anslutning["extern_id"]:
                    continue
                meddelande = handelse.get("message") or {}
                if meddelande.get("is_echo"):
                    continue
                if meddelande:
                    mid = str(meddelande.get("mid") or "")
                    text = str(meddelande.get("text") or "").strip()
                    if not text and meddelande.get("attachments"):
                        text = "[Kunden skickade en bilaga]"
                else:
                    postback = handelse.get("postback") or {}
                    mid = str(postback.get("mid") or "")
                    text = str(postback.get("title") or postback.get("payload") or "").strip()
                if not mid or not text:
                    continue
                ut.append(
                    Inkommande(
                        extern_meddelande_id=mid,
                        extern_anvandare=avsandare,
                        text=text,
                        adress={"psid": avsandare},
                    )
                )
        return ut

    async def skicka(
        self,
        anslutning: dict[str, Any],
        hemligheter: dict[str, str],
        *,
        mottagare: str,
        adress: dict[str, Any],
        text: str,
    ) -> None:
        for bit in dela_text(text, self.max_text):
            await meta.graph_anrop(
                anslutning,
                hemligheter.get("access_token", ""),
                "POST",
                "me/messages",
                kropp={
                    "recipient": {"id": adress.get("psid") or mottagare},
                    "messaging_type": "RESPONSE",
                    "message": {"text": bit},
                },
            )

    async def kontrollera(self, anslutning: dict[str, Any], hemligheter: dict[str, str]) -> str:
        svar = await meta.graph_anrop(anslutning, hemligheter.get("access_token", ""), "GET", "me?fields=id,name")
        if str(svar.get("id") or "") != anslutning["extern_id"]:
            return (
                f"Token hör till {svar.get('name') or 'en annan sida'} ({svar.get('id')}), "
                f"inte sidan {anslutning['extern_id']}."
            )
        return f"Ansluten till sidan {svar.get('name') or anslutning['extern_id']}."
