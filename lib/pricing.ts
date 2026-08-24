import type { Localized } from "@/lib/i18n";

/**
 * All prisdata på ETT ställe.
 *
 * Regeln som gör filen värd att ha: ingen prissiffra får hårdkodas i en
 * komponent. Ett pris som står på två ställen ändras på ett av dem, och
 * skillnaden upptäcks av en kund som läst det andra.
 *
 * Beloppen är i HELA KRONOR och formateras vid rendering, inte här. En
 * förformaterad sträng ("2 990 kr/mån") går varken att räkna på — se
 * `duoBesparingPerManad` — eller att lokalisera.
 */

/**
 * Styr om förbehållet om preliminära priser renderas.
 *
 * Satt till false 2026-08-22 på begäran: priserna nedan är beslutade och
 * pilotförbehållet skulle inte längre stå kvar. Notera vad det innebär —
 * utan den texten finns ingen skrivning på sidan som säger att priserna kan
 * ändras, alltså läses de som utlovade. Sätt tillbaka den till true samma dag
 * som ett pris ska kunna röra sig.
 */
export const PRISER_AR_PRELIMINARA = false;

export type Paket = {
  id: "support" | "leads" | "duo" | "bookkeeping";
  namn: string;
  /**
   * `null` betyder att priset inte är satt ännu, och det är ETT tillstånd, inte
   * ett saknat värde.
   *
   * Alternativet vore `0`, och det vore en osanning: `formateraPris(0)` ger
   * "0 kr", vilket är ett pris — och det står då på prislistan bredvid tre
   * riktiga. Ett paket utan pris ska säga att det saknas och hänvisa vidare,
   * inte påstå att det är gratis.
   *
   * Varje läsare tvingas av typen att ta ställning. Se PricingSection och
   * PlanSettings, som båda renderar en egen text för det här fallet.
   */
  prisPerManad: number | null;
  beskrivning: Localized;
  ingar: Localized[];
  /** Duo markeras. Det är paketet vi vill sälja. */
  populärast?: boolean;
  /** Renderas som en rad under priset. `{belopp}` byts mot besparingen. */
  notisMall?: Localized;
};

export const VALUTA = "SEK";
export const LOCALE_FOR_PRIS = "sv-SE";

export const PAKET: Paket[] = [
  {
    id: "support",
    namn: "Snajp Support",
    prisPerManad: 3990,
    beskrivning: {
      sv: "Kundtjänstagenten som svarar utifrån er egen kunskapsbas.",
      en: "The customer service agent that answers from your own knowledge base."
    },
    ingar: [
      { sv: "Kundtjänstagent", en: "Customer service agent" },
      { sv: "Egen kunskapsbas", en: "Your own knowledge base" },
      { sv: "Obegränsade chattar", en: "Unlimited chats" },
      { sv: "E-posttriage", en: "Email triage" }
    ]
  },
  {
    id: "leads",
    namn: "Snajp Leads",
    prisPerManad: 4490,
    beskrivning: {
      sv: "Leads-agenten som hittar och skriver till rätt företag.",
      en: "The leads agent that finds and writes to the right companies."
    },
    ingar: [
      { sv: "Leads-agent", en: "Leads agent" },
      { sv: "ICP-konfiguration", en: "ICP configuration" },
      { sv: "150 prospekt per månad", en: "150 prospects per month" },
      { sv: "300 mejl per månad", en: "300 emails per month" },
      { sv: "Granskningskö", en: "Review queue" }
    ]
  },
  {
    id: "duo",
    namn: "Snajp Duo",
    prisPerManad: 6990,
    populärast: true,
    beskrivning: {
      sv: "Båda agenterna i samma dashboard, med delad kunddata.",
      en: "Both agents in one dashboard, with shared customer data."
    },
    ingar: [
      { sv: "Båda agenterna", en: "Both agents" },
      { sv: "Gemensam dashboard", en: "One shared dashboard" },
      { sv: "Delad kunddata", en: "Shared customer data" }
    ],
    /**
     * Besparingen räknas fram vid rendering (`duoBesparingPerManad`) i stället
     * för att stå som en siffra i texten. Den stod som "990 kr" när paketen
     * kostade 2 990 och 4 490 mot 6 490; efter prisändringen till 3 990,
     * 4 490 och 6 990 är den 1 490, och en handskriven siffra hade blivit fel
     * i samma sekund utan att något sagt ifrån.
     */
    notisMall: {
      sv: "Sparar {belopp}/mån jämfört med att köpa dem var för sig.",
      en: "Saves {belopp}/month compared to buying them separately."
    }
  },
  {
    /**
     * Bokföringen. 1 990 kr/mån, beslutat 2026-08-24.
     *
     * Fristående paket, inte en del av Duo. Duo är "båda agenterna i samma
     * dashboard, med delad kunddata", och bokföringen delar ingen kunddata med
     * någon av dem — den läser kvitton, inte prospekt eller ärenden. Att lägga
     * den i Duo hade dessutom höjt priset på ett paket kunder redan köpt.
     */
    id: "bookkeeping",
    namn: "Snajp Bokföring",
    prisPerManad: 1990,
    beskrivning: {
      sv: "Bokföringsagenten som läser kvitton och föreslår kontering.",
      en: "The bookkeeping agent that reads receipts and proposes entries."
    },
    ingar: [
      { sv: "Avläsning av kvitton och fakturor", en: "Reading of receipts and invoices" },
      { sv: "Konteringsförslag ur BAS-kontoplanen", en: "Proposed entries from the Swedish BAS chart" },
      { sv: "Periodrapport med momssummor", en: "Period report with VAT totals" },
      { sv: "SIE4-export till ert bokföringsprogram", en: "SIE4 export to your accounting software" },
      { sv: "Bokföringsassistent i chatt", en: "Bookkeeping assistant in chat" }
    ]
  }
];

/** Engångsavgift vid start: kunskapsbas och konfiguration. */
export const UPPSTARTSAVGIFT = 4900;

/** Rörliga priser utöver paketets ingående volym. */
export const EXTRA_PROSPEKT_PRIS = 9;
export const EXTRA_MEJL_PRIS = 3;

/**
 * Alla priser i prislistan renderas med ordet "från" framför sig: paketen är
 * ingångspriser och sätts efter volym och omfattning. Prefixet ligger här och
 * inte i komponenten, av samma skäl som beloppen gör det.
 */
export const PRIS_PREFIX: Localized = { sv: "från", en: "from" };

/**
 * Vad som står där priset skulle stått när `prisPerManad` är null.
 *
 * Här och inte i komponenterna, av samma skäl som beloppen: fyra läsare som
 * var för sig hittar på en formulering blir fyra olika löften om samma paket.
 */
export const PRIS_SAKNAS: Localized = { sv: "Pris på förfrågan", en: "Price on request" };

/** Bindningstid i månader. */
export const BINDNINGSTID_MANADER = 3;

/**
 * Räknas fram, skrivs inte. Står besparingen som en egen siffra kan den sluta
 * stämma med paketpriserna utan att något säger ifrån — och den sortens fel
 * upptäcks av kunden, inte av oss.
 */
export function duoBesparingPerManad(): number {
  const separat = PAKET.filter((p) => p.id === "support" || p.id === "leads").reduce(
    (summa, paket) => summa + (paket.prisPerManad ?? 0),
    0
  );
  const duo = PAKET.find((p) => p.id === "duo");
  // Saknar duo pris finns ingen besparing att räkna, och 0 är rätt svar —
  // renderingen döljer raden på noll. Bokföringen deltar inte: den ingår inte
  // i Duo, så dess pris hör inte hemma i den här jämförelsen.
  return duo && duo.prisPerManad !== null ? separat - duo.prisPerManad : 0;
}

/** "2 990 kr". Ett ställe, så att tusenavgränsaren är densamma överallt. */
export function formateraPris(belopp: number, locale: string = LOCALE_FOR_PRIS): string {
  return `${new Intl.NumberFormat(locale).format(belopp)} kr`;
}
