/**
 * Typerna för leads-ytan, delade mellan vyerna.
 *
 * BAS pekar på sajtens egen proxy (app/api/ag/[...path]/route.ts) — en
 * generisk spegel av backendens tenant-yta. Nyckeln sätts på serversidan
 * (kundsessionens, annars miljöns) och finns aldrig i webbläsaren.
 *
 * Fältnamnen är avlästa ur huvudappens renderare (Bolagsregister,
 * LeadsControls) — backenden serialiserar lagringsraderna rakt av, så det
 * som huvudappen läser är kontraktet som finns.
 */

import type { Eskaleringsregler } from "@/lib/iris";

export const BAS = "/api/ag";

export type Prospekt = {
  id: string;
  company_name: string;
  contact_name?: string | null;
  contact_email?: string | null;
  status?: string | null;
  icp_fit?: number | null;
  qualified?: boolean | null;
  disqualifiers?: string[] | null;
  origin?: string | null;
  ort?: string | null;
  created_at?: string | null;
};

export type KoPost = {
  id: string;
  subject?: string | null;
  body?: string | null;
  prospect_email?: string | null;
  status?: string | null;
  created_at?: string | null;
};

export type Leadslista = {
  id: string;
  titel?: string | null;
  status?: string | null;
  antal?: number | null;
  created_at?: string | null;
};

export type LeadsConfig = {
  autonomy?: string;
  autonomy_description?: string;
  icp?: Record<string, unknown>;
  eskalering?: Eskaleringsregler;
};

export type Jobb = {
  status: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
};
