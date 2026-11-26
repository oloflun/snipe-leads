"use client";

import { Suspense, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { signOut } from "@/lib/actions/auth";
import { bytVy } from "@/lib/actions/vy";
import type { DashboardState } from "@/lib/data/dashboard";
import type { ProductKey, Scope } from "@/lib/routes";
import { SCOPE_COOKIE, productKeys } from "@/lib/routes";

export type { Scope };

/**
 * Identitetsbyten (INV-SEC-014, kunddemon 2026-11-24).
 *
 * En flik som renderats för en identitet får aldrig visa data för en annan.
 * Demon visade kundens skal med adminens paneler: sessionen i webbläsaren hade
 * bytts i en annan flik, och den gamla fliken hämtade vidare med den nya
 * cookien. Tre delar håller ihop det, alla här:
 *
 *  - Den flik där bytet görs (inloggning, utloggning, vybyte) öppnar adressen
 *    med `window.location.replace`, som tömmer flikens state och routercache.
 *  - Den säger till de andra flikarna på kanalen nedan.
 *  - Varje flik med ett inloggat träd jämför layoutens identitet med
 *    `/api/snajp-support/identitet` vid varje navigering, vid fokus och när
 *    fliken blir synlig, och laddar om när de skiljer sig.
 */
const IDENTITETSKANAL = "snajp-identitet";
const IDENTITET_HUVUD = "X-Snajp-Identitet";
/** Skydd mot omladdningsloop: högst en omladdning per byte från A till B. */
const OMLADDNING_NYCKEL = "snajp:identitet-omladdning";

// EN kanal per flik, för både att posta och lyssna: en BroadcastChannel får
// aldrig sina egna meddelanden, så fliken som gör bytet laddar inte om sig själv
// mitt i sin egen navigering.
let kanal: BroadcastChannel | null = null;
function identitetskanal(): BroadcastChannel | null {
  if (typeof BroadcastChannel === "undefined") return null;
  kanal ??= new BroadcastChannel(IDENTITETSKANAL);
  return kanal;
}

/** Efter ett lyckat identitetsbyte: säg till de andra flikarna och öppna adressen hårt. */
export function oppnaEfterIdentitetsbyte(url: string): void {
  identitetskanal()?.postMessage("bytt");
  window.location.replace(url);
}

/** Formulärets action för Admin | Demo, Byt kund, Öppna och Tillbaka till adminytan. */
export async function bytVyOchOppna(formData: FormData): Promise<void> {
  const { url } = await bytVy(formData);
  if (url) oppnaEfterIdentitetsbyte(url);
}

/** Formulärets action för utloggningen. */
export async function loggaUtOchOppna(): Promise<void> {
  const { url } = await signOut();
  oppnaEfterIdentitetsbyte(url);
}

function laddaOmVidByte(fran: string, till: string): void {
  const byte = `${fran}>${till}`;
  try {
    if (window.sessionStorage.getItem(OMLADDNING_NYCKEL) === byte) return;
    window.sessionStorage.setItem(OMLADDNING_NYCKEL, byte);
  } catch {
    // Utan sessionStorage (privat läge) finns inget loopskydd att lita på;
    // en omladdning är ändå rätt svar på ett verkligt byte.
  }
  window.location.reload();
}

function glomOmladdning(): void {
  try {
    window.sessionStorage.removeItem(OMLADDNING_NYCKEL);
  } catch {
    // Inget sparat att glömma.
  }
}

/**
 * Jämförelsen. Egen komponent i en Suspense-gräns: useSearchParams kräver det
 * på sidor som renderas statiskt, och kontrollen ritar ingenting.
 */
function Identitetskontroll({ identitet }: Readonly<{ identitet: string }>) {
  const pathname = usePathname();
  const sokning = useSearchParams().toString();

  const kontrollera = useCallback(async () => {
    try {
      const svar = await fetch("/api/snajp-support/identitet", { cache: "no-store" });
      const aktuell = svar.headers.get(IDENTITET_HUVUD);
      // Tomt eller saknat värde är "okänt" (uppslaget föll), inte ett byte.
      if (aktuell && aktuell !== identitet) laddaOmVidByte(identitet, aktuell);
      // Stämmer det igen är bytet klart: nästa byte, även tillbaka, får ladda om.
      if (aktuell === identitet) glomOmladdning();
    } catch {
      // Nätfel: nästa navigering eller nästa fokus frågar igen.
    }
  }, [identitet]);

  useEffect(() => {
    void kontrollera();
  }, [kontrollera, pathname, sokning]);

  useEffect(() => {
    const vidSynlig = () => {
      if (document.visibilityState === "visible") void kontrollera();
    };
    const vidFokus = () => void kontrollera();
    const vidMeddelande = () => void kontrollera();
    const lyssnare = identitetskanal();
    window.addEventListener("focus", vidFokus);
    document.addEventListener("visibilitychange", vidSynlig);
    lyssnare?.addEventListener("message", vidMeddelande);
    return () => {
      window.removeEventListener("focus", vidFokus);
      document.removeEventListener("visibilitychange", vidSynlig);
      lyssnare?.removeEventListener("message", vidMeddelande);
    };
  }, [kontrollera]);

  return null;
}

type DashboardContextValue = DashboardState & {
  scope: Scope;
  setScope: (next: Scope) => void;
  /** Scopes worth offering. A single-product workspace gets no switch at all. */
  availableScopes: Scope[];
  /** True when the given product should render under the current scope. */
  shows: (product: ProductKey) => boolean;
};

const FALLBACK: DashboardState = {
  // Härledd, inte uppräknad. Stod som ["leads", "support"] och blev fel i samma
  // sekund som bokföringen blev en produkt — samma glidning som ALL_PRODUCTS i
  // lib/data/dashboard.ts hade. Fallbacken är permissiv med flit (den finns för
  // marknadsföringsytorna), och en permissiv lista som glömmer en produkt är
  // permissiv på fel sätt: den döljer något i stället för att visa allt.
  products: [...productKeys],
  addons: [],
  workspaceName: null,
  userEmail: null,
  signedIn: false,
  isDemo: false,
  isPlatformAdmin: false,
  vy: "admin" as const,
  impersonation: null,
  arLasare: false,
  initialScope: "both" as const
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function DashboardProvider({
  state,
  children
}: Readonly<{ state: DashboardState; children: React.ReactNode }>) {
  const availableScopes: Scope[] =
    state.products.length > 1 ? ["both", ...state.products] : [...state.products];

  // Startvärdet kommer FÄRDIGT från servern, som redan läst och validerat
  // cookien (se lib/data/dashboard.ts). Tidigare hämtades det ur localStorage i
  // en useEffect efter mount, vilket gav ett synligt hopp — sidan renderade
  // först i "både" och bytte sedan — och gjorde värdet osynligt för varje
  // server-komponent.
  //
  // products kan vara TOM sedan entitlements blev fail-closed (Fas 3), därav
  // fallbacken: utan den jämför shows() mot undefined, vilket ser ut som ett
  // renderingsfel långt från orsaken.
  const [scope, setScopeState] = useState<Scope>(
    availableScopes.includes(state.initialScope) ? state.initialScope : (availableScopes[0] ?? "both")
  );

  const setScope = useCallback((next: Scope) => {
    setScopeState(next);
    // Ett år: läget är ett arbetssätt, inte en session. Lax räcker — cookien
    // styr ingenting utom vad som ritas, och grinden som räknar är `products`.
    document.cookie = `${SCOPE_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
  }, []);

  const shows = useCallback(
    (product: ProductKey) =>
      state.products.includes(product) && (scope === "both" || scope === product),
    [scope, state.products]
  );

  const value = useMemo(
    () => ({ ...state, scope, setScope, availableScopes, shows }),
    // availableScopes is recomputed each render but is value-stable per session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state, scope, setScope, shows]
  );

  return (
    <DashboardContext.Provider value={value}>
      {state.identitet ? (
        <Suspense fallback={null}>
          <Identitetskontroll identitet={state.identitet} />
        </Suspense>
      ) : null}
      {children}
    </DashboardContext.Provider>
  );
}

/**
 * Safe outside the dashboard tree: /settings renders the same chrome without a
 * provider, and gets the permissive default rather than throwing.
 */
export function useDashboard(): DashboardContextValue {
  const value = useContext(DashboardContext);
  if (value) return value;

  return {
    ...FALLBACK,
    scope: "both",
    setScope: () => {},
    availableScopes: ["both", ...productKeys],
    shows: () => true
  };
}
