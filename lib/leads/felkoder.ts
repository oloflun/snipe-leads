import type { Localized } from "@/lib/i18n";

/**
 * Backendens felkoder på kundens språk, och besked för ett fallet jobb.
 *
 * Bor i en egen fil utan körtidsimporter så att `node --test` kan läsa den
 * (`lib/leads/suite.ts` drar in komponenter); suite.ts återexporterar allt,
 * så tabellen är en och samma för körningsformuläret och utkastrutorna.
 *
 * Backendens text är svensk; koden är det ytan översätter. Koderna kommer ur
 * `detail.kod` (felsvar), `draft_note_kod` (jobbresultat) och `error_kod`
 * (GET /api/jobs/{id}, snajp-support/app/api/chat.py:_FELKODER).
 */
export const KUNDFELKODER: Record<string, Localized> = {
  // business_context.SAKNAR_PRODUKT: produkterna står under Inställningar ›
  // Iris › Målgrupp och automation (IrisInstallningar renderar IrisProdukter).
  saknar_produkt: {
    sv: "Lägg till minst en produkt under Inställningar › Målgrupp och automation innan Iris skriver utkast.",
    en: "Add at least one product under Settings › Audience and automation before Iris writes drafts."
  },
  // business_context.SAKNAR_BESKRIVNING: texten under Inställningar › Vad ni
  // säljer (/settings/affarskontext) saknas eller är för kort.
  saknar_beskrivning: {
    sv: "Beskrivningen av vad ni säljer saknas eller är för kort för att skriva ett mejl på. Fyll i den under Inställningar › Vad ni säljer och försök igen.",
    en: "The description of what you sell is missing or too short to write an email from. Fill it in under Settings › What you sell and try again."
  },
  // kvotfel.KUNDTEXT_KREDITSLUT
  kreditslut: {
    sv: "AI-kapaciteten är slut hos oss för tillfället. Det beror inte på ditt ärende, och inget har gått förlorat. Vi har larmats och fyller på.",
    en: "Our AI capacity has run out for the moment. It is not caused by your request, and nothing has been lost. We have been alerted and are topping it up."
  },
  // kvotfel.KUNDTEXT_KVOT
  kvot: {
    sv: "AI-leverantörens kvot är slut just nu. Det är inte ett fel i ditt ärende, försök igen om en stund.",
    en: "The AI provider's quota is used up right now. It is not a fault in your request, please try again in a moment."
  },
  // jobs/store.py: jobbet passerade tidsgränsen.
  tidsgrans: {
    sv: "Jobbet tog för lång tid och avbröts. Försök igen.",
    en: "The job took too long and was stopped. Please try again."
  }
};

/** Beskedet när ett jobb fallit utan känd kod. */
export const JOBBFEL_ALLMANT: Localized = {
  sv: "Utkastet kunde inte skapas. Försök igen om en stund.",
  en: "The draft could not be created. Please try again in a moment."
};

/** Felkoden i ett felsvar ({"detail": {"message": …, "kod": …}}), om den är känd. */
export function kundfelkod(kropp: unknown): Localized | null {
  if (!kropp || typeof kropp !== "object") return null;
  const detalj = (kropp as { detail?: unknown }).detail;
  const kod = detalj && typeof detalj === "object" ? (detalj as { kod?: unknown }).kod : null;
  return kandKod(kod) ? KUNDFELKODER[kod] : null;
}

function kandKod(kod: unknown): kod is string {
  return typeof kod === "string" && Object.prototype.hasOwnProperty.call(KUNDFELKODER, kod);
}

/**
 * Ett fallet jobbs besked på båda språken.
 *
 * En känd kod ger tabellens text. Annars får svenskan backendens text (den är
 * svensk och bär diagnosen) och engelskan den allmänna reserven: backendens
 * råa text når aldrig den engelska ytan.
 */
export function jobbfel(
  kod: unknown,
  text?: string | null,
  reserv: Localized = JOBBFEL_ALLMANT
): Localized {
  if (kandKod(kod)) return KUNDFELKODER[kod];
  const svensk = typeof text === "string" ? text.trim() : "";
  return { sv: svensk || reserv.sv, en: reserv.en };
}

/** Ett fel som bär sitt besked på båda språken, så att rutan kan följa språkvalet. */
export class JobbFel extends Error {
  readonly besked: Localized;

  constructor(besked: Localized) {
    super(besked.sv);
    this.besked = besked;
    this.name = "JobbFel";
  }
}
