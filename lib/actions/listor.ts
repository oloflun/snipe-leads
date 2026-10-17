"use server";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { readJsonBody } from "@/lib/http/json";
import { requireSnajpTenant } from "@/lib/snajp/tenant";

/**
 * Kopiera eller flytta en leadslista till en annan kund (Antons beställning
 * 2026-10-08). Serveraction och inte adminproxyn: proxyn är GET-only med flit,
 * och masternyckeln ska aldrig nå webbläsaren. Samma mönster som
 * `lib/actions/flytt.ts`.
 *
 * Källkunden härleds ur sessionen på servern — den kund adminen tittar på
 * (eller sin egen arbetsyta) — så klienten väljer aldrig vems lista som
 * flyttas, bara vart. Backend: POST /api/admin/listor/{id}/till-kund
 * (snajp-support/app/api/admin_listor.py).
 */

export type ListaTillKundSvar = {
  kopierade?: number;
  /** Rader vars bolag mottagaren redan hade (prospekt, lista, CRM). */
  upptagna?: number;
  flyttad?: boolean;
  error?: string;
  /** Det här lagrets egna fel, översatta i vyn (LeadslistorView). */
  felkod?: "admin" | "nyckel" | "indata" | "kund";
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function listaTillKund(listId: string, tillSlug: string, flytta: boolean): Promise<ListaTillKundSvar> {
  if (!(await getPlatformAdmin())) return { error: "Kräver plattformsadmin.", felkod: "admin" };
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) return { error: "SNAJP_MASTER_API_KEY är inte satt i den här miljön.", felkod: "nyckel" };
  if (!UUID.test(String(listId)) || !String(tillSlug).trim() || String(tillSlug).length > 120) {
    return { error: "Ogiltig lista eller kund.", felkod: "indata" };
  }
  let franSlug: string;
  try {
    franSlug = (await requireSnajpTenant()).slug;
  } catch {
    return { error: "Kunden gick inte att läsa.", felkod: "kund" };
  }
  const response = await proxyWithApiKey(
    `/api/admin/listor/${encodeURIComponent(listId)}/till-kund`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fran_tenant: franSlug, till_tenant: String(tillSlug).trim(), flytta: Boolean(flytta) })
    },
    masterKey
  );
  const body = await readJsonBody<Record<string, unknown>>(response).catch(() => null);
  if (!response.ok) {
    return { error: (body?.detail as string | undefined) ?? `Backenden svarade ${response.status}.` };
  }
  return {
    kopierade: Number(body?.kopierade ?? 0),
    upptagna: Number(body?.upptagna ?? 0),
    flyttad: Boolean(body?.flyttad)
  };
}
