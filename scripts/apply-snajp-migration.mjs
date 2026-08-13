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

const poolerHosts = [
  "aws-0-eu-west-1.pooler.supabase.com",
  "aws-0-eu-central-1.pooler.supabase.com",
  "aws-0-eu-north-1.pooler.supabase.com",
  "aws-1-eu-west-1.pooler.supabase.com",
  "aws-1-eu-central-1.pooler.supabase.com",
  "aws-1-eu-north-1.pooler.supabase.com",
  "aws-1-eu-west-2.pooler.supabase.com",
  "aws-1-eu-west-3.pooler.supabase.com"
];

// Alla snajp-migrationer i ordning. Samtliga är idempotenta (CREATE ... IF NOT
// EXISTS, DROP ... IF EXISTS), så skriptet kan köras om utan biverkningar.
const files = [
  "002_snajp_support.sql",
  "003_snajp_multitenant.sql",
  "004_snajp_email_pipeline.sql",
  "005_snajp_pilot_categories.sql",
  "006_snajp_selfservice_usage.sql",
  "007_snajp_workspace_link.sql"
].map((name) => join(root, "supabase", "migrations", name));

async function connectClient() {
  let lastError;

  for (const host of poolerHosts) {
    const connectionString = `postgresql://postgres.${projectRef}:${encodeURIComponent(password)}@${host}:6543/postgres`;
    const client = new pg.Client({ connectionString, ssl: { rejectUnauthorized: false } });

    try {
      await client.connect();
      console.log(`Connected via ${host}`);
      return client;
    } catch (error) {
      lastError = error;
      await client.end().catch(() => undefined);
    }
  }

  throw lastError ?? new Error("Could not connect to database");
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
