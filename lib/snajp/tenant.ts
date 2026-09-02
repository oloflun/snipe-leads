import { sqlAsUser } from "@/lib/db";
import { getWorkspaceContext } from "@/lib/workspace";
import { getTenant } from "@/lib/tenants";
import { DEMO_TENANT_SLUG, aktivVy } from "@/lib/vy";

/**
 * Arbetsytans egen backend-nyckel, för tenants utan configfil.
 *
 * Går genom en security definer-funktion och inte en SELECT: tabellen
 * `workspace_tenant_keys` har RLS utan policies, alltså noll rader för appen.
 * Funktionen tar heller ingen workspace_id — med en parameter hade den varit en
 * uppslagsbok över alla arbetsytors nycklar, och en bugg i en anropsplats hade
 * räckt för att läsa fel kunds.
 */
async function tenantApiKeyForWorkspace(userId: string): Promise<string | undefined> {
  const rows = await sqlAsUser<{ nyckel: string | null }>(
    userId,
    "select public.tenant_api_key_for_current_workspace() as nyckel"
  );
  return rows[0]?.nyckel ?? undefined;
}

/**
 * Vilken kund ett inloggat anrop mot Snajp-Support-backenden gäller.
 *
 * Tenanten härleds ur SESSIONEN, aldrig ur något klienten skickar. Det är hela
 * poängen: den tidigare catch-all-proxyn skickade ingen tenant alls, föll
 * tillbaka på demonyckeln, och varje inloggad kunds inkorg, kunskapsbas och
 * röstdokument pekade därmed på demo-tenanten Nordlys Handel. Två kunder hade
 * skrivit i samma SOUL.
 *
 * Den publika chatten (chat/ och jobs/) går INTE genom den här modulen. Den är
 * anonym med flit — kunden publicerar länken själv — och skyddas av rate limit,
 * inte av inloggning.
 */

/**
 * Varför felet bär en KOD och inte bara en text.
 *
 * Meddelandena här är skrivna för den som ska laga något: "Sätt workspaces.slug
 * och ss_tenant_id" är rätt sak att säga till oss och fel sak att visa en kund.
 * Fram till nu gick de rakt igenom proxyn och ut i gränssnittet, så en ny kund
 * som klickade på Kundtjänst möttes av en instruktion om databaskolumner.
 *
 * Koden låter UI:t skilja "din arbetsyta är inte klar än" från "något gick
 * sönder" utan att tolka svensk text. Texten kan skrivas om; koden är
 * kontraktet.
 */
export type SnajpTenantKod =
  /** Arbetsytan finns men är inte kopplad till någon kund ännu. Väntar på oss. */
  | "ej_aktiverad"
  /** Kopplad, men nyckeln saknas i miljön. Ett driftfel, inte ett kundläge. */
  | "nyckel_saknas"
  /** Ingen session. */
  | "ej_inloggad";

export class SnajpTenantError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly kod: SnajpTenantKod = "nyckel_saknas"
  ) {
    super(message);
    this.name = "SnajpTenantError";
  }
}

export type SnajpTenant = {
  workspaceId: string;
  slug: string;
  apiKey: string;
  /**
   * auth.users.id. Går vidare till backenden som X-Snajp-User och används
   * enbart till timtaket per användare (migration 019). Backenden behandlar
   * det som ett ogenomskinligt id — den slår aldrig upp det mot auth.users,
   * och en förfalskad rubrik kan därför bara ge en SNÄVARE kvot, aldrig en
   * vidare. Tenant-taket sitter kvar oavsett vad som står här.
   */
  userId: string;
  /** Demo-workspace — går till backenden som X-Snajp-Demo för ett lägre löptak. */
  isDemo: boolean;
  /**
   * Plattformsadmin tittar som en namngiven kund. Alla skrivningar ska då
   * märkas is_test så de inte dyker upp i kundens skarpa inkorg/lista.
   */
  impersonerar: boolean;
};

export async function requireSnajpTenant(): Promise<SnajpTenant> {
  const context = await getWorkspaceContext();
  if (!context) {
    throw new SnajpTenantError(401, "Du måste vara inloggad.", "ej_inloggad");
  }

  const { workspace, user } = context;

  /**
   * Demovyn — plattformsadmin, och ENBART plattformsadmin, mot demokontot.
   *
   * Grenen ligger före arbetsytans slug med flit: i demoläget ska ingen del av
   * adminens egen tenant nås, inte heller om den råkar vara felkonfigurerad.
   *
   * `aktivVy()` slår upp `platform_admins` och failar stängt (se lib/vy.ts),
   * så cookien i sig är inte ett tenant-byte. Det är hela skillnaden mot den
   * bugg filens docstring ovan beskriver: där föll varje inloggad kund tillbaka
   * på demonyckeln, här kan bara den som redan når /admin göra det, och bara
   * mot en enda hårdkodad tenant.
   *
   * Nyckeln är demonyckeln. `SNAJP_INTERNAL_API_KEY` är samma sträng i den här
   * miljön (se app/api/snajp-support/_lib.ts) och står kvar som reserv för att
   * en saknad variabel annars gör demovyn oöppningsbar utan att säga varför.
   */
  const lage = await aktivVy();

  /**
   * Kundbesök — plattformsadmin i en NAMNGIVEN kunds arbetsyta.
   *
   * Ligger före demogrenen och före arbetsytans egen slug, av samma skäl som
   * demogrenen låg först: i ett besök ska ingen del av adminens EGEN tenant
   * kunna nås, inte heller om något är felkonfigurerat.
   *
   * Tre lås, och inget av dem räcker ensamt:
   *
   *  1. `aktivVy()` slår upp `platform_admins` och failar stängt. En cookie
   *     från någon som inte är admin betyder ingenting.
   *  2. Nyckeln hämtas genom `tenant_api_key_for_admin()` (migration 042), som
   *     gör OM samma kontroll i databasen. Funktionen tar en parameter och vore
   *     annars en uppslagsbok över alla kunders nycklar — därför sitter
   *     villkoret i funktionskroppen, inte hos anroparen.
   *  3. Kunder med configfil har sin nyckel i en miljövariabel och ingen rad i
   *     `workspace_tenant_keys`. Den vägen tas nedan, och den kan bara nå en
   *     slug som faktiskt finns i registret.
   *  4. Finns ingen av delarna utfärdas en nyckel på plats genom
   *     `save_admin_tenant_key()` (migration 061), som gör om admin-kontrollen
   *     en TREDJE gång och dessutom vägrar spara en nyckel som pekar på en
   *     annan tenant än arbetsytans.
   *
   * Vad som INTE görs här: ingen skrivrättighet dras in. Läsläget är i dag en
   * överenskommelse i UI:t (bannern) och inte en teknisk spärr — se HANDOFF.
   */
  if (lage.vy === "kund") {
    const tenant = getTenant(lage.slug);

    /**
     * Demokontot först.
     *
     * `nordlys-handel` är en backend-tenant utan arbetsyta: den har varken en
     * rad i `workspace_tenant_keys` eller en `SNAJP_KEY_*`-variabel, och dess
     * nyckel ÄR demonyckeln. Utan den här grenen mötte "Byt kund" → Nordlys
     * Handel ett 409 på varje yta, vilket är exakt vad felrapporten visade.
     */
    if (lage.slug === DEMO_TENANT_SLUG) {
      const demoKey = process.env.SNAJP_DEMO_API_KEY || process.env.SNAJP_INTERNAL_API_KEY;
      if (demoKey) {
        return {
          workspaceId: workspace.id,
          slug: lage.slug,
          apiKey: demoKey,
          userId: user.id,
          isDemo: false,
          impersonerar: true
        };
      }
    }

    let apiKey = tenant?.perWorkspaceKey === false && tenant?.supportKeyEnv
      ? process.env[tenant.supportKeyEnv]
      : ((
          await sqlAsUser<{ nyckel: string | null }>(
            user.id,
            "select public.tenant_api_key_for_admin($1) as nyckel",
            [lage.slug]
          )
        )[0]?.nyckel ?? (tenant?.supportKeyEnv ? process.env[tenant.supportKeyEnv] : undefined));

    /**
     * Sista utvägen: utfärda en nyckel i stället för att svara 409.
     *
     * Kunder som lades upp före migration 040 har varken nyckelrad eller
     * miljövariabel i den här miljön, och backenden lämnar aldrig tillbaka en
     * redan utfärdad nyckel (bara sha256-hashen sparas). Alternativet till det
     * här är att en människa kör `scripts/railway_tenantnyckel.py` en gång per
     * kund och miljö — alltså att supportytan är trasig tills någon märker det.
     */
    if (!apiKey) {
      const { sakerstallAdminnyckel } = await import("@/lib/snajp/provisionering");
      apiKey = (await sakerstallAdminnyckel(user.id, lage.slug, tenant?.name ?? lage.slug)) ?? undefined;
    }

    if (!apiKey) {
      throw new SnajpTenantError(
        409,
        `Kunden "${lage.slug}" gick inte att öppna. Backenden kunde inte utfärda ` +
          "en nyckel för den — kontrollera att kunden finns och att " +
          "SNAJP_MASTER_API_KEY är satt i den här miljön."
      );
    }

    return {
      workspaceId: workspace.id,
      slug: lage.slug,
      apiKey,
      userId: user.id,
      // Ett kundbesök ska inte köra med sänkt löptak: det är kundens riktiga
      // trafik som granskas, och en strypt körning svarar på fel fråga.
      isDemo: false,
      impersonerar: true
    };
  }

  if (lage.vy === "demo") {
    const apiKey = process.env.SNAJP_DEMO_API_KEY || process.env.SNAJP_INTERNAL_API_KEY;
    if (!apiKey) {
      throw new SnajpTenantError(
        503,
        "SNAJP_DEMO_API_KEY är inte satt i den här miljön. Demovyn kan inte nå backenden förrän den finns."
      );
    }
    return {
      workspaceId: workspace.id,
      slug: DEMO_TENANT_SLUG,
      apiKey,
      userId: user.id,
      // Se lib/data/dashboard.ts: demovyn ska köra skarpt, inte med sänkt tak.
      isDemo: false,
      impersonerar: false
    };
  }

  /**
   * Ingen slug betyder att arbetsytan aldrig kopplats till en kund. Att då tyst
   * låna demo-tenantens data är precis felet vi stänger — men att svara 409 och
   * stanna där var inte heller rätt: uppstarten kopplade BARA testarbetsytor, så
   * varje riktig kund som registrerade sig fick det felet på var enda yta tills
   * någon av oss körde `scripts/onboard_tenant.py` för hand.
   *
   * Arbetsytan får därför sin tenant här, en gång, och kundens uppgifter ur
   * uppstartsformuläret blir samtidigt standardinställningar (se
   * lib/snajp/provisionering.ts). Går det inte står felet kvar som förut.
   */
  if (!workspace.slug) {
    const { sakerstallKundtenant } = await import("@/lib/snajp/provisionering");
    const nykopplad = await sakerstallKundtenant(user.id, workspace, context.businessContext);
    if (nykopplad) {
      return {
        workspaceId: workspace.id,
        slug: nykopplad.slug,
        apiKey: nykopplad.apiKey,
        userId: user.id,
        isDemo: workspace.is_demo,
        impersonerar: false
      };
    }

    throw new SnajpTenantError(
      409,
      "Arbetsytan är inte kopplad till någon kund ännu, och kopplingen kunde inte " +
        "göras automatiskt. Kontrollera att SNAJP_MASTER_API_KEY är satt och att " +
        "backenden svarar.",
      "ej_aktiverad"
    );
  }

  /**
   * Configfilen är INTE ett villkor för att arbetsytan ska fungera.
   *
   * Den styr den publika chatten på kundens egen domän (logotyp, palett,
   * startfrågor) — se TENANTS.md steg 4. Att kräva den här betydde att en
   * automatiskt kopplad kund möttes av "Ingen configfil för …" på sin egen
   * inloggade yta, alltså ett fel om VÅR filstruktur i kundens gränssnitt.
   *
   * Nyckeln i `workspace_tenant_keys` är beviset som räknas: den skrevs av en
   * security definer-funktion mot just den här arbetsytan.
   */
  const tenant = getTenant(workspace.slug);

  /**
   * Två nyckelvägar, och ordningen mellan dem är inte utbytbar.
   *
   * En kund med configfil har sin nyckel i en miljövariabel. En arbetsyta med
   * EGEN tenant skapad i drift (migration 040/061) har sin i databasen — för den
   * är miljövariabeln fel svar: `SNAJP_KEY_TESTKUND` pekar på den GAMLA delade
   * tenanten, alltså en delad kunskapsbas. Att låta env vinna hade tyst
   * återinfört precis det vi byggde bort.
   */
  const apiKey =
    tenant && !tenant.perWorkspaceKey
      ? process.env[tenant.supportKeyEnv]
      : await tenantApiKeyForWorkspace(user.id);

  if (!apiKey && !tenant) {
    throw new SnajpTenantError(
      409,
      `Arbetsytan pekar på "${workspace.slug}" men har ingen sparad backend-nyckel. ` +
        "Kör scripts/railway_tenantnyckel.py --slug " +
        `${workspace.slug} för den här miljön.`,
      "ej_aktiverad"
    );
  }

  if (!apiKey && tenant?.perWorkspaceKey) {
    throw new SnajpTenantError(
      409,
      "Testarbetsytan har ingen egen backend-nyckel sparad. Kör onboardingen igen " +
        "eller koppla arbetsytan med scripts/railway_tenant_keys.py."
    );
  }

  if (!apiKey) {
    // Samma resonemang som MissingTenantKeyError i chat-proxyn: utan nyckel
    // svarar vi inte som ett annat bolag.
    throw new SnajpTenantError(
      503,
      `${tenant?.supportKeyEnv} är inte satt i den här miljön. ${tenant?.name} kan inte nå backenden förrän den finns.`
    );
  }

  // Kunder som kopplades före migration 061 har nyckel men tomma inställningar.
  // Fylls en gång per tenant och processlivstid, utanför anropets väg — se
  // lib/snajp/provisionering.ts för varför det är säkert att inte vänta in.
  const { fyllStandardinstallningarEnGang } = await import("@/lib/snajp/provisionering");
  fyllStandardinstallningarEnGang(workspace.slug, apiKey, workspace, context.businessContext);

  return {
    workspaceId: workspace.id,
    slug: workspace.slug,
    apiKey,
    userId: user.id,
    isDemo: workspace.is_demo,
    impersonerar: false
  };
}
