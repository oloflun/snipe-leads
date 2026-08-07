import { NextRequest } from "next/server";
import { proxyToBackend } from "../_lib";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.text();

  // Tenanten kommer från klientens payload och avgör vilken API-nyckel som
  // används. Den är inte känslig i sig — nyckeln finns bara på servern, så en
  // förfalskad slug ger på sin höjd fel kunds publika kunskapsbas, aldrig
  // åtkomst till någons data.
  let tenant: string | null = null;
  try {
    tenant = (JSON.parse(body) as { tenant?: string }).tenant ?? null;
  } catch {
    // Ogiltig JSON får backenden avvisa med sitt eget felmeddelande.
  }

  return proxyToBackend("/api/chat", { method: "POST", body }, tenant);
}
