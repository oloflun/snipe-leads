"""Den gemensamma spärren: en invändning gäller i varje kanal (migration 166).

Antons beslut 2026-11-27 (docs/crm/SVENSK-STANDARD.md § 4). Rätten att invända
mot direktmarknadsföring (GDPR art. 21.2-3) är ovillkorlig och gäller i alla
system. IMY bötfällde H&M 2023 när invändningar inte nådde alla system
(docs/crm/underlag/svensk-02 § 3.2 och § 6.3).

## Fyra källor, en grind

Före migration 166 fanns tre spärrar som inte kände till varandra. Nu finns
fyra, och `ar_sparrad` läser dem tillsammans:

1. **spärrlistan** (`crm_sparrar`): kanal (mejl, telefon, alla), slag (e-post,
   telefon, domän, organisationsnummer), orsak och datum. Den enda som bär
   orsak och kanal, och den enda som tar NIX-tvättens utfall.
2. **posten** (`kontakta_inte` på CRM:ets bolag och personer). Dit hör varje
   privatperson (migration 161), och personerna hos ett märkt bolag.
3. **avregistreringarna** (`suppressions`), bara för mejl.
4. **leadet** med status `suppressed` (ringlistans och svarens kontakta inte),
   på samma adress eller samma organisationsnummer.

Ingenting kopieras mellan dem: grinden är en sammansatt läsning. Kontakta inte
som sätts på en post genom API:t står på posten och läses därifrån. Utfallet
kontakta inte på ett bolag (`utfall.registrera`) lägger däremot spärrar på
bolagets adress, nummer och organisationsnummer, så att spärren står kvar med
orsak och datum också om posten ändras eller raderas.

Svaret säger VILKEN källa som spärrade, aldrig adressen eller numret.

## Där spärren verkställs

- Sändspärren (`app/leads/scheduler.py`) läser `lagring.kontakta_inte_adresser`,
  som sedan 166 också bär spärrlistans adresser, och prövar domänspärrarna för
  sig. Kampanjutskick och uppföljningar går samma väg.
- Ringlistan och återkopplingen (`app/leads/samtal.py: samtalslista`) tappar
  nummer och organisationsnummer som är spärrade för telefon.

## Vad som aldrig skrivs

Anteckningen skrivs aldrig i en logg, en händelse eller en webhook. Händelserna
`sparr.skapad` och `sparr.havd` bär id, kanal, slag, orsak och källa, aldrig
värdet: mottagaren hämtar spärren med sin nyckel om den behöver adressen.
"""

from __future__ import annotations

from typing import Any

from . import falt, handelser, lagring

KANALER = ("mejl", "telefon", "alla")
SLAG = ("epost", "telefon", "doman", "orgnr")
ORSAKER = ("invandning", "avregistrering", "nix", "kunden_bad", "studs", "annat")
KALLOR = ("app", "api", "utfall", "import", "synk")
#: Källorna grinden kan svara med.
GRINDKALLOR = ("sparrlistan", "posten", "avregistrerad", "lead")

MAX_ANTECKNING = 500
MAX_IMPORT = 10_000

#: Vilka slag som hör hemma i en kanal. Ett telefonnummer kan inte spärra mejl,
#: en adress kan inte spärra telefon. Organisationsnumret gäller bolaget i alla kanaler.
_SLAG_I_KANAL = {"mejl": {"epost", "doman", "orgnr"}, "telefon": {"telefon", "orgnr"}, "alla": set(SLAG)}

_TABELL = "crm_sparrar"


class OgiltigSparr(ValueError):
    """Ett värde eller en kombination som inte går att spärra. `falt` och
    `kod` är stabila; värdet självt följer aldrig med."""

    def __init__(self, falt_: str, kod: str) -> None:
        super().__init__(kod)
        self.falt = falt_
        self.kod = kod


# -- Normaliseringen ---------------------------------------------------------


def normalisera(slag: str, varde: Any) -> str:
    """Värdet så som det lagras: e-post och domän i gemener, telefon i E.164,
    organisationsnummer som tio siffror. En enskild firmas nummer är ett
    personnummer och tas inte emot (beslut 2026-11-23)."""
    if slag not in SLAG:
        raise OgiltigSparr("kind", "slag_okant")
    ra = falt.text(varde, max_langd=320)
    if not ra:
        raise OgiltigSparr("value", "varde_saknas")
    try:
        if slag == "epost":
            return falt.epost(ra) or ""
        if slag == "telefon":
            return falt.telefon(ra) or ""
        if slag == "doman":
            _, doman = falt.webbplats(ra.lstrip("@"))
            if not doman or "@" in doman:
                raise falt.FaltFel("doman_ogiltig")
            return doman
        _, nyckel, enskild = falt.orgnr(ra)
    except falt.FaltFel as fel:
        kod = "doman_ogiltig" if fel.kod == "webbplats_ogiltig" else fel.kod
        raise OgiltigSparr("value", kod) from None
    if enskild or not nyckel:
        raise OgiltigSparr("value", "orgnr_ar_personnummer")
    return nyckel


def gissa_slag(kanal: str, varde: Any) -> str:
    """Slaget när en import inte anger det: en adress med @ är e-post, utan @
    är den en domän i mejlkanalen och ett telefonnummer annars."""
    text = str(varde or "")
    if "@" in text and not text.startswith("@"):
        return "epost"
    if kanal == "mejl":
        return "doman"
    return "telefon"


def _kontrollera(kanal: str, slag: str | None, orsak: str, kalla: str) -> None:
    if kanal not in KANALER:
        raise OgiltigSparr("channel", "kanal_okand")
    if orsak not in ORSAKER:
        raise OgiltigSparr("reason", "orsak_okand")
    if kalla not in KALLOR:
        raise OgiltigSparr("source", "kalla_okand")
    if slag is not None and slag not in SLAG:
        raise OgiltigSparr("kind", "slag_okant")
    if slag is not None and slag not in _SLAG_I_KANAL[kanal]:
        raise OgiltigSparr("kind", "slag_passar_inte_kanalen")


# -- Läsa ----------------------------------------------------------------------


async def hamta(storage: Any, tenant_id: str, sparr_id: str) -> dict[str, Any] | None:
    return await lagring._hamta(storage, tenant_id, _TABELL, sparr_id)


async def _gallande(storage: Any, tenant_id: str, kanal: str, slag: str, varde: str) -> dict[str, Any] | None:
    rader = await lagring._valj(storage, tenant_id, _TABELL,
                                lika={"kanal": kanal, "slag": slag, "varde": varde, "havd_at": None}, limit=1)
    return rader[0] if rader else None


async def lista(
    storage: Any, tenant_id: str, *, limit: int = 50, markor: str | None = None, kanal: str | None = None,
    orsak: str | None = None, q: str | None = None, med_havda: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    """En sida spärrar, senast lagd först, och markören till nästa sida."""
    limit = max(1, min(int(limit), 500))
    efter = lagring.las_markor(markor)
    sok = (q or "").strip().lower() or None
    if lagring._ar_postgres(storage):
        villkor, varden = ["tenant_id = $1::text::uuid"], [tenant_id]
        for kol, varde in (("kanal", kanal), ("orsak", orsak)):
            if varde:
                varden.append(varde)
                villkor.append(f"{kol} = ${len(varden)}")
        if not med_havda:
            villkor.append("havd_at is null")
        if sok:
            varden.append(f"%{sok}%")
            villkor.append(f"varde ilike ${len(varden)}")
        if efter:
            varden.extend(efter)
            villkor.append(f"(created_at, id) < (${len(varden) - 1}::text::timestamptz, ${len(varden)}::text::uuid)")
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select * from {_TABELL} where {' and '.join(villkor)} "
                    f"order by created_at desc, id desc limit {limit + 1}", *varden)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return [], None
            raise
        sparrar = [lagring._rad(r, _TABELL) for r in rader]
    else:
        sparrar = [dict(r) for r in lagring._minne(storage, _TABELL).values()
                   if r["tenant_id"] == tenant_id
                   and (not kanal or r["kanal"] == kanal) and (not orsak or r["orsak"] == orsak)
                   and (med_havda or not r.get("havd_at")) and (not sok or sok in r["varde"].lower())
                   and (not efter or (r["created_at"], r["id"]) < efter)]
        sparrar.sort(key=lambda r: (r["created_at"], r["id"]), reverse=True)
        sparrar = sparrar[: limit + 1]
    if len(sparrar) <= limit:
        return sparrar, None
    sparrar = sparrar[:limit]
    return sparrar, lagring._markor(sparrar[-1]["created_at"], sparrar[-1]["id"])


# -- Skriva --------------------------------------------------------------------


async def lagg_till(
    storage: Any, tenant_id: str, *, kanal: str, slag: str, varde: Any, orsak: str, kalla: str,
    anteckning: str | None = None, bolag_id: str | None = None, person_id: str | None = None,
    via: str = "system", aktor: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """(spärren, skapad). En spärr som redan gäller för samma kanal, slag och
    värde lämnas som den är och kommer tillbaka med `skapad = False`."""
    _kontrollera(kanal, slag, orsak, kalla)
    normal = normalisera(slag, varde)
    anteckning = falt.text(anteckning, max_langd=2000)
    if anteckning and len(anteckning) > MAX_ANTECKNING:
        raise OgiltigSparr("note", "anteckning_for_lang")
    befintlig = await _gallande(storage, tenant_id, kanal, slag, normal)
    if befintlig:
        return befintlig, False
    try:
        rad = await lagring._in(storage, tenant_id, _TABELL, {
            "kanal": kanal, "slag": slag, "varde": normal, "orsak": orsak, "kalla": kalla,
            "anteckning": anteckning, "bolag_id": bolag_id, "person_id": person_id})
    except lagring.FinnsRedan:
        # Två samtidiga anrop: det andra får den första spärren tillbaka.
        befintlig = await _gallande(storage, tenant_id, kanal, slag, normal)
        if befintlig is None:
            raise
        return befintlig, False
    await handelser.logga(storage, tenant_id, [handelser.Handelse("sparr", rad["id"], "skapad", post=rad)],
                          kalla=via, aktor=aktor)
    return rad, True


async def hav(
    storage: Any, tenant_id: str, sparr_id: str, *, via: str = "system", aktor: str | None = None,
) -> dict[str, Any] | None:
    """Häver spärren. Den står kvar som bevis men gäller inte. En redan hävd
    spärr lämnas som den är. None om spärren inte finns hos kunden."""
    rad = await hamta(storage, tenant_id, sparr_id)
    if rad is None or rad.get("havd_at"):
        return rad
    ny = await lagring._upp(storage, tenant_id, _TABELL, sparr_id, {"havd_at": lagring.nu(), "havd_av": aktor or via})
    await handelser.logga(storage, tenant_id, [handelser.Handelse("sparr", sparr_id, "havd", post=ny)],
                          kalla=via, aktor=aktor)
    return ny


async def importera(
    storage: Any, tenant_id: str, *, kanal: str, orsak: str, varden: list[Any], slag: str | None = None,
    kalla: str = "import", via: str = "system", aktor: str | None = None,
) -> dict[str, Any]:
    """Lägger många spärrar i ett anrop, till exempel utfallet av kundens egen
    NIX-tvätt (kanal telefon, orsak nix).

    Returnerar `{"tillagda", "redan_sparrade", "ogiltiga": [{"index", "kod"}]}`.
    De tre talen räknar tillsammans varje värde i anropet: en dubblett i samma
    anrop är redan spärrad. Värdena själva står aldrig i svaret eller i loggen.
    """
    if len(varden) > MAX_IMPORT:
        raise OgiltigSparr("values", "for_manga")
    _kontrollera(kanal, slag, orsak, kalla)
    ogiltiga: list[dict[str, Any]] = []
    nya: dict[tuple[str, str], int] = {}
    redan = 0
    for index, varde in enumerate(varden):
        eget = slag or gissa_slag(kanal, varde)
        try:
            if eget not in _SLAG_I_KANAL[kanal]:
                raise OgiltigSparr("kind", "slag_passar_inte_kanalen")
            nyckel = (eget, normalisera(eget, varde))
        except OgiltigSparr as fel:
            ogiltiga.append({"index": index, "kod": fel.kod})
            continue
        if nyckel in nya:
            redan += 1
        else:
            nya[nyckel] = index
    tillagda = await _in_manga(storage, tenant_id, kanal=kanal, orsak=orsak, kalla=kalla, poster=list(nya))
    redan += len(nya) - len(tillagda)
    if tillagda:
        await handelser.logga(storage, tenant_id, [handelser.Handelse("sparr", r["id"], "skapad", post=r)
                                                   for r in tillagda], kalla=via, aktor=aktor)
    return {"tillagda": len(tillagda), "redan_sparrade": redan, "ogiltiga": ogiltiga}


async def _in_manga(
    storage: Any, tenant_id: str, *, kanal: str, orsak: str, kalla: str, poster: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Skriver de spärrar som inte redan gäller, i en sats i Postgres. Returnerar
    de nya raderna."""
    if not poster:
        return []
    if lagring._ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            rader = await conn.fetch(
                f"insert into {_TABELL} (tenant_id, kanal, slag, varde, orsak, kalla) "
                # Typade parametrar: i en select-lista har Postgres inget att härleda typen ur.
                "select $1::text::uuid, $2::text, t.slag, t.varde, $3::text, $4::text "
                "from unnest($5::text[], $6::text[]) as t(slag, varde) "
                "on conflict (tenant_id, kanal, slag, varde) where havd_at is null do nothing "
                "returning *", tenant_id, kanal, orsak, kalla, [s for s, _ in poster], [v for _, v in poster])
        return [lagring._rad(r, _TABELL) for r in rader]
    nya = []
    for slag, varde in poster:
        try:
            nya.append(await lagring._in(storage, tenant_id, _TABELL, {
                "kanal": kanal, "slag": slag, "varde": varde, "orsak": orsak, "kalla": kalla}))
        except lagring.FinnsRedan:
            continue
    return nya


# -- Grinden -----------------------------------------------------------------


def _kanaler_som_galler(kanal: str) -> tuple[str, ...]:
    """Spärrarnas kanaler som stoppar en kontakt i `kanal`. Frågan `alla` gäller
    om något alls stoppar, i någon kanal."""
    return KANALER if kanal == "alla" else (kanal, "alla")


async def ar_sparrad(
    storage: Any, tenant_id: str, *, epost: Any = None, telefon: Any = None, orgnr: Any = None, kanal: str,
) -> dict[str, Any]:
    """Spärrar NÅGON av källorna kontakten i kanalen?

    Returnerar `{"sparrad": bool, "kallor": [...], "sparr_id": [...]}` där
    `kallor` är några av `GRINDKALLOR` och `sparr_id` är spärrlistans träffar.
    Ingen adress, inget nummer och ingen anteckning följer med.
    """
    if kanal not in KANALER:
        raise OgiltigSparr("channel", "kanal_okand")
    adress = normalisera("epost", epost) if epost else None
    nummer = normalisera("telefon", telefon) if telefon else None
    nyckel = None
    if orgnr:
        try:
            _, nyckel, _ = falt.orgnr(orgnr)
        except falt.FaltFel as fel:
            raise OgiltigSparr("org_number", fel.kod) from None
    if not (adress or nummer or nyckel):
        raise OgiltigSparr("value", "varde_saknas")
    kallor: list[str] = []
    traffar = await _ur_listan(storage, tenant_id, kanal=kanal, adress=adress, nummer=nummer, nyckel=nyckel)
    if traffar:
        kallor.append("sparrlistan")
    if await _ur_posterna(storage, tenant_id, adress=adress, nummer=nummer, nyckel=nyckel):
        kallor.append("posten")
    if adress and kanal in ("mejl", "alla") and adress in await storage.list_suppressions(tenant_id):
        kallor.append("avregistrerad")
    if (adress or nyckel) and await _ur_leaden(storage, tenant_id, adress=adress, nyckel=nyckel):
        kallor.append("lead")
    return {"sparrad": bool(kallor), "kallor": kallor, "sparr_id": sorted(r["id"] for r in traffar)}


async def _ur_listan(
    storage: Any, tenant_id: str, *, kanal: str, adress: str | None, nummer: str | None, nyckel: str | None,
) -> list[dict[str, Any]]:
    sokta = {("epost", adress), ("doman", adress.rsplit("@", 1)[1] if adress else None),
             ("telefon", nummer), ("orgnr", nyckel)}
    sokta = {(s, v) for s, v in sokta if v}
    rader = await lagring._valj(storage, tenant_id, _TABELL, lika={"havd_at": None},
                                bland={"varde": sorted({v for _, v in sokta}),
                                       "kanal": list(_kanaler_som_galler(kanal))})
    return [r for r in rader if (r["slag"], r["varde"]) in sokta]


async def _ur_posterna(
    storage: Any, tenant_id: str, *, adress: str | None, nummer: str | None, nyckel: str | None,
) -> bool:
    """Ett levande bolag eller en levande person märkt kontakta inte, eller en
    person hos ett sådant bolag, med adressen, numret eller numret i registret."""
    bolag: list[dict[str, Any]] = []
    personer: list[dict[str, Any]] = []
    if adress:
        bolag += await lagring.hitta_poster(storage, tenant_id, "bolag", "epost", [adress])
        personer += await lagring.hitta_poster(storage, tenant_id, "person", "epost", [adress])
    if nummer:
        bolag += await lagring.hitta_poster(storage, tenant_id, "bolag", "telefon", [nummer])
        personer += await lagring.hitta_poster(storage, tenant_id, "person", "telefon", [nummer])
        personer += await lagring.hitta_poster(storage, tenant_id, "person", "mobil", [nummer])
    if nyckel:
        bolag += await lagring.hitta_poster(storage, tenant_id, "bolag", "orgnr_nyckel", [nyckel])
    if any(b.get("kontakta_inte") for b in bolag) or any(p.get("kontakta_inte") for p in personer):
        return True
    deras_bolag = sorted({p["bolag_id"] for p in personer if p.get("bolag_id")})
    if deras_bolag:
        return any(b.get("kontakta_inte") for b in await lagring.hitta_poster(
            storage, tenant_id, "bolag", "id", deras_bolag))
    return False


async def _ur_leaden(storage: Any, tenant_id: str, *, adress: str | None, nyckel: str | None) -> bool:
    from . import tidslinje  # sen import: tidslinjen läser leadsflödet

    leads = await tidslinje._prospekt(storage, tenant_id, nycklar=[nyckel] if nyckel else [],
                                      adresser=[adress] if adress else [])
    return any(p.get("status") == "suppressed" for p in leads)


# -- Mängderna sändspärren och ringlistan läser ------------------------------


async def sparrade_adresser(storage: Any, tenant_id: str) -> set[str]:
    """Adresser som aldrig får mejl: spärrlistan (mejl och alla), posterna
    märkta kontakta inte och de avregistrerade. Domänerna står i
    `sparrade_domaner`."""
    return await lagring.kontakta_inte_adresser(storage, tenant_id) | {
        str(a).strip().casefold() for a in await storage.list_suppressions(tenant_id) if a}


async def sparrade_domaner(storage: Any, tenant_id: str) -> set[str]:
    """Domäner där ingen adress får mejl (spärrlistan, mejl och alla)."""
    return await lagring.sparrade_varden(storage, tenant_id, kanaler=("mejl", "alla"), slag="doman")


async def sparrade_nummer(storage: Any, tenant_id: str) -> set[str]:
    """Nummer i E.164 som inte får ringas: spärrlistan (telefon och alla, där
    hör NIX-tvättens nummer hemma) och numren på poster märkta kontakta inte."""
    return await lagring.sparrade_varden(storage, tenant_id, kanaler=("telefon", "alla"), slag="telefon") | \
        await _kontakta_inte_nummer(storage, tenant_id)


async def sparrade_orgnr(storage: Any, tenant_id: str, *, kanal: str = "telefon") -> set[str]:
    """Organisationsnummer (tio siffror) som är spärrade i kanalen, och bolag
    märkta kontakta inte."""
    ut = await lagring.sparrade_varden(storage, tenant_id, kanaler=_kanaler_som_galler(kanal), slag="orgnr")
    bolag = await lagring._valj(storage, tenant_id, "crm_bolag", lika={"kontakta_inte": True}, levande=True)
    return ut | {b["orgnr_nyckel"] for b in bolag if b.get("orgnr_nyckel")}


async def _kontakta_inte_nummer(storage: Any, tenant_id: str) -> set[str]:
    """Telefon och mobil på bolag och personer märkta kontakta inte, och på
    personerna hos ett sådant bolag. Samma urval som `kontakta_inte_adresser`."""
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    """select telefon as nummer from crm_bolag
                        where tenant_id = $1::text::uuid and raderad_at is null
                          and kontakta_inte and telefon is not null
                       union
                       select unnest(array[p.telefon, p.mobil]) from crm_personer p
                         left join crm_bolag b on b.id = p.bolag_id and b.raderad_at is null
                        where p.tenant_id = $1::text::uuid and p.raderad_at is null
                          and (p.kontakta_inte or coalesce(b.kontakta_inte, false))""", tenant_id)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return set()
            raise
        return {r["nummer"] for r in rader if r["nummer"]}
    bolag = {b["id"]: b for b in lagring._minne(storage, "crm_bolag").values()
             if b["tenant_id"] == tenant_id and not b.get("raderad_at")}
    ut = {b["telefon"] for b in bolag.values() if b.get("kontakta_inte") and b.get("telefon")}
    for p in lagring._minne(storage, "crm_personer").values():
        if p["tenant_id"] != tenant_id or p.get("raderad_at"):
            continue
        if p.get("kontakta_inte") or (bolag.get(p.get("bolag_id")) or {}).get("kontakta_inte"):
            ut |= {n for n in (p.get("telefon"), p.get("mobil")) if n}
    return ut

