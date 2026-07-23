import { NextRequest } from "next/server";
import { proxyToBackend } from "../../_lib";

export const runtime = "nodejs";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  return proxyToBackend(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "GET" });
}
