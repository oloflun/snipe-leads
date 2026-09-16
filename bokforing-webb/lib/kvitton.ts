"use client";

import { useCallback, useEffect, useState } from "react";
import { felmeddelande, readJson } from "@/lib/http/json";
import { usePeriod } from "@/lib/period";

/**
 * Kvittohanterarens typer och datahook, delade av alla vyer.
 *
 * KVBAS pekar på sajtens egen proxy (app/api/kv/[[...path]]/route.ts), som
 * sätter X-API-Key på serversidan — nyckeln finns aldrig i webbläsaren.
 * Samma mönster som lib/api.ts hade för bokförings-API:t.
 */

export const KVBAS = "/api/kv";

/** Speglar backendens `LASBARA_MIMETYPER` (app/bookkeeping/underlag.py). */
export const LASBARA = ".pdf,image/jpeg,image/png,image/webp,image/heic";

export type Kvitto = {
  id: string;
  datum: string | null;
  motpart: string | null;
  filnamn: string | null;
  /** STRÄNG, aldrig number — se lib/format.ts. */
  brutto: string | null;
  momssats: string | null;
  kategori: string | null;
  kategorietikett: string;
  status: string;
  betalstatus: string | null;
  kalla: string;
  mejl_amne: string | null;
  mejl_avsandare: string | null;
  valuta: string;
  belopp_original: string | null;
  anmarkning: string;
};

export type Kategorisumma = { kategori: string; etikett: string; antal: number; summa: string };

export type Sammanfattning = {
  antal: number;
  antal_klara: number;
  antal_granska: number;
  totalt: string;
  moms: string;
  per_kategori: Kategorisumma[];
  storsta: { motpart: string | null; brutto: string } | null;
  text?: string;
};

export type Handelse = {
  mejl_id: string;
  avsandare: string;
  amne: string;
  datum: string;
  utfall: "kvitto" | "kvitto_granska" | "ej_kvitto" | "redan_last";
  belopp?: string | null;
  belopp_original?: string | null;
  kategori?: string | null;
  motpart?: string | null;
};

export type Mejlkonto = { kopplad: boolean; leverantor?: string; adress?: string };

/**
 * Periodens kvitton, sammanfattning och mejlkonto — samma tre anrop för alla
 * vyer, så att Översikt, Inkorgen och Kvitton aldrig visar olika verkligheter
 * för samma intervall. Samma delningsskäl som gamla useBokforing.
 */
export function useKvitton() {
  const { period } = usePeriod();
  const [konto, setKonto] = useState<Mejlkonto | null>(null);
  const [kvitton, setKvitton] = useState<Kvitto[] | null>(null);
  const [samman, setSamman] = useState<Sammanfattning | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    try {
      const [k, lista, s] = await Promise.all([
        fetch(`${KVBAS}/mejlkonto`).then((svar) => readJson<Mejlkonto>(svar)),
        fetch(`${KVBAS}?fran=${period.fran}&till=${period.till}`).then((svar) =>
          readJson<{ kvitton: Kvitto[] }>(svar)
        ),
        fetch(`${KVBAS}/sammanfattning?fran=${period.fran}&till=${period.till}`).then((svar) =>
          readJson<Sammanfattning>(svar)
        )
      ]);
      setKonto(k);
      setKvitton(lista?.kvitton ?? []);
      setSamman(s);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setKvitton([]);
      setSamman(null);
    }
  }, [period]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  return { period, konto, kvitton, samman, fel, hamta };
}
