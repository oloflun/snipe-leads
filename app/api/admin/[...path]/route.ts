import { NextRequest, NextResponse } from "next/server";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { komprimera } from "@/lib/http/komprimera";

/**
 * Adminproxyn. Två oberoende grindar, och båda behövs.
 *
 * 1. `getPlatformAdmin()` — sessionen måste tillhöra någon som står i
 *    `platform_admins`. Server-side, aldrig ett klientvillkor.
 * 2. Master-nyckeln — backendens `/api/admin/*` ligger bakom
 *    `require_master_key`. Nyckeln finns bara här på servern.
 *
 * Att bara ha (2) hade betytt att vem som helst som når den här routen får
 * master-behörighet. Att bara ha (1) hade betytt att backenden litar på att
 * Next gjorde rätt. Gränsen ska hålla även om ett av lagren har fel.
 *
 * Svarar 404, inte 403, för den som inte är admin: ett 403 bekräftar att
 * ytan finns och vem den är till för.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

const NOT_FOUND = NextResponse.json({ error: "Hittades inte." }, { status: 404 });

type Params = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, path: string[], method: "GET" | "POST", body?: string) {
  if (!(await getPlatformAdmin())) {
    return NOT_FOUND;
  }

  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    // 503 och inte 500: tjänsten är riktigt konfigurerad men saknar en nyckel
    // i just den här miljön. Meddelandet namnger variabeln så felet går att
    // åtgärda utan att läsa koden.
    return NextResponse.json(
      {
        error:
          "SNAJP_MASTER_API_KEY är inte satt i den här miljön. Adminvyn kan inte nå backenden förrän den finns.",
        configured: false
      },
      { status: 503 }
    );
  }

  const backendPath = `/api/admin/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const svar = await proxyWithApiKey(backendPath, { method, body }, masterKey);
  // Proxyn bygger ett eget JSON-svar och tar bara med ett par av backendens
  // huvuden. Adminsvaren bär kunddata (felrapportens bild bland annat):
  // `private, no-store` sätter proxyWithApiKey, och typen ska aldrig gissas om.
  svar.headers.set("X-Content-Type-Options", "nosniff");
  return komprimera(request, svar);
}

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return forward(request, path, "GET");
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Den ENDA skrivningen genom adminproxyn: lägesbytet på en felrapport ur
 * Hjälprutan (docs/PLAN-HJALPRUTAN-2026-11-25.md). Felrapporterna är Snajps
 * egna ärenden, inte en kunds data, och ett läge måste sättas av en människa
 * hos Snajp. Sökvägen är en vitlista: allt annat svarar 404.
 */
export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const arLagesbyte =
    path.length === 3 && path[0] === "plattformsarenden" && UUID.test(path[1]) && path[2] === "status";
  if (!arLagesbyte) {
    return NOT_FOUND;
  }
  return forward(request, path, "POST", await request.text());
}

// Ingen PUT/PATCH/DELETE, och ingen annan POST än den ovan. Adminvyn LÄSER
// kunddata. En adminvy som kan ändra kunddata gör det förr eller senare av
// misstag, och den enda ändring som faktiskt behövs (autonomi, ICP) gör kunden
// själv i sin egen vy.
