import { NextResponse, type NextRequest } from "next/server";

/**
 * Lösenordsväggen för utvecklingsdeployen.
 *
 * Sajten har inga konton ännu, och dess Railway-domän är annars öppen för
 * hela internet — med en fungerande API-nyckel bakom proxyn hade vem som
 * helst kunnat ladda upp underlag och driva LLM-kostnad. Samma skäl som gör
 * att dev-webben kräver inloggning.
 *
 * HTTP Basic Auth, EN hemlighet, styrd av miljön: är `BOKFORING_LOSEN` inte
 * satt (lokal utveckling) är väggen borta. Användarnamnet ignoreras —
 * webbläsare kräver att fältet finns, men det bär ingen information här.
 *
 * Väggen är ett driftskydd för en icke lanserad yta, inte en produktlogin.
 * Den dagen sajten får riktiga konton ersätts den här filen av riktig auth.
 */

export function proxy(request: NextRequest) {
  const losen = process.env.BOKFORING_LOSEN;
  if (!losen) return NextResponse.next();

  const header = request.headers.get("authorization") ?? "";
  if (header.startsWith("Basic ")) {
    try {
      const [, angivet] = atob(header.slice(6)).split(":");
      if (angivet === losen) return NextResponse.next();
    } catch {
      // Trasig base64 är samma sak som fel lösenord.
    }
  }

  return new NextResponse("Snajp Bokföring är inte öppen ännu. Ange lösenordet.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Snajp Bokföring", charset="UTF-8"',
      "Content-Type": "text/plain; charset=utf-8"
    }
  });
}

export const config = {
  // Allt utom Nexts egna statiska filer — även /api/bk skyddas.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"]
};
