"""WhatsApp Business via Metas Cloud API.

Anslutningen är ETT WhatsApp-nummer: `extern_id` = numrets phone_number_id
(inte telefonnumret, utan Metas id för det). Hemligheter:

  access_token   systemanvändarens token med whatsapp_business_messaging
  app_secret     Meta-appens hemlighet, för signaturkontrollen
  verify_token   valfri sträng kunden hittar på och klistrar in i Meta-appens
                 webhookinställning, för GET-verifieringen

Inkommande: `messages`-fältet i webhooken. Textmeddelanden, knapp- och
listsvar blir text. Bilder, röstmeddelanden och annat blir en rad som säger
vad kunden skickade, så att agenten kan be om texten i stället för att låtsas
att inget kom. Leveranskvitton (`statuses`) ignoreras.

Utgående: fri text inom 24-timmarsfönstret efter kundens senaste
meddelande. Svar utanför fönstret kräver en godkänd mall. Det avvisas av Meta
(131047) och blir ett begripligt KanalFel till medarbetaren.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import meta
from .bas import Inkommande, dela_text

_ICKE_TEXT = {
    "image": "[Kunden skickade en bild]",
    "audio": "[Kunden skickade ett röstmeddelande]",
    "video": "[Kunden skickade en video]",
    "document": "[Kunden skickade ett dokument]",
    "sticker": "[Kunden skickade en sticker]",
    "location": "[Kunden delade en plats]",
    "contacts": "[Kunden delade en kontakt]",
}


class WhatsApp:
    kanal = "whatsapp"
    hemligheter_kravs = ("access_token", "app_secret", "verify_token")
    extern_id_betyder = "Numrets phone_number_id i Meta (WhatsApp Manager > API-inställningar)"
    max_text = 4096

    def verifiera_prenumeration(self, params: Mapping[str, str], hemligheter: dict[str, str]) -> str | None:
        return meta.verifiera_prenumeration(params, hemligheter)

    async def verifiera(
        self, raw: bytes, rubriker: Mapping[str, str], hemligheter: dict[str, str], anslutning: dict[str, Any]
    ) -> bool:
        return meta.verifiera_signatur(raw, rubriker, hemligheter)

    def omedelbart_svar(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def tolka(self, payload: dict[str, Any], anslutning: dict[str, Any]) -> list[Inkommande]:
        if payload.get("object") != "whatsapp_business_account":
            return []
        ut: list[Inkommande] = []
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                if change.get("field") != "messages":
                    continue
                varde = change.get("value") or {}
                # En Meta-app kan ha flera nummer; bara det här numrets
                # meddelanden hör till den här anslutningen.
                if str((varde.get("metadata") or {}).get("phone_number_id") or "") != anslutning["extern_id"]:
                    continue
                namn = {
                    str(c.get("wa_id")): ((c.get("profile") or {}).get("name") or None)
                    for c in varde.get("contacts") or []
                }
                for m in varde.get("messages") or []:
                    fran = str(m.get("from") or "")
                    mid = str(m.get("id") or "")
                    if not fran or not mid:
                        continue
                    text = self._text(m)
                    if not text:
                        continue
                    ut.append(
                        Inkommande(
                            extern_meddelande_id=mid,
                            extern_anvandare=fran,
                            text=text,
                            visningsnamn=namn.get(fran),
                            telefon=f"+{fran}" if fran.isdigit() else fran,
                            adress={"wa_id": fran},
                        )
                    )
        return ut

    @staticmethod
    def _text(m: dict[str, Any]) -> str:
        typ = m.get("type")
        if typ == "text":
            return str((m.get("text") or {}).get("body") or "").strip()
        if typ == "button":
            return str((m.get("button") or {}).get("text") or "").strip()
        if typ == "interactive":
            inter = m.get("interactive") or {}
            svar = inter.get("button_reply") or inter.get("list_reply") or {}
            return str(svar.get("title") or "").strip()
        if typ in _ICKE_TEXT:
            bildtext = str((m.get(typ) or {}).get("caption") or "").strip()
            return f"{_ICKE_TEXT[typ]} {bildtext}".strip()
        return ""

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
                f"{anslutning['extern_id']}/messages",
                kropp={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": adress.get("wa_id") or mottagare,
                    "type": "text",
                    "text": {"preview_url": False, "body": bit},
                },
            )

    async def kontrollera(self, anslutning: dict[str, Any], hemligheter: dict[str, str]) -> str:
        svar = await meta.graph_anrop(
            anslutning, hemligheter.get("access_token", ""), "GET",
            f"{anslutning['extern_id']}?fields=display_phone_number,verified_name",
        )
        return f"Ansluten till {svar.get('verified_name') or 'numret'} ({svar.get('display_phone_number') or anslutning['extern_id']})."
