"use client";

import { useState } from "react";
import { Panelrubrik } from "@/components/dashboard/OversiktPaneler";
import { btnPrimary, etikett, panelKort } from "@/components/ui";
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
 *
 * Överraden "Räknar lokalt · ingen modell" och ingressen om att svaren inte
 * kan säga emot tabellen togs bort 2026-09-27 (F-016): de beskrev verktyget
 * i stället för att använda det. Att rådgivaren säger till när den inte
 * förstår en fråga syns i dess eget svar.
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
    // Ett kort som Översiktens övriga paneler (2026-10-07). Samtalets platta
    // står kvar inne i kortet: bubblornas pappersyta behöver något att ligga på.
    <section aria-labelledby="radgivare-rubrik" className={panelKort}>
      <Panelrubrik id="radgivare-rubrik" titel={{ sv: "Fråga om siffrorna", en: "Ask about the figures" }} />
      <div className="rounded-input bg-paper2/60 p-4 md:p-5">
        {turer.length > 0 ? (
          <div className="flex flex-col gap-4">
            {turer.map((tur, i) => (
              <div key={i} className={tur.fran === "du" ? "text-right" : ""}>
                <p className={etikett}>
                  {tur.fran === "du"
                    ? text({ sv: "Du", en: "You" })
                    : text({ sv: "Rådgivaren", en: "The adviser" })}
                </p>
                <p
                  className={`mt-1 inline-block max-w-[68ch] whitespace-pre-line rounded-input px-4 py-3 text-left text-[0.9375rem] leading-[1.6] ${
                    tur.fran === "du" ? "bg-ink text-paper" : "bg-paper text-ink-muted"
                  }`}
                >
                  {tur.text}
                </p>
              </div>
            ))}
          </div>
        ) : null}

        {forslag.length > 0 ? (
          <div className={`${turer.length > 0 ? "mt-5 " : ""}flex flex-wrap gap-2`}>
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
            aria-label={text({ sv: "Din fråga", en: "Your question" })}
            placeholder={text({
              sv: "Skriv en fråga om intäkter, kostnad eller risk",
              en: "Ask a question about revenue, cost or risk"
            })}
            className="h-12 min-w-0 flex-1 rounded-input border border-ink/20 bg-paper px-4 text-[1rem] focus:border-ochre"
          />
          <button type="submit" className={`${btnPrimary} shrink-0`}>
            {text({ sv: "Fråga", en: "Ask" })}
          </button>
        </form>
      </div>
    </section>
  );
}
