import { NextResponse } from "next/server";
import { getTenant } from "@/lib/tenants";

// Tunn proxy mot den headless Snajp-Support-backenden (FastAPI, hostas på Render).
// Webbläsaren träffar bara Next-appen; den interna API-nyckeln sätts server-side.
// SNAJP_SUPPORT_URL sätts på Vercel till Render-URL:en; lokalt defaultar den till 8000.

export const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";
export const SNAJP_INTERNAL_API_KEY =
  process.env.SNAJP_INTERNAL_API_KEY ?? "snajp_demo_2f8c1a9e4b7d";

// Skiljer på "env-varen är inte satt" och "backenden svarar inte" — utan detta
// ser båda felen likadana ut i UI:t och man felsöker åt fel håll.
const URL_IS_CONFIGURED = Boolean(process.env.SNAJP_SUPPORT_URL);

/**
 * En registrerad kund saknar sin API-nyckel i miljön. Kastas i stället för att
 * tyst svara ur demo-tenantens kunskapsbas.
 */
export class MissingTenantKeyError extends Error {
  constructor(
    readonly tenantName: string,
    readonly envVar: string
  ) {
    super(
      `${tenantName} har ingen egen API-nyckel i den här miljön (${envVar} saknas). ` +
        "Supporten svarar inte förrän nyckeln är satt — annars hade svaren kommit " +
        "ur ett annat bolags kunskapsbas."
    );
    this.name = "MissingTenantKeyError";
  }
}

/**
 * Nyckelval för de ANONYMA routerna — den publika chatten och jobbpollningen.
 * Där kommer sluggen från klienten, och det är i sin ordning: nyckeln finns bara
 * på servern, och jobb-id är UUID.
 *
 * Inloggad trafik använder INTE den här vägen. Den går via requireSnajpTenant()
 * i lib/snajp/tenant.ts, som härleder tenanten ur sessionen. Att de två skiljer
 * sig åt ÄR säkerhetsgränsen: en slug från en klient får aldrig avgöra vilken
 * kunds inkorg, kunskapsbas eller röstdokument som öppnas.
 */
export function apiKeyForTenant(tenantSlug?: string | null): string {
  if (!tenantSlug) {
    return SNAJP_INTERNAL_API_KEY;
  }

  const tenant = getTenant(tenantSlug);
  if (!tenant) {
    console.warn(`snajp-support: okänd tenant "${tenantSlug}", använder demonyckeln.`);
    return SNAJP_INTERNAL_API_KEY;
  }

  const key = process.env[tenant.supportKeyEnv];
  if (!key) {
    // INGEN fallback till demonyckeln här. En registrerad kund utan egen nyckel
    // hade annars fått svar ur demo-tenantens kunskapsbas — alltså ett ANNAT
    // bolags villkor, presenterade som kundens egna. För Livrustning betyder det
    // en annan tillverkares garantitider på medicinteknisk utrustning.
    //
    // Ett tydligt fel är alltid bättre än ett trovärdigt men felaktigt svar.
    // Okänd slug (ovan) faller fortfarande tillbaka, eftersom den bara kan komma
    // från en förfalskad payload och inte från en riktig kund.
    throw new MissingTenantKeyError(tenant.name, tenant.supportKeyEnv);
  }

  return key;
}

export function offlineResponse(cause?: unknown) {
  const reason = cause instanceof Error ? cause.message : undefined;
  // Diagnosen — hostnamn, env-varnamn, orsaken — hör hemma i serverloggen.
  // Den stod tidigare i svarskroppen och renderades som en röd bubbla i den
  // PUBLIKA chatten: en besökare fick läsa vår interna URL, vår hostingplan
  // och vilka variabler som saknades. Kunden får en mänsklig mening; vi får
  // hela bilden i loggen.
  console.error(
    URL_IS_CONFIGURED
      ? `snajp-support: backenden på ${SNAJP_SUPPORT_URL} svarar inte${reason ? ` (${reason})` : ""}.`
      : "snajp-support: SNAJP_SUPPORT_URL är inte satt i denna miljö — proxyn föll tillbaka på localhost, som inte finns i deploy. Sätt env-varen och deploya om."
  );

  return NextResponse.json(
    {
      offline: true,
      error:
        "Assistenten har svårt att nå sin motor just nu — den brukar vara tillbaka inom en minut. " +
        "Vänta en liten stund och skicka gärna frågan igen."
    },
    { status: 503 }
  );
}

// Render free-tier somnar efter 15 min och tar ~1 min att vakna. Ett enskilt
// försök kan alltså inte lyckas — men hela budgeten nedan täcker det mesta av
// uppvakningen, förutsatt att route-filerna sätter `maxDuration = 60`.
//
// Budgeten är räknad mot det taket: 5 × 9 s försök + ~5,5 s pauser ≈ 51 s.
// Den gamla varianten (5 × 10 s + 4 × 1 s = 54 s) låg så nära 60 att sista
// försöket kunde dödas mitt i och ge klienten en TOM kropp — precis felet
// som lib/http/json.ts dokumenterar.
const ATTEMPT_TIMEOUT_MS = 9_000;
const MAX_ATTEMPTS = 5;

/** Exponentiell paus med lite jitter, så fem klienter inte väcker backenden i takt. */
function paus(attempt: number): Promise<void> {
  const bas = Math.min(500 * 2 ** attempt, 2000);
  return new Promise((resolve) => setTimeout(resolve, bas + Math.floor(Math.random() * 250)));
}

/**
 * Vidarebefordran med en REDAN upplöst nyckel. Inloggade routes går hit via
 * proxyAsTenant i _auth.ts; anonyma går via proxyToBackend nedan, som slår upp
 * nyckeln ur en slug först.
 */
export async function proxyWithApiKey(
  path: string,
  init: RequestInit,
  apiKey: string,
  userId?: string,
  isDemo?: boolean
) {
  const metod = String(init.method ?? "GET").toUpperCase();
  // GET får göras om: kallstart är idempotent. POST/PUT/PATCH är det inte —
  // fem omförsök mot /leads/runs/batch startade fem Gemini-sökningar och
  // lämnade spökprospekt när den första ändå blev klar efter aborten.
  const farGorasOm = metod === "GET" || metod === "HEAD";
  const forsok = farGorasOm ? MAX_ATTEMPTS : 1;
  let lastCause: unknown;

  for (let attempt = 0; attempt < forsok; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ATTEMPT_TIMEOUT_MS);
    try {
      const response = await fetch(`${SNAJP_SUPPORT_URL}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
          // Enbart till timtaket per användare. Sätts efter sessionen, aldrig
          // från klienten — och backenden kan bara BEGRÄNSA på den, inte höja.
          ...(userId ? { "X-Snajp-User": userId } : {}),
          ...(isDemo ? { "X-Snajp-Demo": "true" } : {}),
          ...(init.headers ?? {})
        },
        cache: "no-store",
        signal: controller.signal
      });
      // Ett riktigt HTTP-svar ska vidarebefordras, inte göras om.
      //
      // Tidigare stod `await response.json()` här, i samma try som fetch. En
      // kropp som inte var JSON — Renders HTML-sida vid 502, eller en tom kropp
      // när tjänsten dödades mitt i — kastade då likadant som ett nätverksfel
      // och föll in i retry-slingan. Fem försök à 10 s plus pauser tog över 50
      // sekunder, vilket i sin tur sprängde Vercels maxDuration. Klienten fick
      // ett TOMT svar, och frontends `.json()` kastade "Unexpected end of JSON
      // input" — ett felmeddelande som pekar på frontend fast orsaken satt här.
      //
      // Kroppen läses därför som text först, och bara fetch-fel når catch.
      const rawBody = (await response.text()).trim();

      if (response.status === 204 || response.status === 205) {
        return new NextResponse(null, { status: response.status });
      }

      // 502/503/504 utan JSON-kropp är uppvakningsfasen: Renders/Railways egen
      // HTML- eller tomsida, inte ett svar från vår backend. Det är EXAKT det
      // läge retry-slingan finns för, så det behandlas som ett transient fel
      // i stället för att skickas vidare som ett trasigt svar.
      const arGatewayStatus = response.status === 502 || response.status === 503 || response.status === 504;

      if (!rawBody) {
        if (arGatewayStatus && farGorasOm && attempt < forsok - 1) {
          lastCause = new Error(`uppströms ${response.status} utan innehåll`);
          await paus(attempt);
          continue;
        }
        console.error(`snajp-support: backenden svarade ${response.status} utan innehåll (${path}).`);
        return NextResponse.json(
          {
            error: "Svaret kom aldrig fram helt. Vänta en liten stund och prova igen.",
            upstreamStatus: response.status
          },
          { status: response.status >= 400 ? response.status : 502 }
        );
      }

      try {
        const parsed = JSON.parse(rawBody);
        // FastAPI:s HTTPException serialiseras som {"detail": ...} men varje
        // klientkomponent läser `error`. Utan raden blev backendens omsorgsfullt
        // skrivna 429-text "Okänt fel" i chatten.
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          if (typeof parsed.detail === "string" && typeof parsed.error !== "string") {
            parsed.error = parsed.detail;
          }
        }
        return NextResponse.json(parsed, { status: response.status });
      } catch {
        if (arGatewayStatus && farGorasOm && attempt < forsok - 1) {
          lastCause = new Error(`uppströms ${response.status} med icke-JSON-kropp`);
          await paus(attempt);
          continue;
        }
        console.error(
          `snajp-support: backenden svarade ${response.status} med icke-JSON-kropp (${path}): ${rawBody.slice(0, 200)}`
        );
        return NextResponse.json(
          {
            error: "Svaret gick inte att tolka. Vänta en liten stund och prova igen.",
            upstreamStatus: response.status
          },
          { status: response.status >= 400 ? response.status : 502 }
        );
      }
    } catch (cause) {
      lastCause = cause;
      // Bara timeout/nätverksfel är värt att göra om — ett riktigt HTTP-svar
      // har redan returnerats ovan.
      if (farGorasOm && attempt < forsok - 1) {
        await paus(attempt);
      }
    } finally {
      clearTimeout(timer);
    }
  }

  return offlineResponse(lastCause);
}

/** Anonym väg: slug från klienten → nyckel → vidarebefordran. */
export async function proxyToBackend(path: string, init: RequestInit, tenantSlug?: string | null) {
  let apiKey: string;
  try {
    apiKey = apiKeyForTenant(tenantSlug);
  } catch (error) {
    if (error instanceof MissingTenantKeyError) {
      // 503, inte 500: tjänsten är riktigt konfigurerad men saknar en nyckel i
      // just den här miljön. Loggen namnger variabeln så felet går att åtgärda
      // utan att läsa koden — men KLIENTEN får inte env-varnamnet: den texten
      // renderades tidigare ordagrant i den publika chattens felbubbla.
      console.error(`snajp-support: ${error.message}`);
      return NextResponse.json(
        {
          error:
            "Supporten är inte färdigaktiverad för det här kontot ännu. " +
            "Hör av dig till oss så sätter vi den i drift.",
          configured: false
        },
        { status: 503 }
      );
    }
    throw error;
  }

  return proxyWithApiKey(path, init, apiKey);
}
