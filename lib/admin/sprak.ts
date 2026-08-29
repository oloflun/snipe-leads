import type { Locale, Localized } from "@/lib/i18n";

/**
 * Adminytans texter på svenska och engelska.
 *
 * ## Varför de ligger samlade här och inte i komponenterna
 *
 * `lib/i18n.tsx` bär appens GEMENSAMMA copy — navigation, knappar, statusord.
 * Adminytans texter är många, långa och används på ett enda ställe var; hade
 * de lagts i samma ordbok hade den gemensamma ordboken blivit en adminordbok
 * med lite navigation i.
 *
 * Alternativet — `text({ sv: "…", en: "…" })` direkt i JSX — prövades och gör
 * tabellrubriker oläsbara: en rad med nio kolumnrubriker blev nio inbäddade
 * objekt i en map. Här står svenskan och engelskan bredvid varandra, vilket
 * också är det enda sättet att SE att en text saknar sin översättning.
 *
 * Nyckelnamnen är svenska av samma skäl som resten av kodbasen är det.
 */

export const ADMIN: Record<string, Localized> = {
  /* -------------------------------------------------- Översikt */
  oversiktRubrik: { sv: "Översikt", en: "Overview" },
  manadsintakt: { sv: "Månadsintäkt", en: "Monthly revenue" },
  uppskattadKostnad: { sv: "Uppskattad kostnad", en: "Estimated cost" },
  tokensAllaKunder: { sv: "Tokens, alla kunder", en: "Tokens, all customers" },
  marginal: { sv: "Marginal", en: "Margin" },
  ingenIntakt: { sv: "Ingen intäkt att räkna på", en: "No revenue to measure against" },
  intaktMinusToken: { sv: "Intäkt minus tokenkostnad", en: "Revenue minus token cost" },
  kraverAtgard: { sv: "Kräver åtgärd", en: "Needs attention" },

  /* -------------------------------------------------- Kolumner */
  kolKund: { sv: "Kund", en: "Customer" },
  kolPaket: { sv: "Paket", en: "Plan" },
  kolArenden: { sv: "Ärenden", en: "Tickets" },
  kolKorningar: { sv: "Körningar", en: "Runs" },
  kolTokens: { sv: "Tokens", en: "Tokens" },
  kolKostnad: { sv: "Kostnad", en: "Cost" },
  kolMarginal: { sv: "Marginal", en: "Margin" },
  kolFel: { sv: "Fel", en: "Errors" },
  kolSlug: { sv: "Slug", en: "Slug" },
  kolKundSedan: { sv: "Kund sedan", en: "Customer since" },
  kolAvtal: { sv: "Avtal", en: "Contract" },
  kolSenastAktiv: { sv: "Senast aktiv", en: "Last active" },

  /* -------------------------------------------------- Hälsa */
  halsaBra: { sv: "Bra", en: "Healthy" },
  halsaOk: { sv: "Håll koll", en: "Watch" },
  halsaDalig: { sv: "Åtgärda", en: "Act now" },
  halsaTyst: { sv: "Tyst", en: "Dormant" },
  halsaOkand: { sv: "Okänd", en: "Unknown" },

  /* -------------------------------------------------- Fotnoter, Översikt */
  ingaKunder: {
    sv: "Inga kunder ännu. Tom lista är ett giltigt svar, inte ett fel.",
    en: "No customers yet. An empty list is a valid answer, not a failure."
  },
  seAllaKorningar: { sv: "Se alla körningar", en: "See all runs" },
  perManad: { sv: "/mån", en: "/mo" },
  test: { sv: "test", en: "test" },

  /* -------------------------------------------------- Kunder & Data */
  kunderRubrik: { sv: "Kunder & Data", en: "Customers & Data" },
  kunderIngress: {
    sv: "Alla registrerade kunder med volym, avtal och senaste aktivitet. Klicka på kundnamnet för kontaktpersoner och faktureringsuppgifter. Ekonomin och hälsobedömningen ligger under Översikt.",
    en: "Every registered customer with volume, contract and last activity. Click a customer name for contacts and billing details. Finances and the health assessment live under Overview."
  },
  ingaRegistrerade: {
    sv: "Inga kunder registrerade ännu.",
    en: "No customers registered yet."
  },
  saknas: { sv: "saknas", en: "missing" },
  inget: { sv: "inget", en: "none" },
  profil: { sv: "Profil", en: "Profile" },
  oppnaProfilen: { sv: "Öppna agentprofilen för", en: "Open the agent profile for" },
  profilOchArbetsyta: { sv: "Profil och arbetsyta", en: "Profile and workspace" },

  /* -------------------------------------------------- Statistik */
  statistik: { sv: "Statistik", en: "Statistics" },
  statistikIngress: {
    sv: "Signerade avtal och nya kunder över tid. Försäljningstakten nedan är definierad som nya kunder och signerade avtal per vecka — säg till om den ska mäta något annat.",
    en: "Signed contracts and new customers over time. The sales rate below is defined as new customers and signed contracts per week — say so if it should measure something else."
  },
  avtalIdag: { sv: "Avtal i dag", en: "Contracts today" },
  avtalVeckan: { sv: "Avtal denna vecka", en: "Contracts this week" },
  avtalManaden: { sv: "Avtal denna månad", en: "Contracts this month" },
  avtalAret: { sv: "Avtal i år", en: "Contracts this year" },
  nyaKunder: { sv: "Nya kunder", en: "New customers" },
  signeradeAvtal: { sv: "Signerade avtal", en: "Signed contracts" },
  perVecka12: { sv: "per vecka, senaste 12 veckorna", en: "per week, last 12 weeks" },
  visaSomTabell: { sv: "Visa som tabell", en: "Show as table" },
  vecka: { sv: "Vecka", en: "Week" },

  /* -------------------------------------------------- Fel & eskaleringar */
  felOchEskaleringar: { sv: "Fel & eskaleringar", en: "Errors & escalations" },
  eskaleradeArenden: { sv: "Eskalerade ärenden", en: "Escalated tickets" },
  allaKunderTotalt: { sv: "alla kunder, totalt", en: "all customers, total" },
  handelser: { sv: "Händelser", en: "Events" },
  minst: { sv: "minst ", en: "at least " },
  ggr: { sv: "ggr", en: "times" },
  tillKorningen: { sv: "till körningen", en: "to the run" },
  plattformsniva: { sv: "plattformsnivå", en: "platform level" },

  /* -------------------------------------------------- Händelser */
  filterAlla: { sv: "Alla", en: "All" },
  filterFel: { sv: "Fel", en: "Errors" },
  filterVarningar: { sv: "Varningar", en: "Warnings" },
  filterInfo: { sv: "Info", en: "Info" },
  handelserIngress: {
    sv: "Allt som plattformen loggat, grupperat på källa och orsak. Samma fel hundra gånger är ett problem, inte hundra — antalet står vid raden.",
    en: "Everything the platform has logged, grouped by source and cause. The same error a hundred times is one problem, not a hundred — the count sits on the row."
  },
  ingaHandelser: {
    sv: "Inga händelser. Det är det önskade tillståndet.",
    en: "No events. That is the desired state."
  },
  ingaHandelserFilter: {
    sv: "Inga händelser på den här nivån.",
    en: "No events at this level."
  },
  tekniskaDetaljer: { sv: "Tekniska detaljer", en: "Technical detail" },
  senast: { sv: "Senast", en: "Last seen" },
  forsta: { sv: "första", en: "first" },

  /* -------------------------------------------------- Exempeldata */
  exempel: { sv: "Exempel", en: "Example" },
  exempeldataMarkning: {
    sv: "Exempeldata — arbetsytan har ingen egen aktivitet",
    en: "Example data — this workspace has no activity of its own"
  }
};

/** `ADMIN`-uppslagning för ett känt språk. Kortare än `text(ADMIN.x)` i JSX. */
export function a(nyckel: keyof typeof ADMIN, locale: Locale): string {
  return ADMIN[nyckel][locale];
}

/**
 * TIDSZONEN ÄR SPIKAD, och det är inte en detalj.
 *
 * Vyerna som kallar de här funktionerna är klientkomponenter, och en
 * klientkomponent renderas TVÅ gånger: en gång på servern (SSR) och en gång i
 * webbläsaren (hydrering). Servern kör i UTC, webbläsaren i besökarens zon. En
 * tidsstämpel som `2026-08-26T23:30:00Z` blir då 26 augusti på servern och 27
 * augusti i Stockholm — olika text på samma rad, alltså en hydreringskrock.
 *
 * `Europe/Stockholm` och inte besökarens zon: det ÄR besökarens zon här (en
 * intern driftvy för ett svenskt bolag), och en fast zon är det enda som gör
 * de två renderingarna identiska. Bonus: raderna visar numera lokal tid i
 * stället för den råa UTC-strängen den gamla vyn skrev ut.
 */
const TIDSZON = "Europe/Stockholm";

/**
 * Datum enligt språkvalet.
 *
 * `sv-SE` ger 2026-08-29 och `en-GB` ger 29/08/2026 — INTE `en-US`, som hade
 * gett 8/29/2026. En intern driftvy läses av folk som skriver datum bakifrån,
 * och den amerikanska ordningen är den enda som går att missläsa som en annan
 * giltig dag.
 */
export function datum(varde: string | null | undefined, locale: Locale): string {
  if (!varde) return "—";
  const d = new Date(varde);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(locale === "sv" ? "sv-SE" : "en-GB", { timeZone: TIDSZON });
}

/** Tidsstämpel i listor: datum och klockslag, utan sekunder och utan T. */
export function tidpunkt(varde: string, locale: Locale): string {
  const d = new Date(varde);
  if (Number.isNaN(d.getTime())) return varde.slice(0, 19).replace("T", " ");
  return d.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
    timeZone: TIDSZON,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

/** Tusentalsavgränsat heltal enligt språkvalet. */
export function antal(varde: number, locale: Locale): string {
  return varde.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");
}
