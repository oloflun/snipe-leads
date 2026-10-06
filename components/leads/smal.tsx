"use client";

import { createContext, useContext } from "react";

/**
 * Sant när en leadsvy står i en smal kolumn (Leads › Översikt, split view)
 * fast fönstret är brett. Tailwind 3 saknar container queries här, så
 * tabellerna som väljer tabell eller kort på fönstrets bredd (lg:/md:) läser
 * den här i stället och visar korten.
 */
const SmalKontext = createContext(false);

export const SmalKolumn = SmalKontext.Provider;

export function useSmal(): boolean {
  return useContext(SmalKontext);
}
