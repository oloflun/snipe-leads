import { NextRequest } from "next/server";
import { proxyToBackend } from "../_lib";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyToBackend("/api/chat", { method: "POST", body });
}
