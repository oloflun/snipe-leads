/**
 * Vilken modell Email Studio kör mot — ren funktion över miljövariablerna.
 *
 * ## Varför den ligger här och inte i routen
 *
 * Valet är den del av Email Studio som går sönder tyst: fel ordning, en
 * platshållare som räknas som nyckel eller en DeepSeek-nyckel i fel miljö ger
 * alla ett svar som ser friskt ut. Som ren funktion över ett env-objekt går
 * varje sådant utfall att testa utan Next, utan nätverk och utan att röra
 * process.env (lib/llm/modellval.test.ts).
 *
 * ## Ordningen (avsiktlig)
 *
 *   1. OPENAI_API_KEY — vinner när den finns, så att ett byte tillbaka inte
 *      kräver en kodändring.
 *   2. GOOGLE_SERVICE_ACCOUNT_JSON — Vertex AI. Google tog bort Cloud-krediterna
 *      från AI Studio 2026-09, och backenden gick över till Vertex samma dag
 *      (HANDOFF-2026-09-12-VERTEX-AI.md). Samma variabel som backenden läser.
 *   3. GEMINI_API_KEY — AI Studio. Numera gratisnivån, 20 anrop per dygn:
 *      kvar som reserv, inte som drift.
 *   4. DEEPSEEK_API_KEY — bara där ingen riktig kunddata finns, se nedan.
 *
 * Saknas alla simulerar routen och säger det i svaret.
 *
 * Filen har inga runtime-importer med flit: den körs direkt av `node --test`.
 */

export type ServiceAccount = {
  client_email: string;
  private_key: string;
  private_key_id?: string;
  project_id: string;
  token_uri: string;
};

export type Modellval =
  | { provider: "openai"; apiKey: string; namn: string }
  | { provider: "vertex"; serviceAccount: ServiceAccount; region: string; baseURL: string; namn: string }
  | { provider: "gemini"; apiKey: string; baseURL: string; namn: string }
  | { provider: "deepseek"; apiKey: string; baseURL: string; namn: string };

type Miljo = Record<string, string | undefined>;

/** Samma OpenAI-kompatibla endpoint som snajp-support/app/agent/llm.py. */
export const GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/";
/** Samma base_url som backenden. Två adresser till samma leverantör är två saker att byta. */
export const DEEPSEEK_BASE_URL = "https://api.deepseek.com";
/** Default i `Settings.google_cloud_region`. */
export const STANDARDREGION = "europe-west1";
/** Google-tokenendpointen när JSON-filen saknar `token_uri` — google-auths default. */
const STANDARD_TOKEN_URI = "https://oauth2.googleapis.com/token";

/**
 * Miljöer som bär eller speglar riktig kunddata. Ordagrant `MILJOER_MED_KUNDDATA`
 * i snajp-support/app/config.py — development står med eftersom den är en
 * spegel av produktionen (CLAUDE.md).
 */
export const MILJOER_MED_KUNDDATA = ["main", "production", "prod", "development", "dev"] as const;

/** `_LOOPBACK` i config.py. */
const LOOPBACK = ["localhost", "127.0.0.1", "::1", "[::1]", "host.docker.internal"];

/** En platshållare är inte en nyckel. Samma villkor som backendens `_looks_real`. */
export function dugerSomNyckel(key: string | undefined): boolean {
  return Boolean(key) && key!.length >= 20 && !key!.includes("...") && !key!.includes("din-");
}

/**
 * Spegel av `_ar_loopback`: värden tas efter SISTA `@`, så att ett lösenord
 * med snabel-a inte får en produktionsdatabas att se ut som localhost.
 */
export function arLoopback(databaseUrl: string): boolean {
  const utanSchema = String(databaseUrl || "").split("://").slice(1).join("://") || String(databaseUrl || "");
  const myndighet = utanSchema.split("/", 1)[0];
  const efterSnabela = myndighet.slice(myndighet.lastIndexOf("@") + 1);
  const kolon = efterSnabela.lastIndexOf(":");
  const vard = (kolon >= 0 ? efterSnabela.slice(0, kolon) : efterSnabela).trim().toLowerCase();
  return LOOPBACK.includes(vard);
}

/**
 * Spegel av `Settings.har_riktig_kunddata()`: ett känt kunddatamiljönamn, ELLER
 * en databas som inte ligger på loopback.
 *
 * Varför inte bara NODE_ENV, som routen läste förut: NODE_ENV säger att bygget
 * är optimerat, inte var det kör. Och varför inte bara miljönamnet: den
 * bortglömda Render-stacken saknade RAILWAY_ENVIRONMENT_NAME och körde DeepSeek
 * mot en riktig Postgres (se config.py). Databasen avgör, inte värdnamnet.
 *
 * Båda miljönamnsvariablerna prövas — Python läser ENVIRONMENT först,
 * lib/miljo.ts RAILWAY_ENVIRONMENT_NAME först. För en dataskyddsspärr räcker
 * det att EN av dem pekar på kunddata.
 */
export function harRiktigKunddata(env: Miljo): boolean {
  const namn = [env.ENVIRONMENT, env.RAILWAY_ENVIRONMENT_NAME].map((v) => (v || "").trim().toLowerCase());
  if (namn.some((n) => (MILJOER_MED_KUNDDATA as readonly string[]).includes(n))) return true;
  const db = env.DATABASE_URL || "";
  return Boolean(db) && !arLoopback(db);
}

/**
 * Tolkar GOOGLE_SERVICE_ACCOUNT_JSON. null = oanvändbar (tom, platshållare,
 * trasig JSON, fält saknas) — då provas nästa leverantör i ordningen i stället
 * för att varje anrop faller på tokenväxlingen.
 */
export function lasServiceAccount(json: string | undefined): ServiceAccount | null {
  if (!json || !json.trim()) return null;
  let info: Record<string, unknown>;
  try {
    info = JSON.parse(json);
  } catch {
    return null;
  }
  if (!info || typeof info !== "object") return null;
  const { client_email, private_key, project_id, private_key_id, token_uri } = info;
  if (typeof client_email !== "string" || !client_email) return null;
  if (typeof private_key !== "string" || !private_key.includes("PRIVATE KEY")) return null;
  if (typeof project_id !== "string" || !project_id) return null;
  return {
    client_email,
    // En JSON som klistrats in genom ett skal kan bära bokstavliga "\n" i
    // nyckeln i stället för radbrytningar. crypto läser inte den formen.
    private_key: private_key.includes("\\n") ? private_key.replace(/\\n/g, "\n") : private_key,
    project_id,
    private_key_id: typeof private_key_id === "string" ? private_key_id : undefined,
    token_uri: typeof token_uri === "string" && token_uri ? token_uri : STANDARD_TOKEN_URI
  };
}

/** Spegel av `_vertex_base_url` i llm.py. */
export function vertexBaseUrl(projekt: string, region: string): string {
  return (
    `https://${region}-aiplatform.googleapis.com/v1beta1/` +
    `projects/${projekt}/locations/${region}/endpoints/openapi/`
  );
}

/**
 * MODEL, inte EMAIL_STUDIO_MODEL: samma variabelnamn som backenden, så att en
 * delad Railway-variabel styr båda. Men bara ett gemini-namn godtas — `MODEL`
 * stod en gång kvar på "deepseek-v4-flash" efter ett providerbyte och gav 404
 * på varje anrop (MODELLFAMILJER i config.py). Samma vakt som discovery.py.
 */
/**
 * Modellnamnet som Vertex openapi-endpoint vill ha: `google/<modell>`.
 *
 * Ett bart `gemini-2.5-flash` mot `endpoints/openapi/` svarar 400 "Malformed
 * publisher model … expected '<publisher>/<model>'" — uppmätt 2026-09-14 mot
 * båda miljöernas service account. Spegel av `vertex_modellnamn` i
 * snajp-support/app/agent/llm.py; ändra båda om du ändrar den ena. Ett namn
 * som redan bär en publisher lämnas orört.
 */
export function vertexModellnamn(namn: string): string {
  const rent = (namn || "").trim();
  if (!rent || rent.includes("/")) return rent;
  return `google/${rent}`;
}

function geminiModell(env: Miljo, standard: string): string {
  const model = (env.MODEL || "").trim();
  return model.toLowerCase().startsWith("gemini") ? model : standard;
}

export function valjModell(env: Miljo): Modellval | null {
  const openaiKey = env.OPENAI_API_KEY || "";
  if (dugerSomNyckel(openaiKey)) {
    return { provider: "openai", apiKey: openaiKey, namn: env.EMAIL_STUDIO_MODEL || "gpt-4o-mini" };
  }

  const serviceAccount = lasServiceAccount(env.GOOGLE_SERVICE_ACCOUNT_JSON);
  if (serviceAccount) {
    const region = (env.GOOGLE_CLOUD_REGION || "").trim() || STANDARDREGION;
    return {
      provider: "vertex",
      serviceAccount,
      region,
      baseURL: vertexBaseUrl(serviceAccount.project_id, region),
      // Backendens modell i båda miljöerna sedan 2026-09-12 — med publisher,
      // eftersom routen anropar openapi-endpointen (se vertexModellnamn).
      namn: vertexModellnamn(geminiModell(env, "gemini-2.5-flash"))
    };
  }

  const geminiKey = env.GEMINI_API_KEY || "";
  if (dugerSomNyckel(geminiKey)) {
    return { provider: "gemini", apiKey: geminiKey, baseURL: GEMINI_BASE_URL, namn: geminiModell(env, "gemini-2.5-flash") };
  }

  const deepseekKey = env.DEEPSEEK_API_KEY || "";
  // DeepSeek behandlar prompten i Kina, och det som postas hit är kundens
  // utkast med namn och bolagsuppgifter. Beslutet 2026-08-24 (CLAUDE.md)
  // förbjuder det mot riktig kunddata — i main OCH i development, som speglar
  // produktionen. NODE_ENV står kvar som extra bälte: ett produktionsbygge
  // utan känt miljönamn och utan DATABASE_URL är fortfarande inte lokal
  // utveckling mot syntetiska exempel.
  if (dugerSomNyckel(deepseekKey) && !harRiktigKunddata(env) && env.NODE_ENV !== "production") {
    return { provider: "deepseek", apiKey: deepseekKey, baseURL: DEEPSEEK_BASE_URL, namn: env.EMAIL_STUDIO_MODEL || "deepseek-chat" };
  }

  return null;
}
