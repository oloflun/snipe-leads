"use client";

import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";

/**
 * Registrerar service workern och erbjuder installation.
 *
 * ## Två plattformar, två beteenden — och därför två lägen här
 *
 * **Chrome, Edge, Android.** Webbläsaren avgör själv att sidan är
 * installerbar och skjuter `beforeinstallprompt`. Vi hindrar dess egen
 * banner, sparar händelsen och visar vår knapp i stället. `prompt()` FÅR bara
 * anropas i en användargest — därav knappen, aldrig ett automatiskt anrop.
 *
 * **iOS Safari.** Skickar ingen sådan händelse och har inget API. Där finns
 * bara Dela → "Lägg till på hemskärmen", och det enda vi kan göra är att
 * berätta det. Villkoret nedan känner igen iOS och byter ut knappen mot den
 * instruktionen — annars hade iOS-användare sett en knapp som inte gör något,
 * vilket är sämre än ingen knapp.
 *
 * ## När rutan INTE syns
 *
 * Redan installerad (`display-mode: standalone`), redan avvisad en gång
 * (sparat i localStorage), eller ingen installerbarhet alls. En
 * installationsuppmaning som kommer tillbaka efter att man tryckt bort den är
 * en annons, inte en funktion.
 */

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const AVVISAD = "snajp.installation.avvisad";

function arStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS använder en egen, icke-standardiserad flagga.
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function arIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    // iPadOS 13+ utger sig för att vara macOS; pekpunkterna avslöjar den.
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

export function InstalleraApp() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [visaIOS, setVisaIOS] = useState(false);

  useEffect(() => {
    // Registreringen sker oavsett om rutan visas: service workern behövs för
    // offline-sidan och för att webbläsaren ska räkna sidan som installerbar.
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch((error) => {
        // Ett misslyckat SW-bygge får inte krascha appen. Det syns i konsolen.
        console.error("service worker:", error);
      });
    }

    if (arStandalone() || localStorage.getItem(AVVISAD) === "1") {
      return;
    }

    if (arIOS()) {
      setVisaIOS(true);
      return;
    }

    const vidPrompt = (event: Event) => {
      event.preventDefault();
      setPrompt(event as InstallPrompt);
    };

    window.addEventListener("beforeinstallprompt", vidPrompt);
    return () => window.removeEventListener("beforeinstallprompt", vidPrompt);
  }, []);

  function avvisa() {
    localStorage.setItem(AVVISAD, "1");
    setPrompt(null);
    setVisaIOS(false);
  }

  async function installera() {
    if (!prompt) return;
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    // Händelsen går bara att använda EN gång. Oavsett utfall är den förbrukad.
    setPrompt(null);
    if (outcome === "accepted") {
      localStorage.setItem(AVVISAD, "1");
    }
  }

  if (!prompt && !visaIOS) {
    return null;
  }

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-50 border-t border-ink/15 bg-paper2/95 backdrop-blur-xl"
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 pt-3 md:px-6">
        <Download className="hidden h-4 w-4 shrink-0 text-ochre sm:block" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-medium text-ink">Installera Snajp som app</p>
          <p className="mt-0.5 text-[13px] text-ink/60">
            {visaIOS
              ? "Tryck på Dela och välj “Lägg till på hemskärmen”."
              : "Egen ikon, eget fönster, ingen adressrad."}
          </p>
        </div>

        {prompt ? (
          <button
            type="button"
            onClick={() => void installera()}
            className="focus-ring inline-flex min-h-9 shrink-0 items-center rounded-input bg-ink px-3 text-[13px] font-medium text-paper"
          >
            Installera
          </button>
        ) : null}

        <button
          type="button"
          onClick={avvisa}
          aria-label="Stäng"
          className="focus-ring inline-flex min-h-9 w-9 shrink-0 items-center justify-center rounded-input text-ink/50 hover:text-ink"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </div>
  );
}
