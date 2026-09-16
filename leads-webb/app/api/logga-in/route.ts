import { NextResponse, type NextRequest } from "next/server";
import { SESSION_KAKA, saneraNasta, sessionsvarde } from "@/lib/session";

/**
 * Tar emot inloggningsformuläret. Ren HTML-POST utan JavaScript-krav:
 * lyckas → sessionskaka + vidare till sidan man var på väg till;
 * misslyckas → tillbaka till /logga-in med ett fel som sidan visar.
 *
 * Uppgifterna jämförs mot miljön (AGENTSAJT_EPOST/AGENTSAJT_LOSEN) på
 * servern — ingenting av dem skickas till webbläsaren.
 */

export const runtime = "nodejs";

/**
 * Publika basadressen — ur x-forwarded-headrarna, INTE request.url.
 *
 * Bakom Railways proxy är request.url i en route handler den interna
 * adressen (http://localhost:8080), och en redirect byggd på den skickade
 * webbläsaren till localhost. Uppmätt live 2026-09-15 vid första
 * fellösenordet. Middleware-redirecten drabbas inte — det är just
 * handler-vägen som ser den interna värden.
 */
function basUrl(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "";
  return `${proto}://${host}`;
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const epost = String(form.get("epost") ?? "").trim().toLowerCase();
  const losen = String(form.get("losen") ?? "");
  const nasta = saneraNasta(String(form.get("nasta") ?? ""));
  const bas = basUrl(request);

  const rattLosen = process.env.AGENTSAJT_LOSEN;
  const rattEpost = (process.env.AGENTSAJT_EPOST ?? "Snajpsupport@gmail.com").trim().toLowerCase();

  // Utan konfigurerad vägg finns inget att logga in i — skicka bara vidare.
  if (!rattLosen) {
    return NextResponse.redirect(new URL(nasta, bas), 303);
  }

  if (epost !== rattEpost || losen !== rattLosen) {
    const tillbaka = new URL("/logga-in", bas);
    tillbaka.searchParams.set("fel", "1");
    if (nasta !== "/") tillbaka.searchParams.set("nasta", nasta);
    return NextResponse.redirect(tillbaka, 303);
  }

  const svar = NextResponse.redirect(new URL(nasta, bas), 303);
  svar.cookies.set(SESSION_KAKA, await sessionsvarde(rattLosen), {
    httpOnly: true,
    secure: bas.startsWith("https:"),
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30
  });
  return svar;
}
