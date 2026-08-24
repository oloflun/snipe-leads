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
        sv: "Agenterna skickar personliga och professionella mail till noggrant utvalda kunder. Du är alltid den som trycker godkänn och skicka.",
        en: "The agents write personal, professional emails to carefully chosen companies. You are always the one who presses approve and send."
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
    sv: "Agenterna hämtar formuleringarna ur er kunskapsbas, så tonen blir er egen och inte en översättning. Kunden märker att svaret kommer från er, inte från en generisk assistent.",
    en: "The agents take their phrasing from your knowledge base, so the tone is yours rather than a translation. The customer can tell the reply came from you and not from a generic assistant."
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

/**
 * Bokföringen. Invändningarna är hårdare ställda än för de två andra, och det
 * är avsiktligt: en läsare som funderar på att låta en maskin röra sin
 * bokföring har rätt att få de obekväma frågorna besvarade på sidan, inte
 * efter köpet.
 */
const bokforing: SectionCopy = {
  statementLabel: { sv: "Så tänker vi", en: "How we see it" },
  statement: {
    sv: "Bokföring är inte svårt. Det är segt, och det är därför det blir liggande.",
    en: "Bookkeeping is not hard. It is slow, and that is why it piles up."
  },
  problemLabel: TOM,
  problemHeading: {
    sv: "Kvittona ligger kvar tills det är *för sent*.",
    en: "Receipts sit there until it is *too late*."
  },
  problemBody: {
    sv: "Kvitton i plånboken, fakturor i mejlen, ett kontoutdrag som ska stämma. Ingen enskild sak tar lång tid. Att göra dem alla, i tid, varje månad, är det som inte blir gjort.",
    en: "Receipts in your wallet, invoices in your inbox, a bank statement that has to add up. No single task takes long. Doing all of them, on time, every month, is what does not get done."
  },
  problemPoints: [
    {
      sv: "Ett kvitto i taget tar två minuter. Gånger hundra kvitton per kvartal.",
      en: "One receipt takes two minutes. Times a hundred receipts a quarter."
    },
    {
      sv: "Ett tappat kvitto blir en kostnad du inte får dra av.",
      en: "A lost receipt becomes a cost you cannot deduct."
    },
    {
      sv: "Momsen ska stämma på öret, och det gör den sällan i huvudräkning.",
      en: "The VAT has to be right to the öre, and mental arithmetic rarely is."
    }
  ],
  placeLabel: TOM,
  placeHeading: {
    sv: "Byggt mot BAS-kontoplanen, med *dubbel bokföring* i koden.",
    en: "Built on the Swedish BAS chart, with *double entry* in the code."
  },
  placeBody: {
    sv: "Vi sitter i Göteborg och Umeå. Konteringen följer BAS, och verifikaten balanserar av konstruktion.",
    en: "We work from Gothenburg and Umeå. The entries follow BAS, and every voucher balances by construction."
  },
  objectionsHeading: {
    sv: "Det ni undrar",
    en: "What you are wondering"
  },
  objections: [
    {
      q: {
        sv: "Bokför den åt mig?",
        en: "Does it do my bookkeeping for me?"
      },
      a: {
        sv: "Nej. Den föreslår kontering och räknar perioden. Du godkänner och för in det i ert bokföringssystem, eller exporterar en SIE-fil dit.",
        en: "No. It proposes entries and totals the period. You approve and enter it in your accounting system, or export a SIE file to it."
      }
    },
    {
      q: {
        sv: "Kan jag lita på siffrorna?",
        en: "Can I trust the numbers?"
      },
      a: {
        sv: "Modellen räknar aldrig. Den läser av vad som står på kvittot, och all aritmetik görs i kod med exakta decimaltal. Går perioden inte ihop visas bristerna i stället för summorna.",
        en: "The model never calculates. It reads what the receipt says, and all arithmetic runs in code with exact decimals. If the period does not balance you get the gaps instead of the totals."
      }
    },
    {
      q: {
        sv: "Ersätter den min redovisningskonsult?",
        en: "Does it replace my accountant?"
      },
      a: {
        sv: "Nej, och den ska inte göra det. Den gör förarbetet så att konsulten får ett ordnat underlag i stället för en påse kvitton.",
        en: "No, and it should not. It does the preparation so your accountant gets an organised set of records instead of a bag of receipts."
      }
    },
    {
      q: {
        sv: "Vad händer med mina kvitton?",
        en: "What happens to my receipts?"
      },
      a: {
        sv: "Filen läses i minnet och kastas. Det som sparas är fälten som lästes av, plus en kontrollsumma av filen.",
        en: "The file is read in memory and discarded. What is stored are the fields that were read, plus a checksum of the file."
      }
    }
  ]
};

export const sectionCopy: Record<ProductKey, SectionCopy> = {
  leads,
  support,
  bookkeeping: bokforing
};

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
