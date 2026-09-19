"use client";

import { Check, ChevronDown, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EXEMPELRESULTAT, KORSTEG } from "@/lib/demo/leads-korning";
import { btnPrimary } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * Demons körning: färdiggenererad, triggbar, redigerbar.
 *
 * ## Vad den är och inte är
 *
 * Besökaren trycker på knappen, stegen spelas upp och tre exempel­bolag med
 * utkast fälls ut. Ingen modell körs och inget hämtas: allt är skrivet i
 * förväg i lib/demo/leads-korning.ts, och det STÅR ovanför resultatet.
 *
 * LeadsRunForms gamla invändning ("att fejka ett körresultat vore värst av
 * allt") gäller omärkta resultat. Märkta exempel är precis vad demons övriga
 * ytor redan visar — bokföringens förskrivna svar, kundtjänstens
 * exempelärenden — och en leadsdemo där inget går att trycka på visade
 * reglagen men inte produkten.
 *
 * ## Varför utkasten går att redigera HÄR
 *
 * "Ni får ett utkast att ändra i, inte en mall att fylla i" är produktens
 * löfte (UspSection). Då ska demon låta besökaren ändra i utkastet — lokal
 * state, inget sparas och inget skickas.
 */

type Fas = "vilar" | "kor" | "klar";

export function DemoKorning() {
  const [fas, setFas] = useState<Fas>("vilar");
  const [klaraSteg, setKlaraSteg] = useState(0);
  const [oppet, setOppet] = useState<number | null>(0);
  // Utkasten är redigerbara — kopiera in dem i state vid start.
  const [utkast, setUtkast] = useState(() => EXEMPELRESULTAT.map((r) => r.utkast));
  const timers = useRef<number[]>([]);

  // Städa timers vid unmount, annars sätter en lämnad demo state på en
  // död komponent.
  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  function kor() {
    setFas("kor");
    setKlaraSteg(0);
    let ackumulerat = 0;
    KORSTEG.forEach((steg, i) => {
      ackumulerat += steg.varaktighet;
      timers.current.push(
        window.setTimeout(() => {
          setKlaraSteg(i + 1);
          if (i === KORSTEG.length - 1) setFas("klar");
        }, ackumulerat)
      );
    });
  }

  return (
    <div className="mt-6 rounded-card bg-paper2/60 p-5">
      {fas === "vilar" ? (
        <>
          <p className="max-w-[65ch] text-[15px] leading-7 text-ink-muted">
            Prova en färdiggenererad exempelkörning: stegen är desamma som i en
            riktig körning, men bolagen är påhittade och utkasten skrivna i
            förväg. Ingen modell körs och inget skickas.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={kor} className={btnPrimary}>
              Kör exempelkörningen
            </button>
            <Link
              href="/login"
              className="focus-ring text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
            >
              Kör mot er egen målgrupp med ett konto
            </Link>
          </div>
        </>
      ) : (
        <>
          {/* Stegen. Spelas upp i körningens egen takt så att besökaren ser
              ARBETSGÅNGEN, inte bara slutresultatet. */}
          <ol className="grid gap-2" aria-label="Körningens steg">
            {KORSTEG.map((steg, i) => {
              const klar = i < klaraSteg;
              const pagaende = i === klaraSteg && fas === "kor";
              return (
                <li
                  key={steg.text}
                  className={cn(
                    "flex items-center gap-2.5 text-[0.9375rem]",
                    klar ? "text-ink-muted" : pagaende ? "text-ink" : "text-ink-subtle"
                  )}
                >
                  {klar ? (
                    <Check className="h-4 w-4 shrink-0 text-moss" aria-hidden />
                  ) : pagaende ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-warning" aria-hidden />
                  ) : (
                    <span aria-hidden className="inline-block h-4 w-4 shrink-0" />
                  )}
                  {steg.text}
                </li>
              );
            })}
          </ol>

          {fas === "klar" ? (
            <div className="mt-5 border-t border-ink/12 pt-5">
              <p className="text-[0.8125rem] leading-6 text-ink-subtle">
                <strong className="font-semibold text-ink-muted">Exempel.</strong>{" "}
                Bolagen är påhittade och utkasten skrivna i förväg. I produkten
                kommer raderna ur en riktig körning mot er målgrupp.
              </p>

              <ul className="mt-4 divide-y divide-ink/12 border-y border-ink/15" aria-label="Exempelkörningens resultat">
                {EXEMPELRESULTAT.map((resultat, i) => {
                  const arOppet = oppet === i;
                  return (
                    <li key={resultat.bolag}>
                      <button
                        type="button"
                        onClick={() => setOppet(arOppet ? null : i)}
                        aria-expanded={arOppet}
                        className="focus-ring grid w-full grid-cols-12 items-baseline gap-x-4 py-3.5 text-left transition-colors hover:bg-paper2/70"
                      >
                        <span className="col-span-12 min-w-0 sm:col-span-4">
                          <span className="block truncate font-semibold tracking-[-0.01em]">
                            {resultat.bolag}
                          </span>
                          <span className="block truncate text-[0.8125rem] text-ink-subtle">
                            {resultat.kontakt} · {resultat.ort}
                          </span>
                        </span>
                        <span className="col-span-10 mt-1 min-w-0 truncate text-[0.875rem] text-ink-muted sm:col-span-7 sm:mt-0">
                          {resultat.signal}
                        </span>
                        <span className="col-span-2 mt-1 flex justify-end sm:col-span-1 sm:mt-0">
                          <ChevronDown
                            className={cn("h-4 w-4 text-ink-subtle transition-transform", arOppet && "rotate-180")}
                            aria-hidden
                          />
                        </span>
                      </button>

                      {arOppet ? (
                        <div className="pb-5">
                          <p className="max-w-[65ch] text-[0.875rem] leading-6 text-ink-muted">
                            {resultat.behov}
                          </p>
                          <p className="mt-4 text-[0.8125rem] font-medium text-ink-subtle">Ämnesrad</p>
                          <p className="mt-1 text-[1rem] font-semibold tracking-[-0.01em]">
                            {resultat.amne}
                          </p>
                          <label
                            htmlFor={`demo-utkast-${i}`}
                            className="mt-4 block text-[0.8125rem] font-medium text-ink-subtle"
                          >
                            Utkastet, ditt att ändra i
                          </label>
                          <textarea
                            id={`demo-utkast-${i}`}
                            value={utkast[i]}
                            maxLength={4000}
                            onChange={(e) =>
                              setUtkast((u) => u.map((v, j) => (j === i ? e.target.value : v)))
                            }
                            className="focus-ring mt-2 min-h-[200px] w-full resize-y rounded-card border border-ink/12 bg-paper p-4 text-[0.9375rem] leading-7 outline-none transition-colors focus:border-ink/30"
                          />
                          <p className="mt-2 text-[0.8125rem] text-ink-subtle">
                            Inget skickas härifrån. I produkten granskar ni och
                            skickar när ni bestämt er.
                          </p>
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
