import { NextRequest } from "next/server";
import {
  arUuid,
  ejInloggadSvar,
  hittadesInteSvar,
  hjalpIdentitet,
  ogiltigtSvar,
  tillHjalpen,
  tolka,
  utslagskropp
} from "@/lib/snajp/hjalp";
import { getWorkspaceContext } from "@/lib/workspace";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Kundens svar på "Fungerade det?" (status redo_att_testa). Ja är information,
 * aldrig ett godkännande som släpper något (planen del 8). Rapportören sätts
 * ur sessionen.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const { id } = await params;
  if (!arUuid(id)) return hittadesInteSvar();
  const identitet = await hjalpIdentitet(context);
  const kropp = utslagskropp(tolka(await request.text()), identitet);
  if (!kropp) return ogiltigtSvar();
  return tillHjalpen(
    process.env.SNAJP_KEY_SNAJP_HJALP,
    `/api/plattformsarenden/${id}/utslag`,
    { method: "POST", body: JSON.stringify(kropp) },
    identitet.userId
  );
}
