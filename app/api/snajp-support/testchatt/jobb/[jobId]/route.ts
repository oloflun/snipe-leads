import { NextRequest } from "next/server";
import { proxyAsTenant } from "../../../_auth";

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

/**
 * Pollning för Testchatt-fliken (Fas 5, §6). Systerroute till
 * `../route.ts` — se den filens docstring för varför en ny sökväg krävs i
 * stället för `../../jobs/[jobId]/route.ts`, som är den PUBLIKA, anonyma
 * pollningen (INV-SEC-010) och löser tenanten ur en klient-skickad slug.
 *
 * Här kommer tenanten ur sessionen (`proxyAsTenant`), så jobbet slås upp
 * under samma nyckel som skapade det — ingen `?tenant=`-parameter behövs
 * eller accepteras.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  return proxyAsTenant(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "GET" });
}
