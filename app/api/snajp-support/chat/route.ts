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
const SESSIONSDOMAN = "@session.snajp.se";

/** Saknad identitet är tillåten (en besökare utan session får ingen historik). */
function arSessionsidentitet(varde: unknown): boolean {
  if (varde === undefined || varde === null) return true;
  return typeof varde === "string" && varde.trim().toLowerCase().endsWith(SESSIONSDOMAN);
}

export async function POST(request: NextRequest) {
  const body = await request.text();

  // Tenanten kommer från klientens payload och avgör vilken API-nyckel som
  // används. Den är inte känslig i sig — nyckeln finns bara på servern, så en
  // förfalskad slug ger på sin höjd fel kunds publika kunskapsbas, aldrig
  // åtkomst till någons data.
  let tenant: string | null = null;
  let payload = body;
  try {
    const parsed = JSON.parse(body) as {
      tenant?: string;
      arbetsyta?: unknown;
      customer_email?: unknown;
    };
    tenant = parsed.tenant ?? null;
    // Besökaren är anonym och får bara vara sin egen chattsession
    // (`<uuid>@session.snajp.se`, se SupportChat.tsx). Backenden laddar
    // kundens tidigare samtal och sparade fakta in i agentens kontext utifrån
    // adressen — med en riktig mejladress härifrån hade vem som helst kunnat
    // fråga agenten om en annan kunds ärenden (Fas 0-fyndet H1, 2026-11-09).
    // Samma regel som backendens läsväg /api/chat/samtal redan har. En kund
    // som integrerar /api/chat med riktiga adresser gör det med sin egen
    // nyckel mot backenden, inte genom den här anonyma vägen.
    if (!arSessionsidentitet(parsed.customer_email)) {
      return Response.json(
        {
          error:
            "Chatten kunde inte starta. Ladda om sidan och försök igen. / The chat could not start. Reload the page and try again.",
        },
        { status: 422 },
      );
    }
    // `arbetsyta` ger agenten tenantens interna nyckeltal och får BARA
    // sättas av den autentiserade testchatt-routen. Här är vem som helst —
    // fältet strippas, oavsett värde (2026-10-05).
    if ("arbetsyta" in parsed) {
      delete (parsed as Record<string, unknown>).arbetsyta;
      payload = JSON.stringify(parsed);
    }
  } catch {
    // Ogiltig JSON får backenden avvisa med sitt eget felmeddelande.
  }

  return proxyToBackend("/api/chat", { method: "POST", body: payload }, tenant);
}
