"use server";

import { revalidatePath } from "next/cache";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";

/**
 * Manuell avstängning/återaktivering av en kund — trial-konverteringens
 * mänskliga väg (beslut 2026-09-20: ingen automatisk konvertering).
 *
 * Server action och inte en /api-route, av samma skäl som kunddata.ts:
 * skrivningen kräver master-nyckeln och adminproxyn är avsiktligt GET-only.
 * `getPlatformAdmin()` står i funktionen — en action är en POST-endpoint med
 * ett eget id, och att den bara anropas från Kundprofilen är ett antagande
 * om klienten.
 *
 * `masterFetch` är en lokal kopia, inte en import: en "use server"-modul
 * exporterar bara actions, och att exportera hjälparen från kunddata.ts hade
 * gjort den anropbar från klienten.
 */

export type AvstangningsResultat = {
  /** Tenantens nya läge efter skrivningen. */
  active?: boolean;
  error?: string;
};

async function masterFetch<T>(
  path: string,
  init: RequestInit
): Promise<{ data?: T; error?: string }> {
  if (!(await getPlatformAdmin())) {
    return { error: "Kräver plattformsadmin." };
  }
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    return {
      error:
        "SNAJP_MASTER_API_KEY är inte satt i den här miljön. Avstängningen kan inte nå backenden förrän den finns."
    };
  }

  const response = await proxyWithApiKey(`/api/admin${path}`, init, masterKey);
  const body = await readJsonBody<Record<string, unknown>>(response).catch(() => null);
  if (!response.ok) {
    return {
      error:
        (body?.detail as string | undefined) ??
        (body?.error as string | undefined) ??
        `Backenden svarade ${response.status}.`
    };
  }
  return { data: (body ?? {}) as T };
}

/**
 * Slår av eller på kundens konto. `orsak` är fri text som hamnar i
 * platform_events — skriv den som ett besked till den som läser
 * händelseloggen om ett halvår ("Trial gick ut 2026-11-20, inget avtal").
 */
export async function sattKundAktiv(
  tenantId: string,
  active: boolean,
  orsak: string
): Promise<AvstangningsResultat> {
  const { data, error } = await masterFetch<{ tenant: { active: boolean } }>(
    `/tenants/${encodeURIComponent(tenantId)}/aktiv`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active, orsak: orsak.trim() || null })
    }
  );
  if (error) {
    return { error };
  }
  // Kundlistan och profilen visar båda aktiv-läget; utan revalidering står
  // "Inaktiv"-märket kvar fel tills nästa hårda omladdning.
  revalidatePath("/admin/kunder");
  revalidatePath(`/admin/kunder/${tenantId}`);
  return { active: data?.tenant.active };
}
