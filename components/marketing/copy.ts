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
// Egen domän, inte gmail. Brevlådan finns hos Loopia och verifierades ta emot
// post 2026-08-29 (SMTP RCPT -> 250). En gmail-adress som publik kontaktväg för
// en tjänst som faktureras i tusenlappar per månad kostar trovärdighet i just
// det ögonblick en köpare bestämmer sig.
export const KONTAKT_MEJL = "kontakt@snajp.se";

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
  demoLeads: { sv: "Prova Iris, leadsagenten", en: "Try Iris, the leads agent" },
  demoSupport: { sv: "Prova kundtjänstagenten", en: "Try the support agent" },
  demoBokforing: { sv: "Prova kvittohanteraren", en: "Try the receipt agent" },
  footerKontakt: { sv: "Kontakt", en: "Contact" },
  //: MENYN. Etiketterna bytte namn 2026-08-25, och nycklarna bytte med dem —
  //: en nyckel som heter `menyKontakt` men renderar "Boka demo" är en lögn för
  //: nästa läsare, och de fem hade bara ETT anropsställe var att rätta.
  //:
  //: Tre av dem pekar numera på egna sidor i stället för på ankare. Det är ett
  //: avsteg från motiveringen i SidMeny.tsx ("allt innehåll finns redan på
  //: sidan"), och avsteget är motiverat: en bokning, en sökbar FAQ och en
  //: teampresentation är inte avsnitt man skrollar förbi, utan sidor man länkar
  //: till, bokmärker och skickar vidare. Priser är kvar som ankare av precis
  //: det gamla skälet — prissektionen är en del av säljargumentet där den står.
  menyBokaDemo: { sv: "Boka demo", en: "Book a demo" },
  menyPriser: { sv: "Priser & planer", en: "Pricing & plans" },
  menyFaq: { sv: "FAQ", en: "FAQ" },
  menyTeam: { sv: "Vårt team", en: "Our team" },
  menyDataskydd: { sv: "Dataskydd", en: "Data protection" },
  menyEtikett: { sv: "Meny", en: "Menu" },
  //: Länkar från startsidans avsnitt till de sidor som fördjupar dem.
  //:
  //: TILLAGDA vid sidan av avsnittens befintliga CTA, inte i stället för den.
  //: Att byta ut "Skriv till oss" mot en sidlänk hade varit ett beslut om
  //: konverteringsvägen, och det är inte en följd av att sidorna finns. Utan
  //: de här två nås /faq och /vart-team bara via en hopfälld meny, vilket är
  //: samma sak som att inte nås.
  vilkaLank: { sv: "Läs mer om oss", en: "More about us" },
  fragorLank: { sv: "Fler frågor och svar", en: "More questions and answers" },
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
    sv: "Möt *Iris*, din säljare som aldrig sover.",
    en: "Meet *Iris*, your sales rep that never sleeps."
  },
  lede: {
    sv: "Iris är Snajps leadsagent. Hon letar prospekt utifrån er produkt, gör en behovsanalys med källor som går att kontrollera och skriver mejlet medan tajmingen fortfarande gäller. Ni läser igenom och godkänner innan något går ut.",
    en: "Iris is Snajp's leads agent. She finds prospects based on your product, works out what they need with sources you can check, and writes the email while the timing still holds. You read it through and approve before anything goes out."
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
        sv: "Ett bolag som just investerat i en ny lokal. Ett bolag som behöver höja effektiviteten. Iris letar nya kunder baserat på er produkt.",
        en: "A company that just invested in new premises. A company that needs to raise its efficiency. Iris finds new customers based on your product."
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
  word: { sv: "Kvitton", en: "Receipts" },
  headline: {
    sv: "Kvittona i mejlen, *utplockade* åt dig.",
    en: "The receipts in your inbox, *picked out* for you."
  },
  lede: {
    sv: "Koppla mejlen med read-only-åtkomst, så hittar agenten kvitton och utlägg i inkorgen, läser av belopp, moms, datum och kategori och sammanställer perioden. Dubbletter räknas aldrig två gånger, och det du fotar själv laddar du bara upp.",
    en: "Connect your mailbox with read-only access and the agent finds receipts and expenses in the inbox, reads amount, VAT, date and category, and totals the period. Duplicates are never counted twice, and anything you photograph yourself you simply upload."
  },
  cta: { sv: "Se hur det fungerar", en: "See how it works" },
  demoHeading: {
    sv: "Inkorgen, *läst* i realtid.",
    en: "The inbox, *read* in real time."
  },
  demoLede: {
    sv: "Nedan rullar en exempelinkorg in och agenten plockar ut beloppen medan du tittar på. Du kan också fråga kvitto-assistenten om siffrorna.",
    en: "Below, an example inbox rolls in and the agent picks out the amounts while you watch. You can also ask the receipt assistant about the numbers."
  },
  exampleNote: { sv: "", en: "" },
  stepsHeading: {
    sv: "Tre steg, och systemet räknar *varenda* siffra.",
    en: "Three steps, and the system does *every* calculation."
  },
  steps: [
    {
      title: { sv: "Hittar kvittona i mejlen", en: "Finds the receipts in the mail" },
      body: {
        sv: "Agenten läser inkorgen med read-only-åtkomst och skiljer kvitton och utlägg från allt annat. Nyhetsbrev och mötesmejl lämnas orörda.",
        en: "The agent reads the inbox with read-only access and separates receipts and expenses from everything else. Newsletters and meeting mail are left untouched."
      }
    },
    {
      title: { sv: "Läser av fälten", en: "Reads the fields" },
      body: {
        sv: "Belopp, moms, datum, butik och kategori. Saknas ett fält gissar vi aldrig fram det, kvittot flaggas för granskning i stället. Samma kvitto räknas aldrig två gånger.",
        en: "Amount, VAT, date, merchant and category. If a field is missing we never invent it, the receipt is flagged for review instead. The same receipt is never counted twice."
      }
    },
    {
      title: { sv: "Sammanställer, du godkänner", en: "Totals it, you approve" },
      body: {
        sv: "Perioden summeras per kategori, med en sammanfattning i klartext. Flaggade kvitton räknas inte förrän du godkänt dem, aldrig en siffra som bara verkar stämma.",
        en: "The period is totalled per category, with a plain-language summary. Flagged receipts do not count until you approve them, never a number that merely seems right."
      }
    }
  ],
  limitsHeading: {
    sv: "Vad den inte gör",
    en: "What it does not do"
  },
  limits: [
    {
      sv: "Bokför ingenting. Den läser av och sammanställer. Du godkänner och för in.",
      en: "Books nothing. It reads and totals. You approve and enter."
    },
    {
      sv: "Skriver aldrig i din inkorg. Åtkomsten är read-only och kan tas bort när som helst.",
      en: "Never writes in your inbox. Access is read-only and can be revoked at any time."
    },
    {
      sv: "Sparar aldrig mejlens text. Det som lagras är de utlästa kvittofälten, avsändare och ämnesrad samt en kontrollsumma.",
      en: "Never stores the body of your mail. What is kept are the extracted receipt fields, sender and subject line, and a checksum."
    }
  ]
};

export const productCopy = {
  leads: leadsCopy,
  support: supportCopy,
  bookkeeping: bokforingCopy
} as const;
