import type { NextRequest } from "next/server";
import {
  KUND_KAKA,
  KUNDSESSION_MAX_MS,
  dekrypteraKundsession,
  tillatnaBackends,
  type Kundsession
} from "@/lib/kundsession";

/**
 * Proxyn mot backendens kvittoyta (`/api/kvitton/*`) — Kvittohanterarens
 * egna endpoints. Samma nyckel- och backendval som /api/bk (läs dess
 * docstring): kundkakans tenantnyckel när kunden kom via SSO, miljöns
 * delade nyckel annars, och ArrayBuffer åt båda hållen eftersom
 * uppladdningen är multipart och CSV-exporten bär Content-Disposition.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

const MAL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8010";
// Demonyckeln är backendens incheckade dev-default (app/config.py) — ingen
// hemlighet. En riktig miljö sätter SNAJP_BOOKKEEPING_API_KEY.
const NYCKEL = process.env.SNAJP_BOOKKEEPING_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

async function nyckelOchMal(request: NextRequest): Promise<{ nyckel: string; bas: string }> {
  const kaka = request.cookies.get(KUND_KAKA)?.value;
  const hemlighet = process.env.BOKFORING_SSO_SECRET;
  if (kaka && hemlighet) {
    const kund = await dekrypteraKundsession<Kundsession>(kaka, hemlighet);
    if (
      kund?.apiKey &&
      Date.now() - kund.utfardad < KUNDSESSION_MAX_MS &&
      tillatnaBackends().includes(kund.backendUrl)
    ) {
      return { nyckel: kund.apiKey, bas: kund.backendUrl };
    }
  }
  return { nyckel: NYCKEL, bas: MAL };
}

async function vidare(
  request: NextRequest,
  { params }: { params: Promise<{ path?: string[] }> }
): Promise<Response> {
  const { path = [] } = await params;
  const inUrl = new URL(request.url);
  const { nyckel, bas } = await nyckelOchMal(request);
  const svans = path.length ? `/${path.join("/")}` : "";
  const mal = `${bas}/api/kvitton${svans}${inUrl.search}`;

  const headers = new Headers({ "X-API-Key": nyckel });
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const kropp =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  let svar: Response;
  try {
    svar = await fetch(mal, {
      method: request.method,
      headers,
      body: kropp,
      cache: "no-store"
    });
  } catch {
    return Response.json(
      {
        error:
          "Kvittotjänsten svarar inte. Kontrollera att backenden är igång och försök igen."
      },
      { status: 503 }
    );
  }

  const utHeaders = new Headers();
  for (const namn of ["content-type", "content-disposition"]) {
    const varde = svar.headers.get(namn);
    if (varde) utHeaders.set(namn, varde);
  }
  return new Response(await svar.arrayBuffer(), { status: svar.status, headers: utHeaders });
}

export { vidare as DELETE, vidare as GET, vidare as POST };
