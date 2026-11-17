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
 * bara säger "Snajp" är ofullständig; en som säger "[Gatuadress]" är
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

import type { Localized } from "@/lib/i18n";

export const BOLAG = {
  /** Registrerat firmanamn (enskild firma). Samma som varumärket. */
  namn: "Snajp",
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
 * Bolagsidentifikationen som en färdig rad: "Snajp · org.nr … · adress".
 *
 * Bygger raden av det som FINNS. Med bara namnet ifyllt blir det "Snajp",
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
  /** Visas publikt i integritetspolicyn, därför på svenska och engelska. */
  andamal: Localized;
  /**
   * Var behandlingen sker, och överföringsmekanismen när den gäller utan
   * vidare (leverantörens villkor). Ett avtal som ännu inte är ingått
   * påstås inte här; avtalsläget står i kommentaren över varje post och i
   * docs/JURIDIK_ATGARDER.md.
   */
  region: Localized;
};

/*
 * Läget 2026-11-17, ur leverantörsgranskningen samma dag och Railways
 * regionlista. Utelämnade med flit:
 * - OpenAI: konfigurerad i koden men inte i drift. Läggs tillbaka här i
 *   samma ändring som en nyckel sätts i en miljö med riktig data.
 * - Google AI Studio (reservvägen i koden): får inte användas för kunddata
 *   och ska spärras i miljöer med riktig data. Används den, ska den in här.
 */
export const UNDERLEVERANTORER: readonly Underleverantor[] = [
  {
    // Vertex AI sedan 2026-09-12. Avtal: Cloud Data Processing Addendum,
    // gäller automatiskt via GCP-villkoren. Vilken Google-enhet som är
    // avtalspart är inte kontrollerat (faktureringskontot).
    namn: "Google Cloud (Vertex AI)",
    andamal: {
      sv: "Språkmodell (Gemini) som klassificerar och skriver text, beskriver bilder och bygger sökvektorer.",
      en: "Language model (Gemini) that classifies and writes text, describes images and builds search vectors."
    },
    region: {
      sv: "Inom EU, via regionala anrop i Belgien, Nederländerna och Finland. Behandlingen sker inom EU men inte nödvändigtvis i det land vi anropar. Meddelanden som Googles automatiska säkerhetsfilter flaggar kan sparas upp till 90 dagar. Google LLC är amerikanskt; överföring med EU-U.S. Data Privacy Framework och standardavtalsklausuler.",
      en: "Within the EU, through regional endpoints in Belgium, the Netherlands and Finland. Processing takes place within the EU but not necessarily in the country we call. Prompts flagged by Google's automated safety filters may be kept for up to 90 days. Google LLC is a US company; transfers rely on the EU-U.S. Data Privacy Framework and standard contractual clauses."
    }
  },
  {
    // Avtal: Railways DPA signeras via DocuSign och är ännu inte signerad
    // 2026-11-17. Ingen överföringsmekanism skrivs ut förrän den är det.
    namn: "Railway",
    andamal: {
      sv: "Drift av applikationen, databasen, bakgrundsjobben, jobbkön och cachen.",
      en: "Hosting of the application, the database, background jobs, the job queue and the cache."
    },
    region: {
      sv: "Amsterdam, Nederländerna (EU). Railway Corporation är ett amerikanskt bolag.",
      en: "Amsterdam, the Netherlands (EU). Railway Corporation is a US company."
    }
  },
  {
    // Jobbkö 2026-08-29 till 2026-11-17. Jobbkön flyttades till Railways egen
    // Redis 2026-11-17 efter ägarens beslut (docs/BESLUT.md). Den gamla
    // databasen har kvar cache och arbetsminne tills den raderats. Avtal: DPA
    // gäller automatiskt via Redis Cloud Agreement §5.3. Avtalspart Redis EMEA
    // Ltd (UK). Posten stryks när databasen är raderad.
    namn: "Redis Cloud (avvecklas)",
    andamal: {
      sv: "Tidigare jobbkö och cache. Används inte i driften men har kvar tillfälliga uppgifter tills databasen raderats.",
      en: "Former job queue and cache. Not used in operation, but still holds temporary data until the database is deleted."
    },
    region: {
      sv: "Google Cloud europe-west1, Belgien (EU). Avtalspart är Redis EMEA Ltd i Storbritannien; överföring med standardavtalsklausuler.",
      en: "Google Cloud europe-west1, Belgium (EU). The contracting party is Redis EMEA Ltd in the United Kingdom; transfers rely on standard contractual clauses."
    }
  },
  {
    // Sändväg sedan 2026-08-29. Avtal: DPA gäller automatiskt via villkoren.
    // Regionen styr bara varifrån mejlen skickas, inte var de lagras.
    namn: "Resend",
    andamal: {
      sv: "Utskick av mejl och rapporter om studs och klagomål.",
      en: "Sending email and reporting bounces and complaints."
    },
    region: {
      sv: "Mejlen skickas från Irland (EU). Mejlinnehåll och loggar lagras i USA i 30 dagar. Överföring med EU-U.S. Data Privacy Framework och standardavtalsklausuler.",
      en: "Email is sent from Ireland (EU). Email content and logs are stored in the United States for 30 days. Transfers rely on the EU-U.S. Data Privacy Framework and standard contractual clauses."
    }
  },
  {
    // Ägaren beslutade 2026-11-17 att kundmejl inte går till TypeSafe, och
    // inkorgsklassningen via Jev är avstängd i båda miljöerna (docs/BESLUT.md).
    // Slås den på igen ska den här posten ändras först.
    // Avtal: DPA inkorporerad i Master Customer Agreement; det är inte belagt
    // vilka villkor kontot accepterade. Ej i DPF. Ingen mekanism skrivs ut.
    namn: "TypeSafe AI, Inc. (Jev)",
    andamal: {
      sv: "Språkmodell som klassar bolag under leadsresearch. Får publika bolagsuppgifter och sidutdrag utan e-postadresser, telefonnummer och personnummer.",
      en: "Language model that classifies companies during lead research. Receives public company information and page excerpts without email addresses, phone numbers or personal identity numbers."
    },
    region: {
      sv: "USA.",
      en: "United States."
    }
  },
  {
    // Upptäckt saknad 2026-09-02. Avtal: ingen publicerad DPA; begärs via
    // kontaktvägen i villkoren. Ingen överföringsmekanism angiven, ej i DPF.
    namn: "ScrapeGraphAI",
    andamal: {
      sv: "Hämtning av prospekts publika webbsidor (kontakt- och om oss-sidor) och skärmbilder av dem under leadsresearch.",
      en: "Fetching prospects' public web pages (contact and about pages), and screenshots of them, during lead research."
    },
    region: {
      sv: "USA.",
      en: "United States."
    }
  },
  {
    // Synken (GitHub Actions) går main → development sedan 2026-10-17 och bär
    // produktionens persondata. Avtal: GitHubs DPA omfattar inte Free-planen.
    // Posten stryks när synken inte längre bär persondata.
    namn: "GitHub (Microsoft)",
    andamal: {
      sv: "Körmaskiner som synkroniserar produktionsdata till testmiljön och kör databasmigreringar.",
      en: "Runners that synchronise production data to the test environment and run database migrations."
    },
    region: {
      sv: "USA och andra länder. GitHub anger inte i vilken region körmaskinerna står.",
      en: "United States and other countries. GitHub does not state which region the runners are in."
    }
  },
  {
    // Inte längre driftdatabas (Railway sedan augusti). Det gamla projektet
    // bär historiska uppgifter tills det raderats. Avtal: DPA och SCC gäller
    // automatiskt via villkoren. Posten stryks när raderingen är bekräftad.
    namn: "Supabase (avvecklas)",
    andamal: {
      sv: "Tidigare databas. Används inte i driften men har kvar historiska uppgifter tills projektet raderats.",
      en: "Former database. Not used in operation, but still holds historical data until the project is deleted."
    },
    region: {
      sv: "Irland (EU). Supabase Pte. Ltd. finns i Singapore; överföring med standardavtalsklausuler.",
      en: "Ireland (EU). Supabase Pte. Ltd. is based in Singapore; transfers rely on standard contractual clauses."
    }
  }
] as const;
