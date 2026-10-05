"""Kodens kontroll av kvittohanterarens svar — det modellen inte får avgöra ensam.

Prompten (`agent-core/prompts/kvittohanterare-systemprompt.md`) ber modellen
räkna, flagga och sätta status. Allt det som går att avgöra MEKANISKT görs
här igen, och kodens svar vinner:

  * kontrollräkningarna i 3.3 (Decimal, ±1 kr) — modellen räknar sämre än kod
  * förfallodagarna mot dagens datum (`förfaller_snart`, `förfallen`)
  * kontrollsiffror i orgnummer, bankgiro, plusgiro, OCR, IBAN
  * att varje belopp och nummer faktiskt STÅR i texten modellen fick — ett
    belopp som inte går att hitta stryks (avsnitt 3: extrahera aldrig ett
    värde som inte står i underlaget)
  * dubbletter och bytta betalningsuppgifter mot ALLA tidigare underlag, inte
    bara de som fick plats i prompten
  * status enligt 9.2, ur flaggorna och säkerhetsnivåerna

Kontrollen går åt båda hållen: en flagga koden kan motbevisa (till exempel
`belopp_stämmer_inte` när summorna går ihop på öret) stryks, så att ett
kvitto inte hamnar hos en människa för att modellen räknat fel. Det är
halva vägen till "sällan eskalera".
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from . import kontrollsiffror

KLASSER = (
    "UNDERLAG_BILAGA",
    "UNDERLAG_I_TEXT",
    "UNDERLAG_ENDAST_LÄNK",
    "PÅMINNELSE",
    "EJ_UNDERLAG",
)
DOKUMENTTYPER = (
    "kvitto",
    "leverantörsfaktura",
    "kreditfaktura",
    "kontoutdrag_eller_specifikation",
    "okänd",
)
KLAR = "KLAR_FÖR_GRANSKNING"
BEHOVER = "BEHÖVER_GRANSKNING"
PRIORITERAD = "PRIORITERAD_GRANSKNING"
MANUELL_HAMTNING = "KRÄVER_MANUELL_HÄMTNING"
GRANSKNINGSSTATUSAR = (KLAR, BEHOVER, PRIORITERAD, MANUELL_HAMTNING)

FLAGGOR = (
    "oläsligt",
    "belopp_stämmer_inte",
    "saknar_moms",
    "saknar_obligatoriska_fält",
    "utländsk_valuta",
    "utländsk_leverantör",
    "omvänd_skattskyldighet",
    "tvetydigt_datum",
    "osäker_klassning",
    "osäker_dokumenttyp",
    "fel_mottagare",
    "möjligt_privat_köp",
    "möjlig_dubblett",
    "misstänkt_bedrägeri",
    "instruktion_i_innehåll",
    "många_rader",
    "förfaller_snart",
    "förfallen",
)
#: 9.2: flaggor som inte hindrar KLAR_FÖR_GRANSKNING.
_TILLATNA_VID_KLAR = frozenset({"utländsk_valuta", "förfaller_snart"})
#: 9.2: flaggor som ger PRIORITERAD_GRANSKNING.
_PRIORITERADE = frozenset(
    {"misstänkt_bedrägeri", "instruktion_i_innehåll", "förfallen", "belopp_stämmer_inte"}
)

SAKERHETER = ("säker", "osäker", "saknas")

#: Avsnitt 6.1–6.5 utom rader, i promptens ordning.
FALT = (
    "leverantör_namn",
    "leverantör_orgnummer",
    "leverantör_momsregnummer",
    "leverantör_land",
    "dokumentnummer",
    "dokumentdatum",
    "förfallodatum",
    "köpare_namn",
    "köpare_orgnummer",
    "valuta",
    "totalbelopp",
    "belopp_exkl_moms",
    "momsbelopp_totalt",
    "öresavrundning",
    "betalstatus",
    "betalsätt",
    "bankgiro",
    "plusgiro",
    "iban",
    "bic",
    "ocr_referens",
    "beskrivning",
)
BELOPPSFALT = ("totalbelopp", "belopp_exkl_moms", "momsbelopp_totalt", "öresavrundning")
DATUMFALT = ("dokumentdatum", "förfallodatum")
OBLIGATORISKA = ("leverantör_namn", "dokumentdatum", "totalbelopp")
#: Fält med kontrollsiffra → typen `kontrollsiffror.kontrollera` känner.
NUMMERFALT = {
    "leverantör_orgnummer": "orgnummer",
    "köpare_orgnummer": "orgnummer",
    "leverantör_momsregnummer": "momsregnummer",
    "bankgiro": "bankgiro",
    "plusgiro": "plusgiro",
    "iban": "iban",
    "ocr_referens": "ocr",
}
#: Nummer som ska stå i texten tecken för tecken (bortsett från avskiljare).
_IDENTIFIERARE = (*NUMMERFALT, "dokumentnummer", "bic")
#: Betalningsuppgifterna avsnitt 8.3 jämför mot tidigare underlag.
BETALNINGSFALT = ("bankgiro", "plusgiro", "iban")
_BETALSTATUSAR = ("betald", "obetald", "okänd")
MAX_RADER = 30

_TOLERANS = Decimal("1")

#: Text riktad till en AI eller till granskningen (avsnitt 8.1). Medvetet
#: smal: en träff ger en prioriterad granskning, så ordet "AI" i en faktura
#: från en AI-leverantör får inte räcka.
_INSTRUKTION = re.compile(
    r"(?i)("
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)"
    r"|ignorera (alla )?(tidigare|ovanstående|föregående) (instruktioner|regler)"
    r"|disregard (the |all )?(previous |above )?instructions"
    r"|markera (detta |den här |fakturan |underlaget )?som (godkänd|godkänt|betald)"
    r"|mark (this |the invoice )?as (approved|paid)"
    r"|(note|message|instruction)s? (to|for) (the )?(ai|assistant|language model|llm)"
    r"|(till|för) (ai|ai-systemet|assistenten|språkmodellen)\s*:"
    r"|system ?prompt"
    r"|you are an? (ai|assistant|language model)"
    r"|du är en (ai|assistent|språkmodell)"
    r")"
)


def _ascii(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    ).lower()


#: Modellen kan svara med "leverantor_namn" i stället för "leverantör_namn".
_FALTNYCKLAR = {_ascii(f): f for f in (*FALT, "à_pris")}
_FLAGGNYCKLAR = {_ascii(f): f for f in FLAGGOR}
_KLASSNYCKLAR = {_ascii(k): k for k in KLASSER}
_TYPNYCKLAR = {_ascii(t): t for t in DOKUMENTTYPER}
_SAKERHETSNYCKLAR = {_ascii(s): s for s in SAKERHETER}


def _hamta(obj: dict, nyckel: str, default: Any = None) -> Any:
    """`obj[nyckel]`, eller samma nyckel stavad utan å/ä/ö."""
    if not isinstance(obj, dict):
        return default
    if nyckel in obj:
        return obj[nyckel]
    mal = _ascii(nyckel)
    for k, v in obj.items():
        if isinstance(k, str) and _ascii(k) == mal:
            return v
    return default


# -- Tolkning av värden -------------------------------------------------------


def tolka_belopp(varde: Any) -> Decimal | None:
    """1250.5, "1250.50", "1 250,50 kr", "-1 250,50" → Decimal. Annars None."""
    if varde is None or isinstance(varde, bool):
        return None
    if isinstance(varde, (int, Decimal)):
        return Decimal(varde)
    if isinstance(varde, float):
        return Decimal(str(varde))
    if not isinstance(varde, str):
        return None
    text = re.sub(r"(?i)\b(kr|sek|kronor|eur|usd|gbp|nok|dkk)\b|[€$£]", "", varde)
    text = text.replace(" ", "").replace(" ", "").replace(" ", "").strip()
    if not text:
        return None
    negativ = text.startswith("-") or text.endswith("-") or text.startswith("−")
    text = text.strip("-−+")
    sista = max(text.rfind(","), text.rfind("."))
    if sista != -1:
        decimaler = text[sista + 1 :]
        heltal = re.sub(r"[.,]", "", text[:sista])
        text = f"{heltal}.{decimaler}" if len(decimaler) in (1, 2) else f"{heltal}{decimaler}"
    try:
        tal = Decimal(text)
    except InvalidOperation:
        return None
    return -tal if negativ else tal


def _oren(tal: Decimal | None) -> Decimal | None:
    """Belopp med två decimaler: modellen svarar ofta med JSON-talet 1250.0,
    och det ska sparas och visas som 1250.00. Aldrig avrundning av ören —
    ett belopp med fler decimaler lämnas som det står."""
    if tal is None or tal.as_tuple().exponent < -2:
        return tal
    return tal.quantize(Decimal("0.01"))


def tolka_datum(varde: Any) -> str | None:
    """Bara ÅÅÅÅ-MM-DD godtas — prompten kräver formatet, och ett annat
    format är exakt den tvetydighet (03/04) som ska flaggas, inte tolkas."""
    if not isinstance(varde, str):
        return None
    try:
        return date.fromisoformat(varde.strip()).isoformat()
    except ValueError:
        return None


def _kr(tal: Decimal | None) -> str:
    return "" if tal is None else f"{tal:.2f}"


# -- Normalisering av modellens svar ------------------------------------------


def _tomt_falt() -> dict[str, Any]:
    return {"värde": None, "säkerhet": "saknas", "källa": None}


def _normalisera_falt(namn: str, rat: Any, flaggor: set[str]) -> dict[str, Any]:
    if not isinstance(rat, dict):
        rat = {"värde": rat, "säkerhet": "säker" if rat not in (None, "") else "saknas"}
    varde = _hamta(rat, "värde")
    sakerhet = _SAKERHETSNYCKLAR.get(_ascii(str(_hamta(rat, "säkerhet") or "")), "säker")
    kalla = _hamta(rat, "källa")
    kalla = str(kalla).strip() if kalla not in (None, "") else None

    if namn in BELOPPSFALT:
        varde = _oren(tolka_belopp(varde))
    elif namn in DATUMFALT:
        if varde not in (None, "") and tolka_datum(varde) is None:
            # Ett datum i annat format än ÅÅÅÅ-MM-DD: modellen har inte
            # kunnat avgöra det entydigt. Värdet stryks och flaggas.
            flaggor.add("tvetydigt_datum")
            varde = None
        else:
            varde = tolka_datum(varde)
    elif namn == "valuta":
        varde = str(varde).strip().upper() if varde not in (None, "") else None
        if varde is not None and not re.fullmatch(r"[A-Z]{3}", varde):
            varde = None
    elif namn == "betalstatus":
        varde = str(varde).strip().lower() if varde not in (None, "") else None
        if varde not in _BETALSTATUSAR:
            varde = None
    else:
        varde = str(varde).strip() if varde not in (None, "") else None

    if varde is None:
        return {"värde": None, "säkerhet": "saknas", "källa": None}
    if sakerhet == "saknas":
        sakerhet = "osäker"
    return {"värde": varde, "säkerhet": sakerhet, "källa": kalla}


def _normalisera_underlag(rat: Any) -> dict[str, Any]:
    rat = rat if isinstance(rat, dict) else {}
    flaggor: set[str] = set()
    for f in _hamta(rat, "flaggor", []) or []:
        kanonisk = _FLAGGNYCKLAR.get(_ascii(str(f)))
        if kanonisk:
            flaggor.add(kanonisk)

    typ = _TYPNYCKLAR.get(_ascii(str(_hamta(rat, "dokumenttyp") or "")))
    if typ is None:
        typ = "okänd"
    if typ == "okänd":
        flaggor.add("osäker_dokumenttyp")

    ratt_falt = _hamta(rat, "fält", {}) or {}
    falt = {
        namn: _normalisera_falt(namn, _hamta(ratt_falt, namn), flaggor) for namn in FALT
    }

    moms_per_sats = []
    for post in _hamta(rat, "moms_per_sats", []) or []:
        if not isinstance(post, dict):
            continue
        sats = tolka_belopp(_hamta(post, "sats"))
        if sats is None:
            continue
        moms_per_sats.append(
            {
                "sats": sats,
                "underlag": _oren(tolka_belopp(_hamta(post, "underlag"))),
                "moms": _oren(tolka_belopp(_hamta(post, "moms"))),
            }
        )

    rader_rat = _hamta(rat, "rader")
    rader: list[dict[str, Any]] | None
    if rader_rat is None:
        rader = None
    else:
        rader = []
        for rad in rader_rat if isinstance(rader_rat, list) else []:
            if not isinstance(rad, dict):
                continue
            rader.append(
                {
                    "beskrivning": str(_hamta(rad, "beskrivning") or "").strip() or None,
                    "antal": tolka_belopp(_hamta(rad, "antal")),
                    "à_pris": tolka_belopp(_hamta(rad, "à_pris")),
                    "belopp": tolka_belopp(_hamta(rad, "belopp")),
                    "momssats": tolka_belopp(_hamta(rad, "momssats")),
                }
            )
        if len(rader) > MAX_RADER:
            rader = None
            flaggor.add("många_rader")

    kategori = _hamta(rat, "kategori")
    kallfiler = [str(k) for k in (_hamta(rat, "källfiler", []) or []) if str(k).strip()]
    dubblett = _hamta(rat, "möjlig_dubblett_av")
    return {
        "dokumenttyp": typ,
        "status": None,
        "fält": falt,
        "moms_per_sats": moms_per_sats,
        "rader": rader,
        "kategori": str(kategori).strip() if isinstance(kategori, str) and kategori.strip() else None,
        "kategori_är_förslag": True,
        "kontrollräkningar": {
            "netto_plus_moms_lika_total": None,
            "rader_lika_total": None,
            "moms_lika_sats": None,
        },
        "möjlig_dubblett_av": str(dubblett) if dubblett not in (None, "") else None,
        "flaggor": flaggor,
        "källfiler": kallfiler,
    }


def normalisera_resultat(rat: Any, meddelande_id: str) -> dict[str, Any]:
    """Modellens JSON till promptens format, strikt: okända flaggor och
    klasser stryks, saknade fält läggs till som `null`/`saknas`."""
    rat = rat if isinstance(rat, dict) else {}
    underlag = [_normalisera_underlag(u) for u in (_hamta(rat, "underlag", []) or []) if isinstance(u, dict)]
    klass = _KLASSNYCKLAR.get(_ascii(str(_hamta(rat, "klass") or "")))
    if klass is None:
        klass = "UNDERLAG_I_TEXT" if underlag else "EJ_UNDERLAG"
        if underlag:
            for u in underlag:
                u["flaggor"].add("osäker_klassning")
    if klass == "EJ_UNDERLAG":
        # 8.4: ett mejl som inte är ett underlag lämnar ingenting efter sig.
        underlag = []
    return {
        "meddelande_id": meddelande_id,
        "klass": klass,
        "underlag": underlag,
        "intern_notering": str(_hamta(rat, "intern_notering") or "").strip(),
    }


# -- Finns värdet i texten? ---------------------------------------------------

_MANADER_SV = (
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december",
)
_MANADER_EN = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)


def _rensa_text(text: str) -> str:
    return (text or "").replace(" ", " ").replace(" ", " ").replace(" ", " ")


def _beloppsformer(tal: Decimal) -> list[str]:
    tal = abs(tal).quantize(Decimal("0.01"))
    heltal, decimaler = f"{tal:.2f}".split(".")
    grupper = f"{int(heltal):,}"
    former = set()
    for tusen in ("", " ", ".", ","):
        h = grupper.replace(",", tusen) if tusen else heltal
        for dec in (",", "."):
            if tusen and tusen == dec:
                continue
            former.add(f"{h}{dec}{decimaler}")
            if decimaler.endswith("0"):
                former.add(f"{h}{dec}{decimaler[0]}")
        if decimaler == "00":
            former.add(f"{h}:-")
            former.add(h)
    return sorted(former, key=len, reverse=True)


def belopp_star_i_texten(tal: Decimal, text: str) -> bool:
    rensad = _rensa_text(text)
    for form in _beloppsformer(tal):
        if re.search(rf"(?<![\d.,]){re.escape(form)}(?![\d]|[.,]\d)", rensad):
            return True
    return False


def _kompakt(text: str) -> str:
    return re.sub(r"[^0-9A-ZÅÄÖ]", "", (text or "").upper())


def identifierare_star_i_texten(varde: str, text: str) -> bool:
    kompakt = _kompakt(varde)
    return bool(kompakt) and kompakt in _kompakt(text)


def datum_star_i_texten(iso: str, text: str) -> bool:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return False
    rensad = _rensa_text(text).lower()
    yy = f"{d.year % 100:02d}"
    former = {
        d.isoformat(),
        f"{d.year}{d.month:02d}{d.day:02d}",
        f"{d.year}/{d.month:02d}/{d.day:02d}",
        f"{d.year}.{d.month:02d}.{d.day:02d}",
    }
    for dag in (f"{d.day:02d}", str(d.day)):
        for man in (f"{d.month:02d}", str(d.month)):
            for sep in (".", "/", "-"):
                former.add(f"{dag}{sep}{man}{sep}{d.year}")
                former.add(f"{dag}{sep}{man}{sep}{yy}")
                former.add(f"{man}{sep}{dag}{sep}{d.year}")
        for namn in (_MANADER_SV[d.month - 1], _MANADER_EN[d.month - 1]):
            for m in {namn, namn[:3]}:
                former.add(f"{dag} {m} {d.year}")
                former.add(f"{dag} {m}. {d.year}")
                former.add(f"{m} {dag}, {d.year}")
                former.add(f"{m} {dag} {d.year}")
                former.add(f"{m}. {dag}, {d.year}")
    return any(f in rensad for f in former)


def _namn_star_i_texten(namn: str, text: str) -> bool:
    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", _ascii(t))).strip()

    mal = norm(namn)
    return bool(mal) and mal in norm(text)


# -- Kontrollen ---------------------------------------------------------------


def _normaliserat_namn(namn: str | None) -> str:
    text = _ascii(namn or "")
    text = re.sub(r"\b(ab|aktiebolag|hb|kb|inc|ltd|llc|gmbh|oy|as|aps|bv)\b", " ", text)
    return re.sub(r"[^a-z0-9]", "", text)


def _samma_leverantor(u: dict, tidigare: dict) -> bool:
    org = (u["fält"]["leverantör_orgnummer"]["värde"] or "").strip()
    tidigare_org = str(tidigare.get("leverantör_orgnummer") or "")
    if org and tidigare_org and _kompakt(org)[-10:] == _kompakt(tidigare_org)[-10:]:
        return True
    a = _normaliserat_namn(u["fält"]["leverantör_namn"]["värde"])
    b = _normaliserat_namn(tidigare.get("leverantör_namn") or tidigare.get("motpart"))
    return bool(a) and a == b


def tidigare_post(rad: dict[str, Any]) -> dict[str, Any]:
    """En sparad bk_underlag-rad som den kompakta post kontrollen och
    prompten jämför mot."""
    gr = rad.get("granskning") if isinstance(rad.get("granskning"), dict) else {}
    falt = gr.get("fält") if isinstance(gr.get("fält"), dict) else {}

    def v(namn: str) -> Any:
        post = falt.get(namn)
        return post.get("värde") if isinstance(post, dict) else None

    brutto = rad.get("brutto")
    total = v("totalbelopp")
    return {
        "id": str(rad.get("id") or ""),
        "leverantör_namn": v("leverantör_namn") or rad.get("motpart"),
        "leverantör_orgnummer": v("leverantör_orgnummer"),
        "dokumentnummer": v("dokumentnummer"),
        "dokumentdatum": v("dokumentdatum") or (str(rad.get("datum")) if rad.get("datum") else None),
        "totalbelopp": str(total) if total is not None else (f"{brutto:f}" if brutto is not None else None),
        "valuta": v("valuta") or ("SEK" if brutto is not None else rad.get("valuta")),
        "bankgiro": v("bankgiro"),
        "plusgiro": v("plusgiro"),
        "iban": v("iban"),
        "kategori": rad.get("kategori"),
        "status": rad.get("granskningsstatus") or rad.get("status"),
    }


def _dagar_mellan(a: str | None, b: str | None) -> int | None:
    try:
        return abs((date.fromisoformat(str(a)) - date.fromisoformat(str(b))).days)
    except (TypeError, ValueError):
        return None


def _kontrollrakna(u: dict, noter: list[str]) -> None:
    f = u["fält"]
    total = f["totalbelopp"]["värde"]
    netto = f["belopp_exkl_moms"]["värde"]
    moms = f["momsbelopp_totalt"]["värde"]
    ores = f["öresavrundning"]["värde"] or Decimal("0")
    kr = u["kontrollräkningar"]

    if total is not None and netto is not None and moms is not None:
        diff = netto + moms + ores - total
        ok = abs(diff) <= _TOLERANS or abs(netto + moms - total) <= _TOLERANS
        kr["netto_plus_moms_lika_total"] = ok
        if not ok:
            noter.append(
                f"Netto {_kr(netto)} + moms {_kr(moms)} blir inte totalen {_kr(total)}."
            )

    rader = u["rader"]
    if rader and total is not None and all(r["belopp"] is not None for r in rader):
        summa = sum((r["belopp"] for r in rader), Decimal("0"))
        jamfor = [total] + ([netto] if netto is not None else [])
        ok = any(abs(summa - j) <= _TOLERANS or abs(summa + ores - j) <= _TOLERANS for j in jamfor)
        kr["rader_lika_total"] = ok
        if not ok:
            noter.append(f"Raderna summerar till {_kr(summa)}, inte till totalen {_kr(total)}.")

    momsok: list[bool] = []
    for post in u["moms_per_sats"]:
        if post["underlag"] is not None and post["moms"] is not None:
            beraknad = post["underlag"] * post["sats"] / Decimal(100)
            ok = abs(beraknad - post["moms"]) <= _TOLERANS
            momsok.append(ok)
            if not ok:
                noter.append(
                    f"Momsen {_kr(post['moms'])} stämmer inte med {post['sats']:g} % av "
                    f"{_kr(post['underlag'])}."
                )
    if moms is not None and u["moms_per_sats"] and all(p["moms"] is not None for p in u["moms_per_sats"]):
        summa = sum((p["moms"] for p in u["moms_per_sats"]), Decimal("0"))
        ok = abs(summa - moms) <= _TOLERANS
        momsok.append(ok)
        if not ok:
            noter.append(f"Momsen per sats blir {_kr(summa)}, inte momsbeloppet {_kr(moms)}.")
    if (
        not u["moms_per_sats"]
        and netto is not None
        and moms is not None
        and f["valuta"]["värde"] == "SEK"
    ):
        # En ensam momssats utan per-sats-rad: pröva mot de svenska satserna
        # bara för att se om NÅGON går ihop. Väljer ingen sats åt underlaget.
        if netto != 0 and not any(
            abs(netto * s / Decimal(100) - moms) <= _TOLERANS for s in (Decimal(25), Decimal(12), Decimal(6), Decimal(0))
        ):
            momsok.append(False)
            noter.append(f"Momsen {_kr(moms)} motsvarar ingen svensk momssats av {_kr(netto)}.")
    if momsok:
        kr["moms_lika_sats"] = all(momsok)

    utfall = [v for v in kr.values() if v is not None]
    if any(v is False for v in utfall):
        u["flaggor"].add("belopp_stämmer_inte")
    elif utfall:
        # Koden har räknat och allt går ihop: modellens flagga var ett
        # räknefel, inte ett fel i underlaget.
        u["flaggor"].discard("belopp_stämmer_inte")


def _verifiera_text(u: dict, kalltext: str, noter: list[str]) -> None:
    """Avsnitt 3: varje värde ska stå i underlaget. Belopp och nummer som
    inte går att hitta stryks; namn och datum blir `osäker`."""
    f = u["fält"]
    for namn in BELOPPSFALT:
        post = f[namn]
        if post["värde"] is None:
            continue
        if not belopp_star_i_texten(post["värde"], kalltext):
            noter.append(f"{namn} {_kr(post['värde'])} står inte i underlaget och har strukits.")
            f[namn] = _tomt_falt()
            u["flaggor"].add("oläsligt")
    for prs in u["moms_per_sats"]:
        for nyckel in ("underlag", "moms"):
            if prs[nyckel] is not None and not belopp_star_i_texten(prs[nyckel], kalltext):
                prs[nyckel] = None
    for namn in _IDENTIFIERARE:
        post = f[namn]
        if post["värde"] is None:
            continue
        if not identifierare_star_i_texten(post["värde"], kalltext):
            noter.append(f"{namn} {post['värde']} står inte i underlaget och har strukits.")
            f[namn] = _tomt_falt()
            u["flaggor"].add("oläsligt")
    for namn in DATUMFALT:
        post = f[namn]
        if post["värde"] is not None and not datum_star_i_texten(post["värde"], kalltext):
            post["säkerhet"] = "osäker"
            noter.append(f"{namn} {post['värde']} hittades inte ordagrant, kontrollera datumet.")
    for namn in ("leverantör_namn", "köpare_namn"):
        post = f[namn]
        if post["värde"] is not None and not _namn_star_i_texten(post["värde"], kalltext):
            post["säkerhet"] = "osäker"


def _verifiera_nummer(u: dict, noter: list[str]) -> None:
    for namn, typ in NUMMERFALT.items():
        post = u["fält"][namn]
        if post["värde"] is None:
            continue
        if kontrollsiffror.kontrollera(typ, post["värde"]) is False:
            post["säkerhet"] = "osäker"
            u["flaggor"].add("oläsligt")
            noter.append(f"Kontrollsiffran i {namn} {post['värde']} stämmer inte, numret kan vara felläst.")


def _verifiera_forfallo(u: dict, idag: date, dagar_varning: int) -> None:
    f = u["fält"]
    forfaller = f["förfallodatum"]["värde"]
    if forfaller is None:
        # Inget datum att räkna på. En påminnelseavgift kan ändå bära
        # modellens `förfallen` (avsnitt 10) — den står kvar.
        return
    u["flaggor"].discard("förfallen")
    u["flaggor"].discard("förfaller_snart")
    if f["betalstatus"]["värde"] == "betald":
        return
    dagar = (date.fromisoformat(forfaller) - idag).days
    if dagar < 0:
        u["flaggor"].add("förfallen")
    elif dagar <= dagar_varning:
        u["flaggor"].add("förfaller_snart")


def _verifiera_moms_och_obligatoriska(u: dict) -> None:
    f = u["fält"]
    har_moms = f["momsbelopp_totalt"]["värde"] is not None or any(
        p["moms"] is not None or p["sats"] is not None for p in u["moms_per_sats"]
    )
    if har_moms:
        u["flaggor"].discard("saknar_moms")
    else:
        u["flaggor"].add("saknar_moms")
    if any(f[n]["värde"] is None for n in OBLIGATORISKA):
        u["flaggor"].add("saknar_obligatoriska_fält")
    else:
        u["flaggor"].discard("saknar_obligatoriska_fält")


def _verifiera_valuta(u: dict) -> None:
    valuta = u["fält"]["valuta"]["värde"]
    if valuta is None:
        return
    if valuta == "SEK":
        u["flaggor"].discard("utländsk_valuta")
    else:
        u["flaggor"].add("utländsk_valuta")


def _verifiera_kredit(u: dict) -> None:
    """Avsnitt 10: en kreditfaktura bär negativa belopp."""
    if u["dokumenttyp"] != "kreditfaktura":
        return
    for namn in ("totalbelopp", "belopp_exkl_moms", "momsbelopp_totalt"):
        post = u["fält"][namn]
        if post["värde"] is not None and post["värde"] > 0:
            post["värde"] = -post["värde"]
    for post in u["moms_per_sats"]:
        for nyckel in ("underlag", "moms"):
            if post[nyckel] is not None and post[nyckel] > 0:
                post[nyckel] = -post[nyckel]
    for rad in u["rader"] or []:
        if rad["belopp"] is not None and rad["belopp"] > 0:
            rad["belopp"] = -rad["belopp"]


def _verifiera_mottagare(u: dict, foretag_orgnr: str) -> None:
    kopare = u["fält"]["köpare_orgnummer"]["värde"]
    if not kopare or not foretag_orgnr:
        return
    if _kompakt(kopare)[-10:] == _kompakt(foretag_orgnr)[-10:]:
        u["flaggor"].discard("fel_mottagare")
    else:
        u["flaggor"].add("fel_mottagare")


def _verifiera_dubbletter(u: dict, tidigare: list[dict], noter: list[str]) -> None:
    kanda = {t["id"] for t in tidigare}
    if u["möjlig_dubblett_av"] not in kanda:
        u["möjlig_dubblett_av"] = None
    f = u["fält"]
    nummer = f["dokumentnummer"]["värde"]
    total = f["totalbelopp"]["värde"]
    datum = f["dokumentdatum"]["värde"]
    for t in tidigare:
        if not _samma_leverantor(u, t):
            continue
        traff = False
        if nummer and t.get("dokumentnummer") and _kompakt(nummer) == _kompakt(str(t["dokumentnummer"])):
            traff = True
        elif total is not None and t.get("totalbelopp") is not None:
            dagar = _dagar_mellan(datum, t.get("dokumentdatum"))
            if tolka_belopp(t["totalbelopp"]) == total and dagar is not None and dagar <= 3:
                traff = True
        if traff:
            u["möjlig_dubblett_av"] = u["möjlig_dubblett_av"] or t["id"]
            break
    if u["möjlig_dubblett_av"]:
        u["flaggor"].add("möjlig_dubblett")
        original = next((t for t in tidigare if t["id"] == u["möjlig_dubblett_av"]), {})
        noter.append(dubblettnot(original))


def dubblettnot(original: dict[str, Any]) -> str:
    """Kundens version av "möjlig dubblett": vilket underlag, i ord — inte id."""
    delar = [
        str(original.get("leverantör_namn") or "").strip(),
        str(original.get("dokumentdatum") or "").strip(),
        f"{original['totalbelopp']} {original.get('valuta') or ''}".strip()
        if original.get("totalbelopp")
        else "",
    ]
    beskrivning = ", ".join(d for d in delar if d) or "ett tidigare underlag"
    return f"Möjlig dubblett av {beskrivning}. Beloppet räknas inte förrän du godkänt underlaget."


def _verifiera_betalningsuppgifter(u: dict, tidigare: list[dict], noter: list[str]) -> None:
    """8.3: betalningsuppgifter som skiljer sig från samma leverantörs tidigare."""
    for namn in BETALNINGSFALT:
        nu = u["fält"][namn]["värde"]
        if not nu:
            continue
        forra = {
            _kompakt(str(t[namn]))
            for t in tidigare
            if t.get(namn) and _samma_leverantor(u, t)
        }
        if forra and _kompakt(nu) not in forra:
            gamla = next(
                str(t[namn]) for t in tidigare if t.get(namn) and _samma_leverantor(u, t)
            )
            u["flaggor"].add("misstänkt_bedrägeri")
            noter.append(
                f"{namn.capitalize()} skiljer sig från tidigare underlag från samma leverantör "
                f"({gamla} → {nu}). Verifiera med leverantören via ett känt telefonnummer "
                "innan betalning."
            )


def berakna_status(u: dict, klass: str) -> str:
    """Avsnitt 9.2, i den ordning tabellen ska läsas."""
    if klass == "UNDERLAG_ENDAST_LÄNK":
        return MANUELL_HAMTNING
    flaggor = u["flaggor"]
    if flaggor & _PRIORITERADE:
        return PRIORITERAD
    f = u["fält"]
    obligatoriska_sakra = all(f[n]["säkerhet"] == "säker" for n in OBLIGATORISKA)
    nagot_osakert = any(p["säkerhet"] == "osäker" for p in f.values())
    kontroller_ok = all(v is not False for v in u["kontrollräkningar"].values())
    if obligatoriska_sakra and not nagot_osakert and kontroller_ok and flaggor <= _TILLATNA_VID_KLAR:
        return KLAR
    return BEHOVER


def verifiera(
    resultat: dict[str, Any],
    *,
    kalltext: str,
    idag: date,
    dagar_varning: int,
    foretag_orgnr: str = "",
    tidigare: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Kör hela kontrollen på ett normaliserat resultat (muterar och returnerar det).

    `kalltext` är ALL text modellen fick läsa: mejlet, bilagorna och det
    researchen hämtade. `tidigare` är `tidigare_post`-poster.
    """
    tidigare = tidigare or []
    noter: list[str] = []
    instruktion = bool(_INSTRUKTION.search(kalltext or ""))
    for u in resultat["underlag"]:
        _verifiera_text(u, kalltext, noter)
        _verifiera_kredit(u)
        _verifiera_nummer(u, noter)
        _kontrollrakna(u, noter)
        _verifiera_moms_och_obligatoriska(u)
        _verifiera_valuta(u)
        _verifiera_forfallo(u, idag, dagar_varning)
        _verifiera_mottagare(u, foretag_orgnr)
        _verifiera_dubbletter(u, tidigare, noter)
        _verifiera_betalningsuppgifter(u, tidigare, noter)
        if instruktion:
            u["flaggor"].add("instruktion_i_innehåll")
        if u["kategori"] is not None:
            from ..bookkeeping.kontoplan import KOSTNADSKATEGORIER

            if u["kategori"] not in KOSTNADSKATEGORIER:
                u["kategori"] = None
        u["status"] = berakna_status(u, resultat["klass"])

    if instruktion and resultat["underlag"] and "instruktion" not in resultat["intern_notering"].lower():
        noter.append("Innehållet bär text riktad till granskningen eller ett AI-system; den har inte följts.")
    if noter:
        resultat["intern_notering"] = " ".join(
            dict.fromkeys([resultat["intern_notering"], *noter] if resultat["intern_notering"] else noter)
        ).strip()
    return resultat


# -- Lagringsformen -----------------------------------------------------------


def _json(varde: Any) -> Any:
    if isinstance(varde, Decimal):
        return f"{varde:f}"
    if isinstance(varde, set):
        return [f for f in FLAGGOR if f in varde]
    if isinstance(varde, dict):
        return {k: _json(v) for k, v in varde.items()}
    if isinstance(varde, list):
        return [_json(v) for v in varde]
    return varde


def underlag_som_json(u: dict[str, Any], *, klass: str, meddelande_id: str, intern_notering: str) -> dict[str, Any]:
    """Det som sparas i `bk_underlag.granskning` (migration 096): promptens
    underlagsobjekt plus klassen och noteringen. Belopp som strängar."""
    return {
        "version": 1,
        "meddelande_id": meddelande_id,
        "klass": klass,
        **_json(u),
        "intern_notering": intern_notering,
    }


def resultat_som_json(resultat: dict[str, Any]) -> dict[str, Any]:
    return _json(resultat)
