import { NextRequest } from "next/server";
import { proxyToBackend } from "../_lib";

// Catch-all-proxy för inkorg/utkast/regler m.m. — specifika routes (chat, jobs,
// triage) matchar före denna. Endast /api/-prefixade backend-vägar tillåts.

export const runtime = "nodejs";

function backendPath(path: string[], search: string): string {
  return `/api/${path.map(encodeURIComponent).join("/")}${search}`;
}

type Params = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxyToBackend(backendPath(path, request.nextUrl.search), { method: "GET" });
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxyToBackend(backendPath(path, request.nextUrl.search), {
    method: "POST",
    body: body || undefined
  });
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { path } = await params;
  const body = await request.text();
  return proxyToBackend(backendPath(path, request.nextUrl.search), {
    method: "PUT",
    body: body || undefined
  });
}
