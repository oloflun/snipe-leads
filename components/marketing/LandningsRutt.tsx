import { JsonLd } from "@/components/JsonLd";
import { InnehallsSida } from "@/components/marketing/InnehallsSida";
import { Landningssida } from "@/components/marketing/Landningssida";
import type { LandningsVag } from "@/lib/landningar";
import { LANDNING, landningSchema } from "@/lib/landningssidor";
import { notFoundOnTenant } from "@/lib/tenants/server";

/**
 * Det som är lika på alla sökordssidor, så att varje app/<sida>/page.tsx bara
 * bär sin adress och sin sökmotortext.
 *
 * Serverkomponent: tenantspärren och schemat körs här, och skalet
 * (sidhuvud, meny, sidfot) stannar på servern i stället för att följa med
 * Landningssidas klientbundle.
 */
export async function LandningsRutt({ vag }: Readonly<{ vag: LandningsVag }>) {
  // Sidorna säljer Snajp. På en kunds domän är de fel bolag på fel sajt.
  await notFoundOnTenant();
  const sida = LANDNING[vag];
  return (
    <>
      <JsonLd data={landningSchema(sida)} />
      <InnehallsSida bredd="vid">
        <Landningssida sida={sida} />
      </InnehallsSida>
    </>
  );
}
