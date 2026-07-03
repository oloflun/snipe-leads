import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
for (const line of readFileSync(join(root, ".env"), "utf8").split(/\r?\n/)) {
  if (!line || line.startsWith("#") || !line.includes("=")) continue;
  const i = line.indexOf("=");
  process.env[line.slice(0, i).trim()] = line.slice(i + 1).trim();
}

const sec = process.env.SUPABASE_SERVICE_ROLE_KEY;
const base = process.env.NEXT_PUBLIC_SUPABASE_URL;
const email = `snipra.dev.${Date.now()}@example.com`;
const password = "WolfofSnipra26!";
const headers = {
  apikey: sec,
  Authorization: `Bearer ${sec}`,
  "Content-Type": "application/json"
};

const signup = await fetch(`${base}/auth/v1/signup`, {
  method: "POST",
  headers,
  body: JSON.stringify({ email, password, data: { full_name: "Snipra Dev" } })
});
const signupBody = await signup.text();
console.log("signup", signup.status, signupBody.slice(0, 600));

const login = await fetch(`${base}/auth/v1/token?grant_type=password`, {
  method: "POST",
  headers,
  body: JSON.stringify({ email, password })
});
const loginBody = await login.text();
console.log("login", login.status, loginBody.slice(0, 300));

const serviceHeaders = { apikey: sec, Authorization: `Bearer ${sec}` };
const workspaces = await fetch(`${base}/rest/v1/workspaces?select=id,name`, { headers: serviceHeaders });
console.log("workspaces", workspaces.status, await workspaces.text());
const profiles = await fetch(`${base}/rest/v1/profiles?select=id,full_name,workspace_id`, { headers: serviceHeaders });
console.log("profiles", profiles.status, await profiles.text());