"use client";

import { useState } from "react";
import type { Rad } from "@/lib/admin/radgivare";
import { EXEMPELFRAGOR, fragaRadgivaren } from "@/lib/admin/radgivare";

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
  const [turer, setTurer] = useState<Tur[]>([]);
  const [input, setInput] = useState("");

  function fraga(text: string) {
    const rensad = text.trim();
    if (!rensad) return;
    const svar = fragaRadgivaren(rensad, rader);
    setTurer((f) => [
      ...f,
      { fran: "du", text: rensad },
      { fran: "radgivare", text: svar.text, foljdfragor: svar.foljdfragor }
    ]);
    setInput("");
  }

  const forslag = turer.length === 0 ? [...EXEMPELFRAGOR] : (turer.at(-1)?.foljdfragor ?? []);

  return (
    <section
      aria-labelledby="radgivare-rubrik"
      className="mt-12 rounded-card border border-ink/15 bg-paper2/50 p-6 md:p-7"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id="radgivare-rubrik" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          Fråga om siffrorna
        </h2>
        <span className="kicker text-mineral">Räknar lokalt · ingen modell</span>
      </div>

      <p className="mt-2 max-w-[70ch] text-[0.875rem] leading-[1.6] text-ink/65">
        Svaren räknas ur samma data som tabellen ovan. De kan inte säga emot vad du ser, och de
        kan inte hitta på ett tal — men rådgivaren förstår bara frågor den känner igen, och
        säger till när den inte gör det.
      </p>

      {turer.length > 0 ? (
        <div className="mt-6 flex flex-col gap-4">
          {turer.map((tur, i) => (
            <div key={i} className={tur.fran === "du" ? "text-right" : ""}>
              <p className="kicker text-mineral">{tur.fran === "du" ? "Du" : "Rådgivaren"}</p>
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
          placeholder="Skriv en fråga om intäkter, kostnad eller risk"
          className="h-12 min-w-0 flex-1 rounded-input border border-ink/20 bg-paper px-4 text-[0.9375rem] focus:border-ochre"
        />
        <button
          type="submit"
          className="focus-ring min-h-12 shrink-0 rounded-input bg-ink px-5 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
        >
          Fråga
        </button>
      </form>
    </section>
  );
}
