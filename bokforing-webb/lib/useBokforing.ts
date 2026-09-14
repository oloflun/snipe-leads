"use client";

import { useCallback, useEffect, useState } from "react";
import { BAS, type Rapport, type Underlag } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { usePeriod } from "@/lib/period";

/**
 * Periodens underlag och rapport — samma två anrop som huvudappens panel gör,
 * delade av alla vyer så att Översikt, Resultat och listorna aldrig visar
 * olika verkligheter för samma intervall.
 */
export function useBokforing() {
  const { period } = usePeriod();
  const [underlag, setUnderlag] = useState<Underlag[] | null>(null);
  const [rapport, setRapport] = useState<Rapport | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    try {
      const [u, r] = await Promise.all([
        fetch(`${BAS}/underlag?fran=${period.fran}&till=${period.till}`).then((svar) =>
          readJson<{ underlag: Underlag[] }>(svar)
        ),
        fetch(`${BAS}/period?fran=${period.fran}&till=${period.till}`).then((svar) =>
          readJson<Rapport>(svar)
        )
      ]);
      setUnderlag(u?.underlag ?? []);
      setRapport(r);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setUnderlag([]);
      setRapport(null);
    }
  }, [period]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  return { period, underlag, rapport, fel, hamta };
}
