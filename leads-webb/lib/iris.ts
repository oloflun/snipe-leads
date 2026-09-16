/**
 * Iris — leadsagentens namn och regelverk, på ETT ställe.
 *
 * Namnet, gränslistan och eskaleringsreglerna läses av flera vyer (Kör Iris,
 * Inställningar, demon). Ligger de i varsin fil glider formuleringarna isär,
 * och en gränslista som säger olika saker på två sidor är värre än ingen.
 *
 * Hederlighetsregeln (DESIGN.md) gäller här med full kraft: varje rad i
 * GRANSER motsvarar en spärr som faktiskt finns i backenden (granskningskön,
 * avregistreringen, provenienskravet, svarsstoppet). Skriv aldrig in en
 * gräns här som koden inte upprätthåller.
 */

export const IRIS = {
  namn: "Iris",
  /** En mening som presenterar personan, för sajt och marknadsyta. */
  persona:
    "Iris är Snajps leadsagent. Hon letar fram bolag som matchar din målgrupp, gör research med källor som går att kontrollera och skriver personliga utkast. Du granskar och godkänner, alltid.",
} as const;

/**
 * Det Iris aldrig gör utan din granskning. Varje punkt pekar på spärren som
 * bär den, så att listan går att falsifiera mot koden.
 */
export const GRANSER: ReadonlyArray<{ rubrik: string; text: string }> = [
  {
    rubrik: "Skickar aldrig ett första utskick själv",
    text: "Varje utkast går till granskningskön och skickas först när du godkänt det. Godkännandet släpper det till schemaläggaren, inte direkt ut."
  },
  {
    rubrik: "Kontaktar aldrig den som avböjt",
    text: "Avregistrerade adresser och bolag du spärrat rörs inte, och uppföljningen stannar i samma sekund som någon svarar."
  },
  {
    rubrik: "Lämnar aldrig priser eller villkor",
    text: "Prisuppgifter, rabatter och avtalsvillkor formuleras aldrig i ett utskick utan att du sett och godkänt formuleringen."
  },
  {
    rubrik: "Hittar aldrig på uppgifter om ett bolag",
    text: "Utan minst en sparad källa får Iris inte skriva ett utkast. Det som står om ett bolag ska gå att kontrollera, rad för rad."
  },
  {
    rubrik: "Bokar aldrig ett möte bakom din rygg",
    text: "Ett svar som vill boka tid landar hos dig. Iris föreslår, du bekräftar. Kalendern är din."
  }
];

/**
 * Eskaleringsreglerna: när ett lead eller ett svar ska lämnas till en
 * människa i stället för att hanteras vidare automatiskt.
 *
 * Sparas lokalt i webbläsaren tills backenden bär ett eget fält för dem —
 * det här är den lokala utvecklingsytan, och inställningen ska inte låtsas
 * vara synkad när den inte är det. Vyn säger det rakt ut.
 */
export type Eskaleringsregler = {
  /** Kvalificering under tröskeln går till dig i stället för till utkast. */
  osakerKvalificering: boolean;
  /** Träffsäkerhet i procent, 0 till 100. */
  kvalificeringstroskel: number;
  /** Svar som tar upp pris, rabatt eller avtal lämnas alltid till dig. */
  prisforhandling: boolean;
  /** Irriterade eller avvisande svar lämnas till dig, uppföljning stoppas. */
  negativtSentiment: boolean;
  /** Frågor om juridik, avtal eller personuppgifter lämnas alltid till dig. */
  juridik: boolean;
};

export const ESKALERING_STANDARD: Eskaleringsregler = {
  osakerKvalificering: true,
  kvalificeringstroskel: 60,
  prisforhandling: true,
  negativtSentiment: true,
  juridik: true
};

const ESKALERING_NYCKEL = "iris-eskaleringsregler";

/** Läser reglerna ur localStorage; faller alltid tillbaka på standarden.
 *  try/catch för att lagringen kan vara blockerad (privat läge, policy). */
export function lasEskaleringsregler(): Eskaleringsregler {
  try {
    const ra = window.localStorage.getItem(ESKALERING_NYCKEL);
    if (!ra) return ESKALERING_STANDARD;
    const tolkad = JSON.parse(ra) as Partial<Eskaleringsregler>;
    return {
      ...ESKALERING_STANDARD,
      ...tolkad,
      kvalificeringstroskel: Math.min(
        100,
        Math.max(0, Number(tolkad.kvalificeringstroskel ?? ESKALERING_STANDARD.kvalificeringstroskel) || 0)
      )
    };
  } catch {
    return ESKALERING_STANDARD;
  }
}

export function sparaEskaleringsregler(regler: Eskaleringsregler): boolean {
  try {
    window.localStorage.setItem(ESKALERING_NYCKEL, JSON.stringify(regler));
    return true;
  } catch {
    return false;
  }
}

/**
 * Människoläsbar etikett för en käll-URL: "linkedin.com" blir "LinkedIn",
 * allt annat blir sitt värddatornamn. Ingen mappning hittar på en källa som
 * inte finns; okända domäner visas som de är.
 */
const KANDA_KALLOR: ReadonlyArray<[RegExp, string]> = [
  [/(^|\.)linkedin\.com$/i, "LinkedIn"],
  [/(^|\.)allabolag\.se$/i, "Allabolag"],
  [/(^|\.)bolagsverket\.se$/i, "Bolagsverket"],
  [/(^|\.)arbetsformedlingen\.se$/i, "Platsbanken"],
  [/(^|\.)mynewsdesk\.com$/i, "Pressmeddelande"]
];

/** Backendens statusvärden är engelska koder; badgarna ska tala sajtens
 *  språk. Okända värden visas som de är — hellre rått än fel. */
const STATUS_ETIKETTER: Record<string, string> = {
  new: "Ny",
  researched: "Researchad",
  qualified: "Kvalificerad",
  disqualified: "Underkänd",
  contacted: "Kontaktad"
};

export function statusEtikett(status: string): string {
  return STATUS_ETIKETTER[status] ?? status;
}

export function kallEtikett(url: string): string {
  try {
    const vard = new URL(url).hostname.replace(/^www\./i, "");
    for (const [monster, etikett] of KANDA_KALLOR) {
      if (monster.test(vard)) return etikett;
    }
    return vard;
  } catch {
    return url;
  }
}
