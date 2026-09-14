import { createSign } from "node:crypto";
import type { ServiceAccount } from "./modellval.ts";

/**
 * Vertex AI-token ur en service account — utan google-auth-library.
 *
 * ## Varför egen implementation
 *
 * Backenden använder google-auth (snajp-support/app/agent/llm.py). Next-sidan
 * har inget motsvarande beroende, och flödet är litet nog att skriva mot
 * node:crypto: ett RS256-signerat JWT byts mot en OAuth2-token på Googles
 * tokenendpoint (RFC 7523, "jwt-bearer"). Det är exakt vad
 * `service_account.Credentials.refresh()` gör under huven.
 *
 * ## Varför cachen har marginal
 *
 * Tokenen gäller ~1 timme. En token som går ut MITT i ett modellanrop ger 401
 * och ett "tillfälligt fel" kunden inte kan göra något åt. Därför byts den
 * fem minuter före utgång — google-auth har samma slags marginal.
 *
 * Filen läser aldrig process.env och loggar aldrig nyckeln eller tokenen.
 */

const SCOPE = "https://www.googleapis.com/auth/cloud-platform";
const GILTIGHET_SEK = 3600;
/** Byt tokenen så här långt före utgång. */
export const MARGINAL_MS = 5 * 60 * 1000;

function base64url(data: string | Buffer): string {
  return Buffer.from(data).toString("base64").replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
}

/** Det signerade JWT:t som växlas mot en token. `nuSek` är injicerbar för testerna. */
export function byggJwt(sa: ServiceAccount, nuSek: number = Math.floor(Date.now() / 1000)): string {
  const header: Record<string, string> = { alg: "RS256", typ: "JWT" };
  if (sa.private_key_id) header.kid = sa.private_key_id;
  const claims = {
    iss: sa.client_email,
    sub: sa.client_email,
    scope: SCOPE,
    aud: sa.token_uri,
    iat: nuSek,
    exp: nuSek + GILTIGHET_SEK
  };
  const osignerat = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}`;
  const signatur = createSign("RSA-SHA256").update(osignerat).sign(sa.private_key);
  return `${osignerat}.${base64url(signatur)}`;
}

type Cachad = { token: string; utgarMs: number };

/** Nyckeln är kontot — en annan service account får aldrig en annans token. */
const cache = new Map<string, Cachad>();
/** Pågående växlingar: tio samtidiga klick ska ge EN tokenbegäran, inte tio. */
const pagaende = new Map<string, Promise<string>>();

/** Fel från tokenväxlingen, med status så att lib/llm/kvotfel.ts kan klassa det. */
export class VertexTokenFel extends Error {
  statusCode: number | undefined;
  responseBody: string | undefined;
  constructor(meddelande: string, statusCode?: number, responseBody?: string) {
    super(meddelande);
    this.name = "VertexTokenFel";
    this.statusCode = statusCode;
    this.responseBody = responseBody;
  }
}

type Beroenden = { fetch?: typeof fetch; nuMs?: () => number };

/** Aktuell OAuth2-token för kontot. Cachad, bytt i god tid före utgång. */
export async function hamtaVertexToken(sa: ServiceAccount, beroenden: Beroenden = {}): Promise<string> {
  const nuMs = beroenden.nuMs ?? Date.now;
  const nyckel = `${sa.client_email}|${sa.private_key_id ?? ""}`;

  const cachad = cache.get(nyckel);
  if (cachad && cachad.utgarMs - MARGINAL_MS > nuMs()) return cachad.token;

  const redan = pagaende.get(nyckel);
  if (redan) return redan;

  const vaxling = (async () => {
    const hamta = beroenden.fetch ?? fetch;
    const res = await hamta(sa.token_uri, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
        assertion: byggJwt(sa, Math.floor(nuMs() / 1000))
      }).toString(),
      signal: AbortSignal.timeout(10_000)
    });
    const text = await res.text();
    if (!res.ok) {
      // Kroppen är Googles felbeskrivning ("invalid_grant" o.d.) — den bär
      // aldrig nyckeln, och den behövs för att se VARFÖR växlingen föll.
      throw new VertexTokenFel(`Vertex-tokenväxlingen svarade ${res.status}`, res.status, text.slice(0, 500));
    }
    let data: { access_token?: unknown; expires_in?: unknown };
    try {
      data = JSON.parse(text);
    } catch {
      throw new VertexTokenFel("Vertex-tokenväxlingen svarade med något som inte är JSON", res.status);
    }
    if (typeof data.access_token !== "string" || !data.access_token) {
      throw new VertexTokenFel("Vertex-tokenväxlingen svarade utan access_token", res.status);
    }
    const livslangdSek = typeof data.expires_in === "number" ? data.expires_in : GILTIGHET_SEK;
    cache.set(nyckel, { token: data.access_token, utgarMs: nuMs() + livslangdSek * 1000 });
    return data.access_token;
  })();

  pagaende.set(nyckel, vaxling);
  try {
    return await vaxling;
  } finally {
    pagaende.delete(nyckel);
  }
}

/** Bara för testerna. */
export function tomTokencache(): void {
  cache.clear();
  pagaende.clear();
}
