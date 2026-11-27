"use client";

import { Selector } from "@astryxdesign/core/Selector";
import { useLocale, type Localized } from "@/lib/i18n";
import type { Struktur } from "@/lib/leads/struktur";

/** Strukturernas namn, samma överallt där en körning eller ett utkast visar sin struktur. */
export const STRUKTURNAMN: Record<Struktur, Localized> = {
  a: { sv: "A, utförlig", en: "A, detailed" },
  b: { sv: "B, kort och rakt på", en: "B, short and direct" }
};

/** Vad varje struktur är, i valets förklaring. */
const STRUKTURVAD: Record<Struktur, Localized> = {
  a: { sv: "En ingång om dem, vad agenten gör, erbjudandet och en inbjudan.", en: "An opening about them, what the agent does, the offer and an invitation." },
  b: { sv: "Ett kort mejl som slutar med en fråga om vad agenten kan ge dem.", en: "A short email that ends with a question about what the agent can do for them." }
};

/**
 * Valet av utkastens struktur, A eller B (LK-135, LR-074): EN komponent för Kör Iris,
 * Skriv om i utkastredigeraren, Skapa utkast i leadets panel och Iris-listans
 * Skapa utkast, så att namnen och förklaringarna aldrig skiljer sig åt. Den minns
 * inget själv: den som använder den sparar valet (`sparaStruktur`) när det ska minnas.
 */
export function StrukturVal({ value, onChange }: Readonly<{ value: Struktur; onChange: (s: Struktur) => void }>) {
  const { text } = useLocale();
  return (
    <Selector
      label={text({ sv: "Mejlens struktur", en: "Email structure" })}
      value={value}
      onChange={(v) => (v === "a" || v === "b") && onChange(v)}
      options={(["a", "b"] as const).map((s) => ({ value: s, label: text(STRUKTURNAMN[s]), description: text(STRUKTURVAD[s]) }))}
      width="100%"
    />
  );
}
