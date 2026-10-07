"""Mejlsignaturen i Iris utgående leads-mejl — byggd i KOD, aldrig av modellen.

## Varför den här filen finns

Signaturen är tenantens avsändaridentitet i mejlet — namn, titel, telefon
och logotyp. Precis som utskicksfoten (`utskicksfot.py`) får den inte bero
på att modellen råkar komma ihåg den: den läggs på av kod vid KÖNINGEN, så
att den text en människa granskar i dashboarden är exakt den text som
skickas. Konfigurationen bor i `agent_configs.settings["signatur"]`
(leads-agenten) och sätts via PUT /api/leads/config.

## Text och HTML

Sändvägen är ren text i grunden, och textversionen av signaturen är den som
ligger i `send_queue.body` och granskas. Logotypen går inte att uttrycka i
text — den finns bara i HTML-delen, som `bygg_html` renderar deterministiskt
ur SAMMA brödtext i sändögonblicket (multipart/alternative: mottagare med
HTML-klient ser loggan, textklienter ser exakt granskningstexten). HTML-delen
är alltså en presentation av den granskade texten plus logotypen — aldrig
annan text, aldrig modellskriven.

## Ordningen vid köningen

textkvalitet -> signatur -> lagstadgad fot. Signaturen läggs på EFTER
kvalitetskontrollen (den är kodens egen text och ska inte LLM-korras) och
FÖRE foten (foten är alltid sist i mejlet, se utskicksfot.py).
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

#: Fälten i settings["signatur"], i den ordning textblocket renderar dem.
_TEXTFALT = ("namn", "titel", "telefon", "epost")
_PLATSFALT = ("ort", "webb")

#: Samma mönster som `leads_agent._DANGLING_SIGN_OFF`. Duplicerat med flit —
#: leads_agent importerar paket som i sin tur når hit, och en import åt andra
#: hållet hade knutit ihop agentmodulen med köningsvägen. Faller mönstren
#: isär fångas det av tests/leads/test_signatur.py.
_HANGANDE_HALSNING = re.compile(
    r"(?:med\s+vänliga\s+hälsningar|vänliga\s+hälsningar|hälsningar|mvh|bästa\s+hälsningar)\s*,\s*$",
    re.IGNORECASE,
)


def normalisera(val: Any) -> dict[str, str] | None:
    """Ett användbart signaturvärde, eller None.

    None betyder "ingen signatur": fältet saknas, är avstängt (`aktiv: false`)
    eller saknar namn — ett signaturblock utan namn är inte en signatur.
    Alla värden strippas och klipps; en signatur är korta rader, och ett
    inklistrat stycke på tusen tecken i telefonfältet ska inte nå ett mejl.
    """
    if not isinstance(val, dict):
        return None
    if val.get("aktiv") is False:
        return None
    ren: dict[str, str] = {}
    for falt in (*_TEXTFALT, *_PLATSFALT, "bolag", "logotyp_url"):
        text = str(val.get(falt) or "").strip()
        # En rad per fält: radbrytningar i ett fält hade förskjutit blocket
        # som bygg_html letar efter i brödtexten.
        text = " ".join(text.split())
        if text:
            ren[falt] = text[:200]
    if not ren.get("namn"):
        return None
    # Logotypen bäddas in i mejl hos mottagare — bara https duger. Ett http-
    # eller relativt värde tappas tyst hellre än att ge en trasig bild.
    url = ren.get("logotyp_url", "")
    if url and not url.startswith("https://"):
        ren.pop("logotyp_url", None)
    return ren


def bygg_signaturtext(sig: dict[str, str]) -> str:
    """Textversionen — den som köas, granskas och skickas som textdel.

    Tre grupper med blankrad emellan: person (namn/titel/telefon/epost),
    plats (ort/webb), bolag. Logotypen finns inte här; den hör HTML-delen
    till (se modulens docstring).
    """
    grupper: list[str] = []
    person = [sig[f] for f in _TEXTFALT if sig.get(f)]
    if person:
        grupper.append("\n".join(person))
    plats = [sig[f] for f in _PLATSFALT if sig.get(f)]
    if plats:
        grupper.append("\n".join(plats))
    if sig.get("bolag"):
        grupper.append(sig["bolag"])
    return "\n\n".join(grupper)


def med_signatur(brodtext: str, sig: dict[str, str], *, halsning: str | None = None) -> str:
    """Lägger på signaturen om den saknas. Idempotent.

    En uppföljning kan vara byggd ur ett tidigare mejl som redan bär
    signaturen — kontrollen görs på namnraden följd av titel-/telefonraden,
    det minsta som är unikt för blocket (namnet ensamt kan modellen ha
    skrivit själv i hälsningsfrasen).

    Slutar brödtexten med en hängande hälsningsfras ("Med vänliga
    hälsningar,") fullbordar signaturens namnrad den direkt, utan blankrad —
    samma defekt som `leads_agent.sign_off` lagar, och signaturen ska inte
    återinföra den med ett namn två rader ned.
    """
    text = bygg_signaturtext(sig)
    if not text:
        return brodtext
    rader = text.split("\n")
    nyckel = "\n".join(rader[:2]) if len(rader) > 1 else rader[0]
    if nyckel in brodtext:
        return brodtext
    stripped = brodtext.rstrip()
    if _HANGANDE_HALSNING.search(stripped):
        return f"{stripped}\n{text}"
    # Slutar brödtexten redan med avsändarnamnet (sign_off satte dit det, eller
    # modellen skrev det) ersätter signaturens namnrad den raden — annars hade
    # mejlet slutat "…hälsningar,\nSebastian\n\nSebastian Bergman\n…".
    sista = stripped.rsplit("\n", 1)[-1].strip()
    if sista and (sista == sig["namn"] or sig["namn"].startswith(f"{sista} ")):
        stripped = stripped[: len(stripped) - len(stripped.rsplit("\n", 1)[-1])].rstrip()
        return f"{stripped}\n{text}"
    if _AVSLUTNING.search(stripped):
        return f"{stripped}\n{text}"
    # Ingen avslutning alls: mejlet gick rakt från uppmaningen till namnet
    # (uppmätt 2026-10-07 i 16 av 16 utkast i development). Hälsningsfrasen
    # läggs på i kod, på mejlets språk.
    if halsning:
        return f"{stripped}\n\n{halsning}\n{text}"
    return f"{stripped}\n\n{text}"


#: En avslutande hälsningsrad, med eller utan komma, svensk eller engelsk.
#: Lösare än _HANGANDE_HALSNING (som speglar leads_agent och måste hållas lik).
_AVSLUTNING = re.compile(
    r"\n[ \t]*(?:(?:med\s+)?(?:vänliga|bästa|varma)\s+hälsningar|hälsningar|mvh|vänligen|"
    r"best\s+regards|kind\s+regards|regards|best\s+wishes|best|cheers)[ \t]*[,!.]?[ \t]*$",
    re.IGNORECASE,
)

#: Hälsningsfrasen per språk när brödtexten saknar en (`med_signatur`).
HALSNING = {"sv": "Vänliga hälsningar,", "en": "Best regards,"}


#: Första raden i den lagstadgade foten (utskicksfot.bygg_fot). Duplicerad
#: hellre än importerad, av samma skäl som _HANGANDE_HALSNING ovan.
_FOTSTART = "\n--\n"


def dela_utkast(body: str, sig: dict[str, str] | None) -> tuple[str, str]:
    """(brödtext, svans) — svansen är kodens egen text sist i mejlet:
    signaturblocket och/eller den lagstadgade foten.

    Granskningsvyn låter människan och AI-knapparna (Förbättra, Kortare …)
    arbeta på brödtexten och bara den. Förut låg hela mejlet i textrutan, och
    en omskrivning kunde stryka eller skriva om signaturen — då hittade
    `bygg_html` inte blocket och mejlet gick ut utan logga — eller foten,
    som send_guard sedan stoppade utskicket på.
    """
    text = body or ""
    kandidater: list[int] = []
    sigtext = bygg_signaturtext(sig) if sig else ""
    if sigtext and (i := text.find(sigtext)) >= 0:
        kandidater.append(i)
    if (i := text.find(_FOTSTART)) >= 0:
        kandidater.append(i + 1)
    if not kandidater:
        return text.rstrip(), ""
    start = min(kandidater)
    return text[:start].rstrip(), text[start:].strip("\n")


def sla_ihop(
    brodtext: str, svans: str, sig: dict[str, str] | None, *, halsning: str | None = None
) -> str:
    """Inversen av `dela_utkast`: den redigerade brödtexten plus den
    oförändrade svansen. Börjar svansen med signaturen går skarven genom
    `med_signatur`, som fullbordar en hängande hälsningsfras och stryker ett
    avsändarnamn som omskrivningen själv skrev sist."""
    brodtext = (brodtext or "").rstrip()
    if not svans:
        return brodtext
    sigtext = bygg_signaturtext(sig) if sig else ""
    if sigtext and svans.startswith(sigtext):
        resten = svans[len(sigtext) :]
        return med_signatur(brodtext, sig, halsning=halsning).rstrip() + resten  # type: ignore[arg-type]
    return f"{brodtext}\n\n{svans}"


def _radbryt_till_html(text: str) -> str:
    """Escapad text med <br> — stycken hålls ihop, inget tolkas som markup."""
    stycken = _html.escape(text).split("\n\n")
    return "".join(
        f'<p style="margin:0 0 1em 0;">{stycke.replace(chr(10), "<br>")}</p>'
        for stycke in stycken
        if stycke.strip()
    )


def _signatur_html(sig: dict[str, str]) -> str:
    """Signaturblocket med logotypen infogad mellan persongruppen och platsen
    — samma position som i tenantens egen Gmail-signatur. Inline-styles och
    en enkel div-struktur: mejlklienter stödjer varken <style>-block eller
    externa ark."""
    rad = '<div style="margin:0;">{}</div>'
    delar: list[str] = []
    person = [rad.format(_html.escape(sig[f])) for f in _TEXTFALT if sig.get(f)]
    if person:
        person[0] = f'<div style="margin:0;font-weight:bold;">{_html.escape(sig["namn"])}</div>'
        delar.append("".join(person))
    if sig.get("logotyp_url"):
        delar.append(
            f'<img src="{_html.escape(sig["logotyp_url"], quote=True)}" alt="{_html.escape(sig.get("bolag") or sig["namn"])}"'
            ' width="120" style="display:block;width:120px;height:auto;border:0;margin:12px 0;">'
        )
    plats: list[str] = []
    if sig.get("ort"):
        plats.append(rad.format(_html.escape(sig["ort"])))
    if sig.get("webb"):
        webb = _html.escape(sig["webb"])
        href = sig["webb"] if sig["webb"].startswith("http") else f"https://{sig['webb']}"
        plats.append(
            f'<div style="margin:0;"><a href="{_html.escape(href, quote=True)}" style="color:#1a1a1a;">{webb}</a></div>'
        )
    if plats:
        delar.append("".join(plats))
    if sig.get("bolag"):
        delar.append(rad.format(_html.escape(sig["bolag"])))
    inre = '<div style="height:12px;line-height:12px;">&nbsp;</div>'.join(delar)
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:13px;'
        f'line-height:1.5;color:#1a1a1a;margin:1.5em 0 0 0;">{inre}</div>'
    )


def bygg_html(brodtext: str, sig: dict[str, str]) -> str:
    """HTML-delen av mejlet, renderad ur den GRANSKADE texten.

    Textblocket som `med_signatur` la dit byts mot HTML-signaturen (med
    logotyp); texten före och efter (brödtext respektive lagstadgad fot)
    escapas och radbryts, ingenting annat. Finns blocket inte i texten — ett
    äldre köat utkast, en tenant som slog på signaturen efter köningen —
    renderas texten som den är, utan logga: HTML-delen får aldrig visa något
    som inte granskats.
    """
    text = bygg_signaturtext(sig)
    index = brodtext.find(text) if text else -1
    if index < 0:
        kropp = _radbryt_till_html(brodtext)
    else:
        fore = brodtext[:index].rstrip()
        efter = brodtext[index + len(text) :].strip("\n")
        kropp = _radbryt_till_html(fore) + _signatur_html(sig)
        if efter.strip():
            kropp += (
                '<div style="margin-top:1.5em;color:#6b6b6b;font-size:12px;">'
                + _radbryt_till_html(efter)
                + "</div>"
            )
    return (
        '<!doctype html><html><body style="margin:0;padding:0;background:#ffffff;">'
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;'
        f'line-height:1.6;color:#1a1a1a;max-width:600px;padding:16px;">{kropp}</div>'
        "</body></html>"
    )
