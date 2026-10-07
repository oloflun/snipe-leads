"""Kvittohanteraren — en körning per meddelande, utifrån grundprompten.

## Kedjan

    läs bilagorna (PDF-textlager, bildavskrift)
    → modellen läser meddelandet med grundprompten och researchverktygen
    → kontrolläsning av kärnfälten (andra, oberoende genomgången)
    → koden kontrollerar (granskning.verifiera) och sätter status
    → `spara` skriver ett bk_underlag per underlag, med verifikatförslag
      bara för det som både prompten och verifieringsgrinden släpper igenom

## Research i stället för eskalering

Beställningen 2026-10-06: agenten ska sällan behöva lämna över till en
människa, utan hitta svaren själv. Verktygen (`VERKTYG`) är därför till för
att lösa det som annars blivit en flagga: underlaget som ligger i ett annat
mejl, siffran som gick att läsa vid en andra avskrift, leverantörens förra
bankgiro. Alla är läsande. Inget öppnar en länk, skriver i inkorgen eller
sparar mejlets innehåll.

## Två lägen, samma kontrakt

Utan LLM-nyckel (simuleringsläget, testsviten, demon) bygger
`deterministiskt_resultat` promptens JSON ur regexläsaren i `tolkning.py`.
Kontrollen och lagringen efteråt är desamma — bara läsaren byts.
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from agents import Agent, ModelSettings, RunContextWrapper, Runner, function_tool

from ..agent.bookkeeping_agent import bygg_verifikat
from ..agent.step_runner import RunTrace, StepResult
from ..bookkeeping.kontoplan import OkantKontoError
from ..bookkeeping.kunskap import KUNSKAP, sok_amne
from ..bookkeeping.underlag import (
    UnderlagsfelError,
    las_pdf_text,
    normalisera_momssats,
    sha256_av,
)
from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, STATUS_KLAR, check_underlag
from ..config import get_settings
from . import granskning, kontrollsiffror
from .mejl import Bilaga, Mejl, Mejlkonto
from .systemprompt import Foretagsprofil, anvandarmeddelande, dagens_datum, hamta_profil, rendera
from .tolkning import tolka_deterministiskt

STEG_HANTERING = "snajp:kvittohanterare"
STEG_KONTROLL = "snajp:kvittohanterare-kontrollasning"

#: Tidigare underlag som står i prompten. Resten nås med verktyget.
TIDIGARE_I_PROMPTEN = 40
#: Tak per text som ett verktyg lämnar tillbaka — ett mejl på 200 kB ska inte
#: kunna fylla kontextfönstret.
MAX_TECKEN_PER_TEXT = 6000

_BILDPROMPT_FOKUS = (
    "Det här är ett kvitto eller en faktura. Skriv av texten ordagrant, rad för "
    "rad, med särskild noggrannhet för: {fokus}. Hitta inte på något. Kan en "
    "siffra läsas på två sätt, skriv båda inom hakparentes, till exempel [3/8]. "
    "Kan en rad inte läsas, skriv [oläsligt]. Tolka inte och sammanfatta inte."
)


def anvand_deterministisk() -> bool:
    settings = get_settings()
    if (getattr(settings, "kvitto_tolkning", "") or "").strip().lower() == "deterministisk":
        return True
    return settings.is_simulation()


# -- Indata -------------------------------------------------------------------


@dataclass(frozen=True)
class Inkommande:
    """Ett meddelande att hantera: ett mejl, eller en uppladdad fil."""

    meddelande_id: str
    avsandare: str
    mottagare: str
    datum: str
    amne: str
    text: str
    bilagor: tuple[Bilaga, ...] = ()
    lage: str = "mejl"

    @classmethod
    def fran_mejl(cls, mejl: Mejl) -> Inkommande:
        avsandare = mejl.avsandare
        if mejl.avsandaradress:
            avsandare = f"{mejl.avsandare} <{mejl.avsandaradress}>".strip()
        return cls(
            meddelande_id=mejl.id,
            avsandare=avsandare,
            mottagare=mejl.mottagare,
            datum=mejl.datum,
            amne=mejl.amne,
            text=mejl.text,
            bilagor=mejl.bilagor,
        )

    @classmethod
    def fran_fil(cls, data: bytes, mimetyp: str, filnamn: str) -> Inkommande:
        return cls(
            meddelande_id=f"uppladdning:{sha256_av(data)[:16]}",
            avsandare="",
            mottagare="",
            datum="",
            amne="",
            text="",
            bilagor=(Bilaga(filnamn or "underlag", mimetyp, data),),
            lage="uppladdning",
        )


@dataclass
class LastBilaga:
    etikett: str
    filnamn: str
    mimetyp: str
    text: str
    sha256: str
    data: bytes = field(repr=False)


async def _las_bild(data: bytes, mimetyp: str, prompt: str) -> str:
    from ..agent.llm import get_vision_client

    client = get_vision_client()
    if client is None:
        return ""
    settings = get_settings()
    data_url = f"data:{mimetyp};base64,{base64.b64encode(data).decode()}"
    svar = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    return (svar.choices[0].message.content or "").strip()


async def las_bilagor(bilagor: tuple[Bilaga, ...], *, med_bild: bool) -> list[LastBilaga]:
    """Text ur varje bilaga. En bilaga som inte går att läsa blir kvar med
    tom text — modellen ska veta att den FINNS (och flagga), inte tro att
    meddelandet saknar underlag."""
    from ..bookkeeping.underlag import BILDPROMPT

    lasta: list[LastBilaga] = []
    for nr, bilaga in enumerate(bilagor, start=1):
        text = ""
        if bilaga.mimetyp == "application/pdf":
            try:
                text = las_pdf_text(bilaga.data)
            except UnderlagsfelError:
                text = ""
        elif bilaga.mimetyp.startswith("image/") and med_bild:
            text = await _las_bild(bilaga.data, bilaga.mimetyp, BILDPROMPT)
        lasta.append(
            LastBilaga(
                etikett=f"bilaga_{nr}",
                filnamn=bilaga.filnamn,
                mimetyp=bilaga.mimetyp,
                text=text,
                sha256=sha256_av(bilaga.data),
                data=bilaga.data,
            )
        )
    return lasta


def _kalltext(ink: Inkommande, bilagor: list[LastBilaga]) -> str:
    delar = [
        f"Från: {ink.avsandare}",
        f"Till: {ink.mottagare}",
        f"Ämne: {ink.amne}",
        ink.text,
    ]
    delar += [f"[{b.etikett}] {b.filnamn}\n{b.text}" for b in bilagor]
    return "\n".join(d for d in delar if d)


def _tidigare_text(poster: list[dict[str, Any]]) -> str:
    rader = []
    for p in poster[-TIDIGARE_I_PROMPTEN:]:
        kompakt = {k: v for k, v in p.items() if v not in (None, "")}
        rader.append(json.dumps(kompakt, ensure_ascii=False, default=str))
    return "\n".join(rader)


# -- Researchverktygen ----------------------------------------------------------


@dataclass
class ResearchKontext:
    storage: Any
    tenant_id: str
    konto: Mejlkonto | None
    meddelande_id: str
    bilagor: list[LastBilaga]
    tidigare: list[dict[str, Any]]
    #: Allt researchen läste in. Blir en del av källtexten som kontrollen
    #: prövar värdena mot — ett värde ur ett annat mejl är lika grundat.
    lasta_texter: list[str] = field(default_factory=list)
    anrop: list[str] = field(default_factory=list)


def _kort(text: str) -> str:
    return text if len(text) <= MAX_TECKEN_PER_TEXT else text[:MAX_TECKEN_PER_TEXT] + " […]"


async def _sok_i_inkorgen_impl(ctx: ResearchKontext, fraga: str) -> str:
    ctx.anrop.append(f"sok_i_inkorgen({fraga})")
    if ctx.konto is None:
        return json.dumps({"fel": "Ingen inkorg är kopplad, sökningen går inte att göra."}, ensure_ascii=False)
    fraga = (fraga or "").strip()[:200]
    if not fraga:
        return json.dumps({"fel": "Ange vad du söker efter."}, ensure_ascii=False)
    try:
        traffar = await ctx.konto.sok_mejl(fraga, max_antal=5)
    except Exception as fel:  # noqa: BLE001 — en sökning får aldrig fälla avläsningen
        return json.dumps({"fel": f"Sökningen misslyckades: {type(fel).__name__}"}, ensure_ascii=False)
    svar = []
    for mejl in traffar:
        if mejl.id == ctx.meddelande_id:
            continue
        bilagor = await las_bilagor(mejl.bilagor, med_bild=True)
        post = {
            "id": mejl.id,
            "från": f"{mejl.avsandare} <{mejl.avsandaradress}>",
            "datum": mejl.datum,
            "ämne": mejl.amne,
            "text": _kort(mejl.text),
            "bilagor": [
                {"etikett": b.etikett, "filnamn": b.filnamn, "text": _kort(b.text)} for b in bilagor
            ],
        }
        ctx.lasta_texter.append(
            "\n".join(
                [f"[mejl:{mejl.id}] Från: {post['från']}", f"Ämne: {mejl.amne}", mejl.text]
                + [f"[mejl:{mejl.id}, {b.etikett}] {b.filnamn}\n{b.text}" for b in bilagor]
            )
        )
        svar.append(post)
    return json.dumps({"fraga": fraga, "traffar": svar}, ensure_ascii=False)


async def _las_bilaga_igen_impl(ctx: ResearchKontext, bilaga: str, fokus: str) -> str:
    ctx.anrop.append(f"las_bilaga_igen({bilaga})")
    traff = next((b for b in ctx.bilagor if b.etikett == (bilaga or "").strip()), None)
    if traff is None:
        return json.dumps(
            {"fel": f"Okänd bilaga. Finns: {', '.join(b.etikett for b in ctx.bilagor) or 'inga'}."},
            ensure_ascii=False,
        )
    if not traff.mimetyp.startswith("image/"):
        return json.dumps(
            {"bilaga": traff.etikett, "text": _kort(traff.text), "not": "PDF:ens textlager är exakt, en ny läsning ger samma text."},
            ensure_ascii=False,
        )
    if anvand_deterministisk():
        return json.dumps({"fel": "Bildläsning är inte tillgänglig i den här miljön."}, ensure_ascii=False)
    text = await _las_bild(
        traff.data, traff.mimetyp, _BILDPROMPT_FOKUS.format(fokus=(fokus or "alla belopp och nummer")[:200])
    )
    ctx.lasta_texter.append(f"[{traff.etikett}, ny avskrift] {traff.filnamn}\n{text}")
    return json.dumps({"bilaga": traff.etikett, "ny_avskrift": _kort(text)}, ensure_ascii=False)


def _sok_tidigare_impl(
    ctx: ResearchKontext, leverantor: str, dokumentnummer: str, totalbelopp: str
) -> str:
    ctx.anrop.append(f"sok_tidigare_underlag({leverantor}, {dokumentnummer}, {totalbelopp})")
    namn = granskning._normaliserat_namn(leverantor)
    nummer = granskning._kompakt(dokumentnummer)
    belopp = granskning.tolka_belopp(totalbelopp) if totalbelopp else None
    traffar = []
    for post in ctx.tidigare:
        if namn and namn not in granskning._normaliserat_namn(post.get("leverantör_namn")):
            continue
        if nummer and nummer != granskning._kompakt(str(post.get("dokumentnummer") or "")):
            continue
        if belopp is not None and granskning.tolka_belopp(post.get("totalbelopp")) != belopp:
            continue
        traffar.append({k: v for k, v in post.items() if v not in (None, "")})
    return json.dumps(
        {"antal": len(traffar), "underlag": traffar[-20:]}, ensure_ascii=False, default=str
    )


def _kontrollrakna_impl(
    totalbelopp: str, belopp_exkl_moms: str, momsbelopp: str, momssats: str, radbelopp: list[str]
) -> str:
    total = granskning.tolka_belopp(totalbelopp) if totalbelopp else None
    netto = granskning.tolka_belopp(belopp_exkl_moms) if belopp_exkl_moms else None
    moms = granskning.tolka_belopp(momsbelopp) if momsbelopp else None
    sats = granskning.tolka_belopp(momssats) if momssats else None
    rader = [granskning.tolka_belopp(r) for r in radbelopp or []]
    svar: dict[str, Any] = {}
    if total is not None and netto is not None and moms is not None:
        diff = netto + moms - total
        svar["netto_plus_moms_lika_total"] = abs(diff) <= Decimal(1)
        svar["differens_netto_plus_moms_mot_total"] = f"{diff:.2f}"
    if total is not None and rader and all(r is not None for r in rader):
        summa = sum(rader, Decimal(0))
        svar["radsumma"] = f"{summa:.2f}"
        svar["rader_lika_total"] = abs(summa - total) <= Decimal(1) or (
            netto is not None and abs(summa - netto) <= Decimal(1)
        )
    if sats is not None and netto is not None and moms is not None:
        beraknad = netto * sats / Decimal(100)
        svar["moms_enligt_sats"] = f"{beraknad:.2f}"
        svar["moms_lika_sats"] = abs(beraknad - moms) <= Decimal(1)
    if not svar:
        svar["fel"] = "För få värden för någon kontroll. Kontroller som inte går att göra sätts till null."
    return json.dumps(svar, ensure_ascii=False)


def _sla_upp_kunskap_impl(amne: str) -> str:
    traff = sok_amne(amne)
    if traff is None:
        return json.dumps({"hittades": False, "kanda_amnen": sorted(KUNSKAP)}, ensure_ascii=False)
    return json.dumps({"amne": traff.id, "rubrik": traff.rubrik, "text": traff.text}, ensure_ascii=False)


@function_tool
async def sok_i_inkorgen(ctx: RunContextWrapper[ResearchKontext], fraga: str) -> str:
    """Sök i samma inkorg efter mejl som hör till underlaget: fakturan som
    PDF i ett separat mejl, originalet till en påminnelse, kvittot till en
    orderbekräftelse. Läser bara, öppnar aldrig länkar.

    Args:
        fraga: Sökord, till exempel leverantörens namn, ett fakturanummer
            eller ett ordernummer.
    """
    return await _sok_i_inkorgen_impl(ctx.context, fraga)


@function_tool
async def las_bilaga_igen(ctx: RunContextWrapper[ResearchKontext], bilaga: str, fokus: str) -> str:
    """Be om en ny ordagrann avskrift av en bildbilaga, med fokus på det som
    var svårläst.

    Args:
        bilaga: Bilagans etikett, till exempel "bilaga_1".
        fokus: Vad avskriften ska vara extra noggrann med, till exempel
            "momsraden" eller "bankgironumret".
    """
    return await _las_bilaga_igen_impl(ctx.context, bilaga, fokus)


@function_tool
async def sok_tidigare_underlag(
    ctx: RunContextWrapper[ResearchKontext],
    leverantor: str = "",
    dokumentnummer: str = "",
    totalbelopp: str = "",
) -> str:
    """Sök bland företagets redan inlästa underlag: dubbletter, originalet
    till en påminnelse eller kreditfaktura, och leverantörens tidigare
    betalningsuppgifter och kategori.

    Args:
        leverantor: Leverantörens namn (del av namnet räcker).
        dokumentnummer: Faktura-, kvitto- eller ordernummer.
        totalbelopp: Totalbeloppet, till exempel "1250.00".
    """
    return _sok_tidigare_impl(ctx.context, leverantor, dokumentnummer, totalbelopp)


@function_tool
async def kontrollera_nummer(ctx: RunContextWrapper[ResearchKontext], typ: str, nummer: str) -> str:
    """Pröva kontrollsiffran i ett nummer. Bekräftar en läsning, väljer
    aldrig mellan två.

    Args:
        typ: "orgnummer", "bankgiro", "plusgiro", "ocr", "iban" eller "momsregnummer".
        nummer: Numret som det står på underlaget.
    """
    ctx.context.anrop.append(f"kontrollera_nummer({typ})")
    return json.dumps(
        {"typ": typ, "nummer": nummer, "giltig": kontrollsiffror.kontrollera(typ, nummer)},
        ensure_ascii=False,
    )


@function_tool
async def kontrollrakna(
    ctx: RunContextWrapper[ResearchKontext],
    totalbelopp: str = "",
    belopp_exkl_moms: str = "",
    momsbelopp: str = "",
    momssats: str = "",
    radbelopp: list[str] | None = None,
) -> str:
    """Gör kontrollräkningarna i avsnitt 3.3 exakt (tolerans ±1 kr).

    Args:
        totalbelopp: Totalbeloppet inklusive moms.
        belopp_exkl_moms: Nettobeloppet.
        momsbelopp: Momsbeloppet.
        momssats: Momssatsen i procent, till exempel "25".
        radbelopp: Radernas belopp, om rader finns.
    """
    ctx.context.anrop.append("kontrollrakna")
    return _kontrollrakna_impl(totalbelopp, belopp_exkl_moms, momsbelopp, momssats, radbelopp or [])


@function_tool
async def sla_upp_kunskap(ctx: RunContextWrapper[ResearchKontext], amne: str) -> str:
    """Snajps text om momssatser, omvänd skattskyldighet, EU-handel, import,
    fakturakrav med mera. För att klassa och flagga rätt, aldrig för att
    fylla i ett värde.

    Args:
        amne: Ämnet, till exempel "omvänd skattskyldighet" eller "eu-handel".
    """
    ctx.context.anrop.append(f"sla_upp_kunskap({amne})")
    return _sla_upp_kunskap_impl(amne)


VERKTYG = [
    sok_i_inkorgen,
    las_bilaga_igen,
    sok_tidigare_underlag,
    kontrollera_nummer,
    kontrollrakna,
    sla_upp_kunskap,
]


# -- Modellvägen ----------------------------------------------------------------


def las_json(text: str) -> dict[str, Any] | None:
    """Första JSON-objektet i ett svar, med eller utan ```json-staket."""
    if not text:
        return None
    rensad = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    for kandidat in (rensad, rensad[rensad.find("{") : rensad.rfind("}") + 1]):
        try:
            data = json.loads(kandidat)
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def _anvandning(result: Any) -> tuple[int, int]:
    try:
        usage = result.context_wrapper.usage
        return int(usage.input_tokens or 0), int(usage.output_tokens or 0)
    except AttributeError:
        return 0, 0


async def _kor_modellen(
    system: str, anvandare: str, ctx: ResearchKontext, trace: RunTrace
) -> dict[str, Any] | None:
    from ..agent.llm import get_agent_model

    agent = Agent[ResearchKontext](
        name="Snajp-Kvittohanterare",
        instructions=system,
        model=get_agent_model(),
        tools=VERKTYG,
        model_settings=ModelSettings(temperature=0),
    )
    start = time.monotonic()
    meddelanden: list[Any] = [{"role": "user", "content": anvandare}]
    result = await Runner.run(agent, meddelanden, context=ctx, max_turns=12)
    rat = las_json(str(result.final_output or ""))
    forsok = 1
    if rat is None:
        # Ett omförsök med hela historiken, som step_runner gör vid brutet
        # kontrakt. Två misslyckanden ger den deterministiska läsningen.
        forsok = 2
        historik = result.to_input_list()
        historik.append(
            {
                "role": "user",
                "content": "Ditt svar gick inte att läsa som JSON. Svara ENDAST med JSON-objektet enligt avsnitt 12.",
            }
        )
        result = await Runner.run(agent, historik, context=ctx, max_turns=4)
        rat = las_json(str(result.final_output or ""))
    tokens_in, tokens_out = _anvandning(result)
    trace.steps.append(
        StepResult(
            skill=STEG_HANTERING,
            output=rat or {},
            attempts=forsok,
            escalated=rat is None,
            escalation_reason=None if rat is not None else "svaret gick inte att läsa som JSON",
            latency_ms=int((time.monotonic() - start) * 1000),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            injected_chars=len(system),
            system_prompt=system,
            user_message=anvandare,
        )
    )
    return rat


async def _kontrollas(system: str, anvandare: str, trace: RunTrace) -> dict[str, Any] | None:
    """Den andra, oberoende genomgången (produktkrav 2026-09-14). Ett anrop i
    JSON-läge, utan verktyg, bara kärnfälten."""
    from ..agent.llm import get_llm_client

    settings = get_settings()
    start = time.monotonic()
    svar = await get_llm_client().chat.completions.create(
        model=settings.model,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": anvandare}],
    )
    usage = getattr(svar, "usage", None)
    rat = las_json(svar.choices[0].message.content or "")
    trace.steps.append(
        StepResult(
            skill=STEG_KONTROLL,
            output=rat or {},
            attempts=1,
            escalated=False,
            escalation_reason=None,
            model=settings.model,
            latency_ms=int((time.monotonic() - start) * 1000),
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0 if usage else 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0 if usage else 0,
            injected_chars=len(system),
        )
    )
    return rat


_KARNFALT = (
    "leverantör_namn",
    "dokumentnummer",
    "dokumentdatum",
    "förfallodatum",
    "valuta",
    "totalbelopp",
    "belopp_exkl_moms",
    "momsbelopp_totalt",
    "bankgiro",
    "plusgiro",
    "iban",
    "ocr_referens",
)


def jamfor_kontrollasning(resultat: dict[str, Any], kontroll: dict[str, Any] | None) -> None:
    """Sammanför de två genomgångarna. Luckor fylls med kontrolläsningens
    värde (koden prövar sedan att det står i texten); där de läste OLIKA
    blir fältet `osäker` och båda läsningarna står i noteringen."""
    if not kontroll:
        return
    andra = granskning._hamta(kontroll, "underlag", []) or []
    noter: list[str] = []
    for u, k in zip(resultat["underlag"], andra):
        if not isinstance(k, dict):
            continue
        for namn in _KARNFALT:
            post = u["fält"][namn]
            ratt = granskning._hamta(k, namn)
            if isinstance(ratt, dict):
                ratt = granskning._hamta(ratt, "värde")
            andra_post = granskning._normalisera_falt(namn, {"värde": ratt, "säkerhet": "säker"}, set())
            v2 = andra_post["värde"]
            if v2 is None:
                continue
            v1 = post["värde"]
            if v1 is None:
                u["fält"][namn] = {"värde": v2, "säkerhet": "säker", "källa": "kontrolläsningen"}
                continue
            lika = (
                v1 == v2
                if namn in granskning.BELOPPSFALT or namn in granskning.DATUMFALT
                else granskning._kompakt(str(v1)) == granskning._kompakt(str(v2))
                or granskning._normaliserat_namn(str(v1)) == granskning._normaliserat_namn(str(v2))
            )
            if not lika:
                post["säkerhet"] = "osäker"
                noter.append(f"Dubbelläsningen gav olika {namn}: {v1} respektive {v2}.")
    if noter:
        resultat["intern_notering"] = " ".join(
            x for x in (resultat["intern_notering"], *noter) if x
        ).strip()


# -- Den deterministiska läsaren -----------------------------------------------

_MOMSBELOPP = re.compile(
    r"(?i)moms[^\n\d]{0,12}(25|12|6|0)\s*%\s*[:=]?\s*"
    r"(\d{1,3}(?:[  .,]\d{3})*(?:[.,]\d{1,2})?)"
)
_DOKUMENTNUMMER = re.compile(
    r"(?i)(?:kvitto|order|faktura|invoice|receipt)\w*\s*(?:nr|nummer|no\.?|number)?\s*[:#]?\s*#?\s*"
    r"([A-Z]{0,4}-?\d[\dA-Z-]{2,})"
)
_FORFALLO = re.compile(r"(?i)(?:förfallodatum|förfaller|att betala senast|due date)\D{0,5}(20\d{2}-\d{2}-\d{2})")
_BANKGIRO = re.compile(r"(?i)\bbankgiro\b\D{0,5}(\d{3,4}-\d{4})")
_PLUSGIRO = re.compile(r"(?i)\bplusgiro\b\D{0,5}(\d{1,7}-\d)")
_OCR = re.compile(r"(?i)\bocr\b\D{0,10}(\d{2,25})")
_LANK = re.compile(r"(?i)(logga in|log in|ladda (ned|ner)|download|finns tillgänglig|is available|visa fakturan)")
_KRONOR = re.compile(r"(?i)\b(kr|sek|kronor)\b|:-")


def deterministiskt_resultat(ink: Inkommande, bilagor: list[LastBilaga]) -> dict[str, Any]:
    """Promptens JSON ur regexläsaren. Samma regel som modellen: det som
    inte hittas blir null, och kontrollen efteråt flaggar det."""
    brodtext = "\n".join([ink.amne, ink.text, *(b.text for b in bilagor)])
    namn = re.sub(r"\s*<[^>]*>\s*$", "", ink.avsandare or "").strip()
    avlast = tolka_deterministiskt("\n".join([ink.text, *(b.text for b in bilagor)]), avsandare=namn)
    falt = avlast.falt
    kalla = bilagor[0].etikett if bilagor and bilagor[0].text else "e-posttext"

    def post(varde: Any, kalla_: str | None = kalla) -> dict[str, Any]:
        return {"värde": varde, "säkerhet": "säker", "källa": kalla_ if varde is not None else None}

    total: str | None = None
    valuta: str | None = None
    if falt.get("brutto"):
        total = str(falt["brutto"])
        valuta = "SEK" if _KRONOR.search(brodtext) else None
    elif avlast.belopp_original:
        total, valuta = avlast.belopp_original.split(" ", 1)

    moms_per_sats = []
    momsbelopp = None
    if (traff := _MOMSBELOPP.search(brodtext)) and valuta == "SEK":
        momsbelopp = traff.group(2)
        moms_per_sats.append({"sats": int(traff.group(1)), "underlag": None, "moms": momsbelopp})

    betalstatus = falt.get("betalstatus")
    if total is None and _LANK.search(brodtext) and not bilagor:
        klass = "UNDERLAG_ENDAST_LÄNK"
    else:
        klass = "UNDERLAG_BILAGA" if bilagor and any(b.text for b in bilagor) else "UNDERLAG_I_TEXT"
    dokumenttyp = {"betald": "kvitto", "obetald": "leverantörsfaktura"}.get(betalstatus or "", "okänd")

    nummer = _DOKUMENTNUMMER.search(brodtext)
    forfallo = _FORFALLO.search(brodtext)
    bankgiro = _BANKGIRO.search(brodtext)
    plusgiro = _PLUSGIRO.search(brodtext)
    ocr = _OCR.search(brodtext)
    falten = {
        "leverantör_namn": post(falt.get("motpart"), "e-post: avsändare" if namn else kalla),
        "dokumentnummer": post(nummer.group(1) if nummer else None),
        "dokumentdatum": post(falt.get("datum")),
        "förfallodatum": post(forfallo.group(1) if forfallo else None),
        "valuta": post(valuta),
        "totalbelopp": post(total),
        "momsbelopp_totalt": post(momsbelopp),
        "betalstatus": post(betalstatus),
        "bankgiro": post(bankgiro.group(1) if bankgiro else None),
        "plusgiro": post(plusgiro.group(1) if plusgiro else None),
        "ocr_referens": post(ocr.group(1) if ocr else None),
    }
    return {
        "meddelande_id": ink.meddelande_id,
        "klass": klass,
        "underlag": [
            {
                "dokumenttyp": dokumenttyp,
                "fält": falten,
                "moms_per_sats": moms_per_sats,
                "rader": None,
                "kategori": falt.get("kategori"),
                "kategori_är_förslag": True,
                "flaggor": [],
                "källfiler": [b.etikett for b in bilagor],
            }
        ],
        "intern_notering": avlast.anmarkning,
    }


# -- Huvudingången ----------------------------------------------------------------


@dataclass
class Hantering:
    resultat: dict[str, Any]
    bilagor: list[LastBilaga]
    trace: RunTrace
    verktygsanrop: list[str]
    deterministisk: bool


async def hantera(
    storage: Any,
    tenant_id: str,
    ink: Inkommande,
    *,
    konto: Mejlkonto | None = None,
    profil: Foretagsprofil | None = None,
    nu: datetime | None = None,
    riktning: str | None = None,
) -> Hantering:
    """Hela avläsningen av ett meddelande, utan att spara något.

    `riktning="intakt"` är människans besked vid uppladdning ("det här är en
    kundfaktura") och vinner över igenkänningen i granskningen.
    """
    profil = profil or await hamta_profil(storage, tenant_id)
    deterministisk = anvand_deterministisk()
    bilagor = await las_bilagor(ink.bilagor, med_bild=True)

    rader = await storage.list_bk_underlag(tenant_id, limit=100_000)
    tidigare = [granskning.tidigare_post(r) for r in rader]
    trace = RunTrace()
    ctx = ResearchKontext(
        storage=storage,
        tenant_id=tenant_id,
        konto=konto,
        meddelande_id=ink.meddelande_id,
        bilagor=bilagor,
        tidigare=tidigare,
    )

    rat: dict[str, Any] | None = None
    kontroll: dict[str, Any] | None = None
    if not deterministisk:
        system = rendera(profil, meddelande_id=ink.meddelande_id, lage=ink.lage, nu=nu)
        anvandare = anvandarmeddelande(
            avsandare=ink.avsandare,
            mottagare=ink.mottagare,
            datum=ink.datum,
            amne=ink.amne,
            text=ink.text,
            bilagor=[(b.etikett, b.filnamn, b.text) for b in bilagor],
            tidigare=_tidigare_text(tidigare),
        )
        rat = await _kor_modellen(system, anvandare, ctx, trace)
        if rat is not None and rat.get("underlag"):
            extra = "\n\n".join(ctx.lasta_texter)
            kontroll = await _kontrollas(
                rendera(profil, meddelande_id=ink.meddelande_id, lage="kontroll", nu=nu),
                anvandare + (f"\n\n<funnet_vid_research>\n{extra}\n</funnet_vid_research>" if extra else ""),
                trace,
            )

    if rat is None:
        rat = deterministiskt_resultat(ink, bilagor)
        if not deterministisk:
            for u in rat["underlag"]:
                u["flaggor"].append("osäker_klassning")
            rat["intern_notering"] = " ".join(
                x for x in (rat["intern_notering"], "Modellens avläsning gick inte att använda, fälten är lästa maskinellt.") if x
            )

    resultat = granskning.normalisera_resultat(rat, ink.meddelande_id)
    jamfor_kontrollasning(resultat, kontroll)
    kalltext = "\n\n".join([_kalltext(ink, bilagor), *ctx.lasta_texter])
    granskning.verifiera(
        resultat,
        kalltext=kalltext,
        idag=dagens_datum(nu),
        dagar_varning=profil.dagar_forfallo_varning,
        foretag_orgnr=profil.orgnummer,
        # "företaget" är profilens platshållare när tenanten saknar namn.
        foretag_namn="" if profil.foretagsnamn == "företaget" else profil.foretagsnamn,
        tidigare=tidigare,
    )
    if riktning == "intakt":
        for u in resultat["underlag"]:
            if u["riktning"] != "intakt":
                granskning.markera_som_intakt(u)
                u["status"] = granskning.berakna_status(u, resultat["klass"])

    # Samma FIL som redan finns hos tenanten (uppladdad, eller bifogad i ett
    # annat mejl) är en möjlig dubblett oavsett vad fälten säger.
    for u in resultat["underlag"]:
        for b in bilagor:
            if u["källfiler"] and b.etikett not in u["källfiler"]:
                continue
            redan = await storage.get_bk_underlag_by_sha256(tenant_id, b.sha256)
            if redan is not None and not u["möjlig_dubblett_av"]:
                u["möjlig_dubblett_av"] = str(redan.get("id"))
                u["flaggor"].add("möjlig_dubblett")
                u["status"] = granskning.berakna_status(u, resultat["klass"])
                resultat["intern_notering"] = " ".join(
                    x
                    for x in (
                        resultat["intern_notering"],
                        granskning.dubblettnot(granskning.tidigare_post(redan)),
                    )
                    if x
                )
    return Hantering(resultat, bilagor, trace, ctx.anrop, deterministisk)


# -- Lagringen ----------------------------------------------------------------------


def _valutanot(valuta: str | None, total: Decimal) -> str:
    if valuta is None:
        return (
            f"Valutan framgår inte av underlaget ({total:.2f}), beloppet räknas inte "
            "förrän du angett det i kronor"
        )
    return (
        f"Beloppet är i {valuta} ({total:.2f}) och har inte räknats om "
        "till kronor, granska och för in det omräknade beloppet"
    )


@dataclass
class Sparat:
    rad: dict[str, Any]
    status: str
    granskningsstatus: str
    brister: list[str]


async def spara(
    storage: Any,
    tenant_id: str,
    u: dict[str, Any],
    resultat: dict[str, Any],
    *,
    sha256: str,
    filnamn: str,
    mimetyp: str,
    kalla: str,
    mejl_id: str | None = None,
    mejl_amne: str | None = None,
    mejl_avsandare: str | None = None,
    reservdatum: str = "",
) -> Sparat:
    """Ett underlag till en bk_underlag-rad, med verifikatförslag när BÅDE
    promptens status (KLAR_FÖR_GRANSKNING) och verifieringsgrinden säger ja.

    De platta kolumnerna är det summorna och SIE-exporten räknar på. De får
    bara värden som står i underlaget — ett belopp i okänd eller utländsk
    valuta hamnar i belopp_original, aldrig i brutto.
    """
    f = u["fält"]
    intakt = u.get("riktning") == "intakt"
    falt: dict[str, Any] = {"riktning": "intakt" if intakt else "kostnad"}
    anm: list[str] = []
    if f["dokumentdatum"]["värde"]:
        falt["datum"] = date.fromisoformat(f["dokumentdatum"]["värde"])
    elif reservdatum:
        # Utan datum syns raden inte i någon period. Mejlets mottagningsdag
        # står i den platta kolumnen MED anmärkning; granskningen säger
        # fortfarande att dokumentdatumet saknas.
        try:
            falt["datum"] = date.fromisoformat(reservdatum)
            anm.append("Datumet är mejlets mottagningsdag")
        except ValueError:
            pass
    # Motparten är den ANDRA parten: leverantören på ett kvitto, kunden
    # (köparen) på företagets egen faktura. Saknas kunden står fältet tomt och
    # grinden skickar raden till granskning — hellre än företagets eget namn.
    motpart = f["köpare_namn"]["värde"] if intakt else f["leverantör_namn"]["värde"]
    if motpart:
        falt["motpart"] = motpart
    elif intakt:
        anm.append("Kunden framgår inte av fakturan, ange den vid godkännandet")

    valuta = f["valuta"]["värde"]
    total = f["totalbelopp"]["värde"]
    belopp_original = None
    if total is not None:
        if valuta == "SEK":
            falt["brutto"] = total
        else:
            belopp_original = f"{total:.2f} {valuta or ''}".strip()
            anm.append(_valutanot(valuta, total))

    satser = {p["sats"] for p in u["moms_per_sats"]}
    if len(satser) == 1:
        sats = normalisera_momssats(str(next(iter(satser))))
        if sats is not None:
            falt["momssats"] = sats
    elif len(satser) > 1:
        anm.append(
            "Underlaget har flera momssatser ("
            + ", ".join(f"{s:g} %" for s in sorted(satser))
            + "), konteringen behöver delas upp för hand"
        )
    betalstatus = f["betalstatus"]["värde"]
    if betalstatus in ("betald", "obetald"):
        falt["betalstatus"] = betalstatus
    if u["kategori"] and not intakt:
        falt["kategori"] = u["kategori"]

    verdikt = check_underlag(falt)
    status = (
        STATUS_KLAR
        if u["status"] == granskning.KLAR and verdikt.ok and valuta == "SEK" and total is not None
        else STATUS_GRANSKA
    )
    verifikatrader: tuple = ()
    if status == STATUS_KLAR:
        try:
            verifikatrader = tuple(bygg_verifikat(falt))
        except OkantKontoError:
            status = STATUS_GRANSKA
            anm.append(f"Kategorin {falt.get('kategori')!r} finns inte i kontoplanen, välj en annan")

    brister = verdikt.as_report()
    if belopp_original is not None or total is None:
        brister = [b for b in brister if "brutto" not in b and "momssats" not in b]
    if len(satser) > 1:
        brister = [b for b in brister if "momssats" not in b]
    anmarkning = "; ".join(
        dict.fromkeys(a.strip() for a in (resultat["intern_notering"], *anm, *brister) if a and a.strip())
    )

    rad = await storage.create_bk_underlag(
        tenant_id,
        sha256=sha256,
        filnamn=filnamn,
        mimetyp=mimetyp,
        status=status,
        anmarkning=anmarkning,
        kalla=kalla,
        mejl_id=mejl_id,
        mejl_amne=mejl_amne,
        mejl_avsandare=mejl_avsandare,
        valuta="SEK" if valuta is None else valuta,
        belopp_original=belopp_original,
        granskning=granskning.underlag_som_json(
            u,
            klass=resultat["klass"],
            meddelande_id=resultat["meddelande_id"],
            intern_notering=resultat["intern_notering"],
        ),
        granskningsstatus=u["status"],
        **{
            k: v
            for k, v in falt.items()
            if k in ("datum", "motpart", "brutto", "momssats", "riktning", "kategori", "betalstatus")
        },
    )
    if verifikatrader:
        # nummer=None: nästa lediga i serien sätts av lagringen (snipe-a4y).
        await storage.create_bk_verifikat(
            tenant_id,
            underlag_id=rad["id"],
            serie="A",
            nummer=None,
            datum=falt["datum"],
            text=falt.get("motpart", ""),
            rader=[
                {"konto": r.konto, "debet": r.debet, "kredit": r.kredit, "text": r.text}
                for r in verifikatrader
            ],
        )
    return Sparat(rad, status, u["status"], brister)
