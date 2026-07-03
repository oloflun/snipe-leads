#!/usr/bin/env node
/**
 * Provisions a fresh Supabase project for Snipra Phase 1.
 *
 * Usage (PowerShell):
 *   $env:SUPABASE_ACCESS_TOKEN = "sbp_..."
 *   node scripts/provision-supabase.mjs
 */

import { randomBytes } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const API = "https://api.supabase.com/v1";
const PROJECT_NAME = "snipra-dev";
const REGION = "eu-west-1";

const token = process.env.SUPABASE_ACCESS_TOKEN;
if (!token) {
  console.error("Missing SUPABASE_ACCESS_TOKEN.");
  console.error("Create one at https://supabase.com/dashboard/account/tokens");
  process.exit(1);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });

  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }

  if (!response.ok) {
    throw new Error(`${options.method ?? "GET"} ${path} failed (${response.status}): ${JSON.stringify(body)}`);
  }

  return body;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForProject(ref) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const project = await api(`/projects/${ref}`);
    if (project.status === "ACTIVE_HEALTHY") {
      return project;
    }
    console.log(`Waiting for project (${project.status ?? "unknown"})...`);
    await sleep(10_000);
  }
  throw new Error("Project did not become healthy in time.");
}

async function runSql(ref, query) {
  return api(`/projects/${ref}/database/query`, {
    method: "POST",
    body: JSON.stringify({ query })
  });
}

async function main() {
  const orgs = await api("/organizations");
  if (!orgs?.length) {
    throw new Error("No Supabase organizations found for this token.");
  }

  const organizationId = orgs[0].id;
  console.log(`Using organization: ${orgs[0].name} (${organizationId})`);

  const existing = (await api("/projects")).find((project) => project.name === PROJECT_NAME);
  let project = existing;

  if (project) {
    console.log(`Reusing existing project: ${project.name} (${project.id})`);
  } else {
    const dbPass = randomBytes(18).toString("base64url");
    console.log("Creating project...");
    project = await api("/projects", {
      method: "POST",
      body: JSON.stringify({
        name: PROJECT_NAME,
        organization_id: organizationId,
        region: REGION,
        db_pass: dbPass
      })
    });
    console.log(`Created project ref: ${project.id}`);
    writeFileSync(
      join(root, "supabase", ".db-password.txt"),
      `Store this securely. Project: ${PROJECT_NAME}\nDB password: ${dbPass}\n`,
      "utf8"
    );
  }

  await waitForProject(project.id);

  console.log("Disabling email confirmation...");
  await api(`/projects/${project.id}/config/auth`, {
    method: "PATCH",
    body: JSON.stringify({
      mailer_autoconfirm: true,
      disable_signup: false
    })
  });

  const keys = await api(`/projects/${project.id}/api-keys`);
  const anonKey = keys.find((key) => key.name === "anon")?.api_key;
  const serviceRoleKey = keys.find((key) => key.name === "service_role")?.api_key;

  if (!anonKey || !serviceRoleKey) {
    throw new Error("Could not fetch project API keys.");
  }

  const schema = readFileSync(join(root, "supabase", "schema.sql"), "utf8");
  const migration = readFileSync(join(root, "supabase", "migrations", "001_handle_new_user.sql"), "utf8");

  console.log("Applying schema...");
  await runSql(project.id, schema);
  console.log("Applying signup trigger migration...");
  await runSql(project.id, migration);

  const envLocal = [
    `NEXT_PUBLIC_SUPABASE_URL=https://${project.id}.supabase.co`,
    `NEXT_PUBLIC_SUPABASE_ANON_KEY=${anonKey}`,
    `SUPABASE_SERVICE_ROLE_KEY=${serviceRoleKey}`,
    "NEXT_PUBLIC_SITE_URL=http://localhost:3000",
    ""
  ].join("\n");

  writeFileSync(join(root, ".env.local"), envLocal, "utf8");

  const configToml = `project_id = "${project.id}"\n`;
  writeFileSync(join(root, "supabase", "config.toml"), configToml, "utf8");

  console.log("\nDone.");
  console.log(`Project URL: https://${project.id}.supabase.co`);
  console.log(`Dashboard: https://supabase.com/dashboard/project/${project.id}`);
  console.log("Wrote .env.local and supabase/config.toml");
  console.log("Email confirmation: disabled (mailer_autoconfirm=true)");
}

main().catch((error) => {
  console.error(error.message ?? error);
  process.exit(1);
});