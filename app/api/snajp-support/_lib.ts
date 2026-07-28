import { NextResponse } from "next/server";

// Tunn proxy mot den headless Snajp-Support-backenden (FastAPI, hostas på Render).
// Webbläsaren träffar bara Next-appen; den interna API-nyckeln sätts server-side.
// SNAJP_SUPPORT_URL sätts på Vercel till Render-URL:en; lokalt defaultar den till 8000.

export const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";
export const SNAJP_INTERNAL_API_KEY =
  process.env.SNAJP_INTERNAL_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

// Skiljer på "env-varen är inte satt" och "backenden svarar inte" — utan detta
// ser båda felen likadana ut i UI:t och man felsöker åt fel håll.
const URL_IS_CONFIGURED = Boolean(process.env.SNAJP_SUPPORT_URL);

export function offlineResponse(cause?: unknown) {
  const reason = cause instanceof Error ? cause.message : undefined;
  const error = URL_IS_CONFIGURED
    ? `Snajp-Support-backenden på ${SNAJP_SUPPORT_URL} svarar inte${reason ? ` (${reason})` : ""}. Kontrollera att Render-tjänsten är deployad och vaken.`
    : "SNAJP_SUPPORT_URL är inte satt i denna miljö — proxyn föll tillbaka på localhost, som inte finns i deploy. Sätt env-varen till Render-URL:en och deploya om.";

  return NextResponse.json({ offline: true, configured: URL_IS_CONFIGURED, target: SNAJP_SUPPORT_URL, error }, { status: 503 });
}

export async function proxyToBackend(path: string, init: RequestInit) {
  try {
    const response = await fetch(`${SNAJP_SUPPORT_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": SNAJP_INTERNAL_API_KEY,
        ...(init.headers ?? {})
      },
      cache: "no-store"
    });
    const body = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch (cause) {
    return offlineResponse(cause);
  }
}
