"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { DashboardState } from "@/lib/data/dashboard";
import type { ProductKey, Scope } from "@/lib/routes";
import { SCOPE_COOKIE, productKeys } from "@/lib/routes";

export type { Scope };

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
  signedIn: false,
  isDemo: false,
  isPlatformAdmin: false,
  vy: "admin" as const,
  impersonation: null,
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

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
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
