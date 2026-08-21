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

export type Vy = "admin" | "demo";

/** Demokontot. En tenant, hårdkodad — det här är inte generell impersonation. */
export const DEMO_TENANT_SLUG = "nordlys-handel";
export const DEMO_ARBETSYTA = "Nordlys Handel";

export async function aktivVy(): Promise<Vy> {
  const rad = (await cookies()).get(VY_COOKIE)?.value;
  if (rad !== "demo") {
    return "admin";
  }
  return (await getPlatformAdmin()) ? "demo" : "admin";
}
