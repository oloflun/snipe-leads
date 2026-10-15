"""Hälsningsraden och namnvettet i leads-utkast — avgjort i KOD.

Sebbe 2026-10-11: varje utkast ska se ut som ett mänskligt mejl. Hälsningen
bär personens förnamn när mottagaren är en namngiven person, annars bolagets
namn — aldrig "kontaktpersoner", en avdelning eller en ort. Uppmätt i
development samma dag: "Hej Lahoud," skickat ur contact_name "Kontaktpersoner
Lahoud", "Verkstad Öppettider" och "Umeå Börje" som kontakter i kön, och en
stor del av de köade utkasten utan hälsningsrad alls (texten började rakt in
i pitchen).

Regeln bor i kod och inte i prompten, av samma skäl som webbkriterierna
(leadsregel 9): prompten styr vad modellen FÖRSÖKER skriva, grinden här
avgör vad som faktiskt köas. Allt är idempotent — samma funktioner körs vid
köningen, vid läsning av granskningskön (äldre utkast) och vid godkännandet.
"""

from __future__ import annotations

import re

from .discovery import ar_personled

#: Bolagsformer som inte hör hemma i ett tilltal ("Hej Stöcke Svets," — inte
#: "Hej Stöcke Svets Aktiebolag,"). Främst och sist i namnet.
_BOLAGSFORM = re.compile(
    r"^(?:AB|HB|KB)\s+|\s+(?:AB|Aktiebolag|HB|KB|ekonomisk förening|ek\.?\s*för\.?)\.?$",
    re.IGNORECASE,
)

#: Ett namnled: bokstäver, eventuellt bindestreck eller apostrof. Siffror,
#: @ och skiljetecken betyder att "namnet" är något annat (en adress, en rubrik).
_NAMNLED = re.compile(r"^[A-Za-zÅÄÖåäöÉéÜü][A-Za-zÅÄÖåäöÉéÜü'’-]*$")

#: En REN hälsningsrad: hälsningsordet, eventuellt ett namn (utan
#: meningsskiljetecken), och högst ett avslutande tecken. "Hej! Vi hjälper …"
#: är en hälsning följd av text och matchar inte — den raden lämnas orörd.
_HALSNING_SV = re.compile(
    r"^\s*(hej|hejsan|hallå|god dag)\b[ \t]*([^,!.?;:\n]*?)[ \t]*[,!.]?[ \t]*$", re.IGNORECASE
)
_HALSNING_EN = re.compile(
    r"^\s*(hi|hello|hey|dear)\b[ \t]*([^,!.?;:\n]*?)[ \t]*[,!.]?[ \t]*$", re.IGNORECASE
)
_BORJAR_MED_HALSNING = re.compile(r"^\s*(hej|hejsan|hallå|god dag|hi|hello|hey|dear)\b", re.IGNORECASE)

#: Utfyllnad efter hälsningsordet som varken är namn eller bolag: "Hej där,",
#: "Hej alla,", "Dear Sir or Madam". Ersätts med en riktig hälsningsrad.
#: "igen" undantas i sakra_halsning — "Hej igen," är ett legitimt
#: uppföljningstilltal och lämnas orört.
_EJ_TILLTAL = frozenset(
    {"dar", "där", "alla", "du", "ni", "team", "teamet", "vanner", "vänner", "kollegor",
     "foretaget", "företaget", "sir", "madam", "or", "and", "there", "everyone", "all"}
)


def _versal(led: str) -> str:
    """Namnledets skiftläge: "PETER" och "peter" blir "Peter", "Hans-Eric"
    och "McDonald" lämnas — bara led HELT i versaler eller gemener rättas."""
    if not (led.isupper() or led.islower()):
        return led
    return "-".join(del_.capitalize() for del_ in led.split("-"))


def rensa_personnamn(namn: str | None) -> str | None:
    """Ett användbart personnamn ur ett kontaktfält, eller None.

    Led som inte kan vara namn (avdelningar, sajtord, orter — ar_personled)
    stryks: "Kontaktpersoner Lahoud" blir "Lahoud", "Umeå Börje" blir
    "Börje", "Verkstad Öppettider" blir None. Skiftläget rättas per led
    ("PETER SJÖLIN" → "Peter Sjölin"). Mer än fyra led är ingen person."""
    led = [d for d in str(namn or "").split() if _NAMNLED.match(d) and ar_personled(d)]
    if not led or len(led) > 4:
        return None
    return " ".join(_versal(d) for d in led)


def fornamn(namn: str | None, epost: str | None = None) -> str | None:
    """Förnamnet. Bär adressens lokaldel ett av namnets led är det förnamnet,
    oavsett ordning: kontakten "Delsbo Magnus" (orten före namnet på sajten)
    med magnus@akesmotor.se gav "Hej Delsbo," (Anton 2026-10-15)."""
    rensat = rensa_personnamn(namn)
    if not rensat:
        return None
    led = rensat.split()
    from .discovery import _asci

    lokal = _asci(str(epost or "").split("@")[0]) if "@" in str(epost or "") else ""
    for d in led:
        if len(_asci(d)) >= 3 and lokal.startswith(_asci(d)):
            return d
    # Utan stöd i adressen måste ordet se ut som ett förnamn: kontaktsökningen
    # gav "Scandinavia" (ur bolagsnamnet) och "Polarhandlare Inget" (2026-10-15).
    # Ett led som inte kan vara ett namn ("Hising Arbetsledare") gör hela
    # namnet osäkert: efternamnet stod först och rollen efter.
    return led[0] if all(_liknar_fornamn(d) for d in led) else None


#: Ord som står med versal intill en adress men aldrig är ett förnamn.
_INTE_FORNAMN = frozenset({
    "scandinavia", "skandinavien", "sverige", "sweden", "swedish", "nordic", "norden", "europe",
    "norr", "norra", "söder", "södra", "väst", "västra", "öst", "östra", "inget", "ingen", "alla",
    "butik", "butiken", "kundtjänst", "support", "service", "försäljning", "info", "kontakt",
})
#: Ändelser för substantiv och yrken ("Polarhandlare", "Försäljning",
#: "Verksamhet") som inga vanliga svenska förnamn har.
_INTE_NAMNANDELSE = ("are", "ning", "het", "else", "tion", "ande", "ende", "skap", "eri", "itet")


def _liknar_fornamn(ord_: str) -> bool:
    o = ord_.casefold()
    return len(o) >= 2 and o not in _INTE_FORNAMN and not o.endswith(_INTE_NAMNANDELSE)


def snyggt_bolagsnamn(bolag: str | None) -> str | None:
    """Bolagsnamnet som ett tilltal: utan bolagsform och utan avslutande
    ortsled ("B Flemströms Gräv & Last i Luleå AB" → "B Flemströms Gräv &
    Last" — Sebbe 2026-10-12), och versalgrytor ("HORTLAX RÖR AB") till
    läsbar form ("Hortlax Rör"). Ett namn i blandat skiftläge lämnas som
    bolaget själv skriver det."""
    namn = " ".join(str(bolag or "").split())
    forra = None
    while namn != forra:
        forra = namn
        namn = _BOLAGSFORM.sub("", namn).strip()
        namn = _utan_ortsled(namn)
    if not namn:
        return None
    ord_ = namn.split()
    # Helt i versaler OCH mer än ett ord: rätta. Ett ensamt versalord kan
    # vara en initialism (FOPTEC) och lämnas.
    if namn.isupper() and len(ord_) > 1:
        namn = " ".join(d if d == "&" else _versal(d) for d in ord_)
    return namn


#: Ett avslutande " i <Ort>" i bolagsnamnet. Orten måste vara en kommun vi
#: känner (profil.KOMMUNER, en eller två ord) — "ByggMix i Norr" och
#: "Markskydd i Väst" är varumärken, inte ortsled, och lämnas.
_ORTSLED = re.compile(r"\s+i\s+([A-ZÅÄÖ][\wåäöé-]*(?:\s+[A-ZÅÄÖ][\wåäöé-]*)?)$")


def _utan_ortsled(namn: str) -> str:
    m = _ORTSLED.search(namn)
    if not m:
        return namn
    from .profil import KOMMUNER

    if m.group(1).casefold() not in KOMMUNER:
        return namn
    kvar = namn[: m.start()].strip()
    return kvar or namn


def halsningsrad(kontakt: str | None, sprak: str = "sv", epost: str | None = None) -> str:
    """Hälsningsraden ett utkast SKA ha: personens förnamn om en namngiven
    person finns, annars EXAKT "Hej," på egen rad (Sebbe 2026-10-12:
    bolagsnamnet skrivs ALDRIG efter "Hej" — det avslöjar en mall direkt)."""
    namn = fornamn(kontakt, epost)
    if not namn:
        return "Hello," if sprak == "en" else "Hej,"
    return f"{'Hi' if sprak == 'en' else 'Hej'} {namn},"


def _ar_halsningsrad(rad: str, sprak: str) -> re.Match[str] | None:
    if len(rad) > 80:
        return None
    return (_HALSNING_EN if sprak == "en" else _HALSNING_SV).match(rad)


def sakra_halsning(
    body: str, *, kontakt: str | None, bolag: str | None, sprak: str = "sv", epost: str | None = None
) -> str:
    """Ser till att utkastet börjar med en riktig hälsningsrad. Idempotent.

    - Ingen hälsning alls → raden läggs till överst, med blankrad före texten.
    - "Hej," utan namn → personens förnamn sätts in om en person finns.
    - "Hej Verkstad," eller "Hej <Bolagsnamn>," → ersätts: bolagsnamn efter
      "Hej" skrivs ALDRIG (Sebbe 2026-10-12) — `bolag` används bara för att
      KÄNNA IGEN en sådan rad och byta den mot personens namn eller "Hej,".
    - "Hej Peter," där Peter är ett personnamn → lämnas (skiftläget rättas).

    Tilltalsformen (du/ni) rörs inte här — det gör tilltala_med_ni efteråt."""
    rader = body.split("\n")
    forsta = next((i for i, r in enumerate(rader) if r.strip()), None)
    ratt = halsningsrad(kontakt, sprak, epost)
    if forsta is None:
        # En tom text lämnas tom: textkvalitetens tom_text-kontroll ska se
        # den, inte en hälsningsrad som ser ut som ett utkast.
        return body
    m = _ar_halsningsrad(rader[forsta], sprak)
    if m is None:
        # Börjar raden med ett hälsningsord men bär mer text ("Hej! Vi
        # hjälper …") är det redan en hälsning — rör den inte, och lägg
        # framför allt inte en till ovanför.
        if _BORJAR_MED_HALSNING.match(rader[forsta]):
            return body
        return "\n".join([*rader[:forsta], ratt, "", *rader[forsta:]])
    namnet = m.group(2).strip()
    if namnet:
        if namnet.casefold() == "igen":
            return "\n".join(rader)
        # Bolagsnamn efter "Hej" skrivs aldrig — kontrollen ligger FÖRE
        # personkontrollen, för ett bolagsnamn kan se ut som en person
        # ("Hej Briell Bygg,").
        if _ar_bolagstilltal(namnet, bolag):
            rader[forsta] = ratt
            return "\n".join(rader)
        # Mer än fyra ord efter hälsningsordet som INTE är bolagets namn är
        # löptext ("Hej vi kan hjälpa er med …") — raden lämnas orörd hellre
        # än att en mening skrivs över med en hälsningsrad.
        if len(namnet.split()) > 4:
            return body
        rensat = rensa_personnamn(namnet)
        # Känd mottagare: hälsningen bär mottagarens förnamn, inget annat namn
        # ("Hej Delsbo," till Magnus, Anton 2026-10-15).
        kant = fornamn(kontakt, epost)
        if (
            rensat
            and (not kant or rensat.casefold() == kant.casefold())
            and rensat.casefold() == namnet.casefold()
            and namnet[0].isupper()
            and not any(d.casefold() in _EJ_TILLTAL for d in namnet.split())
        ):
            # En riktig persons namn — behåll modellens rad ("Hej Elin!" får
            # behålla sitt utropstecken); bara ett trasigt skiftläge rättas.
            if rensat != namnet:
                rader[forsta] = f"{m.group(1)} {rensat},"
            return "\n".join(rader)
    rader[forsta] = ratt
    return "\n".join(rader)


def _ar_bolagstilltal(namnet: str, bolag: str | None) -> bool:
    """Är hälsningens namn bolagets? Båda sidor jämförs även i kortform
    (utan bolagsform och ortsled), så att "Hej Granec Maskin," känns igen mot
    "Granec Maskin Aktiebolag" och "Hej X i Luleå," mot kortformen av X."""
    bolagsformer = {str(bolag or "").casefold(), (snyggt_bolagsnamn(bolag) or "").casefold()} - {""}
    if not bolagsformer:
        return False
    namnformer = {namnet.casefold(), (snyggt_bolagsnamn(namnet) or "").casefold()} - {""}
    return bool(namnformer & bolagsformer)


def normalisera_utkast(
    body: str, *, kontakt: str | None, bolag: str | None, sprak: str = "sv", epost: str | None = None
) -> str:
    """Hela hälsningspasset för ett utkast: rätt hälsningsrad + rätt tilltal.

    Körs på tre ställen med SAMMA funktion — vid köningen (nya utkast), vid
    läsning av granskningskön (utkast köade innan passet fanns) och vid
    godkännandet (sista nätet) — så att texten granskaren ser är texten som
    skickas. Idempotent."""
    from .outreach_playbook import _intervallstreck, tilltala_med_ni

    text = sakra_halsning(body, kontakt=kontakt, bolag=bolag, sprak=sprak, epost=epost)
    if sprak != "en":
        # "Hej," utan namn tilltalar bolaget: mejlet säger ni rakt igenom.
        text = tilltala_med_ni(text)
    return _intervallstreck(text)


async def normalisera_tenantens_utkast(storage, tenant_id: str) -> dict[str, int]:
    """Svepet: hälsningspasset + signaturen på tenantens ALLA osända utkast,
    oavsett status (väntar på granskning, godkänt i sändfönsterkön, stoppat).

    Köläsningens lata fix når bara awaiting_review, och bara när någon öppnar
    just den kundens kö. Det här är samma rättning för resten (Sebbe
    2026-10-12: alla befintliga utskick ska uppdateras), körbar via
    POST /api/admin/leads/normalisera-utkast. Idempotent: andra svepet
    rättar noll. Skickade mejl rörs aldrig — bara rader med osänd text."""
    from .signatur import HALSNING, dela_utkast, med_signatur_fore_fot, sla_ihop
    from .signatur import normalisera as normalisera_signatur

    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    sig = normalisera_signatur(settings.get("signatur"))
    lagen = await storage.utkast_lagen(tenant_id, med_text=True)
    prospekter = {str(p["id"]): p for p in await storage.list_prospects(tenant_id, limit=2000)}
    granskade = rattade = 0
    for pid, lage in lagen.items():
        # Bara trådar med en OSÄND text: med_text-läsningen tar det väntande
        # meddelandet först, så body är utkastet — men utan osända rader vore
        # body det senast skickade, och det skrivs aldrig om.
        if not lage.get("message_id") or (lage.get("antal_osanda") or 0) <= 0:
            continue
        body = str(lage.get("body") or "")
        if not body.strip():
            continue
        granskade += 1
        trad = await storage.get_outreach_thread(tenant_id, lage["thread_id"]) or {}
        sprak = "en" if trad.get("language_state") == "en_confirmed" else "sv"
        p = prospekter.get(str(pid), {})
        brodtext, svans = dela_utkast(body, sig)
        ny = sla_ihop(
            normalisera_utkast(
                brodtext, kontakt=p.get("contact_name"), bolag=p.get("company_name"), sprak=sprak,
                epost=p.get("contact_email"),
            ),
            svans,
            sig,
            halsning=HALSNING[sprak],
        )
        if sig:
            ny = med_signatur_fore_fot(ny, sig, halsning=HALSNING[sprak])
        if ny != body:
            await storage.update_outreach_message_text(
                tenant_id, lage["message_id"], subject=lage.get("subject") or "", body=ny
            )
            rattade += 1
    return {"granskade": granskade, "rattade": rattade}

