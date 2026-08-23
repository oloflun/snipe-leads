"use client";

import { Check, Download, Share, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useInstallation, type Plattform } from "@/lib/pwa";
import { cn } from "@/lib/utils";

/**
 * "Ladda ner appen" — knappen intill produktväxeln i hjältebilden.
 *
 * ## Vad den gör, och vad den inte kan göra
 *
 * Det finns ingen binär att hämta. Snajp är en PWA, och det användaren menar
 * med "appen ligger på skrivbordet" åstadkoms av webbläsarens installation:
 * egen ikon på skrivbordet eller hemskärmen, eget fönster utan adressrad, egen
 * post i Start-menyn respektive app-lådan. Ikonen är den vi redan har
 * (public/icons), och manifestet bär skärmbilderna som gör att Chrome visar en
 * riktig installationsdialog i stället för "Skapa genväg".
 *
 * På Chrome, Edge och Android räcker ETT klick. Där tar knappen hela vägen.
 *
 * På iOS finns inget API alls — Safari erbjuder bara Dela → Lägg till på
 * hemskärmen, och ingen mängd kod ändrar det. Samma sak på macOS Safari
 * (Arkiv → Lägg till i Dock) och i Firefox, som inte installerar PWA:er.
 *
 * En knapp som ser likadan ut men inte gör något är sämre än ingen knapp. Där
 * automatiken saknas visar den därför exakt de två stegen som gäller för just
 * den enheten, i stället för att låtsas.
 *
 * ## Varför läget avgörs EFTER montering
 *
 * Servern vet inte vilken enhet som frågar. En gissning i markupen hade gett
 * samma hydreringsmiss som temaväxeln redan fällt en gång. `plattform` är
 * därför `null` fram till första effekten, och knappen renderas då exakt som
 * servern renderade den — samma text, samma element. Bara BETEENDET tillkommer.
 */

const STEG: Record<Exclude<Plattform, "kan-installera" | "installerad">, {
  rubrik: string;
  steg: string[];
}> = {
  ios: {
    rubrik: "På iPhone och iPad",
    steg: [
      "Tryck på Dela-ikonen i Safaris verktygsfält.",
      "Välj “Lägg till på hemskärmen”."
    ]
  },
  "mac-safari": {
    rubrik: "I Safari på Mac",
    steg: ["Öppna menyn Arkiv.", "Välj “Lägg till i Dock”."]
  },
  "utan-stod": {
    rubrik: "Den här webbläsaren installerar inte appar",
    steg: [
      "Öppna snajp.se i Chrome eller Edge.",
      "Klicka på “Ladda ner appen” igen — då går det på ett klick."
    ]
  }
};

export function LaddaNerAppen({ tone = "ink" }: Readonly<{ tone?: "ink" | "paper" }>) {
  const { plattform, installera } = useInstallation();
  const [öppen, setÖppen] = useState(false);
  const [klar, setKlar] = useState(false);
  const rutRef = useRef<HTMLDivElement>(null);

  // Klick utanför och Escape stänger. En instruktionsruta som bara går att
  // stänga med sin egen knapp är en ruta man klickar bort från och som ligger
  // kvar bakom nästa sak man gör.
  useEffect(() => {
    if (!öppen) return;
    function vidKlick(e: MouseEvent) {
      if (rutRef.current && !rutRef.current.contains(e.target as Node)) setÖppen(false);
    }
    function vidTangent(e: KeyboardEvent) {
      if (e.key === "Escape") setÖppen(false);
    }
    document.addEventListener("mousedown", vidKlick);
    document.addEventListener("keydown", vidTangent);
    return () => {
      document.removeEventListener("mousedown", vidKlick);
      document.removeEventListener("keydown", vidTangent);
    };
  }, [öppen]);

  // Redan installerad: ingen knapp alls. Att erbjuda en installation till den
  // som redan gjort den är brus, och den som läser sidan i appen har per
  // definition redan lyckats.
  if (plattform === "installerad") return null;

  async function klick() {
    if (plattform === "kan-installera") {
      const lyckades = await installera();
      if (lyckades) setKlar(true);
      return;
    }
    // plattform === null betyder "vet inte än" — då har effekten inte kört, och
    // ett klick så tidigt är i praktiken omöjligt. Rutan är rätt fallback.
    setÖppen((v) => !v);
  }

  const instruktion = plattform && plattform !== "kan-installera" ? STEG[plattform] : null;

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => void klick()}
        aria-expanded={instruktion ? öppen : undefined}
        className={cn(
          "focus-ring group inline-flex min-h-11 items-center gap-2 rounded-input border px-3.5 text-[0.9375rem] font-medium transition-colors",
          tone === "paper"
            ? "border-paper/30 text-paper/85 hover:border-paper/60 hover:text-paper"
            : "border-ink/20 text-ink/75 hover:border-ink/45 hover:text-ink"
        )}
      >
        {klar ? (
          <Check className="h-4 w-4 shrink-0" aria-hidden />
        ) : (
          <Download className="h-4 w-4 shrink-0 transition-transform group-hover:translate-y-0.5" aria-hidden />
        )}
        {klar ? "Appen är installerad" : "Ladda ner appen"}
      </button>

      {instruktion && öppen ? (
        <div
          ref={rutRef}
          role="dialog"
          aria-label={instruktion.rubrik}
          // Ankrad till knappen men vänsterjusterad mot den, och full bredd på
          // mobil: en absolut ruta som ärver knappens högerkant hamnar utanför
          // vyn på en telefon, och body har overflow-x: clip — den hade alltså
          // klippts bort i stället för att synas.
          className="absolute left-0 top-[calc(100%+0.6rem)] z-40 w-[min(20rem,calc(100vw-2.5rem))] rounded-card border border-ink/15 bg-paper p-4 text-ink shadow-lift"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-[0.875rem] font-semibold leading-6">{instruktion.rubrik}</p>
            <button
              type="button"
              onClick={() => setÖppen(false)}
              aria-label="Stäng"
              className="focus-ring -mr-1 -mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-input text-ink/45 hover:text-ink"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>

          <ol className="mt-3 grid gap-2.5">
            {instruktion.steg.map((s, i) => (
              <li key={s} className="flex gap-2.5 text-[0.875rem] leading-6 text-ink/75">
                <span
                  aria-hidden
                  className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ochre/15 font-mono text-[0.6875rem] text-warning"
                >
                  {i + 1}
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ol>

          {plattform === "ios" ? (
            <p className="mt-3 flex items-center gap-2 border-t border-ink/15 pt-3 text-[0.8125rem] text-ink/50">
              <Share className="h-3.5 w-3.5 shrink-0" aria-hidden />
              Dela-ikonen är fyrkanten med pilen uppåt.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
