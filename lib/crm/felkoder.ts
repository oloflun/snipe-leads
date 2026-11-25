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
  finns_redan: { sv: "En annan post har redan samma nyckel.", en: "Another record already has the same key." }
};

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
  tal_ogiltigt: { sv: "Värdet är inte ett tal.", en: "The value is not a number." },
  datum_ogiltigt: { sv: "Datumet går inte att läsa.", en: "The date cannot be read." },
  tidpunkt_ogiltig: { sv: "Tidpunkten går inte att läsa.", en: "The timestamp cannot be read." },
  relation_okand: { sv: "Relationen är okänd.", en: "The relation is unknown." },
  rattslig_grund_okand: { sv: "Den rättsliga grunden är okänd.", en: "The legal basis is unknown." },
  post_inte_objekt: { sv: "Posten är inte ett objekt.", en: "The record is not an object." }
};

/** Körningens eget fel (`error`), när hela körningen föll. */
export const KORNINGSFEL: Record<string, Localized> = {
  tom_full_synk: {
    sv: "Källan skickade inga poster i en full synk. Ingenting ändrades, eftersom ett tomt svar oftare är ett fel än en tömd kundstock.",
    en: "The source sent no records in a full sync. Nothing was changed, since an empty reply is more often a fault than an emptied customer base."
  }
};

export const kodtext = (tabell: Record<string, Localized>, kod: string): Localized => tabell[kod] ?? { sv: kod, en: kod };
