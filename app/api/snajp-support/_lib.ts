import { NextResponse } from "next/server";

// Tunn proxy mot den headless Snajp-Support-backenden (FastAPI, port 8000).
// Webbläsaren träffar bara Next-appen; den interna API-nyckeln sätts server-side.

export const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";
export const SNAJP_INTERNAL_API_KEY =
  process.env.SNAJP_INTERNAL_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

export function offlineResponse() {
  return NextResponse.json(
    {
      offline: true,
      error:
        "Snajp-Support-backenden svarar inte. Starta den med: cd snajp-support && .venv\\Scripts\\uvicorn app.main:app --port 8000"
    },
    { status: 503 }
  );
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
  } catch {
    return offlineResponse();
  }
}
