"""Skanningen — från inkorg till sparade kvitton, med dublettkontroll.

## Kedjan, i ordning

    hämta mejl → är det en kvittokandidat? → har vi läst just det mejlet?
    → läs av fälten (modell eller deterministiskt) → möjlig dubblett?
    → grinden avgör status → spara fälten, kasta mejlet

Mejlets INNEHÅLL sparas aldrig: precis som uppladdningsvägen
(`bookkeeping/underlag.py`) skrivs de avlästa fälten plus ett fingeravtryck,
och texten släpps när anropet är klart. Ett mejl vi inte har är ett mejl som
inte kan läcka.

## Dubbletterna — två spärrar, olika hårda

1. FINGERAVTRYCKET (hårt nej): sha256 över kontots adress + mejlets id.
   Samma mejl skannat två gånger blir aldrig två kvitton — det hoppas över
   utan kostnad, före varje modellanrop. Samma mekanik som uppladdningens
   sha256-spärr, och den delar lagringskolumn med den.
2. INNEHÅLLET (mjuk flagga): samma motpart + datum + belopp som ett redan
   sparat kvitto ger status granska_manuellt med en anmärkning som pekar ut
   originalet. Ett kvitto som skickats om i ett NYTT mejl är nästan alltid
   samma köp — men "nästan alltid" är inte alltid, så en människa avgör i
   stället för att raden tyst kastas.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from ..agent.bookkeeping_agent import bygg_verifikat, las_underlag
from ..bookkeeping.kontoplan import OkantKontoError
from ..bookkeeping.underlag import normalisera_falt
from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, check_underlag
from ..config import get_settings
from .mejl import Mejl, Mejlkonto
from .tolkning import ar_kvittokandidat, tolka_deterministiskt, valutaspärr


def mejlfingeravtryck(kontoadress: str, mejl_id: str) -> str:
    return hashlib.sha256(f"mejl:{kontoadress}:{mejl_id}".encode()).hexdigest()


@dataclass
class Skanningsresultat:
    """Vad en körning gjorde, mejl för mejl — indata till inkorgsvyn."""

    genomlasta: int = 0
    nya_kvitton: int = 0
    hoppade_dubbletter: int = 0
    handelser: list[dict[str, Any]] = field(default_factory=list)


def _anvand_deterministisk() -> bool:
    settings = get_settings()
    if (getattr(settings, "kvitto_tolkning", "") or "").strip().lower() == "deterministisk":
        return True
    return settings.is_simulation()


async def _las_av(mejl: Mejl) -> tuple[dict[str, Any], str, str, str | None]:
    """Fälten ur ett kvittomejl: (normaliserade fält, anmärkning, valuta,
    originalbelopp). Modellen när den finns, regexläsaren annars — grinden
    efteråt är densamma. Se `kvitton/tolkning.py`."""
    if _anvand_deterministisk():
        avlast = tolka_deterministiskt(mejl.text, avsandare=mejl.avsandare)
        return (
            normalisera_falt(avlast.falt),
            avlast.anmarkning,
            avlast.valuta,
            avlast.belopp_original,
        )

    # Modellvägen. Mejltexten går i användarposition som opålitlig data —
    # samma gräns som avläsningen av en uppladdad fil drar.
    avlasning = await las_underlag(
        f"Ämne: {mejl.amne}\nFrån: {mejl.avsandare} <{mejl.avsandaradress}>\n\n{mejl.text}"
    )
    falt, valuta, belopp_original, valutaanmarkning = valutaspärr(
        dict(avlasning.falt), mejl.text
    )
    anmarkning = "; ".join(a for a in (avlasning.anmarkning, valutaanmarkning) if a)
    return falt, anmarkning, valuta, belopp_original


async def skanna_inkorg(
    storage: Any, tenant_id: str, konto: Mejlkonto, *, max_antal: int = 50
) -> Skanningsresultat:
    """Hela kedjan. Returnerar en händelse per genomläst mejl, i inkorgens
    ordning, så att gränssnittet kan visa exakt vad agenten gjorde."""
    resultat = Skanningsresultat()
    mejlen = await konto.hamta_mejl(max_antal=max_antal)

    for mejl in mejlen:
        resultat.genomlasta += 1
        handelse: dict[str, Any] = {
            "mejl_id": mejl.id,
            "avsandare": mejl.avsandare,
            "amne": mejl.amne,
            "datum": mejl.datum,
        }

        if not ar_kvittokandidat(mejl):
            handelse["utfall"] = "ej_kvitto"
            resultat.handelser.append(handelse)
            continue

        fingeravtryck = mejlfingeravtryck(konto.adress, mejl.id)
        redan = await storage.get_bk_underlag_by_sha256(tenant_id, fingeravtryck)
        if redan is not None:
            handelse["utfall"] = "redan_last"
            resultat.hoppade_dubbletter += 1
            resultat.handelser.append(handelse)
            continue

        falt, anmarkning, valuta, belopp_original = await _las_av(mejl)
        if "datum" not in falt and mejl.datum:
            # Kvittot saknar eget datum men mejlet har ett mottagningsdatum.
            # Det skrivs in MED anmärkning: dagen kan skilja från köpdagen.
            try:
                from datetime import date

                falt["datum"] = date.fromisoformat(mejl.datum)
                anmarkning = "; ".join(
                    led
                    for led in (anmarkning, "Datumet är mejlets mottagningsdag")
                    if led
                )
            except ValueError:
                pass

        anmarkningar = [anmarkning] if anmarkning else []

        # Mjuk dubblettflagga: samma motpart + datum + belopp som ett redan
        # sparat kvitto. Se modulens docstring om varför den inte kastar.
        if falt.get("brutto") is not None and falt.get("motpart"):
            # Hela historiken, inte standardtaket på 200 rader: listan sorteras
            # äldst först, och med taket hade just de NYASTE kvittona — de ett
            # omskickat kvitto oftast dubblerar — fallit utanför jämförelsen.
            befintliga = await storage.list_bk_underlag(tenant_id, limit=100_000)
            for rad in befintliga:
                if (
                    rad.get("motpart") == falt.get("motpart")
                    and str(rad.get("datum") or "") == str(falt.get("datum") or "")
                    and rad.get("brutto") == falt.get("brutto")
                ):
                    anmarkningar.append(
                        f"Möjlig dubblett av {rad.get('filnamn') or rad.get('motpart')}"
                        f" ({rad.get('datum')}), beloppet räknas inte förrän du godkänt kvittot"
                    )
                    break

        # Utan underlag_id: bristerna visas för KUNDEN i kvittolistan, och ett
        # "mock-004:"-prefix är felsökningsspråk, inte kundspråk.
        verdikt = check_underlag(falt)
        status = verdikt.status
        mojlig_dubblett = any(a.startswith("Möjlig dubblett") for a in anmarkningar)
        if mojlig_dubblett:
            status = STATUS_GRANSKA

        # Verifikatet byggs FÖRE raden sparas. Grinden kräver bara att
        # kategorin finns, inte att den finns i kontoplanen — en modell som
        # svarar "resor" hade annars gett en sparad "klar" rad utan verifikat
        # och ett 500, och fingeravtrycket hade hoppat över mejlet för gott.
        verifikatrader: tuple = ()
        if verdikt.ok and not mojlig_dubblett:
            try:
                verifikatrader = tuple(bygg_verifikat(falt))
            except OkantKontoError:
                status = STATUS_GRANSKA
                anmarkningar.append(
                    f"Kategorin {falt.get('kategori')!r} finns inte i kontoplanen, välj en annan"
                )

        brister = verdikt.as_report()
        if belopp_original is not None or any("Inget totalbelopp" in a for a in anmarkningar):
            # Valuta- respektive beloppsanmärkningen förklarar redan varför
            # brutto/momssats saknas — att dessutom lista dem är att säga
            # samma sak tre gånger.
            brister = [b for b in brister if "brutto" not in b and "momssats" not in b]

        samlad_anmarkning = "; ".join(
            dict.fromkeys(a for a in (*anmarkningar, *brister) if a)
        )

        underlag = await storage.create_bk_underlag(
            tenant_id,
            sha256=fingeravtryck,
            filnamn=mejl.amne or "kvittomejl",
            mimetyp="message/rfc822",
            status=status,
            anmarkning=samlad_anmarkning,
            kalla="mejl",
            mejl_id=mejl.id,
            mejl_amne=mejl.amne,
            mejl_avsandare=f"{mejl.avsandare} <{mejl.avsandaradress}>".strip(),
            valuta=valuta,
            belopp_original=belopp_original,
            **{
                k: v
                for k, v in falt.items()
                if k in ("datum", "motpart", "brutto", "momssats", "riktning", "kategori", "betalstatus")
            },
        )

        # Verifikatet byggs bara för ett kvitto som grinden släppt igenom OCH
        # som inte är dubblettflaggat — en dubblett med verifikat hade räknats
        # i perioden, vilket är exakt det flaggan finns för att hindra.
        if verifikatrader:
            rader = verifikatrader
            befintliga_verifikat = await storage.list_bk_verifikat(tenant_id)
            await storage.create_bk_verifikat(
                tenant_id,
                underlag_id=underlag["id"],
                serie="A",
                nummer=str(len(befintliga_verifikat) + 1),
                datum=falt["datum"],
                text=falt.get("motpart", ""),
                rader=[
                    {"konto": r.konto, "debet": r.debet, "kredit": r.kredit, "text": r.text}
                    for r in rader
                ],
            )

        resultat.nya_kvitton += 1
        handelse["utfall"] = "kvitto" if status != STATUS_GRANSKA else "kvitto_granska"
        handelse["kvitto_id"] = underlag["id"]
        handelse["belopp"] = None if underlag.get("brutto") is None else f"{underlag['brutto']:f}"
        handelse["belopp_original"] = belopp_original
        handelse["kategori"] = underlag.get("kategori")
        handelse["motpart"] = underlag.get("motpart")
        handelse["status"] = status
        resultat.handelser.append(handelse)

    return resultat
