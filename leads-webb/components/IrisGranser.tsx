import { GRANSER } from "@/lib/iris";

/**
 * "Det här gör Iris aldrig utan din granskning" — gränslistan som ruled
 * list, samma radspråk som resten av sajten. Renderas på Kör Iris-vyn där
 * beslutet att trycka på knappen fattas; det är där löftet ska stå.
 */
export function IrisGranser() {
  return (
    <section aria-label="Det här gör Iris aldrig utan din granskning">
      <h2 className="font-display text-[1.25rem]">
        Det här gör Iris <span className="italic text-ochre">aldrig</span> utan din granskning
      </h2>
      <ul className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
        {GRANSER.map((grans) => (
          <li key={grans.rubrik} className="flex flex-wrap gap-x-8 gap-y-1 py-4">
            <h3 className="w-64 shrink-0 text-[0.9375rem] font-semibold text-ink">
              {grans.rubrik}
            </h3>
            <p className="min-w-0 flex-1 basis-72 text-[0.9375rem] leading-6 text-ink/62">
              {grans.text}
            </p>
          </li>
        ))}
      </ul>
      <p className="mt-3 max-w-[70ch] text-[0.8125rem] leading-5 text-ink/50">
        Gränserna sitter i systemet, inte i en policytext: granskningskön, avregistreringen och
        källkravet är spärrar i koden. Hur Iris eskalerar till dig ställer du in under
        Inställningar.
      </p>
    </section>
  );
}
