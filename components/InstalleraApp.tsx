"use client";

import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useInstallation } from "@/lib/pwa";

/**
 * Registrerar service workern och erbjuder installation.
 *
 * ## Detektionen bor i lib/pwa.ts, inte här
 *
 * Filen hade en egen `beforeinstallprompt`-lyssnare. Sedan knappen i
 * hjältebilden tillkom (LaddaNerAppen) fanns TVÅ, och det är inte en
 * dubblering utan en bugg: händelsen får `prompt()`:as en gång, så den som
 * klickade båda knapparna fick ett kast på den andra. Dessutom missar en
 * komponent som monterar sent en händelse som redan skjutits.
 *
 * `lib/pwa.ts` fångar den på modulnivå och låter båda prenumerera. Lägg aldrig
 * tillbaka en lyssnare här.
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

const AVVISAD = "snajp.installation.avvisad";

export function InstalleraApp() {
  const { plattform, installera: kor } = useInstallation();
  const [avvisad, setAvvisad] = useState(true);

  useEffect(() => {
    // Registreringen sker oavsett om rutan visas: service workern behövs för
    // offline-sidan och för att webbläsaren ska räkna sidan som installerbar.
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch((error) => {
        // Ett misslyckat SW-bygge får inte krascha appen. Det syns i konsolen.
        console.error("service worker:", error);
      });
    }
    // Startar som avvisad och öppnas först efter kontrollen. Motsatt ordning
    // hade blinkat fram rutan för den som redan tryckt bort den.
    setAvvisad(localStorage.getItem(AVVISAD) === "1");
  }, []);

  function avvisa() {
    localStorage.setItem(AVVISAD, "1");
    setAvvisad(true);
  }

  async function installera() {
    if (await kor()) {
      localStorage.setItem(AVVISAD, "1");
      setAvvisad(true);
    }
  }

  // Rutan visas bara där den kan leda någonstans: ett klick (kan-installera)
  // eller en instruktion som faktiskt gäller (iOS). macOS Safari och Firefox
  // får den inte — där bär knappen i hjältebilden instruktionen, och en
  // fastklistrad rad i sidfoten som säger "byt webbläsare" är en annons.
  const visaIOS = plattform === "ios";
  const kanInstallera = plattform === "kan-installera";
  if (avvisad || (!kanInstallera && !visaIOS)) {
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

        {kanInstallera ? (
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
