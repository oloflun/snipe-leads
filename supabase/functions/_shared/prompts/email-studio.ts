import { getAllMarketingSkills } from "../skills-corpus.ts";

export type EmailRefineAction =
  | "shorter"
  | "more_personal"
  | "clearer_cta"
  | "rewrite"
  | "more_professional"
  | "more_human"
  | "more_persuasive";

const SNIPRA_EMAIL_GUARDRAILS = `
Du skriver svenska B2B-outbound-mejl för Snipra.

Tonalitet (obligatorisk):
- mänskliga, professionella, relevanta, svenska, lågmälda, specifika, naturliga
- aldrig aggressiv amerikansk säljton
- undvik spamkänsla, överdrivna claims, clickbait och generiska AI-formuleringar

Förbjudna fraser:
- "I hope this email finds you well"
- "Jag hoppas att detta mejl når dig väl"
- "revolutionerande", "game-changer", "unik möjlighet"
`.trim();

const ACTION_INSTRUCTIONS: Record<EmailRefineAction, string> = {
  shorter: "Gör mejlet 30–40% kortare. Behåll signal, erbjudande och CTA.",
  more_personal: "Gör mejlet mer personligt med konkret signal/kontext. Varmare men inte casual.",
  clearer_cta: "Förtydliga CTA till ett lågmält nästa steg utan press.",
  rewrite: "Skriv om med ny vinkel. Samma fakta och tonalitet.",
  more_professional: "Höj formaliteten något utan att bli stel.",
  more_human: "Gör texten mer mänsklig och naturlig.",
  more_persuasive: "Stärk relevans och nytta utan pushy ton."
};

function trimSkillContent(content: string, maxChars: number): string {
  if (content.length <= maxChars) {
    return content;
  }

  return `${content.slice(0, maxChars).trimEnd()}\n\n[... skill fortsätter — full SKILL.md laddad av agenten]`;
}

function formatSkillsForPrompt() {
  const perSkillBudget = Number(Deno.env.get("SKILLS_PROMPT_MAX_CHARS_PER_SKILL") ?? "2500");

  return getAllMarketingSkills()
    .map((skill) => {
      return [
        `### SKILL: ${skill.name} (${skill.id})`,
        skill.description ? `Description: ${skill.description}` : "",
        trimSkillContent(skill.content, perSkillBudget > 500 ? perSkillBudget : 2500)
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n---\n\n");
}

export function buildEmailStudioPrompt(input: {
  subject: string;
  body: string;
  action: EmailRefineAction;
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

  const system = [
    SNIPRA_EMAIL_GUARDRAILS,
    "",
    "MARKETING SKILLS (alla laddade):",
    formatSkillsForPrompt()
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
      : "",
    input.companyName ? `Företag: ${input.companyName}` : "",
    input.contactName ? `Kontakt: ${input.contactName}` : "",
    input.signal ? `Signal: ${input.signal}` : "",
    input.offer ? `Erbjudande: ${input.offer}` : "",
    input.cta ? `CTA: ${input.cta}` : "",
    "",
    "Nuvarande ämnesrad:",
    input.subject,
    "",
    "Nuvarande brödtext:",
    input.body,
    "",
    'Returnera endast JSON: {"subject":"...","body":"..."}'
  ]
    .filter(Boolean)
    .join("\n");

  return { system, user, skillCount: skills.length };
}