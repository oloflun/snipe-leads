"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "sv" | "en";
export type Localized = { sv: string; en: string };

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  text: (value: Localized) => string;
  t: (key: CopyKey) => string;
};

const commonCopy = {
  "action.start": { sv: "Starta gratis", en: "Start free" },
  "action.demo": { sv: "Boka demo", en: "Book demo" },
  "action.open": { sv: "Öppna", en: "Open" },
  "action.rewrite": { sv: "Skriv om", en: "Rewrite" },
  "action.shorter": { sv: "Kortare", en: "Shorter" },
  "action.professional": { sv: "Mer professionell", en: "More professional" },
  "action.human": { sv: "Mer mänsklig", en: "More human" },
  "action.persuasive": { sv: "Mer övertygande", en: "More persuasive" },
  "nav.dashboard": { sv: "Översikt", en: "Dashboard" },
  "nav.assistant": { sv: "Assistant", en: "Assistant" },
  "nav.leads": { sv: "Leads", en: "Leads" },
  "nav.companies": { sv: "Företag", en: "Companies" },
  "nav.contacts": { sv: "Kontakter", en: "Contacts" },
  "nav.emails": { sv: "Email studio", en: "Email studio" },
  "nav.leadsControl": { sv: "Kontroll", en: "Controls" },
  "nav.leadslistor": { sv: "Leadslistor", en: "Lead lists" },
  "nav.support": { sv: "Kundtjänst", en: "Support" },
  "nav.analytics": { sv: "Analys", en: "Analytics" },
  "nav.bokforing": { sv: "Bokföring", en: "Bookkeeping" },
  "nav.inbox": { sv: "Svar", en: "Replies" },
  "nav.larande": { sv: "Lärande", en: "Learning" },
  "nav.settings": { sv: "Inställningar", en: "Settings" },
  "state.loading": { sv: "Laddar arbetsyta", en: "Loading workspace" },
  "state.empty": { sv: "Inga poster ännu", en: "No records yet" },
  "status.ready": { sv: "Redo", en: "Ready" },
  "status.paused": { sv: "Pausad", en: "Paused" },
  "status.active": { sv: "Aktiv", en: "Active" },
  "status.draft": { sv: "Utkast", en: "Draft" }
} satisfies Record<string, Localized>;

export type CopyKey = keyof typeof commonCopy;

const LocaleContext = createContext<LocaleContextValue | null>(null);

/**
 * Var valet sparas. `localStorage` och inte bara React-state: providern sitter
 * i rot-layouten, så klientnavigering behåller språket — men en omladdning,
 * en ny flik eller en server action som svarar med en redirect monterar om
 * trädet, och då snäppte valet tillbaka till svenska. Uppmätt: byt till EN i
 * adminytan, ladda om, och halva sidan var svensk igen.
 */
const LAGRINGSNYCKEL = "snajp.locale";

function giltigt(värde: string | null): Locale | null {
  return värde === "sv" || värde === "en" ? värde : null;
}

export function LocaleProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  // Alltid "sv" i första renderingen, aldrig ett läst värde: servern renderade
  // svenska, och ett annat startvärde här ger en hydreringskrock i stället för
  // ett språkbyte. Det lagrade värdet läses in efter monteringen.
  const [locale, setLocaleState] = useState<Locale>("sv");

  useEffect(() => {
    try {
      const sparat = giltigt(window.localStorage.getItem(LAGRINGSNYCKEL));
      if (sparat) setLocaleState(sparat);
    } catch {
      // Privat läge, blockerade kakor, inbäddad vy — språkvalet är inte värt
      // att fälla sidan för. Svenska gäller då, precis som förut.
    }
  }, []);

  const setLocale = useCallback((nästa: Locale) => {
    setLocaleState(nästa);
    try {
      window.localStorage.setItem(LAGRINGSNYCKEL, nästa);
    } catch {
      // Se ovan: valet gäller för den här sessionen även om det inte kan sparas.
    }
  }, []);

  // The document was rendered with lang="sv". Without this the attribute keeps
  // claiming Swedish after the user switches, so a screen reader reads English
  // copy with Swedish pronunciation rules.
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const text = useCallback((value: Localized) => value[locale], [locale]);
  const t = useCallback((key: CopyKey) => commonCopy[key][locale], [locale]);
  const toggleLocale = useCallback(
    () => setLocale(locale === "sv" ? "en" : "sv"),
    [locale, setLocale]
  );

  const value = useMemo(
    () => ({ locale, setLocale, toggleLocale, text, t }),
    [locale, setLocale, text, t, toggleLocale]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return value;
}

export function sv(value: Localized) {
  return value.sv;
}
