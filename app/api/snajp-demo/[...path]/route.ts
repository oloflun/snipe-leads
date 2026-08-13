import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend, SNAJP_DEMO_API_KEY } from "@/app/api/snajp-support/_lib";

// Publik proxy för marknadsföringsdemon på /demo/snajp.
//
// Hårdlåst till demo-tenanten (Nordpuls Medical) via demo-nyckeln. Ingen
// inloggning krävs — därför är den här vägen den enda som får nås utan session,
// och den får bara röra demons egna testmail.
//
// Allowlisten nedan är säkerhetsgränsen: självbetjäningsvägarna (/keys, /tenant,
// /usage) är avsiktligt UTELÄMNADE. Utan den hade en utloggad besökare kunnat
// utfärda API-nycklar åt demo-tenanten eller skriva om dess systemprompt.

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

const ALLOWED_PREFIXES = [
  "health",
  "categories",
  "chat",
  "jobs",
  "triage",
  "kb",
  "inbox",
  "drafts",
  "rules"
];

function isAllowed(path: string[]): boolean {
  return path.length > 0 && ALLOWED_PREFIXES.includes(path[0]);
}

function backendPath(path: string[], search: string): string {
  return `/api/${path.map(encodeURIComponent).join("/")}${search}`;
}

function forbidden() {
  return NextResponse.json(
    { error: "Den här vägen är inte tillgänglig i demon. Logga in för din egen arbetsyta." },
    { status: 403 }
  );
}

type Params = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  if (!isAllowed(path)) return forbidden();
  return proxyToBackend(
    backendPath(path, request.nextUrl.search),
    { method: "GET" },
    SNAJP_DEMO_API_KEY
  );
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  if (!isAllowed(path)) return forbidden();
  const body = await request.text();
  return proxyToBackend(
    backendPath(path, request.nextUrl.search),
    { method: "POST", body: body || undefined },
    SNAJP_DEMO_API_KEY
  );
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { path } = await params;
  if (!isAllowed(path)) return forbidden();
  const body = await request.text();
  return proxyToBackend(
    backendPath(path, request.nextUrl.search),
    { method: "PUT", body: body || undefined },
    SNAJP_DEMO_API_KEY
  );
}
