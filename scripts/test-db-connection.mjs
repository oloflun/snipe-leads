import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const envPath = join(root, ".env");
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const i = line.indexOf("=");
    const key = line.slice(0, i).trim();
    const value = line.slice(i + 1).trim();
    if (!(key in process.env)) process.env[key] = value;
  }
}

const ref = "spsmblyvasagpekjmgmf";
const pass = process.env.SUPABASE_DB_PASSWORD ?? "";
console.log("password length:", pass.length);

const attempts = [
  ["direct", `postgresql://postgres:${encodeURIComponent(pass)}@db.${ref}.supabase.co:5432/postgres`],
  ["pooler ew1", `postgresql://postgres.${ref}:${encodeURIComponent(pass)}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres`],
  ["pooler ec1", `postgresql://postgres.${ref}:${encodeURIComponent(pass)}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`],
  ["pooler en1", `postgresql://postgres.${ref}:${encodeURIComponent(pass)}@aws-0-eu-north-1.pooler.supabase.com:6543/postgres`]
];

for (const [name, connectionString] of attempts) {
  const client = new pg.Client({ connectionString, ssl: { rejectUnauthorized: false } });
  try {
    await client.connect();
    console.log(name, "OK");
    await client.end();
    process.exit(0);
  } catch (error) {
    console.log(name, error.message);
    await client.end().catch(() => undefined);
  }
}