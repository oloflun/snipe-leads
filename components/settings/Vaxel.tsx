"use client";

import { useId } from "react";
import { rubrikPanel } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * Växeln — EN komponent för både notiser och tema.
 *
 * ## Varför en <button role="switch"> och inte en <input type="checkbox">
 *
 * De två sidorna som använder den här ställer olika sorters fråga. En kryssruta
 * betyder "det här ingår i något jag skickar in när jag klickar Spara". Temat
 * har ingen Spara-knapp — det byter läge i samma ögonblick man rör det — och en
 * kryssruta som utför något direkt är den vanligaste anledningen till att folk
 * letar efter en Spara-knapp som inte finns.
 *
 * `role="switch"` med `aria-checked` läses upp som "på/av" i stället för
 * "ikryssad", vilket är exakt skillnaden ovan, och den hörs.
 *
 * ## Varför etiketten ligger i komponenten
 *
 * En växel utan synlig etikett kräver `aria-label`, och den texten glöms i
 * praktiken varje gång. Med etiketten som obligatoriskt fält går det inte att
 * rendera en oskyltad växel av misstag.
 */
export function Vaxel({
  etikett,
  beskrivning,
  pa,
  onChange,
  disabled = false
}: Readonly<{
  etikett: string;
  beskrivning?: string;
  pa: boolean;
  onChange: (nytt: boolean) => void;
  disabled?: boolean;
}>) {
  // Etiketten och hjälpmeningen KOPPLAS till knappen. Förut stod de bara
  // bredvid den, så skärmläsaren läste växeln som "På" eller "Av" utan namn.
  const id = useId();
  return (
    <div className="flex items-center justify-between gap-6">
      <span className="min-w-0">
        <span id={`${id}-etikett`} className={cn(rubrikPanel, "block")}>
          {etikett}
        </span>
        {beskrivning ? (
          <span
            id={`${id}-hjalp`}
            className="mt-1 block max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted"
          >
            {beskrivning}
          </span>
        ) : null}
      </span>

      <button
        type="button"
        role="switch"
        aria-checked={pa}
        aria-labelledby={`${id}-etikett`}
        aria-describedby={beskrivning ? `${id}-hjalp` : undefined}
        disabled={disabled}
        onClick={() => onChange(!pa)}
        className={cn(
          // shrink-0: knappen är den enda fasta bredden i raden, och utan den
          // krymper den i stället för texten när etiketten är lång.
          "focus-ring relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200",
          disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
          pa ? "bg-ochre" : "bg-ink/20"
        )}
      >
        {/* Skärmläsaren får tillståndet ur aria-checked. Den här texten finns
            för att en växel som BARA är en färgad pinne är osynlig för den som
            inte skiljer ochre från grått — kontrast är inte den enda kanalen. */}
        <span className="sr-only">{pa ? "På" : "Av"}</span>
        <span
          aria-hidden
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-paper transition-[left] duration-200",
            pa ? "left-[1.375rem]" : "left-0.5"
          )}
        />
      </button>
    </div>
  );
}
