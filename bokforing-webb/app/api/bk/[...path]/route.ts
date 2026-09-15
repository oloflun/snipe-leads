import type { NextRequest } from "next/server";
import {
  KUND_KAKA,
  KUNDSESSION_MAX_MS,
  dekrypteraKundsession,
  tillatnaBackends,
  type Kundsession
} from "@/lib/kundsession";

/**
 * Proxyn mot snajp-support-backendens bokföringsyta.
 *
 * ## Varför en proxy och inte fetch direkt från webbläsaren
 *
 * Backenden autentiserar med `X-API-Key`, och en nyckel som skickas från
 * webbläsaren är en nyckel vem som helst kan läsa i Nätverk-fliken. Den bor
 * därför här, på serversidan, och läses ur miljön.
 *
 * ## ArrayBuffer åt båda hållen
 *
 * Kroppen får inte tolkas som text: uppladdningen är multipart (kvitton,
 * bilder) och SIE-exporten svarar CP437-kodade bytes med Content-Disposition.
 * Samma beslut som huvudappens proxy (app/api/snajp-support/bookkeeping/),
 * och av samma skäl.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

const MAL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8010";
// Demonyckeln är backendens incheckade dev-default (app/config.py) — ingen
// hemlighet. En riktig miljö sätter SNAJP_BOOKKEEPING_API_KEY.
const NYCKEL = process.env.SNAJP_BOOKKEEPING_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

/**
 * Vems nyckel, mot vilken backend?
 *
 * En kund som kom via Snajp-webbens SSO bär sin tenantnyckel i kundkakan
 * (lib/kundsession.ts) och arbetar mot SIN data. Backend-URL:en ur kakan
 * valideras mot allowlistan IGEN här — kakan är visserligen vår egen
 * kryptering, men en kontroll som bara görs vid utfärdandet är en kontroll
 * som slutar gälla när listan ändras.
 *
 * Utan kundkaka (förhandslösnet, lokal utveckling): miljöns delade nyckel
 * mot miljöns backend — demo-tenanten.
 */
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
  { params }: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await params;
  const inUrl = new URL(request.url);
  const { nyckel, bas } = await nyckelOchMal(request);
  const mal = `${bas}/api/bookkeeping/${path.join("/")}${inUrl.search}`;

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
          "Bokföringstjänsten svarar inte. Kontrollera att backenden är igång och försök igen."
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
