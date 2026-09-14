import { NextRequest } from "next/server";
import { proxyAsTenant } from "../_auth";

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

/**
 * Testchatt-fliken (Fas 5, plan 2026-08-28 §6, bd snipe-0r9): SupportChat
 * mot den INLOGGADE tenanten, inte demo och inte en publik länk.
 *
 * En EGEN route i stället för att återanvända `../chat/route.ts` — den är
 * ANONYM med flit (INV-SEC-010): tenanten kommer där ur en slug klienten
 * skickar, upplöst mot `lib/tenants.ts`s statiska konfiguration. En riktig,
 * inloggad kund utan configfil (de allra flesta) skulle ha fått demo-
 * nyckeln där, alltså svar ur Nordlys Handels kunskapsbas — exakt den bugg
 * `lib/snajp/tenant.ts`s egen docstring beskriver. Den här routen går i
 * stället genom `proxyAsTenant`, som härleder tenanten ur SESSIONEN
 * (`requireSnajpTenant`), aldrig ur något klienten skickar.
 *
 * Katalogen `../chat/` och `../jobs/[jobId]/` kan därför inte återanvändas
 * för URL:en heller: Next.js router matchar den bokstavliga rutten
 * `/api/snajp-support/chat` mot den anonyma routen oavsett vad den här
 * filen hade gjort, så en NY sökväg är den enda vägen till en autentiserad
 * chatt-endpoint under samma proxy-familj.
 */
export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAsTenant("/api/chat", { method: "POST", body: body || undefined });
}
