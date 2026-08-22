import "server-only";

import { cookies } from "next/headers";
import { getPlatformAdmin } from "@/lib/auth/admin";

/**
 * Vilken av plattformsadminens två ytor som är aktiv.
 *
 * `admin` är Snajps egna körningar och supportärenden — den skarpa sidan.
 * `demo` renderar produkten exakt som en kundinloggning mot demokontot, utan
 * en enda adminkontroll, för att kunna visa den för någon.
 *
 * ## Varför en cookie och inte en URL
 *
 * Ytan ska följa med genom VARJE undersida, inklusive de som renderas på
 * servern (`/settings/*`). En query-parameter måste bäras vidare av varje länk
 * i appen, och den länk som glöms bort tar användaren tillbaka till fel yta
 * mitt i ett flöde — precis den klassen av fel som `useArbetsvag()` finns för
 * att laga en gång till.
 *
 * ## Varför cookien inte är ett tenant-byte
 *
 * `requireSnajpTenant()` härleder kunden ur SESSIONEN, aldrig ur något
 * klienten skickar — en cookie ÄR något klienten skickar. Därför är
 * `getPlatformAdmin()` inte en detalj här utan hela villkoret: för alla andra
 * betyder cookien ingenting alls, och en manipulerad rad ger sin egen
 * arbetsyta, inte demokontots. Uppslaget failar dessutom stängt (se
 * lib/auth/admin.ts), så ett databasavbrott ger `admin`, inte `demo`.
 *
 * `httpOnly` för att ingen klientkod behöver läsa den: läget kommer till
 * webbläsaren som ett fält i DashboardState, från servern som redan avgjort.
 */

export const VY_COOKIE = "snajp.vy";

export type Vy = "admin" | "demo" | "kund";

/** Demokontot. Fortfarande hårdkodat — `demo` är en visning, inte ett kundbesök. */
export const DEMO_TENANT_SLUG = "nordlys-handel";
export const DEMO_ARBETSYTA = "Nordlys Handel";

/**
 * Läget, och vilken kund det gäller.
 *
 * `kund` är läsläge hos en NAMNGIVEN kund och tillkom efter `demo`. De är inte
 * samma sak och slås därför inte ihop: demovyn visar produkten för någon och
 * kör mot ett konto som inte tillhör en riktig kund, medan `kund` öppnar
 * riktiga ärenden och riktiga mejladresser. Det andra kräver en gul banner och
 * en logg; det första gör det inte.
 */
export type Lage =
  | { vy: "admin"; slug: null }
  | { vy: "demo"; slug: typeof DEMO_TENANT_SLUG }
  | { vy: "kund"; slug: string };

/** Cookievärdet för ett kundbesök. Prefixet gör läget läsbart i en logg. */
const KUND_PREFIX = "kund:";

/**
 * Sluggens tillåtna form. Samma teckenmängd som `workspaces.slug` använder.
 *
 * Kontrollen sker FÖRE databasfrågan, inte i stället för den: cookien är
 * klientdata, och `tenant_api_key_for_admin()` i migration 042 är den grind
 * som faktiskt avgör. Det här är bara att inte skicka skräp vidare.
 */
const SLUG_MONSTER = /^[a-z0-9][a-z0-9-]{0,62}$/;

export function kundVyVarde(slug: string): string {
  return `${KUND_PREFIX}${slug}`;
}

export async function aktivVy(): Promise<Lage> {
  const rad = (await cookies()).get(VY_COOKIE)?.value ?? "";

  if (rad !== "demo" && !rad.startsWith(KUND_PREFIX)) {
    return { vy: "admin", slug: null };
  }

  // Ett enda uppslag för båda lägena, och det avgör allt: för den som inte är
  // plattformsadmin betyder cookien ingenting alls. `getPlatformAdmin()` failar
  // stängt (se lib/auth/admin.ts), så ett databasavbrott ger `admin`.
  if (!(await getPlatformAdmin())) {
    return { vy: "admin", slug: null };
  }

  if (rad === "demo") {
    return { vy: "demo", slug: DEMO_TENANT_SLUG };
  }

  const slug = rad.slice(KUND_PREFIX.length);
  if (!SLUG_MONSTER.test(slug)) {
    return { vy: "admin", slug: null };
  }

  return { vy: "kund", slug };
}
