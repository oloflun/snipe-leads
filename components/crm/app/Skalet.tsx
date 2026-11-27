"use client";

import { createContext, useContext, useMemo } from "react";
import { loggaUtOchOppna, oppnaEfterIdentitetsbyte } from "@/components/dashboard/DashboardContext";
import { bytVy } from "@/lib/actions/vy";

/**
 * Skalets åtgärder som byter vem eller vad man tittar som: vyväxeln Admin och
 * Demo, Byt kund, Avsluta kundbesöket och Logga ut (SK-065, SK-074 till SK-076,
 * AD-008 till AD-011). Banderollen, arbetsyteväxlarens meny och kommandopaletten
 * läser dem härifrån, så att alla gör exakt samma sak.
 *
 * Det riktiga skalet kör samma server action som dagens app (`bytVy`: grinden,
 * cookien och loggen `log_admin_impersonation`) och öppnar sedan adressen hårt
 * (INV-SEC-014), men stannar i CRM:et: på samma vy, utan frågesträngen, eftersom
 * en post i adressen hör till den förra arbetsytan. Förhandsvisningen skickar in
 * sina egna åtgärder, som bara byter läge i adressen.
 */
export type Skalatgarder = {
  /** `admin`, `demo` eller `kund:<slug>`. Svarar falskt om inget byttes (inte plattformsadmin, ogiltig slug). */
  bytVy: (varde: string) => Promise<boolean>;
  loggaUt: () => Promise<void>;
};

async function bytVyICrm(varde: string): Promise<boolean> {
  const formular = new FormData();
  formular.set("vy", varde);
  const { url } = await bytVy(formular);
  if (!url) return false;
  oppnaEfterIdentitetsbyte(window.location.pathname);
  return true;
}

const SKARPA: Skalatgarder = { bytVy: bytVyICrm, loggaUt: loggaUtOchOppna };

const Kontext = createContext<Skalatgarder>(SKARPA);

export function SkaletsAtgarder({ atgarder, children }: Readonly<{ atgarder?: Partial<Skalatgarder>; children: React.ReactNode }>) {
  const varde = useMemo(() => ({ ...SKARPA, ...atgarder }), [atgarder]);
  return <Kontext.Provider value={varde}>{children}</Kontext.Provider>;
}

export const useSkaletsAtgarder = () => useContext(Kontext);
