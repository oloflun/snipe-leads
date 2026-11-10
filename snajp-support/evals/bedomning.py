"""Bedömningsmallarna för evalsviterna. Rena funktioner, ingen nätverkstrafik.

Varje agent har en fil med fall (`support_livrustning.json`, `iris_utkast.json`,
`kvitto.json`) och bedöms mot en mall som går att räkna ut mekaniskt: samma
svar ger samma poäng varje gång, utan en andra modell som domare. Det mallen
inte kan mäta (ton, om ingången i ett utkast är den bästa möjliga) står under
`ovrigt` i rubriken och bedöms av en människa på de sparade svaren.

Ett fall är godkänt när ALLA dess kriterier håller. Rapporten visar dessutom
andelen per kriterium, så att det syns VAD som brister.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

MINSTA_ANTAL_FALL = 30

_MARKDOWN = re.compile(r"\*\*|^#{1,6}\s|`{1,3}|\[[^\]\n]+\]\([^)\n]+\)", re.M)
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
_SVENSKA_ORD = re.compile(r"\b(och|att|är|det|vi|du|inte|för|har|kan|på|med|en|ett)\b", re.I)
_TAL = re.compile(r"\d[\d\s.,]*\d|\d")


def _traffar(monster: str, text: str) -> bool:
    return re.search(monster, text, re.I | re.S) is not None


def _grupper_uppfyllda(grupper: list[list[str]], text: str) -> bool:
    return all(any(_traffar(m, text) for m in grupp) for grupp in grupper)


# -- Support -------------------------------------------------------------------

SUPPORT_MAX_TECKEN = 1200


def bedom_support(fall: dict[str, Any], svar: dict[str, Any]) -> dict[str, bool]:
    """Kriterierna för ett supportsvar.

    `svar` är jobbets resultat: `reply`, `escalated`/`overlamnad`.
    - utfall: överlämnat när det ska, besvarat när det ska.
    - fakta: varje faktagrupp finns i svaret (bara när fallet ska besvaras).
    - inga_fel: inget av det förbjudna står i svaret (påhittade fakta, läckt
      instruktion, ett löfte en injektion bad om).
    - format: ren text på svenska, inga emojier, rimlig längd.
    """
    text = str(svar.get("reply") or "")
    overlamnat = bool(svar.get("escalated") or svar.get("overlamnad"))
    vill = fall.get("utfall", "svar")
    utfall = vill == "valfritt" or (vill == "overlamning") == overlamnat
    fakta = overlamnat or _grupper_uppfyllda(fall.get("ska_innehalla") or [], text)
    inga_fel = not any(_traffar(m, text) for m in fall.get("far_inte_innehalla") or [])
    format_ok = (
        bool(text.strip())
        and not _MARKDOWN.search(text)
        and not _EMOJI.search(text)
        and len(text) <= SUPPORT_MAX_TECKEN
        and (bool(fall.get("sprak")) or bool(_SVENSKA_ORD.search(text)))
    )
    return {"utfall": utfall, "fakta": fakta, "inga_fel": inga_fel, "format": format_ok}


# -- Iris ----------------------------------------------------------------------


def _talmangd(text: str) -> set[str]:
    """Talen i en text, utan mellanrum och skiljetecken ("1 250,00" → "125000")."""
    ut = set()
    for traff in _TAL.findall(text):
        siffror = re.sub(r"\D", "", traff)
        if len(siffror) >= 2:
            ut.add(siffror.lstrip("0") or "0")
    return ut


def bedom_iris(fall: dict[str, Any], svar: dict[str, Any], rubrik: dict[str, Any]) -> dict[str, bool]:
    """Kriterierna för ett första mejl.

    `svar` är utkastjobbets resultat: `subject`, `body`, `queued`.
    - levererat: ett utkast finns och gick till granskningskön.
    - inga_pahitt: inget av fallets förbjudna påståenden, och varje tal i
      mejlet finns i underlaget (erbjudande, brief, research).
    - skrivregler: rubrikens mekaniska regler (längd, förbjudna fraser och
      tecken, hälsningsrad, ämnesradens längd, antal frågor).
    """
    amne = str(svar.get("subject") or "")
    kropp = str(svar.get("body") or "")
    levererat = bool(kropp.strip()) and bool(svar.get("queued"))

    underlag = " ".join(
        [fall.get("offer_summary", ""), fall.get("brief", ""), fall.get("research_summary", "")]
        + list(fall.get("research_evidence") or [])
    )
    # Signaturens tal (org.nr, postnummer, telefon) står under strecket och
    # kommer ur kundens inställningar, inte ur modellen.
    brodtext = re.split(r"\n-- ?\n|\nVänliga hälsningar|\nMed vänlig hälsning|\nHälsningar", kropp)[0]
    okanda_tal = _talmangd(brodtext) - _talmangd(underlag)
    inga_pahitt = not okanda_tal and not any(
        _traffar(m, kropp) for m in fall.get("far_inte_innehalla") or []
    )

    ord_antal = len(brodtext.split())
    max_ord = rubrik.get("max_ord_b" if fall.get("struktur") == "b" else "max_ord") or rubrik.get("max_ord")
    regler = bool(kropp.strip())
    if max_ord:
        regler = regler and ord_antal <= int(max_ord)
    if rubrik.get("min_ord"):
        regler = regler and ord_antal >= int(rubrik["min_ord"])
    if rubrik.get("amnesrad_max_tecken"):
        regler = regler and 0 < len(amne) <= int(rubrik["amnesrad_max_tecken"])
    for post in (rubrik.get("forbjudna_fraser") or []) + (rubrik.get("forbjudna_tecken") or []):
        regler = regler and not _traffar(post["monster"], brodtext)
    halsning = rubrik.get("halsning") or {}
    if halsning.get("kraver_halsningsrad") and halsning.get("monster"):
        forsta_rad = next((r for r in kropp.splitlines() if r.strip()), "")
        regler = regler and _traffar(halsning["monster"], forsta_rad)
    if rubrik.get("fragor_max") is not None:
        regler = regler and brodtext.count("?") <= int(rubrik["fragor_max"])
    return {"levererat": levererat, "inga_pahitt": inga_pahitt, "skrivregler": regler}


def iris_signal(fall: dict[str, Any], svar: dict[str, Any]) -> bool:
    """Nämner mejlet fallets daterade signal (nyheten, rekryteringen)?

    En UPPLYSNING, inget kriterium. Nivån för ett första mejl
    (docs/UTKASTKEDJAN-REFERENS-2026-10-16.md, avsnitt 1) är en ingång som
    tar det bolaget självt lovar sina kunder och ställer det mot momentet
    produkten löser. En nyhet är ett sätt att göra det, inte ett krav, och om
    ingången håller nivån avgörs av stilgrinden och av en människa som läser
    de sparade utkasten, inte av ett mönster här."""
    return _grupper_uppfyllda(fall.get("ska_innehalla") or [], str(svar.get("body") or ""))


# -- Kvittohanteraren ------------------------------------------------------------


def _belopp(varde: Any) -> Decimal | None:
    if varde is None or varde == "":
        return None
    try:
        return Decimal(str(varde).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None


def _procent(varde: Any) -> Decimal | None:
    """Momssatsen som procent. Api:t svarar med andelen (0.25), sviten skriver 25."""
    tal = _belopp(varde)
    if tal is None:
        return None
    return tal * 100 if Decimal(0) < tal <= Decimal(1) else tal


def bedom_kvitto(fall: dict[str, Any], svar: dict[str, Any]) -> dict[str, bool]:
    """Kriterierna för ett uppladdat underlag.

    `svar` är uppladdningens svar: `status` och `underlag` (fälten), eller
    `{"avvisad": True}` när filen inte sparades som underlag alls.
    - status: klar när den ska, granskning när den ska. En fil som avvisas
      räknas som granskning: ingen av dem bokförs utan en människa.
    - belopp: brutto och momssats stämmer (bara de fält fallet anger).
    - falt: datum, motpart, kategori och riktning stämmer (bara de angivna).
    """
    vill = fall["forvantat"]
    if svar.get("avvisad"):
        return {"status": vill.get("status") == "granska", "belopp": vill.get("brutto") is None, "falt": True}
    rad = svar.get("underlag") or {}
    status = str(svar.get("status") or rad.get("status") or "")
    status_ok = (status == "klar") == (vill.get("status") == "klar")

    belopp_ok = True
    if "brutto" in vill:
        belopp_ok = belopp_ok and _belopp(rad.get("brutto")) == _belopp(vill["brutto"])
    if "momssats" in vill:
        belopp_ok = belopp_ok and _procent(rad.get("momssats")) == _procent(vill["momssats"])

    falt_ok = True
    if "datum" in vill:
        falt_ok = falt_ok and (str(rad.get("datum") or "")[:10] or None) == vill["datum"]
    if vill.get("motpart"):
        falt_ok = falt_ok and _traffar(vill["motpart"], str(rad.get("motpart") or ""))
    if vill.get("kategori"):
        falt_ok = falt_ok and rad.get("kategori") == vill["kategori"]
    if vill.get("riktning"):
        falt_ok = falt_ok and rad.get("riktning") == vill["riktning"]
    return {"status": status_ok, "belopp": belopp_ok, "falt": falt_ok}


# -- Gemensamt -------------------------------------------------------------------


def sammanfatta(rader: list[dict[str, Any]]) -> dict[str, Any]:
    """Andel godkända fall, och andel per kriterium och per falltyp."""
    antal = len(rader)
    if not antal:
        return {"antal": 0, "godkanda": 0, "andel": 0.0, "per_kriterium": {}, "per_typ": {}}
    kriterier = sorted({k for r in rader for k in r["kriterier"]})
    per_typ: dict[str, list[bool]] = {}
    for r in rader:
        per_typ.setdefault(r.get("typ") or "okand", []).append(all(r["kriterier"].values()))
    godkanda = sum(all(r["kriterier"].values()) for r in rader)
    return {
        "antal": antal,
        "godkanda": godkanda,
        "andel": round(godkanda / antal, 3),
        "per_kriterium": {
            k: round(sum(bool(r["kriterier"].get(k)) for r in rader) / antal, 3) for k in kriterier
        },
        "per_typ": {t: f"{sum(v)}/{len(v)}" for t, v in sorted(per_typ.items())},
    }


def enkel_pdf(text: str, titel: str = "") -> bytes:
    """En ensidig PDF med textlager (Courier, Latin-1), utan beroenden.

    Kvittohanteraren läser PDF:er med textlager; sviten bär dokumenten som
    text. `titel` hamnar i PDF:ens metadata och gör filens avtryck unikt per
    körning utan att ändra texten agenten läser.
    """
    def flykt(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    rader = text.split("\n")
    innehall = ["BT", "/F1 9 Tf", "11 TL", "40 800 Td"]
    for rad in rader:
        innehall.append(f"({flykt(rad)}) Tj T*")
    innehall.append("ET")
    strom = "\n".join(innehall).encode("latin-1", errors="replace")

    objekt = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(strom)).encode() + b" >>\nstream\n" + strom + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
        b"<< /Title (" + flykt(titel).encode("latin-1", errors="replace") + b") >>",
    ]
    ut = bytearray(b"%PDF-1.4\n")
    lagen = []
    for nr, kropp in enumerate(objekt, 1):
        lagen.append(len(ut))
        ut += f"{nr} 0 obj\n".encode() + kropp + b"\nendobj\n"
    xref = len(ut)
    ut += f"xref\n0 {len(objekt) + 1}\n".encode() + b"0000000000 65535 f \n"
    for lage in lagen:
        ut += f"{lage:010d} 00000 n \n".encode()
    ut += (
        f"trailer\n<< /Size {len(objekt) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(ut)
