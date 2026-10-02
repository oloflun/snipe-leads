/**
 * Prospektets bedömningskriterier — och spärren som gör att ett oväntat
 * fältvärde inte tar ner sidan.
 *
 * ## Varför den här filen finns
 *
 * `score_breakdown` är jsonb (migration 031). asyncpg avkodar varken json eller
 * jsonb utan en typkodare, så kolumnen nådde webbläsaren som en STRÄNG. Två
 * ställen läste den som en lista:
 *
 *   Bolagsregister: `p.score_breakdown?.find(...)`  → "find is not a function"
 *   Bolagssida:     `p.score_breakdown?.length` följt av `.map(...)`
 *
 * Det andra är lömskare: en sträng HAR `.length`, så vakten släppte igenom
 * värdet och `.map` kastade ett steg senare.
 *
 * Följden var att hela vyn ersattes av webbläsarens felruta — statuskod 200,
 * ingenting i serverloggen, inget spår i sviten. Uppmätt på /admin/leads och
 * /admin/contacts 2026-08-23 med `scripts/qa_vyer.mjs`.
 *
 * ## Varför spärren finns kvar trots att backenden är fixad
 *
 * Backendfixen (`_avkoda_prospekt` i storage/postgres.py) är den riktiga
 * lösningen och den bör inte tas bort. Men det är ANDRA gången samma
 * avkodningsmiss slår igenom — `step_log` gick samma väg och fällde adminytans
 * spårvy — och priset för att en tredje kolumn glöms ska inte vara en vit sida.
 *
 * En saknad motivering är ett tomt fält. Det är ett acceptabelt fel. En vy som
 * inte går att öppna är det inte.
 */

import type { Localized } from "@/lib/i18n";

/** Prospektets status (migration 010) i kanbanordning; `suppressed` sist. */
export const STATUS_ORDNING = [
  "new",
  "researching",
  "ready",
  "contacted",
  "replied",
  "meeting",
  "won",
  "lost",
  "suppressed"
] as const;

/** Statusens etikett, delad av Iris › Bolag, tabellen och pipelinen. */
export const STATUS_ETIKETT: Record<string, Localized> = {
  new: { sv: "Ny", en: "New" },
  researching: { sv: "Research pågår", en: "Researching" },
  ready: { sv: "Redo", en: "Ready" },
  contacted: { sv: "Kontaktad", en: "Contacted" },
  replied: { sv: "Svarat", en: "Replied" },
  meeting: { sv: "Möte", en: "Meeting" },
  won: { sv: "Vunnen", en: "Won" },
  lost: { sv: "Förlorad", en: "Lost" },
  suppressed: { sv: "Spärrad", en: "Blocked" }
};

/**
 * Leadets typ ur `origin`, samma mappning som backendens
 * `app/leads/automation.py::typ_av`: inkorg, import och lista är sina egna,
 * allt annat (manual, example, test) är Iris.
 */
export type LeadTyp = "iris" | "lista" | "import" | "inkorg";

export function leadTyp(origin: string | null | undefined): LeadTyp {
  return origin === "inkorg" || origin === "import" || origin === "lista" ? origin : "iris";
}

export const LEAD_TYP_ETIKETT: Record<LeadTyp, Localized> = {
  iris: { sv: "Iris", en: "Iris" },
  lista: { sv: "Lista", en: "List" },
  import: { sv: "Import", en: "Import" },
  inkorg: { sv: "Inkorg", en: "Inbox" }
};

export type Kriterium = {
  /** Bolagssidan nycklar sina rader på den här när den finns. */
  nyckel?: string;
  etikett: string;
  vikt?: number;
  utfall: string;
  motivering: string;
  hart?: boolean;
  /** Iris-bedömningen (2026-09-30): verifierade citat ur källmaterialet. */
  belagg?: { url: string; citat: string }[];
};

/** Kodens nivå (app/leads/bedomning.py) — aldrig modellens eget omdöme. */
export const NIVA_ETIKETT: Record<string, string> = {
  A: "Stark",
  B: "Möjlig",
  C: "Bortvald"
};

/** Utfallen som kunden läser dem. */
export const UTFALL_ETIKETT: Record<string, string> = {
  träff: "Uppfyllt",
  delvis: "Delvis",
  miss: "Uppfylls inte",
  okänd: "Okänt",
  ej_satt: "Ej satt"
};

const NIVA_ETIKETT_EN: Record<string, string> = {
  A: "Strong",
  B: "Possible",
  C: "Ruled out"
};

const UTFALL_ETIKETT_EN: Record<string, string> = {
  träff: "Met",
  delvis: "Partly",
  miss: "Not met",
  okänd: "Unknown",
  ej_satt: "Not set"
};

/** Nivåns etikett på kundens språk (INV-COPY-001); okänd nivå ger `undefined`. */
export function nivaEtikett(niva: string, locale: "sv" | "en"): string | undefined {
  return (locale === "en" ? NIVA_ETIKETT_EN : NIVA_ETIKETT)[niva];
}

/** Utfallets etikett på kundens språk; okänt utfall ger `undefined`. */
export function utfallEtikett(utfall: string, locale: "sv" | "en"): string | undefined {
  return (locale === "en" ? UTFALL_ETIKETT_EN : UTFALL_ETIKETT)[utfall];
}

function arKriterium(v: unknown): v is Kriterium {
  return (
    typeof v === "object" &&
    v !== null &&
    typeof (v as Kriterium).etikett === "string" &&
    typeof (v as Kriterium).utfall === "string"
  );
}

/**
 * Kriterierna som en lista, vad backenden än skickade.
 *
 * Tar emot listan (det normala), en JSON-sträng (den avkodningsmiss som gav
 * upphov till filen), null, eller något annat — och ger alltid en array.
 * Anropare kan därför använda `.find`, `.map` och `.length` utan vakt.
 */
export function kriterier(varde: unknown): Kriterium[] {
  let rått = varde;

  if (typeof rått === "string") {
    try {
      rått = JSON.parse(rått);
    } catch {
      return [];
    }
  }

  if (!Array.isArray(rått)) return [];
  return rått.filter(arKriterium);
}
