/**
 * Modellvalet i Email Studio. Kör: node --test "lib/llm/*.test.ts"
 *
 * Varje test här motsvarar ett sätt valet har gått sönder tyst: fel ordning,
 * en platshållare räknad som nyckel, eller DeepSeek i en miljö med riktig
 * kunddata (CLAUDE.md, beslut 2026-08-24).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync } from "node:crypto";
import {
  arLoopback,
  harRiktigKunddata,
  lasServiceAccount,
  valjModell,
  vertexBaseUrl,
  vertexModellnamn
} from "./modellval.ts";

const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const PEM = privateKey.export({ type: "pkcs8", format: "pem" }).toString();
const SA_JSON = JSON.stringify({
  type: "service_account",
  project_id: "test-proj",
  private_key_id: "abc123",
  private_key: PEM,
  client_email: "snajp@test-proj.iam.gserviceaccount.com",
  token_uri: "https://oauth2.googleapis.com/token"
});
const NYCKEL = "sk-riktig-nyckel-0123456789abcdef";

test("OpenAI vinner över allt annat", () => {
  const val = valjModell({ OPENAI_API_KEY: NYCKEL, GOOGLE_SERVICE_ACCOUNT_JSON: SA_JSON, GEMINI_API_KEY: NYCKEL });
  assert.equal(val?.provider, "openai");
});

test("Vertex väljs före GEMINI_API_KEY när service account finns", () => {
  const val = valjModell({ GOOGLE_SERVICE_ACCOUNT_JSON: SA_JSON, GEMINI_API_KEY: NYCKEL });
  assert.equal(val?.provider, "vertex");
  assert.ok(val && val.provider === "vertex");
  assert.equal(val.region, "europe-west1");
  // Med publisher: openapi-endpointen svarar 400 på ett bart namn.
  assert.equal(val.namn, "google/gemini-2.5-flash");
  assert.equal(
    val.baseURL,
    "https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/test-proj/locations/europe-west1/endpoints/openapi/"
  );
});

test("Vertex: GOOGLE_CLOUD_REGION och ett gemini-MODEL respekteras", () => {
  const val = valjModell({ GOOGLE_SERVICE_ACCOUNT_JSON: SA_JSON, GOOGLE_CLOUD_REGION: "europe-north1", MODEL: "gemini-2.5-pro" });
  assert.ok(val && val.provider === "vertex");
  assert.equal(val.region, "europe-north1");
  assert.equal(val.namn, "google/gemini-2.5-pro");
  assert.ok(val.baseURL.startsWith("https://europe-north1-aiplatform.googleapis.com/"));
});

test("Vertex: ett MODEL från annan leverantör ger gemini-default, inte 404", () => {
  const val = valjModell({ GOOGLE_SERVICE_ACCOUNT_JSON: SA_JSON, MODEL: "deepseek-v4-flash" });
  assert.equal(val?.namn, "google/gemini-2.5-flash");
});

test("vertexModellnamn: bart namn får google/, en satt publisher lämnas orörd", () => {
  assert.equal(vertexModellnamn("gemini-2.5-flash"), "google/gemini-2.5-flash");
  assert.equal(vertexModellnamn("  gemini-2.5-pro "), "google/gemini-2.5-pro");
  // Aldrig google/google/… — en redan prefixad sträng är ett beslut.
  assert.equal(vertexModellnamn("google/gemini-2.5-flash"), "google/gemini-2.5-flash");
  assert.equal(vertexModellnamn("meta/llama-4"), "meta/llama-4");
  assert.equal(vertexModellnamn(""), "");
});

test("GEMINI_API_KEY-grenen (AI Studio) får INTE prefix — den endpointen vill ha bart namn", () => {
  const val = valjModell({ GEMINI_API_KEY: NYCKEL });
  assert.equal(val?.provider, "gemini");
  assert.equal(val?.namn, "gemini-2.5-flash");
});

test("trasig service account-JSON faller vidare till GEMINI_API_KEY", () => {
  const val = valjModell({ GOOGLE_SERVICE_ACCOUNT_JSON: "{inte json", GEMINI_API_KEY: NYCKEL });
  assert.equal(val?.provider, "gemini");
});

test("platshållare räknas inte som nyckel", () => {
  assert.equal(valjModell({ OPENAI_API_KEY: "sk-...", GEMINI_API_KEY: "din-gemini-nyckel-har-xxxxxxxx" }), null);
});

test("DeepSeek tillåts lokalt mot syntetisk data", () => {
  const val = valjModell({ DEEPSEEK_API_KEY: NYCKEL, NODE_ENV: "development" });
  assert.equal(val?.provider, "deepseek");
});

for (const miljo of ["development", "main", "production", "dev", "prod"]) {
  test(`DeepSeek spärras i Railway-miljön '${miljo}'`, () => {
    // NODE_ENV medvetet INTE production: spärren får inte hänga på den.
    assert.equal(valjModell({ DEEPSEEK_API_KEY: NYCKEL, RAILWAY_ENVIRONMENT_NAME: miljo, NODE_ENV: "development" }), null);
    assert.equal(valjModell({ DEEPSEEK_API_KEY: NYCKEL, ENVIRONMENT: miljo, NODE_ENV: "development" }), null);
  });
}

test("DeepSeek spärras mot en fjärrdatabas även utan miljönamn (Render-fallet)", () => {
  const env = { DEEPSEEK_API_KEY: NYCKEL, NODE_ENV: "development", DATABASE_URL: "postgres://u:p@db.railway.internal:5432/x" };
  assert.equal(valjModell(env), null);
});

test("DeepSeek spärras i ett produktionsbygge utan miljönamn och databas", () => {
  assert.equal(valjModell({ DEEPSEEK_API_KEY: NYCKEL, NODE_ENV: "production" }), null);
});

test("harRiktigKunddata: loopback-databasen är syntetisk", () => {
  assert.equal(harRiktigKunddata({ DATABASE_URL: "postgresql://postgres:x@127.0.0.1:54322/postgres" }), false);
  assert.equal(harRiktigKunddata({ DATABASE_URL: "postgres://u:p@localhost/db" }), false);
  assert.equal(harRiktigKunddata({}), false);
});

test("arLoopback: snabel-a i lösenordet lurar inte spärren", () => {
  assert.equal(arLoopback("postgres://u:p@ss@localhost@prod.example.com:5432/db"), false);
  assert.equal(arLoopback("postgres://u:p@ss@127.0.0.1:5432/db"), true);
});

test("lasServiceAccount: bokstavliga \\n i nyckeln blir radbrytningar", () => {
  const inklistrad = JSON.stringify({
    project_id: "p",
    client_email: "a@p.iam.gserviceaccount.com",
    private_key: PEM.replace(/\n/g, "\\n")
  });
  const sa = lasServiceAccount(inklistrad);
  assert.ok(sa);
  assert.equal(sa.private_key, PEM);
  assert.equal(sa.token_uri, "https://oauth2.googleapis.com/token");
});

test("lasServiceAccount: fält som saknas ger null", () => {
  assert.equal(lasServiceAccount(JSON.stringify({ project_id: "p" })), null);
  assert.equal(lasServiceAccount(""), null);
});

test("vertexBaseUrl speglar llm.py", () => {
  assert.equal(
    vertexBaseUrl("proj", "europe-west1"),
    "https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/proj/locations/europe-west1/endpoints/openapi/"
  );
});
