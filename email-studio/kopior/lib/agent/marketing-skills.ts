import fs from "node:fs";
import path from "node:path";

export type MarketingSkill = {
  id: string;
  name: string;
  description: string;
  content: string;
};

const SKILLS_ROOT = path.join(process.cwd(), "references", "marketingskills-main", "skills");

function parseFrontmatter(raw: string): { name: string; description: string; body: string } {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) {
    return { name: "unknown", description: "", body: raw.trim() };
  }

  const frontmatter = match[1];
  const body = match[2].trim();
  const name = frontmatter.match(/^name:\s*(.+)$/m)?.[1]?.trim() ?? "unknown";
  const description = frontmatter.match(/^description:\s*(.+)$/m)?.[1]?.trim() ?? "";

  return { name, description, body };
}

/**
 * Loads every marketing skill from disk on each call so the agent always works
 * with the full skill corpus (per product requirement).
 */
export function loadAllMarketingSkills(): MarketingSkill[] {
  if (!fs.existsSync(SKILLS_ROOT)) {
    throw new Error(`Marketing skills not found at ${SKILLS_ROOT}. Run: node scripts/bundle-marketing-skills.mjs`);
  }

  return fs
    .readdirSync(SKILLS_ROOT, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const skillPath = path.join(SKILLS_ROOT, entry.name, "SKILL.md");
      if (!fs.existsSync(skillPath)) {
        return null;
      }

      const raw = fs.readFileSync(skillPath, "utf8");
      const parsed = parseFrontmatter(raw);

      return {
        id: entry.name,
        name: parsed.name,
        description: parsed.description,
        content: parsed.body
      };
    })
    .filter((skill): skill is MarketingSkill => skill !== null)
    .sort((a, b) => a.id.localeCompare(b.id));
}

function getPerSkillPromptBudget(): number {
  const configured = Number(process.env.SKILLS_PROMPT_MAX_CHARS_PER_SKILL ?? "2500");
  return Number.isFinite(configured) && configured > 500 ? configured : 2500;
}

function trimSkillContent(content: string, maxChars: number): string {
  if (content.length <= maxChars) {
    return content;
  }

  return `${content.slice(0, maxChars).trimEnd()}\n\n[... skill fortsätter — full SKILL.md laddad av agenten]`;
}

/**
 * Formats every loaded skill for the LLM prompt. All skills are always represented;
 * per-skill body text is capped to keep requests within model context limits.
 */
export function formatSkillsForPrompt(skills: MarketingSkill[]): string {
  const perSkillBudget = getPerSkillPromptBudget();

  return skills
    .map((skill) => {
      return [
        `### SKILL: ${skill.name} (${skill.id})`,
        skill.description ? `Description: ${skill.description}` : "",
        trimSkillContent(skill.content, perSkillBudget)
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n---\n\n");
}