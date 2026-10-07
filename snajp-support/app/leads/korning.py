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
    nått, poolen och rundorna är slut, taket (4×N undersökta) är nått eller
    dygnsbudgeten tar slut. Slutet är alltid ärligt: tratten namnger det
    kriterium som strypte.

Körningens tillstånd bor i batchjobbets eget resultat (jobbstoret, TTL 1 h)
— ingen ny tabell. Läs-ändra-skriv skyddas av ett lås per körning
(`_korningslas` i app/api/leads.py, infört 2026-10-06 när leads_workers
höjdes över 1): workers i samma process serialiseras per körning, olika
körningar går parallellt. Fler REPLIKER av processen kräver ett Redis-lås.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from . import jev
from .discovery import hitta_bolag
from .existens import styrk
from .forfilter import forfiltrera
from .geo import _prefix_ur_postnr
from .webbsignal import mat_webbplats

MAX_RUNDOR = 3
TAK_FAKTOR = 4
MAX_PER_RUNDA = 10


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
    behov = korning["mal"] - korning["levererade"]
    antal = min(MAX_PER_RUNDA, max(3, 2 * behov))
    ring = korning["rundor"]
    korning["rundor"] += 1
    listspar: list[dict[str, Any]] = []
    fynd = await hitta_bolag(icp, antal, uteslut_namn=uteslut, profil=profil, ring=ring, listspar=listspar)
    # Bara de ej kvalificerade är bortval i tratten. Ringlistan och de som
    # prövas om räknas för sig i sammanfattningen (fordelning nedan).
    for rad in listspar:
        if rad.get("spar", "ej_kvalificerad") == "ej_kvalificerad":
            korning["tratt"].append({"namn": rad["company_name"], "steg": "listspår", "skal": rad["signal_detalj"]})
    korning.setdefault("listspar", []).extend(listspar)
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
    ):
        orsak = "inga_traffar"
    korning["klar"] = True
    korning["slut_orsak"] = orsak
    if korning["levererade"] < korning["mal"] and korning["tratt"]:
        typer = Counter(_skalstyp(t.get("skal")) for t in korning["tratt"])
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
    if korning.get("slut_orsak") == "inga_traffar":
        return (
            "Sökningen hittade inga bolag i målgruppen. Kontrollera stavningen på orterna "
            "eller bredda bransch eller område och kör igen."
        )
    delar = [f"{korning['undersokta']} undersökta"]
    typer = Counter(_skalstyp(t.get("skal")) for t in korning["tratt"])
    delar += [f"{antal} bortvalda: {typ.lower()}" for typ, antal in typer.most_common(3) if typ]
    f = fordelning(korning)
    text = ", ".join(delar) + (
        f" → {korning['levererade']} Iris-leads, {f['ring']} till ringlistan, "
        f"{f['ej_kvalificerade']} ej kvalificerade, {f['prova_om']} sajter utan hittad kontakt (prövas om)"
    )
    if f["tak"]:
        text += f", {f['tak']} stoppade av sidtaket (prövas om)"
    text += "."
    if korning["levererade"] < korning["mal"] and korning.get("flaskhals"):
        text += f" Det som strypte mest: {korning['flaskhals'].lower()}."
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
