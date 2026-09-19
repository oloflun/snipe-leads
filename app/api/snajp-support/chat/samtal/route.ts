import { NextRequest } from "next/server";
import { proxyToBackend } from "../../_lib";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Chattfönstrets hämtning av sitt eget samtal (bd snipe-1fl): medarbetarens
 * svar efter en överlämning, och hela samtalet när en besökare öppnar sin
 * sessionslänk igen.
 *
 * ANONYM av samma skäl som `../route.ts` (INV-SEC-010): kundens kunder
 * loggar inte in. Skyddet är backendens — den läser bara tillbaka
 * sessionsidentiteter (`<uuid>@session.snajp.se`, en slumpad hemlighet som
 * bara besökarens flik känner till), aldrig en riktig e-postadress som går
 * att gissa. POST och inte GET: identiteten ska inte hamna i en URL.
 */
export async function POST(request: NextRequest) {
  const body = await request.text();

  let tenant: string | null = null;
  try {
    tenant = (JSON.parse(body) as { tenant?: string }).tenant ?? null;
  } catch {
    // Ogiltig JSON får backenden avvisa med sitt eget felmeddelande.
  }

  return proxyToBackend("/api/chat/samtal", { method: "POST", body }, tenant);
}
