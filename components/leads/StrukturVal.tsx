"use client";

import { useEffect, useState } from "react";
import { useLocale, type Localized } from "@/lib/i18n";
import { lasStruktur, sparaStruktur, type Struktur } from "@/lib/leads/struktur";
import { cn } from "@/lib/utils";

/**
 * A/B-väljaren för utkastens struktur (Sebbe 2026-11-05). En komponent för
 * alla ställen där ett utkast skapas: Kör Iris, "Skapa utkast" på bolaget, i
 * registret och i Iris bolagslista, och automationens körningar. Samma val,
 * samma ord, så att B finns överallt där A finns.
 */

const T = {
  etikett: { sv: "Mejlens struktur", en: "Email structure" },
  a: { sv: "Utförlig", en: "Detailed" },
  b: { sv: "Kort och rakt på", en: "Short and direct" },
  aText: {
    sv: "Dagens mejl: en ingång om dem, vad agenten gör, erbjudandet och en inbjudan.",
    en: "Today's email: an opening about them, what the agent does, the offer and an invitation."
  },
  bText: {
    sv: "Ett kort mejl som slutar med en fråga om vad agenten kan ge dem. Samma signatur, logga, fot och granskning som A.",
    en: "A short email that ends with a question about what the agent can do for them. Same signature, logo, footer and review as A."
  }
} satisfies Record<string, Localized>;

/** Senaste valet i den här webbläsaren, läst efter monteringen (ingen hydreringskrock). */
export function useStruktur(): [Struktur, (v: Struktur) => void] {
  const [struktur, setStruktur] = useState<Struktur>("a");
  useEffect(() => {
    setStruktur(lasStruktur());
  }, []);
  return [
    struktur,
    (v: Struktur) => {
      setStruktur(v);
      sparaStruktur(v);
    }
  ];
}

export function StrukturVal({
  value,
  onChange,
  etikett,
  beskrivning = true,
  disabled = false,
  className
}: Readonly<{
  value: Struktur;
  onChange: (v: Struktur) => void;
  /** Rubrik över valet; standard "Mejlens struktur". */
  etikett?: Localized;
  /** Förklaringen under valet; av där utrymmet är litet. */
  beskrivning?: boolean;
  disabled?: boolean;
  className?: string;
}>) {
  const { text } = useLocale();
  const rubrik = text(etikett ?? T.etikett);
  return (
    <fieldset className={className} disabled={disabled}>
      <legend className="text-[13px] font-medium text-ink-muted">{rubrik}</legend>
      <div className="mt-1.5 flex flex-wrap gap-2" role="radiogroup" aria-label={rubrik}>
        {(["a", "b"] as const).map((v) => {
          const vald = value === v;
          return (
            <button
              key={v}
              type="button"
              role="radio"
              aria-checked={vald}
              onClick={() => onChange(v)}
              className={cn(
                "focus-ring min-h-11 rounded-input border px-4 py-2 text-left text-[14px] transition-colors disabled:opacity-60",
                vald
                  ? "border-ochre bg-ochre/10 text-ink"
                  : "border-ink/15 bg-paper2/50 text-ink-muted hover:border-ink/30 hover:text-ink"
              )}
            >
              <span className="font-semibold">{v.toUpperCase()}</span>
              <span className="ml-2">{text(v === "a" ? T.a : T.b)}</span>
            </button>
          );
        })}
      </div>
      {beskrivning ? (
        <p className="mt-2 max-w-[62ch] text-[13px] leading-5 text-ink-subtle">{text(value === "a" ? T.aText : T.bText)}</p>
      ) : null}
    </fieldset>
  );
}
