"""Fälten efter svensk standard och källsystemens mappningar.

Varje standardmappning provas mot en post i systemets egen form, så att en
ändring i en mappning syns här och inte först hos en kund.
"""

from __future__ import annotations

import pytest

from app.crm import adaptrar, falt

# -- Organisationsnummer -----------------------------------------------------


@pytest.mark.parametrize("skrivet", ["556036-0793", "5560360793", "16556036-0793", "165560360793",
                                     "SE556036079301", "se 556036-0793 01", " 556036 0793 "])
def test_orgnr_alla_skrivsatt_ger_samma_nyckel(skrivet):
    assert falt.orgnr(skrivet) == ("556036-0793", "5560360793", False)


def test_orgnr_enskild_firma_ar_personnummer_och_marks():
    # Tredje siffran under 2 är en månad: numret är ett personnummer.
    assert falt.orgnr("800101-1231") == ("800101-1231", "8001011231", True)
    assert falt.orgnr("19800101-1231") == ("800101-1231", "8001011231", True)


@pytest.mark.parametrize("skrivet,kod", [("556036-0794", "orgnr_kontrollsiffra"), ("55603607", "orgnr_fel_langd"),
                                         ("DE123456789", "orgnr_ogiltigt"), ("abc", "orgnr_ogiltigt")])
def test_orgnr_fel_har_en_kod(skrivet, kod):
    with pytest.raises(falt.FaltFel) as fel:
        falt.orgnr(skrivet)
    assert fel.value.kod == kod


def test_orgnr_tomt_ar_inget_fel():
    assert falt.orgnr(None) == (None, None, False)
    assert falt.orgnr("  ") == (None, None, False)


def test_momsnr():
    assert falt.momsnr("se556036079301") == "SE556036079301"
    assert falt.momsnr_ur_orgnr("5560360793") == "SE556036079301"
    assert falt.momsnr("DE 123 456 789") == "DE123456789"
    with pytest.raises(falt.FaltFel):
        falt.momsnr("SE556036079401")  # fel kontrollsiffra i orgnr-delen
    with pytest.raises(falt.FaltFel):
        falt.momsnr("SE5560360793")  # saknar 01


# -- Telefon, postnummer, tal, datum -----------------------------------------


@pytest.mark.parametrize("skrivet,e164", [
    ("070-123 45 67", "+46701234567"), ("08-123 456 78", "+46812345678"),
    ("+46 (0)70 123 45 67", "+46701234567"), ("0046 70 123 45 67", "+46701234567"),
    ("46701234567", "+46701234567"), ("+1 415 555 2671", "+14155552671"),
    ("070-123 45 67 / 08-12 34 56", "+46701234567"),
])
def test_telefon_blir_e164(skrivet, e164):
    assert falt.telefon(skrivet) == e164


def test_telefon_utan_riktnummer_sparas_inte():
    with pytest.raises(falt.FaltFel) as fel:
        falt.telefon("123 45 67")
    assert fel.value.kod == "telefon_saknar_riktnummer"


def test_postnummer():
    assert falt.postnr("11122") == "111 22"
    assert falt.postnr("SE-111 22") == "111 22"
    assert falt.postnr("0150", land="NO") == "0150"
    with pytest.raises(falt.FaltFel):
        falt.postnr("1112")


@pytest.mark.parametrize("skrivet,tal", [("1 234 567 kr", 1234567), ("1.234,50", 1235), ("1,234.00", 1234),
                                         ("12 000", 12000), (12000.0, 12000), ("45", 45)])
def test_heltal_svenska_och_engelska_skrivsatt(skrivet, tal):
    assert falt.heltal(skrivet) == tal


@pytest.mark.parametrize("skrivet", ["2026-12-31", "2026-12-31T10:00:00Z", "31/12/2026", "31.12.2026",
                                     "20261231", 1798675200000])
def test_datum_blir_iso(skrivet):
    assert falt.datum(skrivet) == "2026-12-31"


def test_webbplats_och_privata_domaner():
    assert falt.webbplats("www.Bolaget.se/om-oss") == ("https://www.Bolaget.se/om-oss", "bolaget.se")
    assert falt.doman_ar_privat("gmail.com") and falt.doman_ar_privat("telia.com")
    assert not falt.doman_ar_privat("bolaget.se")


def test_epost():
    assert falt.epost("Anna Berg <Anna@Bolaget.SE>") == "anna@bolaget.se"
    with pytest.raises(falt.FaltFel):
        falt.epost("anna(at)bolaget.se")


# -- Sökvägar och mappning ---------------------------------------------------


def test_sokvag_filter_index_och_skiftlage():
    post = {"addresses": [{"type": "Mail", "city": "Umeå"}, {"type": "Visit", "city": "Luleå"}],
            "Org.nr": "556036-0793"}
    assert adaptrar.las(post, "addresses[type=visit].city") == "Luleå"
    assert adaptrar.las(post, "addresses.0.city") == "Umeå"
    assert adaptrar.las(post, "addresses.7.city") is None
    assert adaptrar.las(post, "org_nr") == "556036-0793"
    assert adaptrar.las(post, "saknas.djupt.ner") is None


def test_ett_fel_falt_faller_inte_posten():
    m = adaptrar.mappa({"name": "Bolaget AB", "org_number": "556036-0794", "phone": "1234"},
                       "bolag", adaptrar.gallande_mappning("generisk", None))
    assert m.falt["namn"] == "Bolaget AB"
    assert "orgnr" not in m.falt and "telefon" not in m.falt
    assert {f["falt"] for f in m.fel} == {"orgnr", "telefon"}


def test_utlandskt_registreringsnummer_ar_inget_fel():
    m = adaptrar.mappa({"name": "Firma GmbH", "org_number": "HRB 12345", "country": "Tyskland"},
                       "bolag", adaptrar.gallande_mappning("generisk", None))
    assert m.fel == [] and m.falt["land"] == "DE" and "orgnr" not in m.falt


def test_kundens_mappning_laggs_ovanpa_standarden():
    egen = adaptrar.validera_mappning({"bolag": {"orgnr": "properties.swedish_org_no",
                                                 "extra": {"kundnummer": "properties.customer_no"}}})
    m = adaptrar.mappa({"id": "1", "properties": {"name": "Bolaget AB", "swedish_org_no": "5560360793",
                                                 "customer_no": "K-17", "industry": "Bygg"}},
                       "bolag", adaptrar.gallande_mappning("hubspot", egen))
    assert m.falt["orgnr"] == "556036-0793" and m.falt["namn"] == "Bolaget AB"
    # Bara uppräknade egna fält följer med: industry var inte beställt.
    assert m.extra == {"kundnummer": "K-17"}


@pytest.mark.parametrize("mappning", [{"foretag": {}}, {"bolag": {"finns_inte": "x"}}, {"bolag": {"namn": 7}},
                                      {"bolag": {"namn": {"okand": 1}}}, {"bolag": {"extra": ["a"]}}, "text"])
def test_ogiltig_mappning_avvisas(mappning):
    with pytest.raises(adaptrar.MappningsFel):
        adaptrar.validera_mappning(mappning)


# -- En post per källsystem --------------------------------------------------

_BOLAG = {
    "hubspot": {"id": "901", "updatedAt": "2026-11-20T08:00:00.000Z", "archived": False,
                "properties": {"name": "Byggarna Berggren AB", "orgnr": "556036-0793", "domain": "berggren.se",
                               "phone": "08-123 456 78", "zip": "11122", "city": "Stockholm",
                               "lifecyclestage": "customer", "numberofemployees": "12"}},
    "pipedrive": {"id": 901, "name": "Byggarna Berggren AB", "update_time": "2026-11-20T08:00:00Z",
                  "address": {"value": "Storgatan 1, Stockholm", "route": "Storgatan", "street_number": "1",
                              "postal_code": "11122", "locality": "Stockholm", "country": "Sweden"},
                  "is_deleted": False, "owner_id": 3},
    "lime": {"_id": 901, "name": "Byggarna Berggren AB", "registrationno": "556036-0793", "phone": "08-123 456 78",
             "www": "berggren.se", "visitingzipcode": "111 22", "visitingcity": "Stockholm",
             "buyingstatus": {"key": "active", "text": "Kund"}, "_timestamp": "2026-11-20T08:00:00Z"},
    "lime_go": {"id": "901", "name": "Byggarna Berggren AB", "registrationNumber": "556036-0793",
                "erpCustomerNumber": "K-17", "responsibleCoworker": "Henrik", "phone": "08-123 456 78",
                "webSite": "https://berggren.se", "relation": "IsACustomer",
                "visitingAddress": {"street": "Storgatan 1", "zipCode": "111 22", "city": "Stockholm", "countryCode": "SE"}},
    "upsales": {"id": 901, "name": "Byggarna Berggren AB", "orgNo": "5560360793", "phone": "08-123 456 78",
                "webpage": "berggren.se", "journeyStep": "customer", "active": 1,
                "addresses": [{"type": "Visit", "address": "Storgatan 1", "zipcode": "11122", "city": "Stockholm"}]},
    "salesforce": {"Id": "001A000001", "Name": "Byggarna Berggren AB", "Organization_Number__c": "556036-0793",
                   "Website": "berggren.se", "Phone": "08-123 456 78", "BillingPostalCode": "11122",
                   "BillingCity": "Stockholm", "Type": "Customer - Direct", "IsDeleted": False,
                   "LastModifiedDate": "2026-11-20T08:00:00.000+0000"},
    "twenty": {"id": "c-901", "name": "Byggarna Berggren AB", "orgnr": "556036-0793",
               "domainName": {"primaryLinkUrl": "https://berggren.se"}, "employees": 12, "deletedAt": None,
               "address": {"addressPostcode": "11122", "addressCity": "Stockholm"},
               "updatedAt": "2026-11-20T08:00:00.000Z"},
    "superoffice": {"ContactId": 901, "Name": "Byggarna Berggren AB", "OrgNr": "556036-0793",
                    "Urls": [{"Value": "berggren.se"}], "Phones": [{"Value": "08-123 456 78"}],
                    "Address": {"Street": {"Zipcode": "11122", "City": "Stockholm"}},
                    "Category": {"Value": "Customer"}, "UpdatedDate": "2026-11-20T08:00:00Z"},
    "dynamics": {"accountid": "a-901", "name": "Byggarna Berggren AB", "websiteurl": "berggren.se",
                 "telephone1": "08-123 456 78", "address1_postalcode": "11122", "address1_city": "Stockholm",
                 "customertypecode": 3, "statecode": 0, "modifiedon": "2026-11-20T08:00:00Z"},
    "fortnox": {"CustomerNumber": "901", "Name": "Byggarna Berggren AB", "OrganisationNumber": "556036-0793",
                "Phone1": "08-123 456 78", "ZipCode": "111 22", "City": "Stockholm", "Active": True, "Type": "COMPANY"},
    "visma": {"Id": "v-901", "Name": "Byggarna Berggren AB", "CorporateIdentityNumber": "5560360793",
              "Telephone": "08-123 456 78", "InvoicePostalCode": "11122", "InvoiceCity": "Stockholm",
              "IsActive": True, "IsPrivatePerson": False, "ChangedUtc": "2026-11-20T08:00:00Z"},
    "generisk": {"external_id": "901", "name": "Byggarna Berggren AB", "org_number": "556036-0793",
                 "address": {"postal_code": "11122", "city": "Stockholm"}, "relation": "customer"},
}


@pytest.mark.parametrize("system", adaptrar.SYSTEM)
def test_standardmappningen_for_varje_system(system):
    m = adaptrar.mappa(_BOLAG[system], "bolag", adaptrar.gallande_mappning(system, None))
    assert m.fel == [], m.fel
    assert m.externt_id and "901" in m.externt_id or system == "salesforce"
    assert m.falt["namn"] == "Byggarna Berggren AB"
    assert m.falt["postort"] == "Stockholm" and m.falt["postnr"] == "111 22"
    assert not m.raderad and not m.hoppa_over
    if system != "pipedrive" and system != "dynamics":  # där är orgnr ett eget fält hos kunden
        assert m.falt["orgnr_nyckel"] == "5560360793"
    if system not in ("pipedrive", "twenty"):
        assert m.falt.get("relation", "kund") == "kund"


def test_varje_system_har_en_mappning_och_bara_kanda_falt():
    assert set(adaptrar.STANDARD) == set(adaptrar.SYSTEM)
    for system in adaptrar.SYSTEM:
        # Standardmappningarna ska själva klara kontrollen kundens mappning går igenom.
        utan_stjarna = {o: {k: v for k, v in f.items() if k != "extra"} for o, f in adaptrar.STANDARD[system].items()}
        adaptrar.validera_mappning(utan_stjarna)


def test_pipedrive_bade_v1_och_v2_ger_gatuadressen():
    regler = adaptrar.gallande_mappning("pipedrive", None)
    assert adaptrar.mappa(_BOLAG["pipedrive"], "bolag", regler).falt["gatuadress"] == "Storgatan 1"
    v1 = {"id": 1, "name": "A AB", "address": "Storgatan 1, Stockholm", "address_route": "Storgatan",
          "address_postal_code": "11122", "address_locality": "Stockholm", "active_flag": True}
    m = adaptrar.mappa(v1, "bolag", regler)
    assert m.falt["gatuadress"] == "Storgatan" and m.falt["postort"] == "Stockholm" and not m.raderad


def test_lime_go_bar_affarssystemets_kundnummer_som_eget_falt():
    m = adaptrar.mappa(_BOLAG["lime_go"], "bolag", adaptrar.gallande_mappning("lime_go", None))
    assert m.extra == {"kundnummer_i_affarssystemet": "K-17"} and m.falt["ansvarig"] == "Henrik"


def test_privatpersoner_i_ekonomisystemen_marks_och_bar_inget_personnummer():
    """Mappningen märker posten; om den sparas avgör anslutningen (synk.py,
    tests/crm/test_beslut.py). Personnumret följer aldrig med, och posten
    står aldrig som kontaktbar."""
    regler = adaptrar.gallande_mappning("fortnox", None)
    m = adaptrar.mappa({"CustomerNumber": "1", "Name": "Anna Berg", "Type": "PRIVATE",
                        "OrganisationNumber": "19850101-2384", "VATNumber": "SE850101238401"}, "bolag", regler)
    assert m.falt["privatperson"] is True and m.falt["kontakta_inte"] is True and not m.hoppa_over
    assert not {"orgnr", "orgnr_nyckel", "momsnr", "enskild_firma"} & set(m.falt) and m.fel == []
    bolag = adaptrar.mappa({"CustomerNumber": "2", "Name": "Bolaget AB", "Type": "COMPANY"}, "bolag", regler)
    assert bolag.falt["privatperson"] is False and "kontakta_inte" not in bolag.falt
    assert adaptrar.mappa({"Id": "1", "Name": "Anna Berg", "IsPrivatePerson": True}, "bolag",
                          adaptrar.gallande_mappning("visma", None)).falt["privatperson"] is True


def test_inaktiv_i_kallan_ar_raderad():
    assert adaptrar.mappa({**_BOLAG["upsales"], "active": 0}, "bolag", adaptrar.gallande_mappning("upsales", None)).raderad
    assert adaptrar.mappa({**_BOLAG["pipedrive"], "active_flag": False}, "bolag",
                          adaptrar.gallande_mappning("pipedrive", None)).raderad
    assert adaptrar.mappa({**_BOLAG["twenty"], "deletedAt": "2026-11-21T00:00:00Z"}, "bolag",
                          adaptrar.gallande_mappning("twenty", None)).raderad


def test_personer_ur_pipedrive_och_twenty():
    pd = adaptrar.mappa({"id": 9, "name": "Anna Berg", "org_id": {"value": 901},
                         "emails": [{"value": "x@a.se", "primary": False}, {"value": "Anna@Berggren.se", "primary": True}],
                         "phones": [{"value": "070-123 45 67", "primary": True}]},
                        "person", adaptrar.gallande_mappning("pipedrive", None))
    assert pd.falt == {"fornamn": "Anna", "efternamn": "Berg", "epost": "anna@berggren.se",
                       "telefon": "+46701234567", "bolag_externt_id": "901"}
    tw = adaptrar.mappa({"id": "p1", "name": {"firstName": "Bo", "lastName": "Ek"}, "companyId": "c-901",
                         "emails": {"primaryEmail": "bo@berggren.se"},
                         "phones": {"primaryPhoneCallingCode": "+46", "primaryPhoneNumber": "701234567"}},
                        "person", adaptrar.gallande_mappning("twenty", None))
    assert tw.falt["telefon"] == "+46701234567" and tw.falt["bolag_externt_id"] == "c-901"


# -- CSV ---------------------------------------------------------------------


def test_csv_med_semikolon_och_svenska_rubriker():
    rader = adaptrar.tolka_csv(
        "﻿sep=;\nFöretag;Org.nr;E-post;Telefon;Postnummer;Ort;Avtalsslut\n"
        "Buddy Kund AB;556036-0793;info@kund.se;08-123 456 78;111 22;Stockholm;2027-03-31\n\n")
    assert len(rader) == 1
    m = adaptrar.mappa(rader[0], "bolag", adaptrar.gallande_mappning("generisk", None))
    assert m.fel == []
    assert m.falt["namn"] == "Buddy Kund AB" and m.falt["orgnr"] == "556036-0793"
    assert m.falt["epost"] == "info@kund.se" and m.falt["avtalsslut"] == "2027-03-31"


def test_felen_ur_researchens_prov_ar_rattade():
    """De fyra fel som provet i docs/crm/underlag/svensk-01 § 9.3 hittade."""
    # Anknytningen hör inte till numret.
    assert falt.telefon("08-678 55 00 ankn. 123") == "+4686785500"
    assert falt.telefon("08-678 55 00 ext 12") == "+4686785500" and falt.telefon("031-12 34 56 x 7") == "+46311234 56".replace(" ", "")
    # Excel har tappat mobilnumrets nolla.
    assert falt.telefon("701234567") == "+46701234567"
    with pytest.raises(falt.FaltFel):
        falt.telefon("12345678")                      # åtta siffror utan nolla är fortfarande inget nummer
    # Postnummerområdena 09 och 99 finns inte.
    for trasigt in ("091 00", "99100", "00123"):
        with pytest.raises(falt.FaltFel) as fel:
            falt.postnr(trasigt)
        assert fel.value.kod == "postnr_ogiltigt"
    assert falt.postnr("SE-113 91") == "113 91" and falt.postnr("98100") == "981 00"
    # Det typografiska minustecknet, och avrundning i stället för trunkering.
    assert falt.heltal("−1 234") == -1234 and falt.heltal("1 234,56 kr") == 1235
    assert falt.heltal("1 234,49") == 1234 and falt.heltal("1.234.567") == 1234567 and falt.heltal("-0,5") == -1


def test_bolagsformen_skrivs_som_svenska_system_skriver_den():
    for ra, vantat in [("Aktiebolag", "AB"), ("AB (publ)", "AB"), ("49", "AB"), ("Handelsbolag", "HB"),
                       ("kommanditbolag", "KB"), ("Enskild näringsidkare", "EF"), ("10", "EF"),
                       ("Ek. för.", "EK"), ("Bostadsrättsförening", "BRF"), ("Ideell förening", "Ideell förening"),
                       ("72", "Stiftelse"), ("Sole proprietorship", "EF")]:
        assert falt.bolagsform(ra) == vantat, ra
    # En form som inte är svensk är inget fel: den står som den skrevs.
    assert falt.bolagsform("GmbH") == "GmbH" and falt.bolagsform(" Ltd ") == "Ltd"
    assert falt.bolagsform("") is None and falt.bolagsform(None) is None


def test_sni_koder_utan_punkt_huvudnaringen_forst_hogst_fem():
    assert falt.sni("62.010") == "62010" and falt.sni("62 010") == "62010" and falt.sni(62010) == "62010"
    assert falt.sni("62.010, 62.020; 70220") == "62010,62020,70220"
    assert falt.sni("62010,62010") == "62010"                                   # samma kod en gång
    assert falt.sni("1;2;3".replace("1", "01").replace("2", "02").replace("3", "03")) == "01,02,03"
    assert falt.sni(",".join(str(41000 + i) for i in range(8))).count(",") == 4  # högst fem
    assert falt.sni("") is None
    for trasig in ("IT-konsult", "6", "620100", "62.01a"):
        with pytest.raises(falt.FaltFel) as fel:
            falt.sni(trasig)
        assert fel.value.kod == "sni_ogiltig"
    assert falt.sni_visning("62010") == "62.010" and falt.sni_visning("62") == "62" and falt.sni_visning(None) == ""


def test_mappningen_tolkar_bolagsform_och_sni_fran_kallan():
    regler = adaptrar.gallande_mappning("generisk", None)
    m = adaptrar.mappa({"name": "Bygg AB", "legal_form": "Aktiebolag", "sni_code": "41.200; 43.320"}, "bolag", regler)
    assert m.falt["bolagsform"] == "AB" and m.falt["sni"] == "41200,43320" and m.fel == []
    trasig = adaptrar.mappa({"name": "Bygg AB", "sni_code": "Byggverksamhet"}, "bolag", regler)
    assert "sni" not in trasig.falt and trasig.fel == [{"falt": "sni", "kod": "sni_ogiltig", "varde": "Byggverksamhet"}]


def test_csv_med_komma_och_for_manga_rader():
    assert adaptrar.tolka_csv("name,org_number\nA AB,556036-0793\n")[0] == {"name": "A AB", "org_number": "556036-0793"}
    with pytest.raises(adaptrar.MappningsFel):
        adaptrar.tolka_csv("name\n" + "A\n" * 6, max_rader=5)
