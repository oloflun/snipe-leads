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
 * ## Etiketter som är tomma
 *
 * `problemLabel` och `placeLabel` är tomma strängar. De bar tidigare orden
 * "Problemet" och "Var det kommer ifrån" över respektive rubrik, och båda är
 * borttagna på begäran. De ligger kvar som fält i stället för att tas bort ur
 * typen: renderingen hoppar över en tom etikett, och en framtida rubrik kan
 * återfå sin överrad utan att markup ändras. Se `Label`-anropen i
 * LandingPhoto.
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

const TOM: Localized = { sv: "", en: "" };

const leads: SectionCopy = {
  statementLabel: { sv: "Så tänker vi", en: "How we see it" },
  statement: {
    sv: "Effektiv kundhantering kommer alltid vara en prioritering.",
    en: "Handling customers efficiently will always be a priority."
  },
  problemLabel: TOM,
  problemHeading: {
    sv: "En agent som hanterar *allt*.",
    en: "One agent that handles *all of it*."
  },
  problemBody: {
    sv: "Slipp samma mailutskick till fyrtio bolag, tre svarar, samma sak veckan efter. Problemet är inte vad du skriver. Problemet är att researchen efter bra leads tar tiden du inte har.",
    en: "No more sending the same mailshot to forty companies, three replying, and the same thing again the week after. The problem is not what you write. The problem is that researching good leads takes the time you do not have."
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
      sv: "Mallen, som ofta förblir densamma, ändras hos oss på ett knapptryck.",
      en: "The template, which usually stays the same, changes here at the press of a button."
    }
  ],
  placeLabel: TOM,
  /* The accent word carries the section. The two offices sit in the body and
     the heading stays short enough to hold at 15ch. */
  placeHeading: {
    sv: "Byggt i Göteborg, för bolag som vill *effektivisera arbetet*.",
    en: "Built in Gothenburg, for companies that want to *work more efficiently*."
  },
  placeBody: {
    sv: "Vi sitter i Göteborg och Umeå och jobbar med bolag i hela landet.",
    en: "We work from Gothenburg and Umeå, with companies across the country."
  },
  objectionsHeading: {
    sv: "Frågor och *Svar*.",
    en: "Questions and *answers*."
  },
  objections: [
    {
      q: { sv: "Blir det inte bara mer AI-spam?", en: "Is this not just more AI spam?" },
      a: {
        sv: "Agenten skickar personliga och professionella mail till noggrant utvalda kunder. Du är alltid den som trycker godkänn och skicka.",
        en: "The agent writes personal, professional emails to carefully chosen companies. You are always the one who presses approve and send."
      }
    },
    {
      q: { sv: "Var kommer uppgifterna ifrån?", en: "Where does the data come from?" },
      a: {
        sv: "Öppna källor: bolagets egen webbplats, platsannonser, pressmeddelanden.",
        en: "Public sources: the company's own site, job ads, press releases."
      }
    },
    {
      q: { sv: "Vad händer med kunduppgifterna?", en: "What happens to customer data?" },
      a: {
        sv: "Det är aldrig publikt utan det är bara ni och vi som samlar in kunddata för att förbättra och träna agenterna utifrån ert bolag.",
        en: "It is never public. Only you and we collect customer data, and it is used to improve and train the agents around your business."
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
  problemLabel: TOM,
  problemHeading: {
    sv: "En agent som hanterar *allt*.",
    en: "One agent that handles *all of it*."
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
  placeLabel: TOM,
  placeHeading: {
    sv: "Svarar på svenska, med *era* ord.",
    en: "Answers in Swedish, in *your* words."
  },
  placeBody: {
    sv: "Agenten hämtar formuleringarna ur er kunskapsbas, så tonen blir er egen och inte en översättning. Kunden märker att svaret kommer från er, inte från en generisk assistent.",
    en: "The agent takes its phrasing from your knowledge base, so the tone is yours rather than a translation. The customer can tell the reply came from you and not from a generic assistant."
  },
  objectionsHeading: {
    sv: "Frågor och *Svar*.",
    en: "Questions and *answers*."
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
