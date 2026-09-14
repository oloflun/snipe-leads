/**
 * Vertex-tokenflödet. Kör: node --test "lib/llm/*.test.ts"
 *
 * JWT:t signeras med en nyckel som genereras i testet och verifieras mot dess
 * publika halva — inget nätverk, ingen riktig service account.
 */
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { createVerify, generateKeyPairSync } from "node:crypto";
import { byggJwt, hamtaVertexToken, MARGINAL_MS, tomTokencache, VertexTokenFel } from "./vertex.ts";
import type { ServiceAccount } from "./modellval.ts";

const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const SA: ServiceAccount = {
  client_email: "snajp@test-proj.iam.gserviceaccount.com",
  private_key: privateKey.export({ type: "pkcs8", format: "pem" }).toString(),
  private_key_id: "kid-1",
  project_id: "test-proj",
  token_uri: "https://oauth2.googleapis.com/token"
};

function avkoda(del: string): Record<string, unknown> {
  return JSON.parse(Buffer.from(del, "base64url").toString("utf8"));
}

beforeEach(() => tomTokencache());

test("JWT: header, claims och en RS256-signatur som verifierar", () => {
  const jwt = byggJwt(SA, 1_700_000_000);
  const [h, c, s] = jwt.split(".");
  assert.deepEqual(avkoda(h), { alg: "RS256", typ: "JWT", kid: "kid-1" });
  assert.deepEqual(avkoda(c), {
    iss: SA.client_email,
    sub: SA.client_email,
    scope: "https://www.googleapis.com/auth/cloud-platform",
    aud: "https://oauth2.googleapis.com/token",
    iat: 1_700_000_000,
    exp: 1_700_003_600
  });
  // base64url utan utfyllnad — Google avvisar '=', '+' och '/'.
  assert.doesNotMatch(jwt, /[=+/]/);
  const ok = createVerify("RSA-SHA256").update(`${h}.${c}`).verify(publicKey, Buffer.from(s, "base64url"));
  assert.equal(ok, true);
});

test("JWT: en annan nyckel verifierar inte", () => {
  const annan = generateKeyPairSync("rsa", { modulusLength: 2048 }).publicKey;
  const [h, c, s] = byggJwt(SA).split(".");
  assert.equal(createVerify("RSA-SHA256").update(`${h}.${c}`).verify(annan, Buffer.from(s, "base64url")), false);
});

function falskFetch(svar: () => { status: number; body: string }) {
  const anrop: { url: string; body: string }[] = [];
  const f = (async (url: string | URL | Request, init?: RequestInit) => {
    anrop.push({ url: String(url), body: String(init?.body ?? "") });
    const { status, body } = svar();
    return new Response(body, { status });
  }) as typeof fetch;
  return { f, anrop };
}

test("tokenväxling: jwt-bearer mot token_uri, och tokenen cachas", async () => {
  let nu = 1_700_000_000_000;
  const { f, anrop } = falskFetch(() => ({ status: 200, body: JSON.stringify({ access_token: "ya29.test", expires_in: 3599 }) }));
  const t1 = await hamtaVertexToken(SA, { fetch: f, nuMs: () => nu });
  nu += 10 * 60 * 1000;
  const t2 = await hamtaVertexToken(SA, { fetch: f, nuMs: () => nu });
  assert.equal(t1, "ya29.test");
  assert.equal(t2, "ya29.test");
  assert.equal(anrop.length, 1, "andra anropet inom giltighetstiden ska komma ur cachen");
  assert.equal(anrop[0].url, SA.token_uri);
  const form = new URLSearchParams(anrop[0].body);
  assert.equal(form.get("grant_type"), "urn:ietf:params:oauth:grant-type:jwt-bearer");
  assert.equal(form.get("assertion")?.split(".").length, 3);
});

test("tokenväxling: byts i god tid före utgång", async () => {
  let nu = 1_700_000_000_000;
  let n = 0;
  const { f, anrop } = falskFetch(() => ({ status: 200, body: JSON.stringify({ access_token: `tok-${++n}`, expires_in: 3600 }) }));
  await hamtaVertexToken(SA, { fetch: f, nuMs: () => nu });
  nu += 3600 * 1000 - MARGINAL_MS + 1;
  const ny = await hamtaVertexToken(SA, { fetch: f, nuMs: () => nu });
  assert.equal(ny, "tok-2");
  assert.equal(anrop.length, 2);
});

test("tokenväxling: samtidiga anrop delar en begäran", async () => {
  const { f, anrop } = falskFetch(() => ({ status: 200, body: JSON.stringify({ access_token: "delad", expires_in: 3600 }) }));
  const svar = await Promise.all([hamtaVertexToken(SA, { fetch: f }), hamtaVertexToken(SA, { fetch: f }), hamtaVertexToken(SA, { fetch: f })]);
  assert.deepEqual(svar, ["delad", "delad", "delad"]);
  assert.equal(anrop.length, 1);
});

test("tokenväxling: felstatus kastar VertexTokenFel med status och kropp", async () => {
  const { f } = falskFetch(() => ({ status: 400, body: '{"error":"invalid_grant"}' }));
  await assert.rejects(hamtaVertexToken(SA, { fetch: f }), (fel: unknown) => {
    assert.ok(fel instanceof VertexTokenFel);
    assert.equal(fel.statusCode, 400);
    assert.match(fel.responseBody ?? "", /invalid_grant/);
    return true;
  });
});
