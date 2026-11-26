import { NextRequest } from "next/server";
import {
  arUuid,
  ejInloggadSvar,
  hittadesInteSvar,
  hjalpIdentitet,
  ogiltigtSvar,
  svarkropp,
  tillHjalpen,
  tolka
} from "@/lib/snajp/hjalp";
import { getWorkspaceContext } from "@/lib/workspace";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Kundens svar när Snajp behöver mer (status behover_mer). Rapportören sätts
 * ur sessionen, och backenden svarar bara för rapportörens eget ärende.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const { id } = await params;
  if (!arUuid(id)) return hittadesInteSvar();
  const identitet = await hjalpIdentitet(context);
  const kropp = svarkropp(tolka(await request.text()), identitet);
  if (!kropp) return ogiltigtSvar();
  return tillHjalpen(
    process.env.SNAJP_KEY_SNAJP_HJALP,
    `/api/plattformsarenden/${id}/svar`,
    { method: "POST", body: JSON.stringify(kropp) },
    identitet.userId
  );
}
