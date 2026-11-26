import { NextRequest } from "next/server";
import { requireSnajpTenant, type SnajpTenant } from "@/lib/snajp/tenant";
import { tenantfel, vidarebefordraBilaga } from "../../../../_binar";

/** Bilagans innehåll, som fil: backendens `Content-Disposition: attachment` följer med. */

export const runtime = "nodejs";
export const maxDuration = 60;

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  let tenant: SnajpTenant;
  try {
    tenant = await requireSnajpTenant();
  } catch (orsak) {
    return tenantfel(orsak);
  }
  const { id } = await params;
  return vidarebefordraBilaga(request, tenant, `/api/crm/v1/attachments/${encodeURIComponent(id)}/content`, "GET");
}
