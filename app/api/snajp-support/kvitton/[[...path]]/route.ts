import { NextRequest, NextResponse } from "next/server";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { SNAJP_SUPPORT_URL } from "../../_lib";

/**
 * Kvittohanterarens proxy â€” samma skÃ¤l och samma form som bokfÃ¶ringens
 * granne (../bookkeeping/[...path]/route.ts, lÃ¤s dess docstring):
 * entitlement-grindad pÃ¥ `bookkeeping`-produkten (kvittohanteraren Ã„R den
 * produkten i `workspaces.products`), och binÃ¤rsÃ¤ker i bÃ¥da riktningarna
 * (uppladdningen Ã¤r multipart, CSV-exporten bÃ¤r BOM och Content-Disposition).
 */

export const runtime = "nodejs";
export const maxDuration = 60;

function backendPath(path: string[], search: string): string {
  // `.` kodas inte av encodeURIComponent, sÃ¥ `export.csv` passerar som den ska.
  const svans = path.length ? `/${path.map(encodeURIComponent).join("/")}` : "";
  return `/api/kvitton${svans}${search}`;
}

async function vidarebefordra(
  request: NextRequest,
  path: string[],
  metod: "GET" | "POST" | "DELETE"
) {
  // Grinden FÃ–RST â€” 404, inte 403, sÃ¥ att ytan inte bekrÃ¤ftas. Se grannen.
  const { products, signedIn } = await resolveDashboardState();
  if (!signedIn || !products.includes("bookkeeping")) {
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
  const utgaendeKropp = metod === "POST" ? await request.arrayBuffer() : undefined;

  const DEADLINE_MS = 52_000;
  const start = Date.now();
  let sistaOrsak: unknown;

  for (let forsok = 0; forsok < 3; forsok += 1) {
    const kvar = DEADLINE_MS - (Date.now() - start);
    if (kvar < 2_000) break;

    let svar: Response;
    try {
      svar = await fetch(`${SNAJP_SUPPORT_URL}${backendPath(path, request.nextUrl.search)}`, {
        method: metod,
        headers: {
          "X-API-Key": tenant.apiKey,
          "X-Snajp-User": tenant.userId,
          ...(inkommandeTyp ? { "Content-Type": inkommandeTyp } : {})
        },
        body: utgaendeKropp,
        cache: "no-store",
        signal: AbortSignal.timeout(kvar)
      });
    } catch (orsak) {
      sistaOrsak = orsak;
      await new Promise((klar) => setTimeout(klar, 1000 * (forsok + 1)));
      continue;
    }

    const kropp = await svar.arrayBuffer();
    const arGatewayFel = svar.status === 502 || svar.status === 503 || svar.status === 504;
    if (arGatewayFel && kropp.byteLength === 0 && forsok < 2) {
      sistaOrsak = new Error(`uppstrÃ¶ms ${svar.status} utan kropp`);
      await new Promise((klar) => setTimeout(klar, 1000 * (forsok + 1)));
      continue;
    }

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

  console.error("kvittoproxyn: backenden svarade inte efter omtag:", sistaOrsak);
  return NextResponse.json(
    {
      offline: true,
      error:
        "Kvittohanteraren har svÃ¥rt att nÃ¥ sin motor just nu â€” den brukar vara " +
        "tillbaka inom en minut. VÃ¤nta en liten stund och prova igen."
    },
    { status: 503 }
  );
}

type Params = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  const { path = [] } = await params;
  return vidarebefordra(request, path, "GET");
}

export async function POST(request: NextRequest, { params }: Params) {
  const { path = [] } = await params;
  return vidarebefordra(request, path, "POST");
}

export async function DELETE(request: NextRequest, { params }: Params) {
  const { path = [] } = await params;
  return vidarebefordra(request, path, "DELETE");
}
