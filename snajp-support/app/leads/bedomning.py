"""Bedömningen av ett researchat bolag — räknad i KOD ur modellens utslag.

## Varför modellen inte får avgöra själv

Uppmätt 2026-09-29 hos Alunix: modellens fria `qualified` fällde en
tvåmansbyrå för "Juristbyråer är inte en del av målgruppen" — ett skäl som
inte stod någonstans i kundens profil. Modellen får därför bara ge ett utslag
PER kriterium i Iris-profilen (ja/nej/okänt, med belägg), och koden här
avgör nivå, poäng och kvalificering (INV-LEADS-PROFIL-001).

## Varför ett utslag utan verifierat belägg blir "okänt"

Ett ja eller nej ska gå att peka på: ett ordagrant citat ur det skrapade
materialet eller ur de mätta webbsignalerna. Ett citat som inte finns där är
en gissning, och en gissning får varken fälla eller lyfta ett bolag.

## Varför motiveringen aldrig kan bli tom

Den är det kunden köper (INV-LEADS-SCORE-001). Tom modellmotivering → koden
skriver den ur utslagen.
"""

from __future__ import annotations

import re
from typing import Any

from .geo import _prefix_ur_postnr
from .profil import KOMMUNER, PRODUKTMATCH, produktmatch_text
from .scoring import MISS, OKAND, TRAFF

UTSLAG = {"ja": TRAFF, "nej": MISS, "okänt": OKAND, "okant": OKAND}
_VARDE = {TRAFF: 1.0, OKAND: 0.5, MISS: 0.0}

#: Poängtak för ett fällt bolag — samma tanke som kvalificeringsgrindens
#: TAK_ICP_FIT: modellens övriga bedömning kan vara riktig, men ett fällt
#: bolag ska aldrig sorteras över ett som kvalificerar.
TAK_FALLD = 30
#: Lägsta poäng för A-nivå (alla måste-kriterier ja krävs dessutom).
A_GRANS = 70

#: "uppfyller inte", "inte uppfyller", "uppfylls inte", "does not meet".
_SAGER_NEJ = re.compile(
    r"\buppfyll\w*\s+(?:\w+\s+){0,2}?inte\b|\binte\s+(?:\w+\s+){0,2}?uppfyll|"
    r"\b(?:does|do)\s+not\s+(?:meet|fulfil|satisfy)",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip(" .\"'”“")


def verifierade_belagg(belagg: object, korpus: str) -> list[dict[str, str]]:
    """Beläggen vars citat faktiskt står i materialet (normaliserat)."""
    k = _norm(korpus)
    ut: list[dict[str, str]] = []
    for b in belagg if isinstance(belagg, list) else []:
        if not isinstance(b, dict):
            continue
        citat = str(b.get("citat") or "").strip()
        if len(_norm(citat)) >= 4 and _norm(citat) in k:
            ut.append({"url": str(b.get("url") or "")[:500], "citat": citat[:300]})
    return ut


#: Riktningen på ett webbkriterium. "Företag med gamla hemsidor" vill ha en
#: dålig sajt; "har en modern webbshop" en bra. Okänd riktning = koden avgör
#: inte, modellens citerade utslag gäller som förut.
_VILL_HA_DALIG = re.compile(
    r"gaml|föråldr|dålig|långsam|omodern|utan |ingen |saknar|äldre|old|outdated|slow|poor|bad", re.I
)
_INGEN_SAJT_INGAR = re.compile(r"(ingen|utan|saknar)\s+(hem)?sid|(ingen|utan|saknar)\s+webb|no\s+website", re.I)
_VILL_HA_BRA = re.compile(r"modern|snabb|ny |nya |professionell|fast|new ", re.I)
#: Gränserna på bildbedömningens tiogradiga skala (webbrevision.VISIONPROMPT).
#: Kalibrerade mot Antons facit 2026-10-04: Byggarna Berggren och Vicht
#: (dåliga) under, Björkekärr och Eustaff (bra) över, Ställningskompaniet
#: (gränsfall) mellan.
DALIG_HOGST = 4
BRA_MINST = 7


def webbutslag(kriterium: str, rev: dict[str, Any] | None, *, utan_webbplats: bool = False) -> tuple[str, str] | None:
    """(utfall, motivering) för ett webbkriterium ur webbrevisionen, eller
    None när koden inte kan avgöra (ingen revision eller okänd riktning).

    Avgörs i kod för att samma citat inte ska kunna styrka båda hållen: före
    2026-10-05 räckte raden "Ingen webbplats hittades" som belägg både för ja
    (100 poäng) och nej (fälld)."""
    if not rev or (rev.get("modernitet") is None and not rev.get("saknas") and not rev.get("svarar_inte")):
        return None
    if _VILL_HA_DALIG.search(kriterium):
        vill_dalig = True
    elif _VILL_HA_BRA.search(kriterium):
        vill_dalig = False
    else:
        return None
    if rev.get("saknas"):
        # Profilens utan_webbplats, eller kriteriet självt ("gammal eller
        # ingen hemsida"), avgör i kod. Förut var det en mening i prompten
        # som låg inuti det opålitliga omslaget och därför kunde ignoreras.
        if vill_dalig and (utan_webbplats or _INGEN_SAJT_INGAR.search(kriterium)):
            return TRAFF, "Bolaget saknar webbplats, och kundens målgrupp tar med bolag utan sajt."
        return MISS, "Bolaget saknar webbplats."
    if rev.get("svarar_inte") and rev.get("modernitet") is None:
        # Vicht (facit 2026-10-04): en sajt som inte svarar är en dålig sajt.
        return (TRAFF if vill_dalig else MISS), "Webbplatsen svarade inte när den mättes."
    m = int(rev["modernitet"])
    brister = "; ".join(rev.get("brister") or [])
    if m <= DALIG_HOGST:
        lage, text = "dalig", f"Startsidan bedöms som föråldrad (modernitet {m} av 10)."
    elif m >= BRA_MINST:
        lage, text = "bra", f"Startsidan bedöms som modern och professionell (modernitet {m} av 10)."
    else:
        return OKAND, f"Gränsfall: startsidan är varken tydligt föråldrad eller modern (modernitet {m} av 10)." + (
            f" Brister: {brister}." if brister else "")
    if brister and lage == "dalig":
        text += f" Brister: {brister}."
    return (TRAFF if (lage == "dalig") == vill_dalig else MISS), text


def _rad(nyckel: str, etikett: str, vikt: int, utfall: str, motivering: str, *, hart: bool,
         belagg: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {
        "nyckel": nyckel,
        "etikett": etikett,
        "vikt": vikt,
        "utfall": utfall,
        "motivering": motivering,
        "hart": hart,
        "belagg": belagg or [],
    }


def _ort_rad(profil: dict[str, Any], fynd: dict[str, Any], kand: dict[str, Any]) -> dict[str, Any] | None:
    kommuner = profil.get("kommuner") or []
    if not kommuner:
        return None
    postnr = fynd.get("postnummer") or kand.get("postnr")
    ort = str(fynd.get("ort") or kand.get("ort") or "").strip()
    valda = [KOMMUNER[k.casefold()] for k in kommuner if k.casefold() in KOMMUNER]
    prefix = _prefix_ur_postnr(postnr)
    etikett = "Ligger i " + " eller ".join(kommuner)
    if prefix is not None:
        inne = any(k.innehaller_prefix(prefix) for k in valda)
        return _rad("ort", etikett, 2, TRAFF if inne else MISS,
                    f"Postnummer {postnr} {'ligger' if inne else 'ligger inte'} i målområdet.", hart=True)
    if ort:
        if ort.casefold() in {k.namn.casefold() for k in valda}:
            return _rad("ort", etikett, 2, TRAFF, f"Orten {ort} ligger i målområdet.", hart=True)
        if ort.casefold() in KOMMUNER:
            return _rad("ort", etikett, 2, MISS, f"Orten {ort} ligger utanför målområdet.", hart=True)
        # En ort vi inte känner igen fäller inte: stadsdelar heter annat än
        # kommunen (Västra Frölunda är Göteborg).
        return _rad("ort", etikett, 2, OKAND, f"Orten {ort} kunde inte knytas till en kommun.", hart=True)
    return _rad("ort", etikett, 2, OKAND, "Adressen framgick inte av källmaterialet.", hart=True)


def _storlek_rad(profil: dict[str, Any], fynd: dict[str, Any], kand: dict[str, Any],
                 rev: dict[str, Any] | None = None) -> dict[str, Any] | None:
    lo, hi = profil.get("anstallda_min"), profil.get("anstallda_max")
    if lo is None and hi is None:
        return None
    etikett = f"Storlek {lo if lo is not None else '—'}–{hi if hi is not None else '—'} anställda"
    if hi is not None and (rev or {}).get("internationell"):
        # Ostia (Antons granskning 2026-10-04): den svenska enheten har en
        # anställd i registret, men bolaget är internationellt. Ett tak på
        # antalet anställda betyder att kunden söker små, lokala bolag.
        return _rad("storlek", etikett, 1, MISS,
                    "Webbplatsen visar en internationell verksamhet; den svenska enhetens "
                    "anställda speglar inte bolagets storlek.", hart=True)
    antal = fynd.get("antal_anstallda")
    # Prospektradens tal kommer ur registret: en sökträffs påstådda storlek
    # följer aldrig med till raden (api/leads.py, _skapa_prospekt_ur_kandidat).
    kalla = "källmaterialet"
    if antal is None:
        antal = kand.get("anstallda")
        kalla = "registret"
    try:
        antal = int(antal) if antal is not None and not isinstance(antal, bool) else None
    except (TypeError, ValueError):
        antal = None
    if antal is None:
        return _rad("storlek", etikett, 1, OKAND, "Antalet anställda framgick inte.", hart=True)
    inne = (lo is None or antal >= lo) and (hi is None or antal <= hi)
    return _rad("storlek", etikett, 1, TRAFF if inne else MISS,
                f"{antal} anställda enligt {kalla}.", hart=True)


def _produktmatch_rad(profil: dict[str, Any], b: dict[str, Any], korpus: str,
                      kriterierader: list[dict[str, Any]], produkt_vald: bool | None) -> dict[str, Any]:
    """Kan bolaget köpa det kunden säljer? Bara ett belagt ja räcker.

    Sebbes krav 2026-10-06: ett lead som kunden inte kan sälja sin produkt
    till är inget lead. Okänt är här inte neutralt. Förut blev ett bolag en B
    när profilen saknade kriterier och modellen inte kunde visa någonting,
    och ett bolag där researchen svarat "ingen av kundens produkter passar"
    levererades ändå.

    `produkt_vald`: None när kunden saknar produktlista, annars om researchen
    valde en av produkterna. Ett webbkriterium som koden avgjort som träff
    räknar som belägg: profilens webbkriterier ÄR kundens egen beskrivning av
    vem som behöver produkten ("företag med gamla hemsidor" hos en webbyrå),
    och betyget är mätt."""
    etikett = produktmatch_text(profil)
    if produkt_vald is False:
        return _rad(PRODUKTMATCH, etikett, 3, MISS, "Ingen av kundens produkter passar bolaget.", hart=True)
    utfall = UTSLAG.get(str(b.get("utslag") or "").casefold(), OKAND)
    belagg = verifierade_belagg(b.get("belagg"), korpus)
    resonemang = str(b.get("resonemang") or "").strip()
    if utfall == TRAFF and belagg:
        return _rad(PRODUKTMATCH, etikett, 3, TRAFF, resonemang or "Källmaterialet visar behovet.",
                    hart=True, belagg=belagg)
    webbtraff = next((r for r in kriterierader if r["hart"] and r["utfall"] == TRAFF and r.get("webbkod")), None)
    if webbtraff:
        return _rad(PRODUKTMATCH, etikett, 3, TRAFF, f"{webbtraff['etikett']}: {webbtraff['motivering']}",
                    hart=True, belagg=webbtraff["belagg"])
    if utfall == MISS and belagg:
        motivering = resonemang or "Källmaterialet visar att bolaget inte behöver produkten."
    elif utfall == TRAFF:
        motivering = "Behovet påstods men kunde inte beläggas med ett citat ur källmaterialet."
    else:
        motivering = "Källmaterialet visar inget behov av det kunden säljer."
    return _rad(PRODUKTMATCH, etikett, 3, MISS, motivering, hart=True, belagg=belagg)


def bedom(
    profil: dict[str, Any],
    fynd: dict[str, Any],
    *,
    korpus: str,
    kandidat: dict[str, Any] | None = None,
    webbrevision: dict[str, Any] | None = None,
    har_underlag: bool = True,
    produkt_vald: bool | None = None,
) -> dict[str, Any]:
    """Modellens utslag + hårda fakta → nivå, poäng, rader och motivering.

    `korpus` = skrapat material + mätta webbsignaler; beläggen verifieras mot
    den. Returnerar fälten som sparas på prospektraden plus de bakåt-
    kompatibla `qualified`/`icp_fit`/`disqualifiers` som resten av kedjan
    (eskalering, utkastgrind) redan läser.

    `har_underlag=False`: inget källmaterial gick att hämta. Bolaget bedöms
    då inte alls: nivå C med skälet utskrivet, oavsett vad modellen svarade.
    Provkörningen 2026-10-05 gav poäng 100 och nivå A till tre påhittade bolag
    med motiveringen "det finns inget källmaterial"."""
    kand = kandidat or {}
    if not har_underlag:
        skal = "Inget källmaterial: bolagets sidor gick inte att hämta, så bolaget kunde inte bedömas."
        return {
            "niva": "C",
            "score_total": 0,
            "score_breakdown": [_rad("underlag", "Källmaterial", 1, MISS, skal, hart=True)],
            "motivering": skal,
            "qualified": False,
            "icp_fit": 0.0,
            "disqualifiers": [skal],
        }
    utslag_per_id: dict[str, dict[str, Any]] = {}
    for b in fynd.get("bedomningar") or []:
        if isinstance(b, dict) and b.get("kriterie_id"):
            utslag_per_id[str(b["kriterie_id"])] = b

    rader: list[dict[str, Any]] = []
    fallt: list[str] = []

    for rad in (_ort_rad(profil, fynd, kand), _storlek_rad(profil, fynd, kand, webbrevision)):
        if rad:
            rader.append(rad)
            if rad["utfall"] == MISS:
                fallt.append(f"{rad['etikett']}: {rad['motivering']}")

    for k in profil.get("kriterier") or []:
        b = utslag_per_id.get(k["id"], {})
        kod = (
            webbutslag(k["text"], webbrevision, utan_webbplats=bool(profil.get("utan_webbplats")))
            if k.get("belagg") == "webbsignal" else None
        )
        if kod:
            utfall, motivering = kod
            belagg = [{"url": str(kand.get("website") or ""), "citat": r} for r in (webbrevision or {}).get("rader") or []][:3]
            rader.append({**_rad(k["id"], k["text"], k["vikt"], utfall, motivering, hart=k["krav"] == "maste",
                                 belagg=belagg), "webbkod": True})
            if utfall == MISS:
                fallt.append(f"{k['text']}: {motivering}")
            continue
        utfall = UTSLAG.get(str(b.get("utslag") or "").casefold(), OKAND)
        belagg = verifierade_belagg(b.get("belagg"), korpus)
        if utfall != OKAND and not belagg:
            utfall = OKAND
            motivering = (str(b.get("resonemang") or "").strip() + " (Belägget kunde inte verifieras.)").strip()
        else:
            motivering = str(b.get("resonemang") or "").strip() or "Inget underlag i källmaterialet."
        rader.append(_rad(k["id"], k["text"], k["vikt"], utfall, motivering, hart=k["krav"] == "maste",
                          belagg=belagg))
        # Varje uttryckligt nej fäller, även på ett bör-kriterium, och ett
        # måste-kriterium utan belägg fäller också: ett lead ska uppfylla
        # kraven, inte bara inte motsäga dem (Antons krav 2026-10-06).
        if utfall == MISS:
            fallt.append(f"{k['text']}: {motivering}")
        elif utfall == OKAND and k["krav"] == "maste":
            fallt.append(f"{k['text']}: kravet kunde inte styrkas i källmaterialet")

    kp = _produktmatch_rad(profil, utslag_per_id.get(PRODUKTMATCH, {}), korpus, rader, produkt_vald)
    rader.append(kp)
    if kp["utfall"] != TRAFF:
        fallt.append(f"Ingen belagd koppling till det kunden säljer: {kp['motivering']}")

    for i, u in enumerate(profil.get("uteslut") or [], start=1):
        b = utslag_per_id.get(f"u{i}", {})
        belagg = verifierade_belagg(b.get("belagg"), korpus)
        # För en uteslutning betyder "ja" att bolaget ÄR det kunden inte vill nå.
        if str(b.get("utslag") or "").casefold() == "ja" and belagg:
            motivering = str(b.get("resonemang") or "").strip() or u["text"]
            rader.append(_rad(f"u{i}", f"Uteslut: {u['text']}", 1, MISS, motivering, hart=True, belagg=belagg))
            fallt.append(f"Uteslutet — {u['text']}: {motivering}")

    if not rader:
        # INV-LEADS-SCORE-001: aldrig en tom motivering — säg ärligt varför.
        rader.append(_rad("underlag", "Kundens profil", 1, OKAND,
                          "Profilen saknar kriterier att bedöma mot. Fyll i Affärskontext och målgrupp.",
                          hart=False))

    viktat = [(r["vikt"], _VARDE.get(r["utfall"], 0.5)) for r in rader if not r["nyckel"].startswith("u")]
    total = round(100 * sum(w * v for w, v in viktat) / sum(w for w, _ in viktat)) if viktat else 50

    maste = [r for r in rader if r["hart"] and not r["nyckel"].startswith("u") and r["nyckel"] not in ("ort", "storlek")]
    # Nivå A kräver minst ETT uppfyllt kriterium. Ett ja på en kriterierad är
    # alltid styrkt: modellens ja utan verifierat citat har redan blivit okänt
    # ovan, och webbkriterierna avgörs i kod. Utan kravet var `all([])` sant
    # för en profil utan kriterier, och ort plus storlek räckte till "Stark"
    # (provkörningen 2026-10-05).
    styrkt = any(
        r["utfall"] == TRAFF
        for r in rader
        if not r["nyckel"].startswith("u") and r["nyckel"] not in ("ort", "storlek", PRODUKTMATCH)
    )
    if not fallt and not styrkt and profil.get("kriterier"):
        fallt.append("Inget kriterium kunde styrkas: bolaget uppfyller inte kraven med belägg")
    if fallt:
        niva = "C"
        total = min(total, TAK_FALLD)
    elif styrkt and all(r["utfall"] == TRAFF for r in maste) and total >= A_GRANS:
        niva = "A"
    else:
        niva = "B"

    motivering = str(fynd.get("motivering") or fynd.get("qualification_reasoning") or "").strip()
    if niva != "C" and _SAGER_NEJ.search(motivering):
        # Modellens text säger att bolaget inte uppfyller kraven fast koden
        # godkände det: kunden ska aldrig läsa ett lead som motsäger sig självt.
        motivering = ""
    if not motivering:
        ja = [r["etikett"] for r in rader if r["utfall"] == TRAFF]
        okanda = [r["etikett"] for r in rader if r["utfall"] == OKAND]
        delar = []
        if fallt:
            delar.append("Bortvald: " + "; ".join(fallt[:2]) + ".")
        if ja:
            delar.append("Uppfyller: " + ", ".join(ja) + ".")
        if okanda:
            delar.append("Okänt: " + ", ".join(okanda) + ".")
        motivering = " ".join(delar) or "Källmaterialet räckte inte för någon bedömning."
    elif fallt and niva == "C" and not any(f.split(":")[0] in motivering for f in fallt):
        motivering = f"Bortvald: {fallt[0]}. {motivering}"

    # Textkvalitetslagret: motiveringen är kundtext (INV-LEADS-SCORE-001) —
    # putsa blanksteg och entydiga felstavningar innan den sparas. Kapningen
    # till 1200 görs EFTER putsningen så att gränsen gäller den text som visas.
    from ..textkvalitet import putsa as _putsa_text

    motivering, _ = _putsa_text(motivering)

    return {
        "niva": niva,
        "score_total": int(total),
        "score_breakdown": [{k: v for k, v in r.items() if k != "webbkod"} for r in rader],
        "motivering": motivering[:1200],
        "qualified": niva in ("A", "B"),
        "icp_fit": round(total / 100, 2),
        "disqualifiers": fallt,
    }


def demo() -> None:
    profil = {
        "kommuner": ["Göteborg", "Mölndal"],
        "anstallda_min": 1,
        "anstallda_max": 49,
        "kriterier": [{"id": "k1", "text": "Gammal eller ingen hemsida", "krav": "maste", "vikt": 3}],
        "uteslut": [{"text": "bemanningsföretag"}],
    }
    korpus = "Välkommen till Åbergs. © 2014 Åbergs AB. Besöksadress: Sisjövägen 1, 421 32 Västra Frölunda"
    behov = {"kriterie_id": PRODUKTMATCH, "utslag": "ja", "resonemang": "Sajten är från 2014.",
             "belagg": [{"url": "u", "citat": "© 2014 Åbergs AB"}]}
    bra = bedom(profil, {"postnummer": "421 32", "antal_anstallda": 2, "bedomningar": [
        {"kriterie_id": "k1", "utslag": "ja", "resonemang": "Copyright 2014.", "belagg": [{"url": "u", "citat": "© 2014 Åbergs AB"}]},
        behov,
    ]}, korpus=korpus)
    assert bra["niva"] == "A" and bra["qualified"] and bra["motivering"], bra
    # Påhittat citat: utslaget räknas som okänt — och ett måste-krav utan
    # belägg är inte uppfyllt, så bolaget blir inget lead.
    gissat = bedom(profil, {"postnummer": "421 32", "bedomningar": [
        {"kriterie_id": "k1", "utslag": "nej", "resonemang": "Modern sajt.", "belagg": [{"citat": "byggd 2025"}]}
    ]}, korpus=korpus)
    assert gissat["niva"] == "C" and not gissat["qualified"], gissat
    # Ett nej på ett bör-kriterium fäller också; ett okänt bör ger B.
    bor = {**profil, "kriterier": [*profil["kriterier"], {"id": "k2", "text": "Har webbshop", "krav": "bor", "vikt": 1}]}
    ja_k1 = {"kriterie_id": "k1", "utslag": "ja", "resonemang": "Copyright 2014.", "belagg": [{"url": "u", "citat": "© 2014 Åbergs AB"}]}
    nej_bor = bedom(bor, {"postnummer": "421 32", "bedomningar": [
        ja_k1, {"kriterie_id": "k2", "utslag": "nej", "resonemang": "Ingen shop.", "belagg": [{"citat": "Välkommen till Åbergs"}]}
    ]}, korpus=korpus)
    assert nej_bor["niva"] == "C" and not nej_bor["qualified"], nej_bor
    okand_bor = bedom(bor, {"postnummer": "421 32", "motivering": "Bolaget uppfyller inte alla kriterier.",
                            "bedomningar": [ja_k1, behov]}, korpus=korpus)
    assert okand_bor["qualified"] and "inte" not in okand_bor["motivering"], okand_bor
    # Produktmatchningen (2026-10-06): utan ett belagt behov av det kunden
    # säljer blir bolaget inget lead, och inte heller när ingen av kundens
    # produkter passar — även om kriterierna är uppfyllda.
    utan_behov = bedom(profil, {"postnummer": "421 32", "bedomningar": [ja_k1]}, korpus=korpus)
    assert utan_behov["niva"] == "C" and not utan_behov["qualified"], utan_behov
    ingen_produkt = bedom(profil, {"postnummer": "421 32", "bedomningar": [ja_k1, behov]}, korpus=korpus,
                          produkt_vald=False)
    assert ingen_produkt["niva"] == "C", ingen_produkt
    utan_kriterier = bedom({}, {"bedomningar": []}, korpus=korpus)
    assert utan_kriterier["niva"] == "C", utan_kriterier
    stort = bedom(profil, {"antal_anstallda": 700, "bedomningar": []}, korpus=korpus)
    assert stort["niva"] == "C" and stort["score_total"] <= TAK_FALLD and stort["disqualifiers"]
    print("bedomning: ok")


if __name__ == "__main__":
    demo()
