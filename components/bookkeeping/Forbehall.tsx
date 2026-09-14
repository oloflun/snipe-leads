"use client";

import { Info } from "lucide-react";

/**
 * Förbehållet, hopfällt.
 *
 * ## Varför det ser ut så här och inte som förut
 *
 * Texten stod som ett stycke överst på sidan: fyra rader juridik före det
 * användaren kom för. Den togs bort 2026-08-24 på begäran, och det var rätt
 * beslut om placeringen — men det gjorde också att kunden inte längre möter
 * villkoret någonstans i gränssnittet, bara i API-svar de aldrig ser.
 *
 * En hopfälld `<details>` löser bägge: en rad när den är stängd, hela texten ett
 * klick bort, och den finns på varje sidvisning i stället för i en ruta som
 * klickas bort en gång och sedan aldrig mer.
 *
 * ## Varför `<details>` och inte en egen utfällning
 *
 * Elementet är sökbart med webbläsarens egen sidsökning även när det är
 * stängt i moderna webbläsare, det går att öppna utan JavaScript, och
 * skärmläsare läser upp det som den utfällbara det är. En knapp med
 * `useState` hade gett tre av de sakerna sämre och noll bättre.
 *
 * ## Var texten bor
 *
 * `FORBEHALL` i `snajp-support/app/agent/bookkeeping_agent.py` är originalet —
 * den följer med varje API-svar och SIE-export. Den här kopian är för ögat.
 * Ändras den ena ska den andra ändras samtidigt; de säger samma sak med flit.
 */

export function Forbehall() {
  return (
    <details className="group mt-10 border-t border-ink/15 pt-4">
      <summary className="focus-ring flex cursor-pointer list-none items-center gap-2 rounded-input text-[0.8125rem] text-ink/50 hover:text-ink/75">
        <Info className="h-3.5 w-3.5 shrink-0" aria-hidden />
        Förslag, inte bokföring
        <span aria-hidden className="text-ink/35 transition-transform group-open:rotate-90">
          ›
        </span>
      </summary>
      <p className="mt-3 max-w-[78ch] text-[0.8125rem] leading-6 text-ink/55">
        Snajp Bokföring föreslår kontering och räknar perioden. Förslagen är inte
        granskade av en auktoriserad redovisningskonsult och ersätter inte en. Du
        ansvarar för att uppgifterna är riktiga innan de förs in i ert
        bokföringssystem eller lämnas till Skatteverket.
      </p>
    </details>
  );
}
