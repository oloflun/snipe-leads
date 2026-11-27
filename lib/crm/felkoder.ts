/**
 * Synkens koder i klartext, på båda språken.
 *
 * API:t svarar med koder (docs/crm/API.md räknar upp dem), eftersom den som
 * integrerar ska kunna grena på dem. Appen visar dem för en människa och
 * översätter dem därför här. En kod som saknas i tabellen visas som den är:
 * hellre en rå kod än en gissad förklaring.
 */
import type { Localized } from "@/lib/i18n";

/** Varför en hel post hoppades över eller krockade (`orsak`). */
export const ORSAKER: Record<string, Localized> = {
  hoppas_over_enligt_mappningen: { sv: "Hoppas över enligt mappningen.", en: "Skipped by the mapping." },
  orgnr_tillhor_annat_bolag: { sv: "Organisationsnumret tillhör redan ett annat bolag.", en: "The organisation number already belongs to another company." },
  behandlingen_ar_begransad: { sv: "Behandlingen är begränsad för adressen (art. 18). Posten rörs inte.", en: "Processing is restricted for this address (Art. 18). The record is left alone." },
  saknar_namn: { sv: "Bolaget saknar namn.", en: "The company has no name." },
  saknar_namn_och_epost: { sv: "Personen saknar både namn och e-post.", en: "The person has neither a name nor an email." },
  finns_redan: { sv: "En annan post har redan samma nyckel.", en: "Another record already has the same key." },
  privatperson: {
    sv: "Källan märker posten som privatperson. Anslutningen synkar inte privatpersoner.",
    en: "The source marks the record as a private person. The connection does not sync private persons."
  },
  redan_borta: { sv: "Posten var redan borttagen i Snajp.", en: "The record was already removed in Snajp." }
};

/**
 * Skäl där posten hoppades över med flit, inte av ett fel: privatpersoner,
 * mappningens egna undantag och poster som redan var borta. Samma lista som
 * `MED_FLIT` i snajp-support/app/crm/supportrapport.py. De räknas inte som
 * poster att rätta och går inte vidare till supporten.
 */
export const MED_FLIT = ["privatperson", "hoppas_over_enligt_mappningen", "redan_borta"];

/** En rad i körningens fel som någon behöver rätta: allt utom det som hoppats över med flit. */
export const arFel = (f: { orsak?: string; faltfel?: unknown[] }) => (f.faltfel?.length ?? 0) > 0 || !MED_FLIT.includes(f.orsak ?? "");

/**
 * Poster att rätta i en körning: felraderna, och hoppade poster utöver alla
 * sparade rader (de som synken inte sparade ett skäl för). Samma tal i Synk,
 * översikten och navigeringens kort.
 */
export function attRatta(k: { errors: { orsak?: string; faltfel?: unknown[] }[]; counts: { skipped: number } }): number {
  return k.errors.filter(arFel).length + Math.max(0, k.counts.skipped - k.errors.length);
}

// ---------------------------------------------------------------------------
// Fälten i klartext
// ---------------------------------------------------------------------------

/**
 * API:ts fältnamn med etiketten panelen använder (`etikett`), ordet utan
 * artikel (`naken`, "saknar namn") och med obestämd artikel (`obest`, "har ett
 * telefonnummer som inte gick att läsa"). Historiken och synkens enkla meningar
 * läser härifrån, så att samma fält heter samma sak överallt.
 */
type Faltord = { etikett: Localized; naken: Localized; obest: Localized };

export const FALT: Record<string, Faltord> = {
  name: { etikett: { sv: "Namn", en: "Name" }, naken: { sv: "namn", en: "name" }, obest: { sv: "ett namn", en: "a name" } },
  org_number: {
    etikett: { sv: "Org.nr", en: "Org. no." },
    naken: { sv: "organisationsnummer", en: "organisation number" },
    obest: { sv: "ett organisationsnummer", en: "an organisation number" }
  },
  vat_number: { etikett: { sv: "Momsnummer", en: "VAT number" }, naken: { sv: "momsnummer", en: "VAT number" }, obest: { sv: "ett momsnummer", en: "a VAT number" } },
  legal_form: { etikett: { sv: "Bolagsform", en: "Legal form" }, naken: { sv: "bolagsform", en: "legal form" }, obest: { sv: "en bolagsform", en: "a legal form" } },
  sni_code: { etikett: { sv: "SNI-kod", en: "SNI code" }, naken: { sv: "SNI-kod", en: "SNI code" }, obest: { sv: "en SNI-kod", en: "an SNI code" } },
  website: { etikett: { sv: "Webbplats", en: "Website" }, naken: { sv: "webbplats", en: "website" }, obest: { sv: "en webbadress", en: "a web address" } },
  email: { etikett: { sv: "E-post", en: "Email" }, naken: { sv: "e-post", en: "email" }, obest: { sv: "en e-postadress", en: "an email address" } },
  phone: { etikett: { sv: "Telefon", en: "Phone" }, naken: { sv: "telefonnummer", en: "phone number" }, obest: { sv: "ett telefonnummer", en: "a phone number" } },
  mobile: { etikett: { sv: "Mobil", en: "Mobile" }, naken: { sv: "mobilnummer", en: "mobile number" }, obest: { sv: "ett mobilnummer", en: "a mobile number" } },
  employees: { etikett: { sv: "Anställda", en: "Employees" }, naken: { sv: "antal anställda", en: "number of employees" }, obest: { sv: "ett antal anställda", en: "a number of employees" } },
  revenue_sek: { etikett: { sv: "Omsättning", en: "Revenue" }, naken: { sv: "omsättning", en: "revenue" }, obest: { sv: "en omsättning", en: "a revenue figure" } },
  relation: { etikett: { sv: "Relation", en: "Relation" }, naken: { sv: "relation", en: "relation" }, obest: { sv: "en relation", en: "a relation" } },
  customer_since: { etikett: { sv: "Kund sedan", en: "Customer since" }, naken: { sv: "kunddatum", en: "customer date" }, obest: { sv: "ett kunddatum", en: "a customer date" } },
  contract_end: { etikett: { sv: "Avtalsslut", en: "Contract end" }, naken: { sv: "avtalsslut", en: "contract end" }, obest: { sv: "ett avtalsslut", en: "a contract end date" } },
  owner: { etikett: { sv: "Ansvarig", en: "Owner" }, naken: { sv: "ansvarig", en: "owner" }, obest: { sv: "en ansvarig", en: "an owner" } },
  do_not_contact: { etikett: { sv: "Kontakta inte", en: "Do not contact" }, naken: { sv: "kontaktspärr", en: "contact block" }, obest: { sv: "en kontaktspärr", en: "a contact block" } },
  private_person: { etikett: { sv: "Privatperson", en: "Private person" }, naken: { sv: "privatpersonsmärkning", en: "private person flag" }, obest: { sv: "en privatpersonsmärkning", en: "a private person flag" } },
  "address.street": { etikett: { sv: "Gatuadress", en: "Street address" }, naken: { sv: "gatuadress", en: "street address" }, obest: { sv: "en gatuadress", en: "a street address" } },
  "address.co": { etikett: { sv: "c/o", en: "c/o" }, naken: { sv: "c/o-rad", en: "c/o line" }, obest: { sv: "en c/o-rad", en: "a c/o line" } },
  "address.postal_code": { etikett: { sv: "Postnummer", en: "Postal code" }, naken: { sv: "postnummer", en: "postal code" }, obest: { sv: "ett postnummer", en: "a postal code" } },
  "address.city": { etikett: { sv: "Ort", en: "City" }, naken: { sv: "ort", en: "city" }, obest: { sv: "en ort", en: "a city" } },
  "address.country": { etikett: { sv: "Land", en: "Country" }, naken: { sv: "land", en: "country" }, obest: { sv: "ett land", en: "a country" } },
  first_name: { etikett: { sv: "Förnamn", en: "First name" }, naken: { sv: "förnamn", en: "first name" }, obest: { sv: "ett förnamn", en: "a first name" } },
  last_name: { etikett: { sv: "Efternamn", en: "Last name" }, naken: { sv: "efternamn", en: "last name" }, obest: { sv: "ett efternamn", en: "a last name" } },
  title: { etikett: { sv: "Titel", en: "Title" }, naken: { sv: "titel", en: "title" }, obest: { sv: "en titel", en: "a title" } },
  company_id: { etikett: { sv: "Bolag", en: "Company" }, naken: { sv: "bolag", en: "company" }, obest: { sv: "en bolagskoppling", en: "a company link" } },
  legal_basis: { etikett: { sv: "Rättslig grund", en: "Legal basis" }, naken: { sv: "rättslig grund", en: "legal basis" }, obest: { sv: "en rättslig grund", en: "a legal basis" } },
  custom: { etikett: { sv: "Egna fält", en: "Custom fields" }, naken: { sv: "egna fält", en: "custom fields" }, obest: { sv: "ett eget fält", en: "a custom field" } },
  // Affärens fält (historiken i affärens panel).
  stage_id: { etikett: { sv: "Steg", en: "Stage" }, naken: { sv: "steg", en: "stage" }, obest: { sv: "ett steg", en: "a stage" } },
  amount: { etikett: { sv: "Belopp", en: "Amount" }, naken: { sv: "belopp", en: "amount" }, obest: { sv: "ett belopp", en: "an amount" } },
  currency: { etikett: { sv: "Valuta", en: "Currency" }, naken: { sv: "valuta", en: "currency" }, obest: { sv: "en valuta", en: "a currency" } },
  probability: { etikett: { sv: "Sannolikhet", en: "Probability" }, naken: { sv: "sannolikhet", en: "probability" }, obest: { sv: "en sannolikhet", en: "a probability" } },
  expected_close_date: { etikett: { sv: "Väntat avslut", en: "Expected close" }, naken: { sv: "väntat avslut", en: "expected close" }, obest: { sv: "ett väntat avslut", en: "an expected close date" } },
  closed_at: { etikett: { sv: "Avslutad", en: "Closed" }, naken: { sv: "avslutsdag", en: "close date" }, obest: { sv: "en avslutsdag", en: "a close date" } },
  lost_reason: { etikett: { sv: "Kommentar om förlusten", en: "Comment on the loss" }, naken: { sv: "kommentar om förlusten", en: "comment on the loss" }, obest: { sv: "en kommentar om förlusten", en: "a comment on the loss" } },
  lost_reason_code: { etikett: { sv: "Förlustorsak", en: "Lost reason" }, naken: { sv: "förlustorsak", en: "lost reason" }, obest: { sv: "en förlustorsak", en: "a lost reason" } },
  // Personens källa (GDPR artikel 14).
  source_type: { etikett: { sv: "Uppgifternas källa", en: "Source of the details" }, naken: { sv: "uppgifternas källa", en: "source of the details" }, obest: { sv: "en källa", en: "a source" } },
  source_name: { etikett: { sv: "Källans namn", en: "Name of the source" }, naken: { sv: "källans namn", en: "name of the source" }, obest: { sv: "ett namn på källan", en: "a name for the source" } },
  collected_at: { etikett: { sv: "Insamlad", en: "Collected" }, naken: { sv: "insamlingsdag", en: "collection date" }, obest: { sv: "en insamlingsdag", en: "a collection date" } },
  person_id: { etikett: { sv: "Person", en: "Person" }, naken: { sv: "person", en: "person" }, obest: { sv: "en personkoppling", en: "a person link" } },
  position: { etikett: { sv: "Plats på tavlan", en: "Place on the board" }, naken: { sv: "plats på tavlan", en: "place on the board" }, obest: { sv: "en plats på tavlan", en: "a place on the board" } }
};

/** Ett fälts etikett, eller fältnamnet som det står när tabellen saknar det. */
export const faltetikett = (falt: string): Localized => FALT[falt]?.etikett ?? { sv: falt, en: falt };

/** "Telefon", "Telefon och Ort", "Telefon, Ort och E-post". */
export function uppraknat(delar: string[], och: string): string {
  if (delar.length <= 1) return delar.join("");
  return `${delar.slice(0, -1).join(", ")} ${och} ${delar[delar.length - 1]}`;
}

// ---------------------------------------------------------------------------
// Synkens fel i enkla ord (kundens nivå)
// ---------------------------------------------------------------------------

/** Objektets namn i en mening, i ental och flertal. */
const OBJEKTORD: Record<string, { en1: Localized; flera: Localized }> = {
  company: { en1: { sv: "bolag", en: "company" }, flera: { sv: "bolag", en: "companies" } },
  person: { en1: { sv: "person", en: "person" }, flera: { sv: "personer", en: "people" } }
};

/** Sorter som är upplysning, inte fel: de står för sig, under felen. */
export const UPPLYSNING = ["privatperson", "undantagen", "redan_borta"];

type Fraga = { kind: string; object: string; field: string | null; count: number };

/**
 * En rad ur körningens `issues` som en kort mening på båda språken, utan
 * koder, radnummer eller källans id. `n` är talet som läsaren ska se
 * (formaterat på sitt språk av den som anropar).
 */
export function enkelMening(f: Fraga, n: { sv: string; en: string }): Localized {
  const ett = f.count === 1;
  const ord = OBJEKTORD[f.object] ?? OBJEKTORD.company;
  const obj = ett ? ord.en1 : ord.flera;
  const person = f.object === "person";
  const har = ett ? "has" : "have";
  const falt = f.field ? FALT[f.field] : undefined;
  switch (f.kind) {
    case "ogiltigt_varde": {
      const v = falt ? falt.obest : { sv: "ett värde", en: "a value" };
      return { sv: `${n.sv} ${obj.sv} har ${v.sv} som inte gick att läsa`, en: `${n.en} ${obj.en} ${har} ${v.en} that could not be read` };
    }
    case "saknar_uppgift": {
      if (!falt) {
        return person
          ? { sv: `${n.sv} ${obj.sv} saknar både namn och e-post`, en: `${n.en} ${obj.en} ${har} neither a name nor an email` }
          : { sv: `${n.sv} ${obj.sv} saknar namn`, en: `${n.en} ${obj.en} ${har} no name` };
      }
      return { sv: `${n.sv} ${obj.sv} saknar ${falt.naken.sv}`, en: `${n.en} ${obj.en} ${har} no ${falt.naken.en}` };
    }
    case "dubblett":
      return person
        ? { sv: `${n.sv} ${obj.sv} finns redan med samma e-postadress`, en: ett ? `${n.en} ${obj.en} already exists with the same email address` : `${n.en} ${obj.en} already exist with the same email address` }
        : { sv: `${n.sv} ${obj.sv} finns redan under ett annat nummer`, en: ett ? `${n.en} ${obj.en} already exists under another number` : `${n.en} ${obj.en} already exist under another number` };
    case "begransad":
      return person
        ? {
            sv: `${n.sv} ${obj.sv} har begärt begränsad behandling och rördes inte`,
            en: ett ? `${n.en} ${obj.en} has asked for restricted processing and was left alone` : `${n.en} ${obj.en} have asked for restricted processing and were left alone`
          }
        : {
            sv: `${n.sv} ${obj.sv} har begränsad behandling och rördes inte`,
            en: ett ? `${n.en} ${obj.en} has restricted processing and was left alone` : `${n.en} ${obj.en} have restricted processing and were left alone`
          };
    case "privatperson":
      return ett
        ? { sv: `${n.sv} privatperson hoppades över`, en: `${n.en} private person was skipped` }
        : { sv: `${n.sv} privatpersoner hoppades över`, en: `${n.en} private persons were skipped` };
    case "undantagen":
      return {
        sv: `${n.sv} ${obj.sv} hoppades över enligt anslutningens mappning`,
        en: ett ? `${n.en} ${obj.en} was skipped by the connection's mapping` : `${n.en} ${obj.en} were skipped by the connection's mapping`
      };
    case "redan_borta":
      return person
        ? {
            sv: ett ? `${n.sv} ${obj.sv} var redan borttagen` : `${n.sv} ${obj.sv} var redan borttagna`,
            en: ett ? `${n.en} ${obj.en} was already removed` : `${n.en} ${obj.en} were already removed`
          }
        : {
            sv: ett ? `${n.sv} ${obj.sv} var redan borttaget` : `${n.sv} ${obj.sv} var redan borttagna`,
            en: ett ? `${n.en} ${obj.en} was already removed` : `${n.en} ${obj.en} were already removed`
          };
    default:
      return { sv: `${n.sv} ${obj.sv} kom inte in av ett annat skäl`, en: `${n.en} ${obj.en} did not come in for another reason` };
  }
}

/** Vad som var fel på ett enskilt fält (`faltfel[].kod`). */
export const FALTKODER: Record<string, Localized> = {
  saknas: { sv: "Fältet saknas.", en: "The field is missing." },
  orgnr_ogiltigt: { sv: "Organisationsnumret går inte att läsa.", en: "The organisation number cannot be read." },
  orgnr_fel_langd: { sv: "Organisationsnumret ska ha tio siffror.", en: "The organisation number must have ten digits." },
  orgnr_kontrollsiffra: { sv: "Organisationsnumrets kontrollsiffra stämmer inte.", en: "The check digit of the organisation number is wrong." },
  orgnr_ar_personnummer: { sv: "Numret är ett personnummer och sparas inte.", en: "The number is a personal identity number and is not stored." },
  momsnr_ogiltigt: { sv: "Momsregistreringsnumret är ogiltigt.", en: "The VAT number is invalid." },
  telefon_ogiltig: { sv: "Telefonnumret går inte att läsa.", en: "The phone number cannot be read." },
  telefon_saknar_riktnummer: { sv: "Telefonnumret saknar riktnummer.", en: "The phone number has no area code." },
  telefon_saknar_landskod: { sv: "Telefonnumret saknar landskod.", en: "The phone number has no country code." },
  epost_ogiltig: { sv: "E-postadressen är ogiltig.", en: "The email address is invalid." },
  webbplats_ogiltig: { sv: "Webbadressen är ogiltig.", en: "The web address is invalid." },
  postnr_ogiltigt: { sv: "Postnumret är ogiltigt.", en: "The postal code is invalid." },
  sni_ogiltig: { sv: "SNI-koden ska vara två till fem siffror.", en: "The SNI code must be two to five digits." },
  tal_ogiltigt: { sv: "Värdet är inte ett tal.", en: "The value is not a number." },
  datum_ogiltigt: { sv: "Datumet går inte att läsa.", en: "The date cannot be read." },
  tidpunkt_ogiltig: { sv: "Tidpunkten går inte att läsa.", en: "The timestamp cannot be read." },
  relation_okand: { sv: "Relationen är okänd.", en: "The relation is unknown." },
  rattslig_grund_okand: { sv: "Den rättsliga grunden är okänd.", en: "The legal basis is unknown." },
  post_inte_objekt: { sv: "Posten är inte ett objekt.", en: "The record is not an object." },
  // Affärens, uppgiftens och anteckningens regler (app/crm/objekt.py).
  utanfor_intervall: { sv: "Talet är för stort eller för litet.", en: "The number is too large or too small." },
  for_lang: { sv: "Texten är för lång.", en: "The text is too long." },
  valuta_ogiltig: { sv: "Valutan är okänd. Skriv den med tre bokstäver, till exempel SEK.", en: "The currency is unknown. Use three letters, for example SEK." },
  id_ogiltigt: { sv: "Posten som valts finns inte längre. Välj en annan.", en: "The selected record no longer exists. Choose another." },
  forlustorsak_okand: { sv: "Förlustorsaken är okänd. Välj en ur listan.", en: "The lost reason is unknown. Choose one from the list." },
  kalltyp_okand: { sv: "Källan är okänd. Välj en ur listan.", en: "The source is unknown. Choose one from the list." }
};

/** Körningens eget fel (`error`), när hela körningen föll. */
export const KORNINGSFEL: Record<string, Localized> = {
  tom_full_synk: {
    sv: "Källan skickade inga poster i en full synk. Ingenting ändrades, eftersom ett tomt svar oftare är ett fel än en tömd kundstock.",
    en: "The source sent no records in a full sync. Nothing was changed, since an empty reply is more often a fault than an emptied customer base."
  }
};

export const kodtext = (tabell: Record<string, Localized>, kod: string): Localized => tabell[kod] ?? { sv: kod, en: kod };
