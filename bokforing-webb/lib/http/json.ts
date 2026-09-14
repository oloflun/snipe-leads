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

export class HttpJsonError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: unknown
  ) {
    super(message);
    this.name = "HttpJsonError";
  }
}

/** Begripligt på svenska, och säger vad användaren kan GÖRA. */
function meddelandeForStatus(status: number, tomKropp: boolean): string {
  if (status === 401 || status === 403) {
    return "Din session har gått ut. Ladda om sidan och logga in igen.";
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

/**
 * Returnerar den tolkade kroppen, eller `null` för ett korrekt tomt svar (204).
 * Kastar `HttpJsonError` med ett meddelande som går att visa för en användare —
 * även vid felstatus.
 *
 * Ett `error`-fält i en JSON-felkropp vinner över standardtexten: backenden vet
 * mer om sitt eget fel än den här funktionen gör.
 */
export async function readJson<T = unknown>(response: Response): Promise<T | null> {
  const parsed = await readJsonBody<T>(response);

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
