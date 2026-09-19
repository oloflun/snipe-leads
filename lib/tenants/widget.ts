import type { Tenant } from "./types.ts";

/**
 * Widgetens rena funktioner — utbrutna ur index.ts så att de går att köra i
 * `node --test`, som inte löser extensionslösa imports genom hela registret.
 * index.ts binder dem till registret och är den import resten av appen ska
 * använda.
 */

/**
 * Publik nyckel → tenant, ur en given lista. Nyckeln ÄR publik (den står i
 * kundens HTML), så uppslaget är inte en autentisering utan en adressbok —
 * men bara tenants med ett satt `publicKey` deltar, och jämförelsen är exakt.
 */
export function hittaTenantMedPublicKey(
  alla: Tenant[],
  publicKey: string | null | undefined
): Tenant | null {
  if (!publicKey) {
    return null;
  }
  return alla.find((tenant) => tenant.publicKey === publicKey) ?? null;
}

/**
 * CSP-värdet för /embed/<nyckel> (sätts i proxy.ts). 'self' står alltid med
 * så att en testsida på vår egen domän kan bädda in widgeten; en okänd
 * nyckel ger 'none' — sidan 404:ar ändå, men webbläsaren ska inte ens
 * rendera den i en främmande ram.
 */
export function frameAncestors(tenant: Tenant | null): string {
  const origins = (tenant?.embedOrigins ?? []).filter(Boolean);
  if (!tenant || !tenant.publicKey) {
    return "frame-ancestors 'none'";
  }
  return `frame-ancestors 'self'${origins.length ? " " + origins.join(" ") : ""}`;
}
