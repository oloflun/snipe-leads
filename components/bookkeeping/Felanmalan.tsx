"use client";

import { LifeBuoy } from "lucide-react";
import { KONTAKT_MEJL } from "@/components/marketing/copy";

/**
 * Felanmälan från bokföringsvyn.
 *
 * ## Varför en mailto och inte ett formulär
 *
 * Ett formulär hade krävt en endpoint, en tabell och en vy där någon läser
 * dem — alltså en supportkanal till, vid sidan av den som redan finns och
 * bevakas. Ett mejl landar i inkorgen som faktiskt läses.
 *
 * ## Varför ämnesraden bär sammanhanget
 *
 * En felanmälan som bara säger "det blev fel" kostar en rundtur innan
 * felsökningen ens kan börja. Ämnet bär produktnamnet, och kroppen har en
 * ifylld mall med de tre frågor vi ändå skulle ha ställt: vilket underlag,
 * vad som hände, vad som förväntades.
 *
 * ## Varför mallen INTE bär ett datum
 *
 * Första utkastet la in `new Date()` i kroppen. Det anropet körs vid rendering,
 * alltså både på servern och i webbläsaren, och de två kan hamna på olika sidor
 * om midnatt — exakt den hydreringsmiss temaväxeln redan fällt en gång.
 *
 * Att flytta datumet till klicket hade löst det och samtidigt gjort länken till
 * en knapp. Men mejlet bär redan sin egen tidsstämpel i huvudet, så fältet
 * tillförde ingenting. Det enklaste riktiga svaret var att ta bort det.
 */

const AMNE = "Snajp Bokföring — felanmälan";

const BRODTEXT = [
  "Beskriv gärna kort:",
  "",
  "1. Vilket underlag eller vilken period gäller det?",
  "2. Vad blev fel?",
  "3. Vad hade du förväntat dig i stället?",
  ""
].join("\n");

export function Felanmalan() {
  return (
    <section className="mt-14 border-t border-ink/15 pt-6">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.875rem] leading-6 text-ink/60">
        <LifeBuoy className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
        Ser något fel ut i en avläsning, en kontering eller en period?
        <a
          href={`mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent(AMNE)}&body=${encodeURIComponent(BRODTEXT)}`}
          className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-ochre"
        >
          Anmäl det till oss
        </a>
        <span className="text-ink/45">så tittar vi på det.</span>
      </p>
    </section>
  );
}
