import type { Localized } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";

/**
 * Extra selling sections for the image-led and graphic-led landing variants.
 *
 * Written with copywriting (problem before solution, objection handling, one
 * idea per section), reworked with copy-editing (the seven sweeps, chiefly
 * So What and Specificity), then finished with humanizer on the English and
 * humanizer-svenska on the Swedish.
 *
 * The humanizer passes removed, among others: "i en alltmer digitaliserad
 * vardag" (landskapsuppramning), "det är viktigt att notera att" (passive
 * false formality), "utgör" twice (copula avoidance), and a rule-of-three
 * that had no third real item.
 *
 * Binding rules unchanged: no fabricated proof, no em-dashes in either language.
 */

export type Objection = { q: Localized; a: Localized };

export type SectionCopy = {
  statementLabel: Localized;
  statement: Localized;
  problemLabel: Localized;
  problemHeading: Localized;
  problemBody: Localized;
  problemPoints: Localized[];
  placeLabel: Localized;
  placeHeading: Localized;
  placeBody: Localized;
  objectionsHeading: Localized;
  objections: Objection[];
};

const leads: SectionCopy = {
  statementLabel: { sv: "Så tänker vi", en: "How we see it" },
  statement: {
    sv: "Ett utskick är inte ett samtal.",
    en: "A mailshot is not a conversation."
  },
  problemLabel: { sv: "Problemet", en: "The problem" },
  problemHeading: {
    sv: "Det tar en timme att skriva ett mejl som *förtjänar* ett svar.",
    en: "It takes an hour to write an email that *deserves* a reply."
  },
  problemBody: {
    sv: "Så du skickar mallen i stället. Den går ut till fyrtio bolag, tre svarar undrande, och nästa vecka gör du om det. Problemet är inte att du skriver dåligt. Problemet är att researchen tar tid du inte har.",
    en: "So you send the template instead. It goes out to forty companies, three reply confused, and next week you do it again. You are not a bad writer. The research just costs time you do not have."
  },
  problemPoints: [
    {
      sv: "Att läsa in sig på ett bolag tar tjugo minuter. Gånger fyrtio bolag.",
      en: "Reading up on one company takes twenty minutes. Times forty companies."
    },
    {
      sv: "När du hunnit skriva har tajmingen ofta hunnit gå över.",
      en: "By the time the email is written, the moment has often passed."
    },
    {
      sv: "Mallen som sparar tid är också den som gör att ingen svarar.",
      en: "The template that saves the time is the same one that stops the replies."
    }
  ],
  placeLabel: { sv: "Var det kommer ifrån", en: "Where it comes from" },
  /* The accent word carries the section: "här" means this market, not this city.
     That is why the two offices sit in the body and the heading stays short
     enough to hold at 15ch. */
  placeHeading: {
    sv: "Byggt i Göteborg, för bolag som säljer *här*.",
    en: "Built in Gothenburg, for companies selling *here*."
  },
  placeBody: {
    sv: "Svensk B2B är ett litet rum. Tonen är lågmäld, namnen känns igen och ett utskick som luktar mall syns direkt. Snajp är byggt för det rummet, inte översatt till det. Vi sitter i Göteborg och Umeå och jobbar med bolag i hela landet.",
    en: "Swedish B2B is a small room. The register is understated, the names recur, and a mass mailing is spotted on sight. Snajp is built for that room rather than translated into it. We work from Gothenburg and Umeå, with companies across the country."
  },
  objectionsHeading: {
    sv: "Det du undrar *innan* du testar.",
    en: "What you are wondering *before* you try it."
  },
  objections: [
    {
      q: { sv: "Blir det inte bara mer AI-spam?", en: "Is this not just more AI spam?" },
      a: {
        sv: "Verktyget skickar ingenting. Det skriver ett utkast, du läser det, och du trycker skicka. Går ett mejl ut som du inte står för är det för att du godkände det.",
        en: "The tool sends nothing. It writes a draft, you read it, you press send. If an email goes out that you would not stand behind, it is because you approved it."
      }
    },
    {
      q: { sv: "Var kommer uppgifterna ifrån?", en: "Where does the data come from?" },
      a: {
        sv: "Öppna källor: bolagets egen webbplats, platsannonser, pressmeddelanden. Ingen LinkedIn-skrapning och inga köpta listor. Du kan se vilken källa varje formulering vilar på.",
        en: "Public sources: the company's own site, job ads, press releases. No LinkedIn scraping and no bought lists. You can see which source every claim rests on."
      }
    },
    {
      q: { sv: "Vad händer med kunduppgifterna?", en: "What happens to customer data?" },
      a: {
        sv: "Den ligger kvar hos er, med radnivåbehörighet och loggar på vem som läst vad. Vi tränar inga modeller på ert innehåll.",
        en: "It stays with you, with row level access rules and logs of who read what. We train no models on your content."
      }
    }
  ]
};

const support: SectionCopy = {
  statementLabel: { sv: "Så tänker vi", en: "How we see it" },
  statement: {
    sv: "Ett svar som gissar är sämre än inget svar.",
    en: "An answer that guesses is worse than no answer."
  },
  problemLabel: { sv: "Problemet", en: "The problem" },
  problemHeading: {
    sv: "Inkorgen är full av frågor ni *redan* har svarat på.",
    en: "The inbox is full of questions you have *already* answered."
  },
  problemBody: {
    sv: "Samma fyra ärenden, om och om igen. Någon måste ändå läsa varje mejl för att veta vilket som är brådskande, och den någon hinner sällan med det som faktiskt kräver en människa.",
    en: "The same four cases, over and over. Someone still has to read every email to know which one is urgent, and that someone rarely gets to the cases that genuinely need a person."
  },
  problemPoints: [
    {
      sv: "Sorteringen tar den första timmen av varje arbetsdag.",
      en: "Triage takes the first hour of every working day."
    },
    {
      sv: "Det brådskande ärendet ligger under nio som inte är det.",
      en: "The urgent case sits underneath nine that are not."
    },
    {
      sv: "Svaren finns redan skrivna, men i fel dokument.",
      en: "The answers are already written, just in the wrong document."
    }
  ],
  placeLabel: { sv: "Var det kommer ifrån", en: "Where it comes from" },
  placeHeading: {
    sv: "Svarar på svenska, med *era* ord.",
    en: "Answers in Swedish, in *your* words."
  },
  placeBody: {
    sv: "Agenten hämtar formuleringarna ur er kunskapsbas, så tonen blir er egen och inte en översättning. Kunden märker att svaret kommer från er, inte från en generisk assistent.",
    en: "The agent takes its phrasing from your knowledge base, so the tone is yours rather than a translation. The customer can tell the reply came from you and not from a generic assistant."
  },
  objectionsHeading: {
    sv: "Det du undrar *innan* du testar.",
    en: "What you are wondering *before* you try it."
  },
  objections: [
    {
      q: { sv: "Hittar den på svar?", en: "Does it invent answers?" },
      a: {
        sv: "Nej. Den söker i er kunskapsbas och svarar bara på det den hittar täckning för. Finns inte underlaget lämnas ärendet vidare till en människa i stället.",
        en: "No. It searches your knowledge base and answers only where it finds cover. Without the material, the case goes to a person instead."
      }
    },
    {
      q: { sv: "Vad händer med en riktigt arg kund?", en: "What about a genuinely angry customer?" },
      a: {
        sv: "Den eskalerar direkt. Återbetalning, juridik och GDPR går alltid till en människa, med hela ärendehistoriken bifogad så ingen behöver börja om.",
        en: "It escalates at once. Refunds, legal matters and GDPR always go to a person, with the full case history attached so nobody starts over."
      }
    },
    {
      q: { sv: "Märker kunden att det är en agent?", en: "Can the customer tell it is an agent?" },
      a: {
        sv: "Ja, och det är meningen. Svaret är märkt. Att dölja det skulle spara en sekund och kosta förtroendet.",
        en: "Yes, and that is deliberate. The reply is labelled. Hiding it would save a second and cost the trust."
      }
    }
  ]
};

export const sectionCopy: Record<ProductKey, SectionCopy> = { leads, support };

export const imagery = {
  /**
   * Photographs are vendored into `public/photos` rather than hotlinked. Each was
   * sourced from Unsplash, verified to load, and looked at before selection; the
   * originals were then downsized and re-encoded to WebP. Credits live in
   * `public/photos/credits.json`.
   *
   * The two Stockholm photographs were replaced when the place copy moved to
   * Göteborg. The old pairing put a Gamla stan street next to the words "built
   * in Malmö" and nobody caught it for a whole session: a place claim and a
   * photograph of a place are the same claim made twice.
   */
  hero: {
    src: "/photos/goteborg-golden.webp",
    alt: {
      sv: "Göteborg sett från höjden i gyllene kvällsljus",
      en: "Gothenburg seen from above in golden evening light"
    }
  },
  street: {
    src: "/photos/haga.webp",
    alt: {
      sv: "Kullerstensgata i Haga med landshövdingehus",
      en: "A cobblestone street in Haga, Gothenburg"
    }
  },
  grid: {
    src: "/photos/facade.webp",
    alt: { sv: "Fasad med rader av identiska fönster", en: "A facade of identical repeating windows" }
  },
  desk: {
    src: "/photos/desk.webp",
    alt: {
      sv: "Skandinaviskt skrivbord i dagsljus",
      en: "A Scandinavian desk in daylight"
    }
  }
} as const;

/** Kept as a single seam so the source can move again without touching markup. */
export function photo(src: string): string {
  return src;
}
