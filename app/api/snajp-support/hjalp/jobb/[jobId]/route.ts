import { NextRequest } from "next/server";
import {
  arJobbtoken,
  arUuid,
  ejInloggadSvar,
  hjalpIdentitet,
  jobbetSaknasSvar,
  lasJobb,
  tillHjalpen
} from "@/lib/snajp/hjalp";
import { getWorkspaceContext } from "@/lib/workspace";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Pollningen av ett hjälpjobb som ../route.ts startade. Jobbet skapades under
 * hjälpens nyckel och slås upp under samma nyckel, men backendens kontroll
 * (jobbet tillhör tenanten) skiljer inte kunderna åt: alla frågor ligger under
 * hjälpkunden. Ägarkontrollen sitter därför här. Klienten har bara den
 * signerade token som ../route.ts gav (`<uuid>.<signatur>`), och signaturen
 * prövas mot den inloggades användare och arbetsyta i konstant tid
 * (lib/snajp/hjalp.ts:lasJobb). Fel användare, ett manipulerat id eller en
 * manipulerad signatur får 404, samma svar som ett jobb som inte finns, och
 * når aldrig backenden. Id:t prövas som uuid innan det läggs i sökvägen.
 */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  const context = await getWorkspaceContext();
  if (!context) return ejInloggadSvar();
  const { jobId: token } = await params;
  if (!arJobbtoken(token)) return jobbetSaknasSvar();
  const identitet = await hjalpIdentitet(context);
  const jobId = lasJobb(token, identitet, process.env.AUTH_SECRET);
  if (!jobId || !arUuid(jobId)) return jobbetSaknasSvar();
  return tillHjalpen(process.env.SNAJP_KEY_SNAJP_HJALP, `/api/jobs/${jobId}`, { method: "GET" }, identitet.userId);
}
