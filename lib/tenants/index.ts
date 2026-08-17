import type { Tenant, TenantPalette } from "./types";
import { livrustning } from "./livrustning";
import { snajp } from "./snajp";

export type { Tenant, TenantLogo, TenantPalette } from "./types";

/**
 * Registret. Att lägga till en kund är en rad här plus en configfil — inte ett
 * nytt repo och inte en kopierad mapp.
 */
const tenants: Record<string, Tenant> = {
  livrustning,
  // Vår egen arbetsyta. Vi använder produkten själva, och utan den här raden
  // svarar /chat/snajp med ett internt felmeddelande.
  snajp
};

/** Headern som proxy.ts sätter när värdnamnet pekar ut en kund. */
export const TENANT_HEADER = "x-tenant";

export function getTenant(slug: string | null | undefined): Tenant | null {
  if (!slug) {
    return null;
  }
  return tenants[slug] ?? null;
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
