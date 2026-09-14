"use server";

import { revalidatePath } from "next/cache";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";

/**
 * Kundregistret — fliken Kunder & Data:s skrivväg.
 *
 * Server actions och inte en /api-route, av samma skäl som
 * agentinstruktioner.ts: anropen kräver master-nyckeln, och adminproxyn
 * (`app/api/admin/[...path]`) är avsiktligt GET-only. Grinden
 * `getPlatformAdmin()` står i VARJE funktion — en action är en POST-endpoint
 * med ett genererat id, och att den bara anropas från en skyddad sida är ett
 * antagande om klienten.
 *
 * `masterFetch` är en lokal kopia av samma hjälpare i agentinstruktioner.ts,
 * inte en import: en "use server"-modul exporterar bara actions, och att
 * exportera hjälparen därifrån hade gjort den anropbar från klienten.
 */

export type KunddataFalt = {
  varde: string | null;
  /** "manuell" | "onboarding" | "system" | null (saknas). */
  kalla: string | null;
};

export type Kontakt = {
  id: string;
  namn: string;
  roll: string | null;
  mejl: string | null;
  telefon: string | null;
};

export type Kunddata = {
  tenant: { id: string; slug: string | null; name: string };
  falt: Record<string, KunddataFalt>;
  kontakter: Kontakt[];
  uppdaterad: string | null;
};

export type KunddataResultat = {
  success: boolean;
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
        "SNAJP_MASTER_API_KEY är inte satt i den här miljön. Kundregistret kan inte nå backenden förrän den finns."
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

export async function hamtaKunddata(
  tenantId: string
): Promise<{ kunddata?: Kunddata; error?: string }> {
  const { data, error } = await masterFetch<{ kunddata: Kunddata }>(
    `/tenants/${encodeURIComponent(tenantId)}/kunddata`,
    { method: "GET" }
  );
  return error ? { error } : { kunddata: data?.kunddata };
}

/**
 * Sparar de fält som skickats med. Utelämnat fält rörs inte, tom sträng
 * nollställer — samma semantik hela vägen ner i databasen.
 */
export async function sparaKunddata(
  tenantId: string,
  falt: Partial<
    Record<
      | "orgnr"
      | "faktureringsadress"
      | "faktureringsmejl"
      | "telefon"
      | "foretagsadress"
      | "kund_sedan"
      | "avtal_signerat",
      string
    >
  >
): Promise<KunddataResultat> {
  const { error } = await masterFetch(
    `/tenants/${encodeURIComponent(tenantId)}/kunddata`,
    { method: "PUT", body: JSON.stringify(falt) }
  );
  if (error) return { success: false, error };

  revalidatePath("/admin/kunder");
  revalidatePath(`/admin/kunder/${tenantId}/data`);
  return { success: true };
}

export async function skapaKontakt(
  tenantId: string,
  kontakt: { namn: string; roll?: string; mejl?: string; telefon?: string }
): Promise<KunddataResultat> {
  const { error } = await masterFetch(
    `/tenants/${encodeURIComponent(tenantId)}/kontakter`,
    { method: "POST", body: JSON.stringify(kontakt) }
  );
  if (error) return { success: false, error };

  revalidatePath(`/admin/kunder/${tenantId}/data`);
  return { success: true };
}

export async function uppdateraKontakt(
  tenantId: string,
  kontaktId: string,
  falt: { namn?: string; roll?: string; mejl?: string; telefon?: string }
): Promise<KunddataResultat> {
  const { error } = await masterFetch(
    `/tenants/${encodeURIComponent(tenantId)}/kontakter/${encodeURIComponent(kontaktId)}`,
    { method: "PUT", body: JSON.stringify(falt) }
  );
  if (error) return { success: false, error };

  revalidatePath(`/admin/kunder/${tenantId}/data`);
  return { success: true };
}

export async function taBortKontakt(
  tenantId: string,
  kontaktId: string
): Promise<KunddataResultat> {
  const { error } = await masterFetch(
    `/tenants/${encodeURIComponent(tenantId)}/kontakter/${encodeURIComponent(kontaktId)}`,
    { method: "DELETE" }
  );
  if (error) return { success: false, error };

  revalidatePath(`/admin/kunder/${tenantId}/data`);
  return { success: true };
}
