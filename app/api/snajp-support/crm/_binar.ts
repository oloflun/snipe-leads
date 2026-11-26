import { NextRequest, NextResponse } from "next/server";
import { LASROLL, LASROLL_FEL } from "@/lib/auth/lasroll";
import { SnajpTenantError, svarForTenantfel, type SnajpTenant } from "@/lib/snajp/tenant";
import { backendBas } from "../_lib";

/**
 * Binärsäker vidarebefordran för CRM:ets bilagor. Den allmänna proxyn
 * (`../[...path]/route.ts`) läser kroppen som text och svarar som JSON, vilket
 * förstör både en uppladdad fil och en nedladdad. Samma grindar gäller här:
 * inloggning (routen anropar `requireSnajpTenant` själv, så att INV-SEC-010 ser
 * grinden i routens egen fil), läsrollen skriver ingenting, och den som tittar
 * som kund skriver ingenting i CRM:et (se `../_auth.ts`).
 *
 * Felen har CRM-API:ts form (`detail.code`, `message`, `meddelande`), så att
 * gränssnittet visar dem som vilket annat fel som helst.
 */

/** Backendens gräns är 10 MB per fil. Marginalen är multipartens egna rader. */
const MAX_KROPP = 11 * 1024 * 1024;

const fel = (status: number, code: string, message: string, meddelande: string) =>
  NextResponse.json({ detail: { code, message, meddelande } }, { status, headers: { "Cache-Control": "private, no-store", Vary: "Cookie" } });

/** Svaret när sessionen saknas eller arbetsytan inte är kopplad. Andra fel kastas vidare. */
export function tenantfel(orsak: unknown): Response {
  if (orsak instanceof SnajpTenantError) return NextResponse.json(svarForTenantfel(orsak), { status: orsak.status });
  throw orsak;
}

export async function vidarebefordraBilaga(request: NextRequest, tenant: SnajpTenant, backendVag: string, metod: "GET" | "POST"): Promise<Response> {
  let kropp: ArrayBuffer | undefined;
  if (metod === "POST") {
    if (tenant.roll === LASROLL) return NextResponse.json({ error: LASROLL_FEL, kod: "lasroll" }, { status: 403 });
    if (tenant.impersonerar) {
      return fel(403, "impersonation_read_only", "You are viewing as the customer. Nothing is written to the CRM in that mode.", "Du tittar som kunden. I det läget skrivs ingenting till CRM:et.");
    }
    // Längden prövas innan kroppen läses, så att en för stor fil aldrig hamnar i minnet här.
    const langd = Number(request.headers.get("content-length") ?? "0");
    if (langd > MAX_KROPP) return fel(413, "file_too_large", "The file is larger than 10 MB.", "Filen är större än 10 MB.");
    kropp = await request.arrayBuffer();
    if (kropp.byteLength > MAX_KROPP) return fel(413, "file_too_large", "The file is larger than 10 MB.", "Filen är större än 10 MB.");
  }

  const typ = request.headers.get("content-type");
  const idempotens = request.headers.get("idempotency-key");
  let svar: Response;
  try {
    svar = await fetch(`${backendBas()}${backendVag}`, {
      method: metod,
      headers: {
        "X-API-Key": tenant.apiKey,
        "X-Snajp-User": tenant.userId,
        ...(tenant.isDemo ? { "X-Snajp-Demo": "true" } : {}),
        ...(metod === "POST" && typ ? { "Content-Type": typ } : {}),
        ...(idempotens ? { "Idempotency-Key": idempotens } : {})
      },
      body: kropp,
      cache: "no-store",
      signal: AbortSignal.timeout(50_000)
    });
  } catch {
    return fel(503, "backend_unavailable", "The CRM did not answer. Try again in a moment.", "CRM:et svarade inte. Försök igen om en stund.");
  }

  const huvud: Record<string, string> = {
    "Content-Type": svar.headers.get("content-type") ?? "application/octet-stream",
    // En bilaga är kundens fil: aldrig mellanlagrad, aldrig tolkad som något annat än sin typ.
    "Cache-Control": "private, no-store",
    Vary: "Cookie",
    "X-Content-Type-Options": "nosniff"
  };
  const disposition = svar.headers.get("content-disposition");
  if (disposition) huvud["Content-Disposition"] = disposition;
  return new NextResponse(await svar.arrayBuffer(), { status: svar.status, headers: huvud });
}
