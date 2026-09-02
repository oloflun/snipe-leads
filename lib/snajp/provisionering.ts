import "server-only";

import { sqlAsUser } from "@/lib/db";
import type { BusinessContext, Workspace } from "@/lib/database.types";
import { sattStandardinstallningar } from "@/lib/snajp/standard";
import { skapaKundtenant, utfardaTenantnyckel } from "@/lib/snajp/testtenant";

/**
 * Arbetsytan kopplas till en egen backend-tenant AUTOMATISKT — i uppstarten,
 * och i efterhand för den som redan registrerat sig.
 *
 * ## Varför den finns
 *
 * `lib/actions/onboarding.ts` kopplade bara testarbetsytor. En riktig kund fick
 * `workspaces.slug = null`, och `requireSnajpTenant()` svarade 409 på varje
 * inloggad yta: översikten fick streck i stället för siffror, `/settings/soul`
 * sa "Kunde inte hämta röstdokumentet" och `/settings/leads` visade ett
 * meddelande om databaskolumner. Kunden kunde alltså inte använda produkten
 * förrän någon av oss körde `scripts/onboard_tenant.py` för hand.
 *
 * ## Varför det är säkert att göra automatiskt
 *
 * Kopplingen går genom `link_workspace_tenant` (migration 061), som gör tre
 * kontroller appen inte kan kringgå: sluggen måste vara `kund-<8>`, arbetsytan
 * läses ur anroparens egen profil, och den måste sakna slug. En parallell
 * begäran som hinner först vinner därför, och den andra får `false` — inte en
 * andra tenant med halva kundens data. Därför läser vi om nyckeln i stället för
 * att kasta när kopplingen nekas.
 *
 * ## Vad den INTE gör
 *
 * Ingen configfil i `lib/tenants/` skapas. Den styr den PUBLIKA chatten på
 * kundens egen domän — logotyp, palett, startfrågor — och den ska inte gissas
 * fram. Se TENANTS.md steg 4. Kundens inloggade arbetsyta fungerar direkt;
 * kundens varumärkessida gör det när en människa satt den.
 */

export type Kundtenant = { slug: string; apiKey: string };

/**
 * De fyra fälten standardinställningarna härleds ur.
 *
 * En delmängd av `business_contexts` och inte hela raden: uppstarten skickar en
 * `Insert` och inloggningsvägen en `Row`, och en gemensam delmängd låter båda
 * passera utan en cast. `industries`, `geography` och `contact_roles` ägs av
 * leads-agentens ICP och läses aldrig här — se lib/actions/affarskontext.ts.
 */
export type Kundunderlag = Pick<
  BusinessContext,
  "product" | "target_audience" | "offer" | "cta"
>;

/**
 * Kallstartstaket för läkningsvägarna.
 *
 * `requireSnajpTenant()` körs på VARJE inloggat anrop. Utan taket hade en
 * sovande backend betytt ett 60-sekundersförsök per anrop, alltså en arbetsyta
 * som hänger i stället för att svara — värre än felet vi lagar. Uppstarten
 * använder inte det här taket: där är väntan hela poängen.
 */
const LAKNINGENS_TIMEOUT_MS = 15_000;

/**
 * Hur länge ett misslyckat försök håller nästa borta, per arbetsyta.
 *
 * Räknat mot vad läkningen faktiskt är: ett engångsjobb som får ta en minut
 * extra. Att försöka om vid varje sidladdning hade lagt 15 sekunder på varje
 * anrop så länge backenden var nere.
 */
const OMFORSOK_MS = 60_000;

const senasteForsok = new Map<string, number>();

function farForsokaIgen(workspaceId: string): boolean {
  const senast = senasteForsok.get(workspaceId);
  return senast === undefined || Date.now() - senast > OMFORSOK_MS;
}

async function nyckelForArbetsytan(userId: string): Promise<string | undefined> {
  const rows = await sqlAsUser<{ nyckel: string | null }>(
    userId,
    "select public.tenant_api_key_for_current_workspace() as nyckel"
  );
  return rows[0]?.nyckel ?? undefined;
}

/**
 * Ser till att arbetsytan har en egen tenant och nyckel, och fyller de tomma
 * inställningarna ur kundens underlag.
 *
 * Returnerar `null` när det inte gick — anroparen ska då falla tillbaka på sitt
 * vanliga fel, inte kasta ett nytt. Ett halvfärdigt tillstånd är läkbart vid
 * nästa sidladdning; ett kastat undantag mitt i en inloggning är det inte.
 */
export async function sakerstallKundtenant(
  userId: string,
  workspace: Workspace,
  businessContext: Kundunderlag | null,
  /** `true` i uppstarten, där väntan på en kallstartande backend är poängen. */
  tolamodigt = false
): Promise<Kundtenant | null> {
  if (workspace.slug) {
    // Redan kopplad. Den här funktionen kopplar; den flyttar aldrig en
    // arbetsyta som redan pekar på en kund.
    return null;
  }

  if (!tolamodigt && !farForsokaIgen(workspace.id)) {
    return null;
  }
  senasteForsok.set(workspace.id, Date.now());

  let tenant;
  try {
    tenant = await skapaKundtenant(
      workspace.id,
      workspace.name ?? "Ny kund",
      tolamodigt ? undefined : LAKNINGENS_TIMEOUT_MS
    );
  } catch (error) {
    console.error("[provisionering] kunde inte utfärda tenant:", error);
    return null;
  }

  let kopplad = false;
  try {
    const rader = await sqlAsUser<{ ok: boolean }>(
      userId,
      "select public.link_workspace_tenant($1, $2, $3) as ok",
      [tenant.slug, tenant.tenantId, tenant.apiKey]
    );
    kopplad = Boolean(rader[0]?.ok);
  } catch (error) {
    console.error("[provisionering] link_workspace_tenant föll:", error);
    return null;
  }

  // Nekad koppling betyder nästan alltid att en parallell begäran hann före.
  // Nyckeln som redan står i tabellen är då den rätta.
  const apiKey = kopplad ? tenant.apiKey : await nyckelForArbetsytan(userId);
  if (!apiKey) {
    return null;
  }

  await fyllStandardinstallningar(apiKey, workspace, businessContext);

  return { slug: tenant.slug, apiKey };
}

/**
 * Standardinställningarna, körda mot en färdig nyckel.
 *
 * Egen export därför att den ska gå att köra på en arbetsyta som REDAN har en
 * tenant — kunder som kopplades före den här koden har en fungerande nyckel men
 * tomma inställningar, och de ska inte behöva registrera sig på nytt för att få
 * dem. Funktionen skriver bara tomma fält (se lib/snajp/standard.ts).
 */
export async function fyllStandardinstallningar(
  apiKey: string,
  workspace: Workspace,
  businessContext: Kundunderlag | null
): Promise<void> {
  if (!businessContext) {
    // Inget underlag att härleda ur. Att skriva defaultarna ändå hade gett
    // kunden ett röstdokument och ett ICP innan de sagt ett ord om sin
    // verksamhet — vilket är precis den sortens tysta ifyllnad som gör att man
    // slutar lita på det som står i fälten.
    return;
  }

  const utfall = await sattStandardinstallningar(apiKey, {
    produkt: businessContext.product ?? "",
    malgrupp: businessContext.target_audience,
    erbjudande: businessContext.offer,
    nastaSteg: businessContext.cta,
    namn: workspace.name
  });

  if (utfall.produktbeskrivning || utfall.rostdokument || utfall.icp) {
    console.info(
      `[provisionering] standardinställningar för ${workspace.slug ?? workspace.id}:`,
      utfall
    );
  }
}

/**
 * Kunder som kopplades FÖRE den här koden har en fungerande nyckel men tomma
 * inställningar. De ska inte behöva registrera sig på nytt för att få dem.
 *
 * Två spärrar gör att det här får ligga i inloggningsvägen:
 *
 *  1. `redanKontrollerade` — en gång per tenant och processlivstid. Efter det
 *     kostar en sidladdning ingenting alls.
 *  2. Anropet väntas INTE in. `sattStandardinstallningar` skriver bara tomma
 *     fält, så ett avbrutet försök är ofarligt och görs om vid nästa kallstart.
 *     Att lägga tre backend-anrop i vägen för varje inloggning hade gjort
 *     inloggningen långsammare för alla, för en sak som bara gäller en gång.
 *
 * Gäller ENBART kundens egen session. Under ett adminbesök hör
 * `business_contexts` till ADMINENS arbetsyta medan nyckeln pekar på kunden
 * (se lib/actions/affarskontext.ts) — en ifyllnad därifrån hade skrivit Snajps
 * produkttext i kundens agent.
 */
const redanKontrollerade = new Set<string>();

export function fyllStandardinstallningarEnGang(
  slug: string,
  apiKey: string,
  workspace: Workspace,
  businessContext: Kundunderlag | null
): void {
  if (!businessContext || redanKontrollerade.has(slug)) {
    return;
  }
  redanKontrollerade.add(slug);
  void fyllStandardinstallningar(apiKey, workspace, businessContext).catch((error) => {
    console.error(`[provisionering] standardinställningar för ${slug} föll:`, error);
  });
}

/**
 * Nyckeln för en NAMNGIVEN kund, utfärdad på plats.
 *
 * Bara plattformsadmin når hit — `save_admin_tenant_key` (migration 061) gör om
 * kontrollen i databasen, av samma skäl som `tenant_api_key_for_admin`:
 * funktionen tar en parameter och vore utan villkoret en skrivväg mot vilken
 * kunds nyckel som helst.
 *
 * Varför en NY nyckel och inte den befintliga: backenden lämnar aldrig tillbaka
 * en utfärdad nyckel, bara sha256-hashen sparas. För en kund som lades upp före
 * migration 040 finns alltså ingenting att läsa — vare sig en rad i
 * `workspace_tenant_keys` eller en miljövariabel i den här miljön. `ss_api_keys`
 * är additiv, så den gamla nyckeln fortsätter gälla; ingenting roteras.
 */
export async function sakerstallAdminnyckel(
  userId: string,
  slug: string,
  namn: string
): Promise<string | null> {
  /**
   * Kundens BEFINTLIGA namn, inte ett vi hittar på.
   *
   * Backendens `create_tenant` är en upsert som skriver `name = excluded.name`.
   * Att utfärda en nyckel skulle alltså DÖPA OM kunden: ett anrop med sluggen
   * som namn gör "Livrustning AB" till "livrustning", och ett anrop med
   * arbetsytans namn gör "Snajp" till "Snajp Admin workspace" (de två skiljer
   * sig redan i dag — se lib/tenants/snajp.ts). Namnet läses därför ur
   * `ss_tenants` och skickas tillbaka oförändrat.
   *
   * Läsningen går utan `app.tenant_id`, vilket policyn `tenant_lookup` tillåter
   * — samma väg backendens egen tenant-uppräkning tar.
   */
  let tenantNamn = namn;
  try {
    const rader = await sqlAsUser<{ name: string | null }>(
      userId,
      "select name from public.ss_tenants where slug = $1 limit 1",
      [slug]
    );
    tenantNamn = rader[0]?.name?.trim() || namn;
  } catch (error) {
    console.error(`[provisionering] kunde inte läsa kundnamnet för ${slug}:`, error);
  }

  if (!farForsokaIgen(slug)) {
    return null;
  }
  senasteForsok.set(slug, Date.now());

  let tenant;
  try {
    tenant = await utfardaTenantnyckel(slug, tenantNamn, LAKNINGENS_TIMEOUT_MS);
  } catch (error) {
    console.error(`[provisionering] kunde inte utfärda nyckel för ${slug}:`, error);
    return null;
  }

  try {
    const rader = await sqlAsUser<{ ok: boolean }>(
      userId,
      "select public.save_admin_tenant_key($1, $2, $3) as ok",
      [slug, tenant.tenantId, tenant.apiKey]
    );
    if (!rader[0]?.ok) {
      // Ingen arbetsyta bär sluggen, eller så pekar den på en annan tenant.
      // Nyckeln är utfärdad men sparas inte — den gäller ändå för det här
      // anropet, och nästa besök utfärdar en ny. Att spara en nyckel mot fel
      // tenant hade tyst öppnat fel kunds inkorg.
      console.warn(`[provisionering] nyckeln för ${slug} kunde inte sparas.`);
    }
  } catch (error) {
    console.error(`[provisionering] save_admin_tenant_key föll för ${slug}:`, error);
  }

  return tenant.apiKey;
}
