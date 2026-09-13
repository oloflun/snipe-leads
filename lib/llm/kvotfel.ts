/**
 * Kvotfel mot AI-leverantören — TS-spegeln av snajp-support/app/kvotfel.py.
 *
 * ## Varför en spegel och inte en egen tolkning
 *
 * Ett avvisat modellanrop betyder en av två helt olika saker (se modulens
 * Python-docstring):
 *
 *   1. MINUT-/DYGNSKVOT — övergående. "Försök igen om en stund" är sant.
 *   2. KREDITSLUT — permanent tills en människa agerar (förskottskredit slut,
 *      fakturering avstängd, projekt avstängt, utgiftstak nått). Att vänta
 *      hjälper aldrig, och att be kunden försöka igen är vilseledande.
 *
 * Email Studio behandlade båda som "tillfälligt fel", tog om varje 429 tre
 * gånger och sa "Prova igen om en liten stund" — samma fel backenden hade
 * 2026-09-08. Klassificeringen läser TEXT, inte undantagsklass, av samma skäl
 * som Python-sidan: leverantörer byter felklass och formulering.
 *
 * HÅLL MARKÖRERNA ORDAGRANT LIKA `_KREDITMARKORER` i kvotfel.py. Två listor som
 * glider isär är två sanningar om samma driftstopp — lib/llm/kvotfel.test.ts
 * använder samma uppmätta texter som snajp-support/tests/test_kvotfel.py.
 *
 * Filen har inga runtime-importer med flit: den körs direkt av `node --test`
 * utan bundler.
 */

export type Modellfelklass = "kreditslut" | "kvot" | "tillfälligt fel";

/**
 * Googles egna formuleringar när anropet avvisas för att BETALNINGEN saknas —
 * inte för att takten är för hög. Gemener; jämförelsen gör om texten till gemener.
 *
 * Första tre: AI Studios förskottskredit (uppmätt 429 2026-09-08). Resten:
 * Vertex AI, där ett tomt eller stängt faktureringskonto ger 403
 * PERMISSION_DENIED med BILLING_DISABLED ("This API method requires billing to
 * be enabled"), ett stängt konto för projektet, eller CONSUMER_SUSPENDED — och
 * AI Studios utgiftstak. Bara "billing" räcker INTE: Googles vanliga kvot-429
 * säger "please check your plan and billing details", och det är övergående.
 */
const KREDITMARKORER = [
  "prepayment credits",
  "credits are depleted",
  "billing#prepay",
  "billing_disabled",
  "billing to be enabled",
  "billing account for the owning project",
  "consumer_suspended",
  "has been suspended",
  "spending cap"
] as const;

/**
 * Hur djupt `cause`-kedjan följs — `_KEDJEDJUP` i Python. Ett omslaget fel (AI
 * SDK:ns RetryError, ett eget Error med `cause`) bär leverantörens text i
 * orsaken, inte i sig själv. Taket skyddar mot cykliska kedjor.
 */
const KEDJEDJUP = 5;

type Felform = {
  statusCode?: unknown;
  status?: unknown;
  name?: unknown;
  message?: unknown;
  responseBody?: unknown;
  isRetryable?: unknown;
  cause?: unknown;
};

/** Felet och dess orsaker, närmast först. Spegel av `_kedja`. */
function kedja(fel: unknown): unknown[] {
  const sedda: unknown[] = [];
  let aktuell: unknown = fel;
  while (aktuell != null && sedda.length < KEDJEDJUP && !sedda.includes(aktuell)) {
    sedda.push(aktuell);
    aktuell = typeof aktuell === "object" ? (aktuell as Felform).cause : undefined;
  }
  return sedda;
}

/**
 * Texten i EN länk: meddelande plus leverantörens svarskropp. Svarskroppen är
 * där Google skriver BILLING_DISABLED — meddelandet i APICallError är ofta bara
 * första raden. (Motsvarar `str(led)` i Python.)
 */
function lanktext(led: unknown): string {
  if (typeof led === "string") return led;
  const e = led as Felform;
  const delar: string[] = [];
  if (typeof e.message === "string") delar.push(e.message);
  if (typeof e.responseBody === "string") delar.push(e.responseBody);
  if (delar.length === 0) {
    try {
      delar.push(String(led));
    } catch {
      // Ett objekt utan toString — ingen text att läsa.
    }
  }
  return delar.join("\n");
}

/** HTTP-statusen om felet bär en. AI-SDK:ns APICallError har `statusCode`. */
export function statuskod(fel: unknown): number | null {
  for (const led of kedja(fel)) {
    if (!led || typeof led !== "object") continue;
    const e = led as Felform;
    if (typeof e.statusCode === "number") return e.statusCode;
    if (typeof e.status === "number") return e.status;
  }
  return null;
}

/** Spegel av `ar_kreditslut`: betalningen saknas hos leverantören. */
export function arKreditslut(fel: unknown): boolean {
  const texter = typeof fel === "string" ? [fel] : kedja(fel).map(lanktext);
  return texter.some((text) => {
    const gemen = text.toLowerCase();
    return KREDITMARKORER.some((markor) => gemen.includes(markor));
  });
}

/** Spegel av `ar_kvotfel`: leverantörens kvottak (429-klassen). */
export function arKvotfel(fel: unknown): boolean {
  for (const led of kedja(fel)) {
    if (led && typeof led === "object") {
      const e = led as Felform;
      if (e.statusCode === 429 || e.status === 429) return true;
      if (e.name === "RateLimitError" || e.name === "ResourceExhausted") return true;
    }
    const text = lanktext(led).toLowerCase();
    if (
      text.includes("429") &&
      (text.includes("quota") ||
        text.includes("rate limit") ||
        text.includes("resource_exhausted") ||
        text.includes("resource exhausted"))
    ) {
      return true;
    }
  }
  return false;
}

/**
 * Den klass kunden ska få veta. Kreditslut prövas FÖRST: AI Studios
 * kreditslut kommer som 429 och hade annars klassats som en vanlig kvot —
 * exakt den sammanblandning den här modulen finns för att undvika.
 */
export function klassaModellfel(fel: unknown): Modellfelklass {
  if (arKreditslut(fel)) return "kreditslut";
  if (arKvotfel(fel)) return "kvot";
  return "tillfälligt fel";
}

/**
 * Om ett omtag kan ge ett annat svar.
 *
 * Kreditslut: aldrig — tre anrop mot en tom kredit är tre avvisningar och 3 s
 * väntan för kunden. Vanlig kvot: ja, men anroparen håller antalet begränsat.
 * Resten som förut: AI-SDK:ns `isRetryable`, 408/429/5xx, och fel utan
 * statuskod (nätverk, DNS, timeout — anropet nådde aldrig fram).
 */
export function kanForsokasOm(fel: unknown): boolean {
  if (!fel) return false;
  if (arKreditslut(fel)) return false;
  if ((fel as Felform).isRetryable === true) return true;
  const status = statuskod(fel);
  if (status !== null) {
    return status === 408 || status === 429 || status >= 500;
  }
  return true;
}
