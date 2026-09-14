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

export type Kriterium = {
  /** Bolagssidan nycklar sina rader på den här när den finns. */
  nyckel?: string;
  etikett: string;
  vikt?: number;
  utfall: string;
  motivering: string;
  hart?: boolean;
};

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
