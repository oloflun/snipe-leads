"use client";

import { useEffect, useState } from "react";

/**
 * Installationen av appen — EN källa, flera knappar.
 *
 * ## Varför fångsten sitter på modulnivå och inte i en komponent
 *
 * `beforeinstallprompt` skjuts EN gång, tidigt, och bara om webbläsaren anser
 * sidan installerbar. Två saker följer av det, och båda är fällor:
 *
 *  1. En komponent som monteras efter att händelsen skjutits ser den aldrig.
 *     Knappen i hjältebilden monteras vid första målningen, men rutan i
 *     sidfoten kan monteras senare — och en av dem hade då varit död.
 *  2. Händelsen går att `prompt()`:a en gång. Två komponenter som var för sig
 *     sparar den och båda anropar `prompt()` ger ett kast på den andra.
 *
 * Lyssnaren registreras därför när modulen laddas, resultatet läggs i en
 * modulvariabel, och komponenter PRENUMERERAR på den. Den som monterar sent får
 * det redan fångade värdet direkt.
 *
 * ## Vad "ladda ner appen" faktiskt är
 *
 * Det finns ingen binär att hämta. Snajp är en PWA, och installationen är det
 * webbläsaren gör åt oss: egen ikon på skrivbordet eller hemskärmen, eget
 * fönster utan adressrad, egen post i Start-menyn respektive app-lådan.
 * Resultatet är det användaren menar med "appen ligger på skrivbordet" — vägen
 * dit är bara en annan än en .exe-fil.
 *
 * Det går INTE att göra utan en användargest, och det går inte alls på iOS.
 * Se `plattform()` för vad varje enhet klarar.
 */

export type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

let fangad: InstallPrompt | null = null;
const lyssnare = new Set<(p: InstallPrompt | null) => void>();

function meddela() {
  for (const l of lyssnare) l(fangad);
}

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    // preventDefault stoppar webbläsarens egen banner. Utan den konkurrerar två
    // uppmaningar om samma klick.
    event.preventDefault();
    fangad = event as InstallPrompt;
    meddela();
  });

  // Installationen kan ske utanför vår knapp — genom webbläsarens egen meny.
  // Utan den här raden står knappen kvar och erbjuder något som redan är gjort.
  window.addEventListener("appinstalled", () => {
    fangad = null;
    meddela();
  });
}

export type Plattform =
  /** Chrome, Edge, Android: `beforeinstallprompt` finns. Ett klick räcker. */
  | "kan-installera"
  /** iOS/iPadOS: inget API. Bara Dela → Lägg till på hemskärmen. */
  | "ios"
  /** Safari på macOS: Arkiv → Lägg till i Dock. Inget API. */
  | "mac-safari"
  /** Firefox och övriga utan stöd. Instruktionen är att byta webbläsare. */
  | "utan-stod"
  /** Redan installerad — appen körs i eget fönster. */
  | "installerad";

export function arStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.matchMedia("(display-mode: window-controls-overlay)").matches ||
    // iOS använder en egen, icke-standardiserad flagga.
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export function arIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    // iPadOS 13+ utger sig för att vara macOS; pekpunkterna avslöjar den.
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function arMacSafari(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return /Macintosh/.test(ua) && /Safari/.test(ua) && !/Chrome|Chromium|Edg/.test(ua);
}

/**
 * Vad DEN HÄR enheten klarar, avgjort efter montering.
 *
 * Får aldrig anropas under serverrendering: den läser `navigator` och
 * `matchMedia`. Hooken nedan sköter det, och anledningen står där.
 */
export function plattform(prompt: InstallPrompt | null): Plattform {
  if (arStandalone()) return "installerad";
  if (prompt) return "kan-installera";
  if (arIOS()) return "ios";
  if (arMacSafari()) return "mac-safari";
  return "utan-stod";
}

export type Installation = {
  /** null tills komponenten monterat. Se hooken om varför. */
  plattform: Plattform | null;
  /** Kör installationen. Sant om webbläsaren faktiskt installerade. */
  installera: () => Promise<boolean>;
};

/**
 * Installationsläget, med ett medvetet `null` före montering.
 *
 * Servern kan inte veta vilken enhet som frågar, och en gissning här hade gett
 * exakt den hydreringsmiss som TemaSettings redan fällt en gång: markup som
 * säger en sak på servern och en annan i webbläsaren. `null` betyder "vet
 * inte än", och anroparen renderar då samma neutrala knapp som servern gjorde.
 */
export function useInstallation(): Installation {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [monterad, setMonterad] = useState(false);

  useEffect(() => {
    setMonterad(true);
    setPrompt(fangad);
    const l = (p: InstallPrompt | null) => setPrompt(p);
    lyssnare.add(l);
    return () => {
      lyssnare.delete(l);
    };
  }, []);

  async function installera(): Promise<boolean> {
    if (!prompt) return false;
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    // Händelsen är förbrukad oavsett utfall. Att behålla den hade gett ett kast
    // vid nästa klick.
    fangad = null;
    meddela();
    return outcome === "accepted";
  }

  return { plattform: monterad ? plattform(prompt) : null, installera };
}
