import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { offlineResponse, SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";

// Proxy för PILOT-arbetsytan: riktig kundinkorg, riktiga utskick.
//
// Två skillnader mot den publika /api/snajp-support-proxyn:
//  1. Varje anrop kräver en inloggad Supabase-session — annars 401. Utan detta
//     hade vem som helst kunnat läsa kundmail via den publika sidan.
//  2. Pilotens egen API-nyckel används, så backendens tenant-separation ger
//     åtkomst till pilotens data i stället för demons.

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

const PILOT_API_KEY = process.env.SNAJP_PILOT_API_KEY ?? "";

function backendPath(path: string[], search: string): string {
  return `/api/${path.map(encodeURIComponent).join("/")}${search}`;
}

async function requireSession() {
  const supabase = await createClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();
  return user;
}

async function proxy(request: NextRequest, path: string[], method: string, body?: string) {
  const user = await requireSession();
  if (!user) {
    return NextResponse.json(
      { error: "Du måste vara inloggad för att se kundtjänstärenden." },
      { status: 401 }
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
