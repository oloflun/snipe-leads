"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

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
  "nav.campaigns": { sv: "Kampanjer", en: "Campaigns" },
  "nav.emails": { sv: "Emails", en: "Emails" },
  "nav.snajpSupport": { sv: "Snajp-Support", en: "Snajp-Support" },
  "nav.kundtjanst": { sv: "Kundtjänst", en: "Support desk" },
  "nav.analytics": { sv: "Analys", en: "Analytics" },
  "nav.inbox": { sv: "Inkorg", en: "Inbox" },
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

export function LocaleProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [locale, setLocale] = useState<Locale>("sv");

  const text = useCallback((value: Localized) => value[locale], [locale]);
  const t = useCallback((key: CopyKey) => commonCopy[key][locale], [locale]);
  const toggleLocale = useCallback(() => setLocale((current) => (current === "sv" ? "en" : "sv")), []);

  const value = useMemo(
    () => ({ locale, setLocale, toggleLocale, text, t }),
    [locale, text, t, toggleLocale]
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
