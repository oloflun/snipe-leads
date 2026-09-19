"""Kanaler: support-agenten i WhatsApp, Messenger, Slack och Teams (bd snipe-36u).

Ebbots löfte, som vi bygger motsvarigheten till: kunden möter agenten där den
redan är. Varje kanal är en adapter (bas.Adapter) med samma fem uppgifter:

  verifiera     bevisa att webhooken kommer från kanalen (HMAC för Meta och
                Slack, JWT för Teams). Aldrig valfritt.
  omedelbart    svar som kanalen kräver i själva webhooken (Slacks
                url_verification).
  tolka         kanalens format -> bas.Inkommande.
  skicka        ett svar tillbaka, via kanalens API och genom nätvakten.
  kontrollera   provkörning från portalen: fungerar nycklarna?

Flödet för ett inkommande meddelande (mottagning.py):

  webhook -> verifiera -> kvittera direkt (Slack ger tre sekunder) ->
  bakgrund: dubblettspärr -> kund (kontakt eller ny) -> support-agenten ->
  svar ut i samma kanal.

Medarbetarens svar i sömlös överlämning (snipe-1fl) går ut samma väg:
leverans.leverera, anropad efter overlamning.medarbetarsvar.
"""

from __future__ import annotations

from .bas import Adapter, Inkommande, KanalFel
from .messenger import Messenger
from .slack import Slack
from .teams import Teams
from .whatsapp import WhatsApp

ADAPTRAR: dict[str, Adapter] = {
    "whatsapp": WhatsApp(),
    "messenger": Messenger(),
    "slack": Slack(),
    "teams": Teams(),
}

KANALER = tuple(ADAPTRAR)

__all__ = ["ADAPTRAR", "KANALER", "Adapter", "Inkommande", "KanalFel"]
