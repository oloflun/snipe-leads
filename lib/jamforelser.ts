import type { Localized } from "@/lib/i18n";

/**
 * Andra leverantörer, för jämförelsesidorna /jamfor-ai-sdr och
 * /jamfor-supportagenter.
 *
 * ## Varför filen finns (Anton 2026-11-06)
 *
 * AI-översikterna på "ai sdr sverige", "leadsagent sverige" och "supportbot
 * sverige" byggs ur jämförelser och topplistor, inte ur bolagens egna sidor.
 * Snajp stod inte med i någon av dem. En egen, saklig jämförelse är den sortens
 * sida AI-svaren citerar.
 *
 * ## Reglerna
 *
 * Jämförande reklam ska vara saklig och gå att kontrollera (marknadsföringslagen).
 * Därför:
 * - varje uppgift står på leverantörens egen sajt, och `kalla` är den sida där
 *   den står; underlaget med alla sidor är docs/SEO-JAMFORELSER-KALLOR.md
 * - det leverantören inte själv skriver är "Ej angivet", aldrig en gissning
 * - priserna är leverantörernas egna, med valuta, så som de stod den dag som
 *   `KONTROLLERAD` anger
 * - Snajps egna rader byggs i lib/landningssidor.ts ur lib/pricing.ts och står
 *   inte här: Snajps pris skrivs aldrig för hand.
 *
 * Kontrollera om minst var tredje månad och ändra `KONTROLLERAD` när det är gjort.
 * INV-SEO-001 fäller en kontroll som är äldre än 120 dagar.
 */

/** Dagen varje uppgift nedan kontrollerades mot leverantörens egna sidor. */
export const KONTROLLERAD = "2026-11-06";

const EJ_ANGIVET: Localized = { sv: "Ej angivet", en: "Not stated" };

export type AiSdrVerktyg = {
  namn: string;
  kalla: string;
  vad: Localized;
  svenska: Localized;
  godkannande: Localized;
  data: Localized;
  pris: Localized;
};

export type Supportverktyg = {
  namn: string;
  kalla: string;
  vad: Localized;
  svenska: Localized;
  overlamning: Localized;
  data: Localized;
  pris: Localized;
};

export const AI_SDR_VERKTYG: AiSdrVerktyg[] = [
  {
    namn: "AI Kollegorna (Erik)",
    kalla: "https://www.aikollegorna.se/priser",
    vad: { sv: "AI-säljare för svenska B2B-företag, via mejl och LinkedIn", en: "AI sales rep for Swedish B2B companies, via email and LinkedIn" },
    svenska: { sv: "Sajten är svensk; skrivspråket anges inte", en: "The site is Swedish; the writing language is not stated" },
    godkannande: { sv: "Ja, ni godkänner det som går ut", en: "Yes, you approve what goes out" },
    data: { sv: "Lagring och drift inom EU; krävande uppgifter i amerikanska modeller", en: "Storage and hosting in the EU; demanding tasks on US models" },
    pris: { sv: "4 900 kr/mån exkl. moms", en: "SEK 4,900 a month excl. VAT" }
  },
  {
    namn: "Revexa (Leo)",
    kalla: "https://revexa.io/pris",
    vad: { sv: "AI-SDR som skriver via LinkedIn och mejl utifrån köpsignaler", en: "AI SDR that writes via LinkedIn and email based on buying signals" },
    svenska: { sv: "Ja, enligt Revexa", en: "Yes, according to Revexa" },
    godkannande: { sv: "Ja, som standard", en: "Yes, by default" },
    data: { sv: "Inom EU; krypterade säkerhetskopior i USA", en: "In the EU; encrypted backups in the US" },
    pris: { sv: "999 kr/mån exkl. moms, 7 dagar gratis", en: "SEK 999 a month excl. VAT, 7 days free" }
  },
  {
    namn: "Salesforge (Agent Frank)",
    kalla: "https://www.salesforge.ai/pricing",
    vad: { sv: "AI-SDR i en plattform för kalla utskick, mejl och LinkedIn", en: "AI SDR in a cold outreach platform, email and LinkedIn" },
    svenska: { sv: "Ja, bland drygt 20 språk", en: "Yes, among 20+ languages" },
    godkannande: { sv: "Valfritt: Co-Pilot granskar, Auto-Pilot skickar själv", en: "Optional: Co-Pilot reviews, Auto-Pilot sends on its own" },
    data: { sv: "Servrar inom EU", en: "Servers in the EU" },
    pris: { sv: "499 USD/mån, lägre vid årsbetalning", en: "USD 499 a month, less when billed yearly" }
  },
  {
    namn: "11x (Alice)",
    kalla: "https://www.11x.ai/products/alice/pricing",
    vad: { sv: "Utgående AI-agent för mejl och sociala kanaler", en: "Outbound AI agent for email and social channels" },
    svenska: { sv: "Fler än 105 språk; svenska nämns inte", en: "105+ languages; Swedish is not named" },
    godkannande: { sv: "Valfritt", en: "Optional" },
    data: { sv: "AWS; region anges inte", en: "AWS; region not stated" },
    pris: { sv: "Från 3 750 USD/mån, årsvis", en: "From USD 3,750 a month, billed yearly" }
  },
  {
    namn: "SuperOffice Lead Agent",
    kalla: "https://docs.superoffice.com/en/ai/learn/lead-agent",
    vad: { sv: "Hittar och kvalificerar prospekt i SuperOffice CRM; i tidig tillgång", en: "Finds and qualifies prospects in SuperOffice CRM; in early access" },
    svenska: EJ_ANGIVET,
    godkannande: { sv: "Ja, säljaren godkänner", en: "Yes, the salesperson approves" },
    data: { sv: "Inom EU", en: "In the EU" },
    pris: { sv: "Ej publicerat; kräver CRM Suite Plus", en: "Not published; requires CRM Suite Plus" }
  },
  {
    namn: "Sista AI",
    kalla: "https://sista.ai/sv/services/ai-sales-agents-sdr",
    vad: { sv: "Konsultbolag som bygger säljagenter på beställning", en: "Consultancy that builds sales agents to order" },
    svenska: EJ_ANGIVET,
    godkannande: { sv: "Ja, i piloten", en: "Yes, in the pilot" },
    data: EJ_ANGIVET,
    pris: { sv: "Pilot 7 000 EUR", en: "Pilot EUR 7,000" }
  }
];

export const SUPPORTVERKTYG: Supportverktyg[] = [
  {
    namn: "ImBox (ImBot)",
    kalla: "https://www.imbox.se/chatbot/",
    vad: { sv: "Kundtjänstplattform med en AI-chatbot tränad på ert innehåll", en: "Customer service platform with an AI chatbot trained on your content" },
    svenska: { sv: "Byter språk automatiskt; svenska nämns inte", en: "Switches language automatically; Swedish is not named" },
    overlamning: { sv: "Ja, till en mänsklig agent", en: "Yes, to a human agent" },
    data: { sv: "Inom EU/ESS", en: "In the EU/EEA" },
    pris: { sv: "Offert efter demo", en: "Quote after a demo" }
  },
  {
    namn: "Kundo (AI Chat)",
    kalla: "https://www.kundo.se/ai-chat",
    vad: { sv: "Ärendehantering med en AI-chatt som svarar ur kopplade källor", en: "Case management with an AI chat that answers from connected sources" },
    svenska: { sv: "Översätter fråga och svar i realtid", en: "Translates question and answer in real time" },
    overlamning: { sv: "Ja, med hela konversationen", en: "Yes, with the whole conversation" },
    data: { sv: "Inom EU; språkmodellen i Azures EU-miljö", en: "In the EU; the language model in Azure's EU environment" },
    pris: { sv: "Ej publicerat", en: "Not published" }
  },
  {
    namn: "Ebbot",
    kalla: "https://www.ebbot.com/platform/chat-agent",
    vad: { sv: "AI-agenter för chatt och mejl, svar ur godkänd kunskap", en: "AI agents for chat and email, answers from approved knowledge" },
    svenska: { sv: "Fler än 100 språk; svenska nämns inte", en: "100+ languages; Swedish is not named" },
    overlamning: { sv: "Ja", en: "Yes" },
    data: { sv: "Var anges inte", en: "Location not stated" },
    pris: { sv: "Ej publicerat", en: "Not published" }
  },
  {
    namn: "Dstny",
    kalla: "https://www.dstny.se/produkter/ai-tjanster/voice-agent",
    vad: { sv: "Chatbot på hemsidan och en röstagent för samtal", en: "Website chatbot and a voice agent for calls" },
    svenska: { sv: "Ja, för röstagenten", en: "Yes, for the voice agent" },
    overlamning: { sv: "Ja, till livechatt eller en människa", en: "Yes, to live chat or a person" },
    data: { sv: "Röstagenten: Azure Sweden Central", en: "Voice agent: Azure Sweden Central" },
    pris: { sv: "Ej publicerat", en: "Not published" }
  },
  {
    namn: "chattbot.se",
    kalla: "https://chattbot.se/",
    vad: { sv: "Chatbot för kundsupport med kopplingar till chattappar", en: "Customer support chatbot with connections to chat apps" },
    svenska: EJ_ANGIVET,
    overlamning: EJ_ANGIVET,
    data: EJ_ANGIVET,
    pris: { sv: "Från 899 kr/mån, 30 dagar gratis", en: "From SEK 899 a month, 30 days free" }
  },
  {
    namn: "Zendesk AI agents",
    kalla: "https://www.zendesk.com/service/ai/ai-agents/",
    vad: { sv: "AI-agenter i Zendesks kundtjänstsvit, för webb, mejl och röst", en: "AI agents in Zendesk's service suite, for web, email and voice" },
    svenska: { sv: "Ja", en: "Yes" },
    overlamning: { sv: "Ja, dirigerar till rätt team", en: "Yes, routes to the right team" },
    data: { sv: "EES som tillägg", en: "EEA as an add-on" },
    pris: { sv: "Från 55 USD per agent/mån; AI-ärenden över kvoten extra", en: "From USD 55 per agent a month; AI resolutions above quota extra" }
  },
  {
    namn: "Intercom Fin",
    kalla: "https://fin.ai/pricing",
    vad: { sv: "AI-agent för chatt, mejl och röst", en: "AI agent for chat, email and voice" },
    svenska: { sv: "Ja", en: "Yes" },
    overlamning: { sv: "Ja, med hela sammanhanget", en: "Yes, with full context" },
    data: { sv: "USA som standard, EU på avtal", en: "US by default, EU on contract" },
    pris: { sv: "0,99 USD per löst ärende", en: "USD 0.99 per resolution" }
  }
];
