import { getAllMarketingSkills } from "../skills-corpus.ts";

export type EmailStudioAction =
  | "shorter"
  | "rewrite"
  | "improve"
  | "personalize"
  | "translate"
  | "ab_variants"
  | "followup"
  | "analyze";

export type EmailRefineAction = EmailStudioAction; // compat

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

// Master spec (condensed for edge) — full principles from marketingskills + Snipra Prompt
const EMAIL_STUDIO_SYSTEM_BASE = `
Du är Email Studio, den autonoma AI-assistenten i Snipe-Leads (Snipra).

Enda uppgift: extremt effektiva, personliga, mänskliga B2B cold emails som får svar — aldrig spammiga.

KRITISK REGEL: För VARJE funktion (Kortare, Skriv om, Förbättra, Personalisera, Översätt, A/B-varianter, Uppföljning, Analysera) MÅSTE du utgå från och tillämpa ramverken från https://github.com/coreyhaines31/marketingskills (cold-email, copywriting, copy-editing, ab-testing, emails, marketing-psychology).

Skriv som peer. Ruthlessly short. Lead with their world. Trigger events (expansion, hiring, funding, new location). Låg-friktion CTA. Varje follow-up adderar värde.

Agent-arkitektur internt: Research, Scoring (≥6), Personalization, Writing, Variant, Follow-up, Analyzer sub-agents.

Kvalitet: Mänsklig ton, kopplad personalisering, GDPR/CAN-SPAM compliant. Aldrig spam-taktik.

Output-format (EXAKT JSON, inga andra texter):
{
  "original_version": "Ursprunglig eller null",
  "new_version": "Full body för den nya versionen",
  "explanation": "Kort förklaring. Referera explicit t.ex. 'Ruthlessly short enligt cold-email/SKILL.md'",
  "subject_suggestions": ["2-3 ämnesrader"],
  "confidence_tips": "Tips, betyg, nästa steg"
}

Använd svensk ton om inte annat. Proaktiv.

MARKETING SKILLS (tillämpa aktivt):
`.trim();

function trimSkillContent(content: string, maxChars: number): string {
  if (content.length <= maxChars) {
    return content;
  }
  return `${content.slice(0, maxChars).trimEnd()}\n\n[... skill fortsätter — full SKILL.md laddad av agenten]`;
}

function formatSkillsForPrompt() {
  const perSkillBudget = Number(Deno.env.get("SKILLS_PROMPT_MAX_CHARS_PER_SKILL") ?? "2200");
  return getAllMarketingSkills()
    .map((skill) => {
      return [
        `### SKILL: ${skill.name} (${skill.id})`,
        skill.description ? `Description: ${skill.description}` : "",
        trimSkillContent(skill.content, perSkillBudget > 500 ? perSkillBudget : 2200)
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n---\n\n");
}

export function buildEmailStudioPrompt(input: {
  subject: string;
  body: string;
  action: EmailStudioAction;
  locale: "sv" | "en";
  businessContext?: {
    product: string;
    target_audience: string;
    tone: string;
    offer: string;
    cta: string;
  } | null;
  companyName?: string;
  signal?: string;
  offer?: string;
  cta?: string;
  contactName?: string;
}) {
  const skills = getAllMarketingSkills();
  const skillsBlock = formatSkillsForPrompt();

  const system = [
    EMAIL_STUDIO_SYSTEM_BASE,
    "",
    skillsBlock
  ].join("\n");

  const user = [
    `Uppgift: ${ACTION_INSTRUCTIONS[input.action]}`,
    `Språk: ${input.locale === "sv" ? "svenska (sv-SE)" : "engelska"}`,
    "",
    input.businessContext
      ? [
          "Business context:",
          `- Produkt: ${input.businessContext.product}`,
          `- Målgrupp: ${input.businessContext.target_audience}`,
          `- Ton: ${input.businessContext.tone}`,
          `- Erbjudande: ${input.businessContext.offer}`,
          `- CTA: ${input.businessContext.cta}`
        ].join("\n")
      : "- Ingen business context — följ marketingskills + guardrails.",
    "",
    "Mejl-kontext:",
    input.companyName ? `- Företag: ${input.companyName}` : "",
    input.contactName ? `- Kontakt: ${input.contactName}` : "",
    input.signal ? `- Signal: ${input.signal}` : "",
    input.offer ? `- Erbjudande: ${input.offer}` : "",
    input.cta ? `- CTA: ${input.cta}` : "",
    "",
    "Nuvarande ämnesrad:",
    input.subject || "(tom)",
    "",
    "Nuvarande brödtext:",
    input.body || "(tom)",
    "",
    "Returnera ENDAST den exakta JSON-strukturen från systemet (original_version, new_version, explanation, subject_suggestions, confidence_tips). Inga andra kommentarer."
  ]
    .filter(Boolean)
    .join("\n");

  return { system, user, skillCount: skills.length };
}