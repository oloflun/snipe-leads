"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

/**
 * Företagsprofilen kunden själv fyller i under Inställningar.
 *
 * Ligger i localStorage tills sajten får riktiga konton — den bär inga
 * hemligheter (namn, orgnr och webbplats är offentliga uppgifter), och den
 * används på tre ställen: SIE-exporten (företagsnamn + orgnr i filhuvudet),
 * assistentens sammanhang, och hälsningen på Översikt.
 */

export type Profil = {
  foretagsnamn: string;
  orgnr: string;
  webbplats: string;
  beskrivning: string;
};

export const TOM_PROFIL: Profil = {
  foretagsnamn: "",
  orgnr: "",
  webbplats: "",
  beskrivning: ""
};

const NYCKEL = "snajp-bokforing:profil";

type ProfilContext = {
  profil: Profil;
  sattProfil: (profil: Profil) => void;
  /** True först när localStorage faktiskt lästs — hindrar att ett tomt
   *  förstavärde blinkar förbi innan det sparade hunnit in. */
  laddad: boolean;
};

const Context = createContext<ProfilContext | null>(null);

export function ProfilProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [profil, setProfil] = useState<Profil>(TOM_PROFIL);
  const [laddad, setLaddad] = useState(false);

  useEffect(() => {
    try {
      const sparad = window.localStorage.getItem(NYCKEL);
      if (sparad) {
        const tolkad = JSON.parse(sparad) as Partial<Profil>;
        setProfil({ ...TOM_PROFIL, ...tolkad });
      }
    } catch {
      // Oåtkomlig lagring: börja tomt.
    }
    setLaddad(true);
  }, []);

  const varde = useMemo<ProfilContext>(
    () => ({
      profil,
      laddad,
      sattProfil: (ny) => {
        setProfil(ny);
        try {
          window.localStorage.setItem(NYCKEL, JSON.stringify(ny));
        } catch {
          // Se ovan.
        }
      }
    }),
    [profil, laddad]
  );

  return <Context.Provider value={varde}>{children}</Context.Provider>;
}

export function useProfil(): ProfilContext {
  const varde = useContext(Context);
  if (!varde) throw new Error("useProfil kräver ProfilProvider i layouten.");
  return varde;
}

/**
 * Raden assistenten får som sammanhang. En RAD, märkt som delad från
 * Inställningar — den skickas synligt i historiken, inte smugglad i en
 * systemprompt vi inte äger.
 */
export function profilSomKontext(profil: Profil): string | null {
  const delar = [
    profil.foretagsnamn && `Företag: ${profil.foretagsnamn}`,
    profil.orgnr && `Organisationsnummer: ${profil.orgnr}`,
    profil.webbplats && `Webbplats: ${profil.webbplats}`,
    profil.beskrivning && `Om verksamheten: ${profil.beskrivning}`
  ].filter(Boolean);
  if (!delar.length) return null;
  return `(Företagsprofil, delad från Inställningar — bakgrund, inte en fråga.) ${delar.join(". ")}.`;
}
