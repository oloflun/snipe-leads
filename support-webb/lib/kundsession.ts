/**
 * Kundsessionen — det som gör att en kund arbetar mot SIN bokföring.
 *
 * ## Kedjan
 *
 * Snajp-webben (där kunden redan är inloggad) skapar en kortlivad krypterad
 * biljett med kundens tenant-API-nyckel och backend-URL, och skickar hit via
 * /sso. Den löses in mot en httpOnly-kaka med samma innehåll, och API-proxyn
 * (/api/bk) använder kakans nyckel i stället för miljöns delade demonyckel.
 * Nyckeln passerar alltså aldrig webbläsarens JavaScript och står aldrig i
 * en URL i klartext — biljetten är AES-256-GCM och dör efter 60 sekunder.
 *
 * ## Varför Web Crypto och inte node:crypto
 *
 * Dekrypteringen körs även i proxyn (middleware), som kan köra i en
 * edge-runtime utan node-moduler. Webbens biljettsida använder node:crypto
 * men skriver EXAKT samma format: iv (12 byte) följt av ciphertext+tag,
 * base64url. Ändras formatet på ena sidan måste andra sidan med.
 */

export const KUND_KAKA = "bk_kund";

/** 12 timmar — en arbetsdag. Därefter går kunden via webben igen. */
export const KUNDSESSION_MAX_MS = 12 * 60 * 60 * 1000;

export type Kundsession = {
  /** Tenantens API-nyckel mot bokförings-backenden. */
  apiKey: string;
  /** Vilken backend nyckeln gäller — main-api eller dev-api, allowlistad. */
  backendUrl: string;
  slug: string;
  namn: string;
  /** Epoch-ms när sessionen utfärdades — proxyn fäller för gamla kakor. */
  utfardad: number;
};

function base64urlTillBytes(text: string): Uint8Array {
  const b64 = text.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "="));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function bytesTillBase64url(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function aesNyckel(hemlighet: string): Promise<CryptoKey> {
  const rå = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(hemlighet));
  return crypto.subtle.importKey("raw", rå, "AES-GCM", false, ["encrypt", "decrypt"]);
}

export async function krypteraKundsession(
  data: Record<string, unknown>,
  hemlighet: string
): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const nyckel = await aesNyckel(hemlighet);
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    nyckel,
    new TextEncoder().encode(JSON.stringify(data))
  );
  const ut = new Uint8Array(iv.length + ct.byteLength);
  ut.set(iv);
  ut.set(new Uint8Array(ct), iv.length);
  return bytesTillBase64url(ut);
}

/** null vid varje form av fel — en biljett som inte dekrypterar ÄR ingen
 *  biljett, och vilken bit som föll är inget en angripare ska få veta. */
export async function dekrypteraKundsession<T = Record<string, unknown>>(
  text: string,
  hemlighet: string
): Promise<T | null> {
  try {
    const bytes = base64urlTillBytes(text);
    if (bytes.length < 13) return null;
    const nyckel = await aesNyckel(hemlighet);
    const klar = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: bytes.slice(0, 12) },
      nyckel,
      bytes.slice(12)
    );
    return JSON.parse(new TextDecoder().decode(klar)) as T;
  } catch {
    return null;
  }
}

/** Backends som en biljett får peka på. Utan listan hade sajten varit en
 *  öppen proxy mot vad som helst som kan signera en biljett. */
export function tillatnaBackends(): string[] {
  const lista = (process.env.SNAJP_SUPPORT_TILLATNA ?? process.env.SNAJP_SUPPORT_URL ?? "")
    .split(",")
    .map((u) => u.trim().replace(/\/$/, ""))
    .filter(Boolean);
  return lista;
}
