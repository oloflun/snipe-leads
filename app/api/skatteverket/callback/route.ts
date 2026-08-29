import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import {
  SKV_RETUR_COOKIE,
  SKV_STATE_COOKIE,
  SKV_TOKEN_COOKIE,
  SKV_TOKEN_LIVSLANGD_SEKUNDER,
  sakerReturvag,
  vaxlaKodMotToken
} from "@/lib/skatteverket/oauth";

/**
 * Steg 2: Skatteverket skickar tillbaka användaren hit med en kod.
 *
 * ## Varför tokenen hamnar i en httpOnly-kaka och inte i databasen
 *
 * Den lever en timme, gäller EN inloggad person, och ger läsning av ett
 * identifierat bolags beskattningsuppgifter. En databaskolumn hade gjort den
 * till något som överlever sessionen, syns i en dump och måste städas — för ett
 * värde som ändå är dött om sextio minuter. Kakan är httpOnly och secure,
 * försvinner med sessionen, och når aldrig klientens JavaScript.
 *
 * Kakans livslängd sätts till tokenens egen. En kaka som överlever sitt
 * innehåll gör att gränssnittet visar "inloggad" medan varje uppslag svarar
 * 401 — ett läge som ser ut som ett API-fel och felsöks åt fel håll.
 *
 * ## Refresh token sparas INTE
 *
 * Skatteverket utfärdar en (65 minuters giltighet för e-legitimationsflödet),
 * men att lagra den vore att förlänga en fullmakt användaren gav för ett
 * uppslag. Går tokenen ut legitimerar sig kunden igen — det är en knapptryckning
 * och ett BankID, och det är rätt kostnad för att slippa lagra en förnybar
 * åtkomst till någons beskattningsuppgifter.
 */
export const runtime = "nodejs";

function tillbaka(retur: string, fel?: string): NextResponse {
  const mal = new URL(retur, "http://placeholder.invalid");
  if (fel) mal.searchParams.set("skv_fel", fel);
  // Bara path+query går vidare — `mal` byggdes mot en påhittad bas just för
  // att kunna parsa en relativ sökväg, och basen får aldrig följa med ut.
  return NextResponse.redirect(new URL(`${mal.pathname}${mal.search}`, process.env.NEXTAUTH_URL ?? "http://localhost:3000"));
}

export async function GET(request: NextRequest) {
  const kakor = await cookies();
  const retur = sakerReturvag(kakor.get(SKV_RETUR_COOKIE)?.value);

  try {
    await requireSnajpTenant();
  } catch (error) {
    if (error instanceof SnajpTenantError) return tillbaka(retur, "ej_inloggad");
    throw error;
  }

  const params = request.nextUrl.searchParams;

  // Skatteverket rapporterar avbrott och nekat samtycke som `error`, inte som
  // ett uteblivet svar. Ett avbrutet BankID är inte ett fel hos oss.
  const skvFel = params.get("error");
  if (skvFel) {
    return tillbaka(retur, skvFel === "access_denied" ? "avbruten" : "nekad");
  }

  const state = params.get("state");
  const forvantat = kakor.get(SKV_STATE_COOKIE)?.value;

  // CSRF-spärren. Saknas kakan har flödet inte startat här — och en kod som
  // inte hör till den här sessionen får aldrig växlas in i den.
  if (!state || !forvantat || state !== forvantat) {
    return tillbaka(retur, "state_stamde_inte");
  }
  kakor.delete(SKV_STATE_COOKIE);
  kakor.delete(SKV_RETUR_COOKIE);

  const code = params.get("code");
  if (!code) return tillbaka(retur, "ingen_kod");

  let token: string;
  let livslangd = SKV_TOKEN_LIVSLANGD_SEKUNDER;
  try {
    const svar = await vaxlaKodMotToken(code);
    token = svar.access_token;
    // Skatteverkets egen expires_in vinner över vår konstant när den finns —
    // konstanten är dokumentationens värde, svaret är sanningen.
    if (typeof svar.expires_in === "number" && svar.expires_in > 0) {
      livslangd = svar.expires_in;
    }
  } catch (error) {
    // Meddelandet kan innehålla Skatteverkets svarskropp. Det loggas för oss
    // och går ALDRIG ut i en query-parameter till webbläsaren.
    console.error("Skatteverket: kodväxlingen misslyckades", error);
    return tillbaka(retur, "kodvaxling_misslyckades");
  }

  kakor.set(SKV_TOKEN_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: livslangd
  });

  return tillbaka(retur);
}
