"use client";

/**
 * Synkens läge, delat av hela CRM:et (CLAUDE.md: varje funktion visar sitt förlopp).
 *
 * Navigeringens synkkort, översikten och Synk visade förut var sin hämtning (var
 * femte, fjärde och tredje sekund), så samma körning kunde stå med tre olika tal
 * på samma skärm. Nu finns körningarna på ett ställe: ramen hämtar `/oversikt`
 * var tredje sekund medan något pågår, och varje vy som själv hämtar körningar
 * lämnar in dem här. Alla ytor läser samma körning, med det senast hämtade talet.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { crmAnrop, type Anslutning, type Korning, type Oversikt } from "@/lib/crm/api";

/** Hur ofta läget hämtas om medan en körning pågår. */
export const SYNKPULS = 3000;

export const pagar = (k: Korning) => k.status === "queued" || k.status === "processing";
export const klara = (k: Korning) => k.counts.created + k.counts.updated + k.counts.unchanged + k.counts.skipped + k.counts.conflicts;
/**
 * Alla poster är behandlade men körningen är inte stängd än. Stapeln är då full
 * men synken pågår fortfarande: ytorna säger "Avslutar" med obestämd stapel.
 */
export const avslutar = (k: Korning) => k.status === "processing" && k.counts.total > 0 && klara(k) >= k.counts.total;

type Synklage = {
  /** De senaste körningarna, nyast först, eller null innan första hämtningen. */
  korningar: Korning[] | null;
  anslutningar: Record<string, Anslutning>;
  /** En vy som själv hämtat körningar lämnar in dem, så att alla ytor visar samma tal. */
  publicera: (k: Korning[]) => void;
  /** Hämta om nu, till exempel efter att en vy ändrat något. */
  hamtaOm: () => void;
};

const Kontext = createContext<Synklage | null>(null);

export function SynklageKalla({ children }: Readonly<{ children: React.ReactNode }>) {
  const [perId, setPerId] = useState<Record<string, Korning> | null>(null);
  const [anslutningar, setAnslutningar] = useState<Record<string, Anslutning>>({});
  const vag = usePathname();
  const omgang = useRef(0);

  const publicera = useCallback((lista: Korning[]) => {
    setPerId((forr) => {
      const ny = { ...(forr ?? {}) };
      for (const k of lista) ny[k.id] = k;
      return ny;
    });
  }, []);

  const hamtaOm = useCallback(async () => {
    const denna = ++omgang.current;
    try {
      const [o, a] = await Promise.all([crmAnrop<Oversikt>("/oversikt"), crmAnrop<{ data: Anslutning[] }>("/v1/connections")]);
      if (denna !== omgang.current) return;
      publicera(o.korningar);
      setAnslutningar(Object.fromEntries(a.data.map((x) => [x.id, x])));
    } catch {
      if (denna === omgang.current) setPerId((forr) => forr ?? {});
    }
  }, [publicera]);

  // Vid varje vybyte: en synk som startats någon annanstans syns direkt.
  useEffect(() => {
    void hamtaOm();
  }, [hamtaOm, vag]);

  const korningar = useMemo(
    () => (perId ? Object.values(perId).sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? "")) : null),
    [perId]
  );

  const igang = korningar?.some(pagar) ?? false;
  useEffect(() => {
    if (!igang) return;
    const t = window.setInterval(() => void hamtaOm(), SYNKPULS);
    return () => window.clearInterval(t);
  }, [igang, hamtaOm]);

  const varde = useMemo<Synklage>(
    () => ({ korningar, anslutningar, publicera, hamtaOm: () => void hamtaOm() }),
    [korningar, anslutningar, publicera, hamtaOm]
  );
  return <Kontext.Provider value={varde}>{children}</Kontext.Provider>;
}

/** Synkens delade läge. Utanför ramen (tester) finns inget att dela: tomt läge. */
export function useSynklage(): Synklage {
  return (
    useContext(Kontext) ?? {
      korningar: null,
      anslutningar: {},
      publicera: () => undefined,
      hamtaOm: () => undefined
    }
  );
}

/** Den senaste versionen av en körning: det som hämtats senast, var det än hämtades. */
export function useAktuell(lista: Korning[] | null): Korning[] | null {
  const { korningar } = useSynklage();
  return useMemo(() => {
    if (!lista) return lista;
    const delade = new Map((korningar ?? []).map((k) => [k.id, k]));
    return lista.map((k) => delade.get(k.id) ?? k);
  }, [lista, korningar]);
}
