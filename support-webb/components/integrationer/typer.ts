/**
 * Kontraktet mot /api/integrationer och /api/kanaler (snajp-support,
 * bd snipe-36u). Fältnamnen är backendens — se app/api/integrationer.py och
 * app/api/kanaler.py.
 */

import { HttpJsonError, readJsonBody } from "@/lib/http/json";

export type Integrationstyp = "http" | "mcp";

export type Integration = {
  id: string;
  typ: Integrationstyp;
  namn: string;
  beskrivning: string;
  konfig: Record<string, unknown>;
  /** Namn -> "[hemlighet]". Värdet lämnar aldrig backenden. */
  hemligheter: Record<string, string>;
  aktiv: boolean;
  updated_at?: string | null;
};

export type IntegrationsSvar = {
  integrationer: Integration[];
  kontextvarden: string[];
  handelser: Record<string, string[]>;
};

export type SchemaEgenskap = {
  type?: string;
  description?: string;
  enum?: unknown[];
  default?: unknown;
};

export type JsonSchema = {
  type?: string;
  properties?: Record<string, SchemaEgenskap>;
  required?: string[];
};

export type Verktyg = {
  namn: string;
  forfragan?: string;
  beskrivning: string;
  argument: JsonSchema;
  skrivande: boolean;
  handelse?: string | null;
  synligt_for_agenten: boolean;
};

export type Provresultat = {
  verktyg: string;
  data?: string;
  status?: number;
  fel?: string;
  simulerat?: boolean;
};

export type Kanalnamn = "whatsapp" | "messenger" | "slack" | "teams";

export type Anslutning = {
  id: string;
  kanal: Kanalnamn;
  namn: string;
  extern_id: string;
  konfig: Record<string, string>;
  hemligheter: Record<string, string>;
  aktiv: boolean;
  webhook_url: string | null;
  saknade_hemligheter: string[];
};

export type KanalSvar = {
  anslutningar: Anslutning[];
  kanaler: Record<Kanalnamn, { hemligheter: string[]; extern_id: string }>;
  webhook_bas: string | null;
};

/**
 * Läser ett svar och kastar med BACKENDENS besked vid fel.
 *
 * `readJson` i lib/http/json.ts läser bara fältet `error`, men FastAPI svarar
 * `detail` — och här är beskedet hela poängen ("Konfigurationen använder
 * hemligheter som inte är sparade: {{hemlighet.token}}"). En generisk
 * "oväntat svar (status 422)" hade lämnat admin att gissa vad som var fel.
 * 401/403 får däremot den vanliga sessionstexten: där vet backenden mindre
 * om vad användaren ska göra än sidan gör.
 */
export async function las<T>(svar: Response): Promise<T> {
  const kropp = await readJsonBody<unknown>(svar);
  if (svar.ok) return kropp as T;
  if (svar.status === 401 || svar.status === 403) {
    throw new HttpJsonError("Din session har gått ut. Ladda om sidan och logga in igen.", svar.status, kropp);
  }
  const detalj = (kropp as { detail?: unknown; error?: unknown } | null)?.detail ??
    (kropp as { error?: unknown } | null)?.error;
  if (typeof detalj === "string") throw new HttpJsonError(detalj, svar.status, kropp);
  if (Array.isArray(detalj)) {
    // Pydantics valideringslista: [{loc: ["body", "namn"], msg: "..."}]
    const rader = detalj
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const falt = (d.loc ?? []).filter((x) => x !== "body").join(".");
        return falt ? `${falt}: ${d.msg ?? ""}` : d.msg ?? "";
      })
      .filter(Boolean);
    if (rader.length) throw new HttpJsonError(rader.join(" · "), svar.status, kropp);
  }
  throw new HttpJsonError(`Oväntat svar från servern (status ${svar.status}).`, svar.status, kropp);
}

export function skicka(metod: string, url: string, kropp?: unknown): Promise<Response> {
  return fetch(url, {
    method: metod,
    headers: kropp === undefined ? undefined : { "Content-Type": "application/json" },
    body: kropp === undefined ? undefined : JSON.stringify(kropp),
    cache: "no-store"
  });
}

/** Ändringar i hemligheter: ett värde sätter, null tar bort. Oförändrade utelämnas. */
export type Hemlighetsandringar = Record<string, string | null>;

export const faltklass =
  "focus-ring mt-1.5 h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] placeholder:text-ink/35";

export const textfaltklass =
  "focus-ring mt-1.5 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6 placeholder:text-ink/35";
