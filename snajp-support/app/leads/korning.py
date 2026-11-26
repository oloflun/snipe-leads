"""Körningens motor: sök, förfiltrera, triagera — tills N leverbara leads.

## Varför "N" betyder leverbara leads, inte kandidater

Uppmätt 2026-09-29 hos Alunix: kunden beställde 3 leads och fick 3
kandidater som Iris själv underkände — plus inga utkast. Ett beställt antal
är ett löfte om leads kunden kan agera på: kvalificerade (nivå A/B), över
kundens egen tröskel och med en mejlväg, så att utkastagenten kan skriva
till dem (INV-LEADS-N-001).

## Flödet

    sökrunda (profilstyrd, geo-ring för ring)
        → förfilter (kod, känd data)          → tratten
        → Jev-triage (läge pa fäller säkra missar) → tratten
        → kandidatpoolen
    fyll_pa: köar research för så många som behövs; varje avslutat
    prospektjobb rapporterar tillbaka och fyll_pa körs igen, tills målet är
    nått, målgruppen är tom (TOMMA_RUNDOR efter breddningen), kredittaket är
    nått eller sökningen föll. Taket (TAK_FAKTOR×N undersökta) och rundtaket
    (max_rundor) förlängs under målet i stället för att avsluta (2026-11-24).
    Slutet är alltid ärligt: tratten namnger det kriterium som strypte.

Körningens tillstånd bor i batchjobbets eget resultat (jobbstoret, TTL 1 h)
— ingen ny tabell. Läs-ändra-skriv skyddas av ett lås per körning
(`_korningslas` i app/api/leads.py, infört 2026-10-06 när leads_workers
höjdes över 1): workers i samma process serialiseras per körning, olika
körningar går parallellt. Fler REPLIKER av processen kräver ett Redis-lås.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from . import jev
from .discovery import hitta_bolag
from .existens import styrk
from .forfilter import forfiltrera
from .geo import _prefix_ur_postnr
from .webbsignal import mat_webbplats

MAX_RUNDOR = 3
#: Undersökta bolag per beställt lead innan körningen ger upp. Var 4 till
#: 2026-10-15: en körning på 50 fick då granska högst 200, och med elva
#: sökrundor om åtta kandidater såg den aldrig fler än 88 bolag. Anton samma
#: dag: "vi slutar inte förrän vi levererat det beställda antalet PROCESSADE
#: leads". Taket finns kvar som skydd mot en skenande körning, inte som mål.
#: Sedan 2026-11-24 är det ett kostnadslarm: under målet förlängs det med
#: återstående behov × TAK_FAKTOR och loggas (api/leads.py:_forlang_tak).
TAK_FAKTOR = 12
#: Sökrundor i rad utan en enda ny kandidat innan körningen räknar
#: målgruppen som uttömd. Det är det verkliga slutet; max_rundor är bara
#: skyddsnätet ovanför. Den första tomma rundan i kundens egna branscher
#: breddar i stället sökningen till de breda B2B-branscherna i samma område
#: (korning["bred"], api/leads.py:_sla_in_sokrunda), och räkningen börjar om:
#: Antons beställning 2026-10-23, leverera beställt antal vad som än krävs.
#: Området breddas aldrig; bedömningen fäller ändå bolag utanför det.
TOMMA_RUNDOR = 4
#: Kandidater per sökrunda. Små rundor med flit (2026-10-09): en runda
#: levererar ingenting förrän den är klar, och med 25 per runda granskade
#: den första rundan i en körning på 40 bolagssidor och kontaktsökte i 13
#: minuter innan ett enda bolag researchades. Med 8 börjar researchen efter
#: några minuter, och nästa runda söker medan den pågår (sökrundan körs
#: utanför körningens lås, api/leads.py:_fyll_pa). Var 10 med tre rundor
#: före 2026-10-08: en körning kunde aldrig se fler än 30 kandidater.
MAX_PER_RUNDA = 8


def max_rundor(mal: int) -> int:
    """Skyddsnätet för antalet sökrundor: så många att TAK_FAKTOR undersökta
    per beställt lead ryms (50 → 75). Före 2026-10-15 var det 11 för 50, och
    körningarna slutade under beställt antal fast registret hade tusentals
    bolag kvar. Körningen slutar i stället när TOMMA_RUNDOR rundor i rad inte
    gett en enda ny kandidat (_fyll_pa_last). Kredittaket (korningstak) gäller
    fortfarande de betalda hämtningarna. Under målet förlängs rundtaket
    (korning["rundor_tak"], api/leads.py:_forlang_tak, 2026-11-24)."""
    return max(MAX_RUNDOR, -(-int(mal) * TAK_FAKTOR // MAX_PER_RUNDA))


def korningstak(mal: int) -> int:
    """Betalda sidhämtningar för hela körningen. 30 per beställt lead med
    golvet 60 (små beställningar) och taket 160 räckte inte: i en målgrupp
    där de flesta registerbolag saknar webbplats tog 101 registersidor slut
    på 8 granskade. Nu 12 per lead över golvet; taket var 600 (50 leads)
    och höjdes till 2400 när beställningstaket höjdes till 200 (Sebbe
    2026-10-18) — annars fick en körning på 200 bara 3 hämtningar per lead
    och svalt under målet med samma kvalitetsgrindar som strypte den."""
    mal = int(mal)
    return min(2400, max(60, 30 * mal if mal <= 5 else max(150, 12 * mal)))


def ny_korning(*, mal: int, scope: str, overrides: dict | None, is_test: bool) -> dict[str, Any]:
    return {
        "mal": mal,
        "levererade": 0,
        "undersokta": 0,
        "pagaende": 0,
        "kandidater": [],
        "rundor": 0,
        "tak": mal * TAK_FAKTOR,
        "tratt": [],
        "jobs": [],
        "klar": False,
        "slut_orsak": None,
        "flaskhals": None,
        "scope": scope,
        "overrides": overrides,
        "is_test": is_test,
    }


def har_malgrupp(profil: dict[str, Any], icp: dict[str, Any]) -> bool:
    """Har körningen något att sikta på utöver ort och storlek?

    Bransch (kundens filter, profilens segment eller SNI), ett kriterium eller
    en signal kunden kräver, eller en målgruppstext som sökningen kan läsa.
    Standarduteslutningen räknas inte: den säger bara vad som INTE söks."""
    return bool(
        icp.get("industries")
        or icp.get("sni_codes")
        or icp.get("must_have")
        or profil.get("branscher")
        or profil.get("segment")
        or profil.get("kriterier")
        or str(profil.get("malgrupp") or "").strip()
    )


def _ring_index(profil: dict[str, Any], kandidat: dict[str, Any]) -> int:
    """Lägre = tidigare i kundens geografiska prioritet. Okänt sist."""
    prefix = _prefix_ur_postnr(kandidat.get("postnr"))
    for i, ring in enumerate(profil.get("geo_prioritet") or []):
        if prefix is not None and f"{prefix:03d}" in (ring.get("postnr_prefix") or []):
            return i
    return len(profil.get("geo_prioritet") or []) + (0 if prefix is not None else 1)


async def sokrunda(
    profil: dict[str, Any], icp: dict[str, Any], korning: dict[str, Any], *, uteslut: set[str]
) -> None:
    """En sökrunda i nästa geo-ring. Fyller korning["kandidater"] och
    korning["tratt"]; höjer rundor. Kastar DiscoveryError om sökningen
    själv faller (anroparen avgör vad det betyder)."""
    # Hela rundor (2026-11-24): rundan krympte förr mot slutet (min(8, 2×behov),
    # behov utan de som redan researchas) men räknades ändå som en hel runda
    # mot max_rundor, så rundtaket nåddes med färre kandidater än taket. Är
    # registret slut syns det som tomma rundor (TOMMA_RUNDOR).
    antal = MAX_PER_RUNDA
    ring = korning["rundor"]
    korning["rundor"] += 1
    listspar: list[dict[str, Any]] = []
    bortval: list[dict[str, Any]] = []
    fynd = await hitta_bolag(
        icp, antal, uteslut_namn=uteslut, profil=profil, ring=ring, listspar=listspar, bortval=bortval,
        bred=bool(korning.get("bred")),
    )
    # Registrets bortval (filtret och Jev i sources/merinfo.sok) står i
    # tratten, så att nästa runda inte bedömer dem igen: annars började varje
    # runda om på samma fällda bolag och körningen tog slut långt under målet.
    # Org.nr följer med (2026-11-24): påfyllnadens storleksvidgning släpper
    # just de bortval som ligger närmast gränsen (tolka_storleksskal).
    for rad in bortval:
        korning["tratt"].append({"namn": rad["company_name"], "steg": "jev" if rad.get("jev") else "register",
                                 "skal": rad["skal"], "orgnr": rad.get("orgnr")})
    # Bara de ej kvalificerade är bortval i tratten. Ringlistan och de som
    # prövas om räknas för sig i sammanfattningen (fordelning nedan).
    for rad in listspar:
        if rad.get("spar", "ej_kvalificerad") == "ej_kvalificerad":
            korning["tratt"].append({"namn": rad["company_name"], "steg": "listspår", "skal": rad["signal_detalj"]})
    korning.setdefault("listspar", []).extend(listspar)
    for rad in listspar:
        pool_in(korning, rad)
    kvar: list[dict[str, Any]] = []
    for kandidat in fynd:
        namn = kandidat["company_name"]
        skal = forfiltrera(profil, kandidat, exclude_domains=icp.get("exclude_domains"))
        utslag(korning, namn, "förfilter", skal)
        if skal:
            korning["tratt"].append({"namn": namn, "steg": "förfilter", "skal": skal})
            continue
        fakta = await mat_webbplats(kandidat.get("website"))
        # Existensgrinden (leads/existens.py): en kandidat som inte kommer ur
        # registret måste styrkas av sin egen webbplats innan den kostar ett
        # Jev- eller researchanrop.
        ostyrkt = styrk(kandidat, fakta)
        utslag(korning, namn, "existens", ostyrkt)
        if ostyrkt:
            korning["tratt"].append({"namn": namn, "steg": "existens", "skal": ostyrkt})
            continue
        # Webbpoolen (plan 2026-10-08): varje styrkt bolag med webbplats, även
        # de Jev fäller nedan. Bara bolagsnivå (webbpool.POOLFALT).
        pool_in(korning, kandidat)
        kandidat["webbsignaler"] = fakta.get("rader") or []
        # Registerkällan (merinfo) har redan triagerat sina kandidater; en
        # andra Jev-fråga på samma bolag är bara kostnad.
        triage = kandidat.get("jev_triage") or await jev.triage(
            profil, kandidat, utdrag=fakta.get("utdrag") or "", signaler=kandidat["webbsignaler"]
        )
        if triage:
            kandidat["jev_triage"] = triage
            utslag(korning, namn, "jev", "; ".join(triage.get("fall_skal") or []) if triage.get("beslut") == "fall" else None)
            if triage.get("beslut") == "fall":
                korning["tratt"].append(
                    {
                        "namn": kandidat["company_name"],
                        "steg": "jev",
                        "skal": "; ".join(triage.get("fall_skal") or []),
                        "belagg": triage.get("stodrad"),
                    }
                )
                continue
        kvar.append(kandidat)
    kvar.sort(key=lambda k: _ring_index(profil, k))
    korning["kandidater"].extend(kvar)


def pool_in(korning: dict[str, Any], kandidat: dict[str, Any]) -> None:
    """Bolagets poolrad i körningens tillstånd, en per domän. Läses av
    webbpool.efter_korning när körningen är klar."""
    from .webbpool import bolagsrad

    rad = bolagsrad(kandidat, "korning")
    if rad:
        korning.setdefault("webbpool", {})[rad["doman"]] = rad


def utslag(korning: dict[str, Any], namn: str, grind: str, skal: str | None) -> None:
    """Kodgrindens utslag för ett bolag, släppt som fällt (Fas 7, insynen).

    Tratten bär bara bortvalen och räknas i sammanfattningen till kunden; en
    släppt rad där hade blivit en "bortvald" utan skäl. Utslagen ligger därför
    bredvid, i korning["utslag"], och följer med körningens tillstånd till
    liggaren (set_leads_job_status)."""
    korning.setdefault("utslag", []).append(
        {"namn": namn, "grind": grind, "utslag": "falld" if skal else "slappt", "skal": skal}
    )


def registrera_utfall(
    korning: dict[str, Any], *, namn: str, leverbar: bool, skal: str | None, undersokt: bool = True
) -> None:
    korning["pagaende"] = max(0, korning["pagaende"] - 1)
    korning["undersokta"] += int(undersokt)
    utslag(korning, namn, "research", None if leverbar else (skal or "inte leverbar"))
    if leverbar:
        korning["levererade"] += 1
    elif skal:
        korning["tratt"].append({"namn": namn, "steg": "research", "skal": skal})


#: Slut där ett tak stoppade körningen, och taket som namnges som flaskhals.
TAKSLUT = {"kredittak": "Sidtaket", "tak": "Taket"}


def avsluta(korning: dict[str, Any], orsak: str) -> None:
    """Sätter slutet — och namnger flaskhalsen när målet inte nåddes.

    "Slut på kandidater" utan ett enda bolag att pröva är inte en tom
    målgrupp, det är en sökning som inte hittade något: den heter
    `inga_traffar` och säger åt kunden vad som går att ändra."""
    if (
        orsak == "slut_pa_kandidater"
        and not korning["undersokta"]
        and not korning["levererade"]
        and not korning["tratt"]
        and not korning.get("listspar")
        # En körning vars sökrundor FÖLL (k["sokfel"], _sla_in_sokrunda) har
        # inte prövat målgruppen: den ska aldrig be kunden stava om orterna.
        and not korning.get("sokfel")
    ):
        orsak = "inga_traffar"
    korning["klar"] = True
    korning["slut_orsak"] = orsak
    if korning["levererade"] >= korning["mal"]:
        return
    if orsak in TAKSLUT:
        # Ett tak stoppade: det är taket som strypte, inte trattens vanligaste skäl.
        korning["flaskhals"] = TAKSLUT[orsak]
        return
    # Registrets och Jevs gratisbortval räknas inte (demon 2026-11-24: "för
    # stort", 621 gratis storleksbortval, stod som strypare fast taket stoppade).
    skal = [t for t in korning["tratt"] if t.get("steg") not in ("register", "jev")]
    if skal:
        typer = Counter(_skalstyp(t.get("skal")) for t in skal)
        korning["flaskhals"] = typer.most_common(1)[0][0] or None


def _skalstyp(skal: object) -> str:
    """Skälets rubrik, för räkningen i sammanfattningen.

    De flesta skäl är redan "Rubrik: detalj". Bedömningens bortval
    (bedomning.py) har formen "<kriteriets namn>: <vad som föll>", och
    kriteriets namn är det kunden VILL ha: sammanfattningen sa "3 bortvalda:
    ligger i göteborg" om bolag som låg utanför Göteborg (provkörningen
    2026-10-05). Ort och storlek får därför sin egen rubrik."""
    text = str(skal or "").strip()
    rubrik = text.split(":")[0].strip()
    if rubrik.casefold().startswith("ligger i "):
        return "Utanför målområdet"
    if rubrik.casefold().startswith("storlek "):
        return "Fel storlek"
    return rubrik


def fordelning(korning: dict[str, Any]) -> dict[str, int]:
    """Hur bolagen utanför Iris fördelades (Antons regler 12–16, 2026-10-07).
    Det körningen sparade (api/leads.py:_spara_listspar sätter "fordelning",
    efter dubblettkontrollen) går före räkningen ur listspåret."""
    if korning.get("fordelning"):
        return {"ring": 0, "ej_kvalificerade": 0, "prova_om": 0, "tak": 0, **korning["fordelning"]}
    rader = korning.get("listspar") or []
    spar = Counter(r.get("spar", "ej_kvalificerad") for r in rader)
    tak = sum(1 for r in rader if r.get("spar") == "prova_om" and r.get("tak"))
    return {
        "ring": spar["ring"],
        "ej_kvalificerade": spar["ej_kvalificerad"],
        "prova_om": spar["prova_om"] - tak,
        "tak": tak,
    }


def sammanfatta(korning: dict[str, Any]) -> str:
    """Tratten i en mening, för kunden."""
    # En vilande körning (vila) har inget slut, men skälet säger detsamma.
    orsak = korning.get("slut_orsak") or (korning.get("vilande") or {}).get("skal")
    if orsak == "inga_traffar":
        return (
            "Sökningen hittade inga bolag i målgruppen. Kontrollera stavningen på orterna "
            "eller bredda bransch eller område och kör igen."
        )
    if orsak == "sokningen_foll" and not korning["undersokta"]:
        # Tjänstefel, inte målgruppsfel: rådet "kontrollera stavningen" hör
        # inte hemma här, och "0 undersökta → 0 Iris-leads" säger inte varför.
        return (
            "Sökningen gick inte att genomföra: tjänsten bakom bolagssökningen svarade "
            "med fel. Målgruppen behöver inte ändras — försök igen om en stund."
        )
    delar = [f"{korning['undersokta']} undersökta"]
    typer = Counter(_skalstyp(t.get("skal")) for t in korning["tratt"])
    delar += [f"{antal} bortvalda: {typ.lower()}" for typ, antal in typer.most_common(3) if typ]
    f = fordelning(korning)
    # En provkörnings ringbolag är en lista under Listor, inte Samtal ›
    # Ringlista (api/leads.py:_spara_listspar, 2026-11-24). Texten visas som
    # den är (IrisKorningar), därför bara svenska som resten av meningen.
    ring = "i ringlistan under Listor" if korning.get("is_test") else "till ringlistan"
    text = ", ".join(delar) + (
        f" → {korning['levererade']} Iris-leads, {f['ring']} {ring}, "
        f"{f['ej_kvalificerade']} ej kvalificerade, {f['prova_om']} sajter utan hittad kontakt (prövas om)"
    )
    if f["tak"]:
        text += f", {f['tak']} stoppade av sidtaket (prövas om)"
    text += "."
    if korning["levererade"] < korning["mal"] and korning.get("flaskhals"):
        text += f" Det som strypte mest: {korning['flaskhals'].lower()}."
    if korning.get("bred"):
        text += " Bolagen i kundens branscher tog slut i området, så sökningen breddades till fler branscher där."
    skrap = korning.get("skrap") or {}
    betalda = sum(
        int(v) for k, v in skrap.items() if k not in ("cache", "tjanstefel") and isinstance(v, (int, float))
    )
    if skrap:
        text += f" {betalda} betalda sidhämtningar, {int(skrap.get('cache') or 0)} ur cachen."
    # Sanningsregeln: ett slut som beror på tjänsten ska säga det, inte låta
    # som att målgruppen var tom (tre körningar 2026-10-06 slutade så).
    if int(skrap.get("tjanstefel") or 0) > 0:
        text += f" {int(skrap['tjanstefel'])} hämtningar föll hos tjänsten (kredit, kvot eller tidsgräns)."
    return text


# --- Påfyllnaden (Antons regel 2026-11-24) ---------------------------------
#
# "Iris får aldrig, under inga omständigheter leverera under beställt antal,
# i värsta fall får man ta ett av de (mest kvalificerade) bortsorterade
# bolagen för att fylla ut kvoten, om inga fullt kvalificerade hittas."
#
# När målgruppen är slut under målet (api/leads.py:_fyll_pa_last) körs
# stegen nedan i ordning, ett i taget, med tillståndet i
# korning["pafyllnad"]. Är alla tömda vilar körningen (vila) i stället för
# att bli klar under målet, och väckaren prövar den igen en gång per dygn.
# Gäller Iris-körningar, även provkörningar, men inte listjobb.
# Geografin vidgas aldrig (Antons beslut 2026-10-23).

#: Steg 5, bolag med belagt nej på produktmatchningen eller ett måste-
#: kriterium. Sista utvägen; av med False.
PAFYLL_BELAGT_NEJ = True
#: Stegen i ordning: 1 researcha om tjänstefelen (och fallna sökrundor),
#: 2 pröva om sajterna utan hittad kontakt, 3 researchens bortval i
#: rangordning, 4 storleken vidgad stegvis, 5 belagt nej.
PAFYLLNADSSTEG = ("omforsok", "prova_om", "bortval", "storlek_25", "storlek_50", "storlek_100", "belagt_nej")
#: Storleksvidgningen per steg, som andel av kundens gräns (se vidgad_grans).
VIDGNING = {"storlek_25": 0.25, "storlek_50": 0.5, "storlek_100": 1.0}
#: Stegen som kräver nya sökrundor: meningslösa när kredittaket eller en
#: fallen sökning stoppat körningen, eller när målgruppen saknas.
_SOKSTEG = frozenset(VIDGNING)
_SOKSTOPP = frozenset({"kredittak", "sokningen_foll", "ingen_malgrupp"})
#: En vilande körning prövas igen så här ofta.
VILA_TIMMAR = 24
#: Researchens tjänstefel: bolaget bedömdes aldrig (steg 1, inte steg 3).
TJANSTEFEL = ("Inget källmaterial", "Researchen misslyckades", "Researchen gavs upp")


def nasta_pafyllnad(korning: dict[str, Any], orsak: str | None = None) -> str | None:
    """Nästa påfyllnadssteg som inte körts, eller None (då vilar körningen).
    `orsak` är slutet som utlöste påfyllnaden."""
    if korning.get("kalla") == "lista" or korning["levererade"] >= korning["mal"]:
        return None
    klara = set((korning.get("pafyllnad") or {}).get("klara") or [])
    stoppad = (orsak or korning.get("stopp")) in _SOKSTOPP
    for steg in PAFYLLNADSSTEG:
        if steg in klara or (steg == "belagt_nej" and not PAFYLL_BELAGT_NEJ) or (stoppad and steg in _SOKSTEG):
            continue
        return steg
    return None


#: Researchens bortval i den ordning de fyller på (steg 3): (a) under
#: kundens tröskel, (b) produktmatchningen okänd och alla måste-kriterier ja,
#: (c) ett okänt måste-kriterium, (d) ett nej på ett bör-kriterium, sist
#: övriga utan något belagt nej. "nej" (belagt nej) är steg 5.
BORTVALSGRUPPER = ("a", "b", "c", "d", "ovrigt")
#: Skälet kunden ser sparas som en kod i prospects.pafylld_skal och
#: översätts i gränssnittet (components/leads/pafyllnad.ts), så att det läses
#: på kundens språk. Svenska texter här för loggar och läsning av koden:
#: "a" under kundens tröskel (som "a:<träff>:<tröskel>" när talen finns),
#: "b" kopplingen till det kunden säljer kunde inte beläggas men alla krav är
#: uppfyllda, "c" ett krav kunde inte styrkas, "d" ett önskemål uppfylls
#: inte, "ovrigt" närmast att klara bedömningen, "nej" uppfyller inte alla
#: krav men var närmast målgruppen. Storleken: se utanfor_ursprung.
_GRUPPSKAL = frozenset({"a", "b", "c", "d", "ovrigt", "nej"})
_TROSKELTAL = re.compile(r"träffsäkerhet (\d+) av (\d+)")


def _utfall(p: dict[str, Any]) -> list[dict[str, Any]]:
    rader = p.get("score_breakdown")
    return [r for r in rader if isinstance(r, dict)] if isinstance(rader, list) else []


def bortvalsgrupp(p: dict[str, Any]) -> str | None:
    """Gruppen ett researchat bortval hör till, eller None när det inte är
    ett bortval ur researchen (inte nivå C, eller ett tjänstefel)."""
    from .profil import PRODUKTMATCH
    from .scoring import MISS, OKAND, TRAFF

    if p.get("niva") != "C" and p.get("qualified") is not False:
        return None
    dq = [str(d) for d in p.get("disqualifiers") or []]
    if any(d.startswith(TJANSTEFEL) for d in dq):
        return None
    rader = _utfall(p)
    kp = next((r for r in rader if r.get("nyckel") == PRODUKTMATCH), None)
    # Ett nej utan belägg (ingen verifierad rad ur källmaterialet) är okänt.
    kp_nej = bool(kp and kp.get("utfall") == MISS and (kp.get("belagg") or "produkter passar" in str(kp.get("motivering"))))
    kp_okand = bool(kp and not kp_nej and kp.get("utfall") != TRAFF)
    maste = [r for r in rader if r.get("hart") and r.get("nyckel") not in (PRODUKTMATCH, "underlag", "ort")
             and not str(r.get("nyckel") or "").startswith("u")]
    maste_nej = any(r.get("utfall") == MISS for r in maste)
    maste_okanda = sum(1 for r in maste if r.get("utfall") == OKAND)
    bor_nej = any(not r.get("hart") and r.get("utfall") == MISS for r in rader)
    if kp_nej or maste_nej:
        return "nej"
    if any(d.startswith("Under tröskeln") for d in dq):
        return "a"
    if kp_okand and not maste_okanda and not bor_nej:
        return "b"
    if maste_okanda == 1 and not bor_nej:
        return "c"
    if bor_nej and not maste_okanda:
        return "d"
    return "ovrigt"


def rangordna_bortval(prospekt: list[dict[str, Any]], *, grupper: tuple[str, ...]) -> list[dict[str, Any]]:
    """Bortvalen i `grupper`, i gruppernas ordning och inom varje grupp
    icp_fit fallande."""
    def fit(p: dict[str, Any]) -> float:
        try:
            return float(p.get("icp_fit") or 0)
        except (TypeError, ValueError):
            return 0.0

    valda = [(grupper.index(g), -fit(p), p) for p in prospekt if (g := bortvalsgrupp(p)) in grupper]
    return [p for _, _, p in sorted(valda, key=lambda t: (t[0], t[1]))]


def pafyllnadsskal(p: dict[str, Any], grupp: str | None) -> str:
    """Koden för skälet kunden ser ("Påfyllt: …"), se _GRUPPSKAL. Byggd ur
    gruppen och kundens egen tröskel, aldrig ur webbrevisionen eller dess
    betyg (Antons beslut 2026-10-08: webbplatsbedömningen är hemlig)."""
    dq = next((str(d) for d in p.get("disqualifiers") or [] if str(d).startswith("Under tröskeln")), None)
    if grupp == "a" and dq and (m := _TROSKELTAL.search(dq)):
        return f"a:{m[1]}:{m[2]}"
    return grupp if grupp in _GRUPPSKAL else "ovrigt"


_STORLEKSSKAL = re.compile(
    r"^För (?P<riktning>stort|litet): (?P<varde>\d+) anställda[^(]*\((?:högst|minst) (?P<grans>\d+)\)"
)
_OMSATTNINGSSKAL = re.compile(
    r"^För (?P<riktning>hög|låg) omsättning: (?P<varde>\d+) kr[^(]*\((?:högst|minst) (?P<grans>\d+) kr\)"
)


def tolka_storleksskal(skal: object) -> tuple[str, int, int] | None:
    """(gränsens fält, bolagets värde, kundens gräns) ur registrets eller
    förfiltrets bortvalsskäl, eller None. Fältet är profilens
    (anstallda_max/min, omsattning_max/min)."""
    text = str(skal or "").strip()
    if m := _STORLEKSSKAL.match(text):
        return ("anstallda_max" if m["riktning"] == "stort" else "anstallda_min", int(m["varde"]), int(m["grans"]))
    if m := _OMSATTNINGSSKAL.match(text):
        return ("omsattning_max" if m["riktning"] == "hög" else "omsattning_min", int(m["varde"]), int(m["grans"]))
    return None


def vidgad_grans(falt: str, grans: int, andel: float) -> int:
    """Kundens gräns vidgad med `andel` av sig själv: en övre gräns uppåt
    (49 → 62 vid 25 %), en undre nedåt (5 → 2 vid 50 %)."""
    if falt.endswith("_max"):
        return max(grans + 1, math.ceil(grans * (1 + andel)))
    return max(0, math.floor(grans * (1 - andel)))


def inom_vidgning(tolkat: tuple[str, int, int] | None, andel: float) -> bool:
    if not tolkat:
        return False
    falt, varde, grans = tolkat
    ny = vidgad_grans(falt, grans, andel)
    return varde <= ny if falt.endswith("_max") else varde >= ny


def utanfor_ursprung(pafyllnad: dict[str, Any], kandidat: dict[str, Any]) -> str | None:
    """Skälets kod "storlek:<fält>:<max|min>:<värde>:<gräns>" ("storleken
    vidgad: 55 anställda, kundens gräns är högst 49") när kandidaten ligger
    utanför kundens ursprungliga gränser (pafyllnad["ursprung"]) men inom den
    vidgade, annars None. Gränssnittet översätter koden (se _GRUPPSKAL)."""
    ursprung = pafyllnad.get("ursprung") or {}
    if not pafyllnad.get("vidgad"):
        return None
    for falt in ("anstallda", "omsattning"):
        varde = kandidat.get(falt)
        if not isinstance(varde, int) or isinstance(varde, bool):
            continue
        hi, lo = ursprung.get(f"{falt}_max"), ursprung.get(f"{falt}_min")
        if hi is not None and varde > hi:
            return f"storlek:{falt}:max:{varde}:{hi}"
        if lo is not None and varde < lo:
            return f"storlek:{falt}:min:{varde}:{lo}"
    return None


def far_fyllas_pa(
    rad: dict[str, Any],
    *,
    profil: dict[str, Any] | None,
    kontaktade: set[str] | frozenset[str] = frozenset(),
    sparrade: set[str] | frozenset[str] = frozenset(),
) -> str | None:
    """None när bolaget får fylla på kvoten, annars skälet. Den ENDA spärren
    för alla påfyllnadssteg (Antons regel 2026-11-24, punkt 2): avvecklat
    (regel 19), enskild firma (regel 15–16), Kontakta inte, redan kontaktat,
    ingen mottagaradress (telefon ensam räcker inte, regel 10), uteslutet i
    kundens profil, offentlig sektor som profilen inte pekat ut, listspårets
    ring och ej kvalificerade, och ett bolag utanför området (området
    breddas aldrig, 2026-10-23).

    `kontaktade`: bolagsnycklar (upptagna.nyckel) för bolag kunden redan
    mejlat eller fått Kontakta inte om i ett samtal. `sparrade`: adresser på
    suppressionslistan (casefold). Båda hämtas av api/leads.py:
    _pafyllnadens_sparrar."""
    from . import upptagna
    from .discovery import mottagare
    from .forfilter import ar_enskild_firma
    from .offentlig import offentlig_eller_skola
    from .platshallare import AVVECKLAT
    from .scoring import MISS

    texter = " ".join(
        str(t) for t in (*(rad.get("disqualifiers") or []), rad.get("signal_detalj"), rad.get("skal")) if t
    ).casefold()
    if rad.get("avvecklas") or AVVECKLAT in texter:
        return "Avvecklat: bolaget avvecklas (regel 19)."
    if ar_enskild_firma(rad.get("orgnr")) or "enskild" in str(rad.get("bolagsform") or "").casefold():
        return "Enskild firma (regel 15–16)."
    epost = str(rad.get("contact_email") or "").strip().casefold()
    if (
        rad.get("status") == "suppressed" or rad.get("utfall") == "kontakta_inte" or rad.get("kontakta_inte")
        or (epost and epost in sparrade)
    ):
        return "Kontakta inte: bolaget har bett att inte bli kontaktat."
    if rad.get("status") in ("contacted", "replied", "meeting", "won", "lost") or rad.get("arkiverad_at") or (
        kontaktade and upptagna.upptagen(set(kontaktade), rad.get("company_name"), rad.get("orgnr"))
    ):
        return "Redan kontaktat."
    if rad.get("spar") in ("ring", "ej_kvalificerad"):
        return "Listspårets bolag (ring eller ej kvalificerat) fylls aldrig på."
    if any(str(d).startswith("Uteslutet") for d in rad.get("disqualifiers") or []):
        return "Uteslutet i kundens profil."
    if not (profil or {}).get("offentlig_sektor") and offentlig_eller_skola(rad):
        return "Offentlig sektor: kundens profil pekar inte ut den."
    if any(r.get("nyckel") == "ort" and r.get("utfall") == MISS for r in _utfall(rad)):
        return "Utanför området: området breddas aldrig."
    if not mottagare(rad):
        return "Ingen mottagare: bolaget saknar en kontaktmejl (telefon ensam räcker inte)."
    return None


def vila(korning: dict[str, Any], skal: str, *, nu: datetime | None = None) -> None:
    """Körningen vilar under målet i stället för att bli klar: status kvar i
    'processing', undantagen från städaren, väckt en gång per dygn.
    `skal`: "registret" (alla steg tömda), "kredittak", "sokningen_foll"
    eller "ingen_malgrupp"."""
    korning["vilande"] = {"sedan": (nu or datetime.now(timezone.utc)).isoformat(), "skal": skal}
    korning["klar"] = False
    korning["slut_orsak"] = None


def vilans_skal(korning: dict[str, Any], orsak: str | None) -> str:
    """Vad som håller en vilande körning: ett stopp, en sökning utan en enda
    träff, eller ett register där alla påfyllnadssteg är tömda."""
    if orsak in _SOKSTOPP:
        return str(orsak)
    if not (korning["undersokta"] or korning["levererade"] or korning["tratt"] or korning.get("listspar")
            or korning.get("sokfel")):
        return "inga_traffar"
    return "registret"


def ska_vackas(korning: dict[str, Any], nu: datetime | None = None) -> bool:
    vilande = korning.get("vilande") or {}
    try:
        sedan = datetime.fromisoformat(str(vilande.get("sedan")))
    except ValueError:
        return True
    return (nu or datetime.now(timezone.utc)) - sedan >= timedelta(hours=VILA_TIMMAR)


def vakna(korning: dict[str, Any]) -> None:
    """Ett nytt dygn: stegen prövas om från början (nya bolag i registret,
    bortval som löpt ut), och sökningens stopp och räkning nollas."""
    korning.pop("vilande", None)
    for falt in ("stopp", "tomma_rundor", "sokfel", "dubblettrundor"):
        korning.pop(falt, None)
    pafyllnad = korning.setdefault("pafyllnad", {})
    pafyllnad["klara"] = []
    pafyllnad["vackt"] = int(pafyllnad.get("vackt") or 0) + 1


def demo() -> None:
    k = ny_korning(mal=2, scope="research_and_draft", overrides=None, is_test=True)
    k["pagaende"] = 2
    registrera_utfall(k, namn="A", leverbar=True, skal=None)
    registrera_utfall(k, namn="B", leverbar=False, skal="För stort: 700 anställda")
    k["tratt"].append({"namn": "C", "steg": "förfilter", "skal": "För stort: 120 anställda enligt källan"})
    avsluta(k, "slut_pa_kandidater")
    assert k["levererade"] == 1 and k["undersokta"] == 2 and k["flaskhals"] == "För stort"
    assert "För stort" in sammanfatta(k) or "för stort" in sammanfatta(k)
    profil = {"geo_prioritet": [{"etikett": "Sisjön", "postnr_prefix": ["421"]}, {"etikett": "Mölndal", "postnr_prefix": ["431"]}]}
    assert _ring_index(profil, {"postnr": "421 32"}) == 0
    assert _ring_index(profil, {"postnr": "431 30"}) == 1
    assert _ring_index(profil, {}) == 3
    print("korning: ok")


if __name__ == "__main__":
    demo()
