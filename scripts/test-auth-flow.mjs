// Verifierar registreringsflödet mot Supabase:
//   1. ny användare får profil + workspace
//   2. inbjuden adress hamnar i det befintliga workspacet, inte i ett nytt
//   3. ett konto utan profil kan läkas i efterhand
//
//   node scripts/test-auth-flow.mjs
//
// Kräver NEXT_PUBLIC_SUPABASE_URL och SUPABASE_SERVICE_ROLE_KEY (läses ur
// .env.local eller .env om de finns). Städar upp efter sig även vid fel.

import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "@supabase/supabase-js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

for (const name of [".env.local", ".env"]) {
  const path = join(root, name);
  if (!existsSync(path)) continue;
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const index = line.indexOf("=");
    const key = line.slice(0, index).trim();
    if (!(key in process.env)) process.env[key] = line.slice(index + 1).trim();
  }
}

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!url || !serviceKey) {
  console.error("Saknar NEXT_PUBLIC_SUPABASE_URL eller SUPABASE_SERVICE_ROLE_KEY.");
  process.exit(1);
}

const admin = createClient(url, serviceKey, { auth: { persistSession: false } });
const stamp = Date.now();
const created = [];

function check(condition, label) {
  if (!condition) throw new Error(`FEL: ${label}`);
  console.log(`  ok  ${label}`);
}

async function createUser(email) {
  const { data, error } = await admin.auth.admin.createUser({
    email,
    password: `Test-${stamp}-abcdef`,
    email_confirm: true,
    user_metadata: { full_name: "Testanvändare" }
  });
  if (error) throw new Error(`kunde inte skapa ${email}: ${error.message}`);
  created.push(data.user.id);
  return data.user;
}

async function profileOf(userId) {
  const { data } = await admin
    .from("profiles")
    .select("workspace_id, role")
    .eq("id", userId)
    .maybeSingle();
  return data;
}

async function run() {
  console.log("1. Registrering ger profil + workspace");
  const owner = await createUser(`snajp.test.${stamp}@example.com`);
  const ownerProfile = await profileOf(owner.id);
  check(ownerProfile, "profilrad skapades av triggern");
  check(ownerProfile.workspace_id, "profilen pekar på ett workspace");
  check(ownerProfile.role === "owner", "första användaren blir owner");

  console.log("2. Inbjuden adress hamnar i det befintliga workspacet");
  const invitedEmail = `snajp.invited.${stamp}@example.com`;
  const { error: inviteError } = await admin.from("workspace_invites").insert({
    email: invitedEmail,
    workspace_id: ownerProfile.workspace_id,
    role: "member"
  });
  if (inviteError) throw new Error(`kunde inte skapa inbjudan: ${inviteError.message}`);

  const invited = await createUser(invitedEmail);
  const invitedProfile = await profileOf(invited.id);
  check(invitedProfile, "inbjuden användare fick profilrad");
  check(
    invitedProfile.workspace_id === ownerProfile.workspace_id,
    "inbjuden användare delar workspace med den som bjöd in"
  );
  check(invitedProfile.role === "member", "rollen från inbjudan användes");

  const { data: usedInvite } = await admin
    .from("workspace_invites")
    .select("accepted_at")
    .eq("email", invitedEmail)
    .maybeSingle();
  check(usedInvite?.accepted_at, "inbjudan markerades som förbrukad");

  console.log("3. Självläkning av ett konto utan profil");
  await admin.from("profiles").delete().eq("id", owner.id);
  check(!(await profileOf(owner.id)), "profilen är borta (simulerar trasig trigger)");
  const { error: repairError } = await admin.rpc("ensure_workspace_for_user", {
    target_user: owner.id,
    display_name: null
  });
  if (repairError) throw new Error(`reparation misslyckades: ${repairError.message}`);
  check(await profileOf(owner.id), "profilen återskapades");
}

async function cleanup() {
  for (const id of created) {
    const profile = await profileOf(id);
    await admin.auth.admin.deleteUser(id);
    if (profile?.workspace_id) {
      await admin.from("workspaces").delete().eq("id", profile.workspace_id);
    }
  }
}

try {
  await run();
  console.log("\nAllt grönt.");
} catch (error) {
  console.error(`\n${error.message}`);
  process.exitCode = 1;
} finally {
  await cleanup();
}
