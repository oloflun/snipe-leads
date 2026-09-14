import { NextResponse } from "next/server";
import { hasDatabase, sql } from "@/lib/db";

export const dynamic = "force-dynamic";

/**
 * Hälsokontroll för web-tjänsten. Speglar backendens /health/ready.
 *
 * ANONYM MED FLIT (INV-SEC-010, ANON_ALLOWLIST). En hälsokontroll som kräver
 * inloggning kan inte användas av det som ska kontrollera hälsan — Railways
 * healthcheck skickar ingen cookie.
 *
 * Den är ÄRLIG av samma skäl som backendens: en kontroll som svarar 200 så
 * länge processen lever mäter bara att processen lever. Den här svarar 503 om
 * databasen inte går att nå, vilket är skillnaden mellan "startade" och
 * "fungerar". Backenden fick den distinktionen först efter att en container
 * startat grönt och fallit på det första riktiga anropet.
 *
 * Den läcker ingenting: inga tabellnamn, inga rader, ingen version.
 */
export async function GET() {
  if (!hasDatabase()) {
    return NextResponse.json({ status: "degraded", database: "unconfigured" }, { status: 503 });
  }
  try {
    await sql("select 1");
    return NextResponse.json({ status: "ok", database: "ok" });
  } catch {
    return NextResponse.json({ status: "degraded", database: "unreachable" }, { status: 503 });
  }
}
