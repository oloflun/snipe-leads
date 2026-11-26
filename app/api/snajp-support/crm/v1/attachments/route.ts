import { NextRequest } from "next/server";
import { komprimera } from "@/lib/http/komprimera";
import { proxyAsTenant } from "../../../_auth";
import { requireSnajpTenant, type SnajpTenant } from "@/lib/snajp/tenant";
import { tenantfel, vidarebefordraBilaga } from "../../_binar";

/**
 * CRM:ets bilagor. Listan (GET) är JSON och går den vanliga vägen.
 * Uppladdningen (POST) är `multipart/form-data` och går binärsäkert: den
 * allmänna proxyn hade läst filen som text.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

export async function GET(request: NextRequest) {
  return komprimera(request, await proxyAsTenant(`/api/crm/v1/attachments${request.nextUrl.search}`, { method: "GET" }));
}

export async function POST(request: NextRequest) {
  let tenant: SnajpTenant;
  try {
    tenant = await requireSnajpTenant();
  } catch (orsak) {
    return tenantfel(orsak);
  }
  return vidarebefordraBilaga(request, tenant, "/api/crm/v1/attachments", "POST");
}
