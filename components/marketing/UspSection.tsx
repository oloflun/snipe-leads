"use client";

import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";

/**
 * Löftet, direkt under hjältebilden.
 *
 * ## Varför siffran står som ett spann och med ett förbehåll
 *
 * Kunden gav "50–70 % av det repetitiva jobbet". Den siffran är ett estimat,
 * inte en uppmätt effekt hos en befintlig kund — och en procentsats utan
 * förbehåll läses som ett garanterat resultat. Blir utfallet 30 % hos den
 * första kunden är det vi som har lovat för mycket, i skrift, på förstasidan.
 *
 * Därför står "räknar vi med" i texten. Det är skillnaden mellan ett estimat
 * och ett löfte, och den skillnaden är hela skälet till att raden inte bara
 * säger "50–70 %".
 *
 * Byt till en uppmätt siffra när ni har en, och ta då bort förbehållet — en
 * mätt siffra tål att stå naken.
 *
 * ## Varför kontrollen upprepas
 *
 * "Du har alltid kontrollen" står både i rubriken och som en egen punkt. Det
 * är avsiktligt: invändningen mot en AI i kundservice är alltid att den svarar
 * fel i kundens namn. Den invändningen ska mötas innan läsaren hinner
 * formulera den, inte längre ner på sidan.
 */

const copy = {
  kicker: { sv: "Vad ni får", en: "What you get" },
  rubrik: {
    sv: "AI som sorterar och svarar, men du har alltid kontrollen",
    en: "AI that sorts and answers, while you stay in control"
  },
  lede: {
    sv: "Vi räknar med att ta bort 50–70 % av det repetitiva jobbet i er kundservice-inkorg. Mejl sorteras automatiskt i rätt fack och får färdiga, korrekta svar — ni behåller alltid sista ordet.",
    en: "We expect to remove 50–70 % of the repetitive work in your support inbox. Emails are sorted into the right category and get complete, accurate drafts — you always have the final say."
  },
  punkter: {
    sv: [
      ["Sorteras automatiskt", "Varje mejl hamnar i rätt fack: garanti, leverans, betalning, teknisk support. Ni slutar sortera för hand."],
      ["Färdiga, korrekta svar", "Agenten svarar utifrån ER kunskapsbas, inte ur en allmän modell. Saknas svaret säger den det i stället för att gissa."],
      ["Ni har sista ordet", "Inget går ut utan att ni bestämt det. De tre första utskicken granskas alltid av en människa, oavsett inställning."]
    ],
    en: [
      ["Sorted automatically", "Every email lands in the right category: warranty, delivery, payment, technical support. No more manual triage."],
      ["Complete, accurate drafts", "The agent answers from YOUR knowledge base, not from a general model. If the answer is missing it says so instead of guessing."],
      ["You have the final say", "Nothing goes out unless you decide it does. The first three sends are always reviewed by a human, whatever the setting."]
    ]
  }
} satisfies Record<string, Localized | { sv: string[][]; en: string[][] }>;

export function UspSection() {
  const { locale, text } = useLocale();
  const punkter = (copy.punkter as { sv: string[][]; en: string[][] })[locale];

  return (
    <section
      id="loftet"
      aria-labelledby="loftet-rubrik"
      className="border-t border-ink/15 bg-paper"
    >
      <div className="mx-auto max-w-[1480px] px-6 py-20 md:px-10 md:py-28">
        <p className="kicker text-mineral">{text(copy.kicker as Localized)}</p>

        <h2
          id="loftet-rubrik"
          className="mt-4 max-w-[22ch] font-display text-[clamp(2rem,4.6vw,3.5rem)] font-semibold leading-[1.03] tracking-[-0.03em]"
        >
          {text(copy.rubrik as Localized)}
        </h2>

        <p className="mt-6 max-w-[58ch] text-[1.125rem] leading-[1.65] text-ink/80">
          {text(copy.lede as Localized)}
        </p>

        <div className="mt-14 grid gap-8 md:grid-cols-3 md:gap-10">
          {punkter.map(([rubrik, brod], i) => (
            <div key={rubrik} className="border-t border-ink/15 pt-5">
              <span className="kicker text-ochre">0{i + 1}</span>
              <h3 className="mt-3 text-[1.0625rem] font-semibold tracking-[-0.01em]">{rubrik}</h3>
              <p className="mt-2 max-w-[42ch] text-[0.9375rem] leading-[1.6] text-ink/70">
                {brod}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
