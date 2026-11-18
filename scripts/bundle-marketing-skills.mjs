import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const skillsRoot = path.join(root, "references", "marketingskills-main", "skills");
const outJson = path.join(root, "lib", "agent", "skills-corpus.json");

function parseFrontmatter(raw) {
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

function loadSkills() {
  if (!fs.existsSync(skillsRoot)) {
    throw new Error(`Skills directory not found: ${skillsRoot}`);
  }

  return fs
    .readdirSync(skillsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const skillPath = path.join(skillsRoot, entry.name, "SKILL.md");
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
    .filter(Boolean)
    .sort((a, b) => a.id.localeCompare(b.id));
}

const skills = loadSkills();
const payload = {
  generatedAt: new Date().toISOString(),
  source: "https://github.com/coreyhaines31/marketingskills",
  count: skills.length,
  skills
};

fs.mkdirSync(path.dirname(outJson), { recursive: true });
fs.writeFileSync(outJson, JSON.stringify(payload, null, 2), "utf8");

console.log(`Bundled ${skills.length} marketing skills`);
console.log(`  -> ${path.relative(root, outJson)}`);