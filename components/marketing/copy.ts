import type { Localized } from "@/lib/i18n";

/**
 * Marknadssidornas copy, en post per text.
 *
 * ## Regeln som håller sidorna isär
 *
 * `leadsCopy` får bara handla om utgående försäljning och `supportCopy` bara om
 * kundtjänst. Det låter självklart och var ändå fel: hjältetexten på
 * leads-sidan beskrev en kundtjänstinkorg ("50–70 % av det repetitiva jobbet")
 * medan rubriken lovade säljmejl. En besökare som kom via /leads läste alltså
 * om fel produkt i första stycket.
 *
 * Samma sak gäller de delade sektionerna: UspSection tar numera emot vilken
 * produkt sidan visar, i stället för att bära en text som beskrev kundtjänst
 * på båda sidorna.
 *
 * ## Stjärnorna i texterna
 *
 * `*ord*` renderas kursivt i den gula accentfärgen (se `Display` i
 * LandingPhoto). Det är den enda kursiveringen på sidorna, och den är alltid
 * gul — kursivt utan färg finns inte här.
 *
 * Oförändrade regler: inga påhittade bevis, inga tankstreck i någotdera språket.
 */

/**
 * Kontaktadressen på ETT ställe. Den stod tidigare inskriven i tolv `mailto:`
 * i fyra filer, och ett byte av adress betydde tolv chanser att missa en.
 */
export const KONTAKT_MEJL = "Snajpsupport@gmail.com";

/** `mailto:` med adressen förifylld i mottagarfältet. */
export function mejlaOss(amne?: string): string {
  return amne
    ? `mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent(amne)}`
    : `mailto:${KONTAKT_MEJL}`;
}

export type ProductCopy = {
  word: Localized;
  headline: Localized;
  lede: Localized;
  cta: Localized;
  demoHeading: Localized;
  demoLede: Localized;
  /** Tom sträng betyder att ingen finstilt rad renderas under demon. */
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
    sv: "Tveka inte på att *kontakta oss*.",
    en: "Do not hesitate to *get in touch*."
  },
  closingBody: {
    sv: "Har något inte fungerat som det ska, eller har du bara en fråga? Hör av dig så hjälper vi dig vidare.",
    en: "Has something not worked the way it should, or do you simply have a question? Get in touch and we will help you on."
  },
  closingCta: { sv: KONTAKT_MEJL, en: KONTAKT_MEJL },
  //: Ersätter "Sverige · GDPR · RLS" i hjältebilden.
  //:
  //: Den raden var tre förkortningar där två är interna: RLS är en
  //: databasmekanism, och en besökare som inte bygger programvara läser den som
  //: brus. Det som faktiskt betyder något för en svensk B2B-köpare är vem de
  //: köper av — och det står nu i stället.
  heroTrust: {
    sv: "Utvecklat i Sverige",
    en: "Built in Sweden"
  },
  demoLeads: { sv: "Prova leads-agenten", en: "Try the leads agent" },
  demoSupport: { sv: "Prova kundtjänstagenten", en: "Try the support agent" },
  demoBokforing: { sv: "Prova bokföringsagenten", en: "Try the bookkeeping agent" },
  footerKontakt: { sv: "Kontakt", en: "Contact" },
  menyKontakt: { sv: "Kontakta oss", en: "Contact us" },
  menyPriser: { sv: "Prislista", en: "Pricing" },
  menyFragor: { sv: "Frågor och svar", en: "Questions and answers" },
  menyVilka: { sv: "Vilka är vi", en: "Who we are" },
  menyGdpr: { sv: "GDPR och data", en: "GDPR and data" },
  menyEtikett: { sv: "Meny", en: "Menu" },
  //: Avsnittet "Vilka är vi". Skrivet för den som undrar vem de skulle köpa av
  //: — inte som en grundarberättelse. Svensk B2B väger vem som står bakom, och
  //: den frågan besvaras inte av en produktbeskrivning.
  vilkaRubrik: { sv: "Vilka är vi", en: "Who we are" },
  vilkaRubrikStor: {
    sv: "Ett nystartat svenskt bolag som utvecklar ett effektivare verktyg för ditt företag.",
    en: "A new Swedish company building a tool that makes your company more efficient."
  },
  vilkaText1: {
    sv: "Snajp är byggt i Göteborg och Umeå av ett litet team. Vi säljer till svensk B2B, " +
      "och vi använder alla tre agenterna i vår egen verksamhet — det är därför spärrarna finns " +
      "där de finns: vi har själva stått med ett utkast som inte borde gå ut.",
    en: "Snajp is built in Gothenburg and Umeå by a small team. We sell to Swedish B2B, and we " +
      "run all three agents in our own business — that is why the safeguards sit where they do: we " +
      "have stood with a draft that should not go out."
  },
  vilkaText2: {
    sv: "Vi tar hellre ett nej i tid än ett ja som inte håller. Därför säger agenterna " +
      "ifrån när de saknar underlag i stället för att gissa, och därför säljer vi hellre " +
      "rätt paket än det dyraste.",
    en: "We would rather have an early no than a yes that does not hold. That is why the agent " +
      "says so when it lacks grounding instead of guessing, and why we would rather sell the " +
      "right plan than the most expensive one."
  },
  footerPlats: { sv: "Göteborg och Umeå · Sverige", en: "Gothenburg and Umeå · Sweden" },
  gdprRubrik: { sv: "Kunddata hanteras skilt, aldrig publikt", en: "Customer data is kept separate, never public" },
  //: Texten säger numera OCKSÅ att mejltexten skickas till en AI-leverantör.
  //:
  //: Den gjorde inte det förut, och det var den sortens utelämnande som inte
  //: syns förrän en inköpares jurist läser stycket och undrar vad mer som
  //: inte står där. Produkten ÄR en språkmodell; att inte nämna att texten
  //: bearbetas av en var att sälja på en halv beskrivning.
  //:
  //: Formuleringen är gjord mer specifik, inte mer försiktig. "Vi säger vad
  //: vi faktiskt gör" väger tyngre hos en svensk B2B-köpare än trygghetsord,
  //: och isoleringen mellan kunder är fortfarande det första som står.
  gdprText: {
    sv: "Varje kunds data ligger i en egen avgränsning och kan bara läsas av den kunden — " +
      "det är en spärr i databasen, inte en inställning i koden. Ingenting publiceras, och " +
      "ingenting delas mellan kunder. För att skriva svaret skickas mejltexten till vår " +
      "AI-leverantör, som behandlar den åt oss och inte tränar på den. Inget mejl går ut " +
      "utan att en människa godkänt det.",
    en: "Every customer's data sits in its own boundary and can only be read by that customer — " +
      "enforced in the database, not by a setting in the code. Nothing is published, and nothing " +
      "is shared between customers. To write the reply, the email text is sent to our AI " +
      "provider, which processes it on our behalf and does not train on it. No email goes out " +
      "without a person approving it."
  },
  gdprLank: {
    sv: "Läs hela integritetspolicyn",
    en: "Read the full privacy policy"
  }
} satisfies Record<string, Localized>;

export const leadsCopy: ProductCopy = {
  word: { sv: "Leads", en: "Leads" },
  headline: {
    sv: "Din säljare som aldrig *sover*.",
    en: "Your sales rep that never *sleeps*."
  },
  lede: {
    sv: "Leads-agenten letar prospekt utifrån er produkt, gör en behovsanalys och skriver mejlet medan tajmingen fortfarande gäller. Ni läser igenom och godkänner innan något går ut.",
    en: "The leads agent finds prospects based on your product, works out what they need and writes the email while the timing still holds. You read it through and approve before anything goes out."
  },
  cta: { sv: "Testa Email Studio", en: "Try Email Studio" },
  demoHeading: {
    sv: "Redigera mailet med ett *knapptryck*.",
    en: "Edit the email with a *single click*."
  },
  demoLede: {
    sv: "Ändra, förbättra eller skriv om exempelmailet nedan genom att trycka på knapparna.",
    en: "Change, improve or rewrite the example email below by pressing the buttons."
  },
  exampleNote: { sv: "", en: "" },
  stepsHeading: {
    sv: "Tre steg, och du äger *vartenda* ett.",
    en: "Three steps, and *every one* is yours."
  },
  steps: [
    {
      title: { sv: "Hittar nya leads", en: "Finds new leads" },
      body: {
        sv: "Ett bolag som just investerat i en ny lokal. Ett bolag som behöver höja effektiviteten. Agenterna letar nya kunder baserat på er produkt.",
        en: "A company that just invested in new premises. A company that needs to raise its efficiency. The agent finds new customers based on your product."
      }
    },
    {
      title: { sv: "Formulerar ett personligt mail", en: "Writes a personal email" },
      body: {
        sv: "Skriver en offert eller ett erbjudande som går in i mailet, och som du ändrar på enkelt genom ett knapptryck.",
        en: "It writes a quote or an offer straight into the email, and you change it easily with a single click."
      }
    },
    {
      title: { sv: "Du godkänner", en: "You approve" },
      body: {
        sv: "Du behåller alltid kontrollen innan något skickas. Ett klick på Godkänn och skicka.",
        en: "You stay in control before anything is sent. One click on Approve and send."
      }
    }
  ],
  limitsHeading: {
    sv: "Byggd för att vara tryggt att använda",
    en: "Built to be safe to use"
  },
  limits: [
    {
      sv: "Skickar aldrig något du inte har läst och godkänt.",
      en: "Never sends anything you have not read and approved."
    },
    {
      sv: "Slutar följa upp i samma sekund som någon svarar.",
      en: "Stops following up the second someone replies."
    },
    {
      sv: "Skriver inte samma mejl till hundra bolag.",
      en: "Does not write the same email to a hundred companies."
    },
    {
      sv: "Säkerhet och kontroll från början.",
      en: "Safety and control from the start."
    }
  ]
};

export const supportCopy: ProductCopy = {
  word: { sv: "Support", en: "Support" },
  headline: {
    sv: "*Support 24/7*",
    en: "*Support 24/7*"
  },
  lede: {
    sv: "Vi räknar med att ta bort 50–70 % av det repetitiva jobbet i er kundtjänstinkorg. Mejl sorteras automatiskt i rätt fack och får färdiga, korrekta svar — ni behåller alltid kontrollen.",
    en: "We expect to remove 50–70 % of the repetitive work in your support inbox. Emails are sorted into the right category and get complete, accurate replies — you always stay in control."
  },
  cta: { sv: "Testa agenten", en: "Try the agent" },
  demoHeading: {
    sv: "Skriv som en kund och följ ärendet *hela vägen*.",
    en: "Write as a customer and follow the case *all the way*."
  },
  demoLede: {
    sv: "Ställ frågan i egna ord. Du ser vilket fack ärendet hamnar i, hur säkra agenterna är och vilket svar de föreslår. Ingen inloggning.",
    en: "Ask in your own words. You see which queue the case lands in, how confident the agents are and the reply they propose. No login."
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
  limitsHeading: {
    sv: "Byggd för att vara tryggt att använda",
    en: "Built to be safe to use"
  },
  limits: [
    {
      sv: "Hittar aldrig på ett svar. Skickar det vidare till manuell hantering.",
      en: "Never invents an answer. It passes the case on for manual handling."
    },
    {
      sv: "Lovar inga betalningar, inga återbetalningar och fattar inga juridiska beslut.",
      en: "Promises no payments, no refunds and makes no legal decisions."
    },
    {
      sv: "Säkerhet och kontroll från början.",
      en: "Safety and control from the start."
    },
    {
      sv: "Agenterna vet sina gränser.",
      en: "The agents know their limits."
    }
  ]
};

/**
 * Bokföringen. Tredje produkten, och den som lovar MINST med flit.
 *
 * De två andra beskriver vad agenten gör åt kunden. Den här beskriver lika
 * tydligt vad den INTE gör: den bokför inte, den lämnar ingenting till
 * Skatteverket och den ersätter ingen redovisningskonsult. Samma förbehåll
 * som `FORBEHALL` i api/bookkeeping.py, formulerat för en besökare i stället
 * för för ett JSON-svar.
 *
 * Det är inte försiktighet för sakens skull. En produkt som antyder att den
 * sköter bokföringen tar på sig ett ansvar den varken har eller kan bära, och
 * kunden upptäcker skillnaden vid en revision.
 */
export const bokforingCopy: ProductCopy = {
  word: { sv: "Bokföring", en: "Bookkeeping" },
  headline: {
    sv: "Kvittohögen blir ett *underlag*.",
    en: "The pile of receipts becomes a *record*."
  },
  lede: {
    sv: "Fotografera kvittot. Agenten läser av datum, belopp och moms, föreslår kontering och räknar perioden. Du godkänner innan något förs in i er bokföring.",
    en: "Photograph the receipt. The agent reads off date, amount and VAT, proposes the entries and totals the period. You approve before anything enters your books."
  },
  cta: { sv: "Se hur det fungerar", en: "See how it works" },
  demoHeading: {
    sv: "Ett kvitto, *avläst* och konterat.",
    en: "One receipt, *read* and posted."
  },
  demoLede: {
    sv: "Exemplet nedan visar hela vägen: avläsningen, verifikatet och periodsumman.",
    en: "The example below shows the whole path: the reading, the entry and the period total."
  },
  exampleNote: {
    sv: "Exempel. Påhittat underlag, inte en riktig körning hos en kund.",
    en: "Example. A made-up document, not a real run for a customer."
  },
  stepsHeading: {
    sv: "Tre steg, och koden räknar *varenda* siffra.",
    en: "Three steps, and the code does *every* calculation."
  },
  steps: [
    {
      title: { sv: "Läser av underlaget", en: "Reads the document" },
      body: {
        sv: "Datum, motpart, totalbelopp och momssats. Står ett fält inte på kvittot gissas det inte, utan går till granskning.",
        en: "Date, counterparty, total and VAT rate. If a field is not on the receipt it is not guessed, it goes to review."
      }
    },
    {
      title: { sv: "Föreslår konteringen", en: "Proposes the entries" },
      body: {
        sv: "Modellen väljer kategori, koden väljer konto ur BAS och bygger raderna. Verifikatet balanserar därför av konstruktion.",
        en: "The model picks a category, the code picks the account from the Swedish BAS chart and builds the rows. The entry balances by construction."
      }
    },
    {
      title: { sv: "Du godkänner", en: "You approve" },
      body: {
        sv: "Perioden summeras först när den går ihop. Går den inte ihop får du bristerna i stället för trovärdiga siffror.",
        en: "The period is totalled only when it balances. If it does not, you get the gaps instead of plausible numbers."
      }
    }
  ],
  limitsHeading: {
    sv: "Vad den inte gör",
    en: "What it does not do"
  },
  limits: [
    {
      sv: "Bokför ingenting. Den föreslår, du godkänner och för in.",
      en: "Books nothing. It proposes, you approve and enter."
    },
    {
      sv: "Lämnar ingenting till Skatteverket eller Bolagsverket.",
      en: "Files nothing with the Swedish Tax Agency or Companies Registration Office."
    },
    {
      sv: "Ersätter ingen auktoriserad redovisningskonsult.",
      en: "Replaces no authorised accounting consultant."
    },
    {
      sv: "Räknar aldrig ett belopp i modellen. Momsen räknas i kod.",
      en: "Never has the model calculate an amount. VAT is calculated in code."
    }
  ]
};

export const productCopy = {
  leads: leadsCopy,
  support: supportCopy,
  bookkeeping: bokforingCopy
} as const;
