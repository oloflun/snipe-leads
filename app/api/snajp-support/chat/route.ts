import { NextRequest } from "next/server";
import { proxyToBackend } from "../_lib";

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

/**
 * ANONYM MED FLIT (INV-SEC-010). Den här routen är den publika demon och
 * kundernas egna chattlänkar. Kunden publicerar länken själv — att kräva
 * inloggning här hade varit att kräva inloggning av kundens kunder, alltså
 * att ta bort produkten.
 *
 * Skyddet är därför ett annat: rate limit per IP i databasen (migration 019),
 * som överlever Renders spin-down. Ingen session, ingen kunddata, ingen
 * administrativ yta — den får bara starta ett chattjobb.
 */
export async function POST(request: NextRequest) {
  const body = await request.text();

  // Tenanten kommer från klientens payload och avgör vilken API-nyckel som
  // används. Den är inte känslig i sig — nyckeln finns bara på servern, så en
  // förfalskad slug ger på sin höjd fel kunds publika kunskapsbas, aldrig
  // åtkomst till någons data.
  let tenant: string | null = null;
  try {
    tenant = (JSON.parse(body) as { tenant?: string }).tenant ?? null;
  } catch {
    // Ogiltig JSON får backenden avvisa med sitt eget felmeddelande.
  }

  return proxyToBackend("/api/chat", { method: "POST", body }, tenant);
}
