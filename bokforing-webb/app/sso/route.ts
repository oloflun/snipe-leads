import { NextResponse, type NextRequest } from "next/server";
import {
  KUND_KAKA,
  dekrypteraKundsession,
  krypteraKundsession,
  tillatnaBackends,
  type Kundsession
} from "@/lib/kundsession";
import { basUrl } from "@/lib/session";

/**
 * Löser in Snajp-webbens biljett mot en kundsession — se lib/kundsession.ts
 * för hela kedjan. Biljetten är engångsartad i praktiken (60 s livstid);
 * kakan den byts mot bär en dags arbete.
 *
 * Varje fel landar på /logga-in?fel=sso med samma yttre beteende — vilken
 * kontroll som fällde är ingenting en URL-fifflare ska kunna mäta sig till.
 */

export const runtime = "nodejs";

const BILJETT_MAX_MS = 60_000;

type Biljett = {
  k: string; // tenantens API-nyckel
  b: string; // backend-URL
  s: string; // slug
  n: string; // arbetsytans namn
  exp: number; // epoch-ms
};

export async function GET(request: NextRequest) {
  const bas = basUrl(request);
  const hemlighet = process.env.BOKFORING_SSO_SECRET;
  const till = (svar: string) =>
    NextResponse.redirect(new URL(svar, bas), 303);

  if (!hemlighet) return till("/logga-in?fel=sso");

  const rå = request.nextUrl.searchParams.get("b") ?? "";
  const biljett = await dekrypteraKundsession<Biljett>(rå, hemlighet);
  const backend = (biljett?.b ?? "").replace(/\/$/, "");
  const giltig =
    biljett &&
    typeof biljett.k === "string" &&
    biljett.k.length > 0 &&
    typeof biljett.exp === "number" &&
    Date.now() < biljett.exp &&
    Date.now() > biljett.exp - BILJETT_MAX_MS * 2 &&
    tillatnaBackends().includes(backend);

  if (!giltig || !biljett) return till("/logga-in?fel=sso");

  const session: Kundsession = {
    apiKey: biljett.k,
    backendUrl: backend,
    slug: String(biljett.s ?? ""),
    namn: String(biljett.n ?? biljett.s ?? ""),
    utfardad: Date.now()
  };

  const svar = till("/");
  svar.cookies.set(KUND_KAKA, await krypteraKundsession(session, hemlighet), {
    httpOnly: true,
    secure: bas.startsWith("https:"),
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 12
  });
  return svar;
}
