"use server";

import { revalidatePath } from "next/cache";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";

/**
 * Kontots läge från adminens paketflik: aktiv, pausad eller avstängd
 * (migration 080). Pausad och avstängd låser ute lika hårt, skillnaden är
 * avsikten — en paus ska öppnas igen, en avstängning är ett avslut — och den
 * skillnaden bär adminytan och händelseloggen.
 *
 * Server action och inte en /api-route, av samma skäl som avstangning.ts:
 * skrivningen kräver master-nyckeln och adminproxyn är avsiktligt GET-only.
 * `masterFetch` är en lokal kopia av samma skäl som där — en "use server"-
 * modul exporterar bara actions.
 */

export type Kundstatus = "aktiv" | "pausad" | "avstangd";

export type StatusResultat = {
  /** Tenantens nya läge efter skrivningen. */
  status?: Kundstatus;
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
        "SNAJP_MASTER_API_KEY är inte satt i den här miljön. Kontoläget kan inte nå backenden förrän den finns."
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
 * Sätter kundens kontoläge. `orsak` är fri text som hamnar i platform_events,
 * skriven som ett besked till den som läser händelseloggen om ett halvår.
 */
export async function sattKundStatus(
  tenantId: string,
  status: Kundstatus,
  orsak: string
): Promise<StatusResultat> {
  const { data, error } = await masterFetch<{
    tenant: { status: Kundstatus; active: boolean };
  }>(`/tenants/${encodeURIComponent(tenantId)}/status`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, orsak: orsak.trim() || null })
  });
  if (error) {
    return { error };
  }
  // Paketfliken, kundlistan och profilen visar alla läget.
  revalidatePath("/admin/paket");
  revalidatePath("/admin/kunder");
  revalidatePath(`/admin/kunder/${tenantId}`);
  return { status: data?.tenant.status, active: data?.tenant.active };
}
