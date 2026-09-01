/**
 * OAuth2 Authorization Code Grant mot Skatteverket — BankID-inloggningen.
 *
 * Endpointerna är LÄSTA ur Skatteverkets dokumentation, inte gissade:
 * https://www.skatteverket.se/omoss/digitalasamarbeten/utvecklingavapierochoppnadata/sakerhetochapier/authorizationcodegrantacg
 *
 *   authorize  GET  https://peroauth2[.test].skatteverket.se/oauth2/v1/per/authorize
 *   token      POST https://peroauth2[.test].skatteverket.se/oauth2/v1/per/token
 *
 * `per` är e-legitimationsvarianten (BankID). `org`-varianten på
 * orgoauth2.skatteverket.se kräver ett organisationscertifikat från Expisoft
 * och en egen ombudsansökan — den bygger vi inte nu.
 *
 * ## Varför backenden inte kan göra det här själv
 *
 * Det finns ingen client_credentials-variant av Beskattningsengagemang. En
 * riktig människa måste legitimera sig, och först då gäller tokenen — för det
 * bolag hen är huvudman för eller företräder. Det är därför uppslaget bor i en
 * webbläsarsession och inte i ett bakgrundsjobb.
 *
 * ## Vad som är konfiguration och varför
 *
 * `scope` är API-specifikt och står inte i den publika dokumentationen — det
 * kommer med nycklarna. Det är därför en env-var utan default: ett gissat
 * scope hade gett ett flöde som ser färdigt ut och avvisas vid första riktiga
 * inloggningen, alltså exakt den sortens fel som är dyrast att hitta.
 *
 * ## Två nyckelpar, inte ett
 *
 * OAuth2-klientens `client_id`/`client_secret` används mot auktorisations-
 * servern. API-anropet självt kräver dessutom `Client_Id`/`Client_Secret` som
 * HTTP-huvuden (tjänstebeskrivningen §5.5). Skatteverket kallar de senare
 * "APIgw client ID" och delar i praktiken ut dem tillsammans. Koden håller dem
 * isär ändå: samma värden idag betyder inte samma värden imorgon, och en
 * hopslagning är svår att ta isär när den väl gjorts.
 */

export const SKV_STATE_COOKIE = "skv_oauth_state";
export const SKV_RETUR_COOKIE = "skv_oauth_retur";
export const SKV_TOKEN_COOKIE = "skv_access_token";

/** Access tokens lever 3600 sekunder enligt Skatteverket. Cookien får aldrig
 *  leva längre än tokenen den bär — en cookie som överlever sitt innehåll gör
 *  att gränssnittet visar "inloggad" medan varje uppslag svarar 401. */
export const SKV_TOKEN_LIVSLANGD_SEKUNDER = 3600;

/** Kort liv: staten ska bara överleva resan till Skatteverket och tillbaka. */
export const SKV_STATE_LIVSLANGD_SEKUNDER = 15 * 60;

type Miljo = "test" | "produktion";

function miljo(): Miljo {
  // Testmiljön är default, med flit — samma val som backendens
  // SKATTEVERKET_API_BAS_URL. En felriktad produktionsnyckel mot testmiljön
  // svarar 401; en testnyckel mot produktion hade slagit mot riktiga
  // beskattningsuppgifter.
  return process.env.SKATTEVERKET_MILJO === "produktion" ? "produktion" : "test";
}

function authServerBas(): string {
  return miljo() === "produktion"
    ? "https://peroauth2.skatteverket.se"
    : "https://peroauth2.test.skatteverket.se";
}

export function authorizeUrl(params: { state: string; redirectUri: string }): string {
  const url = new URL(`${authServerBas()}/oauth2/v1/per/authorize`);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", kravEnv("SKATTEVERKET_CLIENT_ID"));
  url.searchParams.set("scope", kravEnv("SKATTEVERKET_SCOPE"));
  url.searchParams.set("redirect_uri", params.redirectUri);
  url.searchParams.set("state", params.state);
  return url.toString();
}

export function tokenUrl(): string {
  return `${authServerBas()}/oauth2/v1/per/token`;
}

/**
 * Redirect-URI:n MÅSTE vara exakt den som registrerats hos Skatteverket, och
 * exakt densamma i båda stegen — auktorisationsservern jämför dem.
 *
 * Den härleds därför INTE ur inkommande request. En angripare som styr
 * `Host`-huvudet hade annars kunnat få koden skickad till sin egen domän.
 * Env-varen är sanningen; matchar den inte det som står i registreringen
 * faller flödet hos Skatteverket, vilket är rätt ställe att falla på.
 */
export function redirectUri(): string {
  return kravEnv("SKATTEVERKET_REDIRECT_URI");
}

export class SkatteverketKonfigFel extends Error {
  constructor(readonly envVar: string) {
    super(
      `${envVar} är inte satt. BankID-inloggningen mot Skatteverket kan inte ` +
        `starta utan den. Värdena delas ut av Skatteverket efter ansökan — se ` +
        `Skatteverket-avsnittet i DEPLOY.md.`
    );
    this.name = "SkatteverketKonfigFel";
  }
}

function kravEnv(namn: string): string {
  const varde = process.env[namn];
  if (!varde) throw new SkatteverketKonfigFel(namn);
  return varde;
}

/** Om flödet över huvud taget är påslaget. Läser utan att kasta, så att ett
 *  gränssnitt kan dölja knappen i stället för att visa en trasig sådan. */
export function arKonfigurerad(): boolean {
  return Boolean(
    process.env.SKATTEVERKET_CLIENT_ID &&
      process.env.SKATTEVERKET_CLIENT_SECRET &&
      process.env.SKATTEVERKET_SCOPE &&
      process.env.SKATTEVERKET_REDIRECT_URI
  );
}

export type TokenSvar = {
  access_token: string;
  expires_in?: number;
  refresh_token?: string;
  token_type?: string;
};

/**
 * Växlar auktorisationskoden mot en access token.
 *
 * Kroppen är form-urlencoded, inte JSON — Skatteverket anger
 * `application/x-www-form-urlencoded;charset=UTF-8`, och en JSON-kropp avvisas.
 */
export async function vaxlaKodMotToken(code: string): Promise<TokenSvar> {
  const kropp = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: kravEnv("SKATTEVERKET_CLIENT_ID"),
    client_secret: kravEnv("SKATTEVERKET_CLIENT_SECRET"),
    code,
    redirect_uri: redirectUri()
  });

  const svar = await fetch(tokenUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: kropp.toString(),
    cache: "no-store"
  });

  if (!svar.ok) {
    // Kroppen bär Skatteverkets egen förklaring (fel redirect_uri, utgången
    // kod, okänt scope) och är det som gör felet åtgärdbart. Klipps så att ett
    // gateway-fel inte fyller loggen med HTML.
    const text = (await svar.text()).slice(0, 300);
    throw new Error(`Skatteverket avvisade kodväxlingen (${svar.status}): ${text}`);
  }

  // .catch: ett 200 med tom eller icke-JSON-kropp (gateway, dödad funktion)
  // ska ge vårt begripliga fel nedan, inte "Unexpected end of JSON input"
  // (INV-API-001).
  const data = (await svar.json().catch(() => null)) as TokenSvar | null;
  if (!data?.access_token) {
    throw new Error("Skatteverket svarade utan access_token.");
  }
  return data;
}

/**
 * Var användaren ska hamna efter inloggningen.
 *
 * ÖPPEN REDIRECT-SPÄRR: bara relativa sökvägar släpps igenom. Utan den kunde
 * `?retur=https://ondskan.example` få vår egen domän att skicka en nyss
 * legitimerad användare vidare till en angripares sida. `//` fångas separat —
 * `//example.com` är en protokollrelativ ABSOLUT url som annars ser relativ ut.
 */
export function sakerReturvag(rat: string | null | undefined, standard = "/dashboard/bokforing"): string {
  const varde = (rat ?? "").trim();
  if (!varde.startsWith("/") || varde.startsWith("//")) return standard;
  return varde;
}
