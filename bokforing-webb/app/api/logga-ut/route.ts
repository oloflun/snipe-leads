import { NextResponse, type NextRequest } from "next/server";
import { KUND_KAKA } from "@/lib/kundsession";
import { SESSION_KAKA, basUrl } from "@/lib/session";

/** Rensar båda sessionsformerna (kundens SSO-kaka och förhandslösnets) och
 *  landar på inloggningssidan. POST från en vanlig form — inget JS-krav. */

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const svar = NextResponse.redirect(new URL("/logga-in", basUrl(request)), 303);
  for (const kaka of [SESSION_KAKA, KUND_KAKA]) {
    svar.cookies.set(kaka, "", { path: "/", maxAge: 0 });
  }
  return svar;
}
