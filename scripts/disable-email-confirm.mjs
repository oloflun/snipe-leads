import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const envPath = join(root, ".env");

for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
  if (!line || line.startsWith("#") || !line.includes("=")) continue;
  const i = line.indexOf("=");
  process.env[line.slice(0, i).trim()] = line.slice(i + 1).trim();
}

const ref = "spsmblyvasagpekjmgmf";
const pass = process.env.SUPABASE_DB_PASSWORD;
const client = new pg.Client({
  connectionString: `postgresql://postgres.${ref}:${encodeURIComponent(pass)}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres`,
  ssl: { rejectUnauthorized: false }
});

await client.connect();

try {
  const { rowCount } = await client.query(
    "update auth.config set value = 'true' where parameter = 'mailer_autoconfirm'"
  );
  console.log("mailer_autoconfirm rows updated:", rowCount);
} catch (error) {
  console.log("auth.config update:", error.message);
}

await client.end();

const sec = process.env.SUPABASE_SERVICE_ROLE_KEY;
const response = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/settings`, {
  headers: { apikey: sec, Authorization: `Bearer ${sec}` }
});
console.log("auth settings:", await response.text());