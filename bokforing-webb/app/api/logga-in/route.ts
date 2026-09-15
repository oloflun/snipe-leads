import { NextResponse, type NextRequest } from "next/server";
import { SESSION_KAKA, saneraNasta, sessionsvarde } from "@/lib/session";

/**
 * Tar emot inloggningsformuläret. Ren HTML-POST utan JavaScript-krav:
 * lyckas → sessionskaka + vidare till sidan man var på väg till;
 * misslyckas → tillbaka till /logga-in med ett fel som sidan visar.
 *
 * Uppgifterna jämförs mot miljön (BOKFORING_EPOST/BOKFORING_LOSEN) på
 * servern — ingenting av dem skickas till webbläsaren.
 */

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const epost = String(form.get("epost") ?? "").trim().toLowerCase();
  const losen = String(form.get("losen") ?? "");
  const nasta = saneraNasta(String(form.get("nasta") ?? ""));

  const rattLosen = process.env.BOKFORING_LOSEN;
  const rattEpost = (process.env.BOKFORING_EPOST ?? "Snajpsupport@gmail.com").trim().toLowerCase();

  // Utan konfigurerad vägg finns inget att logga in i — skicka bara vidare.
  if (!rattLosen) {
    return NextResponse.redirect(new URL(nasta, request.url), 303);
  }

  if (epost !== rattEpost || losen !== rattLosen) {
    const tillbaka = new URL("/logga-in", request.url);
    tillbaka.searchParams.set("fel", "1");
    if (nasta !== "/") tillbaka.searchParams.set("nasta", nasta);
    return NextResponse.redirect(tillbaka, 303);
  }

  const svar = NextResponse.redirect(new URL(nasta, request.url), 303);
  svar.cookies.set(SESSION_KAKA, await sessionsvarde(rattLosen), {
    httpOnly: true,
    secure: request.nextUrl.protocol === "https:",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30
  });
  return svar;
}
