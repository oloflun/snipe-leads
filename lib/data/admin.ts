import "server-only";

import { headers } from "next/headers";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";

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
    const body = await response.json().catch(() => ({}));
    return new AdminUnavailableError(
      body.error ?? `Backenden svarade ${response.status} på ${path}.`
    );
  }
  const body = (await response.json()) as Record<string, unknown>;
  const key = Object.keys(body)[0];
  return (body[key] as T) ?? fallback;
}

export type TenantRow = {
  id: string;
  slug: string | null;
  name: string;
  tickets: number;
  runs: number;
  tokens_in: number;
  tokens_out: number;
  errors: number;
  last_activity: string | null;
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
  step_log?: StepLogEntry[] | null;
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

export async function getRun(runId: string): Promise<RunRow | null | AdminUnavailableError> {
  const result = await adminFetch<RunRow | null>(`/runs/${encodeURIComponent(runId)}`, null);
  return result;
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
