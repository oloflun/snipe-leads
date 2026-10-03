"use server";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";
import { aktivMiljo } from "@/lib/miljo";

/**
 * Flytta till main — serveractions för panelen i Byt kund (plan del E).
 *
 * Webbläsaren ser aldrig masternyckeln och når aldrig main: panelen anropar
 * de här actions, som anropar DEN HÄR miljöns api (`/api/admin/flytt/*`) med
 * masternyckeln, och det är api:t som signerar och skickar paketet till main
 * (FLYTT_MAL_URL + FLYTT_NYCKEL). Panelen finns bara i development: i main
 * returnerar `hamtaFlyttbart` null och inget renderas.
 */

export type FlyttKandidater = {
  tenant_id: string;
  mejl: { id: string; subject: string; from_email: string; status: string; klass: string | null; received_at: string | null; is_test: boolean }[];
  korningar: { job_id: string; status: string; scope: string; created_at: string | null; is_test: boolean; mal: number | null; levererade: number | null }[];
  flyttade: { typ: string; ref_id: string; resultat: string; flyttad_at: string | null }[];
};

export type FlyttStatus = {
  spegel: { environment: string; seeded_at: string | null } | null;
  nasta_spegling: string;
  mal_konfigurerat: boolean;
  nyckel_konfigurerad: boolean;
};

async function masterFetch<T>(path: string, init: RequestInit): Promise<{ data?: T; error?: string }> {
  if (!(await getPlatformAdmin())) return { error: "Kräver plattformsadmin." };
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) return { error: "SNAJP_MASTER_API_KEY är inte satt i den här miljön." };
  const response = await proxyWithApiKey(`/api/admin/flytt${path}`, init, masterKey);
  const body = await readJsonBody<Record<string, unknown>>(response).catch(() => null);
  if (!response.ok) {
    return {
      error: (body?.detail as string | undefined) ?? (body?.error as string | undefined) ?? `Backenden svarade ${response.status}.`
    };
  }
  return { data: (body ?? {}) as T };
}

/** null = inte en spegel (main): panelen renderas inte. */
export async function hamtaFlyttbart(slug: string): Promise<{ status: FlyttStatus; kandidater: FlyttKandidater } | { error: string } | null> {
  if (aktivMiljo() !== "development") return null;
  const status = await masterFetch<FlyttStatus>("/status", { method: "GET" });
  if (status.error || !status.data) return { error: status.error ?? "Statusen gick inte att läsa." };
  if (!status.data.spegel) return null;
  const kandidater = await masterFetch<FlyttKandidater>(`/kandidater?slug=${encodeURIComponent(slug)}`, { method: "GET" });
  if (kandidater.error || !kandidater.data) return { error: kandidater.error ?? "Kandidaterna gick inte att läsa." };
  return { status: status.data, kandidater: kandidater.data };
}

export async function flyttaTillMain(
  slug: string,
  typ: "mejl" | "korning",
  ids: string[]
): Promise<{ rader?: { ref_id: string; resultat: string; fel?: string }[]; error?: string }> {
  if (aktivMiljo() !== "development") return { error: "Flytt till main går bara från development." };
  const { data, error } = await masterFetch<{ rader: { ref_id: string; resultat: string; fel?: string }[] }>("/skicka", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, typ, ids })
  });
  return error ? { error } : { rader: data?.rader ?? [] };
}
