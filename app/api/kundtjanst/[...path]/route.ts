import { NextRequest, NextResponse } from "next/server";
import { getWorkspaceContext } from "@/lib/workspace";
import { isPilotWorkspace } from "@/lib/snajp/pilot";
import { offlineResponse, SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";

// Proxy för PILOT-arbetsytan: riktig kundinkorg, riktiga utskick.
//
// Tre skillnader mot /api/snajp-support-proxyn:
//  1. Kräver en inloggad Supabase-session.
//  2. Kräver att användarens ORGANISATION står på pilot-allowlisten. Tidigare
//     räckte det att vara inloggad över huvud taget — och eftersom vem som helst
//     kan registrera sig innebar det att varje ny kund kunde läsa pilotbolagets
//     riktiga kundmail, och till och med skicka svar från deras inkorg.
//  3. Pilotens egen API-nyckel används, så backendens tenant-separation ger
//     åtkomst till pilotens data i stället för demons.
//
// Allowlisten är medvetet fail-closed: är SNAJP_PILOT_WORKSPACE_IDS inte satt
// släpps INGEN in. Att öppna för alla när konfigurationen saknas är precis den
// bugg som fanns här.

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

const PILOT_API_KEY = process.env.SNAJP_PILOT_API_KEY ?? "";


function backendPath(path: string[], search: string): string {
  return `/api/${path.map(encodeURIComponent).join("/")}${search}`;
}

async function proxy(request: NextRequest, path: string[], method: string, body?: string) {
  const context = await getWorkspaceContext();
  if (!context) {
    return NextResponse.json(
      { error: "Du måste vara inloggad för att se kundtjänstärenden." },
      { status: 401 }
    );
  }
  if (!isPilotWorkspace(context.workspace.id)) {
    // 403 och inte 404: användaren ÄR inloggad och vet redan att vyn finns —
    // det som saknas är behörighet, och det ska sägas rakt ut.
    return NextResponse.json(
      {
        error:
          "Din organisation har inte åtkomst till pilot-arbetsytan. Den " +
          "innehåller ett annat bolags riktiga kundärenden."
      },
      { status: 403 }
    );
  }
  if (!PILOT_API_KEY) {
    return NextResponse.json(
      {
        error:
          "Pilot-arbetsytan är inte konfigurerad (SNAJP_PILOT_API_KEY saknas i miljövariablerna)."
      },
      { status: 503 }
    );
  }

  try {
    const response = await fetch(
      `${SNAJP_SUPPORT_URL}${backendPath(path, request.nextUrl.search)}`,
      {
        method,
        body,
        headers: { "Content-Type": "application/json", "X-API-Key": PILOT_API_KEY },
        cache: "no-store"
      }
    );
    return NextResponse.json(await response.json(), { status: response.status });
  } catch (cause) {
    return offlineResponse(cause);
  }
}

type Params = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxy(request, path, "GET");
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxy(request, path, "POST", body || undefined);
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxy(request, path, "PUT", body || undefined);
}
