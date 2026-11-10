import type { NextRequest } from "next/server";
import {
  KUND_KAKA,
  KUNDSESSION_MAX_MS,
  dekrypteraKundsession,
  tillatnaBackends,
  type Kundsession
} from "@/lib/kundsession";
import { valjNyckel, type Nyckelval } from "@/lib/proxynyckel";

/**
 * Proxyn mot snajp-support-backenden — GENERISK spegel under /api/ag.
 *
 * Till skillnad från bokföringssajtens proxy (ett fast /api/bookkeeping-
 * prefix) speglar den här hela tenant-ytan: agentens flikar spänner flera
 * path-familjer (/api/leads, /api/inbox, /api/drafts, /api/kb, /api/jobs …),
 * precis som huvudappens catch-all. Nyckeln är kundens egen, så ytan är
 * kundens egen data — samma exponering som huvudappen ger.
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
// hemlighet. En riktig miljö sätter SNAJP_AGENT_API_KEY.
const NYCKEL = process.env.SNAJP_AGENT_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

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
 *
 * En kundkaka som inte håller ger aldrig den delade nyckeln, och en driftsatt
 * sajt utan inloggningsvägg ger den inte till någon (lib/proxynyckel.ts).
 */
async function nyckelval(request: NextRequest): Promise<Nyckelval> {
  const kaka = request.cookies.get(KUND_KAKA)?.value;
  const hemlighet = process.env.AGENTSAJT_SSO_SECRET;
  const kund =
    kaka && hemlighet ? await dekrypteraKundsession<Kundsession>(kaka, hemlighet) : null;
  return valjNyckel({
    harKundkaka: Boolean(kaka),
    kund,
    nu: Date.now(),
    maxAlderMs: KUNDSESSION_MAX_MS,
    tillatna: tillatnaBackends(),
    vaggPa: Boolean(process.env.AGENTSAJT_LOSEN),
    produktion: process.env.NODE_ENV === "production"
  });
}

async function vidare(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await params;
  const inUrl = new URL(request.url);
  const val = await nyckelval(request);
  if (val.slag === "avvisad") {
    const svar = Response.json(
      {
        error:
          "Din session har gått ut. Öppna supportagenten från Snajp igen. / Your session has expired. Open the support agent from Snajp again."
      },
      { status: 401 }
    );
    // En utgången kundkaka plockas bort: nästa begäran prövas då som en utan
    // kaka, i stället för att fastna på samma svar.
    if (val.skal === "kundsession") {
      svar.headers.append("Set-Cookie", `${KUND_KAKA}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`);
    }
    return svar;
  }
  const { nyckel, bas } = val.slag === "kund" ? val : { nyckel: NYCKEL, bas: MAL };
  const mal = `${bas}/api/${path.join("/")}${inUrl.search}`;

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
      cache: "no-store",
      // Utan gräns väntade ett anrop mot en hängd backend tills webbläsaren
      // gav upp, och vyn stod med sin laddsnurra (Fas 0, 2026-11-09). 55 s
      // ligger under routens maxDuration; det som tar längre är jobb som
      // pollas, inte en enda begäran.
      signal: AbortSignal.timeout(55_000)
    });
  } catch (fel) {
    const tidsgrans = fel instanceof Error && fel.name === "TimeoutError";
    return Response.json(
      {
        // Texten sa förut "Bokföringstjänsten" — kvar från filen routen
        // kopierades ur. Läsaren är en supportmedarbetare, inte en utvecklare.
        error: tidsgrans
          ? "Supportagenten svarade inte i tid. Försök igen om en stund. / The support agent did not respond in time. Try again shortly."
          : "Supportagenten går inte att nå just nu. Försök igen om en stund. / The support agent cannot be reached right now. Try again shortly."
      },
      { status: tidsgrans ? 504 : 503 }
    );
  }

  const utHeaders = new Headers();
  for (const namn of ["content-type", "content-disposition"]) {
    const varde = svar.headers.get(namn);
    if (varde) utHeaders.set(namn, varde);
  }
  return new Response(await svar.arrayBuffer(), { status: svar.status, headers: utHeaders });
}

export { vidare as DELETE, vidare as GET, vidare as PATCH, vidare as POST, vidare as PUT };
