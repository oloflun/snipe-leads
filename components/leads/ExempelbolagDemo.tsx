"use client";

import { useState } from "react";
import { Exempelbolagslista } from "@/components/leads/LeadsRunForm";
import { EXEMPEL_OMGANG_1, EXEMPEL_OMGANG_2, kontaktnamn, type ExempelBolag } from "@/lib/demo/iris-exempel";

/**
 * Exempellistan som EGEN komponent, med sina data.
 *
 * Datat bodde inline i /forhandsvisning/exempelbolag. När listan skulle visas
 * bredvid körningsformuläret på fler ytor (adminens Testkörningar, kundens
 * leads-vy) fanns två vägar: kopiera de tre bolagen till varje yta, eller
 * flytta dem hit EN gång. Kopior av exempeldata glider isär precis som
 * formulärkopior gjorde (se LeadsRunForm:s docstring) — därför bor bolagen
 * i lib/demo/iris-exempel.ts och alla ytor renderar samma komponent.
 *
 * Allt är påhittat och kan aldrig mejlas: org.numren har medvetet fel
 * kontrollsiffra och domänerna ligger under `.example` (RFC 2606). Se
 * app/leads/exempelbolag.py — samma regel som backendens (separata) generator.
 *
 * ## Varför bolagen och utkasten flyttades till lib/demo/iris-exempel.ts
 *
 * Uppmätt 2026-09-18: knapparna i Email Studio genererade utkasten ur
 * strängmallar (`simulateAction` i app/api/email-studio/route.ts, borttagen),
 * och `contact_name` här var en ROLL ("Inköpschef") som gick rakt in som
 * hälsning — "Hej Inköpschef,". De sex bolagen och deras HANDSKRIVNA utkast
 * bor nu i EN källa som både den här listan och API-routens demoläge läser,
 * så att listan och knapparnas svar aldrig kan glida isär.
 *
 * "Uppdatera" växlar mellan två fasta urval. I produkten hämtar knappen ett
 * nytt urval från backenden (`fro` i ExempelbolagRequest); fördröjningen här
 * motsvarar det anropet så att knappens läge går att se.
 */

/** Fixturens form → formen `Exempelbolagslista`/`Pitchutkast` (LeadsRunForm.tsx) förväntar sig. */
function tillListvy(b: ExempelBolag) {
  return {
    id: b.id,
    company_name: b.companyName,
    contact_name: `${kontaktnamn(b)}, ${b.contactRole}`,
    orgnr: b.orgnr,
    ort: b.ort,
    website: b.website,
    anstallda: b.anstallda,
    bransch: b.bransch,
    beskrivning: b.beskrivning,
    pitch_subject: b.draft.subject,
    pitch_body: b.draft.body,
    signal: b.signal,
    offer: b.offer,
    cta: b.cta
  };
}

export function ExempelbolagDemo() {
  const [omgang, setOmgang] = useState(0);
  const [hamtar, setHamtar] = useState(false);
  const bolag = (omgang % 2 === 0 ? EXEMPEL_OMGANG_1 : EXEMPEL_OMGANG_2).map(tillListvy);

  function uppdatera() {
    setHamtar(true);
    window.setTimeout(() => {
      setOmgang((n) => n + 1);
      setHamtar(false);
    }, 450);
  }

  return <Exempelbolagslista bolag={bolag} onUppdatera={uppdatera} uppdaterar={hamtar} />;
}
