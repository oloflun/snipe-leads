import "server-only";

import { headers } from "next/headers";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { readJsonBody } from "@/lib/http/json";

/**
 * Adminvyns datahämtning, server-side.
 *
 * Går direkt mot backenden i stället för via den egna /api/admin-routen:
 * en server component som fetchar sin egen HTTP-endpoint betyder en extra
 * rundtur och en cookie som måste vidarebefordras för hand. Grinden är
 * densamma — `getPlatformAdmin()` anropas här också, inte bara i layouten,
 * eftersom en funktion som läser över alla kunder inte ska gå att anropa
 * från fel ställe utan att märka det.
 */

export class AdminUnavailableError extends Error {}

async function adminFetch<T>(path: string, fallback: T): Promise<T | AdminUnavailableError> {
  if (!(await getPlatformAdmin())) {
    return new AdminUnavailableError("Inte plattformsadmin.");
  }

  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    return new AdminUnavailableError(
      "SNAJP_MASTER_API_KEY är inte satt i den här miljön. Adminvyn kan inte nå backenden förrän den finns."
    );
  }

  const response = await proxyWithApiKey(`/api/admin${path}`, { method: "GET" }, masterKey);
  if (!response.ok) {
    const body = await readJsonBody<{ error?: string }>(response).catch(() => null);
    return new AdminUnavailableError(
      body?.error ?? `Backenden svarade ${response.status} på ${path}.`
    );
  }

  // Adminvyn är ett driftverktyg: en tom kropp ska bli ett synligt fel, inte
  // en nolla som ser ut som ett mätvärde.
  let body: Record<string, unknown> | null;
  try {
    body = await readJsonBody<Record<string, unknown>>(response);
  } catch (cause) {
    return new AdminUnavailableError(
      cause instanceof Error ? cause.message : `Kunde inte läsa svaret från ${path}.`
    );
  }
  if (!body) {
    return new AdminUnavailableError(`Backenden svarade utan innehåll på ${path}.`);
  }

  const key = Object.keys(body)[0];
  return (body[key] as T) ?? fallback;
}

export type TenantRow = {
  id: string;
  slug: string | null;
  name: string;
  tickets: number;
  /** Ärenden med status 'escalated' — samma villkor som veckoanalysen. */
  escalated?: number;
  /** KUNDVOLYM. Räknar inte rader med `is_test` — se list_tenants_with_stats. */
  runs: number;
  /** Våra egna provkörningar. Redovisas separat, göms inte. */
  test_runs?: number;
  tokens_in: number;
  tokens_out: number;
  errors: number;
  last_activity: string | null;
  /** Registrets datum om ett finns, annars tenantens skapelsedatum (053). */
  kund_sedan?: string | null;
  /** Null = inget avtal registrerat. Ett datum = avtal finns, signerat då. */
  avtal_signerat?: string | null;
};

export type RunRow = {
  id: string;
  tenant_slug?: string | null;
  agent_type: string;
  pack_version: string;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  created_at: string;
  step_log?: StepLogEntry[] | string | null;
  input?: string | null;
  output?: string | null;
};

export type StepLogEntry = {
  skill: string;
  attempts: number;
  escalated: boolean;
  escalation_reason: string | null;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  reasoning_tokens: number;
  thinking_mode: string;
  overlay: string | null;
  sources_used: string[];
  context_refs: string[];
  system_prompt?: string | null;
  user_message?: string | null;
  raw_output?: string | null;
  reasoning_content?: string | null;
};

export type EventRow = {
  id: string;
  tenant_slug?: string | null;
  level: "error" | "warning" | "info";
  source: string;
  message: string;
  detail: Record<string, unknown>;
  run_id: string | null;
  created_at: string;
};

export const listTenants = () => adminFetch<TenantRow[]>("/tenants", []);
export const listRuns = (query = "") => adminFetch<RunRow[]>(`/runs${query}`, []);
export const listEvents = (query = "") => adminFetch<EventRow[]>(`/events${query}`, []);

/**
 * `step_log` är jsonb i databasen och kom en tid tillbaka som en STRÄNG:
 * asyncpg avkodar inte jsonb utan typkodare, och backenden avkodade inte
 * kolumnen (`postgres.py::_avkoda_jsonb` gör det nu). Spårvyn föll då på
 * `steps.map is not a function` — en vit sida, inte ett felmeddelande.
 *
 * Normaliseringen står kvar även efter backend-fixen, och det är inte bälte
 * och hängslen: web och api är SKILDA tjänster på Railway och deployar var för
 * sig. Ett web som är nyare än sitt api är ett normaltillstånd i minuterna
 * efter en push, och en adminvy som kraschar under dem är värre än en som
 * visar stegen.
 */
export type AdminRun = Omit<RunRow, "step_log"> & { step_log: StepLogEntry[] };

function normaliseraSteg(run: RunRow | null): AdminRun | null {
  if (!run) {
    return null;
  }
  const rå: unknown =
    typeof run.step_log === "string" ? tolkaJson(run.step_log) : run.step_log;
  return { ...run, step_log: Array.isArray(rå) ? (rå as StepLogEntry[]) : [] };
}

function tolkaJson(värde: string): unknown {
  try {
    return JSON.parse(värde);
  } catch {
    return null;
  }
}

export async function getRun(runId: string): Promise<AdminRun | null | AdminUnavailableError> {
  const result = await adminFetch<RunRow | null>(`/runs/${encodeURIComponent(runId)}`, null);
  return result instanceof AdminUnavailableError ? result : normaliseraSteg(result);
}

/** Så att sidorna slipper upprepa instanceof-kontrollen. */
export function unwrap<T>(value: T | AdminUnavailableError): { data: T | null; error: string | null } {
  if (value instanceof AdminUnavailableError) {
    return { data: null, error: value.message };
  }
  return { data: value, error: null };
}

// headers() importeras för att tvinga dynamisk rendering även om en sida
// råkar sakna force-dynamic — adminsiffror får aldrig cachas och visas för
// nästa besökare.
export async function noStore(): Promise<void> {
  await headers();
}
