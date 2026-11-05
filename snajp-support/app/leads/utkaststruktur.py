"""Utkastets struktur: A (utförlig, dagens) eller B (kort och rakt på).

Sebbes beställning 2026-11-05: den som kör Iris väljer A eller B vid "Kör
Iris", och alla nya leads i körningen får sina första mejl i den strukturen.
Förebilden för B är ett engelskt mejl på tre rader: hälsning, en enda fråga
om ett konkret utfall ("If I could … would that be useful?"), signatur.

## Vad som skiljer B från A

- **A** är oförändrad: ingång, produkt, erbjudande, inbjudan (facit
  2026-10-16, INV-LEADS-UTKAST-002, och formen i `erbjudanden.FORMER`).
- **B** är hälsningen, högst en kort mening om något konkret hos dem och en
  fråga om produktens utfall för dem. Mejlet SLUTAR med frågan, och
  erbjudandet (piloten) står bara i ungefär vart tredje B-mejl
  (`med_erbjudande`). Reglerna "aldrig sluta med en fråga" och "piloten i
  varje mejl" gäller A, inte B (Sebbe 2026-11-05: "gäller bara en förändring
  i nya B").

## Utfallet frågan bygger på

Kundens korta utfall per produkt (`erbjudanden.kort_utfall`, t.ex. Snajps
"40–50 nya företag i veckan som passar er …"). Utan det bygger frågan på
produktens nytta. Utfallet går in i faktagrindens underlag, så att dess
siffror får stå i mejlet men inga andra.

## Var valet bor

Körningens tillstånd (`k["struktur"]`), varje barnjobbs nyttolast, och
utkastets agent_runs-post (`{"step": "struktur"}`), så att "Skapa om utkast"
skriver om ett B-mejl som B (`tidigare`).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

Struktur = Literal["a", "b"]
STRUKTURER: tuple[str, ...] = ("a", "b")
STANDARD: Struktur = "a"
#: Postens nyckel i utkastets step_log (samma form som kodgrindarna).
LOGGSTEG = "struktur"

#: Brödtextens tak i B, hälsningen oräknad. Förebilden är 20 ord; 60 ger
#: plats åt den korta ingången och en erbjudandemening. Prövas i
#: stilkontrollen, som äger talet.
from .stilkontroll import MAX_ORD_B  # noqa: E402


def normalisera(varde: Any) -> Struktur:
    """Okänt eller saknat värde = A, så att gamla jobb och klienter som inte
    skickar fältet beter sig exakt som förut."""
    return "b" if str(varde or "").strip().casefold() == "b" else "a"


def med_erbjudande(tenant_id: str, prospect_id: str | None) -> bool:
    """Står erbjudandet i just det här B-mejlet? Ungefär vart tredje,
    deterministiskt per prospekt så att ett omskrivet utkast behåller sin
    variant (samma skäl som erbjudandearmarna i `erbjudanden.tilldela`)."""
    digest = hashlib.sha256(f"struktur_b:{tenant_id}:{prospect_id}".encode("utf-8")).digest()
    return digest[0] % 3 == 0


def med_ingang(tenant_id: str, prospect_id: str | None) -> bool:
    """Bär B-mejlet en kort mening om dem före frågan? Hälften av mejlen utan
    erbjudandet, deterministiskt, så att en körnings B-mejl inte alla ser
    likadana ut. Aldrig tillsammans med erbjudandet: provet i development
    2026-11-05 gav då 76 ord (ingång + agent + pilot + fråga), förebilderna
    har en sak före frågan, inte två."""
    if med_erbjudande(tenant_id, prospect_id):
        return False
    digest = hashlib.sha256(f"struktur_b_ingang:{tenant_id}:{prospect_id}".encode("utf-8")).digest()
    return digest[0] % 2 == 0


_HANDLING = re.compile(r"\s*Handling:.*$", re.IGNORECASE | re.DOTALL)


def kort_villkor(villkor: str | None) -> str:
    """Erbjudandet i B: villkorens första mening, utan dess "Handling".
    B:s handling är frågan, och villkorens övriga siffror (tre månader, upp
    till 50 %) gjorde B-mejlet i provet 2026-11-05 lika långt som A. Det som
    står här är också det stilgrinden kräver ska stå kvar i mejlet."""
    text = _HANDLING.sub("", (villkor or "").strip())
    forsta = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    return forsta


#: Förebilderna (Sebbe 2026-11-05: "alla utskick ska utgå från de du skrev som
#: exempel, för både leads och support"). Tre per agent: bara frågan, en rad
#: om dem före frågan, och med erbjudandet. Bolagsdetaljerna gäller påhittade
#: bolag och ska bytas mot mottagarens; formen och tonen är det som följs.
#: Hälsningen och signaturen läggs på i kod och står därför inte här.
FOREBILDER: dict[str | None, tuple[str, ...]] = {
    "leads": (
        "Om vår agent Iris kunde ta fram 40–50 nya företag i veckan som passar er, med ett färdigt "
        "första mejl till varje, skulle det vara till nytta?",
        "Ni har nyss börjat ta uppdrag åt fastighetsbolag. Om vår agent Iris varje vecka tog fram "
        "fastighetsbolag i regionen och skrev första mejlet till dem, skulle det hjälpa?",
        # Agenten före siffrorna (Antons regel, stilkontroll agent_efter_loftet).
        "Vår agent Iris hittar nya företagskunder åt er och skriver första mejlet, som ni godkänner "
        "innan det skickas. Just nu tar vi in 20 företag i en kostnadsfri pilot. Vore det intressant "
        "för er?",
    ),
    "support": (
        "Om vår Supportagent svarade direkt på de vanligaste kundfrågorna, dygnet runt, utifrån er "
        "egen information, skulle det frigöra tid för er?",
        "Ni har många kurser med olika datum och intyg. Om vår Supportagent svarade på frågorna om "
        "dem direkt i chatten och mejlen, även kvällar och helger, skulle det vara användbart?",
        "Vår Supportagent svarar på era kunders frågor utifrån er egen information och lämnar över "
        "till er när den inte är säker. Just nu tar vi in 20 företag i en kostnadsfri pilot. Låter det "
        "som något för er?",
    ),
}


def forebilder(produkt: str | None) -> tuple[str, ...]:
    """Förebilderna för produktens slag (Snajps Iris eller Supportagent).
    En annan kunds produkt får inga: förebilderna handlar om Snajps agenter,
    och formreglerna räcker."""
    from .stilkontroll import produktslag

    return FOREBILDER.get(produktslag(produkt), ())


def block(
    *,
    produkt: str | None,
    nytta: str | None,
    utfall: str | None,
    villkor: str | None,
    ingang: bool,
) -> str:
    """Promptblocket för struktur B, i utkaststeget och humanizern. Ersätter
    erbjudandeblocket i A. `villkor` = erbjudandets villkor när just det här
    mejlet ska bära erbjudandet (`med_erbjudande`), annars None."""
    namn = (produkt or "produkten").split(",")[0].strip()
    grund = (utfall or "").strip() or (nytta or "").strip()
    delar = [
        "## Mejlets struktur: B, kort och rakt på",
        "Mejlet är ett kort, personligt meddelande, inte ett säljmejl. Det går före skrivstilens "
        "regler om ingång, stycken och avslut. Efter hälsningen, i den här ordningen:",
    ]
    steg = 1
    if ingang:
        delar.append(
            f"({steg}) En mening om högst 20 ord om något konkret ur deras verksamhet enligt researchen "
            f"som {namn} hjälper dem med. Inget problem, ingen kritik, ingen uppräkning av sortimentet."
        )
        steg += 1
    if villkor:
        # Provet 2026-11-05: utan ordtak per mening blev varianten 66–76 ord.
        delar.append(
            f"({steg}) En mening om högst 15 ord om vad {namn} gör åt dem, sedan en mening om högst 15 ord "
            "med erbjudandet ur villkoren nedan, siffrorna oförändrade i sak. Inget annat ur villkoren."
        )
        steg += 1
    delar.append(
        f"({steg}) En enda fråga om högst 25 ord: om {namn} kunde ge dem utfallet nedan, översatt till "
        "deras verksamhet, skulle det vara till nytta (eller användbart, intressant) för dem? "
        f"{namn} namnges i frågan. Frågans ordalydelse väljer du själv."
    )
    delar.append(
        "Mejlet SLUTAR med frågan. Ingen inbjudan efter den, ingen länk, ingen bokning, ingen "
        "funktionslista och inget annat stycke. "
        + ("" if villkor else "Inget erbjudande, ingen pilot och ingen rabatt i det här mejlet. ")
        + f"Hela brödtexten högst {MAX_ORD_B} ord. Ämnesraden två till fem ord om utfallet för dem."
    )
    delar.append(
        f"\n### Utfallet frågan bygger på\n{grund or 'Det som står om produkten i produktlistan.'}\n"
        "Lova inget utöver det här och produktens nytta: siffror som inte står här eller i villkoren "
        "skrivs aldrig."
    )
    exempel = forebilder(produkt)
    if exempel:
        delar.append(
            "\n### Förebilder (brödtexten efter hälsningen)\n"
            "Mejlet utgår från de här förebilderna: samma längd, ton och rörelse, anpassat till just "
            "mottagarens verksamhet ur researchen. Detaljerna i dem (fastighetsbolag, kurser) gäller andra "
            "bolag och skrivs aldrig om de inte stämmer för mottagaren.\n"
            + "\n".join(f"- \"{e}\"" for e in exempel)
        )
    if villkor:
        delar.append(f"\n### Villkor för erbjudandet\n{villkor.strip()}")
    return "\n".join(delar)


def loggpost(struktur: Struktur, *, med_erbjudande_: bool = False, med_ingang_: bool = False) -> dict[str, Any]:
    post: dict[str, Any] = {"step": LOGGSTEG, "struktur": struktur}
    if struktur == "b":
        post.update(erbjudande=med_erbjudande_, ingang=med_ingang_)
    return post


async def tidigare(storage, tenant_id: str, prospect_id: str) -> Struktur:
    """Strukturen leadets senaste utkast skrevs i, eller A. Läses ur
    utkastets agent_runs-post; kastar aldrig."""
    try:
        runs = await storage.list_agent_runs_all(
            tenant_id=tenant_id, agent_type="leads_outreach", prospect_id=prospect_id, limit=1
        )
    except Exception:  # noqa: BLE001 — ett läsfel ska ge dagens beteende, inte fälla jobbet
        return STANDARD
    if not runs:
        return STANDARD
    logg = runs[0].get("step_log")
    if isinstance(logg, str):
        import json

        try:
            logg = json.loads(logg)
        except ValueError:
            return STANDARD
    for post in logg if isinstance(logg, list) else []:
        if isinstance(post, dict) and post.get("step") == LOGGSTEG:
            return normalisera(post.get("struktur"))
    return STANDARD
