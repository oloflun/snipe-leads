import { headers } from "next/headers";
import { notFound } from "next/navigation";
import { getTenant, tenantSlugFromHost, type Tenant } from "./index";

/**
 * Vilken kund den här requesten gäller, härlett ur värdnamnet.
 *
 * Upplösningen sker här och inte i proxy.ts med flit: proxyns matcher täcker
 * bara den inloggade ytan, och att bredda den till de publika sidorna hade
 * inneburit ett Supabase-anrop per anonym besökare. Server components kan läsa
 * host-headern direkt, så mellanhanden behövs inte.
 */
export async function getCurrentTenant(): Promise<Tenant | null> {
  const headerList = await headers();
  return getTenant(tenantSlugFromHost(headerList.get("host")));
}

/**
 * Snajps egna marknadsföringssidor finns inte på en kunds domän.
 *
 * Utan detta nås /leads och /support på livrustning.<domän> och visar
 * leverantörens säljsajt för kundens besökare — med kundens färger, vilket gör
 * förväxlingen värre snarare än bättre.
 */
export async function notFoundOnTenant(): Promise<void> {
  if (await getCurrentTenant()) {
    notFound();
  }
}
