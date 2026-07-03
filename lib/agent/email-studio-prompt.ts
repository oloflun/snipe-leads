import fs from "node:fs";
import path from "node:path";
import type { BusinessContext } from "@/lib/database.types";
import { formatSkillsForPrompt, loadAllMarketingSkills } from "@/lib/agent/marketing-skills";
import { SNIPRA_EMAIL_GUARDRAILS } from "@/lib/agent/snipra-tone";

function loadProductMarketingContext(): string | null {
  const filePath = path.join(process.cwd(), ".agents", "product-marketing.md");
  if (!fs.existsSync(filePath)) {
    return null;
  }

  return fs.readFileSync(filePath, "utf8").trim();
}

export type EmailRefineAction =
  | "shorter"
  | "more_personal"
  | "clearer_cta"
  | "rewrite"
  | "more_professional"
  | "more_human"
  | "more_persuasive";

const ACTION_INSTRUCTIONS: Record<EmailRefineAction, string> = {
  shorter: "Gör mejlet 30–40% kortare. Behåll signal, erbjudande och CTA. Ta bort utfyllnad.",
  more_personal: "Gör mejlet mer personligt med konkret referens till signal, roll eller kontext. Varmare men inte casual.",
  clearer_cta: "Förtydliga CTA till ett lågmält, tydligt nästa steg utan press eller flera val.",
  rewrite: "Skriv om med ny vinkel. Samma fakta, samma tonalitet, samma språk.",
  more_professional: "Höj formaliteten något utan att bli stel. Behåll lågmäld svensk B2B-ton.",
  more_human: "Gör texten mer mänsklig och naturlig. Undvik AI-formuleringar och mallkänsla.",
  more_persuasive: "Stärk relevansen och övertygelsen med konkret signal och nytta — utan pushy ton."
};

export type EmailStudioContext = {
  subject: string;
  body: string;
  action: EmailRefineAction;
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

export function buildEmailStudioPrompt(context: EmailStudioContext): EmailStudioPrompt {
  const skills = loadAllMarketingSkills();
  const skillsBlock = formatSkillsForPrompt(skills);
  const actionInstruction = ACTION_INSTRUCTIONS[context.action];
  const business = context.businessContext;

  const productMarketing = loadProductMarketingContext();

  const system = [
    SNIPRA_EMAIL_GUARDRAILS,
    "",
    productMarketing ? `PRODUCT MARKETING CONTEXT:\n${productMarketing}` : "",
    "",
    "Du har tillgång till hela marketing skills-biblioteket nedan. Tillämpa relevanta principer från alla skills, med extra vikt på cold-email, copywriting, emails och marketing-psychology för denna uppgift.",
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
    "Business context:",
    business
      ? [
          `- Produkt: ${business.product}`,
          `- Målgrupp: ${business.target_audience}`,
          `- Ton: ${business.tone}`,
          `- Erbjudande: ${business.offer}`,
          `- CTA: ${business.cta}`
        ].join("\n")
      : "- Ingen sparad business context — följ Snipra-guardrails.",
    "",
    "Mejl-kontext:",
    context.companyName ? `- Företag: ${context.companyName}` : "",
    context.contactName ? `- Kontakt: ${context.contactName}` : "",
    context.signal ? `- Signal: ${context.signal}` : "",
    context.offer ? `- Erbjudande (input): ${context.offer}` : "",
    context.cta ? `- CTA (input): ${context.cta}` : "",
    "",
    "Nuvarande ämnesrad:",
    context.subject,
    "",
    "Nuvarande brödtext:",
    context.body,
    "",
    "Returnera endast giltig JSON med exakt dessa fält:",
    '{"subject":"...","body":"..."}'
  ]
    .filter(Boolean)
    .join("\n");

  return { system, user, skillCount: skills.length };
}