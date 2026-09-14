import "server-only";

import { randomBytes, scrypt as scryptCb, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

const scrypt = promisify(scryptCb) as (
  password: string,
  salt: Buffer,
  keylen: number
) => Promise<Buffer>;

/**
 * Lösenordshashning med Nodes egen scrypt.
 *
 * Ingen bcrypt, ingen argon2: scrypt är en minneshård KDF i standardbiblioteket,
 * och att lägga till ett beroende med native-bygge för det som redan finns i
 * `node:crypto` är precis den sortens rörliga del ombyggnaden skulle bli av med.
 *
 * Formatet bär sina egna parametrar (`scrypt$<N>$<salt>$<hash>`) så att kostnaden
 * kan höjas senare utan att befintliga hashar blir olästa.
 */

const KEYLEN = 64;

export async function hashPassword(password: string): Promise<string> {
  const salt = randomBytes(16);
  const key = await scrypt(password, salt, KEYLEN);
  return `scrypt$1$${salt.toString("base64")}$${key.toString("base64")}`;
}

export async function verifyPassword(password: string, stored: string | null): Promise<boolean> {
  if (!stored) {
    return false;
  }
  const [scheme, , saltB64, hashB64] = stored.split("$");
  if (scheme !== "scrypt" || !saltB64 || !hashB64) {
    return false;
  }
  const expected = Buffer.from(hashB64, "base64");
  const actual = await scrypt(password, Buffer.from(saltB64, "base64"), expected.length);
  // timingSafeEqual kastar på olika längder, vilket i sig läcker information.
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}
