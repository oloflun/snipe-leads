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
 * Priserna är EXEMPEL under pilotperioden.
 *
 * Flaggan är inte dekoration: den styr om förbehållet renderas. Sätts den till
 * false utan att någon faktiskt bestämt priserna, försvinner den enda text som
 * säger att de kan ändras — och då är de i praktiken utlovade.
 */
export const PRISER_AR_PRELIMINARA = true;

export type Paket = {
  id: "support" | "leads" | "duo";
  namn: string;
  prisPerManad: number;
  beskrivning: Localized;
  ingar: Localized[];
  /** Duo markeras. Det är paketet vi vill sälja. */
  populärast?: boolean;
  /** Renderas som en rad under priset. */
  notis?: Localized;
};

export const VALUTA = "SEK";
export const LOCALE_FOR_PRIS = "sv-SE";

export const PAKET: Paket[] = [
  {
    id: "support",
    namn: "Snajp Support",
    prisPerManad: 2990,
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
    prisPerManad: 6490,
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
    notis: {
      sv: "Sparar 990 kr/mån jämfört med att köpa dem var för sig.",
      en: "Saves 990 kr/month compared to buying them separately."
    }
  }
];

/** Engångsavgift vid start: kunskapsbas och konfiguration. */
export const UPPSTARTSAVGIFT = 4900;

/** Rörliga priser utöver paketets ingående volym. */
export const EXTRA_PROSPEKT_PRIS = 9;
export const EXTRA_MEJL_PRIS = 3;

/** Bindningstid i månader. */
export const BINDNINGSTID_MANADER = 3;

/**
 * Räknas fram, skrivs inte. Står besparingen som en egen siffra kan den sluta
 * stämma med paketpriserna utan att något säger ifrån — och den sortens fel
 * upptäcks av kunden, inte av oss.
 */
export function duoBesparingPerManad(): number {
  const separat = PAKET.filter((p) => p.id === "support" || p.id === "leads").reduce(
    (summa, paket) => summa + paket.prisPerManad,
    0
  );
  const duo = PAKET.find((p) => p.id === "duo");
  return duo ? separat - duo.prisPerManad : 0;
}

/** "2 990 kr". Ett ställe, så att tusenavgränsaren är densamma överallt. */
export function formateraPris(belopp: number, locale: string = LOCALE_FOR_PRIS): string {
  return `${new Intl.NumberFormat(locale).format(belopp)} kr`;
}
