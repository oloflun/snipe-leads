import { NextResponse } from "next/server";

// Tunn proxy mot den headless Snajp-Support-backenden (FastAPI, hostas på Render).
// Webbläsaren träffar bara Next-appen; den interna API-nyckeln sätts server-side.
// SNAJP_SUPPORT_URL sätts på Vercel till Render-URL:en; lokalt defaultar den till 8000.

export const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";
// Demo-tenantens nyckel. Används ENBART av den publika demon (/api/snajp-demo).
// Inloggade kunder proxas med sin egen tenants nyckel, se lib/snajp/tenant.ts.
export const SNAJP_DEMO_API_KEY =
  process.env.SNAJP_INTERNAL_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

// Skiljer på "env-varen är inte satt" och "backenden svarar inte" — utan detta
// ser båda felen likadana ut i UI:t och man felsöker åt fel håll.
const URL_IS_CONFIGURED = Boolean(process.env.SNAJP_SUPPORT_URL);

export function offlineResponse(cause?: unknown) {
  const reason = cause instanceof Error ? cause.message : undefined;
  const error = URL_IS_CONFIGURED
    ? `Snajp-Support-backenden på ${SNAJP_SUPPORT_URL} svarar inte${reason ? ` (${reason})` : ""}. Gratisplanen på Render somnar efter 15 minuters inaktivitet och tar ungefär en minut att vakna — vänta och försök igen.`
    : "SNAJP_SUPPORT_URL är inte satt i denna miljö — proxyn föll tillbaka på localhost, som inte finns i deploy. Sätt env-varen till Render-URL:en och deploya om.";

  return NextResponse.json(
    { offline: true, configured: URL_IS_CONFIGURED, target: SNAJP_SUPPORT_URL, error },
    { status: 503 }
  );
}

// Render free-tier somnar efter 15 min och tar ~1 min att vakna. Ett enskilt
// försök kan alltså inte lyckas — men hela budgeten nedan (5 × 10 s) täcker
// uppvakningen, förutsatt att route-filerna sätter `maxDuration = 60` så att
// Vercel inte dödar funktionen på vägen.
const ATTEMPT_TIMEOUT_MS = 10_000;
const MAX_ATTEMPTS = 5;

/**
 * Vidarebefordrar ett anrop till backenden som en bestämd tenant.
 *
 * apiKey är obligatorisk och avgör VEMS data anropet når — backendens
 * tenant-separation utgår från nyckeln. Anroparen ansvarar för att ha
 * autentiserat användaren och hämtat rätt nyckel (se lib/snajp/tenant.ts).
 */
export async function proxyToBackend(path: string, init: RequestInit, apiKey: string) {
  let lastCause: unknown;

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ATTEMPT_TIMEOUT_MS);
    try {
      const response = await fetch(`${SNAJP_SUPPORT_URL}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
          ...(init.headers ?? {})
        },
        cache: "no-store",
        signal: controller.signal
      });
      const body = await response.json();
      return NextResponse.json(body, { status: response.status });
    } catch (cause) {
      lastCause = cause;
      // Bara timeout/nätverksfel är värt att göra om — ett riktigt HTTP-svar
      // har redan returnerats ovan.
      if (attempt < MAX_ATTEMPTS - 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    } finally {
      clearTimeout(timer);
    }
  }

  return offlineResponse(lastCause);
}
