/**
 * Läs ett JSON-svar utan att krascha på ett svar som inte är JSON.
 *
 * BAKGRUNDEN, så att mönstret inte återuppfinns halvt nästa gång:
 *
 * `await response.json()` kastar `Unexpected end of JSON input` så fort kroppen
 * är tom eller inte är JSON. Det gäller fler fall än man tror:
 *
 *   - Vercel dödar funktionen vid `maxDuration` och svarar UTAN kropp.
 *   - Render svarar 502/504 med en HTML-sida medan tjänsten vaknar ur viloläge.
 *   - En route kastar innan den hunnit skriva sin felkropp.
 *   - 204 No Content — helt korrekt, men har per definition ingen kropp.
 *
 * Anropas `.json()` före `response.ok` blir felet dessutom det RÅA
 * webbläsarmeddelandet, som sedan visades ordagrant för kunden i Email Studio:
 * "Failed to execute 'json' on 'Response': Unexpected end of JSON input".
 *
 * Därför läses kroppen som text FÖRST. Texten kan bara läsas en gång, så
 * ordningen är inte valfri: `response.json()` följt av `response.text()` i en
 * felgren kastar `body stream already read` och döljer det ursprungliga felet.
 */

import type { Localized } from "@/lib/i18n";

export class HttpJsonError extends Error {
  // Utskrivna fält, inte parameteregenskaper: då kan node --test ladda filen
  // (lib/http/json.test.ts).
  readonly status: number;
  readonly body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = "HttpJsonError";
    this.status = status;
    this.body = body;
  }
}

/**
 * 403 är inte en utgången session: sessionen finns, men kontot får inte göra
 * det här. Förut fick båda samma text, och "logga in igen" hjälpte inte.
 */
const SAKNAR_BEHORIGHET: Localized = {
  sv: "Du saknar behörighet för det här. Be den som administrerar kontot om åtkomst om du behöver den.",
  en: "You do not have permission for this. Ask the person who administers the account for access if you need it."
};

/** Sidans språk (LocaleProvider sätter `<html lang>`); svenska utanför webbläsaren. */
function sidansSprak(): keyof Localized {
  return typeof document !== "undefined" && document.documentElement?.lang === "en" ? "en" : "sv";
}

/** Begripligt på svenska, och säger vad användaren kan GÖRA. */
function meddelandeForStatus(status: number, tomKropp: boolean): string {
  if (status === 401) {
    return "Din session har gått ut. Ladda om sidan och logga in igen.";
  }
  if (status === 403) {
    return SAKNAR_BEHORIGHET[sidansSprak()];
  }
  if (status === 404) {
    return "Tjänsten kunde inte hittas. Kontakta support om det upprepas.";
  }
  if (status === 429) {
    return "För många förfrågningar just nu. Vänta en stund och försök igen.";
  }
  if (status === 502 || status === 503 || status === 504) {
    return "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut — försök igen om en stund.";
  }
  if (tomKropp) {
    // Det klassiska maxDuration-fallet: statusen kan mycket väl vara 200.
    return "Svaret avbröts innan det hann bli klart. Det beror oftast på att anropet tog för lång tid — försök igen.";
  }
  if (status >= 500) {
    return "Något gick fel på servern. Försök igen om en stund.";
  }
  return `Oväntat svar från servern (status ${status}).`;
}

/**
 * Tolkar kroppen OAVSETT statuskod. Kastar bara när det inte GÅR att tolka —
 * tom kropp, HTML, avhugget svar.
 *
 * Finns för anropare som har egen felsemantik i kroppen och därför måste läsa
 * den även vid felstatus: proxyns `{ offline: true, error }` kommer med 503,
 * och den ska bli ett läge i UI:t, inte ett kastat fel. Använd `readJson` när
 * den semantiken inte finns.
 */
export async function readJsonBody<T = unknown>(response: Response): Promise<T | null> {
  let text: string;
  try {
    text = await response.text();
  } catch (cause) {
    throw new HttpJsonError(
      "Kunde inte läsa svaret från servern. Kontrollera din uppkoppling.",
      response.status,
      cause
    );
  }

  const trimmed = text.trim();

  if (!trimmed) {
    if (response.ok && (response.status === 204 || response.status === 205)) {
      return null;
    }
    throw new HttpJsonError(meddelandeForStatus(response.status, true), response.status);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    // Icke-JSON med 200 är lika trasigt som med 500 — en HTML-felsida räknas
    // inte som ett lyckat svar bara för att statusraden säger det.
    throw new HttpJsonError(meddelandeForStatus(response.status, false), response.status, trimmed);
  }

  return parsed as T;
}

type Navigering = (url: string) => void;

const standardnavigering: Navigering = (url) => window.location.assign(url);
let navigera: Navigering = standardnavigering;
let omdirigerad = false;

/** Byter navigeringen vid 401 (testet), eller återställer den med null. */
export function sattInloggningsnavigering(fn: Navigering | null): void {
  navigera = fn ?? standardnavigering;
  omdirigerad = false;
}

/**
 * Bara Next-sidans eget 401 betyder att sessionen är borta: det bär
 * `kod: "ej_inloggad"` (lib/snajp/tenant.ts:svarForTenantfel,
 * lib/snajp/hjalp.ts:ejInloggadSvar). Proxyn skickar backendens 401 vidare
 * oförändrat ("Ogiltig API-nyckel", "X-API-Key saknas"), och det är ett
 * driftfel: inloggningen hade skickat vidare till /dashboard (proxyn ser en
 * giltig token) och tappat både sidan och förklaringen.
 */
function arUtloggad(kropp: unknown): boolean {
  return (
    !!kropp && typeof kropp === "object" && (kropp as Record<string, unknown>).kod === "ej_inloggad"
  );
}

/**
 * Ett 401 med `ej_inloggad` betyder att sessionen är borta. Då leder vi till inloggningen med
 * sidan man stod på i `next`, i stället för att bara visa "logga in igen" i
 * en ruta. Bara i webbläsaren (på servern finns ingen sida att lämna), aldrig
 * från /login själv, och högst en gång per sidladdning: flera paneler som
 * får 401 samtidigt ska inte starta flera navigeringar.
 *
 * Bara `readJson`, inte `readJsonBody`: den senare är för anropare med egen
 * felsemantik i kroppen, och de avgör själva vad ett 401 betyder.
 */
function tillInloggningen(): void {
  if (omdirigerad || typeof window === "undefined" || !window.location) {
    return;
  }
  const { pathname, search } = window.location;
  if (pathname === "/login" || pathname.startsWith("/login/")) {
    return;
  }
  omdirigerad = true;
  navigera(`/login?next=${encodeURIComponent(`${pathname}${search}`)}`);
}

/**
 * Returnerar den tolkade kroppen, eller `null` för ett korrekt tomt svar (204).
 * Ett 401 med `kod: "ej_inloggad"` i webbläsaren leder dessutom till
 * inloggningen (`tillInloggningen`); andra 401 blir bara ett fel.
 * Kastar `HttpJsonError` med ett meddelande som går att visa för en användare —
 * även vid felstatus.
 *
 * Ett `error`-fält i en JSON-felkropp vinner över standardtexten: backenden vet
 * mer om sitt eget fel än den här funktionen gör.
 */
export async function readJson<T = unknown>(response: Response): Promise<T | null> {
  const parsed = await readJsonBody<T>(response);

  if (response.status === 401 && arUtloggad(parsed)) {
    tillInloggningen();
  }

  if (!response.ok) {
    const kropp: unknown = parsed;
    const fromBody =
      kropp && typeof kropp === "object" && typeof (kropp as Record<string, unknown>).error === "string"
        ? ((kropp as Record<string, unknown>).error as string)
        : null;
    throw new HttpJsonError(
      fromBody ?? meddelandeForStatus(response.status, false),
      response.status,
      parsed
    );
  }

  return parsed;
}

// Egen fil: testet (node --test) kan inte ladda den här filens parameteregenskaper.
export { kroppsbesked } from "./besked.ts";

/** Meddelande som går att visa för en användare, oavsett vad som kastades. */
export function felmeddelande(error: unknown, reserv = "Något gick fel. Försök igen."): string {
  if (error instanceof HttpJsonError) {
    return error.message;
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return "Anropet avbröts eftersom det tog för lång tid. Försök igen.";
  }
  if (error instanceof TypeError) {
    // Så ser ett nätverksavbrott ut i fetch.
    return "Kunde inte nå servern. Kontrollera din uppkoppling och försök igen.";
  }
  return error instanceof Error && error.message ? error.message : reserv;
}
