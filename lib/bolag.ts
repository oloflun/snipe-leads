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
 *
 * ## Platshållare får ALDRIG renderas
 *
 * Den gula rutan som förr sade "de här uppgifterna är platshållare" är
 * borttagen (2026-08-25, på begäran). Utan den läste "org.nr [XXXXXX-XXXX]"
 * i sidfoten som ett trasigt bygge i stället för som en känd lucka — och
 * `mailto:[integritet@snajp.se]` var en länk ingen kunde använda, på just den
 * rad där en registrerad ska utöva sina rättigheter.
 *
 * Regeln är därför: ingen renderingsplats skriver ut ett värde utan att först
 * köra det genom `utanPlatshallare`. Det som saknas UTELÄMNAS. En sida som
 * bara säger "Snajp AB" är ofullständig; en som säger "[Gatuadress]" är
 * felaktig, och bara det ena går att missta för att vara sant.
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
 * Värdet om det är riktigt, annars null. Grinden mellan lib/bolag.ts och allt
 * som renderas för en besökare.
 *
 * Returnerar null och inte tom sträng med flit: null tvingar anroparen att
 * skriva vad som händer när uppgiften saknas, medan "" tyst hade blivit ett
 * kommatecken utan text framför sig.
 */
export function utanPlatshallare(varde: string): string | null {
  return arPlatshallare(varde) ? null : varde;
}

/**
 * Adressen för dataskyddsärenden, med en fungerande reserv.
 *
 * `DATASKYDD_MEJL` ska ligga på egen domän och gör det inte ännu. Tills dess
 * pekar länken på adressen supporten faktiskt läser. Det är ETT STEG SÄMRE än
 * en egen domän — och flera steg bättre än en adress som inte finns, vilket är
 * vad som stod här tidigare. Byt inte reserven mot ingenting: en registrerad
 * som inte kan nå oss har inte fått sina rättigheter tillgodosedda.
 *
 * Reserven skickas in av anroparen i stället för att importeras hit, för att
 * lib/ inte ska bero på components/. Adressen bor i components/marketing/copy.ts.
 */
export function dataskyddKontakt(reservadress: string): string {
  return utanPlatshallare(DATASKYDD_MEJL) ?? reservadress;
}

/**
 * Bolagsidentifikationen som en färdig rad: "Snajp AB · org.nr … · adress".
 *
 * Bygger raden av det som FINNS. Med bara namnet ifyllt blir det "Snajp AB",
 * utan efterhängande avdelare — vilket är precis vad som gick fel när raden
 * skrevs som en mall med hål i.
 */
export function bolagsraden(avdelare: string = " · "): string {
  return [
    utanPlatshallare(BOLAG.namn),
    utanPlatshallare(BOLAG.orgnr) ? `org.nr ${BOLAG.orgnr}` : null,
    utanPlatshallare(BOLAG.postadress)
  ]
    .filter((del): del is string => del !== null)
    .join(avdelare);
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
  },
  {
    // Jobbkö sedan 2026-08-29: pågående chatt- och leadsjobb (inklusive
    // agentens svar till kunden) ligger här med kort TTL tills de hämtats.
    namn: "Redis Cloud (Redis Ltd)",
    andamal:
      "Jobbkö och cache: pågående ärenden och svar under behandling, med automatisk radering (TTL).",
    region:
      "[Verifiera EU-region och TLS med scripts/redis_kontroll.py, teckna " +
      "Redis DPA i kontot. Se docs/JURIDIK_ATGARDER.md, P1.2.]"
  },
  {
    // Sändväg sedan 2026-08-29 (EMAIL_PROVIDER=resend): utgående svar till
    // kunder går via Resends API.
    namn: "Resend",
    andamal: "Utskick av mejlsvar till kunder (HTTPS-sändväg).",
    region:
      "[Ange dataregion och avtalsform — DPA + SCC. Resend är ett " +
      "US-bolag; region och DPF-status ska bekräftas. Se P1.2.]"
  },
  {
    // Upptäckt saknad 2026-09-02: tjänsten har använts av leads-researchen
    // (app/agent/research_tools.py) sedan skrapningen byggdes, men stod
    // aldrig här — exakt det "avtalsbrott, inte stavfel" som kommentaren
    // ovanför listan varnar för. Den hämtar prospektens EGNA publika sidor
    // (kontakt/om oss), och det som kommer tillbaka är namngivna personer,
    // titlar och arbetsmejl — personuppgifter behandlade för vår räkning.
    namn: "ScrapeGraphAI",
    andamal:
      "Hämtning av prospekts publika webbsidor (kontakt- och om oss-sidor) " +
      "under leads-research.",
    region:
      "[Ange dataregion och avtalsform — DPA + ev. SCC. Varken region eller " +
      "avtal är bekräftat; flaggat till Anton 2026-09-02.]"
  }
] as const;
