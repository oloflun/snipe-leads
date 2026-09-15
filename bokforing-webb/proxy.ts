import { NextResponse, type NextRequest } from "next/server";
import {
  KUND_KAKA,
  KUNDSESSION_MAX_MS,
  dekrypteraKundsession,
  type Kundsession
} from "@/lib/kundsession";
import { SESSION_KAKA, sessionsvarde } from "@/lib/session";

/**
 * Inloggningsväggen för utvecklingsdeployen.
 *
 * Ersatte Basic Auth-varianten 2026-09-15: webbläsarens nativa ruta gav
 * ingen feedback vid fel lösenord — den bara studsade tillbaka — så väggen
 * är nu en riktig sida (/logga-in) med sessionskaka. Samma skyddsroll:
 * sajten har inga konton, och utan vägg hade Railway-domänen exponerat
 * uppladdning och LLM-kostnad mot hela internet.
 *
 * Styrd av miljön: är `BOKFORING_LOSEN` inte satt (lokal utveckling) är
 * väggen borta. API-anrop utan session får 401 med JSON i stället för en
 * redirect — vyernas felhantering visar en mening, inte en HTML-sida.
 *
 * Den dagen sajten får riktiga konton ersätts det här av riktig auth.
 */

export async function proxy(request: NextRequest) {
  const losen = process.env.BOKFORING_LOSEN;
  if (!losen) return NextResponse.next();

  const { pathname } = request.nextUrl;
  if (pathname === "/logga-in" || pathname === "/api/logga-in" || pathname === "/sso") {
    return NextResponse.next();
  }

  // Två giltiga sessionsformer: förhandslösnets kaka, eller kundsessionen
  // från Snajp-webbens SSO (lib/kundsession.ts). Kundens är den vanliga —
  // lösnet är dörren för oss själva och för direktbesök.
  const kaka = request.cookies.get(SESSION_KAKA)?.value;
  if (kaka && kaka === (await sessionsvarde(losen))) {
    return NextResponse.next();
  }

  const kundKaka = request.cookies.get(KUND_KAKA)?.value;
  const ssoHemlighet = process.env.BOKFORING_SSO_SECRET;
  if (kundKaka && ssoHemlighet) {
    const kund = await dekrypteraKundsession<Kundsession>(kundKaka, ssoHemlighet);
    if (kund?.apiKey && Date.now() - kund.utfardad < KUNDSESSION_MAX_MS) {
      return NextResponse.next();
    }
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json(
      { error: "Du är utloggad. Ladda om sidan och logga in igen." },
      { status: 401 }
    );
  }

  const till = new URL("/logga-in", request.url);
  if (pathname !== "/") till.searchParams.set("nasta", pathname);
  return NextResponse.redirect(till);
}

export const config = {
  // Allt utom Nexts egna statiska filer. Loggan och symbolerna i /public
  // släpps igenom: inloggningssidan bär dem, och en vägg som blockerar sin
  // egen sidas logga visar en trasig sida.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|snajp-logo-|snajp-symbol-).*)"]
};
