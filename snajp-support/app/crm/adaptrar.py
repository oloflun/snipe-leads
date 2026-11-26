"""Källsystemens format in till den kanoniska modellen.

Varje anslutning pekar ut ett system (HubSpot, Pipedrive, Lime, Upsales,
Salesforce, Twenty med flera, eller `generisk`) och får dess standardmappning.
Kunden kan lägga en egen mappning ovanpå, fält för fält: det som står i
anslutningens `mappning` går före standarden, resten ärvs.

## Mappningens form

    {"bolag":  {<målfält>: <källa>, ...},
     "person": {<målfält>: <källa>, ...}}

En källa är en av:

- en sökväg: `"properties.name"`
- en lista av sökvägar, där den första som har ett värde gäller
- ett objekt: `{"fran": <sökväg eller lista>, "uppslag": {...}, "standard": ...,
  "fast": ..., "sammanfoga": [<sökvägar>], "skilje": " "}`

Sökvägen går med punkt genom objekt och listor: `addresses.0.city`. En lista
kan filtreras på ett fält: `addresses[type=Visit].city`,
`emails[primary=true].value`. Nycklar jämförs utan hänsyn till skiftläge när
den exakta nyckeln saknas, så att en CSV-rubrik `Organisationsnummer` träffar.

Hur värdet tolkas avgörs av MÅLFÄLTET, inte av mappningen: `orgnr` går alltid
genom `falt.orgnr`, `telefon` alltid genom `falt.telefon`. Kunden kan alltså
peka om ett fält men inte stänga av kontrollen.

`extra` är kundens egna fält: `{"extra": {"bransch": "properties.industry"}}`.
Bara det som räknas upp följer med (dataminimering, beslut 2026-11-23).

Standardmappningarna är skrivna efter leverantörernas dokumentation och är
avsedda att justeras: organisationsnumret är ett eget fält i de flesta
utländska system, och heter olika hos varje kund.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any

from . import falt

SYSTEM = (
    "generisk", "hubspot", "pipedrive", "lime", "lime_go", "upsales", "salesforce",
    "twenty", "superoffice", "dynamics", "fortnox", "visma",
)
OBJEKT = ("bolag", "person")
RELATIONER = ("kund", "tidigare_kund", "prospekt", "partner", "leverantor", "ovrigt")
RATTSLIGA_GRUNDER = ("avtal", "berattigat_intresse", "samtycke")

#: Styrfält som inte lagras på posten.
_STYRFALT = ("externt_id", "uppdaterad", "raderad", "hoppa_over")

BOLAGSFALT = (
    "namn", "orgnr", "momsnr", "bolagsform", "sni", "webbplats", "epost", "telefon",
    "gatuadress", "co", "postnr", "postort", "land", "anstallda", "omsattning",
    "relation", "kund_sedan", "avtalsslut", "ansvarig", "kontakta_inte", "privatperson",
)
PERSONFALT = (
    "fornamn", "efternamn", "namn", "titel", "epost", "telefon", "mobil",
    "bolag_externt_id", "bolag_orgnr", "rattslig_grund", "kontakta_inte",
)
MALFALT = {"bolag": BOLAGSFALT, "person": PERSONFALT}

# -- Standardmappningar ------------------------------------------------------

_RELATION_ALLMAN = {
    "kund": "kund", "customer": "kund", "client": "kund", "aktiv": "kund", "active": "kund",
    "tidigare_kund": "tidigare_kund", "tidigare kund": "tidigare_kund",
    "former_customer": "tidigare_kund", "former customer": "tidigare_kund",
    "lost customer": "tidigare_kund", "churned": "tidigare_kund", "avslutad": "tidigare_kund",
    "prospekt": "prospekt", "prospect": "prospekt", "lead": "prospekt",
    "partner": "partner", "leverantor": "leverantor", "leverantör": "leverantor",
    "supplier": "leverantor", "vendor": "leverantor",
    "ovrigt": "ovrigt", "övrigt": "ovrigt", "other": "ovrigt",
}
_INTE_AKTIV = {"false": True, "0": True, "true": False, "1": False}

STANDARD: dict[str, dict[str, dict[str, Any]]] = {
    "generisk": {
        "bolag": {
            "externt_id": ["external_id", "externt_id", "id", "kundnummer", "customer_number"],
            "uppdaterad": ["updated_at", "uppdaterad", "modified", "andrad"],
            "raderad": ["deleted", "raderad", "archived"],
            "namn": ["name", "namn", "company_name", "company", "foretag", "företag",
                     "foretagsnamn", "företagsnamn", "bolagsnamn", "kundnamn", "kund"],
            "orgnr": ["org_number", "orgnr", "org_nr", "organisationsnummer",
                      "organization_number", "organisation_number", "registration_number"],
            "momsnr": ["vat_number", "momsnr", "momsregistreringsnummer", "vat"],
            "bolagsform": ["legal_form", "bolagsform"],
            "sni": ["sni_code", "sni", "sni_kod"],
            "webbplats": ["website", "webbplats", "hemsida", "url", "domain", "doman", "domän"],
            "epost": ["email", "epost", "e_post", "e_mail", "mejl"],
            "telefon": ["phone", "telefon", "telefonnummer", "tel"],
            "gatuadress": ["address.street", "street", "gatuadress", "adress", "address"],
            "co": ["address.co", "co", "c_o"],
            "postnr": ["address.postal_code", "postal_code", "postnr", "postnummer", "zip", "zipcode"],
            "postort": ["address.city", "city", "postort", "ort", "stad"],
            "land": ["address.country", "country", "land"],
            "anstallda": ["employees", "anstallda", "anställda", "antal_anstallda", "antal_anställda"],
            "omsattning": ["revenue_sek", "revenue", "omsattning", "omsättning"],
            "relation": {"fran": ["relation", "type", "typ", "status", "kundstatus"],
                         "uppslag": _RELATION_ALLMAN},
            "kund_sedan": ["customer_since", "kund_sedan"],
            "avtalsslut": ["contract_end", "avtalsslut", "avtal_slutar", "bindningstid_slut"],
            "ansvarig": ["owner", "ansvarig", "saljare", "säljare", "kundansvarig"],
            "kontakta_inte": ["do_not_contact", "kontakta_inte"],
            "privatperson": ["is_private_person", "private_person", "privatperson"],
            "extra": {"*": "custom"},
        },
        "person": {
            "externt_id": ["external_id", "externt_id", "id"],
            "uppdaterad": ["updated_at", "uppdaterad", "modified"],
            "raderad": ["deleted", "raderad", "archived"],
            "fornamn": ["first_name", "fornamn", "förnamn"],
            "efternamn": ["last_name", "efternamn"],
            "namn": ["name", "namn", "full_name", "kontaktperson"],
            "titel": ["title", "titel", "job_title", "befattning", "roll"],
            "epost": ["email", "epost", "e_post", "e_mail", "mejl"],
            "telefon": ["phone", "telefon", "direktnummer"],
            "mobil": ["mobile", "mobil", "mobiltelefon", "mobilnummer"],
            "bolag_externt_id": ["company_external_id", "company_id", "bolag_externt_id", "kundnummer"],
            "bolag_orgnr": ["company_org_number", "org_number", "orgnr", "organisationsnummer"],
            "rattslig_grund": ["legal_basis", "rattslig_grund"],
            "kontakta_inte": ["do_not_contact", "kontakta_inte"],
            "extra": {"*": "custom"},
        },
    },
    "hubspot": {
        "bolag": {
            "externt_id": "id",
            "uppdaterad": ["updatedAt", "properties.hs_lastmodifieddate"],
            "raderad": "archived",
            "namn": "properties.name",
            "orgnr": ["properties.orgnr", "properties.organisationsnummer", "properties.org_number",
                      "properties.organization_number", "properties.org_nr"],
            "momsnr": ["properties.vat_number", "properties.momsnr"],
            "webbplats": ["properties.website", "properties.domain"],
            "telefon": "properties.phone",
            "gatuadress": "properties.address",
            "co": "properties.address2",
            "postnr": "properties.zip",
            "postort": "properties.city",
            "land": "properties.country",
            "anstallda": "properties.numberofemployees",
            "omsattning": "properties.annualrevenue",
            "relation": {"fran": "properties.lifecyclestage", "uppslag": {
                "customer": "kund", "evangelist": "kund", "subscriber": "prospekt", "lead": "prospekt",
                "marketingqualifiedlead": "prospekt", "salesqualifiedlead": "prospekt",
                "opportunity": "prospekt", "other": "ovrigt"}},
            "ansvarig": "properties.hubspot_owner_id",
        },
        "person": {
            "externt_id": "id",
            "uppdaterad": ["updatedAt", "properties.lastmodifieddate"],
            "raderad": "archived",
            "fornamn": "properties.firstname",
            "efternamn": "properties.lastname",
            "titel": "properties.jobtitle",
            "epost": "properties.email",
            "telefon": "properties.phone",
            "mobil": "properties.mobilephone",
            "bolag_externt_id": "properties.associatedcompanyid",
            "kontakta_inte": "properties.hs_email_optout",
        },
    },
    "pipedrive": {
        "bolag": {
            "externt_id": "id",
            "uppdaterad": "update_time",
            "raderad": ["is_deleted", {"fran": "active_flag", "uppslag": _INTE_AKTIV}],
            "namn": "name",
            "webbplats": "website",
            # v2 har gatan och numret var för sig, v1 har dem som egna fält eller en rad.
            "gatuadress": [{"sammanfoga": ["address.route", "address.street_number"], "skilje": " "},
                           "address_route", "address.value", "address"],
            "postnr": ["address.postal_code", "address_postal_code"],
            "postort": ["address.locality", "address_locality"],
            "land": ["address.country", "address_country"],
            "ansvarig": ["owner_id.name", "owner_name", "owner_id"],
            "anstallda": "employee_count",
            "omsattning": "annual_revenue",
        },
        "person": {
            "externt_id": "id",
            "uppdaterad": "update_time",
            "raderad": ["is_deleted", {"fran": "active_flag", "uppslag": _INTE_AKTIV}],
            "fornamn": "first_name",
            "efternamn": "last_name",
            "namn": "name",
            "titel": "job_title",
            "epost": ["emails[primary=true].value", "email[primary=true].value",
                      "emails.0.value", "email.0.value", "primary_email"],
            "telefon": ["phones[primary=true].value", "phone[primary=true].value",
                        "phones.0.value", "phone.0.value"],
            "bolag_externt_id": ["org_id.value", "org_id"],
        },
    },
    "lime": {
        "bolag": {
            "externt_id": ["_id", "id"],
            "uppdaterad": "_timestamp",
            "namn": "name",
            "orgnr": ["registrationno", "corporateidentitynumber", "orgnr"],
            "momsnr": "vatno",
            "telefon": "phone",
            "webbplats": ["www", "website"],
            "epost": "email",
            "gatuadress": ["visitingaddress1", "postaladdress1"],
            "postnr": ["visitingzipcode", "postalzipcode"],
            "postort": ["visitingcity", "postalcity"],
            "land": "country",
            "relation": {"fran": ["buyingstatus.key", "buyingstatus"], "uppslag": {
                "active": "kund", "customer": "kund", "excustomer": "tidigare_kund",
                "prospect": "prospekt", "notinterested": "ovrigt", "declined": "ovrigt",
                "none": "ovrigt"}},
            "ansvarig": ["coworker.name", "coworker"],
        },
        "person": {
            "externt_id": ["_id", "id"],
            "uppdaterad": "_timestamp",
            "fornamn": "firstname",
            "efternamn": "lastname",
            "namn": "name",
            "titel": "position",
            "epost": "email",
            "telefon": "phone",
            "mobil": "mobilephone",
            "bolag_externt_id": ["company._id", "company.id", "company"],
        },
    },
    "lime_go": {
        "bolag": {
            "externt_id": "id",
            "namn": "name",
            "orgnr": "registrationNumber",
            "telefon": "phone",
            "epost": "email",
            "webbplats": "webSite",
            "gatuadress": ["visitingAddress.street", "postalAddress.street"],
            "postnr": ["visitingAddress.zipCode", "postalAddress.zipCode"],
            "postort": ["visitingAddress.city", "postalAddress.city"],
            "land": ["visitingAddress.countryCode", "postalAddress.countryCode"],
            # Vid läsning är relationen ett tal vars betydelse Lime inte dokumenterar;
            # namnen är de API:t tar emot vid skrivning. Kunden pekar om vid behov.
            "relation": {"fran": "relation", "uppslag": {
                "isacustomer": "kund", "wasacustomer": "tidigare_kund", "workingonit": "prospekt",
                "beenintouch": "prospekt", "norelation": "ovrigt"}},
            "ansvarig": "responsibleCoworker",
            "extra": {"kundnummer_i_affarssystemet": "erpCustomerNumber"},
        },
        "person": {},
    },
    "upsales": {
        "bolag": {
            "externt_id": "id",
            "uppdaterad": "modDate",
            "raderad": {"fran": "active", "uppslag": _INTE_AKTIV},
            "namn": "name",
            "orgnr": "orgNo",
            "telefon": "phone",
            "webbplats": "webpage",
            "sni": "sniCode",
            "gatuadress": ["addresses[type=Visit].address", "addresses[type=Mail].address",
                           "addresses.0.address"],
            "postnr": ["addresses[type=Visit].zipcode", "addresses[type=Mail].zipcode",
                       "addresses.0.zipcode"],
            "postort": ["addresses[type=Visit].city", "addresses[type=Mail].city", "addresses.0.city"],
            "land": ["addresses[type=Visit].country", "addresses[type=Mail].country",
                     "addresses.0.country"],
            "anstallda": "noEmployees",
            "omsattning": "turnover",
            "relation": {"fran": "journeyStep", "uppslag": {
                "customer": "kund", "lost_customer": "tidigare_kund", "lead": "prospekt",
                "mql": "prospekt", "assigned": "prospekt", "sql": "prospekt",
                "pipeline": "prospekt", "lost_opportunity": "prospekt", "disqualified": "ovrigt"}},
            "ansvarig": ["users.0.name", "users.0.id"],
        },
        "person": {
            "externt_id": "id",
            "uppdaterad": "modDate",
            "raderad": {"fran": "active", "uppslag": _INTE_AKTIV},
            "fornamn": "firstName",
            "efternamn": "lastName",
            "namn": "name",
            "titel": "title",
            "epost": "email",
            "telefon": "phone",
            "mobil": "cellPhone",
            "bolag_externt_id": ["client.id", "client"],
        },
    },
    "salesforce": {
        "bolag": {
            "externt_id": "Id",
            "uppdaterad": ["LastModifiedDate", "SystemModstamp"],
            "raderad": "IsDeleted",
            "namn": "Name",
            "orgnr": ["Organization_Number__c", "Organisationsnummer__c", "OrgNumber__c", "Org_nr__c"],
            "momsnr": ["VAT_Number__c", "VATNumber__c"],
            "webbplats": "Website",
            "telefon": "Phone",
            "gatuadress": ["BillingStreet", "BillingAddress.street", "ShippingStreet"],
            "postnr": ["BillingPostalCode", "BillingAddress.postalCode", "ShippingPostalCode"],
            "postort": ["BillingCity", "BillingAddress.city", "ShippingCity"],
            "land": ["BillingCountryCode", "BillingCountry", "BillingAddress.country"],
            "anstallda": "NumberOfEmployees",
            "omsattning": "AnnualRevenue",
            "relation": {"fran": "Type", "uppslag": {
                "customer": "kund", "customer - direct": "kund", "customer - channel": "kund",
                "prospect": "prospekt", "partner": "partner",
                "channel partner / reseller": "partner", "installation partner": "partner",
                "technology partner": "partner", "former customer": "tidigare_kund",
                "other": "ovrigt"}},
            "ansvarig": ["Owner.Name", "OwnerId"],
        },
        "person": {
            "externt_id": "Id",
            "uppdaterad": ["LastModifiedDate", "SystemModstamp"],
            "raderad": "IsDeleted",
            "fornamn": "FirstName",
            "efternamn": "LastName",
            "titel": "Title",
            "epost": "Email",
            "telefon": "Phone",
            "mobil": "MobilePhone",
            "bolag_externt_id": "AccountId",
            "kontakta_inte": "HasOptedOutOfEmail",
        },
    },
    "twenty": {
        "bolag": {
            "externt_id": "id",
            "uppdaterad": "updatedAt",
            "raderad": "deletedAt",
            "namn": "name",
            "orgnr": ["orgnr", "organisationsnummer", "orgNumber"],
            "webbplats": ["domainName.primaryLinkUrl", "domainName"],
            "gatuadress": "address.addressStreet1",
            "co": "address.addressStreet2",
            "postnr": "address.addressPostcode",
            "postort": "address.addressCity",
            "land": "address.addressCountry",
            "anstallda": "employees",
            "ansvarig": ["accountOwner.name.firstName", "accountOwnerId"],
        },
        "person": {
            "externt_id": "id",
            "uppdaterad": "updatedAt",
            "raderad": "deletedAt",
            "fornamn": "name.firstName",
            "efternamn": "name.lastName",
            "titel": "jobTitle",
            "epost": "emails.primaryEmail",
            "telefon": {"sammanfoga": ["phones.primaryPhoneCallingCode", "phones.primaryPhoneNumber"]},
            "bolag_externt_id": ["companyId", "company.id"],
        },
    },
    "superoffice": {
        "bolag": {
            "externt_id": "ContactId",
            "uppdaterad": "UpdatedDate",
            "namn": "Name",
            "orgnr": "OrgNr",
            "webbplats": "Urls.0.Value",
            "telefon": "Phones.0.Value",
            "epost": "Emails.0.Value",
            "gatuadress": ["Address.Street.Address1", "Address.Postal.Address1"],
            "postnr": ["Address.Street.Zipcode", "Address.Postal.Zipcode"],
            "postort": ["Address.Street.City", "Address.Postal.City"],
            "land": "Country.TwoLetterISOCountry",
            "raderad": "Deleted",
            "relation": {"fran": "Category.Value", "uppslag": {
                "customer": "kund", "kund": "kund", "a-customer": "kund", "b-customer": "kund",
                "lost customer": "tidigare_kund", "prospect": "prospekt", "potential customer": "prospekt",
                "partner": "partner", "supplier": "leverantor", "leverantör": "leverantor"}},
            "ansvarig": "Associate.FullName",
        },
        "person": {
            "externt_id": "PersonId",
            "uppdaterad": "UpdatedDate",
            "fornamn": "Firstname",
            "efternamn": "Lastname",
            "titel": "Title",
            "epost": "Emails.0.Value",
            "telefon": "OfficePhones.0.Value",
            "mobil": "MobilePhones.0.Value",
            "bolag_externt_id": "Contact.ContactId",
            "kontakta_inte": "NoMailing",
        },
    },
    "dynamics": {
        "bolag": {
            "externt_id": "accountid",
            "uppdaterad": "modifiedon",
            "raderad": {"fran": "statecode", "uppslag": {"1": True, "0": False}},
            "namn": "name",
            "webbplats": "websiteurl",
            "telefon": "telephone1",
            "epost": "emailaddress1",
            "gatuadress": "address1_line1",
            "co": "address1_line2",
            "postnr": "address1_postalcode",
            "postort": "address1_city",
            "land": "address1_country",
            "anstallda": "numberofemployees",
            "omsattning": "revenue",
            "relation": {"fran": "customertypecode", "uppslag": {
                "3": "kund", "8": "prospekt", "5": "partner", "9": "partner",
                "10": "leverantor", "11": "leverantor", "12": "ovrigt"}},
            "ansvarig": "_ownerid_value",
        },
        "person": {
            "externt_id": "contactid",
            "uppdaterad": "modifiedon",
            "raderad": {"fran": "statecode", "uppslag": {"1": True, "0": False}},
            "fornamn": "firstname",
            "efternamn": "lastname",
            "titel": "jobtitle",
            "epost": "emailaddress1",
            "telefon": "telephone1",
            "mobil": "mobilephone",
            "bolag_externt_id": "_parentcustomerid_value",
            "kontakta_inte": "donotemail",
        },
    },
    "fortnox": {
        "bolag": {
            "externt_id": "CustomerNumber",
            "raderad": {"fran": "Active", "uppslag": _INTE_AKTIV},
            # Privatkunder hoppas över om anslutningen inte slår på dem (synk.py).
            "privatperson": {"fran": "Type", "uppslag": {"private": True, "company": False}},
            "namn": "Name",
            "orgnr": "OrganisationNumber",
            "momsnr": "VATNumber",
            "epost": "Email",
            "telefon": ["Phone1", "Phone2"],
            "webbplats": "WWW",
            "gatuadress": "Address1",
            "co": "Address2",
            "postnr": "ZipCode",
            "postort": "City",
            "land": "CountryCode",
            "ansvarig": "OurReference",
            "relation": {"fast": "kund"},
        },
        "person": {},
    },
    "visma": {
        "bolag": {
            "externt_id": ["Id", "CustomerNumber"],
            "uppdaterad": "ChangedUtc",
            "raderad": {"fran": "IsActive", "uppslag": _INTE_AKTIV},
            "privatperson": "IsPrivatePerson",
            "namn": "Name",
            "orgnr": "CorporateIdentityNumber",
            "momsnr": "VatNumber",
            "epost": "EmailAddress",
            "telefon": ["Telephone", "MobilePhone"],
            "webbplats": "WwwAddress",
            "gatuadress": "InvoiceAddress1",
            "co": "InvoiceAddress2",
            "postnr": "InvoicePostalCode",
            "postort": "InvoiceCity",
            "land": "InvoiceCountryCode",
            "relation": {"fast": "kund"},
        },
        "person": {},
    },
}


class MappningsFel(ValueError):
    """Kundens mappning går inte att använda. Texten säger var."""


def validera_mappning(mappning: Any) -> dict[str, dict[str, Any]]:
    """En mappning ur API:t, kontrollerad till formen. Höjer `MappningsFel`."""
    if mappning in (None, {}):
        return {}
    if not isinstance(mappning, dict):
        raise MappningsFel("mappning ska vara ett objekt med nycklarna bolag och person.")
    ut: dict[str, dict[str, Any]] = {}
    for objekt, falten in mappning.items():
        if objekt not in OBJEKT:
            raise MappningsFel(f"okänt objekt {objekt!r}; välj bolag eller person.")
        if not isinstance(falten, dict):
            raise MappningsFel(f"{objekt} ska vara ett objekt med målfält som nycklar.")
        tillatna = set(MALFALT[objekt]) | set(_STYRFALT) | {"extra"}
        for mal, kalla in falten.items():
            if mal not in tillatna:
                raise MappningsFel(f"{objekt}.{mal} är inget fält. Fälten är: {', '.join(sorted(tillatna))}.")
            if mal == "extra":
                if not isinstance(kalla, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in kalla.items()
                ):
                    raise MappningsFel(f"{objekt}.extra ska vara ett objekt: eget fältnamn till sökväg.")
                if len(kalla) > 50:
                    raise MappningsFel(f"{objekt}.extra får ha högst 50 fält.")
                continue
            _validera_kalla(f"{objekt}.{mal}", kalla)
        ut[objekt] = falten
    return ut


def _validera_kalla(var: str, kalla: Any, *, djup: int = 0) -> None:
    if kalla is None or isinstance(kalla, str):
        return
    if isinstance(kalla, list) and djup == 0:
        for del_ in kalla:
            _validera_kalla(var, del_, djup=1)
        return
    if isinstance(kalla, dict):
        okanda = set(kalla) - {"fran", "uppslag", "standard", "fast", "sammanfoga", "skilje"}
        if okanda:
            raise MappningsFel(f"{var}: okända nycklar {sorted(okanda)}.")
        if "uppslag" in kalla and not isinstance(kalla["uppslag"], dict):
            raise MappningsFel(f"{var}: uppslag ska vara ett objekt.")
        return
    raise MappningsFel(f"{var}: en källa är en sökväg, en lista av sökvägar eller ett objekt.")


def gallande_mappning(system: str, egen: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Standardmappningen för systemet med kundens egen ovanpå, fält för fält."""
    grund = STANDARD.get(system) or STANDARD["generisk"]
    ut = {objekt: dict(grund.get(objekt) or {}) for objekt in OBJEKT}
    for objekt, falten in (egen or {}).items():
        if objekt not in ut:
            continue
        for mal, kalla in falten.items():
            if mal == "extra":
                ut[objekt]["extra"] = {**{k: v for k, v in (ut[objekt].get("extra") or {}).items() if k != "*"},
                                       **kalla}
            elif kalla is None:
                ut[objekt].pop(mal, None)
            else:
                ut[objekt][mal] = kalla
    return ut


# -- Sökvägar ----------------------------------------------------------------

_DEL = re.compile(r"^([^\[\]]*)(?:\[([^=\]]+)=([^\]]*)\])?$")
_SAKNAS = object()


def _nyckel(objekt: dict, namn: str) -> Any:
    if namn in objekt:
        return objekt[namn]
    lagt = namn.casefold()
    for k, v in objekt.items():
        if isinstance(k, str) and _rubrik(k) == lagt:
            return v
    return _SAKNAS


def _rubrik(namn: str) -> str:
    """`Org.nr`, `E-post` och `Antal anställda` blir `org_nr`, `e_post`, `antal_anställda`."""
    return re.sub(r"[\s.\-/]+", "_", namn.strip()).strip("_").casefold()


def las(post: Any, sokvag: str) -> Any:
    """Värdet på sökvägen, eller None. Kastar aldrig."""
    nu: Any = post
    for del_ in sokvag.split("."):
        traff = _DEL.match(del_)
        if not traff:
            return None
        namn, filterfalt, filtervarde = traff.groups()
        if namn:
            if isinstance(nu, list):
                if namn.isdigit():
                    nu = nu[int(namn)] if int(namn) < len(nu) else None
                else:
                    nu = next((p for p in nu if isinstance(p, dict)), None)
                    nu = _nyckel(nu, namn) if isinstance(nu, dict) else None
            elif isinstance(nu, dict):
                nu = _nyckel(nu, namn)
            else:
                return None
            if nu is _SAKNAS or nu is None:
                return None
        if filterfalt:
            if not isinstance(nu, list):
                return None
            nu = next(
                (p for p in nu if isinstance(p, dict)
                 and str(_nyckel(p, filterfalt)).casefold() == filtervarde.casefold()),
                None,
            )
            if nu is None:
                return None
    return nu


def _tomt(varde: Any) -> bool:
    return varde is None or varde == "" or varde == [] or varde == {}


def _los(post: Any, kalla: Any) -> Any:
    """Källans värde ur posten, eller None."""
    if kalla is None:
        return None
    if isinstance(kalla, str):
        varde = las(post, kalla)
        return None if _tomt(varde) else varde
    if isinstance(kalla, list):
        for del_ in kalla:
            varde = _los(post, del_)
            if not _tomt(varde):
                return varde
        return None
    if "fast" in kalla:
        return kalla["fast"]
    if "sammanfoga" in kalla:
        delar = [las(post, s) for s in kalla["sammanfoga"]]
        text = str(kalla.get("skilje") or "").join(
            str(d) for d in delar if not _tomt(d) and not isinstance(d, (dict, list)))
        varde: Any = text or None
    else:
        varde = _los(post, kalla.get("fran"))
    uppslag = kalla.get("uppslag")
    if uppslag is not None and not _tomt(varde) and not isinstance(varde, (dict, list)):
        nyckel = str(varde).strip().casefold()
        if isinstance(varde, bool):
            nyckel = "true" if varde else "false"
        traff = next((v for k, v in uppslag.items() if str(k).casefold() == nyckel), _SAKNAS)
        varde = None if traff is _SAKNAS else traff
    return kalla.get("standard") if _tomt(varde) else varde


def _sann(varde: Any) -> bool:
    """Ett ifyllt värde är sant om det inte uttryckligen säger nej. En
    tidpunkt i `deletedAt` betyder alltså raderad."""
    if isinstance(varde, str):
        return varde.strip().casefold() not in ("", "false", "0", "nej", "no", "n", "f", "null", "none")
    return bool(varde)


def _nagon_sann(post: Any, kalla: Any) -> bool:
    """För `raderad` och `hoppa_over`: det räcker att EN av källorna säger ja.
    Annars hade ett `is_deleted: false` dolt ett `active_flag: false` bredvid."""
    if isinstance(kalla, list):
        return any(_sann(_skalar(_los(post, del_))) for del_ in kalla)
    return _sann(_skalar(_los(post, kalla)))


# -- Mappning av en post -----------------------------------------------------


@dataclass
class Mappad:
    """En källpost tolkad till den kanoniska modellen."""

    falt: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    externt_id: str | None = None
    uppdaterad: str | None = None
    raderad: bool = False
    hoppa_over: bool = False
    #: Fält som inte gick att tolka: [{"falt", "kod", "varde"}]. Posten synkas ändå.
    fel: list[dict[str, Any]] = field(default_factory=list)


def _skalar(varde: Any) -> Any:
    """Ett objekt eller en lista är aldrig ett fältvärde."""
    return None if isinstance(varde, (dict, list)) else varde


def mappa(post: Any, objekt: str, mappning: dict[str, dict[str, Any]]) -> Mappad:
    """Tolkar en källpost. Kastar aldrig: fel hamnar i `Mappad.fel`."""
    ut = Mappad()
    if not isinstance(post, dict):
        ut.fel.append({"falt": "*", "kod": "post_inte_objekt"})
        ut.hoppa_over = True
        return ut
    regler = mappning.get(objekt) or {}

    eid = _skalar(_los(post, regler.get("externt_id")))
    ut.externt_id = falt.text(eid, max_langd=200)
    ut.raderad = _nagon_sann(post, regler.get("raderad"))
    ut.hoppa_over = _nagon_sann(post, regler.get("hoppa_over"))
    try:
        ut.uppdaterad = falt.tidpunkt(_skalar(_los(post, regler.get("uppdaterad"))))
    except falt.FaltFel:
        ut.uppdaterad = None

    ra = {mal: _skalar(_los(post, regler.get(mal))) for mal in MALFALT[objekt]}
    land = (falt.text(ra.get("land"), max_langd=60) or "SE") if objekt == "bolag" else "SE"
    land = _landskod(land)

    def satt(mal: str, tolk) -> None:
        if _tomt(ra.get(mal)):
            return
        try:
            varde = tolk(ra[mal])
        except falt.FaltFel as fel:
            ut.fel.append({"falt": mal, "kod": fel.kod, "varde": str(fel.varde)[:80]})
            return
        if varde is not None:
            ut.falt[mal] = varde

    if objekt == "bolag":
        # Landet skrivs bara när källan anger det; annars gäller postens eget
        # (Sverige för en ny post). Tolkningen av telefon och postnummer
        # utgår ändå från Sverige.
        if not _tomt(ra.get("land")):
            ut.falt["land"] = land
        satt("namn", lambda v: falt.text(v, max_langd=300))
        # Källan säger att kunden är en privatperson. Synken avgör sedan om
        # posten sparas alls (anslutningens `privatpersoner`). Numret är då ett
        # personnummer och sparas aldrig, och posten är ingen enskild firma.
        privat = not _tomt(ra.get("privatperson")) and _sann(ra["privatperson"])
        if not _tomt(ra.get("privatperson")):
            ut.falt["privatperson"] = privat
        if privat:
            ra["orgnr"] = ra["momsnr"] = None
        if not _tomt(ra.get("orgnr")):
            try:
                visning, nyckel, enskild = falt.orgnr(ra["orgnr"])
            except falt.FaltFel as fel:
                # Ett utländskt bolags registreringsnummer är inget fel, bara inget svenskt orgnr.
                # Värdet sparas inte i felloggen: ett felskrivet nummer kan vara ett personnummer.
                if land == "SE":
                    ut.fel.append({"falt": "orgnr", "kod": fel.kod})
            else:
                if enskild:
                    # En enskild firmas organisationsnummer är ägarens personnummer, och
                    # personnummer sparas inte (docs/BESLUT.md 2026-11-23). Bolaget märks
                    # som enskild firma och känns igen på domän eller namn i stället.
                    ut.falt["enskild_firma"] = True
                    ut.fel.append({"falt": "orgnr", "kod": "orgnr_ar_personnummer", "varde": "(sparas inte)"})
                else:
                    ut.falt.update(orgnr=visning, orgnr_nyckel=nyckel, enskild_firma=False)
        satt("momsnr", falt.momsnr)
        satt("bolagsform", lambda v: falt.text(v, max_langd=60))
        satt("sni", lambda v: falt.text(v, max_langd=20))
        if not _tomt(ra.get("webbplats")):
            try:
                url, doman = falt.webbplats(ra["webbplats"])
            except falt.FaltFel as fel:
                ut.fel.append({"falt": "webbplats", "kod": fel.kod, "varde": str(fel.varde)[:80]})
            else:
                ut.falt.update(webbplats=url, doman=doman)
        satt("epost", falt.epost)
        satt("telefon", lambda v: falt.telefon(v, land=land))
        satt("gatuadress", lambda v: falt.text(v, max_langd=300))
        satt("co", lambda v: falt.text(v, max_langd=200))
        satt("postnr", lambda v: falt.postnr(v, land=land))
        satt("postort", lambda v: falt.text(v, max_langd=120))
        satt("anstallda", falt.heltal)
        satt("omsattning", falt.heltal)
        satt("relation", _relation)
        satt("kund_sedan", falt.datum)
        satt("avtalsslut", falt.datum)
        satt("ansvarig", lambda v: falt.text(v, max_langd=200))
    else:
        satt("fornamn", lambda v: falt.text(v, max_langd=120))
        satt("efternamn", lambda v: falt.text(v, max_langd=120))
        if "fornamn" not in ut.falt and "efternamn" not in ut.falt and not _tomt(ra.get("namn")):
            namn = falt.text(ra["namn"], max_langd=240) or ""
            forst, _, sist = namn.partition(" ")
            ut.falt["fornamn"] = forst
            if sist:
                ut.falt["efternamn"] = sist
        satt("titel", lambda v: falt.text(v, max_langd=200))
        satt("epost", falt.epost)
        satt("telefon", falt.telefon)
        satt("mobil", falt.telefon)
        satt("rattslig_grund", _rattslig_grund)
        satt("bolag_externt_id", lambda v: falt.text(v, max_langd=200))
        if not _tomt(ra.get("bolag_orgnr")):
            try:
                ut.falt["bolag_orgnr_nyckel"] = falt.orgnr(ra["bolag_orgnr"])[1]
            except falt.FaltFel:
                pass
    if not _tomt(ra.get("kontakta_inte")):
        ut.falt["kontakta_inte"] = _sann(ra["kontakta_inte"])
    if ut.falt.get("privatperson"):
        # En privatperson står aldrig som kontaktbar (migration 161).
        ut.falt["kontakta_inte"] = True

    for namn, sokvag in (regler.get("extra") or {}).items():
        varde = las(post, sokvag)
        if namn == "*":
            # Hela objektet på sökvägen, bara skalära värden och högst 50 fält.
            if isinstance(varde, dict):
                for k, v in list(varde.items())[:50]:
                    if isinstance(k, str) and not isinstance(v, (dict, list)) and not _tomt(v):
                        ut.extra[k[:60]] = v if isinstance(v, (int, float, bool)) else str(v)[:500]
        elif not _tomt(varde) and not isinstance(varde, (dict, list)):
            ut.extra[namn[:60]] = varde if isinstance(varde, (int, float, bool)) else str(varde)[:500]
    return ut


def _relation(varde: Any) -> str:
    nyckel = str(varde).strip().casefold()
    traff = _RELATION_ALLMAN.get(nyckel) or (nyckel if nyckel in RELATIONER else None)
    if not traff:
        raise falt.FaltFel("relation_okand", varde)
    return traff


def _rattslig_grund(varde: Any) -> str:
    nyckel = str(varde).strip().casefold().replace(" ", "_")
    nyckel = {"contract": "avtal", "legitimate_interest": "berattigat_intresse",
              "berättigat_intresse": "berattigat_intresse", "consent": "samtycke"}.get(nyckel, nyckel)
    if nyckel not in RATTSLIGA_GRUNDER:
        raise falt.FaltFel("rattslig_grund_okand", varde)
    return nyckel


_LANDER = {
    "sverige": "SE", "sweden": "SE", "se": "SE", "swe": "SE",
    "norge": "NO", "norway": "NO", "danmark": "DK", "denmark": "DK",
    "finland": "FI", "suomi": "FI", "tyskland": "DE", "germany": "DE",
    "storbritannien": "GB", "united kingdom": "GB", "uk": "GB",
    "usa": "US", "united states": "US",
}


def _landskod(land: str) -> str:
    ren = land.strip()
    if len(ren) == 2 and ren.isalpha():
        return ren.upper()
    return _LANDER.get(ren.casefold(), ren[:60])


# -- CSV ---------------------------------------------------------------------


def tolka_csv(text: str, *, max_rader: int = 5000) -> list[dict[str, str]]:
    """En CSV-kropp till poster med rubrikraden som nycklar.

    Skiljetecknet gissas mellan semikolon, komma och tabb (svensk Excel skriver
    semikolon). `sep=;` på första raden respekteras. Rubrikerna normaliseras
    som i `_rubrik`, så att `Org.nr` och `org_nr` är samma kolumn.
    """
    text = text.lstrip("﻿")
    forsta, _, resten = text.partition("\n")
    skilje = None
    if forsta.strip().lower().startswith("sep=") and len(forsta.strip()) == 5:
        skilje, text = forsta.strip()[4], resten
        forsta = text.partition("\n")[0]
    if skilje is None:
        skilje = max(";,\t", key=forsta.count)
    lasare = csv.reader(io.StringIO(text), delimiter=skilje)
    rubriker = [_rubrik(r) for r in next(lasare, [])]
    ut: list[dict[str, str]] = []
    for rad in lasare:
        if not any(cell.strip() for cell in rad):
            continue
        if len(ut) >= max_rader:
            raise MappningsFel(f"Filen har fler än {max_rader} rader. Dela upp den.")
        ut.append({r: (rad[i].strip() if i < len(rad) else "") for i, r in enumerate(rubriker) if r})
    return ut
