"""Faktagrinden för supportsvar: ett svar får inte påstå något kunskapsbasen
inte bär.

## Varför en grind och inte bara en instruktion

Utkaststeget instrueras redan att grunda sig ENBART i kunskapsbasen. Det är
en förhoppning. Leads fick samma lärdom den hårda vägen (INV-GROUND-001: en
uppfunnen procentsats på väg ut i Snajps namn), och en supportagent som hittar
på ett telefonnummer, en returfrist eller en avgift gör kunden en björntjänst
i tenantens namn. Grinden körs i KOD på den exakta text kunden ska få.

## Nivåerna (per kund, `support_regler.FAKTAKONTROLL`)

Ebbots tre nivåer, men verkställda deterministiskt mot kunskapsbasen i
stället för av en andra modell — noll extra LLM-anrop när svaret håller:

  * **tillatande** — kontaktuppgifter: telefonnummer, e-postadresser och
    webbadresser måste finnas i underlaget. Det är den hallucination som
    skadar mest (kunden ringer ett nummer som inte finns).
  * **forsiktig** (standard) — dessutom siffror, belopp och procent:
    leveranstider, avgifter, frister.
  * **strikt** — dessutom löftesord (gratis, återbetalning, ersättning,
    garanti, rabatt), superlativ och namngivna exempel som inte står i
    underlaget.

## Underlaget

Kunskapsbasens träffar plus kundens EGNA repliker i samtalet (ordernumret
kunden själv angav är inte en hallucination) och tenantens namn.
Affärskontexten ingår INTE — den är bakgrund, inte faktakälla, samma gräns
som prompten drar.

Extraktorn för siffror och löftesord är leads-grindens
(`leads/grounding_gate.py`): en extraktor, två riktningar, så att underlaget
och svaret aldrig normaliseras olika.

## Källbindningen (INV-GROUND-002, 2026-11-16)

Underlaget var EN hopslagen textmassa: ett tal dög om det stod någonstans,
och kundens eget meddelande räknades som källa, tvärt emot grundprompten
avsnitt 3. Kunden kunde skriva "ni har väl 90 dagars öppet köp?" och få det
bekräftat. Mönstret är hämtat ur NVIDIA/auto-ontology (`kb_coverage.py`:
modellen pekar ut, koden slår upp, och bara det som faktiskt finns räknas):

  * Varje uppgift måste stå i EN namngiven källa (`Kalla`), och domen säger
    vilken (`Faktadom.belagg`).
  * Kundens egen text bär aldrig ett pris, en procentsats, en frist eller en
    webbadress. Ett ordernummer kunden själv angav får upprepas.
  * En frist binds till sin tidsenhet: källans "8 år" bär inte "8 månader".
  * På `strikt`: företagsuppgifterna i en mening måste stå i en och samma
    källa. En mening får inte sys ihop ur två artiklar.

## Citatläget (nivån `ordagrant`, INV-GROUND-003)

De tre första nivåerna prövar det som går att känna igen i en text: nummer,
adresser, tal, löftesord. Fri text ("du kan returnera utan kvitto") går inte
att pröva mekaniskt, och en omskrivning kan alltid ändra innebörden. Därför
finns en fjärde nivå som inte prövar modellens formuleringar alls:

  * Svaret till kunden byggs av KOD (`citatsvar`): bara meningar som står
    ordagrant i en källa, skrivna som de står i källan, plus hälsningen och
    agentens egna frågor. Allt annat modellen skrev stryks.
  * Finns ingen sådan mening säger agenten att den inte vet och erbjuder en
    kollega. Kundens egen text citeras aldrig.
  * Bara på svenska: kunskapsbasen är svensk, och en översättning är en ny
    formulering. Ett svar på ett annat språk lämnas till en kollega.

Det som sägs är alltså kundens egna godkända meningar. Det nivån inte kan
lova är att RÄTT mening valdes: urvalet gör modellen.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..leads.grounding_gate import (
    PermittedFacts,
    _extract_numbers,
    _mask_non_claims,
    build_permitted_facts,
    check_grounding,
)
from ..leads.text_delta import split_sentences
from . import support_texter

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>()\"']+", re.IGNORECASE)
# Samma svenska telefonformat som leads-grinden maskar bort: 0771-123456,
# 08-123 45 67, +46 70 123 45 67.
_TELEFON = re.compile(r"(?:\+46[\s-]?|\b0)\d[\d\s-]{5,}\d")
# Numrerade listor ("1. Logga in") — siffran är en ordningsmarkör, inte ett
# påstående. Maskas innan sifferkontrollen.
_LISTMARKOR = re.compile(r"(?m)^\s*\d{1,2}[.)]\s")

_LOFTESORD = re.compile(
    r"\b(gratis|kostnadsfri\w*|fri\s+frakt|återbetal\w*|ersätt\w*|kompensation\w*|"
    r"garanti\w*|garanter\w*|rabatt\w*|pengarna\s+tillbaka)\b",
    re.IGNORECASE,
)

#: Siffror och belopp — det `forsiktig` kontrollerar ur leads-grindens fynd.
_SIFFERSLAG = ("number", "percent", "amount")

#: Talets storlek ur en normaliserad nyckel ("3990SEK" -> "3990", "2.5%" -> "2.5").
_STORLEK = re.compile(r"^\d+(?:\.\d+)?")

#: Klockslag ("14:00", "9:30"). Sifferextraktorn läser kolonet som en
#: avgränsare och ser två tal, 14 och 00 — och "00" finns sällan i en
#: kunskapsbas som skriver "klockan 14". Uppmätt 2026-09-19 på dev: ett
#: korrekt arabiskt svar ("قبل الساعة 14:00") fälldes på exakt det och
#: ersattes av osäkerhetssvaret. Skrivs om till decimalform (14.00 → 14,
#: 14:30 → 14.3) på BÅDA sidor, så att normaliseringen förblir symmetrisk.
#: `\d` är Unicode här med flit: en arabisk kund kan få "١٤:٠٠", och
#: normalize_number läser arabisk-indiska siffror (float("١٤") == 14.0).
_KLOCKSLAG = re.compile(r"\b(\d{1,2}):(\d{2})\b")


#: Engelsk tusentalsavgränsare ("3,990", "12,500", "1,234,567"). Sifferext-
#: raktorn är svensk: komma är decimaltecken, så "3,990" blev 3.99 och föll
#: mot kunskapsbasens "3 990 kr". Uppmätt på dev 2026-09-19: en engelsk kund
#: fick "I don't have information on the exact monthly cost" — faktagrinden
#: hade strukit ett KORREKT pris. Bara grupper om exakt tre siffror efter
#: kommat räknas, så en svensk decimal ("3,99", "1,5") är orörd. Samma
#: omskrivning på båda sidor håller jämförelsen symmetrisk.
_TUSENTAL_KOMMA = re.compile(r"(?<![\d,])(\d{1,3})((?:,\d{3})+)(?![\d,])")


def _klockslag_som_tal(text: str) -> str:
    text = _TUSENTAL_KOMMA.sub(lambda m: m.group(1) + m.group(2).replace(",", ""), text)
    return _KLOCKSLAG.sub(r"\1.\2", text)


#: Nivån som bygger svaret av källans meningar (citatläget).
ORDAGRANT = "ordagrant"
#: Källslaget för det kunden själv skrivit. Bär ekon, aldrig villkor.
KUNDTEXT = "kundtext"
#: Fasta uppgifter: tenantens namn och 112 vid kris.
FAST = "fast"
#: Slag som inte bär företagets egna uppgifter, och därför står utanför
#: meningskravet på `strikt`. Varje annat slag bär dem: ett nytt eller
#: felstavat slag hamnar innanför kravet, inte utanför.
_EJ_BARANDE = frozenset({KUNDTEXT, FAST})


@dataclass(frozen=True)
class Kalla:
    """En namngiven källa i faktagrindens underlag.

    `id` är det som skrivs i domens belägg ("KB-2" är artikel två i
    körningens kunskapsbasblock, samma ordning som svarets `kb_sources`).
    `slag` är en etikett; bara `KUNDTEXT` och `FAST` ändrar vad källan bär.
    """

    id: str
    text: str
    slag: str = "kb"


def kb_kallor(articles: Sequence[dict]) -> list[Kalla]:
    """Kunskapsbasens träffar som källor, numrerade som i prompten (KB-1 är
    första artikeln i `support_agent._kb_block`)."""
    return [
        Kalla(f"KB-{i}", f"{a.get('title') or ''}\n{a.get('content') or ''}")
        for i, a in enumerate(articles, 1)
    ]


def kundtext(text: str) -> Kalla:
    """Det kunden själv skrivit: ämne, meddelande, tidigare repliker."""
    return Kalla("KUNDTEXT", text or "", KUNDTEXT)


@dataclass(frozen=True)
class Faktadom:
    ok: bool
    #: Läsbara beskrivningar av det som saknar stöd, i fyndordning.
    ostodda: tuple[str, ...] = ()
    #: (uppgift, käll-ID:n som bär den) för varje uppgift som höll.
    belagg: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def belagg_json(self) -> list[dict]:
        """Belägget i den form körningens `faktagrind` sparar."""
        return [{"uppgift": u, "kallor": list(k)} for u, k in self.belagg]


#: Tidsenheten direkt efter ett tal: "30 dagar", "8 års", "5 arbetsdagar",
#: "14-day", "2 weeks". En frist är talet OCH enheten.
# ponytail: bara enheten direkt efter talet läses. I "2–4 dagar" får 2 ingen
# enhet och jämförs på storlek som förut. Räcker tills en mätning visar annat.
# Hela ord med sina böjningar, inte prefix: "min" får inte träffa "minst".
_TID = re.compile(
    r"[\s-]*(?:arbets|var|bank|kalender|business\s+|working\s+)?(?:"
    r"(?P<sekund>sekund(?:er|ers)?|sek)|(?P<minut>minut(?:er|ers)?|min|minutes?)"
    r"|(?P<timme>timm(?:e|ar|ars)|tim|hours?)|(?P<dag>dag(?:ar|ars|s)?|dygn|days?)"
    r"|(?P<vecka>veck(?:a|or|ors)|weeks?)|(?P<månad>månad(?:er|ers|s)?|mån|months?)"
    r"|(?P<år>års?|years?)"
    r")\b",
    re.IGNORECASE,
)


def _tidsenhet(text: str, slut: int) -> str | None:
    m = _TID.match(text, slut)
    return m.lastgroup if m else None


def _telefonsiffror(text: str) -> str:
    siffror = re.sub(r"\D", "", text)
    return "0" + siffror[2:] if siffror.startswith("46") else siffror


def _doman(url: str) -> str:
    utan = re.sub(r"^(?:https?://)?(?:www\.)?", "", url.lower())
    return utan.split("/", 1)[0].rstrip(".,;:!?")


@dataclass(frozen=True)
class _Index:
    """Det EN källa bär, extraherat med samma mönster som svaret läses med."""

    kalla: Kalla
    mejl: frozenset[str]
    domaner: frozenset[str]
    nummer: frozenset[str]
    #: Talets storlek -> tidsenheterna det står med (None = utan tidsenhet).
    tal: dict[str, set[str | None]]


def _indexera(kalla: Kalla) -> _Index:
    text = _klockslag_som_tal(kalla.text)
    mejl = {m.group(0).lower() for m in _EMAIL.finditer(text)}
    tal: dict[str, set[str | None]] = {}
    # Kontaktuppgifter maskas på källsidan som i svaret: siffrorna i ett
    # telefonnummer ("08-123 45 67") är inga tal som bär "8 månader".
    utan_kontakt = _mask_non_claims(text)
    for claim in _extract_numbers(utan_kontakt):
        if storlek := _STORLEK.match(claim.normalized):
            tal.setdefault(storlek.group(0), set()).add(_tidsenhet(utan_kontakt, claim.span[1]))
    return _Index(
        kalla=kalla,
        mejl=frozenset(mejl),
        domaner=frozenset(
            {_doman(m.group(0)) for m in _URL.finditer(text)} | {a.split("@", 1)[1] for a in mejl}
        ),
        nummer=frozenset(_telefonsiffror(m.group(0)) for m in _TELEFON.finditer(text)),
        tal=tal,
    )


# -- Citatläget ---------------------------------------------------------------

#: Kortaste mening som räknas som ett citat. En rubrik ("Returer") bär ingen
#: uppgift, och ett enstaka ord skulle träffa mitt i modellens egna meningar.
_MIN_CITATORD = 3
_ORD = re.compile(r"[^\W_]+")
_LISTTECKEN = "-•*#> \t"
_HALSNING = frozenset({"hej", "hejsan", "hallå"})
#: Artighetsfraser som får stå utan källa. Listan är sluten med flit: varje
#: öppen formulering här vore ett ställe där en uppgift kan smita förbi.
_TACK = frozenset(
    tuple(fras.split())
    for fras in (
        "tack",
        "tack för ditt meddelande",
        "tack för din fråga",
        "tack för att du hör av dig",
    )
)


def _ordfoljd(text: str) -> tuple[str, ...]:
    """Orden i texten, utan skiftläge och skiljetecken. Det är jämförelsenyckeln
    för ett citat: samma ord i samma ordning."""
    return tuple(_ORD.findall(unicodedata.normalize("NFKC", text).lower()))


def _meningar(text: str) -> list[str]:
    """Texten i meningar, rad för rad: en punktlista är en mening per rad."""
    ut: list[str] = []
    for rad in _LISTMARKOR.sub("", text).splitlines():
        for start, slut in split_sentences(rad):
            if mening := rad[start:slut].strip().lstrip(_LISTTECKEN).strip():
                ut.append(mening)
    return ut


@dataclass(frozen=True)
class _Citat:
    """Det som får citeras: källornas meningar, och orden i fasta uppgifter."""

    #: Ordföljd -> (meningen som den står i källan, käll-ID).
    meningar: dict[tuple[str, ...], tuple[str, str]]
    #: Första ordet -> längderna på de citat som börjar med det, längst
    #: först: ett långt citat går före ett kort, och bara de längder som
    #: kan träffa prövas.
    langder: dict[str, tuple[int, ...]]
    #: Orden i fasta uppgifter (tenantens och kundens namn), åt hälsningen.
    namnord: frozenset[str]

    @classmethod
    def ur(cls, kallor: Sequence[Kalla]) -> "_Citat":
        meningar: dict[tuple[str, ...], tuple[str, str]] = {}
        langder: dict[str, set[int]] = {}
        namnord: set[str] = set()
        for kalla in kallor:
            if kalla.slag == KUNDTEXT:
                continue  # kundens egen text är aldrig ett belägg
            if kalla.slag == FAST:
                namnord.update(_ordfoljd(kalla.text))
            for mening in _meningar(kalla.text):
                ordfoljd = _ordfoljd(mening)
                if len(ordfoljd) >= _MIN_CITATORD:
                    meningar.setdefault(ordfoljd, (mening, kalla.id))
                    langder.setdefault(ordfoljd[0], set()).add(len(ordfoljd))
        return cls(
            meningar,
            {o: tuple(sorted(l, reverse=True)) for o, l in langder.items()},
            frozenset(namnord),
        )

    def i(self, ordfoljd: tuple[str, ...]) -> tuple[list[tuple[str, str]], bool]:
        """Källmeningarna som står ordagrant i ordföljden, och om de täcker
        hela ordföljden (inga egna ord mellan eller runt citaten)."""
        funna: list[tuple[str, str]] = []
        hel, pos = True, 0
        while pos < len(ordfoljd):
            for langd in self.langder.get(ordfoljd[pos], ()):
                if traff := self.meningar.get(ordfoljd[pos : pos + langd]):
                    funna.append(traff)
                    pos += langd
                    break
            else:
                hel, pos = False, pos + 1
        return funna, hel

    def prov(self, svar: str):
        """Varje mening i svaret med sitt utfall: (mening, slag, citaten i
        den, hel). Slaget är "fraga", "artighet" eller "citat"; en mening med
        slaget "citat" som inte är `hel` bär egna ord. EN regel, läst av både
        `citatsvar` (som bygger svaret) och `kontrollera` (som dömer det)."""
        for mening in _meningar(svar):
            ordfoljd = _ordfoljd(mening)
            if not ordfoljd:
                continue
            if _ar_fraga(mening):
                yield mening, "fraga", [], True
            elif self.artighet(ordfoljd):
                yield mening, "artighet", [], True
            else:
                yield mening, "citat", *self.i(ordfoljd)

    def artighet(self, ordfoljd: tuple[str, ...]) -> bool:
        """"Hej Anna" (bara hälsningsord och ett känt namn) eller ett fast tack."""
        return ordfoljd in _TACK or (
            ordfoljd[0] in _HALSNING and set(ordfoljd[1:]) <= self.namnord
        )


def _ar_fraga(mening: str) -> bool:
    # ponytail: en fråga är inget påstående och släpps igenom som den står.
    # Tal, adresser och löftesord i den prövas fortfarande av nivåerna under.
    return mening.rstrip().endswith("?")


def citatsvar(svar: str, kallor: Sequence[Kalla]) -> tuple[str, int]:
    """Svaret i citatläget, byggt av kod: hälsningen, agentens frågor och de
    meningar som står ordagrant i en källa. Citaten skrivs som de står I
    KÄLLAN, inte som modellen skrev dem. Returnerar texten och antalet strukna
    meningar; texten är tom när varken ett citat eller en fråga finns kvar."""
    rader: list[str] = []
    bar_nagot, strukna = False, 0
    for mening, slag, funna, hel in _Citat.ur(kallor).prov(svar):
        strukna += not hel
        # En hälsning står kvar men bär inget: ensam är den inget svar.
        bar_nagot = bar_nagot or slag == "fraga" or bool(funna)
        for rad in [mening] if slag != "citat" else [kallmening for kallmening, _ in funna]:
            if rad not in rader:
                rader.append(rad)
    return ("\n".join(rader) if bar_nagot else ""), strukna


#: Nivån `forsiktig` dömer bara talen, och de prövas källa för källa. Den
#: tomma mängden får `check_grounding` att lämna tillbaka varje tal i svaret.
_INGA_FAKTA = PermittedFacts(frozenset(), frozenset(), frozenset(), ())


def kontrollera(
    svar: str,
    *,
    niva: str,
    kallor: Sequence[str | Kalla],
    tenant_namn: str = "",
) -> Faktadom:
    """Håller svaret mot underlaget på kundens nivå?

    `kallor` är namngivna källor (`Kalla`). En ren sträng läses som en
    kunskapsbaskälla. En okänd nivå behandlas som `forsiktig` — standardvärdet,
    inte det tillåtande.
    """
    namngivna = [k if isinstance(k, Kalla) else Kalla(f"K{i}", k) for i, k in enumerate(kallor, 1)]
    namngivna.append(Kalla("TENANT", tenant_namn, FAST))
    index = [_indexera(k) for k in namngivna if k.text]
    # `tillatande` är oförändrad: kontaktuppgifter mot vilken källa som helst.
    skarpt = niva != "tillatande"
    ordagrant = niva == ORDAGRANT
    strikt = ordagrant or niva == "strikt"
    text = _klockslag_som_tal(svar)

    ostodda: list[str] = []
    #: (position, uppgift, käll-ID:n som bär den, räknas i meningskravet)
    hallna: list[tuple[int, str, frozenset[str], bool]] = []

    def prova(pos: int, uppgift: str, alla: list[_Index], *, villkor: bool = False) -> None:
        """`alla` är källorna som har uppgiften. Ett villkor (pris, procent,
        frist, webbadress) får inte hämtas ur kundens egen text."""
        stod = [ix for ix in alla if not (villkor and skarpt and ix.kalla.slag == KUNDTEXT)]
        if stod:
            hallna.append((
                pos,
                uppgift,
                frozenset(ix.kalla.id for ix in stod),
                all(ix.kalla.slag not in _EJ_BARANDE for ix in stod),
            ))
        else:
            ostodda.append(uppgift + (" (står bara i kundens eget meddelande)" if alla else ""))

    for m in _EMAIL.finditer(text):
        v = m.group(0).lower()
        prova(m.start(), f"e-postadress: {m.group(0)!r}", [ix for ix in index if v in ix.mejl])
    for m in _URL.finditer(text):
        v = _doman(m.group(0))
        prova(
            m.start(), f"webbadress: {m.group(0)!r}",
            [ix for ix in index if v in ix.domaner], villkor=True,
        )
    for m in _TELEFON.finditer(text):
        v = _telefonsiffror(m.group(0))
        prova(
            m.start(), f"telefonnummer: {m.group(0).strip()!r}",
            [ix for ix in index if v in ix.nummer],
        )

    underlag = "\n".join(ix.kalla.text for ix in index) if strikt else ""
    if skarpt:
        # Superlativ, namngivna kunder och case döms bara på `strikt`, mot hela
        # underlaget som förut. Talen prövas källa för källa på båda nivåerna.
        fakta = _INGA_FAKTA
        if strikt:
            fakta = replace(
                build_permitted_facts(
                    context_pack=_klockslag_som_tal(underlag),
                    research_evidence=(),
                    offer_summary="",
                    brief="",
                    tenant_name=tenant_namn,
                    company_name=tenant_namn,
                ),
                numbers=frozenset(),
            )
        # Kontaktuppgifterna är redan kontrollerade ovan, och listmarkörer
        # är inga påståenden — båda maskas med samma längd.
        maskerad = _LISTMARKOR.sub(lambda m: " " * len(m.group(0)), text)
        for claim in check_grounding(maskerad, fakta).unsupported:
            if claim.kind not in _SIFFERSLAG:
                if strikt:
                    ostodda.append(claim.describe())
                continue
            # Storleken, inte valutan eller procenttecknet. Leads-extraktorn
            # läser enheten bara EFTER talet och bara på svenska: "SEK 3,990"
            # blir talet 3990 medan kunskapsbasens "3 990 kr" blir beloppet
            # 3990SEK, och engelskans "25 percent" matchar inte "25 procent".
            # Ett påhittat tal har en storlek som inte finns i underlaget.
            storlek = _STORLEK.match(claim.normalized)
            if not storlek:
                ostodda.append(claim.describe())
                continue
            s, tid = storlek.group(0), _tidsenhet(maskerad, claim.span[1])
            # ponytail: en källa som har talet utan tidsenhet bär det med
            # vilken enhet som helst ("8 elektroder" bär "8 månader").
            # Hellre det än att fälla "inom 5" + radbrytning + "dagar".
            prova(
                claim.span[0],
                claim.describe(),
                [
                    ix
                    for ix in index
                    if (enheter := ix.tal.get(s)) is not None
                    and (tid is None or tid in enheter or None in enheter)
                ],
                villkor=tid is not None or claim.kind in ("percent", "amount"),
            )

    if strikt:
        lagt = underlag.lower()
        for m in _LOFTESORD.finditer(svar):
            if m.group(0).lower() not in lagt:
                ostodda.append(f"löfte: {m.group(0)!r}")
        # En mening, en källa. Ekon ur kundens text och fasta uppgifter står
        # utanför: "Din order 12345 levereras inom 5 dagar" är en källa och
        # ett eko, inte två hopblandade källor.
        # I citatläget är varje mening redan en hel källmening; där dömer
        # ordagrant-kontrollen nedan i stället.
        if not ordagrant:
            for start, slut in split_sentences(text):
                bundna = [ids for pos, _, ids, barande in hallna if barande and start <= pos < slut]
                if len(bundna) > 1 and not frozenset.intersection(*bundna):
                    ostodda.append(f"blandade källor i en mening: {text[start:slut].strip()[:120]!r}")

    belagg = [(uppgift, tuple(sorted(ids))) for _, uppgift, ids, _ in hallna]
    if ordagrant:
        # Varje mening är en hälsning, en fråga eller ett citat ur en källa.
        # `citatsvar` bygger sådana svar; här döms texten som faktiskt ska ut.
        for mening, slag, funna, hel in _Citat.ur(namngivna).prov(svar):
            if not hel:
                ostodda.append(f"mening utan ordagrant belägg: {mening[:120]!r}")
            elif slag == "citat":
                belagg.append((f"mening: {mening[:120]!r}", tuple(sorted({k for _, k in funna}))))

    return Faktadom(ok=not ostodda, ostodda=tuple(ostodda), belagg=tuple(belagg))


@dataclass(frozen=True)
class Grindutfall:
    #: Texten som döms. På en nivå som bygger svaret är det den byggda
    #: texten, tom när ingenting höll.
    text: str
    dom: Faktadom
    #: Meningar som ströks när svaret byggdes (bara nivåer som bygger).
    strukna: int = 0


def bygger_svar(niva: str) -> bool:
    """Bygger nivån svaret av källans meningar (citatläget)? Då får inget
    steg efter utkastet skriva om texten."""
    return niva == ORDAGRANT


def grinda(
    svar: str,
    *,
    niva: str,
    kallor: Sequence[str | Kalla],
    tenant_namn: str = "",
    svenska: bool = True,
    kundnamn: str = "",
) -> Grindutfall:
    """Hela nivån i ett anrop: bygger svaret där nivån gör det, och dömer
    sedan exakt den text som ska ut. Ett tomt svar håller aldrig.

    I citatläget är kundens namn (åt hälsningen) och våra egna fasta texter
    en del av det som får stå, och på ett annat språk än svenska finns inget
    att citera."""
    kallor, strukna = list(kallor), 0
    tomt = "svaret är tomt"
    if bygger_svar(niva):
        kallor += [
            Kalla("KUNDNAMN", kundnamn or "", FAST),
            Kalla("FASTTEXT", support_texter.alla("sv"), "fasttext"),
        ]
        svar, strukna = citatsvar(svar, kallor) if svenska else ("", 0)
        tomt = (
            "ingen mening ur kunskapsbasen besvarar frågan"
            if svenska
            else "citatläget gäller bara svenska"
        )
    dom = kontrollera(svar, niva=niva, kallor=kallor, tenant_namn=tenant_namn)
    if not svar:
        dom = replace(dom, ok=False, ostodda=dom.ostodda or (tomt,))
    return Grindutfall(svar, dom, strukna)


def reparationsuppgift(niva: str, ostodda: Sequence[str]) -> str:
    """Uppgiften till reparationsrundan, utan formatraden. Citatläget ber om
    källans meningar; övriga nivåer ber modellen stryka det ostödda."""
    if bygger_svar(niva):
        return (
            "Citatläge. Återge EXAKT, ord för ord, de meningar ur kunskapsbasen "
            "nedan som besvarar kundens fråga, en mening per rad. Lägg inte till "
            "något eget och skriv inte om någon mening. Besvarar ingen mening "
            "frågan: returnera en tom sträng. "
        )
    return (
        "Texten innehåller uppgifter som INTE finns i kunskapsbasen: "
        + "; ".join(ostodda)
        + ". Skriv om texten så att de uppgifterna stryks. Där de behövdes: säg "
        "rakt ut att du inte har den uppgiften. Hitta inte på något nytt och "
        "ändra inget annat. Ren text, ingen markdown. "
    )
