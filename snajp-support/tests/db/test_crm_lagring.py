"""CRM-lagret mot en riktig Postgres (migration 160).

Testerna i tests/crm går mot minneslagret. De visar att logiken stämmer, men
inte att SQL:en gör det: typomvandlingarna, de unika indexen, RLS-policyn och
körningens räknare finns bara i databasen. Här körs samma funktioner mot
tabellerna, som rollen snajp_app, i en transaktion som alltid rullas tillbaka.

Hoppas över utan DATABASE_URL. I CI körs det i jobbet `databastester`
(.github/workflows/verify.yml) mot hela migrationskedjan.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.crm import adaptrar, lagring, nycklar, synk

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = [
    pytest.mark.skipif(not DATABASE_URL, reason="Kräver en riktig Postgres-anslutning (DATABASE_URL)."),
    pytest.mark.anyio,
]

ORGNR_A, ORGNR_B = "556036-0793", "556016-0680"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Pool:
    """`pool.acquire()` som PostgresStorage använder för oskopade läsningar.
    En poolad anslutning utan kund har `app.tenant_id` = '' (se migration 028),
    så det sätts här inom en egen sparpunkt: annars hade testets tidigare
    `_scoped` lämnat kvar en kund och läsningen inte varit oskopad."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        async with self.conn.transaction():
            await self.conn.fetchval("select set_config('app.tenant_id', '', true)")
            yield self.conn


class Lager:
    """Det av PostgresStorage som CRM-lagret använder, på EN anslutning, så att
    allt hamnar i testets transaktion."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn
        self._nycklar: dict = {}
        self.pool = _Pool(conn)

    # Den riktiga systemläsningen, så att SQL:en och policyn tenant_lookup provas.
    from app.storage.postgres import PostgresStorage as _PG
    list_alla_tenant_ids = _PG.list_alla_tenant_ids
    del _PG

    @asynccontextmanager
    async def _scoped(self, tenant_id: str):
        async with self.conn.transaction():
            await self.conn.fetchval("select set_config('app.tenant_id', $1, true)", tenant_id)
            yield self.conn

    async def list_suppressions(self, tenant_id: str) -> set[str]:
        return set()

    async def list_begransade(self, tenant_id: str) -> set[str]:
        return set()


@pytest.fixture
async def miljo():
    """(lager, kund A, kund B) i en transaktion som rullas tillbaka."""
    conn = await asyncpg.connect(DATABASE_URL)
    tx = conn.transaction()
    await tx.start()
    try:
        a, b = str(uuid.uuid4()), str(uuid.uuid4())
        for tid, slug in ((a, "crm-a"), (b, "crm-b")):
            await conn.execute("insert into ss_tenants (id, slug, name) values ($1::text::uuid, $2, $3)",
                               tid, f"{slug}-{tid[:8]}", slug)
        # Resten körs som appens roll: utan BYPASSRLS, så att policyn gäller.
        await conn.execute("set local role snajp_app")
        yield Lager(conn), a, b
    finally:
        await tx.rollback()
        await conn.close()


def hubspot(eid: str, namn: str, orgnr: str | None = None, **egenskaper) -> dict:
    return {"id": eid, "updatedAt": egenskaper.pop("updatedAt", "2026-11-20T08:00:00.000Z"), "archived": False,
            "properties": {"name": namn, **({"orgnr": orgnr} if orgnr else {}), "lifecyclestage": "customer", **egenskaper}}


async def test_hela_synken_gar_mot_tabellerna(miljo):
    lager, a, _ = miljo
    anslutning = await lagring.skapa_anslutning(lager, a, namn="hubspot", system="hubspot",
                                                mappning={"bolag": {"extra": {"bransch": "properties.industry"}}},
                                                saknade="tidigare_kund")
    assert anslutning["mappning"] == {"bolag": {"extra": {"bransch": "properties.industry"}}}
    assert (await lagring.hamta_anslutning(lager, a, "HubSpot"))["id"] == anslutning["id"]
    with pytest.raises(lagring.FinnsRedan):
        await lagring.skapa_anslutning(lager, a, namn="HUBSPOT", system="hubspot")

    korning = await lagring.skapa_korning(lager, a, anslutning_id=anslutning["id"], lage="full", startad_av="api")
    sats = [hubspot("1", "Byggarna Berggren AB", ORGNR_A, phone="08-123 456 78", zip="11122", city="Stockholm",
                    numberofemployees="12", annualrevenue="12000000", industry="Bygg"),
            hubspot("2", "Måleri Nord AB", ORGNR_B),
            hubspot("3", ""),
            hubspot("4", "Fel Nummer AB", "556036-0794")]
    ut = await synk.synka_sats(lager, a, anslutning, korning, "bolag", sats)
    assert [p["status"] for p in ut["poster"]] == ["skapad", "skapad", "hoppad", "skapad"]

    bolag = (await lagring.hitta_poster(lager, a, "bolag", "orgnr_nyckel", ["5560360793"]))[0]
    # Typerna kommer tillbaka som de ska: tal, datum, json, bool.
    assert bolag["anstallda"] == 12 and bolag["omsattning"] == 12000000
    assert bolag["extra"] == {"bransch": "Bygg"} and bolag["manuellt_andrade"] == {}
    assert bolag["enskild_firma"] is False and bolag["relation"] == "kund" and bolag["land"] == "SE"
    assert bolag["postnr"] == "111 22" and bolag["telefon"] == "+46812345678" and bolag["raderad_at"] is None

    # Samma sats igen: inget skapas, inget ändras.
    igen = await synk.synka_sats(lager, a, anslutning, korning, "bolag", sats)
    assert igen["summering"] == {"totalt": 4, "oforandrade": 3, "hoppade": 1}

    # En handändring, sedan en ändring i källan: konfliktregeln läser manuellt_andrade.
    await synk.andra(lager, a, "bolag", bolag["id"], {"telefon": "070-111 11 11", "avtalsslut": "2027-03-31"})
    efter = await lagring.hamta_post(lager, a, "bolag", bolag["id"])
    assert efter["avtalsslut"] == "2027-03-31" and set(efter["manuellt_andrade"]) == {"telefon", "avtalsslut"}
    await lagring.uppdatera_anslutning(lager, a, anslutning["id"], konfliktregel="snajp_vinner")
    anslutning = await lagring.hamta_anslutning(lager, a, anslutning["id"])
    sats[0] = hubspot("1", "Byggarna Berggren AB", ORGNR_A, phone="08-999 99 99", city="Göteborg")
    andrad = await synk.synka_sats(lager, a, anslutning, korning, "bolag", sats[:2])
    assert andrad["poster"][0]["behallna_falt"] == ["telefon"]
    efter = await lagring.hamta_post(lager, a, "bolag", bolag["id"])
    assert efter["telefon"] == "+46701111111" and efter["postort"] == "Göteborg"

    # Personer, knutna via källans bolags-id.
    personer = await synk.synka_sats(lager, a, anslutning, korning, "person", [
        {"id": "p1", "properties": {"firstname": "Anna", "lastname": "Berg", "email": "Anna@Berggren.se",
                                    "associatedcompanyid": "1"}}])
    person = await lagring.hamta_post(lager, a, "person", personer["poster"][0]["id"])
    assert person["bolag_id"] == bolag["id"] and person["epost"] == "anna@berggren.se"

    # Liggaren: räknarna summeras i databasen, felen sparas.
    liggare = await lagring.hamta_korning(lager, a, korning["id"])
    assert (liggare["totalt"], liggare["skapade"], liggare["uppdaterade"], liggare["oforandrade"]) == (11, 4, 1, 4)
    assert len(liggare["fel"]) == 4 and liggare["fel"][0]["orsak"] == "saknar_namn"

    # Full synk avslutas: bolag 4 nämndes inte i sista satsen men sågs i körningen, så inget saknas.
    klar = await synk.slutfor(lager, a, anslutning, korning)
    assert klar["status"] == "completed" and klar["borttagna"] == 0 and klar["completed_at"]
    # Nästa fulla synk nämner bara bolag 1: de andra två kunderna blir tidigare kunder.
    natt = await lagring.skapa_korning(lager, a, anslutning_id=anslutning["id"], lage="full")
    await synk.synka_sats(lager, a, anslutning, natt, "bolag", sats[:1])
    assert (await synk.slutfor(lager, a, anslutning, natt))["borttagna"] == 2
    assert await lagring.rakna_poster(lager, a, "bolag") == {"kund": 1, "tidigare_kund": 2, "alla": 3}
    # Ordningen prövas i tests/crm: här delar raderna transaktion och därmed now().
    assert {k["id"] for k in await lagring.lista_korningar(lager, a)} == {natt["id"], korning["id"]}


async def test_felen_pa_en_korning_har_ett_tak(miljo):
    lager, a, _ = miljo
    korning = await lagring.skapa_korning(lager, a, lage="delta")
    for _ in range(3):
        await lagring.rakna_korning(lager, a, korning["id"], {"totalt": 90, "hoppade": 90}, [{"index": i} for i in range(90)])
    rad = await lagring.hamta_korning(lager, a, korning["id"])
    assert rad["totalt"] == 270 and rad["hoppade"] == 270 and len(rad["fel"]) == lagring.MAX_FEL


async def test_orgnr_ar_unikt_per_kund_bland_levande_rader(miljo):
    lager, a, b = miljo
    ett, skapad = await synk.skapa(lager, a, "bolag", {"namn": "A AB", "orgnr": ORGNR_A}, kalla="api")
    assert skapad and ett["orgnr_nyckel"] == "5560360793"
    samma, skapad = await synk.skapa(lager, a, "bolag", {"namn": "A AB", "orgnr": "16556036-0793", "anstallda": 5}, kalla="api")
    assert not skapad and samma["id"] == ett["id"] and samma["anstallda"] == 5
    # Indexet självt, förbi uppslaget i koden.
    with pytest.raises(lagring.FinnsRedan):
        await lagring.skapa_post(lager, a, "bolag", {"namn": "Kopia AB", "orgnr_nyckel": "5560360793"})
    # Hos en annan kund är samma nummer en egen post.
    annan, skapad = await synk.skapa(lager, b, "bolag", {"namn": "A AB", "orgnr": ORGNR_A}, kalla="api")
    assert skapad and annan["id"] != ett["id"]
    # En mjukt raderad rad håller inte numret.
    assert await synk.radera(lager, a, "bolag", ett["id"])
    ny, skapad = await synk.skapa(lager, a, "bolag", {"namn": "A AB", "orgnr": ORGNR_A}, kalla="api")
    assert skapad and ny["id"] != ett["id"]
    # Kontrollvillkoret på nyckeln: tio siffror, inget annat.
    with pytest.raises(asyncpg.CheckViolationError):
        await lagring.skapa_post(lager, a, "bolag", {"namn": "X", "orgnr_nyckel": "556036-0793"})


async def test_epost_ar_unik_per_kund_utan_hansyn_till_skiftlage(miljo):
    lager, a, _ = miljo
    await lagring.skapa_post(lager, a, "person", {"epost": "anna@a.se"})
    with pytest.raises(lagring.FinnsRedan):
        await lagring.skapa_post(lager, a, "person", {"epost": "Anna@A.se"})


async def test_listning_sok_markor_och_andringsordning(miljo):
    lager, a, _ = miljo
    for i in range(7):
        await synk.skapa(lager, a, "bolag", {"namn": f"Bolag {i} AB", "postort": "Umeå" if i % 2 else "Luleå"}, kalla="api")
    sedda, markor = [], None
    while True:
        sida, markor = await lagring.lista_poster(lager, a, "bolag", limit=3, ordning="namn", markor=markor)
        sedda += [p["namn"] for p in sida]
        if not markor:
            break
    assert sedda == [f"Bolag {i} AB" for i in range(7)]
    assert len((await lagring.lista_poster(lager, a, "bolag", q="umeå"))[0]) == 3
    assert len((await lagring.lista_poster(lager, a, "bolag", lika={"relation": "kund"}))[0]) == 7
    alla, _ = await lagring.lista_poster(lager, a, "bolag", limit=500)
    # Ändringsordning: sidorna tillsammans är alla poster, var och en en gång.
    forsta, markor = await lagring.lista_poster(lager, a, "bolag", limit=4)
    resten, slut = await lagring.lista_poster(lager, a, "bolag", limit=4, markor=markor)
    assert slut is None and [p["id"] for p in forsta + resten] == [p["id"] for p in alla]
    # Gravstenar syns bara när de efterfrågas.
    await synk.radera(lager, a, "bolag", alla[0]["id"])
    assert len((await lagring.lista_poster(lager, a, "bolag"))[0]) == 6
    med, _ = await lagring.lista_poster(lager, a, "bolag", med_raderade=True, andrad_sedan=alla[0]["updated_at"])
    assert any(p["raderad_at"] for p in med)
    assert [r["company_name"] for r in await lagring.upptagna_rader(lager, a)] == sorted(
        f"Bolag {i} AB" for i in range(1, 7)) or len(await lagring.upptagna_rader(lager, a)) == 6


async def test_rls_en_kund_nar_aldrig_en_annans_rader(miljo):
    """Policyn själv, inte bara filtret i koden: läsningen nedan har INGET
    tenant_id i frågan."""
    lager, a, b = miljo
    bolag, _ = await synk.skapa(lager, a, "bolag", {"namn": "Hemligt AB", "orgnr": ORGNR_A}, kalla="api")
    anslutning = await lagring.skapa_anslutning(lager, a, namn="kalla")
    await lagring.skapa_korning(lager, a, anslutning_id=anslutning["id"])
    await lagring.spara_idempotens(lager, a, "n1", vag="POST /x", kroppshash="h", statuskod=201, svar={"id": 1})
    tabeller = ("crm_bolag", "crm_anslutningar", "crm_synkkorningar", "crm_idempotens")
    async with lager._scoped(a) as conn:
        for tabell in tabeller:
            assert await conn.fetchval(f"select count(*) from {tabell}") == 1, tabell
    async with lager._scoped(b) as conn:
        for tabell in tabeller:
            assert await conn.fetchval(f"select count(*) from {tabell}") == 0, tabell
        assert await conn.fetchrow("select 1 from crm_bolag where id = $1::text::uuid", bolag["id"]) is None
        andrade = await conn.execute("update crm_bolag set namn = 'Kapat' where id = $1::text::uuid", bolag["id"])
        assert andrade == "UPDATE 0"
        # Och det går inte att skriva en rad i en annan kunds namn.
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            async with conn.transaction():
                await conn.execute("insert into crm_bolag (tenant_id, namn) values ($1::text::uuid, 'Smugglat AB')", a)
    assert await lagring.hamta_post(lager, b, "bolag", bolag["id"]) is None
    assert await lagring.uppdatera_post(lager, b, "bolag", bolag["id"], {"namn": "Kapat"}) is None
    assert await lagring.las_idempotens(lager, b, "n1") is None
    assert (await lagring.las_idempotens(lager, a, "n1"))["svar"] == {"id": 1}
    assert (await lagring.hamta_post(lager, a, "bolag", bolag["id"]))["namn"] == "Hemligt AB"


async def test_kundadresser_och_papperskorgen_i_databasen(miljo):
    lager, a, b = miljo
    kund, _ = await synk.skapa(lager, a, "bolag", {"namn": "Kund AB", "orgnr": ORGNR_A, "epost": "Info@Kund.se"}, kalla="api")
    prospekt, _ = await synk.skapa(lager, a, "bolag", {"namn": "Prospekt AB", "epost": "info@prospekt.se",
                                                      "relation": "prospekt"}, kalla="api")
    anna, _ = await synk.skapa(lager, a, "person", {"fornamn": "Anna", "epost": "anna@kund.se", "bolag_id": kund["id"],
                                                   "extra": {"not": "ringer helst på förmiddagen"}}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "bo@prospekt.se", "bolag_id": prospekt["id"]}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "los@ingenstans.se"}, kalla="api")
    # Bara kundernas adresser spärras för kallmejl: bolagets egen och personernas.
    assert await lagring.kundadresser(lager, a) == {"info@kund.se", "anna@kund.se"}
    assert await lagring.kundadresser(lager, b) == set()

    # Permanent radering tömmer raden i databasen, och källans id glöms.
    anslutning = await lagring.skapa_anslutning(lager, a, namn="kalla")
    await lagring.satt_externt_id(lager, a, befintlig=None, anslutning_id=anslutning["id"], objekt="person",
                                  externt_id="p1", post_id=anna["id"])
    assert await synk.radera(lager, a, "person", anna["id"], permanent=True)
    async with lager._scoped(a) as conn:
        rad = dict(await conn.fetchrow("select * from crm_personer where id = $1::text::uuid", anna["id"]))
        assert rad["kalla"] == "gravsten" and rad["raderad_at"] is not None
        assert all(rad[k] is None for k in ("fornamn", "efternamn", "epost", "telefon", "mobil", "bolag_id"))
        assert "anna" not in str(rad).lower() and "förmiddagen" not in str(rad)
        assert await conn.fetchval("select count(*) from crm_externa_id where post_id = $1::text::uuid", anna["id"]) == 0
    with pytest.raises(synk.RedanTomd):
        await synk.aterstall(lager, a, "person", anna["id"])
    assert await lagring.kundadresser(lager, a) == {"info@kund.se"}

    # Trettio dagar i papperskorgen: sedan töms raden av nästa radering.
    await synk.radera(lager, a, "bolag", prospekt["id"])
    assert (await synk.aterstall(lager, a, "bolag", prospekt["id"]))["raderad_at"] is None
    await synk.radera(lager, a, "bolag", prospekt["id"])
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_bolag set raderad_at = now() - interval '31 days' where id = $1::text::uuid", prospekt["id"])
    assert await lagring.tom_papperskorg(lager, a, "bolag") == 1
    assert await lagring.tom_papperskorg(lager, a, "bolag") == 0
    tomd = await lagring.hamta_post(lager, a, "bolag", prospekt["id"], med_raderade=True)
    assert tomd["kalla"] == "gravsten" and tomd["namn"] == "" and tomd["epost"] is None and tomd["relation"] == "ovrigt"


async def test_nycklar_med_omfang_i_databasen(miljo):
    lager, a, b = miljo
    ny = await nycklar.skapa(lager, a, tenant_namn="A", namn="Buddys CRM", omfang=["crm:synk", "crm:las"])
    assert ny["api_key"].startswith("snajp_crm_") and ny["omfang"] == ["crm:las", "crm:synk"]
    assert [n["namn"] for n in await nycklar.lista(lager, a)] == ["Buddys CRM"]
    assert await nycklar.lista(lager, b) == []
    assert not await nycklar.aterkalla(lager, b, ny["id"])       # fel kund
    assert await nycklar.aterkalla(lager, a, ny["id"])
    assert not await nycklar.aterkalla(lager, a, ny["id"])       # redan indragen
    assert (await nycklar.lista(lager, a))[0]["revoked_at"]


async def test_varje_kolumn_i_koden_finns_i_databasen(miljo):
    """TABELLER i lagret och migrationen får inte glida isär."""
    lager, a, _ = miljo
    async with lager._scoped(a) as conn:
        for tabell, kolumner in lagring.TABELLER.items():
            finns = {r["column_name"] for r in await conn.fetch(
                "select column_name from information_schema.columns where table_schema = 'public' and table_name = $1",
                tabell)}
            assert set(kolumner) <= finns, (tabell, set(kolumner) - finns)
            assert finns - set(kolumner) <= {"synk_andrad_at"}, (tabell, finns - set(kolumner))
    assert set(adaptrar.BOLAGSFALT) <= set(lagring.TABELLER["crm_bolag"])


# -- Migration 161: besluten -------------------------------------------------


async def test_privatperson_kontakta_inte_och_fria_tidigare_kunder_i_databasen(miljo):
    lager, a, b = miljo
    privat, _ = await synk.skapa(lager, a, "bolag", {"namn": "Anna Berg", "privatperson": True,
                                                    "epost": "anna@example.se"}, kalla="api")
    assert privat["privatperson"] is True and privat["kontakta_inte"] is True
    # Databasen bär regeln själv: en privatperson kan inte stå som kontaktbar.
    with pytest.raises(asyncpg.CheckViolationError):
        async with lager._scoped(a) as conn:
            await conn.execute("update crm_bolag set kontakta_inte = false where id = $1::text::uuid", privat["id"])
    tyst, _ = await synk.skapa(lager, a, "bolag", {"namn": "Tyst AB", "epost": "info@tyst.se",
                                                  "kontakta_inte": True}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "vd@tyst.se", "bolag_id": tyst["id"]}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "nej@annat.se", "kontakta_inte": True}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "fri@annat.se"}, kalla="api")
    assert await lagring.kontakta_inte_adresser(lager, a) == {
        "anna@example.se", "info@tyst.se", "vd@tyst.se", "nej@annat.se"}
    assert await lagring.kontakta_inte_adresser(lager, b) == set()

    await synk.skapa(lager, a, "bolag", {"namn": "Gamla Kunden AB", "orgnr": ORGNR_A,
                                         "relation": "tidigare_kund"}, kalla="api")
    await synk.skapa(lager, a, "bolag", {"namn": "Kund AB", "orgnr": ORGNR_B}, kalla="api")
    upptagna = {r["company_name"]: r for r in await lagring.upptagna_rader(lager, a)}
    assert "Gamla Kunden AB" not in upptagna and upptagna["Kund AB"]["bara_orgnr"] is True
    assert upptagna["Tyst AB"]["bara_orgnr"] is False

    anslutning = await lagring.skapa_anslutning(lager, a, namn="fortnox", system="fortnox", privatpersoner=True)
    assert anslutning["privatpersoner"] is True
    assert (await lagring.skapa_anslutning(lager, a, namn="annan"))["privatpersoner"] is False


async def test_senast_andrad_forst_och_papperskorgen_i_databasen(miljo):
    lager, a, b = miljo
    poster = [(await synk.skapa(lager, a, "bolag", {"namn": namn}, kalla="api"))[0]
              for namn in ("Alfa AB", "Beta AB", "Gamma AB", "Delta AB")]
    # Raderna delar transaktion och därmed now(): sätt tiderna för hand.
    async with lager._scoped(a) as conn:
        for i, post in enumerate(poster):
            await conn.execute("update crm_bolag set updated_at = now() - make_interval(mins => $2) "
                               "where id = $1::text::uuid", post["id"], 10 - i)
    forsta, markor = await lagring.lista_poster(lager, a, "bolag", ordning="andrad_fallande", limit=3)
    assert [p["namn"] for p in forsta] == ["Delta AB", "Gamma AB", "Beta AB"] and markor
    resten, slut = await lagring.lista_poster(lager, a, "bolag", ordning="andrad_fallande", limit=3, markor=markor)
    assert [p["namn"] for p in resten] == ["Alfa AB"] and slut is None

    for post in poster[:3]:
        await synk.radera(lager, a, "bolag", post["id"])
    await synk.radera(lager, a, "bolag", poster[2]["id"], permanent=True)   # töms: hör inte till korgen
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_bolag set raderad_at = now() - interval '2 days' where id = $1::text::uuid",
                           poster[0]["id"])
    korg, _ = await lagring.lista_poster(lager, a, "bolag", ordning="raderad")
    assert [p["namn"] for p in korg] == ["Beta AB", "Alfa AB"]
    sida, markor = await lagring.lista_poster(lager, a, "bolag", ordning="raderad", limit=1)
    nasta, _ = await lagring.lista_poster(lager, a, "bolag", ordning="raderad", limit=1, markor=markor)
    assert [p["namn"] for p in sida + nasta] == ["Beta AB", "Alfa AB"]
    assert (await lagring.lista_poster(lager, b, "bolag", ordning="raderad"))[0] == []


# -- Migration 162: händelser och webhooks ----------------------------------


async def test_handelseloggen_och_flodet_i_databasen(miljo):
    from app.crm import handelser

    lager, a, b = miljo
    bolag, _ = await synk.skapa(lager, a, "bolag", {"namn": "Bygg AB", "orgnr": ORGNR_A}, kalla="api",
                                via="api", aktor="nyckel:prov")
    await synk.andra(lager, a, "bolag", bolag["id"], {"telefon": "08-123 456 78", "postort": "Umeå"},
                     via="app", aktor="anvandare:1")
    await synk.radera(lager, a, "bolag", bolag["id"])
    await synk.aterstall(lager, a, "bolag", bolag["id"])
    flode, markor = await handelser.flode(lager, a)
    assert [(h["objekt"], h["typ"], h["kalla"]) for h in flode] == [
        ("bolag", "skapad", "api"), ("bolag", "andrad", "app"), ("bolag", "raderad", "api"),
        ("bolag", "aterstalld", "api")]
    assert flode[1]["falt"] == ["postort", "telefon"] and flode[1]["aktor"] == "anvandare:1"
    assert isinstance(flode[0]["id"], int) and markor == flode[-1]["id"]
    assert await handelser.flode(lager, a, efter=markor) == ([], markor)
    assert [h["typ"] for h in (await handelser.flode(lager, a, efter=flode[1]["id"], limit=1))[0]] == ["raderad"]
    assert (await handelser.flode(lager, a, objekt="person"))[0] == []
    assert [h["typ"] for h in await handelser.for_post(lager, a, "bolag", bolag["id"])] == [
        "aterstalld", "raderad", "andrad", "skapad"]
    # Radskyddet: den andra kunden ser varken flödet eller postens historik.
    assert (await handelser.flode(lager, b))[0] == []
    assert await handelser.for_post(lager, b, "bolag", bolag["id"]) == []


async def test_webhookarnas_ko_reservation_och_logg_i_databasen(miljo, monkeypatch):
    from app.crm import webhooks

    lager, a, b = miljo
    webhooks.nollstall()
    hake, hemlighet = await webhooks.skapa(lager, a, url="https://kund.example.se/snajp",
                                           handelser=["company.created"], beskrivning="prov")
    assert hemlighet.startswith("whsec_") and hake["handelser"] == ["company.created"] and hake["aktiv"] is True
    assert hemlighet not in str(hake)
    assert await webhooks.lista(lager, b) == [] and await webhooks.hamta(lager, b, hake["id"]) is None

    await synk.skapa(lager, a, "bolag", {"namn": "Bygg AB"}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "anna@bygg.se"}, kalla="api")     # inte prenumererad
    (leverans,) = await webhooks.leveranser(lager, a, hake["id"])
    assert leverans["handelsetyp"] == "company.created" and leverans["status"] == "vantar"
    assert leverans["kropp"]["data"]["object"] == "company" and leverans["forsok"] == 0

    # Reservationen: samma leverans tas inte två gånger.
    tagna = await webhooks._ta(lager, a, 10)
    assert [t["id"] for t in tagna] == [leverans["id"]] and tagna[0]["forsok"] == 1
    assert await webhooks._ta(lager, a, 10) == [] and await webhooks._ta(lager, b, 10) == []

    # Leveransen: mottagaren svarar 500, sedan 200.
    svar = {"status": 500}

    async def anropa(metod, url, **kw):
        class Svar:
            status = svar["status"]
            ok = 200 <= svar["status"] < 300
        return Svar()

    monkeypatch.setattr(webhooks.natvakt, "anropa", anropa)
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_webhook_leveranser set nasta_forsok_at = now() - interval '1 second'")
    assert await webhooks.leverera_for_kund(lager, a) == {"levererade": 0, "omforsok": 1, "misslyckade": 0}
    (rad,) = await webhooks.leveranser(lager, a, hake["id"])
    assert (rad["status"], rad["forsok"], rad["statuskod"], rad["fel"]) == ("vantar", 2, 500, "HTTP 500")
    assert (await webhooks.hamta(lager, a, hake["id"]))["fel_i_rad"] == 1
    svar["status"] = 200
    assert (await webhooks.skicka_om(lager, a, hake["id"], rad["id"]))["forsok"] == 0
    # Testet är en enda transaktion, så databasens now() står still på dess början.
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_webhook_leveranser set nasta_forsok_at = now() - interval '1 second'")
    assert await webhooks.leverera_for_kund(lager, a) == {"levererade": 1, "omforsok": 0, "misslyckade": 0}
    (rad,) = await webhooks.leveranser(lager, a, hake["id"])
    assert rad["status"] == "levererad" and rad["levererad_at"] and rad["statuskod"] == 200
    klar = await webhooks.hamta(lager, a, hake["id"])
    assert klar["fel_i_rad"] == 0 and klar["senast_ok_at"] and not await webhooks._har_ko(lager, a)

    # Loggen gallras efter trettio dagar, och webhooken tar sina leveranser med sig.
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_webhook_leveranser set created_at = now() - interval '31 days'")
    await webhooks._gallra(lager, a)
    assert await webhooks.leveranser(lager, a, hake["id"]) == []
    await webhooks.prova(lager, a, hake["id"])
    assert await webhooks.ta_bort(lager, a, hake["id"])
    async with lager._scoped(a) as conn:
        assert await conn.fetchval("select count(*) from crm_webhook_leveranser") == 0
    webhooks.nollstall()


# -- Migration 164: affärer, uppgifter, anteckningar, aktiviteter, bilagor ---


async def test_affarer_steg_och_tavlan_i_databasen(miljo):
    from app.crm import handelser, objekt

    lager, a, b = miljo
    steg = await objekt.lista_steg(lager, a)
    assert [s["namn"] for s in steg] == [s[0] for s in objekt.STANDARDSTEG]
    assert await objekt.lista_steg(lager, a) == steg                       # skapas en gång
    assert len(await objekt.lista_steg(lager, b)) == len(steg)              # varje kund sin egen uppsättning
    ny, vunnen = steg[0], next(s for s in steg if s["typ"] == "vunnen")
    bolag, _ = await synk.skapa(lager, a, "bolag", {"namn": "Bygg AB", "orgnr": ORGNR_A}, kalla="api")
    andras, _ = await synk.skapa(lager, b, "bolag", {"namn": "Annat AB"}, kalla="api")

    ett = await objekt.skapa(lager, a, "affar", {"namn": "Ett", "bolag_id": bolag["id"], "belopp": 120000})
    tva = await objekt.skapa(lager, a, "affar", {"namn": "Två", "belopp": 30000, "forvantat_avslut": "2026-12-31"})
    tre = await objekt.skapa(lager, a, "affar", {"namn": "Tre"})
    assert ett["steg_id"] == ny["id"] and ett["belopp"] == 120000 and ett["valuta"] == "SEK"
    assert isinstance(ett["position"], float) and ett["position"] < tva["position"] < tre["position"]
    assert tva["forvantat_avslut"] == "2026-12-31" and ett["avslutad_at"] is None
    # En koppling till en annan kunds bolag avvisas.
    with pytest.raises(objekt.ObjektFel):
        await objekt.skapa(lager, a, "affar", {"namn": "Fel", "bolag_id": andras["id"]})

    # Flytt: Tre överst, sedan mellan Ett och Två.
    await objekt.flytta(lager, a, tre["id"], ny["id"], fore_id=ett["id"])
    await objekt.flytta(lager, a, tre["id"], ny["id"], efter_id=ett["id"])
    tavla = await objekt.tavla(lager, a)
    assert [x["namn"] for x in tavla[0]["affarer"]] == ["Ett", "Tre", "Två"]
    # Till vunnen sätter avslutet, tillbaka nollar det.
    flyttad = await objekt.flytta(lager, a, ett["id"], vunnen["id"])
    assert flyttad["steg_id"] == vunnen["id"] and flyttad["avslutad_at"]
    assert (await objekt.flytta(lager, a, ett["id"], ny["id"]))["avslutad_at"] is None
    # Ett steg med affärer i går inte att ta bort.
    with pytest.raises(objekt.ObjektFel):
        await objekt.ta_bort_steg(lager, a, ny["id"])

    # Listan: sortering, sökning, filter och papperskorg.
    poster, _ = await lagring.lista_poster(lager, a, "affar", ordning="namn")
    assert [p["namn"] for p in poster] == ["Ett", "Tre", "Två"]
    assert [p["namn"] for p in (await lagring.lista_poster(lager, a, "affar", q="tv"))[0]] == ["Två"]
    assert [p["namn"] for p in (await lagring.lista_poster(lager, a, "affar", lika={"bolag_id": bolag["id"]}))[0]] == ["Ett"]
    await objekt.radera(lager, a, "affar", tva["id"])
    assert [p["namn"] for p in (await lagring.lista_poster(lager, a, "affar", ordning="raderad"))[0]] == ["Två"]
    assert (await objekt.aterstall(lager, a, "affar", tva["id"]))["raderad_at"] is None
    assert (await lagring.lista_poster(lager, b, "affar"))[0] == []
    assert await objekt.hamta(lager, b, "affar", ett["id"]) is None
    flode, _ = await handelser.flode(lager, a, objekt="affar")
    assert [h["typ"] for h in flode][:3] == ["skapad", "skapad", "skapad"] and "raderad" in [h["typ"] for h in flode]


async def test_uppgifter_anteckningar_aktiviteter_och_bilagor_i_databasen(miljo):
    from app.crm import objekt

    lager, a, b = miljo
    bolag, _ = await synk.skapa(lager, a, "bolag", {"namn": "Bygg AB"}, kalla="api")
    anna, _ = await synk.skapa(lager, a, "person", {"fornamn": "Anna", "epost": "anna@bygg.se",
                                                   "bolag_id": bolag["id"]}, kalla="api")

    sen = await objekt.skapa(lager, a, "uppgift", {"titel": "Senare", "forfaller_at": "2026-12-20T09:00:00+00:00"})
    snart = await objekt.skapa(lager, a, "uppgift", {"titel": "Snart", "forfaller_at": "2026-12-01T09:00:00+00:00",
                                                    "bolag_id": bolag["id"]})
    utan = await objekt.skapa(lager, a, "uppgift", {"titel": "Utan dag"})
    forfall, _ = await lagring.lista_poster(lager, a, "uppgift", ordning="forfaller")
    assert [u["titel"] for u in forfall] == ["Snart", "Senare", "Utan dag"]
    klar = await objekt.andra(lager, a, "uppgift", snart["id"], {"status": "klar"})
    assert klar["status"] == "klar" and klar["klar_at"]
    assert (await objekt.andra(lager, a, "uppgift", snart["id"], {"status": "pagar"}))["klar_at"] is None
    assert sen["status"] == "att_gora" and utan["forfaller_at"] is None

    anteckning = await objekt.skapa(lager, a, "anteckning", {"titel": "Möte", "text": "Vill ha offert på två platser.",
                                                            "person_id": anna["id"], "fast": True})
    assert anteckning["fast"] is True and anteckning["text"].startswith("Vill ha")
    with pytest.raises(objekt.ObjektFel):
        await objekt.skapa(lager, a, "anteckning", {"text": "Utan koppling"})
    aktivitet = await objekt.skapa(lager, a, "aktivitet", {"typ": "samtal", "rubrik": "Ringde Anna",
                                                          "varaktighet_min": 12, "person_id": anna["id"]})
    assert aktivitet["typ"] == "samtal" and aktivitet["varaktighet_min"] == 12 and aktivitet["tid"]

    fil = b"%PDF-1.7 " + bytes(range(256)) * 40                                 # binärt, med nollbyte
    bilaga = await objekt.skapa_bilaga(lager, a, filnamn="..\\..\\Offert Bygg.pdf", typ="application/pdf",
                                       innehall=fil, kopplingar={"person_id": anna["id"],
                                                                 "anteckning_id": anteckning["id"]})
    assert bilaga["filnamn"] == "Offert Bygg.pdf" and bilaga["storlek"] == len(fil) and "innehall" not in bilaga
    assert bytes(await lagring.bilagans_innehall(lager, a, bilaga["id"])) == fil
    assert await lagring.bilagans_innehall(lager, b, bilaga["id"]) is None
    assert await lagring.bilagornas_storlek(lager, a) == len(fil) and await lagring.bilagornas_storlek(lager, b) == 0
    listade, _ = await lagring.lista_poster(lager, a, "bilaga", lika={"person_id": anna["id"]})
    assert [x["filnamn"] for x in listade] == ["Offert Bygg.pdf"] and "innehall" not in listade[0]

    # Personen töms för gott (art. 17): anteckningen, aktiviteten och filen töms med henne.
    assert await synk.radera(lager, a, "person", anna["id"], permanent=True)
    async with lager._scoped(a) as conn:
        rad = dict(await conn.fetchrow("select * from crm_anteckningar where id = $1::text::uuid", anteckning["id"]))
        assert rad["kalla"] == "gravsten" and rad["text"] == "" and rad["titel"] is None and rad["raderad_at"]
        rad = dict(await conn.fetchrow("select * from crm_aktiviteter where id = $1::text::uuid", aktivitet["id"]))
        assert rad["kalla"] == "gravsten" and rad["text"] is None and "Anna" not in str(rad)
        rad = dict(await conn.fetchrow("select filnamn, storlek, kalla, octet_length(innehall) as langd "
                                       "from crm_bilagor where id = $1::text::uuid", bilaga["id"]))
        assert rad["kalla"] == "gravsten" and rad["langd"] == 0 and "Offert" not in str(rad)
    assert await lagring.bilagornas_storlek(lager, a) == 0
    # Uppgiften på bolaget står kvar: den pekade inte på personen.
    assert (await objekt.hamta(lager, a, "uppgift", snart["id"]))["bolag_id"] == bolag["id"]


# -- Tidslinjen: frågan mot prospekten --------------------------------------


async def test_tidslinjens_prospektfraga_i_databasen(miljo):
    """Bara om prospekttabellen har leadsflödets kolumner (hela kedjan rest):
    frågan läser den genererade kolumnen foretagsnyckel."""
    from app.crm import tidslinje

    lager, a, b = miljo
    async with lager._scoped(a) as conn:
        kolumner = {r["column_name"] for r in await conn.fetch(
            "select column_name from information_schema.columns where table_name = 'prospects'")}
    if not {"foretagsnyckel", "contact_email", "origin", "company_name"} <= kolumner:
        pytest.skip("prospects saknar leadsflödets kolumner i den här databasen")
    assert await tidslinje._prospekt(lager, a, nycklar=["5560360793"], adresser=["ingen@ingenstans.se"]) == []
    assert await tidslinje._prospekt(lager, b, nycklar=[], adresser=[]) == []


# -- Migration 163: rapporten till supporten ---------------------------------


async def test_supportrapporten_sparas_pa_korningen_i_databasen(miljo):
    from app.crm import supportrapport

    lager, a, b = miljo
    anslutning = await lagring.skapa_anslutning(lager, a, namn="egen", system="generisk")
    korning = await lagring.skapa_korning(lager, a, anslutning_id=anslutning["id"])
    await synk.synka_sats(lager, a, anslutning, korning, "bolag", [
        {"id": "1", "name": "Rent AB"}, {"id": "2", "name": "Fel Telefon AB", "phone": "12 34 56 7"}, {"id": "3"}])
    klar = await synk.slutfor(lager, a, anslutning, korning)
    assert klar["support_lamnad_at"] and klar["support_arende"] is None
    rapport = klar["supportrapport"]
    assert rapport["koder"] == {"saknar_namn": 1, "telefon_saknar_riktnummer": 1}
    assert rapport["rader"][0]["faltfel"] == [{"falt": "telefon", "kod": "telefon_saknar_riktnummer", "form": "99 99 99 9"}]
    assert rapport["anslutning"]["system"] == "generisk" and rapport["korning"]["raknare"]["totalt"] == 3
    assert supportrapport.enkelt(klar) == [
        {"sort": "ogiltigt_varde", "objekt": "bolag", "falt": "telefon", "antal": 1},
        {"sort": "saknar_uppgift", "objekt": "bolag", "falt": None, "antal": 1}]
    assert (await supportrapport.satt_arende(lager, a, klar["id"], "F-7KQ2"))["support_arende"] == "F-7KQ2"
    assert await supportrapport.satt_arende(lager, b, klar["id"], "F-FEL") is None


async def test_supportarendets_arbetsyta_och_kaskaden_for_en_affar_i_databasen(miljo):
    """Arbetsytan slås upp oskopat (som tillgang.grund), bara id. En tömd affär
    tar med sig sin anteckning, och uppgiften tappar kopplingen."""
    from app.crm import objekt, supportrapport

    lager, a, b = miljo
    assert await supportrapport._arbetsyta(lager, a) is None
    ws = str(uuid.uuid4())
    # Arbetsytan läggs in som ägaren: workspaces har eget radskydd i kedjan.
    await lager.conn.execute("reset role")
    await lager.conn.execute("insert into workspaces (id, ss_tenant_id) values ($1::text::uuid, $2::text::uuid)", ws, a)
    await lager.conn.execute("set local role snajp_app")
    assert await supportrapport._arbetsyta(lager, a) == ws
    assert await supportrapport._arbetsyta(lager, b) is None

    affar = await objekt.skapa(lager, a, "affar", {"namn": "Takbyte"})
    anteckning = await objekt.skapa(lager, a, "anteckning", {"text": "Offert till Anna", "affar_id": affar["id"]})
    uppgift = await objekt.skapa(lager, a, "uppgift", {"titel": "Skicka offert", "affar_id": affar["id"]})
    await lagring.gor_gravsten(lager, a, "affar", affar["id"])
    async with lager._scoped(a) as conn:
        rad = dict(await conn.fetchrow("select text, kalla, affar_id from crm_anteckningar where id = $1::text::uuid",
                                       anteckning["id"]))
        assert rad == {"text": "", "kalla": "gravsten", "affar_id": None}
        rad = dict(await conn.fetchrow("select titel, affar_id, raderad_at from crm_uppgifter "
                                       "where id = $1::text::uuid", uppgift["id"]))
        assert rad == {"titel": "Skicka offert", "affar_id": None, "raderad_at": None}


async def test_synkens_supportarende_skapas_och_ateranvands_i_databasen(miljo, monkeypatch):
    """Granskningens fynd: ärendeflödet var bara provat mot minneslagret. Här
    går det mot plattformsärendena (migration 156) med PostgresStorages egna
    metoder och systemrapportörens värden: ärendet skapas, den första
    händelsen är synkens och intern, nästa körning återanvänder ärendet med
    en intern händelse, och ett stängt ärende ger ett nytt."""
    from app.crm import supportrapport
    from app.storage.postgres import PostgresStorage as PG

    lager, a, b = miljo
    for namn in ("_ARENDE_KOLUMNER", "_plattformsarenden_med_handelser", "skapa_plattformsarende",
                 "hitta_oppet_plattformsarende", "andra_plattformsarende", "hamta_plattformsarende",
                 "list_plattformsarenden"):
        monkeypatch.setattr(Lager, namn, getattr(PG, namn), raising=False)

    async def _kund(tenant_id):
        return {"id": tenant_id, "slug": "crm-a" if tenant_id == a else "crm-b", "name": "Kund"}

    async def _inga_kunder():
        return []

    lager.get_tenant, lager.list_tenants = _kund, _inga_kunder
    ws = str(uuid.uuid4())
    await lager.conn.execute("reset role")
    await lager.conn.execute("insert into workspaces (id, ss_tenant_id) values ($1::text::uuid, $2::text::uuid)", ws, a)
    await lager.conn.execute("set local role snajp_app")

    anslutning = await lagring.skapa_anslutning(lager, a, namn="egen", system="generisk")

    async def _korning():
        korning = await lagring.skapa_korning(lager, a, anslutning_id=anslutning["id"])
        await synk.synka_sats(lager, a, anslutning, korning, "bolag", [{"id": "1", "name": "Rent AB"}, {"id": "3"}])
        return await synk.slutfor(lager, a, anslutning, korning)

    forsta = await _korning()
    nummer = forsta["support_arende"]
    assert nummer and nummer.startswith("F-")
    oppet = await lager.hitta_oppet_plattformsarende(
        rapportor_user_id=supportrapport.SYSTEMRAPPORTOR, kund_workspace_id=ws, kund_tenant_slug="crm-a",
        gjorde="Synk från egen (delta)")
    assert oppet and oppet["nummer"] == nummer and oppet["status"] == "mottagen"
    arende = await lager.hamta_plattformsarende(oppet["id"])
    assert (arende["rapportor_user_id"], arende["vy"], arende["roll"], arende["sida"]) == (
        supportrapport.SYSTEMRAPPORTOR, "crm", "system", "/crm/synk")
    assert [(h["typ"], h["aktor"], h["synlig_for_kund"]) for h in arende["handelser"]] == [("skapad", "system", False)]

    andra = await _korning()
    assert andra["support_arende"] == nummer
    arende = await lager.hamta_plattformsarende(oppet["id"])
    # I testets enda transaktion står now() still: händelsernas ordning
    # avgörs då av id, så de jämförs utan ordning.
    assert sorted((h["typ"], h["aktor"], h["synlig_for_kund"]) for h in arende["handelser"]) == [
        ("skapad", "system", False), ("synk", "system", False)]
    (synk_handelse,) = [h for h in arende["handelser"] if h["typ"] == "synk"]
    assert synk_handelse["meddelande"] == f"Samma anslutning föll igen i körning {andra['id']}: 1 poster"
    assert arende["status"] == "mottagen"
    # En annan arbetsyta eller ett annat `gjorde` hittar inte ärendet.
    assert await lager.hitta_oppet_plattformsarende(
        rapportor_user_id=supportrapport.SYSTEMRAPPORTOR, kund_workspace_id=str(uuid.uuid4()),
        kund_tenant_slug="crm-a", gjorde="Synk från egen (delta)") is None

    await lager.andra_plattformsarende(oppet["id"], status="stangd",
                                       handelse={"typ": "status", "aktor": "plattformsadmin"})
    tredje = await _korning()
    assert tredje["support_arende"] not in (None, nummer)
    assert len(await lager.list_plattformsarenden(rapportor_user_id=supportrapport.SYSTEMRAPPORTOR)) == 2


async def test_ej_aktuell_ar_upptagen_och_raknas_i_databasen(miljo):
    """Migration 165: relationen ej_aktuell tas emot av check-villkoret, står
    kvar bland de upptagna och räknas för sig i översikten."""
    lager, a, b = miljo
    await synk.skapa(lager, a, "bolag", {"namn": "Nej Tack AB", "orgnr": ORGNR_A, "relation": "ej_aktuell"},
                     kalla="api")
    await synk.skapa(lager, a, "bolag", {"namn": "Gammal AB", "orgnr": ORGNR_B, "relation": "tidigare_kund"},
                     kalla="api")
    assert [r["company_name"] for r in await lagring.upptagna_rader(lager, a)] == ["Nej Tack AB"]
    assert await lagring.rakna_poster(lager, a, "bolag") == {"ej_aktuell": 1, "tidigare_kund": 1, "alla": 2}
    assert await lagring.upptagna_rader(lager, b) == []
    with pytest.raises(asyncpg.CheckViolationError):
        await lagring.skapa_post(lager, a, "bolag", {"namn": "Fel AB", "relation": "pagaende"})


async def test_forlustorsak_kod_i_databasen(miljo):
    from app.crm import objekt

    lager, a, b = miljo
    forlorad = next(s for s in await objekt.lista_steg(lager, a) if s["typ"] == "forlorad")
    affar = await objekt.skapa(lager, a, "affar", {"namn": "Växel", "steg_id": forlorad["id"],
                                                   "forlustorsak_kod": "price", "forlustorsak": "Billigare"})
    assert affar["forlustorsak_kod"] == "pris" and affar["forlustorsak"] == "Billigare"
    await objekt.skapa(lager, a, "affar", {"namn": "Öppen"})
    poster, _ = await lagring.lista_poster(lager, a, "affar", lika={"forlustorsak_kod": "pris"})
    assert [p["id"] for p in poster] == [affar["id"]]
    assert (await lagring.lista_poster(lager, b, "affar", lika={"forlustorsak_kod": "pris"}))[0] == []
    with pytest.raises(asyncpg.CheckViolationError):
        await lagring.uppdatera_post(lager, a, "affar", affar["id"], {"forlustorsak_kod": "vadret"})
    await lagring.gor_gravsten(lager, a, "affar", affar["id"])
    assert (await lagring.hamta_post(lager, a, "affar", affar["id"], med_raderade=True))["forlustorsak_kod"] is None


async def test_personens_kalla_i_databasen(miljo):
    """Källan sätts av synken, skrivs inte över av nästa synk, filtreras och
    töms med gravstenen."""
    lager, a, b = miljo
    anslutning = await lagring.skapa_anslutning(lager, a, namn="lime", system="generisk",
                                                mappning={"person": {"kalla_typ": "kalltyp"}})
    korning = await lagring.skapa_korning(lager, a, anslutning_id=anslutning["id"])
    svar = await synk.synka_sats(lager, a, anslutning, korning, "person", [
        {"id": "p1", "email": "anna@kund.se"}, {"id": "p2", "email": "bo@kund.se", "kalltyp": "register"}])
    anna_id, bo_id = (p["id"] for p in svar["poster"])
    anna = await lagring.hamta_post(lager, a, "person", anna_id)
    assert (anna["kalla_typ"], anna["kalla_namn"], anna["kalla"]) == ("synk", "lime", "synk") and anna["insamlad_at"]
    bo = await lagring.hamta_post(lager, a, "person", bo_id)
    assert bo["kalla_typ"] == "register" and bo["kalla_namn"] is None
    await synk.synka_sats(lager, a, anslutning, korning, "person", [
        {"id": "p1", "email": "anna@kund.se", "first_name": "Anna", "kalltyp": "kunden"}])
    anna_efter = await lagring.hamta_post(lager, a, "person", anna_id)
    assert anna_efter["fornamn"] == "Anna" and anna_efter["kalla_typ"] == "synk"
    assert anna_efter["insamlad_at"] == anna["insamlad_at"]

    utan, _ = await synk.skapa(lager, a, "person", {"epost": "cecilia@kund.se"}, kalla="api")
    assert utan["kalla_typ"] is None and utan["insamlad_at"]
    saknar, _ = await lagring.lista_poster(lager, a, "person", tomma=["kalla_typ"])
    assert [p["id"] for p in saknar] == [utan["id"]]
    register, _ = await lagring.lista_poster(lager, a, "person", lika={"kalla_typ": "register"})
    assert [p["id"] for p in register] == [bo_id]
    assert (await lagring.lista_poster(lager, b, "person", tomma=["kalla_typ"]))[0] == []
    with pytest.raises(asyncpg.CheckViolationError):
        await lagring.uppdatera_post(lager, a, "person", utan["id"], {"kalla_typ": "rykten"})

    await lagring.gor_gravsten(lager, a, "person", bo_id)
    tomd = await lagring.hamta_post(lager, a, "person", bo_id, med_raderade=True)
    assert (tomd["kalla_typ"], tomd["kalla_namn"], tomd["insamlad_at"]) == (None, None, None)


# -- Migration 166: den gemensamma spärren -----------------------------------


async def test_sparren_och_det_unika_indexet_i_databasen(miljo):
    from app.crm import handelser, sparr

    lager, a, b = miljo
    rad, skapad = await sparr.lagg_till(lager, a, kanal="alla", slag="epost", varde="VD@Bygg.se",
                                        orsak="invandning", kalla="api", anteckning="Bad oss sluta.",
                                        via="api", aktor="nyckel:prov")
    assert skapad and rad["varde"] == "vd@bygg.se" and rad["havd_at"] is None and rad["created_at"]
    igen, skapad = await sparr.lagg_till(lager, a, kanal="alla", slag="epost", varde="vd@bygg.se",
                                         orsak="annat", kalla="app")
    assert not skapad and igen["id"] == rad["id"]
    # Det unika indexet gäller de ohävda: databasen säger nej till en andra.
    with pytest.raises(lagring.FinnsRedan):
        await lagring._in(lager, a, "crm_sparrar", {"kanal": "alla", "slag": "epost", "varde": "vd@bygg.se",
                                                    "orsak": "annat", "kalla": "app"})
    # Samma värde i en annan kanal är en annan spärr, och den andra kunden har ett eget index.
    assert (await sparr.lagg_till(lager, a, kanal="mejl", slag="epost", varde="vd@bygg.se",
                                  orsak="annat", kalla="app"))[1]
    assert (await sparr.lagg_till(lager, b, kanal="alla", slag="epost", varde="vd@bygg.se",
                                  orsak="annat", kalla="app"))[1]
    # Hävd står kvar, och då går samma spärr att lägga igen.
    havd = await sparr.hav(lager, a, rad["id"], via="api", aktor="nyckel:prov")
    assert havd["havd_at"] and havd["havd_av"] == "nyckel:prov"
    assert (await sparr.hav(lager, a, rad["id"]))["havd_at"] == havd["havd_at"]
    assert (await sparr.lagg_till(lager, a, kanal="alla", slag="epost", varde="vd@bygg.se",
                                  orsak="invandning", kalla="app"))[1]
    # Villkoren i tabellen: tio siffror för organisationsnumret, kända kanaler.
    for falt in ({"kanal": "alla", "slag": "orgnr", "varde": "556036-0793"},
                 {"kanal": "sms", "slag": "telefon", "varde": "+46701234567"}):
        with pytest.raises(asyncpg.CheckViolationError):
            async with lager._scoped(a) as conn:
                await conn.execute(
                    "insert into crm_sparrar (tenant_id, kanal, slag, varde) values ($1::text::uuid, $2, $3, $4)",
                    a, falt["kanal"], falt["slag"], falt["varde"])
    # Händelserna står i loggen med typen havd, utan värdet och anteckningen.
    flode, _ = await handelser.flode(lager, a, objekt="sparr")
    assert [h["typ"] for h in flode] == ["skapad", "skapad", "havd", "skapad"]
    assert "vd@bygg.se" not in str(flode) and "Bad oss" not in str(flode)
    # Radskyddet: den andra kunden ser bara sin egen.
    alla_b, _ = await sparr.lista(lager, b)
    assert len(alla_b) == 1 and alla_b[0]["tenant_id"] == b


async def test_sparrens_lista_import_och_grind_i_databasen(miljo):
    from app.crm import sparr

    lager, a, b = miljo
    ut = await sparr.importera(lager, a, kanal="telefon", orsak="nix",
                               varden=["070-123 45 67", "+46701234567", "123", "08-555 666 77"])
    assert ut == {"tillagda": 2, "redan_sparrade": 1, "ogiltiga": [{"index": 2, "kod": "telefon_saknar_landskod"}]}
    igen = await sparr.importera(lager, a, kanal="telefon", orsak="nix", varden=["0701234567"])
    assert igen == {"tillagda": 0, "redan_sparrade": 1, "ogiltiga": []}
    await sparr.lagg_till(lager, a, kanal="mejl", slag="doman", varde="konkurrent.se", orsak="annat", kalla="app")
    await sparr.lagg_till(lager, a, kanal="alla", slag="orgnr", varde=ORGNR_A, orsak="kunden_bad", kalla="utfall")
    # Listan, senast lagd först, med markör; filtret på kanal och sökningen.
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_sparrar set created_at = now() - make_interval(mins => 10) "
                           "where tenant_id = $1::text::uuid and orsak = 'nix'", a)
    forsta, markor = await sparr.lista(lager, a, limit=2)
    # De två senaste delar now() i testets transaktion: ordningen mellan dem går på id.
    assert {r["slag"] for r in forsta} == {"doman", "orgnr"}
    resten, slut = await sparr.lista(lager, a, limit=2, markor=markor)
    assert {r["orsak"] for r in resten} == {"nix"} and slut is None
    assert len((await sparr.lista(lager, a, kanal="telefon"))[0]) == 2
    assert [r["varde"] for r in (await sparr.lista(lager, a, q="KONKURRENT"))[0]] == ["konkurrent.se"]
    # Organisationsnumret går att söka så som API:t visar det, med streck.
    for q in (ORGNR_A, ORGNR_A.replace("-", "")):
        assert [r["varde"] for r in (await sparr.lista(lager, a, q=q))[0]] == ["5560360793"], q
    # Grinden: listan, kanalerna och domänen.
    assert (await sparr.ar_sparrad(lager, a, telefon="0701234567", kanal="telefon"))["kallor"] == ["sparrlistan"]
    assert not (await sparr.ar_sparrad(lager, a, telefon="0701234567", kanal="mejl"))["sparrad"]
    assert (await sparr.ar_sparrad(lager, a, epost="vd@konkurrent.se", kanal="mejl"))["sparrad"]
    assert (await sparr.ar_sparrad(lager, a, orgnr=ORGNR_A, kanal="telefon"))["sparrad"]
    assert not (await sparr.ar_sparrad(lager, b, orgnr=ORGNR_A, kanal="alla"))["sparrad"]
    # Mängderna sändspärren och ringlistan läser.
    assert await sparr.sparrade_domaner(lager, a) == {"konkurrent.se"}
    assert await sparr.sparrade_nummer(lager, a) == {"+46701234567", "+46855566677"}
    assert await sparr.sparrade_orgnr(lager, a) == {"5560360793"}
    assert await sparr.sparrade_nummer(lager, b) == set()


async def test_posten_och_sandsparrens_mangd_i_databasen(miljo):
    from app.crm import sparr

    lager, a, b = miljo
    tyst, _ = await synk.skapa(lager, a, "bolag", {"namn": "Tyst AB", "orgnr": ORGNR_B, "telefon": "08-123 456 78",
                                                  "kontakta_inte": True}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "vd@tyst.se", "mobil": "070-111 22 33",
                                          "bolag_id": tyst["id"]}, kalla="api")
    await synk.skapa(lager, a, "person", {"epost": "fri@annat.se", "telefon": "070-999 88 77"}, kalla="api")
    await sparr.lagg_till(lager, a, kanal="mejl", slag="epost", varde="lista@bygg.se", orsak="annat", kalla="app")
    await sparr.lagg_till(lager, a, kanal="telefon", slag="telefon", varde="070-222 33 44", orsak="nix", kalla="app")
    assert await lagring.kontakta_inte_adresser(lager, a) == {"vd@tyst.se", "lista@bygg.se"}
    assert await sparr.sparrade_nummer(lager, a) == {"+46812345678", "+46701112233", "+46702223344"}
    assert ORGNR_B.replace("-", "") in await sparr.sparrade_orgnr(lager, a)
    svar = await sparr.ar_sparrad(lager, a, telefon="0701112233", kanal="telefon")
    assert svar["kallor"] == ["posten"] and svar["sparr_id"] == []
    assert not (await sparr.ar_sparrad(lager, a, epost="fri@annat.se", kanal="alla"))["sparrad"]
    assert await lagring.kontakta_inte_adresser(lager, b) == set()


# -- Städjobbet: papperskorgen töms utan en skrivning -------------------------


async def test_stadjobbets_systemlasning_och_tomning_i_databasen(miljo):
    """Den riktiga systemläsningen (`PostgresStorage.list_alla_tenant_ids`) ger
    bara kundernas id, även en pausad kunds, som appens roll utan kund satt.
    Frågan om något ska tömmas ställs sedan inom varje kunds radskydd: B:s
    fråga ser aldrig A:s rader."""
    from app.crm import stadning

    lager, a, b = miljo
    # Kund A pausas: dess papperskorg ska tömmas ändå.
    await lager.conn.execute("reset role")
    await lager.conn.execute("update ss_tenants set active = false where id = $1::text::uuid", a)
    await lager.conn.execute("set local role snajp_app")
    ids = await lager.list_alla_tenant_ids()
    assert {a, b} <= set(ids) and all(isinstance(i, str) for i in ids)
    # Med en kund satt släpper policyn bara igenom den kundens egen rad.
    async with lager._scoped(b) as conn:
        assert [str(r["id"]) for r in await conn.fetch("select id from ss_tenants")] == [b]

    gammal, _ = await synk.skapa(lager, a, "bolag", {"namn": "Gammal AB", "orgnr": ORGNR_A}, kalla="api")
    ung, _ = await synk.skapa(lager, b, "bolag", {"namn": "Ung AB", "orgnr": ORGNR_B}, kalla="api")
    uppgift = await lagring.skapa_post(lager, a, "uppgift", {"titel": "Ring tillbaka"})
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_bolag set raderad_at = now() - interval '31 days' where id = $1::text::uuid",
                           gammal["id"])
        await conn.execute("update crm_uppgifter set raderad_at = now() - interval '40 days' where id = $1::text::uuid",
                           uppgift["id"])
    async with lager._scoped(b) as conn:
        await conn.execute("update crm_bolag set raderad_at = now() - interval '29 days' where id = $1::text::uuid",
                           ung["id"])
        # Radskyddet: B:s anslutning ser inte A:s raderade bolag.
        assert await conn.fetchval("select count(*) from crm_bolag where raderad_at is not null") == 1

    assert await stadning.har_utgangna(lager, a) is True
    assert await stadning.har_utgangna(lager, b) is False
    assert await stadning.kunder_att_tomma(lager) == [a]

    assert await stadning.kor_varv(lager) == {"bolag": 1, "uppgift": 1}
    tomd = await lagring.hamta_post(lager, a, "bolag", gammal["id"], med_raderade=True)
    assert tomd["kalla"] == "gravsten" and tomd["namn"] == "" and tomd["orgnr"] is None
    assert (await lagring.hamta_post(lager, a, "uppgift", uppgift["id"], med_raderade=True))["titel"] == ""
    assert (await lagring.hamta_post(lager, b, "bolag", ung["id"], med_raderade=True))["namn"] == "Ung AB"
    assert await stadning.kunder_att_tomma(lager) == []

    # De begränsade sorteras bort i SQL:en, före taket på 200.
    begransad = await lagring.skapa_post(lager, a, "person", {"fornamn": "B", "epost": "b@x.se"})
    vanlig = await lagring.skapa_post(lager, a, "person", {"fornamn": "V", "epost": "v@x.se"})
    async with lager._scoped(a) as conn:
        await conn.execute("update crm_personer set raderad_at = now() - interval '31 days' "
                           "where id = any($1::text[]::uuid[])", [begransad["id"], vanlig["id"]])
    assert await lagring.tom_papperskorg(lager, a, "person", undanta={"B@x.se"}) == 1
    assert (await lagring.hamta_post(lager, a, "person", begransad["id"], med_raderade=True))["epost"] == "b@x.se"
    assert (await lagring.hamta_post(lager, a, "person", vanlig["id"], med_raderade=True))["epost"] is None


# -- Migration 167: registrets status på bolaget ------------------------------


async def test_registrets_status_och_berikningen_i_databasen(miljo):
    from app.api.crm_v1_berikning import berika
    from app.crm import scb

    lager, a, b = miljo
    bolag, _ = await synk.skapa(lager, a, "bolag", {"namn": "Berggren", "orgnr": ORGNR_A, "postort": "Solna"},
                                kalla="api")
    uppgifter = scb.tolka(ORGNR_A, {"namn": "Byggarna Berggren AB", "jurform": "49", "bolStat": "52", "ftgStat": "9",
                                    "postAdress": {"gatuAdress": "Storgatan 1", "postNr": "11122", "postOrt": "STOCKHOLM"},
                                    "naringsgrenar": [{"rangordning": 1, "naringsgren": "41200"}]})
    skriv, fyllda, hoppade = berika(bolag, uppgifter, overwrite=False)
    assert fyllda == ["bolagsform", "sni", "gatuadress", "postnr"] and hoppade == ["namn", "postort"]
    ny = await lagring.uppdatera_post(lager, a, "bolag", bolag["id"], skriv)
    assert ny["registerstatus"] == "deregistered" and ny["registret_last_at"]
    assert ny["bolagsform"] == "AB" and ny["sni"] == "41200" and ny["postnr"] == "111 22" and ny["postort"] == "Solna"
    # Bara de kända värdena tas emot.
    with pytest.raises(asyncpg.CheckViolationError):
        await lagring.uppdatera_post(lager, a, "bolag", bolag["id"], {"registerstatus": "kanske"})
    # Den andra kunden når inte raden.
    assert await lagring.uppdatera_post(lager, b, "bolag", bolag["id"], {"registerstatus": "active"}) is None
