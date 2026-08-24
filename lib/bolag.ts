/**
 * Snajps egna bolagsuppgifter — på ETT ställe.
 *
 * ## Platshållarna är avsiktliga och ska INTE gissas
 *
 * Organisationsnummer, bolagsform och postadress står som `[...]`. Det är inte
 * en glömska: en marknadsföringssida som anger fel organisationsnummer är
 * felaktig marknadsföring, och ett påhittat org.nr kan tillhöra ett annat
 * bolag. Fyll i dem från registreringsbeviset, inte från minnet.
 *
 * `bolagsuppgifterna_klara` nedan är sanningen om huruvida det är gjort.
 * Sidfoten och de juridiska sidorna renderar en synlig ruta så länge den är
 * falsk — en osynlig platshållare hade legat kvar i produktion i ett halvår.
 *
 * ## Kontaktadressen
 *
 * `KONTAKT_MEJL` i components/marketing/copy.ts är Gmail-adressen som
 * supporten faktiskt läser. Den duger som svarsadress men inte som ett
 * företags enda officiella kontaktväg på en B2B-säljsida, och den duger inte
 * alls som den adress en registrerad ska skriva till för att utöva sina
 * rättigheter enligt GDPR. `DATASKYDD_MEJL` är den adressen, och den ska
 * ligga på egen domän.
 */

export const BOLAG = {
  /** Registrerat namn, inte varumärket. Varumärket är "Snajp". */
  namn: "Snajp AB",
  orgnr: "[XXXXXX-XXXX]",
  postadress: "[Gatuadress, postnummer, ort]",
  /** Sätts när integritetspolicyn granskats av jurist och publicerats skarpt. */
  policyUppdaterad: "[DATUM]"
} as const;

/** Adressen för dataskyddsärenden. Ska ligga på snajp.se, inte på Gmail. */
export const DATASKYDD_MEJL = "[integritet@snajp.se]";

/** En platshållare är en text som fortfarande bär hakparenteser. */
export function arPlatshallare(varde: string): boolean {
  return varde.includes("[");
}

/**
 * Om bolagsuppgifterna är ifyllda. Falskt = sidorna visar en varningsruta i
 * stället för att låtsas att uppgifterna stämmer.
 */
export const bolagsuppgifterna_klara =
  !arPlatshallare(BOLAG.namn) &&
  !arPlatshallare(BOLAG.orgnr) &&
  !arPlatshallare(BOLAG.postadress) &&
  !arPlatshallare(DATASKYDD_MEJL);

/**
 * Underleverantörerna som behandlar personuppgifter för vår räkning.
 *
 * Listan är INTE dekoration. Den ska stämma med verkligheten på tre ställen
 * samtidigt: här, i PUB-avtalets bilaga och i registerförteckningen
 * (docs/registerforteckning.md). Läggs en leverantör till i koden ska den
 * läggas till här i samma ändring — en kund som upptäcker en leverantör vi
 * inte nämnt har hittat ett avtalsbrott, inte ett stavfel.
 */
export type Underleverantor = {
  namn: string;
  andamal: string;
  /** Var behandlingen sker. Tredjeland kräver SCC — se juridik-checklistan. */
  region: string;
};

export const UNDERLEVERANTORER: readonly Underleverantor[] = [
  {
    // Aktiv chattprovider sedan 2026-08-24 (LLM_PROVIDER=gemini). Driver
    // dessutom bildbeskrivning och embeddings sedan tidigare.
    namn: "Google (Gemini)",
    andamal: "Språkmodell som genererar och klassificerar text, beskriver bilder och bygger sökvektorer.",
    region:
      "[Ange dataregion OCH avtalsnivå. Avgörande: en gratisnivå tillåter " +
      "typiskt leverantören att använda innehållet för produktförbättring. " +
      "Se docs/JURIDIK_ATGARDER.md, P0.1c.]"
  },
  {
    // Konfigurerad i koden men ingen nyckel satt i någon miljö 2026-08-24.
    namn: "OpenAI",
    andamal: "Alternativ språkmodell. Inte i drift just nu.",
    region: "[Ange dataregion och avtalsform — DPA + SCC]"
  },
  {
    namn: "Supabase",
    andamal: "Databaslagring och autentisering.",
    region: "Irland, EU"
  },
  {
    namn: "Railway",
    andamal: "Drift av applikationen och databasen.",
    region: "[Ange datacenterregion]"
  }
] as const;
