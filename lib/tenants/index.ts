import type { Tenant, TenantPalette } from "./types";
import { livrustning } from "./livrustning";
import { snajp } from "./snajp";
import { testkund } from "./testkund";

export type { Tenant, TenantLogo, TenantPalette } from "./types";

/**
 * Registret. Att lägga till en kund är en rad här plus en configfil — inte ett
 * nytt repo och inte en kopierad mapp.
 */
const tenants: Record<string, Tenant> = {
  livrustning,
  // Vår egen arbetsyta. Vi använder produkten själva, och utan den här raden
  // svarar /chat/snajp med ett internt felmeddelande.
  snajp,
  // Delad tenant för konton skapade med "Testarbetsyta" ikryssad. Utan den
  // möter en nyskapad testkund 409 på sina egna ytor — uppmätt, se filen.
  testkund
};

/** Headern som proxy.ts sätter när värdnamnet pekar ut en kund. */
export const TENANT_HEADER = "x-tenant";

/**
 * Testarbetsytornas slugmönster: `testkund-<8 tecken ur workspace-id>`.
 *
 * Måste stämma med regexen i `public.link_test_tenant` (migration 040). Den
 * databasfunktionen är grinden — matchar sluggen inte, kopplas ingenting, och
 * en manipulerad frontend kan därför inte peka en arbetsyta på en RIKTIG kunds
 * tenant.
 */
const TESTKUND_SLUG = /^testkund-[a-z0-9]{4,32}$/;

export function arTestkundSlug(slug: string): boolean {
  return TESTKUND_SLUG.test(slug);
}

export function getTenant(slug: string | null | undefined): Tenant | null {
  if (!slug) {
    return null;
  }
  const registrerad = tenants[slug];
  if (registrerad) {
    return registrerad;
  }

  /**
   * Testarbetsytor har EGEN tenant men INGEN configfil.
   *
   * Det är hela poängen: en configfil per testkonto är en commit och en deploy
   * per testkonto, alltså precis den friktion testarbetsytan finns för att ta
   * bort. Configen härleds därför ur `testkund`-mallen — samma utseende, samma
   * texter, men en egen slug och en nyckel som bor i databasen (migration 040).
   *
   * Utan det här delade alla testkunder inkorg, kunskapsbas och röstdokument.
   * En kunds villkor kunde grunda ett svar till en annan kunds kund, och
   * grundningsgrinden kan inte se skillnaden — den ser bara en träff.
   */
  if (arTestkundSlug(slug)) {
    return { ...testkund, slug, perWorkspaceKey: true };
  }

  return null;
}

export function tenantSlugs(): string[] {
  return Object.keys(tenants);
}

/**
 * Plockar kundens slug ur värdnamnet. `livrustning.snajp.se` → `livrustning`.
 *
 * Rena apex-domäner, localhost och Vercels egna previewvärdar ger null, så
 * Snajps egen sajt renderas som vanligt. Preview-URL:er är formen
 * `snipra-git-branch-team.vercel.app` — den första etiketten är alltså inte en
 * kund, och utan detta undantag hade varje preview försökt slå upp en tenant.
 */
export function tenantSlugFromHost(host: string | null | undefined): string | null {
  if (!host) {
    return null;
  }

  const hostname = host.split(":")[0].toLowerCase();

  if (hostname === "localhost" || hostname.endsWith(".localhost")) {
    // Lokalt testas kunder som livrustning.localhost:3000, vilket löser sig
    // själv i moderna webbläsare utan att röra hosts-filen.
    const [first] = hostname.split(".");
    return first === "localhost" ? null : first;
  }

  if (hostname.endsWith(".vercel.app")) {
    return null;
  }

  const labels = hostname.split(".");
  if (labels.length < 3) {
    return null;
  }

  const [first] = labels;
  return first === "www" ? null : first;
}

/** Genererar :root-overriden. Komponenterna läser redan dessa variabler. */
export function paletteToCss(palette: TenantPalette): string {
  const entries: [keyof TenantPalette, string][] = [
    ["ink", "--ink"],
    ["ink2", "--ink2"],
    ["paper", "--paper"],
    ["paper2", "--paper2"],
    ["mineral", "--mineral"],
    ["seal", "--seal"],
    ["ochre", "--ochre"],
    ["moss", "--moss"],
    ["danger", "--danger"]
  ];

  const declarations = entries
    .map(([key, variable]) => `${variable}: ${palette[key]};`)
    .join("")
    // --focus följer accenten enligt DESIGN.md; den får aldrig hamna på efterkälken.
    .concat(`--focus: ${palette.ochre};`);

  return `:root{${declarations}}`;
}
