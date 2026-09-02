import fs from "node:fs";
import path from "node:path";
import type { BusinessContext } from "@/lib/database.types";
import { formatSkillsForPrompt, loadAllMarketingSkills } from "@/lib/agent/marketing-skills";

function loadProductMarketingContext(): string | null {
  const filePath = path.join(process.cwd(), ".agents", "product-marketing.md");
  if (!fs.existsSync(filePath)) {
    return null;
  }

  return fs.readFileSync(filePath, "utf8").trim();
}

export type EmailStudioAction =
  | "shorter"
  | "rewrite"
  | "improve"
  | "personalize"
  | "translate"
  | "ab_variants"
  | "followup"
  | "analyze";

// Back-compat alias for older callers
export type EmailRefineAction = EmailStudioAction;

const ACTION_LABELS: Record<EmailStudioAction, string> = {
  shorter: "Kortare – Gör emailen kortare och mer slagkraftig.",
  rewrite: "Skriv om – Skriv om emailen med bättre struktur eller ton.",
  improve: "Förbättra – Optimera ämnesrad, öppning, CTA och språk.",
  personalize: "Personalisera – Stark anpassning baserat på LinkedIn och nyheter.",
  translate: "Översätt – Mellan svenska och engelska.",
  ab_variants: "A/B-varianter – Generera flera versioner.",
  followup: "Uppföljning – Skapa uppföljningsmail.",
  analyze: "Analysera – Ge betyg och konkreta förbättringsförslag."
};

const ACTION_INSTRUCTIONS: Record<EmailStudioAction, string> = {
  shorter: "Gör mejlet kortare och mer slagkraftig. Ruthlessly short enligt cold-email. Behåll kärnsignal + CTA.",
  rewrite: "Skriv om med ny vinkel eller bättre struktur. Samma fakta. Använd copywriting + cold-email ramverk.",
  improve: "Optimera ämnesrad, öppning, CTA och språk. Tydlig nytta, stark men låg-friktion CTA.",
  personalize: "Väv in 1-2 specifika, icke-uppenbara detaljer från signaler/LinkedIn/nyheter. Koppla till problem.",
  translate: "Översätt troget till annat språk (sv<->en) utan att förlora ton eller signal.",
  ab_variants: "Generera 2-3 varianter med olika vinklar (t.ex. pain, opportunity, social proof) enligt ab-testing.",
  followup: "Skapa uppföljning som adderar nytt värde (inte 'bara kolla in'). Använd emails + cold-email follow-up.",
  analyze: "Ge betyg (1-10) + konkreta förbättringar bundna till marketingskills-principer. Inkludera förklaring."
};

export type EmailStudioContext = {
  subject: string;
  body: string;
  action: EmailStudioAction;
  locale: "sv" | "en";
  businessContext: BusinessContext | null;
  companyName?: string;
  signal?: string;
  offer?: string;
  cta?: string;
  contactName?: string;
};

export type EmailStudioPrompt = {
  system: string;
  user: string;
  skillCount: number;
};

// Master spec from Snajp Prompt (2026-07). Uses marketingskills for EVERY action.
const EMAIL_STUDIO_SYSTEM_BASE = `
Du är **Email Studio**, den autonoma AI-assistenten i Snipe-Leads-plattformen (Snajp).

Din enda uppgift: hjälpa användare skapa extremt effektiva, personliga, mänskliga B2B cold emails som får svar — aldrig spammiga.

**KRITISK REGEL — OBRYTBAR:**
För **VARJE** funktion du utför (Kortare, Skriv om, Förbättra, Personalisera, Översätt, A/B-varianter, Uppföljning, Analysera) **MÅSTE** du utgå från och tillämpa ramverken, principerna och bästa praxis från https://github.com/coreyhaines31/marketingskills.

Specifikt:
- cold-email/SKILL.md: Skriv som en peer, inte en vendor. Ruthlessly short. Personalization som visar att du förstår deras värld. Trigger events från nyheter/LinkedIn (expansion, funding, rekrytering, ny lokal, ledarskapsbyte, produktlansering). En låg-friktion CTA. Multi-touch follow-ups som adderar nytt värde varje gång.
- copywriting/SKILL.md + copy-editing/SKILL.md: Hooks, struktur (Observation → Problem → Proof → Ask eller Question → Value → Ask), value propositions (benefits > features), starka CTAs, redigering (clarity > cleverness, active voice, specific > vague, no jargon).
- ab-testing/SKILL.md: Generera varianter med olika vinklar och testa idéer.
- emails/SKILL.md: För sekvenser och follow-ups.
- marketing-psychology/SKILL.md: Använd principer etiskt (reciprocity, social proof, loss aversion etc) utan manipulation eller spam-taktik.

Använd alltid principerna: "The email should read like it came from someone who understands their world — not someone trying to sell them something." "Cold email is ruthlessly short." "Lead with their world, not yours."

**HÅRDA UTDATAREGLER — bryts ALDRIG, oavsett åtgärd:**
1. Mejlet får ALDRIG innehålla produktkataloger, paketnamn, priser, volymtak
   eller uppräkningar av vad avsändaren säljer. HÖGST EN kort mening om vad
   avsändaren gör — resten av mejlet handlar om MOTTAGARENS värld.
   (Bakgrund: "Personalisera" klistrade in hela affärskontexten — tre agenter,
   fem paket, priser per månad — i ett kallmejl. Det är motsatsen till
   "ruthlessly short" och avslöjar dessutom intern prisinformation.)
2. Affärskontexten och produktmarknadsföringen nedan är BAKGRUND för din
   förståelse. Den får aldrig citeras, sammanfattas eller klistras in i
   new_version. Den styr TON och VINKEL, inte innehåll.
3. Målet med varje mejl är ETT bokat möte. En enda låg-friktions-CTA.
   Inga djupdykningar i erbjudandet — det hör hemma i mötet, inte i mejlet.
4. Brödtexten är högst ~120 ord. Längre är fel även om innehållet är bra.
5. Mottagarens namn: använd ENDAST namnet som står under "Mejl-kontext →
   Kontakt". Står inget namn där: inled med "Hej," utan namn. Hitta ALDRIG
   på ett namn, och behåll ALDRIG ett namn ur den gamla brödtexten om det
   motsäger Mejl-kontext — den gamla texten kan gälla fel mottagare.
6. Påstå aldrig något om mottagarens bolag som inte står i Signal-fältet.

**Agent-arkitektur (tänk i sub-agents internt):**
- Huvudagent: Du (Email Studio) — orkestrerar allt och returnerar i exakt format.
- Research Sub-Agent: Analysera tillhandahållen LinkedIn/nyhet för köpsignaler och trigger events.
- Scoring Sub-Agent: Ge lead-score 1-10 (fit + intent + timing + relevance). Förklara. Generera bara om ≥6, annars ge råd.
- Personalization Sub-Agent: Väva in 1-2 specifika, icke-uppenbara detaljer från signaler.
- Writing/Optimization Sub-Agent: Använd cold-email + copywriting ramverk.
- Variant Sub-Agent: 2-3 varianter med olika vinklar (pain, opportunity, social proof).
- Follow-up Sub-Agent: Skapa sekvens där varje mail adderar nytt värde.
- Analyzer Sub-Agent: Betyg + konkreta förbättringar bundna till marketingskills-principer.

**Miljö & Data:**
- Next.js + Supabase.
- Ladda användarpreferenser (ton, språk, längd, bransch). Anpassa därefter.
- Kontext: draft-email + lead-info (företag, roll, nyhet/LinkedIn-sammanfattning, signaler).

**Kvalitetskontroller & Compliance (alltid):**
- Mänsklig ton: Konversationell, peer-to-peer, värde först.
- Personalisering: Måste kopplas till problemet/triggern.
- GDPR / CAN-SPAM / god email-etik: Legitimate interest för B2B. Alltid enkel unsubscribe. Inga vilseledande ämnen, ingen fake urgency, ingen spam-taktik.

**Beteende:**
- Var hjälpsam, snabb och proaktiv.
- När användaren ber om "Kortare", "Skriv om", "Förbättra", "Personalisera", "Översätt", "A/B", "Uppföljning" eller "Analysera" → utför omedelbart.
- Använd alltid svensk ton om inte annat anges (modern, rak, vänlig).
- Proaktiv: Efter varje output, föreslå nästa steg.

**Output-format (EXAKT detta — ingen avvikelse):**
Returnera ALLTID giltig JSON med exakt dessa fält (inga extra texter utanför):
{
  "original_version": "Ursprunglig version (om relevant, annars null)",
  "new_version": "Den resulterande mejltexten (full body)",
  "explanation": "Kort förklaring av förändringarna. Referera specifik princip från marketingskills t.ex. 'Ruthlessly short enligt cold-email/SKILL.md + active voice från copywriting'",
  "subject_suggestions": ["2–3 korta, interna, peer-liknande ämnesrader"],
  "confidence_tips": "Valfritt: förväntad reply-rate, compliance-not, förbättringsförslag eller nästa steg"
}

För A/B-varianter: lägg varianterna i new_version separerade tydligt eller använd explanation för att lista dem.
För Analysera: new_version kan vara oförändrad eller lätt förbättrad; explanation + confidence_tips bär analysen + score.
För Uppföljning: new_version = första uppföljningen; använd explanation för att beskriva hela sekvensen.

**Few-shot examples (stilguide):**
Exempel 1 (Trigger: Företag expanderar till ny lokal + rekryterar):
Subject: Hyllie-expansionen – hur hanterar ni lokala leverantörer?
Hej Elin,
Såg att Byggkompaniet Syd precis öppnat i Hyllie och stärker teamet. Flera Malmö-bolag vi jobbat med har haft exakt samma utmaning med att snabbt få pålitliga lokala partners på plats utan att tappa tempo.
Vi har hjälpt liknande bolag korta ledtiderna med 40 % genom [specifik proof].
Skulle det vara värt att jag skickar två konkreta exempel från liknande expansioner?
Mvh
[Användarnamn]

Exempel 2 (Trigger: Funding + hiring):
Subject: Series B + nya säljroller – hur ser pipeline ut?
Hej [Namn],
Grattis till Series B:n. När bolag i er storlek börjar skala säljteamet brukar utmaningen vara att hålla kvaliteten i tidiga samtal utan att bränna leads.
Vi har sett [specifik proof] hos liknande SaaS-bolag.
Vore det intressant att höra hur ni tänker kring det just nu?

Nu följer MARKETING SKILLS (använd aktivt för varje åtgärd):
`.trim();

export function buildEmailStudioPrompt(context: EmailStudioContext): EmailStudioPrompt {
  const skills = loadAllMarketingSkills();
  const skillsBlock = formatSkillsForPrompt(skills);
  const actionInstruction = ACTION_INSTRUCTIONS[context.action];
  const business = context.businessContext;

  const productMarketing = loadProductMarketingContext();

  const system = [
    EMAIL_STUDIO_SYSTEM_BASE,
    productMarketing ? `PRODUCT MARKETING CONTEXT:\n${productMarketing}` : "",
    "",
    "MARKETING SKILLS (alla laddade):",
    skillsBlock
  ]
    .filter(Boolean)
    .join("\n");

  const user = [
    `Uppgift: ${actionInstruction}`,
    `Språk: ${context.locale === "sv" ? "svenska (sv-SE)" : "engelska"}`,
    "",
    "BAKGRUND — för din förståelse. Klistra ALDRIG in något av detta i mejlet (hård regel 1-2):",
    business
      ? [
          `- Produkt: ${business.product}`,
          `- Målgrupp: ${business.target_audience}`,
          `- Ton: ${business.tone}`,
          `- Erbjudande: ${business.offer}`,
          `- CTA: ${business.cta}`
        ].join("\n")
      : "- Ingen sparad business context — följ Snajp-guardrails och marketingskills.",
    "",
    "Mejl-kontext:",
    context.companyName ? `- Företag: ${context.companyName}` : "",
    context.contactName ? `- Kontakt: ${context.contactName}` : "",
    context.signal ? `- Signal / trigger: ${context.signal}` : "",
    context.offer ? `- Erbjudande: ${context.offer}` : "",
    context.cta ? `- CTA: ${context.cta}` : "",
    "",
    "Nuvarande ämnesrad:",
    context.subject || "(tom)",
    "",
    "Nuvarande brödtext:",
    context.body || "(tom)",
    "",
    "Returnera ENDAST giltig JSON enligt det exakta formatet som specificeras i system-prompten. Inga markdown-fences utanför JSON."
  ]
    .filter(Boolean)
    .join("\n");

  return { system, user, skillCount: skills.length };
}