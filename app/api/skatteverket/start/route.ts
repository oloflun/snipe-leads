import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import {
  SKV_RETUR_COOKIE,
  SKV_STATE_COOKIE,
  SKV_STATE_LIVSLANGD_SEKUNDER,
  SkatteverketKonfigFel,
  authorizeUrl,
  redirectUri,
  sakerReturvag
} from "@/lib/skatteverket/oauth";

/**
 * Steg 1 av BankID-inloggningen: skicka användaren till Skatteverket.
 *
 * KRÄVER INLOGGNING hos oss först. Skälet är inte formellt: uppslaget görs för
 * en tenant, och tokenen som kommer tillbaka kopplas till den sessionen. Utan
 * grinden hade vem som helst kunnat starta ett flöde vars resultat sedan
 * användes i någon annans agentkörning. Samma hållning som `_auth.ts` beskriver
 * för proxyn — grinden hör hemma i routen, inte i proxy.ts-matchern.
 */
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    await requireSnajpTenant();
  } catch (error) {
    if (error instanceof SnajpTenantError) {
      return NextResponse.json(
        { error: error.message, kod: error.kod },
        { status: error.status }
      );
    }
    throw error;
  }

  let url: string;
  const state = crypto.randomUUID();

  try {
    url = authorizeUrl({ state, redirectUri: redirectUri() });
  } catch (error) {
    if (error instanceof SkatteverketKonfigFel) {
      // 503 och inte 500: tjänsten är inte trasig, den är inte påslagen. Ett
      // gränssnitt ska kunna skilja de två utan att läsa svensk text.
      return NextResponse.json(
        { error: error.message, kod: "ej_konfigurerad" },
        { status: 503 }
      );
    }
    throw error;
  }

  const kakor = await cookies();
  const sakerKaka = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    // `lax` och inte `strict`: återkomsten från Skatteverket är en navigering
    // från en annan sajt, och `strict` hade utelämnat kakan just då — alltså
    // fällt varje inloggning på ett state som "saknas".
    sameSite: "lax" as const,
    path: "/",
    maxAge: SKV_STATE_LIVSLANGD_SEKUNDER
  };

  // State jämförs i callbacken och är hela CSRF-skyddet: utan det kan någon
  // annan mata in sin egen auktorisationskod i vår session.
  kakor.set(SKV_STATE_COOKIE, state, sakerKaka);
  kakor.set(
    SKV_RETUR_COOKIE,
    sakerReturvag(request.nextUrl.searchParams.get("retur")),
    sakerKaka
  );

  return NextResponse.redirect(url);
}
