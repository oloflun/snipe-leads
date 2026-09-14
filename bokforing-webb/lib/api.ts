/**
 * Typerna för bokförings-API:t, delade mellan vyerna.
 *
 * BAS pekar på sajtens egen proxy (app/api/bk/[...path]/route.ts), som sätter
 * X-API-Key på serversidan — nyckeln finns aldrig i webbläsaren.
 */

export const BAS = "/api/bk";

/** Speglar backendens `LASBARA_MIMETYPER` (app/bookkeeping/underlag.py). */
export const LASBARA = ".pdf,image/jpeg,image/png,image/webp,image/heic";

export type Underlag = {
  id: string;
  filnamn: string;
  status: string;
  datum: string | null;
  motpart: string | null;
  /** STRÄNG, aldrig number — se lib/format.ts. */
  brutto: string | null;
  momssats: string | null;
  kategori: string | null;
  riktning: string | null;
  betalstatus: string | null;
  anmarkning: string;
};

export type Summor = Record<string, string> & { antal_poster: number };

export type Rapport = {
  fran: string;
  till: string;
  status: string;
  brister: string[];
  summor: Summor;
  antal_underlag: number;
  antal_verifikat: number;
};
