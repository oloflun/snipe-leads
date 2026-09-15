/**
 * Typerna för supportytan, delade mellan vyerna.
 *
 * BAS pekar på sajtens egen proxy (app/api/ag/[...path]/route.ts) — en
 * generisk spegel av backendens tenant-yta. Nyckeln sätts på serversidan
 * och finns aldrig i webbläsaren. Fältnamnen är avlästa ur huvudappens
 * renderare (components/snajp/Dashboard.tsx) — det huvudappen läser är
 * kontraktet som finns.
 */

export const BAS = "/api/ag";

export type Klassificering = {
  category?: string | null;
  confidence?: number | null;
};

export type Utkast = {
  id: string;
  content?: string | null;
  status?: string | null;
  confidence?: number | null;
};

export type Mail = {
  id: string;
  from_email?: string | null;
  from_name?: string | null;
  subject?: string | null;
  body?: string | null;
  status?: string | null;
  is_test?: boolean | null;
  classification?: Klassificering | null;
  draft?: Utkast | null;
  created_at?: string | null;
};

export type Inkorgssvar = {
  emails: Mail[];
  category_counts: Record<string, number>;
  status_counts: Record<string, number>;
};

export type KbArtikel = {
  id?: string;
  title?: string | null;
  content?: string | null;
  category?: string | null;
};

export type Regel = {
  category?: string | null;
  mode?: string | null;
};

export type Jobb = {
  status: string;
  result?: { reply?: string; simulation?: boolean } | null;
  error?: string | null;
};
