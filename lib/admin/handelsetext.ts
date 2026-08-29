import type { Localized } from "@/lib/i18n";

/**
 * Händelsetexter: från stacktrace till mening.
 *
 * ## Problemet
 *
 * Backendens `log_exception` skriver `f"{type(error).__name__}: {error}"`, och
 * för en LLM-klient är `{error}` hela leverantörens JSON-svar. Notiscentret
 * visade därför rader på tvåtusen tecken av `{'@type':
 * 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [...]}` — text
 * som är fullt läsbar för den som redan vet vad den betyder och obegriplig för
 * alla andra. Och de flesta av dem säger samma sak: kvoten är slut.
 *
 * ## Lösningen, och vad den INTE gör
 *
 * Varje tolkare nedan känner igen ett felmönster och byter ut det mot en
 * rubrik, en förklaring och en åtgärd. Råtexten kastas ALDRIG — den ligger
 * kvar under "tekniska detaljer" i vyn. Ett notiscenter som bara visar en
 * vänlig omskrivning är ett notiscenter man inte kan felsöka ur, och den som
 * behöver `retryDelay` i sekunder ska hitta den utan att öppna databasen.
 *
 * `tolkad: false` betyder att inget mönster matchade. Vyn visar då den städade
 * råtexten — inte en påhittad förklaring. En felaktig tolkning av ett fel är
 * värre än ingen, för den skickar felsökningen åt fel håll.
 */

export type Kategori =
  | "kvot"
  | "modell"
  | "behorighet"
  | "timeout"
  | "anslutning"
  | "mail"
  | "databas"
  | "indata"
  | "overbelastad"
  | "internt"
  | "okant";

export type Handelsetolkning = {
  /** En rad, utan felkod. Det som står i listan. */
  rubrik: Localized;
  /**
   * Vad det betyder och vad man gör åt det. Två meningar, sällan fler.
   *
   * Null när raden inte gick att tolka: rubriken ÄR då meddelandet, och en
   * utfyllnadsmening under varje sådan rad ("ingen känd orsak…") hade upprepats
   * i listan utan att tillföra något. Tystnad läser bättre än en platshållare.
   */
  forklaring: Localized | null;
  kategori: Kategori;
  /** Originalmeddelandet, oförändrat. Ligger under "tekniska detaljer". */
  teknisk: string;
  /** Falskt = inget mönster matchade, och vyn ska inte låtsas annat. */
  tolkad: boolean;
};

/* ------------------------------------------------------------------ *
 * Utplock ur råtexten
 * ------------------------------------------------------------------ */

/** Leverantörens modellnamn, t.ex. `gemini-3.6-flash` eller `deepseek-v4-flash`. */
function modellnamn(text: string): string | null {
  const monster = [
    /['"]model['"]\s*:\s*['"]([^'"]+)['"]/i,
    /\bmodels?\/([A-Za-z0-9._-]+)/,
    /\bmodel[:=]\s*([A-Za-z0-9._-]+)/i
  ];
  for (const re of monster) {
    const m = re.exec(text);
    if (m?.[1]) return m[1];
  }
  return null;
}

/**
 * Vilken leverantör modellnamnet hör till. Namnet ensamt säger inget för den
 * som ska agera — "kvoten är slut" är en fråga till Google, till DeepSeek
 * eller till OpenAI, och det är olika konton hos olika parter.
 */
function leverantor(text: string): string | null {
  const t = text.toLowerCase();
  if (t.includes("gemini") || t.includes("googleapis") || t.includes("generativelanguage")) {
    return "Google Gemini";
  }
  if (t.includes("deepseek")) return "DeepSeek";
  if (t.includes("anthropic") || t.includes("claude")) return "Anthropic";
  if (t.includes("openai") || /\bgpt-|\bo[1-9]-/.test(t)) return "OpenAI";
  return null;
}

/** Sekunder tills det går att försöka igen, om leverantören sa det. */
function aterforsok(text: string): number | null {
  const m =
    /['"]retryDelay['"]\s*:\s*['"](\d+)s['"]/i.exec(text) ?? /retry in ([\d.]+)\s*s/i.exec(text);
  if (!m?.[1]) return null;
  const n = Math.ceil(Number(m[1]));
  return Number.isFinite(n) && n > 0 ? n : null;
}

/** Dagligt tak, när leverantören råkar skicka med det. */
function kvottak(text: string): number | null {
  const m = /\blimit['"]?\s*[:=]\s*['"]?(\d+)/i.exec(text);
  if (!m?.[1]) return null;
  const n = Number(m[1]);
  return Number.isFinite(n) ? n : null;
}

/** HTTP-status ur `Error code: 429` eller `status_code=503`. */
function statuskod(text: string): number | null {
  const m =
    /Error code:\s*(\d{3})/i.exec(text) ??
    /status[_ ]?code[=:]\s*(\d{3})/i.exec(text) ??
    /\bHTTP\s+(\d{3})\b/i.exec(text);
  return m?.[1] ? Number(m[1]) : null;
}

/** Undantagstypen ur `NotFoundError: ...`. Tom sträng om raden inte har någon. */
function undantagstyp(text: string): string {
  const m = /^([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Timeout|Warning))\s*:/.exec(text.trim());
  return m?.[1] ?? "";
}

/**
 * Städar råtexten till en läsbar mening: kapar leverantörens JSON-svans, tar
 * bort undantagstypen och allt efter första radbrytningen.
 *
 * Det här är GOLVET, inte en tolkning — den används när inget mönster matchar,
 * och den lägger inte till någon betydelse som inte redan står i texten.
 */
function stada(text: string): string {
  let t = text.trim();
  const typ = undantagstyp(t);
  if (typ) t = t.slice(typ.length + 1).trim();

  // Leverantörernas svar ser ut som `Error code: 429 - [{'error': {...}}]`.
  // Allt från ` - [` eller ` - {` och framåt är maskintext.
  const nyttlast = /\s[-–]\s[[{]/.exec(t);
  if (nyttlast) t = t.slice(0, nyttlast.index).trim();

  // Bär raden ändå en inbäddad `'message': '...'` är den nästan alltid det
  // begripligaste som finns i strängen.
  if (/^[[{]/.test(t) || t.length === 0) {
    const m = /['"]message['"]\s*:\s*['"]([^'"]{4,300})['"]/.exec(text);
    if (m?.[1]) t = m[1];
  }

  t = t.split("\n")[0].trim().replace(/\s+/g, " ");
  if (t.length > 240) t = `${t.slice(0, 237).trimEnd()}…`;
  if (!t) t = text.slice(0, 240);
  return t;
}

/** Undantagstyper vars namn faktiskt bär betydelse, översatta. */
const TYPNAMN: Record<string, Localized> = {
  ValueError: { sv: "Ogiltigt värde", en: "Invalid value" },
  KeyError: { sv: "Ett fält saknas", en: "A field is missing" },
  TypeError: { sv: "Fel datatyp", en: "Wrong data type" },
  PermissionError: { sv: "Nekad åtkomst", en: "Access denied" },
  FileNotFoundError: { sv: "Filen finns inte", en: "File not found" },
  JSONDecodeError: { sv: "Svaret gick inte att tolka", en: "The response could not be parsed" }
};

/* ------------------------------------------------------------------ *
 * Tolkarna. Ordningen är betydelsebärande — se kommentaren vid TOLKARE.
 * ------------------------------------------------------------------ */

type Tolkare = (text: string) => Handelsetolkning | null;

function svar(
  kategori: Kategori,
  rubrik: Localized,
  forklaring: Localized,
  teknisk: string
): Handelsetolkning {
  return { kategori, rubrik, forklaring, teknisk, tolkad: true };
}

/**
 * Kvottak hos AI-leverantören. Den absolut vanligaste raden i loggen, och den
 * som gjorde mest skada som råtext: samma fel dök upp i fyra formuleringar och
 * såg ut som fyra problem.
 */
const kvot: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    statuskod(text) === 429 ||
    t.includes("ratelimit") ||
    t.includes("resource_exhausted") ||
    t.includes("quota") ||
    t.includes("rate limit");
  if (!traff) return null;

  const lev = leverantor(text);
  const modell = modellnamn(text);
  const tak = kvottak(text);
  const vanta = aterforsok(text);

  const vemSv = modell ? `${lev ?? "AI-leverantören"} (${modell})` : (lev ?? "AI-leverantören");
  const vemEn = modell ? `${lev ?? "the AI provider"} (${modell})` : (lev ?? "the AI provider");

  const takSv = tak ? ` Taket ligger på ${tak} anrop per dygn på nuvarande plan.` : "";
  const takEn = tak ? ` The ceiling is ${tak} requests per day on the current plan.` : "";
  const vantaSv = vanta
    ? ` Nästa försök går igenom om ungefär ${vanta} sekunder.`
    : " Anropen går igenom igen när kvoten återställs.";
  const vantaEn = vanta
    ? ` The next attempt should go through in about ${vanta} seconds.`
    : " Requests resume once the quota resets.";

  return svar(
    "kvot",
    { sv: `Kvoten hos ${vemSv} är slut`, en: `Quota exhausted at ${vemEn}` },
    {
      sv: `Fler anrop än planen tillåter har gjorts under perioden, så leverantören avvisar resten.${takSv}${vantaSv} Återkommer det dagligen är det plangränsen som är för låg, inte ett fel i koden.`,
      en: `More requests were made than the plan allows for the period, so the provider is rejecting the rest.${takEn}${vantaEn} If this recurs daily the plan limit is too low — it is not a defect in the code.`
    },
    text
  );
};

/** Modellnamnet finns inte hos leverantören — nästan alltid en felstavning. */
const modellSaknas: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    (statuskod(text) === 404 && t.includes("model")) ||
    t.includes("is not found for api version") ||
    t.includes("model_not_found") ||
    (t.includes("does not exist") && t.includes("model"));
  if (!traff) return null;

  const modell = modellnamn(text);
  const lev = leverantor(text);

  return svar(
    "modell",
    {
      sv: `${modell ? `Modellen ${modell}` : "Den begärda modellen"} finns inte${lev ? ` hos ${lev}` : ""}`,
      en: `${modell ? `The model ${modell}` : "The requested model"} does not exist${lev ? ` at ${lev}` : ""}`
    },
    {
      sv: "Leverantören känner inte igen modellnamnet — det är oftast en felstavning eller en modell som pensionerats. Rätta namnet i miljövariablerna; anropet kommer inte att lyckas förrän modellen finns hos leverantören.",
      en: "The provider does not recognise the model name — usually a typo or a model that has been retired. Correct the name in the environment variables; the call will keep failing until the model exists at the provider."
    },
    text
  );
};

/** Nyckeln saknas, är fel eller saknar behörighet. */
const behorighet: Tolkare = (text) => {
  const kod = statuskod(text);
  const t = text.toLowerCase();
  const traff =
    kod === 401 ||
    kod === 403 ||
    t.includes("authenticationerror") ||
    t.includes("invalid_api_key") ||
    t.includes("invalid api key") ||
    t.includes("permissiondenied") ||
    t.includes("unauthorized");
  if (!traff) return null;

  const lev = leverantor(text);

  return svar(
    "behorighet",
    {
      sv: `API-nyckeln${lev ? ` hos ${lev}` : ""} avvisades`,
      en: `The API key${lev ? ` for ${lev}` : ""} was rejected`
    },
    {
      sv: "Nyckeln saknas, har gått ut eller saknar behörighet till det som anropades. Kontrollera nyckeln i miljövariablerna — den behöver bytas, inte försökas om.",
      en: "The key is missing, expired, or lacks permission for what was called. Check the key in the environment variables — it needs replacing, not retrying."
    },
    text
  );
};

/** Svaret kom aldrig i tid. */
const timeout: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    statuskod(text) === 504 ||
    t.includes("timeout") ||
    t.includes("timed out") ||
    t.includes("deadline exceeded");
  if (!traff) return null;

  return svar(
    "timeout",
    { sv: "Svaret kom inte i tid", en: "The response did not arrive in time" },
    {
      sv: "Anropet avbröts innan motparten hann svara. Enstaka fall är normalt när backenden just vaknat; återkommer det för samma kund är det volymen eller en långsam källa som är orsaken.",
      en: "The call was cut off before the other end responded. Isolated cases are normal right after the backend wakes; if it recurs for the same customer, the cause is volume or a slow upstream source."
    },
    text
  );
};

/** Motparten gick inte att nå alls. */
const anslutning: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    t.includes("apiconnectionerror") ||
    t.includes("connectionerror") ||
    t.includes("connection refused") ||
    t.includes("connection reset") ||
    t.includes("getaddrinfo") ||
    t.includes("name or service not known") ||
    (t.includes("ssl") && t.includes("handshake"));
  if (!traff) return null;

  return svar(
    "anslutning",
    { sv: "Tjänsten gick inte att nå", en: "The service could not be reached" },
    {
      sv: "Ingen förbindelse kom upp mot motparten — den är nere, blockerad av nätverket eller adresserad fel. Kontrollera att adressen i miljövariablerna stämmer och att tjänsten svarar.",
      en: "No connection could be established with the other end — it is down, blocked by the network, or addressed incorrectly. Verify the address in the environment variables and that the service responds."
    },
    text
  );
};

/** Utgående mail. Plattformen blockerar SMTP — det är mätt, inte gissat. */
const mail: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    t.includes("smtp") ||
    t.includes("smtplib") ||
    t.includes("sendmail") ||
    (t.includes("mail") && t.includes("relay"));
  if (!traff) return null;

  return svar(
    "mail",
    { sv: "Mejlet kunde inte skickas", en: "The email could not be sent" },
    {
      sv: "Den utgående mailvägen svarade inte. Plattformen som backenden kör på blockerar utgående SMTP, så det är en spärr i infrastrukturen och inte ett fel i inloggningsuppgifterna.",
      en: "The outbound mail path did not respond. The platform the backend runs on blocks outbound SMTP, so this is an infrastructure restriction rather than a credentials problem."
    },
    text
  );
};

/** Databasen. Skiljer på "nere" och "schemat stämmer inte". */
const databas: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    t.includes("asyncpg") ||
    t.includes("psycopg") ||
    t.includes("undefinedcolumn") ||
    t.includes("undefinedtable") ||
    (t.includes("relation") && t.includes("does not exist")) ||
    t.includes("duplicate key") ||
    t.includes("operationalerror") ||
    t.includes("integrityerror");
  if (!traff) return null;

  const schemafel =
    t.includes("undefinedcolumn") ||
    t.includes("undefinedtable") ||
    (t.includes("relation") && t.includes("does not exist"));

  if (schemafel) {
    return svar(
      "databas",
      {
        sv: "Databasen saknar en tabell eller kolumn som koden väntar sig",
        en: "The database is missing a table or column the code expects"
      },
      {
        sv: "Koden är nyare än databasen — en migration har inte körts i den här miljön. Kör migrationerna mot miljön; felet försvinner inte av sig självt.",
        en: "The code is ahead of the database — a migration has not been applied in this environment. Run the migrations against it; this will not resolve on its own."
      },
      text
    );
  }

  return svar(
    "databas",
    { sv: "Databasen svarade med ett fel", en: "The database returned an error" },
    {
      sv: "Frågan gick fram men avvisades, eller så tappades förbindelsen. Enstaka fall är oftast en förbindelse som återanvänts efter att databasen skalat om; ett mönster betyder att skrivningen i sig är felaktig.",
      en: "The query reached the database but was rejected, or the connection dropped. Isolated cases are usually a reused connection after the database scaled; a pattern means the write itself is wrong."
    },
    text
  );
};

/** Leverantören är överbelastad — vårt fel finns inte, väntan är åtgärden. */
const overbelastad: Tolkare = (text) => {
  const kod = statuskod(text);
  const t = text.toLowerCase();
  const traff = kod === 529 || kod === 503 || t.includes("overloaded") || t.includes("unavailable");
  if (!traff) return null;

  const lev = leverantor(text);

  return svar(
    "overbelastad",
    {
      sv: `${lev ?? "Leverantören"} är tillfälligt överbelastad`,
      en: `${lev ?? "The provider"} is temporarily overloaded`
    },
    {
      sv: "Tjänsten tar inte emot fler anrop just nu. Det går över av sig självt — ingen åtgärd behövs om det inte håller i sig över timmar.",
      en: "The service is not accepting further requests right now. This clears on its own — no action is needed unless it persists for hours."
    },
    text
  );
};

/** Indata som inte höll formen. */
const indata: Tolkare = (text) => {
  const t = text.toLowerCase();
  const traff =
    t.includes("validationerror") ||
    t.includes("pydantic") ||
    statuskod(text) === 422 ||
    t.includes("unprocessable");
  if (!traff) return null;

  return svar(
    "indata",
    { sv: "Uppgifterna hade fel format", en: "The submitted data had the wrong format" },
    {
      sv: "Ett fält saknades eller innehöll något annat än väntat, så anropet avvisades innan det utfördes. Ingen data ändrades.",
      en: "A field was missing or contained something other than expected, so the call was rejected before it ran. No data was changed."
    },
    text
  );
};

/** Serverfel i vår egen backend. */
const internt: Tolkare = (text) => {
  const kod = statuskod(text);
  if (kod !== 500 && kod !== 502) return null;

  return svar(
    "internt",
    { sv: "Ett internt fel avbröt anropet", en: "An internal error interrupted the call" },
    {
      sv: "Backenden fällde anropet innan den hann svara. De tekniska detaljerna nedan pekar ut raden — den här behöver rättas i koden.",
      en: "The backend failed the call before it could respond. The technical detail below points at the line — this one needs a code fix."
    },
    text
  );
};

/**
 * ORDNINGEN ÄR INTE GODTYCKLIG. Ett kvotfel bär ofta både 429 och ordet
 * "unavailable", och en modell som inte finns ger 404 tillsammans med
 * "not found" — ett brett mönster som prövas för tidigt skulle svälja de
 * smala. Smalast först, bredast sist.
 */
const TOLKARE: Tolkare[] = [
  kvot,
  modellSaknas,
  // Mail FÖRE behörighet: `SMTPAuthenticationError` innehåller ordet
  // "authenticationerror" och fångades annars som en avvisad API-nyckel — en
  // tolkning som skickar felsökningen till fel leverantör.
  mail,
  behorighet,
  databas,
  indata,
  timeout,
  anslutning,
  overbelastad,
  internt
];

/**
 * Tolkar ett händelsemeddelande. Matchar inget mönster returneras den städade
 * råtexten med `tolkad: false` — vyn visar den då som den är, utan att hitta på
 * en förklaring den inte har täckning för.
 */
export function tolkaHandelse(meddelande: string): Handelsetolkning {
  const text = meddelande ?? "";
  for (const tolkare of TOLKARE) {
    const traff = tolkare(text);
    if (traff) return traff;
  }

  const typ = undantagstyp(text);
  const stadad = stada(text);
  const kant = TYPNAMN[typ];

  // Känd undantagstyp: typnamnet blir rubrik och det städade meddelandet
  // förklaring. Okänd: meddelandet är allt vi har, och det får stå ensamt.
  return {
    kategori: "okant",
    rubrik: kant ?? { sv: stadad, en: stadad },
    forklaring: kant ? { sv: stadad, en: stadad } : null,
    teknisk: text,
    tolkad: false
  };
}

/** Nivåernas namn. `level`-strängen ur databasen är inte en etikett för en läsare. */
export const NIVANAMN: Record<string, Localized> = {
  error: { sv: "Fel", en: "Error" },
  warning: { sv: "Varning", en: "Warning" },
  info: { sv: "Info", en: "Info" }
};

/**
 * Källnamn. `source` är ett tekniskt id (`admin.kunddata`, `tenant:soul`) och
 * läses av en människa som letar efter var något gick fel — punkt och kolon
 * gör inte det jobbet.
 */
const KALLNAMN: Record<string, Localized> = {
  api: { sv: "API", en: "API" },
  db: { sv: "Databas", en: "Database" },
  admin: { sv: "Adminytan", en: "Admin area" },
  "admin.kunddata": { sv: "Kunduppgifter", en: "Customer records" },
  "admin.profil": { sv: "Agentprofil", en: "Agent profile" },
  "admin.instruktioner": { sv: "Agentinstruktioner", en: "Agent instructions" },
  "tenant-edit": { sv: "Kundinställningar", en: "Customer settings" },
  "tenant:soul": { sv: "Agentens tonläge", en: "Agent tone of voice" },
  "tenant:product_marketing": { sv: "Produktunderlag", en: "Product material" },
  "customer:memory": { sv: "Kundminne", en: "Customer memory" },
  "onboarding-agent": { sv: "Uppstartsagenten", en: "Onboarding agent" }
};

export function kallnamn(source: string): Localized {
  const kant = KALLNAMN[source];
  if (kant) return kant;
  // Okänd källa: visa id:t som det är. Ett påhittat vänligt namn för en källa
  // vi inte känner till hade dolt vilken kod som faktiskt loggade raden.
  return { sv: source, en: source };
}
