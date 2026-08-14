import { NextRequest } from "next/server";
import { proxyToBackend } from "../../_lib";

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna. Utan detta dödar Vercel
// funktionen efter 10 s och en frisk backend ser ut att vara nere.
export const maxDuration = 60;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;

  // Tenanten MÅSTE följa med hit. Jobbet skapades med kundens egen nyckel av
  // chat-routen, och backenden slår upp jobb inom en tenant — pollar vi med
  // demonyckeln finns jobbet inte, och chatten fastnar på "Agenten arbetar" i
  // evighet. Felet syns inte i drift så länge kundens nyckel saknas i env,
  // eftersom båda anropen då faller tillbaka på samma demonyckel.
  //
  // Sluggen kommer från klienten, precis som i chat-routen. Jobb-id:t är ett
  // UUID, så en förfalskad slug ger ingen väg in i någon annans data.
  const tenant = request.nextUrl.searchParams.get("tenant");

  return proxyToBackend(
    `/api/jobs/${encodeURIComponent(jobId)}`,
    { method: "GET" },
    tenant
  );
}
