"""Klassning av inkommande mejl: support, lead eller ej relaterat (plan del D).

Antons beställning 2026-10-01: Jev ska sortera kundtjänstinkorgen i vad som är
supportrelaterat, vad som inte hör hit alls, och vad som är ett lead — och
leads-kunder ska ha en egen inkorg under Iris, i samma system som
kundtjänstinkorgen.

Ordningen är billigast först och säkrast först (samma mönster som
Iris-profilen: koden avgör, Jev är förgrind, modellen formulerar):

  1. Kodregler, som fäller säkert: avsändare som avregistrerat sig →
     ej relaterat; avsändare som är ett prospekt eller en outreach-tråd →
     lead; nyhetsbrev (ämnesord) → ej relaterat; brevlådans syfte 'leads'
     → lead.
  2. Jev (choice support | lead | ej relaterat), bara när svaret är säkert
     (τ ≥ 0,9). Ett osäkert svar räknas inte.
  3. Standard: support — kundtjänstinkorgens vanliga väg, där LLM-triagen
     redan finns.

Varje beslut bär sin källa (`kalla`) så en manuell omklassning blir lärdata
och Jev går att mäta mot människan.

## Jev i inkorgen är en egen brytare (INKORG_JEV, 2026-10-04)

Kundmejl är kundens data, och Antons beslut 2026-09-30 (app/leads/jev.py)
är att Jev aldrig ser kundmejl eller e-postadresser. IRIS_JEV räcker därför
inte: inkorgen frågar Jev bara när `INKORG_JEV` säger det — `off` (standard,
bara kodregler), `prov` (knappen Provsortera, aldrig automatiskt) eller
`auto` (varje nytt mejl). Även då går bara avsändarens domän och en text
utan adresser och telefonnummer till Jev.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ..leads import jev

logger = logging.getLogger("snajp-support.klassning")

KLASSER = ("support", "lead", "ej_relaterat")
JEV_TROSKEL = 0.9

_NYHETSBREV = re.compile(
    r"\b(nyhetsbrev|newsletter|unsubscribe|avregistrera|avsluta prenumeration|no-?reply)\b",
    re.IGNORECASE,
)


def _doman(adress: str) -> str:
    return adress.rsplit("@", 1)[-1].casefold().strip() if "@" in adress else ""


def _webbdoman(website: str | None) -> str:
    w = re.sub(r"^https?://(www\.)?", "", str(website or "").casefold())
    return w.split("/")[0]


async def _prospektmatch(storage, tenant_id: str, fran: str) -> dict[str, Any] | None:
    """Prospektet avsändaren hör till: samma adress, eller samma domän som
    bolagets sajt (ett svar från en annan adress på samma domän)."""
    if not fran:
        return None
    doman = _doman(fran)
    for p in await storage.list_prospects(tenant_id, limit=500):
        if str(p.get("contact_email") or "").casefold() == fran:
            return p
        if doman and _webbdoman(p.get("website")) == doman and doman not in _ALLMANNA_DOMANER:
            return p
    return None


#: Gratisdomäner: samma domän betyder inte samma bolag.
_ALLMANNA_DOMANER = {
    "gmail.com", "hotmail.com", "outlook.com", "live.se", "hotmail.se", "icloud.com",
    "yahoo.com", "yahoo.se", "telia.com", "bredband.net", "me.com", "protonmail.com",
}


def jev_lage() -> str:
    from ..config import get_settings

    varde = (get_settings().inkorg_jev or "off").strip().lower()
    return varde if varde in ("off", "prov", "auto") else "off"


async def klassa(
    storage, tenant_id: str, email: dict[str, Any], *, syfte: str = "support", med_jev: bool = False
) -> dict[str, Any]:
    """→ {klass, kalla, stodrad, prospect_id, thread_id, jev}. Kastar aldrig.
    `med_jev`: anroparen har läst INKORG_JEV och får fråga Jev."""
    fran = str(email.get("from_email") or "").casefold().strip()
    amne = str(email.get("subject") or "")
    text = str(email.get("body_text") or "")

    # 1. Kodregler.
    try:
        if fran and fran in {s.casefold() for s in await storage.list_suppressions(tenant_id)}:
            return _utfall("ej_relaterat", "regel", "Avsändaren har avregistrerat sig.")
    except Exception:  # noqa: BLE001 — en trasig suppressionsläsning fäller inte klassningen
        logger.exception("Kunde inte läsa suppressions för %s", tenant_id)
    if _NYHETSBREV.search(amne) or (fran.startswith("noreply") or fran.startswith("no-reply")):
        return _utfall("ej_relaterat", "regel", "Nyhetsbrev eller automatutskick.")
    prospekt = await _prospektmatch(storage, tenant_id, fran)
    if prospekt:
        trad = None
        try:
            trad = await storage.find_outreach_thread(tenant_id, prospect_id=prospekt["id"])
        except Exception:  # noqa: BLE001
            logger.exception("Kunde inte slå upp tråden för %s", prospekt["id"])
        return _utfall(
            "lead", "regel", f"Avsändaren hör till prospektet {prospekt.get('company_name')}.",
            prospect_id=prospekt["id"], thread_id=str(trad["id"]) if trad else None,
        )
    if syfte == "leads":
        return _utfall("lead", "syfte", "Brevlådan används bara för leads.")

    # 2. Jev, bara när svaret är säkert. Ett osäkert svar fäller inget men
    # följer med som `jev`, så Provsortera kan visa vad Jev trodde.
    gissning = None
    if med_jev and jev.aktiv():
        try:
            svar = await jev.fraga(
                {
                    "sender_domain": _doman(fran),
                    "subject": jev._utan_personuppgifter(amne)[:200],
                    "excerpt": jev._utan_personuppgifter(text)[:1500],
                    "mailbox_purpose": syfte,
                },
                {
                    "klass": {
                        "type": "choice",
                        "instructions": (
                            "Is this email a customer support request to the company (support), "
                            "a reply or inquiry from a sales prospect (lead), or unrelated "
                            "(newsletter, spam, vendor pitch, automatic notice)?"
                        ),
                        "criteria": {"support": None, "lead": None, "ej_relaterat": None},
                    }
                },
            )
            val = (svar.get("klass") or {}).get("choice")
            konf = (svar.get("klass") or {}).get("confidence")
            if val in KLASSER and isinstance(konf, (int, float)):
                gissning = {"klass": val, "konfidens": round(float(konf), 2)}
                if konf >= JEV_TROSKEL:
                    return _utfall(val, "jev", f"Jev: {val} ({konf:.2f})", jev_svar=gissning)
        except Exception:  # noqa: BLE001 — Jev faller öppet
            logger.warning("Jev-klassningen gick inte att köra; standardvägen tar vid.")

    # 3. Standard.
    return _utfall("support", "standard", None, jev_svar=gissning)


def _utfall(klass: str, kalla: str, stodrad: str | None, *, prospect_id: str | None = None,
            thread_id: str | None = None, jev_svar: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"klass": klass, "kalla": kalla, "stodrad": stodrad, "prospect_id": prospect_id,
            "thread_id": thread_id, "jev": jev_svar}


def demo() -> None:
    """Minsta kontroll: nyhetsbrev och no-reply faller utan att röra lagret."""
    assert _NYHETSBREV.search("Vårt nyhetsbrev vecka 40")
    assert _doman("Anna@Alfa.SE") == "alfa.se"
    assert _webbdoman("https://www.alfa.se/kontakt") == "alfa.se"


if __name__ == "__main__":
    demo()
    print("ok")
