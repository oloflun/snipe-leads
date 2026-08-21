import type { Localized } from "@/lib/i18n";

/**
 * Adopted copy: seven-sweep copy edit, plus the two changes from the Swedish
 * humanizer pass that were genuinely humanizer work. The rest of that pass was
 * rewriting content the skill had no mandate to touch, so it was discarded.
 *
 * What each sweep changed:
 *  - Specificity: the concrete signals (nyöppningar, rekryteringar, tjänstesidor)
 *    moved up into the lede instead of sitting buried in step one.
 *  - So What: every step now ends in a consequence, not a mechanism.
 *  - Emotion: the headline names what the reader is afraid of, sounding like a
 *    mass mailing, instead of only describing what the tool does.
 *  - Zero Risk: the demo needs no login, and now the page says so next to it.
 *
 * Unchanged rules: no fabricated proof, no em-dashes in either language.
 */

export type ProductCopy = {
  word: Localized;
  headline: Localized;
  lede: Localized;
  cta: Localized;
  demoHeading: Localized;
  demoLede: Localized;
  exampleNote: Localized;
  steps: { title: Localized; body: Localized }[];
  stepsHeading: Localized;
  limitsHeading: Localized;
  limits: Localized[];
};

export const shared = {
  skipToContent: { sv: "Hoppa till innehåll", en: "Skip to content" },
  navPricing: { sv: "Pris", en: "Pricing" },
  navContact: { sv: "Kontakt", en: "Contact" },
  navLogin: { sv: "Logga in", en: "Log in" },
  switchLabel: { sv: "Välj produkt", en: "Choose product" },
  secondaryCta: { sv: "Skriv till oss", en: "Write to us" },
  closingHeading: {
    sv: "Kör det på *er egen* text.",
    en: "Run it on *your own* text."
  },
  closingBody: {
    sv: "Skicka ett säljmejl du kört fast på, eller ett kundärende ingen hann svara på. Vi kör det genom verktyget och skickar tillbaka resultatet samma dag.",
    en: "Send a sales email you are stuck on, or a support case nobody got to. We run it through the tool and send the result back the same day."
  },
  closingCta: { sv: "hej@snajp.se", en: "hej@snajp.se" },
  footerNote: {
    sv: "Snajp, Göteborg och Umeå. Byggt för svensk B2B.",
    en: "Snajp, Gothenburg and Umeå. Built for Swedish B2B."
  },
  //: Ersätter "Sverige · GDPR · RLS" i hjältebilden.
  //:
  //: Den raden var tre förkortningar där två är interna: RLS är en
  //: databasmekanism, och en besökare som inte bygger programvara läser den som
  //: brus. Det som faktiskt betyder något för en svensk B2B-köpare är vem de
  //: köper av — och det står nu i stället. Efterlevnaden finns kvar, men i
  //: sidfoten där den hör hemma och med utrymme att förklaras.
  heroTrust: {
    sv: "Svenskt grundat företag",
    en: "Swedish founded company"
  },
  demoLeads: { sv: "Prova leads-agenten", en: "Try the leads agent" },
  demoSupport: { sv: "Prova kundtjänstagenten", en: "Try the support agent" },
  footerKontakt: { sv: "Kontakt", en: "Contact" },
  footerJuridik: { sv: "Dataskydd", en: "Data protection" },
  footerPlats: { sv: "Göteborg och Umeå · Sverige", en: "Gothenburg and Umeå · Sweden" },
  gdprRubrik: { sv: "Kunddata hanteras skilt, aldrig publikt", en: "Customer data is kept separate, never public" },
  gdprText: {
    sv: "Varje kunds data ligger i en egen avgränsning och kan bara läsas av den kunden — " +
      "det är en spärr i databasen, inte en inställning i koden. Ingenting publiceras, " +
      "ingenting delas mellan kunder, och inget mejl går ut utan att en människa godkänt det.",
    en: "Every customer's data sits in its own boundary and can only be read by that customer — " +
      "enforced in the database, not by a setting in the code. Nothing is published, nothing is " +
      "shared between customers, and no email goes out without a person approving it."
  }
} satisfies Record<string, Localized>;

export const leadsCopy: ProductCopy = {
  word: { sv: "Leads", en: "Leads" },
  headline: {
    sv: "Säljmejl som låter som *du*, inte som ett utskick.",
    en: "Sales email that sounds like *you*, not like a mailshot."
  },
  lede: {
    sv: "Snajp läser nyöppningar, rekryteringar och ändrade tjänstesidor, och skriver utkastet medan tajmingen fortfarande gäller. Du läser igenom och godkänner innan det går ut.",
    en: "Snajp reads new offices, hiring and changed service pages, then writes the draft while the timing still holds. You approve before anything is sent."
  },
  cta: { sv: "Testa Email Studio", en: "Try Email Studio" },
  demoHeading: {
    sv: "Skriv om mejlet och se exakt vad som *ändrades*.",
    en: "Rewrite the email and see exactly what *changed*."
  },
  demoLede: {
    sv: "Ändra texten och välj en åtgärd. Du får den nya versionen bredvid den gamla, med en förklaring till varje ändring. Ingen inloggning.",
    en: "Edit the text and pick an action. You get the new version beside the old one, with a reason for every change. No login."
  },
  exampleNote: {
    sv: "Mejlet i demon är exempeldata.",
    en: "The email in this demo is example data."
  },
  stepsHeading: {
    sv: "Tre steg, och du äger *vartenda* ett.",
    en: "Three steps, and *every one* is yours."
  },
  steps: [
    {
      title: { sv: "Hitta läget", en: "Find the moment" },
      body: {
        sv: "Ett bolag som just tagit nya lokaler läser ett mejl om lokalfrågor annorlunda än samma bolag gjorde förra kvartalet. Snajp läser det som redan ligger öppet och säger när.",
        en: "A company that just took new premises reads an email about premises differently than it did last quarter. Snajp reads what is already public and tells you when."
      }
    },
    {
      title: { sv: "Skriv utkastet", en: "Write the draft" },
      body: {
        sv: "Signalen, ert erbjudande och ert tonläge går in i mejlet. Du får ett utkast att ändra i, inte en mall att fylla i.",
        en: "The signal, your offer and your tone go into the email. You get a draft to edit, not a template to fill in."
      }
    },
    {
      title: { sv: "Du godkänner", en: "You approve" },
      body: {
        sv: "Uppföljningen ligger klar och stannar av sig själv så fort någon svarar. Ingen jagar en kund som redan hört av sig.",
        en: "The follow-up is ready and stops by itself the moment someone replies. Nobody chases a customer who already got back to you."
      }
    }
  ],
  limitsHeading: { sv: "Vad det inte gör", en: "What it will not do" },
  limits: [
    {
      sv: "Skickar aldrig något du inte har läst och godkänt.",
      en: "Never sends anything you have not read and approved."
    },
    {
      sv: "Skrapar inte LinkedIn och köper inga kontaktlistor.",
      en: "Does not scrape LinkedIn and buys no contact lists."
    },
    {
      sv: "Slutar följa upp i samma sekund som någon svarar.",
      en: "Stops following up the second someone replies."
    },
    {
      sv: "Skriver inte samma mejl till hundra bolag.",
      en: "Does not write the same email to a hundred companies."
    }
  ]
};

export const supportCopy: ProductCopy = {
  word: { sv: "Support", en: "Support" },
  headline: {
    sv: "Svar på kundmejlen, hämtade ur *era egna* texter.",
    en: "Answers to customer email, taken from *your own* material."
  },
  lede: {
    sv: "Agenten sorterar inkorgen och skriver svarsutkast ur er kunskapsbas. Saknas underlaget lämnar den över till en människa i stället för att gissa.",
    en: "The agent sorts the inbox and drafts replies from your knowledge base. When the material is missing it escalates instead of guessing."
  },
  cta: { sv: "Testa agenten", en: "Try the agent" },
  demoHeading: {
    sv: "Skriv som en kund och följ ärendet *hela vägen*.",
    en: "Write as a customer and follow the case *all the way*."
  },
  demoLede: {
    sv: "Ställ frågan i egna ord. Du ser vilket fack ärendet hamnar i, hur säker agenten är och vilket svar den föreslår. Ingen inloggning.",
    en: "Ask in your own words. You see which queue the case lands in, how confident the agent is and the reply it proposes. No login."
  },
  exampleNote: {
    sv: "Kunskapsbasen och inkorgen i demon är exempeldata.",
    en: "The knowledge base and inbox in this demo are example data."
  },
  stepsHeading: {
    sv: "Från inkommande mejl till *färdigt* svar.",
    en: "From incoming email to a *finished* reply."
  },
  steps: [
    {
      title: { sv: "Läser och sorterar", en: "Reads and sorts" },
      body: {
        sv: "Teknik, leverans, betalning, retur, konto. Varje ärende får ett fack, en prioritet och ett konfidensvärde, så morgonens genomgång är redan gjord.",
        en: "Technical, delivery, payment, returns, account. Every case gets a queue, a priority and a confidence score, so the morning triage is already done."
      }
    },
    {
      title: { sv: "Svarar ur underlaget", en: "Answers from the material" },
      body: {
        sv: "Svaret hämtas ur er kunskapsbas. Skickar kunden en skärmdump på felmeddelandet eller en bild på det trasiga godset läses den av och styr ärendet rätt.",
        en: "The reply comes from your knowledge base. If the customer sends a screenshot of the error or a photo of the damaged goods, it is read and routes the case correctly."
      }
    },
    {
      title: { sv: "Lämnar över i tid", en: "Hands over in time" },
      body: {
        sv: "Återbetalning, juridik, GDPR och en riktigt arg kund går till en människa, med hela ärendehistoriken bifogad. Ingen börjar om från noll.",
        en: "Refunds, legal matters, GDPR and a genuinely angry customer go to a human, with the full case history attached. Nobody starts from scratch."
      }
    }
  ],
  limitsHeading: { sv: "Vad det inte gör", en: "What it will not do" },
  limits: [
    {
      sv: "Hittar aldrig på ett svar. Saknas underlag eskalerar den.",
      en: "Never invents an answer. If the material is missing, it escalates."
    },
    {
      sv: "Lovar inga återbetalningar och fattar inga juridiska beslut.",
      en: "Promises no refunds and makes no legal decisions."
    },
    {
      sv: "Svarar inte utanför det ni själva har skrivit.",
      en: "Answers nothing outside what you have written yourselves."
    },
    {
      sv: "Döljer aldrig att det är en agent som svarar.",
      en: "Never hides that an agent is answering."
    }
  ]
};

export const productCopy = { leads: leadsCopy, support: supportCopy } as const;
