import { createCipheriv, createHash, randomBytes } from "node:crypto";
import "server-only";

/**
 * SSO-biljetten till den fristående bokföringssajten (bokforing-webb/).
 *
 * En inloggad kund som klickar på Bokföring ska landa på sajten SOM SIG
 * SJÄLV — med sin tenantnyckel, mot sin miljös backend — utan att logga in
 * en gång till och utan att nyckeln passerar webbläsaren i klartext.
 * Biljetten är AES-256-GCM med den delade hemligheten BOKFORING_SSO_SECRET
 * och dör efter 60 sekunder; sajten löser in den mot en httpOnly-kaka
 * (bokforing-webb/app/sso/route.ts).
 *
 * FORMATKONTRAKT med bokforing-webb/lib/kundsession.ts, som dekrypterar med
 * Web Crypto: nyckel = SHA-256 av hemligheten, meddelande = iv (12 byte)
 * följt av ciphertext+authtag, base64url. Web Cryptos AES-GCM förväntar sig
 * taggen SIST i ciphertexten — därav ordningen i concat. Ändras något här
 * måste andra sidan med.
 */

export type BokforingsBiljett = {
  /** Tenantens API-nyckel mot bokförings-backenden. */
  k: string;
  /** Backend-URL:en nyckeln gäller — valideras mot sajtens allowlist. */
  b: string;
  s: string;
  n: string;
  exp: number;
};

const LIVSTID_MS = 60_000;

export function skapaBokforingsBiljett(
  data: Omit<BokforingsBiljett, "exp">,
  hemlighet: string
): string {
  const nyckel = createHash("sha256").update(hemlighet, "utf8").digest();
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", nyckel, iv);
  const kropp = Buffer.concat([
    cipher.update(JSON.stringify({ ...data, exp: Date.now() + LIVSTID_MS }), "utf8"),
    cipher.final()
  ]);
  return Buffer.concat([iv, kropp, cipher.getAuthTag()]).toString("base64url");
}
