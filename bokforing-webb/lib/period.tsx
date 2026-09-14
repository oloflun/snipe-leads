"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

/**
 * Perioden är EN för hela sajten. Översikt, Resultat, Intäkter & utgifter och
 * PDF-filer läser alla samma intervall — fyra egna periodväljare hade betytt
 * fyra vyer som tyst visar olika månader, och det upptäcks alltid i fel läge.
 *
 * localStorage är ett per-webbläsare-minne för bekvämlighet, inte sanning:
 * går det inte att läsa (privat fönster, blockerad lagring) faller allt
 * tillbaka på innevarande månad.
 */

export type Period = { fran: string; till: string };

export function innevarandeManad(): Period {
  const nu = new Date();
  const fran = new Date(nu.getFullYear(), nu.getMonth(), 1);
  const till = new Date(nu.getFullYear(), nu.getMonth() + 1, 0);
  const iso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { fran: iso(fran), till: iso(till) };
}

const NYCKEL = "snajp-bokforing:period";

type PeriodContext = {
  period: Period;
  sattPeriod: (period: Period) => void;
};

const Context = createContext<PeriodContext | null>(null);

export function PeriodProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [period, setPeriod] = useState<Period>(innevarandeManad);

  useEffect(() => {
    try {
      const sparad = window.localStorage.getItem(NYCKEL);
      if (!sparad) return;
      const tolkad = JSON.parse(sparad) as Partial<Period>;
      if (typeof tolkad.fran === "string" && typeof tolkad.till === "string") {
        setPeriod({ fran: tolkad.fran, till: tolkad.till });
      }
    } catch {
      // Trasig lagring är inte ett fel användaren kan agera på.
    }
  }, []);

  const varde = useMemo<PeriodContext>(
    () => ({
      period,
      sattPeriod: (ny) => {
        setPeriod(ny);
        try {
          window.localStorage.setItem(NYCKEL, JSON.stringify(ny));
        } catch {
          // Se ovan.
        }
      }
    }),
    [period]
  );

  return <Context.Provider value={varde}>{children}</Context.Provider>;
}

export function usePeriod(): PeriodContext {
  const varde = useContext(Context);
  if (!varde) throw new Error("usePeriod kräver PeriodProvider i layouten.");
  return varde;
}
