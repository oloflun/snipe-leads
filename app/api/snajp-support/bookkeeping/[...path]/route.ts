import { NextRequest, NextResponse } from "next/server";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { SNAJP_SUPPORT_URL } from "../../_lib";

/**
 * Bokföringens egen proxy. Två skäl till att den inte går via catch-allen.
 *
 * 1. **Den är entitlement-grindad.** Bokföringen är en produkt som en
 *    arbetsyta antingen har köpt eller inte, och grinden är `products` precis
 *    som för leads och support. Ytan var admin-grindad fram till att den blev
 *    säljbar; kontrollen byttes samtidigt som routen fick sin ProductKey, och
 *    de två måste bytas TILLSAMMANS — en meny som visar fliken mot en proxy
 *    som svarar 404 är en produkt som ser trasig ut för den som köpt den.
 *    Svaret är 404 och inte 403, samma val som app/admin/layout.tsx: ett 403
 *    bekräftar att ytan finns.
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

async function vidarebefordra(
  request: NextRequest,
  path: string[],
  metod: "GET" | "POST" | "DELETE"
) {
  // Grinden FÖRST, före allt annat. En tenant-uppslagning innan
  // entitlement-kontrollen hade lämnat en tidsskillnad som avslöjar om kontot
  // finns, och gjort ett databasanrop åt någon som inte får vara här.
  //
  // `signedIn` måste stå med, och det är inte bältesspänne på hängslen.
  // `resolveDashboardState()` returnerar ANONYMOUS utan session, och den listan
  // är PERMISSIV med flit — den finns för marknadsföringsytorna, där
  // demodashboarden ska visa allt. Utan raden nedan passerade alltså en
  // oinloggad förfrågan entitlement-kontrollen och föll först på
  // `requireSnajpTenant` med 401.
  //
  // Uppmätt mot dev 2026-08-24: POST /api/snajp-support/bookkeeping/chat utan
  // session gav 401, inte 404. Ingen data läckte — men ytan bekräftades, vilket
  // är precis vad 404:an ovan finns för att undvika, och databasanropet gjordes
  // åt någon som inte skulle ha kommit så långt.
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
  // Kroppen läses EN gång, före omtagsloopen — en förbrukad request-ström går
  // inte att läsa om, men buffern går att skicka hur många gånger som helst.
  const utgaendeKropp = metod === "POST" ? await request.arrayBuffer() : undefined;

  /**
   * Omtag med deadline i stället för fast antal: den här routen var den enda
   * backend-proxyn HELT utan retry (den delades av från catch-allen för
   * binärtrafikens skull och tappade resiliensen på köpet), fast kallstarten
   * på ~1 min är precis lika verklig här. Ett chatt-anrop kan samtidigt ta
   * 30–40 s på riktigt (flera LLM-varv), så per-försökstiden är resten av
   * budgeten, inte en kort fast tid. Budgeten 52 s lämnar marginal till
   * maxDuration = 60 så att routen alltid hinner skriva en egen svarskropp.
   */
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
          // Multipart bär en boundary i sin content-type. Sätts den om, eller
          // utelämnas, kan mottagaren inte dela upp kroppen alls.
          ...(inkommandeTyp ? { "Content-Type": inkommandeTyp } : {})
        },
        // DELETE bär inga bytes. Att läsa kroppen ändå hade varit ofarligt, men
        // `fetch` avvisar en DELETE med kropp i vissa runtimes — och det finns
        // ingenting att skicka: urvalet står i frågesträngen.
        body: utgaendeKropp,
        cache: "no-store",
        signal: AbortSignal.timeout(kvar)
      });
    } catch (orsak) {
      // Nätverksfel eller timeout — backenden nåddes aldrig. Paus och nytt
      // försök så länge budgeten räcker.
      sistaOrsak = orsak;
      await new Promise((klar) => setTimeout(klar, 1000 * (forsok + 1)));
      continue;
    }

    const kropp = await svar.arrayBuffer();

    // 502/503/504 med tom kropp är plattformens egen sida under uppvakning,
    // inte ett svar från vår backend — värt ett omtag, inte en vidarebefordran.
    const arGatewayFel = svar.status === 502 || svar.status === 503 || svar.status === 504;
    if (arGatewayFel && kropp.byteLength === 0 && forsok < 2) {
      sistaOrsak = new Error(`uppströms ${svar.status} utan kropp`);
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

  // Diagnosen till loggen; kunden får en mening som säger vad hen kan göra.
  console.error("bokföringsproxyn: backenden svarade inte efter omtag:", sistaOrsak);
  return NextResponse.json(
    {
      offline: true,
      error:
        "Assistenten har svårt att nå sin motor just nu — den brukar vara tillbaka " +
        "inom en minut. Vänta en liten stund och prova igen; din fråga och din fil " +
        "finns kvar."
    },
    { status: 503 }
  );
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

// Rensningen av en period. Går genom SAMMA grind som resten — entitlement
// först, tenant sedan — vilket är hela skälet till att den ligger här och inte
// får en egen route: en raderingsväg utanför `vidarebefordra` hade varit en
// väg utan de två kontrollerna.
export async function DELETE(request: NextRequest, { params }: Params) {
  const { path } = await params;
  return vidarebefordra(request, path, "DELETE");
}
