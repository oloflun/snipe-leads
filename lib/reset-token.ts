import { createHash, randomBytes } from "node:crypto";

/**
 * Engångstoken för lösenordsåterställning.
 *
 * Token är 32 slumpbytes i base64url — den formen går oskadd genom en
 * query-parameter utan kodning. I databasen lagras bara SHA-256-hashen
 * (password_reset_tokens.token_hash): en läckt tabell ger inga användbara
 * länkar, och ett uppslag är en exakt indexträff i stället för en skanning.
 *
 * SHA-256 utan salt är rätt här, till skillnad från lösenord: token har 256
 * bitar entropi och går inte att gissa med ordlista — saltets jobb är redan
 * gjort av slumpen.
 */

export const RESET_TOKEN_GILTIG_MINUTER = 60;

export function nyResetToken(): { token: string; hash: string } {
  const token = randomBytes(32).toString("base64url");
  return { token, hash: hashaResetToken(token) };
}

export function hashaResetToken(token: string): string {
  return createHash("sha256").update(token, "utf8").digest("hex");
}

/**
 * Snabb formgrind innan databasen tillfrågas. Base64url för 32 bytes är 43
 * tecken; allt annat är skräp eller en manipulerad länk och ska inte ge en
 * databasfråga.
 */
export function serUtSomResetToken(varde: unknown): varde is string {
  return typeof varde === "string" && /^[A-Za-z0-9_-]{43}$/.test(varde);
}
