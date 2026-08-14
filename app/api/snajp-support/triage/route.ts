import { NextRequest } from "next/server";
import { proxyToBackend } from "../_lib";

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyToBackend("/api/triage", { method: "POST", body });
}
