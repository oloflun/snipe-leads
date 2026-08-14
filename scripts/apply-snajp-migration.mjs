#!/usr/bin/env node
/**
 * Applies the snajp-support migrations (002, 003, 004) via direct Postgres connection.
 *
 * Usage:
 *   $env:SUPABASE_DB_PASSWORD = "your-database-password"
 *   node scripts/apply-snajp-migration.mjs
 */

import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const projectRef = "spsmblyvasagpekjmgmf";

function loadEnvFile() {
  const envPath = join(root, ".env");
  if (!existsSync(envPath)) {
    return;
  }
  for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    if (!line || line.startsWith("#") || !line.includes("=")) {
      continue;
    }
    const index = line.indexOf("=");
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim();
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

loadEnvFile();

const password = process.env.SUPABASE_DB_PASSWORD;

if (!password) {
  console.error("Missing SUPABASE_DB_PASSWORD.");
  console.error("Find it in Supabase Dashboard → Project Settings → Database → Database password");
  process.exit(1);
}

// Platshållaren ger "password authentication failed" långt senare, efter att
// åtta värdar provats — ett fel som ser ut som ett nätverksproblem men inte är
// det. Fånga det här i stället, med besked om vad som faktiskt saknas.
if (/^(your[-_]?db[-_]?password|din[-_].*|<.*>)$/i.test(password)) {
  console.error("SUPABASE_DB_PASSWORD är fortfarande platshållaren i .env.");
  console.error("Hämta det riktiga lösenordet: Supabase Dashboard → Project Settings");
  console.error("→ Database → Database password, och klistra in det i .env.");
  process.exit(1);
}

// Reservlista. Rätt värd hämtas i första hand från Management API (se nedan) —
// den här används bara när ingen PAT finns. Flera av namnen existerar inte för
// ett givet projekt och ger DNS-fel, vilket är förväntat.
const fallbackPoolerHosts = [
  "aws-0-eu-west-1.pooler.supabase.com",
  "aws-0-eu-central-1.pooler.supabase.com",
  "aws-0-eu-north-1.pooler.supabase.com",
  "aws-1-eu-west-1.pooler.supabase.com",
  "aws-1-eu-central-1.pooler.supabase.com",
  "aws-1-eu-north-1.pooler.supabase.com"
];

/** Projektets faktiska pooler-värd, enligt Supabase själv. */
async function resolvePoolerHost() {
  const pat = process.env.SUPABASE_PAT_SNIPRA ?? process.env.SUPABASE_ACCESS_TOKEN;
  if (!pat) {
    return null;
  }
  try {
    const response = await fetch(
      `https://api.supabase.com/v1/projects/${projectRef}/config/database/pooler`,
      { headers: { Authorization: `Bearer ${pat}` } }
    );
    if (!response.ok) {
      return null;
    }
    const entries = await response.json();
    const primary = entries.find((e) => e.database_type === "PRIMARY") ?? entries[0];
    return primary?.db_host ?? null;
  } catch {
    return null;
  }
}

// Alla snajp-migrationer i ordning. Samtliga är idempotenta (CREATE ... IF NOT
// EXISTS, DROP ... IF EXISTS), så skriptet kan köras om utan biverkningar.
const files = [
  "002_snajp_support.sql",
  "003_snajp_multitenant.sql",
  "004_snajp_email_pipeline.sql",
  "005_snajp_pilot_categories.sql",
  "006_snajp_selfservice_usage.sql",
  "007_snajp_workspace_link.sql",
  // 008 (snajp_app-rollen) körs INTE här: den kräver att ett lösenord sätts
  // manuellt i filen först, och ska köras medvetet — inte som en sidoeffekt.
  "009_company_profile.sql"
].map((name) => join(root, "supabase", "migrations", name));

async function connectClient() {
  const resolved = await resolvePoolerHost();
  const hosts = resolved ? [resolved] : fallbackPoolerHosts;
  if (resolved) {
    console.log(`Pooler-värd enligt Supabase: ${resolved}`);
  }

  const failures = [];

  for (const host of hosts) {
    const connectionString = `postgresql://postgres.${projectRef}:${encodeURIComponent(password)}@${host}:6543/postgres`;
    const client = new pg.Client({ connectionString, ssl: { rejectUnauthorized: false } });

    try {
      await client.connect();
      console.log(`Connected via ${host}`);
      return client;
    } catch (error) {
      failures.push({ host, error });
      await client.end().catch(() => undefined);
    }
  }

  // Tidigare kastades bara SISTA felet — nästan alltid ett DNS-fel från en värd
  // som inte finns för det här projektet. Det dolde den verkliga orsaken (fel
  // lösenord) bakom något som såg ut som ett nätverksproblem.
  const authFailure = failures.find((f) => f.error.code === "28P01");
  if (authFailure) {
    throw new Error(
      `Fel lösenord: databasen på ${authFailure.host} nekade inloggningen (28P01). ` +
        "Kontrollera SUPABASE_DB_PASSWORD i .env mot Supabase Dashboard → Project " +
        "Settings → Database."
    );
  }

  const detail = failures
    .map((f) => `  ${f.host}: ${f.error.code ?? ""} ${f.error.message}`)
    .join("\n");
  throw new Error(`Kunde inte ansluta till databasen.\n${detail}`);
}

async function main() {
  const client = await connectClient();

  try {
    for (const file of files) {
      const sql = readFileSync(file, "utf8");
      console.log(`Applying ${file}...`);
      await client.query(sql);
      console.log("OK");
    }

    const { rows } = await client.query(
      "select tablename from pg_tables where schemaname = 'public' and tablename like 'ss_%' order by tablename"
    );
    console.log("\nSnajp-Support tables:", rows.map((row) => row.tablename).join(", "));
  } finally {
    await client.end().catch(() => undefined);
  }
}

main().catch((error) => {
  console.error(error.message ?? error);
  process.exit(1);
});
