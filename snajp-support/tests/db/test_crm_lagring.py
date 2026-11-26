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


class Lager:
    """Det av PostgresStorage som CRM-lagret använder, på EN anslutning, så att
    allt hamnar i testets transaktion."""

    pool = True

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn
        self._nycklar: dict = {}

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
