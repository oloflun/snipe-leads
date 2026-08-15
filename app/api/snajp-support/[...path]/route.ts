import { NextRequest } from "next/server";
import { proxyAsTenant } from "../_auth";

// Catch-all-proxy för inkorg/utkast/regler/kunskapsbas/leads — specifika routes
// (chat, jobs, triage) matchar före denna.
//
// KRÄVER INLOGGNING, och tenanten kommer ur sessionen. Tidigare skickades ingen
// tenant alls härifrån, vilket gav två fel på samma rad: hela ytan var anonymt
// nåbar, och varje inloggad kunds data lästes ur demo-tenanten. Den kunde
// dessutom adressera POST /api/keys — räddat enbart av att den interna nyckeln
// råkade vara demonyckeln och inte master.

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

function backendPath(path: string[], search: string): string {
  return `/api/${path.map(encodeURIComponent).join("/")}${search}`;
}

type Params = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxyAsTenant(backendPath(path, request.nextUrl.search), { method: "GET" });
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxyAsTenant(backendPath(path, request.nextUrl.search), {
    method: "POST",
    body: body || undefined
  });
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxyAsTenant(backendPath(path, request.nextUrl.search), {
    method: "PUT",
    body: body || undefined
  });
}

// PATCH för delvisa uppdateringar (prospektets bedömning). Ingen DELETE här:
// ingen backend-endpoint tar DELETE, och en metod som proxas utan mottagare
// är bara en yta till att hålla stängd.
export async function PATCH(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxyAsTenant(backendPath(path, request.nextUrl.search), {
    method: "PATCH",
    body: body || undefined
  });
}
