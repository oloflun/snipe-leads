import { NextRequest } from "next/server";
import { proxyAsTenant } from "../../../_auth";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Inloggad pollning av ett leads-jobb.
 *
 * Får inte gå via `jobs/[jobId]` — den routen är anonym med flit (publik
 * chatt) och slår upp jobbet under demonyckeln om ingen `?tenant=` skickas.
 * Här kommer tenanten ur sessionen, samma mönster som testchattens
 * `testchatt/jobb/[jobId]`.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  return proxyAsTenant(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "GET" });
}
