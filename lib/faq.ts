import type { Localized } from "@/lib/i18n";

/**
 * Sajtens gemensamma frågor och svar.
 *
 * ## Varför den inte återanvänder `objections` i copy-sections.ts
 *
 * De frågorna är TRE PER PRODUKT och står på respektive produktsida — leads
 * får sina, supporten sina. De besvarar "varför just den här agenten", vilket
 * är en säljfråga mitt i ett säljargument.
 *
 * Den här listan besvarar något annat: vad plattformen är, var datan kommer
 * ifrån, vad den kostar, hur man säger upp. Det är frågor en köpare ställer
 * FÖRE hen valt produkt, och att smyga in dem i leads-sidans invändningar
 * hade gjort dem osynliga för den som kom för supporten.
 *
 * ## Svaren är kontrollerade mot koden, inte påhittade
 *
 * Varje svar som påstår något om hur produkten fungerar går att härleda till
 * en fil. Där påståendet skulle bli ett löfte om pris, uppsägningstid eller
 * avtal står i stället `TODO: bekräfta med Sebbe` — de sakerna avgörs av ett
 * avtal och inte av en kodbas, och ett vackert formulerat antagande på en
 * publik sida är ett löfte vi inte vet om vi kan hålla.
 */

export type FaqKategori = "plattform" | "data" | "pris" | "juridik" | "igang";

export type FaqPost = {
  /** Stabilt id — används som DOM-id och som `#ankare` i url:en. */
  id: string;
  kategori: FaqKategori;
  fraga: Localized;
  /** Svaret som stycken. Flera element i stället för en textklump med \n. */
  svar: Localized[];
  /** Valfri länk vidare, när svaret har ett dokument bakom sig. */
  lank?: { etikett: Localized; href: string };
};

export const FAQ_KATEGORIER: { nyckel: FaqKategori; etikett: Localized }[] = [
  { nyckel: "plattform", etikett: { sv: "Plattformen", en: "The platform" } },
  { nyckel: "data", etikett: { sv: "Data och källor", en: "Data and sources" } },
  { nyckel: "pris", etikett: { sv: "Pris och avtal", en: "Pricing and contract" } },
  { nyckel: "juridik", etikett: { sv: "Dataskydd", en: "Data protection" } },
  { nyckel: "igang", etikett: { sv: "Komma igång", en: "Getting started" } }
];

export const FAQ: FaqPost[] = [
  // -- Plattformen ---------------------------------------------------------
  {
    id: "vad-ar-snajp",
    kategori: "plattform",
    fraga: { sv: "Vad är Snajp, konkret?", en: "What is Snajp, concretely?" },
    svar: [
      {
        sv:
          "Tre agenter i en arbetsyta. Leads-agenten söker upp företag som liknar era befintliga " +
          "kunder och skriver ett förslag till mejl. Supportagenten läser kundtjänstinkorgen, " +
          "sorterar ärendena och föreslår svar ur er egen kunskapsbas. Bokföringsagenten läser av " +
          "kvitton och fakturor och föreslår kontering.",
        en:
          "Three agents in one workspace. The leads agent finds companies that resemble your " +
          "existing customers and drafts an email. The support agent reads your service inbox, " +
          "sorts the cases and proposes replies from your own knowledge base. The bookkeeping " +
          "agent reads receipts and invoices and proposes the accounting entries."
      },
      {
        sv:
          "Gemensamt för alla tre: de föreslår, en människa godkänner. Det finns ingen kodväg " +
          "där en agent skickar ett mejl eller lämnar in något till en myndighet på egen hand.",
        en:
          "What they share: they propose, a person approves. There is no code path where an " +
          "agent sends an email or files anything with an authority on its own."
      }
    ]
  },
  {
    id: "manniska-godkanner",
    kategori: "plattform",
    fraga: {
      sv: "Skickar agenten något utan att jag sett det?",
      en: "Does the agent send anything without me seeing it?"
    },
    svar: [
      {
        sv:
          "Nej. Utkast är standardläget, och sändknappen är er. Bokföringsagenten har dessutom " +
          "en spärr som fäller svar där ett belopp inte går att härleda till ett underlag: hellre " +
          "”jag vet inte” än en siffra som ser rimlig ut.",
        en:
          "No. Draft is the default state, and the send button is yours. The bookkeeping agent " +
          "also has a gate that rejects answers where a figure cannot be traced to a document: " +
          "better ”I don't know” than a number that merely looks plausible."
      }
    ]
  },
  {
    id: "sprak",
    kategori: "plattform",
    fraga: { sv: "Fungerar det på svenska?", en: "Does it work in Swedish?" },
    svar: [
      {
        sv:
          "Ja. Agenterna hämtar sina formuleringar ur er kunskapsbas, så tonen blir er egen och " +
          "inte en översättning. Produkten är byggd för svensk B2B från början, inte lokaliserad " +
          "i efterhand.",
        en:
          "Yes. The agents take their phrasing from your knowledge base, so the tone is yours " +
          "rather than a translation. The product was built for Swedish B2B from the start, not " +
          "localised afterwards."
      }
    ]
  },

  // -- Data och källor -----------------------------------------------------
  {
    id: "varifran-datan",
    kategori: "data",
    fraga: {
      sv: "Var kommer uppgifterna om företagen ifrån?",
      en: "Where does the company data come from?"
    },
    svar: [
      {
        sv:
          "Öppna och offentliga källor: bolagets egen webbplats, deras platsannonser och " +
          "pressmeddelanden. Uppgifterna gäller företag och yrkesroller, inte privatpersoner.",
        en:
          "Open, public sources: the company's own website, their job ads and press releases. " +
          "The data concerns companies and professional roles, not private individuals."
      },
      {
        sv:
          "Vi skrapar inte sociala medier och köper inte listor med privata profiler. Hittar " +
          "agenten inte tillräckligt om ett bolag lämnar den fältet tomt i stället för att fylla " +
          "det med en gissning.",
        en:
          "We do not scrape social media and we do not buy lists of private profiles. If the " +
          "agent cannot find enough about a company it leaves the field empty rather than " +
          "filling it with a guess."
      }
    ],
    lank: {
      etikett: { sv: "Läs hela integritetspolicyn", en: "Read the full privacy policy" },
      href: "/integritetspolicy"
    }
  },
  {
    id: "vad-hander-med-var-data",
    kategori: "data",
    fraga: {
      sv: "Vad händer med vår egen kunddata?",
      en: "What happens to our own customer data?"
    },
    svar: [
      {
        sv:
          "Den är er. Varje arbetsyta är avskild i databasen med radsäkerhet, alltså en spärr i " +
          "databasen själv och inte bara i koden ovanpå. Kunddata blir aldrig publik och delas " +
          "aldrig med andra kunder.",
        en:
          "It is yours. Every workspace is isolated in the database with row level security, a " +
          "gate in the database itself and not only in the code above it. Customer data is never " +
          "public and is never shared with other customers."
      },
      {
        sv:
          "Innehållet i ett kundmejl skickas till den AI-leverantör som driver modellen, för att " +
          "svaret ska kunna skrivas. Vilken leverantör det är, och var behandlingen sker, står i " +
          "integritetspolicyn.",
        en:
          "The content of a customer email is sent to the AI provider running the model so the " +
          "reply can be written. Which provider that is, and where the processing happens, is " +
          "stated in the privacy policy."
      }
    ],
    lank: {
      etikett: { sv: "Underleverantörer och var de finns", en: "Sub-processors and where they are" },
      href: "/integritetspolicy"
    }
  },
  {
    id: "kvitton-sparas",
    kategori: "data",
    fraga: {
      sv: "Sparar ni kvittona vi laddar upp?",
      en: "Do you store the receipts we upload?"
    },
    svar: [
      {
        sv:
          "Nej. Filen finns i minnet under själva avläsningen och kastas sedan. Kvar blir de " +
          "avlästa fälten och ett kontrollsummevärde som gör att samma kvitto går att känna igen " +
          "om det laddas upp två gånger. Originalet ska arkiveras i ert eget system, eftersom " +
          "bokföringslagen lägger det ansvaret på den som för bokföringen.",
        en:
          "No. The file exists in memory during the reading itself and is then discarded. What " +
          "remains are the extracted fields and a checksum that lets us recognise the same " +
          "receipt if it is uploaded twice. The original should be archived in your own system, " +
          "since Swedish bookkeeping law places that duty on whoever keeps the books."
      }
    ]
  },

  // -- Pris och avtal ------------------------------------------------------
  {
    id: "kostar",
    kategori: "pris",
    fraga: { sv: "Vad kostar det?", en: "What does it cost?" },
    svar: [
      {
        sv:
          "Priserna per plan står på prissidan. Vilket paket som passar beror på hur många " +
          "agenter ni vill använda och hur stor volym ni har, och det är den frågan en demo " +
          "är till för.",
        en:
          "The price per plan is listed on the pricing page. Which package fits depends on how " +
          "many agents you want and what volume you have, and that is what a demo is for."
      }
    ],
    lank: { etikett: { sv: "Se priser och planer", en: "See pricing and plans" }, href: "/#priser" }
  },
  {
    id: "gratis-period",
    kategori: "pris",
    fraga: {
      sv: "Finns det en kostnadsfri testperiod?",
      en: "Is there a free trial?"
    },
    svar: [
      {
        // TODO: bekräfta med Sebbe — längd på testperiod och om kortuppgifter
        // krävs. Skrivs INTE ut som ett löfte förrän det är bestämt: en
        // utlovad provperiod som inte finns är ett avtalsbrott vid första
        // kunden som åberopar den.
        sv:
          "Alla tre agenterna går att prova direkt i webbläsaren utan konto, med exempeldata. " +
          "Vill ni köra mot er egen inkorg eller era egna kvitton sätter vi upp det tillsammans " +
          "under demon.",
        en:
          "All three agents can be tried straight in the browser without an account, using " +
          "sample data. If you want to run against your own inbox or your own receipts we set " +
          "that up together during the demo."
      }
    ],
    lank: { etikett: { sv: "Boka en demo", en: "Book a demo" }, href: "/boka-demo" }
  },
  {
    id: "saga-upp",
    kategori: "pris",
    fraga: {
      sv: "Kan vi säga upp när som helst?",
      en: "Can we cancel at any time?"
    },
    svar: [
      {
        // TODO: bekräfta med Sebbe — bindningstid, uppsägningstid och vad som
        // händer med data vid uppsägning. Villkorssidan är den text som
        // gäller; den här raden får inte säga något den inte säger.
        sv:
          "Uppsägningstid och bindningstid framgår av avtalsvillkoren. Er data går att få " +
          "utlämnad, och radering sker på begäran — det är en rättighet ni har oavsett vad " +
          "avtalet säger om uppsägning.",
        en:
          "Notice period and any minimum term are set out in the terms. Your data can be " +
          "exported, and deletion happens on request, which is a right you have regardless of " +
          "what the contract says about termination."
      }
    ],
    lank: { etikett: { sv: "Läs avtalsvillkoren", en: "Read the terms" }, href: "/villkor" }
  },

  // -- Dataskydd -----------------------------------------------------------
  {
    id: "gdpr",
    kategori: "juridik",
    fraga: {
      sv: "Hur hanterar ni GDPR och personuppgifter?",
      en: "How do you handle GDPR and personal data?"
    },
    svar: [
      {
        sv:
          "För era kontouppgifter är vi personuppgiftsansvariga. För kunddatan i produkten är " +
          "ni ansvariga och vi biträde, under ett personuppgiftsbiträdesavtal. Den rättsliga " +
          "grunden för B2B-prospektering är berättigat intresse.",
        en:
          "For your account details we are the controller. For the customer data inside the " +
          "product you are the controller and we are the processor, under a data processing " +
          "agreement. The legal basis for B2B prospecting is legitimate interest."
      },
      {
        sv:
          "Varje utskick bär en avregistreringslänk som fungerar med ett klick, och en adress " +
          "som avregistrerat sig spärras för framtida utskick.",
        en:
          "Every outgoing email carries a one-click unsubscribe link, and an address that has " +
          "unsubscribed is blocked from future sends."
      }
    ],
    lank: { etikett: { sv: "Till Dataskydd", en: "To Data protection" }, href: "/integritetspolicy" }
  },
  {
    id: "var-lagras-data",
    kategori: "juridik",
    fraga: { sv: "Var lagras datan?", en: "Where is the data stored?" },
    svar: [
      {
        sv:
          "Databasen ligger inom EU. Modellanropen går till en AI-leverantör, och vilken det är " +
          "samt var den behandlingen sker står specificerat i integritetspolicyn — vi räknar upp " +
          "underleverantörerna med namn i stället för att skriva ”betrodda partners”.",
        en:
          "The database sits inside the EU. Model calls go to an AI provider, and which one it " +
          "is and where that processing happens is specified in the privacy policy. We name our " +
          "sub-processors instead of writing ”trusted partners”."
      }
    ],
    lank: {
      etikett: { sv: "Se listan över underleverantörer", en: "See the sub-processor list" },
      href: "/integritetspolicy"
    }
  },

  // -- Komma igång ---------------------------------------------------------
  {
    id: "komma-igang",
    kategori: "igang",
    fraga: { sv: "Hur kommer vi igång?", en: "How do we get started?" },
    svar: [
      {
        sv:
          "Boka en demo på 15–20 minuter. Vi går igenom era ärenden eller era kunder live, ni " +
          "ser vad agenten föreslår, och vi säger rakt ut om vi tror att det passar er. Inga " +
          "förpliktelser.",
        en:
          "Book a 15–20 minute demo. We go through your cases or your customers live, you " +
          "see what the agent proposes, and we say plainly whether we think it fits. No " +
          "obligations."
      }
    ],
    lank: { etikett: { sv: "Boka demo", en: "Book a demo" }, href: "/boka-demo" }
  },
  {
    id: "hur-lang-tid",
    kategori: "igang",
    fraga: {
      sv: "Hur lång tid tar det att komma igång?",
      en: "How long does setup take?"
    },
    svar: [
      {
        sv:
          "Att koppla en inkorg och fylla kunskapsbasen är dagens arbete, inte månadens. Det " +
          "som tar tid är att komma överens om tonen i svaren, och det arbetet gör ni bäst " +
          "genom att köra agenten i utkastläge ett par dagar och rätta det som blir fel.",
        en:
          "Connecting an inbox and filling the knowledge base is a day's work, not a month's. " +
          "What takes time is agreeing on the tone of the replies, and that is best done by " +
          "running the agent in draft mode for a few days and correcting what comes out wrong."
      }
    ]
  }
];
