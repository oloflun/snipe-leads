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

// Demon körs av oinloggade besökare, så inget destruktivt får släppas igenom:
// en anonym besökare ska inte kunna radera demo-tenantens kunskapsbas. Utan
// artiklar tvingar grundningsregeln eskalering av varje fråga, och demon slutar
// visa något.
//
// DELETE och PATCH saknar handler i den här filen och ger redan 405. Kontrollen
// finns ändå kvar som spärr: lägger någon till en DELETE-export i framtiden ska
// hålet inte öppnas tyst.
const DESTRUCTIVE = new Set(["DELETE", "PATCH"]);

function isAllowed(path: string[], method: string): boolean {
  if (path.length === 0 || !ALLOWED_PREFIXES.includes(path[0])) {
    return false;
  }
  if (DESTRUCTIVE.has(method)) {
    return false;
  }
  // PUT mot en enskild KB-artikel skriver om demons innehåll. PUT /rules är
  // däremot en del av demon (regelpanelen) och lämnas öppen.
  if (method === "PUT" && path[0] === "kb") {
    return false;
  }
  return true;
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

/**
 * Godkännande i demon får ALDRIG skicka riktig e-post.
 *
 * `POST /api/drafts/{id}/approve` skickar annars ett skarpt mail till mailets
 * avsändaradress, och mock-scenarierna använder verklighetstrogna adresser
 * (hr@storaforetaget.se och liknande). Eftersom demon är oinloggad blev den
 * därmed en öppen väg för vem som helst att trigga utgående mail från det
 * kopplade kontot.
 *
 * `send: false` finns redan i backendens API och ger exakt samma synliga flöde
 * — utkastet markeras godkänt — men ingenting lämnar systemet.
 */
function withoutSending(path: string[], body: string): string {
  const isApprove = path[0] === "drafts" && path[path.length - 1] === "approve";
  if (!isApprove) {
    return body;
  }
  let payload: Record<string, unknown> = {};
  if (body) {
    try {
      const parsed = JSON.parse(body);
      if (parsed && typeof parsed === "object") {
        payload = parsed as Record<string, unknown>;
      }
    } catch {
      // Trasig JSON får backenden avvisa — men aldrig med utskick påslaget.
    }
  }
  return JSON.stringify({ ...payload, send: false });
}

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  if (!isAllowed(path, "GET")) return forbidden();
  return proxyToBackend(
    backendPath(path, request.nextUrl.search),
    { method: "GET" },
    SNAJP_DEMO_API_KEY
  );
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  if (!isAllowed(path, "POST")) return forbidden();
  const body = withoutSending(path, await request.text());
  return proxyToBackend(
    backendPath(path, request.nextUrl.search),
    { method: "POST", body },
    SNAJP_DEMO_API_KEY
  );
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { path } = await params;
  if (!isAllowed(path, "PUT")) return forbidden();
  const body = await request.text();
  return proxyToBackend(
    backendPath(path, request.nextUrl.search),
    { method: "PUT", body: body || undefined },
    SNAJP_DEMO_API_KEY
  );
}
