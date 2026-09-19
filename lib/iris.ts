/**
 * Iris — leadsagentens namn och regelverk, på ETT ställe.
 *
 * Portad från `leads-webb/lib/iris.ts` (den fristående Iris-sajten) när Iris
 * flyttade in i huvudappens vänsterrail (2026-09-19, se
 * `.agent-context`-planen för restruktureringen). Namnet, gränslistan och
 * eskaleringsreglerna läses av flera vyer (Kör Iris, Inställningar, demon).
 * Ligger de i varsin fil glider formuleringarna isär, och en gränslista som
 * säger olika saker på två sidor är värre än ingen.
 *
 * Hederlighetsregeln (DESIGN.md) gäller här med full kraft: varje rad i
 * GRANSER motsvarar en spärr som faktiskt finns i backenden (granskningskön,
 * avregistreringen, provenienskravet, svarsstoppet). Skriv aldrig in en
 * gräns här som koden inte upprätthåller.
 */

export const IRIS = {
  namn: "Iris",
  /** En mening som presenterar personan, för rubrikraden ovanför Kör Iris. */
  persona:
    "Iris är Snajps leadsagent. Hon letar fram bolag som matchar din målgrupp, gör research med källor som går att kontrollera och skriver personliga utkast. Du granskar och godkänner, alltid."
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
 * Bor i backenden (agent_configs.settings.eskalering, se
 * snajp-support/app/leads/eskalering.py) och verkställs där: i
 * svarshanteringen och före utkastet i körningen. Fältnamnen är backendens.
 */
export type Eskaleringsregler = {
  /** Kvalificerade bolag under tröskeln får inget automatiskt utkast. */
  osaker_kvalificering: boolean;
  /** Träffsäkerhet i procent, 0 till 100. */
  kvalificeringstroskel: number;
  /** Svar om pris, rabatt eller budget får inget utkast; du aviseras. */
  prisfragor: boolean;
  /** Avvisande svar aviserar dig; uppföljningen stoppas alltid. */
  negativt_svar: boolean;
  /** Svar om avtal, villkor, juridik eller personuppgifter får inget utkast. */
  juridik: boolean;
};

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
