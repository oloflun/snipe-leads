"use server";

import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { getPlatformAdmin } from "@/lib/auth/admin";
import type { LagerPost, SkillDel, StepLogEntry } from "@/lib/data/admin";
import { readJsonBody } from "@/lib/http/json";

/**
 * Insynens hämtningar från klienten (Fas 7): kedjan för en vald körning,
 * en hel skillfil och KB-provet.
 *
 * Server actions och inte adminproxyn, av samma skäl som kunddata.ts: anropen
 * kräver master-nyckeln och KB-provet är en POST, medan proxyn är GET-only.
 * Inget här skriver; backenden tar dem i läsroutern (app/api/admin.py).
 * `masterFetch` är en lokal kopia av samma hjälpare i kunddata.ts: en
 * "use server"-modul exporterar bara actions.
 */

async function masterFetch<T>(path: string, init: RequestInit): Promise<{ data?: T; error?: string }> {
  if (!(await getPlatformAdmin())) {
    return { error: "Kräver plattformsadmin." };
  }
  const masterKey = process.env.SNAJP_MASTER_API_KEY;
  if (!masterKey) {
    return { error: "SNAJP_MASTER_API_KEY är inte satt i den här miljön." };
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

export type KedjeNod = {
  typ: "steg" | "grind";
  id: string;
  grind?: string;
  skill?: string;
  bana?: string;
  utfall: "kord" | "slappt" | "falld" | "stoppad" | "hoppad" | "ej_nadd" | "okant";
  skal: { kod?: string; tecken?: number; text?: string | null; [k: string]: unknown } | null;
  run_id?: string;
  post?: StepLogEntry | null;
  utdata?: Record<string, unknown>;
  kallor?: string[];
  sidoanrop?: StepLogEntry[];
};

export type Kedja = {
  prospect: { id: string; company_name: string; website?: string | null; origin?: string | null };
  kedja: string;
  korningar: { id: string; agent_type: string; created_at: string }[];
  texter: Record<string, string>;
  noder: KedjeNod[];
  stannade: { nod: string; skal: KedjeNod["skal"] } | null;
  skills: { steg: string; skill: string; run_id?: string; delar: SkillDel[]; lager: LagerPost[] }[];
};

export async function hamtaKedja(
  tenantId: string,
  prospectId: string
): Promise<{ kedja?: Kedja; error?: string }> {
  const svar = await masterFetch<{ kedja: Kedja }>(
    `/prospects/${encodeURIComponent(prospectId)}/kedja?tenant_id=${encodeURIComponent(tenantId)}`,
    { method: "GET" }
  );
  return svar.error ? { error: svar.error } : { kedja: svar.data?.kedja };
}

export type KorningSteg = { step_log: StepLogEntry[]; lagertexter: Record<string, string> };

export async function hamtaKorning(runId: string): Promise<{ korning?: KorningSteg; error?: string }> {
  const svar = await masterFetch<{ run: { step_log: StepLogEntry[] | string; lagertexter?: Record<string, string> } }>(
    `/runs/${encodeURIComponent(runId)}`,
    { method: "GET" }
  );
  if (svar.error || !svar.data) return { error: svar.error };
  const rå = svar.data.run.step_log;
  let logg: unknown = rå;
  if (typeof rå === "string") {
    try {
      logg = JSON.parse(rå);
    } catch {
      logg = [];
    }
  }
  return {
    korning: {
      step_log: Array.isArray(logg) ? (logg as StepLogEntry[]) : [],
      lagertexter: svar.data.run.lagertexter ?? {}
    }
  };
}

export type Skillfil = {
  skill: string;
  fil: string;
  text: string;
  tecken: number;
  sha256: string;
  manifest: string;
  orord: boolean;
};

export async function hamtaSkillfil(skill: string, fil: string): Promise<{ fil?: Skillfil; error?: string }> {
  const svar = await masterFetch<{ fil: Skillfil }>(
    `/skills/fil?skill=${encodeURIComponent(skill)}&fil=${encodeURIComponent(fil)}`,
    { method: "GET" }
  );
  return svar.error ? { error: svar.error } : { fil: svar.data?.fil };
}

export type KbProv = {
  fraga: string;
  forsok: string[];
  utan_omformulering: boolean;
  artiklar: { id: string; title: string | null; tecken: number; utdrag: string }[];
};

export async function provaKb(tenantId: string, fraga: string): Promise<{ prov?: KbProv; error?: string }> {
  const svar = await masterFetch<{ prov: KbProv }>(`/tenants/${encodeURIComponent(tenantId)}/insyn/kb-prov`, {
    method: "POST",
    body: JSON.stringify({ fraga })
  });
  return svar.error ? { error: svar.error } : { prov: svar.data?.prov };
}
