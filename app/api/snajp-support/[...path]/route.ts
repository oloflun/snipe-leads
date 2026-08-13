import { NextRequest } from "next/server";
import { proxyAsTenant } from "../_auth";

// Catch-all-proxy för inkorg/utkast/regler/kunskapsbas m.m. — specifika routes
// (chat, jobs, triage) matchar före denna. Endast /api/-prefixade backend-vägar
// tillåts. Kräver inloggning och kör mot den egna organisationens tenant.

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

export async function DELETE(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxyAsTenant(backendPath(path, request.nextUrl.search), { method: "DELETE" });
}
