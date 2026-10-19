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

/**
 * "Varför Snajp finns", styckena (inte rubriken) från /vart-team. Står sedan
 * 2026-10-18 även på startsidan under "Byggt i Göteborg" (Antons beställning),
 * så texten bor här en gång och läses av båda sidorna.
 */
export const varforSnajp: Localized[] = [
  {
    sv:
      "B2B-prospektering är tidskrävande och blir opersonlig precis när den skalas. Antingen " +
      "skriver någon femton genomtänkta mejl i veckan, eller så skickas trehundra som alla " +
      "läser likadant. Samma sak i kundtjänsten: svaren finns redan skrivna, men i fel " +
      "dokument, och någon måste ändå läsa varje ärende för att veta vilket som brådskar.",
    en:
      "B2B prospecting takes time and turns impersonal exactly when it scales. Either someone " +
      "writes fifteen considered emails a week, or three hundred go out that all read the same. " +
      "The same thing in customer service: the answers are already written, but in the wrong " +
      "document, and someone still has to read every case to know which one is urgent."
  },
  {
    sv:
      "Vi bygger verktyget som gör förarbetet — hittar företagen och sorterar ärendena — och " +
      "lämnar beslutet till en människa. Målet är inte att ersätta den som " +
      "säljer eller svarar, utan att ge tillbaka timmarna som gick åt till att leta.",
    en:
      "We build the tool that does the groundwork, finding the companies and sorting the cases, " +
      "and leaves the decision to a person. The aim is not to replace whoever sells or replies, " +
      "but to give back the hours that went into searching."
  }
];

export type ProductCopy = {
  word: Localized;
  headline: Localized;
  lede: Localized;
  cta: Localized;
  demoHeading: Localized;
  demoLede: Localized;
  /** Tom sträng betyder att ingen finstilt rad renderas under demon. */
  exampleNote: Localized;
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
      "ingen kunds uppgifter delas med en annan kund. För att skriva svaret skickas mejltexten till vår " +
      "AI-leverantör, som behandlar den åt oss och inte tränar på den. Inget mejl går ut " +
      "utan att en människa godkänt det.",
    en: "Every customer's data sits in its own boundary and can only be read by that customer — " +
      "enforced in the database, not by a setting in the code. Nothing is published, and no " +
      "customer's data is shared with another customer. To write the reply, the email text is sent to our AI " +
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
    sv: "Nedan rullar en exempelinkorg in och agenten plockar ut beloppen medan du tittar på. Du kan också fråga kvittoassistenten om siffrorna.",
    en: "Below, an example inbox rolls in and the agent picks out the amounts while you watch. You can also ask the receipt assistant about the numbers."
  },
  exampleNote: { sv: "", en: "" },
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
