import "server-only";

import { promisify } from "node:util";
import { gzip } from "node:zlib";

const gzipAsync = promisify(gzip);

/** Under det här lönar sig komprimeringen inte: huvudet äter vinsten. */
const MINSTA_BYTE = 1024;

/**
 * Gzippar ett JSON-svar från en route handler, om klienten tar emot gzip.
 *
 * ## Varför det behövs
 *
 * Next komprimerar sidor och statiska filer, men INTE svaren från route
 * handlers — och Railways edge komprimerar ingenting. Uppmätt 2026-10-09:
 * Leads-fliken hämtade 364 KB körningar och 259 KB prospekt okomprimerat vid
 * varje besök, JSON som krymper till ungefär en tiondel. På en mobil eller en
 * svag uppkoppling var det skillnaden mellan ett flikbyte och en väntan.
 *
 * Bara route handlers ska anropa den här. Server actions och server-
 * komponenter läser proxyns svar själva (lib/data/admin.ts, lib/actions/*),
 * och en gzippad kropp i en lokalt skapad Response packas aldrig upp åt dem.
 *
 * Asynkron gzip med flit: den synkrona varianten kör i händelseloopen och
 * hade låst varje samtidig förfrågan medan ett stort svar packades.
 */
export async function komprimera(request: Request, svar: Response): Promise<Response> {
  if (!svar.body || svar.headers.has("content-encoding")) {
    return svar;
  }
  const typ = svar.headers.get("content-type") ?? "";
  if (!typ.includes("json")) {
    return svar;
  }
  const accepterar = request.headers.get("accept-encoding") ?? "";
  if (!/\bgzip\b/i.test(accepterar)) {
    return svar;
  }

  const kropp = Buffer.from(await svar.arrayBuffer());
  const huvuden = new Headers(svar.headers);
  huvuden.append("Vary", "Accept-Encoding");

  if (kropp.byteLength < MINSTA_BYTE) {
    return new Response(kropp, { status: svar.status, statusText: svar.statusText, headers: huvuden });
  }

  const packad = await gzipAsync(kropp, { level: 6 });
  huvuden.set("Content-Encoding", "gzip");
  huvuden.delete("Content-Length");
  return new Response(packad, { status: svar.status, statusText: svar.statusText, headers: huvuden });
}
