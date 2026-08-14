#!/usr/bin/env node
/**
 * Skriver DATABASE_URL i snajp-support/.env så backenden går från in-memory
 * till Postgres.
 *
 * Anslutningssträngen byggs av SUPABASE_DB_PASSWORD (repots .env) plus
 * pooler-värden som hämtas från Supabase Management API — värden gissas alltså
 * inte. Utan detta hamnar man lätt på en aws-1-host som inte finns för
 * projektet, och får ett DNS-fel som ser ut som ett nätverksproblem.
 *
 * Kör:  node scripts/set-snajp-database-url.mjs
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const projectRef = "spsmblyvasagpekjmgmf";
const targetEnv = join(root, "snajp-support", ".env");

function readEnv(file, key) {
  const path = join(root, file);
  if (!existsSync(path)) return null;
  for (const raw of readFileSync(path, "utf8").split(/\r?\n/)) {
    const line = raw.replace(/^﻿/, "");
    const i = line.indexOf("=");
    if (i > 0 && line.slice(0, i).trim() === key) return line.slice(i + 1).trim();
  }
  return null;
}

const password = readEnv(".env", "SUPABASE_DB_PASSWORD");

if (!password) {
  console.error("SUPABASE_DB_PASSWORD saknas i .env.");
  process.exit(1);
}

if (/^(your[-_]?db[-_]?password|din[-_].*|<.*>)$/i.test(password)) {
  console.error("SUPABASE_DB_PASSWORD är fortfarande platshållaren i .env.");
  console.error("Hämta lösenordet: Supabase Dashboard → Project Settings → Database");
  console.error("→ Database password. Klistra in det i .env och kör om.");
  process.exit(1);
}

const pat = process.env.SUPABASE_PAT_SNIPRA ?? process.env.SUPABASE_ACCESS_TOKEN;
let host = "aws-0-eu-west-1.pooler.supabase.com";
let port = 6543;
let user = `postgres.${projectRef}`;

if (pat) {
  try {
    const response = await fetch(
      `https://api.supabase.com/v1/projects/${projectRef}/config/database/pooler`,
      { headers: { Authorization: `Bearer ${pat}` } }
    );
    if (response.ok) {
      const entries = await response.json();
      const primary = entries.find((e) => e.database_type === "PRIMARY") ?? entries[0];
      if (primary?.db_host) {
        host = primary.db_host;
        port = primary.db_port ?? port;
        user = primary.db_user ?? user;
        console.log(`Pooler-värd enligt Supabase: ${host}:${port}`);
      }
    }
  } catch {
    console.log("Kunde inte nå Management API — använder känd standardvärd.");
  }
} else {
  console.log("Ingen SUPABASE_PAT_SNIPRA — använder känd standardvärd.");
}

const url = `postgresql://${user}:${encodeURIComponent(password)}@${host}:${port}/postgres`;

if (!existsSync(targetEnv)) {
  console.error(`Hittar inte ${targetEnv}.`);
  process.exit(1);
}

const contents = readFileSync(targetEnv, "utf8");
const pattern = /^DATABASE_URL=.*$/m;
const updated = pattern.test(contents)
  ? contents.replace(pattern, `DATABASE_URL=${url}`)
  : `${contents.replace(/\n*$/, "\n")}DATABASE_URL=${url}\n`;

writeFileSync(targetEnv, updated, "utf8");

// Lösenordet skrivs aldrig ut.
console.log(`DATABASE_URL satt i snajp-support/.env (${host}, användare ${user}).`);
console.log("");
console.log("Nästa steg:");
console.log("  1. node scripts/apply-snajp-migration.mjs   (migrationerna 002-009)");
console.log("  2. Starta om backenden — /health ska visa storage: postgres");
console.log("  3. Samma sträng behöver sättas som DATABASE_URL på Render.");
