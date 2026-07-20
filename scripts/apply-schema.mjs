#!/usr/bin/env node
/**
 * Applies supabase/schema.sql + migrations via direct Postgres connection.
 *
 * Usage:
 *   $env:SUPABASE_DB_PASSWORD = "your-database-password"
 *   node scripts/apply-schema.mjs
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
  "aws-0-eu-north-1.pooler.supabase.com"
];

const files = [
  join(root, "supabase", "schema.sql"),
  join(root, "supabase", "migrations", "001_handle_new_user.sql")
];

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
      "select tablename from pg_tables where schemaname = 'public' order by tablename"
    );
    console.log("\nPublic tables:", rows.map((row) => row.tablename).join(", "));
  } finally {
    await client.end().catch(() => undefined);
  }
}

main().catch((error) => {
  console.error(error.message ?? error);
  process.exit(1);
});