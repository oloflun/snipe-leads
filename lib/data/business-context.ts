import "server-only";

import type { BusinessContextInsert } from "@/lib/database.types";
import { sqlAsUser } from "@/lib/db";

/**
 * Enda skrivvägen mot `business_contexts`.
 *
 * Två anropare: uppstartsformuläret (`lib/actions/onboarding.ts`) skapar raden,
 * inställningssidan (`lib/actions/affarskontext.ts`) ändrar den. Innan den här
 * filen fanns ägde onboardingen satsen ensam, och inställningssidan skrev inte
 * alls — dess fem textrutor läste `lib/mock-data.ts` och hade ingen
 * spara-knapp. Fliken fanns, funktionen inte.
 *
 * En upsert i stället för läs-sen-skriv: unika index på workspace_id gör
 * villkoret till databasens jobb, och två samtidiga sparningar kan inte längre
 * skapa två rader.
 */
export async function sparaBusinessContext(
  userId: string,
  payload: BusinessContextInsert
): Promise<void> {
  await sqlAsUser(
    userId,
    `insert into public.business_contexts
       (workspace_id, product, target_audience, industries, geography, tone, offer, cta, contact_roles, updated_at)
     values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
     on conflict (workspace_id) do update set
       product = excluded.product,
       target_audience = excluded.target_audience,
       industries = excluded.industries,
       geography = excluded.geography,
       tone = excluded.tone,
       offer = excluded.offer,
       cta = excluded.cta,
       contact_roles = excluded.contact_roles,
       updated_at = excluded.updated_at`,
    [
      payload.workspace_id,
      payload.product,
      payload.target_audience,
      payload.industries ?? [],
      payload.geography ?? [],
      payload.tone,
      payload.offer,
      payload.cta,
      payload.contact_roles ?? [],
      payload.updated_at ?? new Date().toISOString()
    ]
  );
}
