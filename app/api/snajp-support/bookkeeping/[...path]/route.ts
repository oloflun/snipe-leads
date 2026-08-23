import { NextRequest, NextResponse } from "next/server";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { SNAJP_SUPPORT_URL } from "../../_lib";

/**
 * Bokföringens egen proxy. Två skäl till att den inte går via catch-allen.
 *
 * 1. **Den är admin-grindad.** Bokföringsagenten är inte såld: ingen kund har
 *    produkten, och ytan ska inte vara nåbar för någon annan än
 *    plattformsadmin. `notFound()`-motsvarigheten här är 404 och inte 403,
 *    samma val som app/admin/layout.tsx — ett 403 bekräftar att ytan finns.
 *
 * 2. **Trafiken är BINÄR i båda riktningarna.** Catch-allen läser kroppen med
 *    `request.text()` och `proxyWithApiKey` läser svaret med `response.text()`
 *    och tvingar `Content-Type: application/json`. Ett kvitto på väg in är
 *    multipart med bytes; SIE4-filen på väg ut är CP437-kodad och innehåller
 *    bytes som inte är giltig UTF-8. Båda hade blivit obrukbara av en
 *    text-rundtur — kvittot oläsbart, SIE-filen avvisad av kundens
 *    bokföringsprogram med å/ä/ö som skräp.
 *
 * Kroppen och svaret strömmas därför som `ArrayBuffer`, och mottagarens
 * `Content-Type` bevaras i stället för att sättas.
 */

export const runtime = "nodejs";
// Render free-tier tar ~1 min att vakna, och uppladdningen väntar dessutom på
// ett LLM-anrop. Utan detta dödar Vercel funktionen och svarar UTAN kropp —
// se INV-API-001 för hela paret.
export const maxDuration = 60;

function backendPath(path: string[], search: string): string {
  // `.` kodas inte av encodeURIComponent, så `period.sie` passerar som den ska.
  return `/api/bookkeeping/${path.map(encodeURIComponent).join("/")}${search}`;
}

async function vidarebefordra(request: NextRequest, path: string[], metod: "GET" | "POST") {
  // Grinden FÖRST, före allt annat. En tenant-uppslagning innan
  // adminkontrollen hade lämnat en tidsskillnad som avslöjar om kontot finns.
  const admin = await getPlatformAdmin();
  if (!admin) {
    return NextResponse.json({ error: "Hittades inte." }, { status: 404 });
  }

  let tenant;
  try {
    tenant = await requireSnajpTenant();
  } catch (error) {
    if (error instanceof SnajpTenantError) {
      return NextResponse.json(
        { error: error.message, kod: error.kod },
        { status: error.status }
      );
    }
    throw error;
  }

  const inkommandeTyp = request.headers.get("content-type");
  const svar = await fetch(`${SNAJP_SUPPORT_URL}${backendPath(path, request.nextUrl.search)}`, {
    method: metod,
    headers: {
      "X-API-Key": tenant.apiKey,
      "X-Snajp-User": tenant.userId,
      // Multipart bär en boundary i sin content-type. Sätts den om, eller
      // utelämnas, kan mottagaren inte dela upp kroppen alls.
      ...(inkommandeTyp ? { "Content-Type": inkommandeTyp } : {})
    },
    body: metod === "POST" ? await request.arrayBuffer() : undefined,
    cache: "no-store"
  });

  const kropp = await svar.arrayBuffer();
  return new NextResponse(kropp, {
    status: svar.status,
    headers: {
      "Content-Type": svar.headers.get("content-type") ?? "application/octet-stream",
      ...(svar.headers.get("content-disposition")
        ? { "Content-Disposition": svar.headers.get("content-disposition") as string }
        : {})
    }
  });
}

type Params = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return vidarebefordra(request, path, "GET");
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return vidarebefordra(request, path, "POST");
}
