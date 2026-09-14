"use client";

import { useState } from "react";
import type { Rad } from "@/lib/admin/radgivare";
import { useLocale } from "@/lib/i18n";
import { exempelfragor, fragaRadgivaren } from "@/lib/admin/radgivare";

/**
 * Rådgivaren, som svarar på frågor om siffrorna.
 *
 * Den räknar i webbläsaren på exakt den data tabellen ovanför visar. Inget
 * nätverksanrop, ingen modell, ingen nyckel — och därmed inget svar som kan
 * säga emot skärmen eller hitta på ett tal. Se lib/admin/radgivare.ts om
 * varför det valet är viktigare här än på andra ytor.
 */

type Tur = { fran: "du" | "radgivare"; text: string; foljdfragor?: string[] };

export function Radgivare({ rader }: Readonly<{ rader: Rad[] }>) {
  const { locale, text } = useLocale();
  const [turer, setTurer] = useState<Tur[]>([]);
  const [input, setInput] = useState("");

  function fraga(text: string) {
    const rensad = text.trim();
    if (!rensad) return;
    // Språket skickas med: både svaret OCH följdfrågorna formuleras på det
    // språk gränssnittet står i. Ett svenskt svar under en engelsk rubrik är
    // värre än ingen översättning alls — det ser ut som ett fel i datan.
    const svar = fragaRadgivaren(rensad, rader, locale);
    setTurer((f) => [
      ...f,
      { fran: "du", text: rensad },
      { fran: "radgivare", text: svar.text, foljdfragor: svar.foljdfragor }
    ]);
    setInput("");
  }

  const forslag = turer.length === 0 ? exempelfragor(locale) : (turer.at(-1)?.foljdfragor ?? []);

  return (
    <section
      aria-labelledby="radgivare-rubrik"
      className="mt-12 rounded-card border border-ink/15 bg-paper2/50 p-6 md:p-7"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id="radgivare-rubrik" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          {text({ sv: "Fråga om siffrorna", en: "Ask about the figures" })}
        </h2>
        <span className="kicker text-mineral">
          {text({ sv: "Räknar lokalt · ingen modell", en: "Computed locally · no model" })}
        </span>
      </div>

      <p className="mt-2 max-w-[70ch] text-[0.875rem] leading-[1.6] text-ink/65">
        {text({
          sv: "Svaren räknas ur samma data som tabellen ovan. De kan inte säga emot vad du ser, och de kan inte hitta på ett tal — men rådgivaren förstår bara frågor den känner igen, och säger till när den inte gör det.",
          en: "Answers are computed from the same data as the table above. They cannot contradict what you see, and they cannot invent a number — but the adviser only understands questions it recognises, and says so when it does not."
        })}
      </p>

      {turer.length > 0 ? (
        <div className="mt-6 flex flex-col gap-4">
          {turer.map((tur, i) => (
            <div key={i} className={tur.fran === "du" ? "text-right" : ""}>
              <p className="kicker text-mineral">
                {tur.fran === "du"
                  ? text({ sv: "Du", en: "You" })
                  : text({ sv: "Rådgivaren", en: "The adviser" })}
              </p>
              <p
                className={`mt-1 inline-block max-w-[68ch] whitespace-pre-line rounded-input px-4 py-3 text-left text-[0.9375rem] leading-[1.6] ${
                  tur.fran === "du" ? "bg-ink text-paper" : "bg-paper text-ink/85"
                }`}
              >
                {tur.text}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {forslag.length > 0 ? (
        <div className="mt-5 flex flex-wrap gap-2">
          {forslag.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => fraga(f)}
              className="focus-ring min-h-10 rounded-input border border-ink/20 bg-paper px-3 text-[0.875rem] transition-colors hover:bg-paper2"
            >
              {f}
            </button>
          ))}
        </div>
      ) : null}

      <form
        className="mt-5 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          fraga(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={text({
            sv: "Skriv en fråga om intäkter, kostnad eller risk",
            en: "Ask a question about revenue, cost or risk"
          })}
          className="h-12 min-w-0 flex-1 rounded-input border border-ink/20 bg-paper px-4 text-[0.9375rem] focus:border-ochre"
        />
        <button
          type="submit"
          className="focus-ring min-h-12 shrink-0 rounded-input bg-ink px-5 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
        >
          {text({ sv: "Fråga", en: "Ask" })}
        </button>
      </form>
    </section>
  );
}
