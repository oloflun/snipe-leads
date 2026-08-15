import { NextRequest } from "next/server";
import { proxyToBackend } from "../_lib";

// ANONYM med flit. Den här routen driver "Sortera inkorgen" på den publika
// /support-sidan (components/snajp/InboxTriage.tsx), alltså marknadsföringsdemon.
//
// Att den får vara öppen vilar på att backendens /api/triage är läsande:
// den klassificerar mejl som klienten själv skickat in och slår i demo-tenantens
// kunskapsbas. Ingenting skrivs. Kostnadsspärren är rate limit, inte inloggning.
// Ändras endpointen till att skriva måste den flyttas bakom proxyAsTenant.

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyToBackend("/api/triage", { method: "POST", body });
}
