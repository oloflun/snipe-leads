import { NextRequest } from "next/server";
import { proxyAsTenant } from "../../_auth";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Testchattens motsvarighet till `../../chat/samtal/route.ts` (bd snipe-1fl):
 * samma hämtning, men tenanten kommer ur SESSIONEN (`proxyAsTenant`) och inte
 * ur en slug klienten skickar — av exakt samma skäl som `../route.ts`.
 * Låter en inloggad kund prova hela överlämningen: eskalera i testchatten,
 * svara i portalens Chattar-vy, se svaret dyka upp här.
 */
export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAsTenant("/api/chat/samtal", { method: "POST", body: body || undefined });
}
