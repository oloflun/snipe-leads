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
        # Sebbes exempel, med frågan översatt till mottagaren (volymprovet
        # 2026-11-05: utan detaljen blev frågan samma mening till alla).
        "Om vår agent Iris kunde ta fram 40–50 nya byggföretag i veckan som behöver era tjänster, med "
        "ett färdigt första mejl till varje, skulle det vara till nytta?",
        "Ni har nyss börjat ta uppdrag åt fastighetsbolag. Om vår agent Iris varje vecka tog fram "
        "fastighetsbolag i regionen och skrev första mejlet till dem, skulle det hjälpa?",
        # Agenten före siffrorna (Antons regel, stilkontroll agent_efter_loftet),
        # och erbjudandet i EN mening: provet 2026-11-05 upprepade annars vad
        # agenten gör i frågan.
        "Vår agent Iris finns just nu i en kostnadsfri pilot för 20 företag. Om Iris tog fram hotell "
        "och konferensanläggningar som köper era tjänster och skrev första mejlet till dem, vore det "
        "intressant för er?",
    ),
    "support": (
        "Om vår Supportagent svarade direkt på kundernas frågor om leveranser och returer, dygnet runt, "
        "utifrån er egen information, skulle det frigöra tid för er?",
        "Ni har många kurser med olika datum och intyg. Om vår Supportagent svarade på frågorna om "
        "dem direkt i chatten och mejlen, även kvällar och helger, skulle det vara användbart?",
        "Vår Supportagent finns just nu i en kostnadsfri pilot för 20 företag. Om den svarade på era "
        "kunders frågor utifrån er egen information och lämnade över när den inte är säker, låter det "
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
            f"({steg}) En mening om högst 20 ord som konstaterar något konkret ur deras verksamhet enligt "
            f"researchen som {namn} hjälper dem med. Inget problem och ingen kritik: aldrig vad de eller "
            "deras kunder kräver, förväntar sig, behöver eller måste, aldrig \"för att driva "
            "verksamheten framåt\", och ingen uppräkning av sortimentet eller märken."
        )
        steg += 1
    if villkor:
        # Provet 2026-11-05: med en egen mening om vad agenten gör blev
        # varianten 53–76 ord, och frågan upprepade samma sak.
        delar.append(
            f"({steg}) EN mening om högst 15 ord med erbjudandet ur villkoren nedan, där {namn} står före "
            "siffrorna (\"Vår … finns just nu i …\"), siffrorna oförändrade i sak. Ingen separat mening om "
            "vad agenten gör, och inget annat ur villkoren."
        )
        steg += 1
    # Volymprovet 2026-11-05 (30 B-mejl): frågan blev ofta samma mening med
    # bara bolagsnamnet utbytt, och långa bolagsnamn sprängde meningstaket.
    delar.append(
        f"({steg}) En enda fråga om högst 30 ord: om {namn} kunde ge dem utfallet nedan, översatt till "
        "deras verksamhet, skulle det vara till nytta (eller användbart, intressant) för dem? "
        f"{namn} namnges i frågan. Frågan bär alltid en konkret detalj ur researchen om just dem, "
        "till exempel vilka deras kunder är eller vilken sorts bolag som passar dem (\"40–50 "
        "restauranger och caféer i regionen\" i stället för \"40–50 nya företag som passar er\"), "
        "aldrig bara bolagsnamnet. Skriv inte bolagsnamnet i frågan: \"för er\" eller \"för dig\" räcker. "
        "Detaljen får aldrig ändra vad produkten gör: hittar den företag är det sorter av företag "
        "(\"hotell och restauranger\"), aldrig privatpersoner, uppdrag eller \"kunder\" i allmänhet. "
        "Frågans ordalydelse väljer du själv."
    )
    delar.append(
        "Mejlet SLUTAR med frågan. Ingen inbjudan efter den, ingen länk, ingen bokning, ingen "
        "funktionslista och inget annat stycke. Säg aldrig samma sak två gånger: frågan upprepar inte "
        "en tidigare mening. "
        + ("" if villkor else "Inget erbjudande, ingen pilot och ingen rabatt i det här mejlet. ")
        + f"Hela brödtexten högst {MAX_ORD_B} ord. Ämnesraden två till fem ord om utfallet för dem."
    )
    delar.append(
        f"\n### Utfallet frågan bygger på\n{grund or 'Det som står om produkten i produktlistan.'}\n"
        "Översätt det till just dem, skriv det aldrig ordagrant. Lova inget utöver det här och "
        "produktens nytta: siffror som inte står här eller i villkoren skrivs aldrig."
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


_HALSNINGSRAD = re.compile(r"^(hej|hejsan|hallå|hi|hello)\b[^.?!]*,?$", re.IGNORECASE)
_HALSNINGSFRAS = re.compile(r"^(vänliga|bästa|med vänlig|hälsningar|mvh|best|kind)\b", re.IGNORECASE)


def ar_b(text: str) -> bool:
    """Är mejlet skrivet i struktur B? Brödtexten (utan hälsningsrad och
    hälsningsfras) är högst 70 ord och slutar med en fråga; ett A-mejl slutar
    aldrig med en fråga. Samma regel som `lib/leads/struktur.ts:arStrukturB`,
    för verktyg som läser köade utkast utan körningens spår
    (scripts/granska_utkast.py)."""
    rader = [r.strip() for r in str(text or "").strip().splitlines() if r.strip()]
    if rader and _HALSNINGSRAD.match(rader[0]):
        rader.pop(0)
    while rader and _HALSNINGSFRAS.match(rader[-1]):
        rader.pop()
    brod = " ".join(rader)
    return bool(brod) and brod.endswith("?") and len(brod.split()) <= 70


def _ordfoljd(text: str) -> list[str]:
    return re.findall(r"[0-9a-zåäöé–-]+", (text or "").casefold())


def utfall_ordagrant(text: str, utfall: str | None) -> bool:
    """Står kundens utfallstext ordagrant i mejlet? Då är frågan inte översatt
    till mottagaren (volymprovet 2026-11-05: "40–50 nya företag i veckan som
    passar er" i nästan varje B-mejl, med bara bolagsnamnet utbytt)."""
    ord_ = _ordfoljd(utfall or "")
    if len(ord_) < 5:
        return False
    hela = " ".join(_ordfoljd(text))
    return f" {' '.join(ord_)} " in f" {hela} "


#: Vad siffran i Iris-frågan får gälla: sorters företag. Bekräftelseprovet
#: 2026-11-05 lovade "40–50 nya byggprojekt" och "nya konsultuppdrag", och
#: volymprov fyra "nya kunder som söker hudvårdsbehandlingar" (privatpersoner).
_FEL_SAK = re.compile(
    r"\d+\s*[–-]\s*\d+\s+nya\s+(\w*projekt\w*|\w*uppdrag\w*|privatpersoner|kunder|konsumenter)\b",
    re.IGNORECASE,
)


def fel_sak_i_fragan(text: str, produkt: str | None) -> str | None:
    """Ordet efter siffran i ett Iris-mejl när det inte är en sorts företag
    ("byggprojekt", "uppdrag", "kunder"), annars None. Gäller bara Iris:
    Supportagentens fråga har ingen sådan siffra."""
    from .stilkontroll import produktslag

    if produktslag(produkt) != "leads":
        return None
    traff = _FEL_SAK.search(text or "")
    return traff.group(1) if traff else None


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
