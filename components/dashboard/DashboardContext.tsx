"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { DashboardState } from "@/lib/data/dashboard";
import type { ProductKey } from "@/lib/routes";
import { isProductKey } from "@/lib/routes";

/** What the user is currently looking at, within what they are entitled to. */
export type Scope = ProductKey | "both";

type DashboardContextValue = DashboardState & {
  scope: Scope;
  setScope: (next: Scope) => void;
  /** Scopes worth offering. A single-product workspace gets no switch at all. */
  availableScopes: Scope[];
  /** True when the given product should render under the current scope. */
  shows: (product: ProductKey) => boolean;
};

const FALLBACK: DashboardState = {
  products: ["leads", "support"],
  addons: [],
  variant: "demo",
  workspaceName: null,
  signedIn: false,
  isPlatformAdmin: false
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

const STORAGE_KEY = "snajp.dashboard.scope";

export function DashboardProvider({
  state,
  children
}: Readonly<{ state: DashboardState; children: React.ReactNode }>) {
  const availableScopes: Scope[] =
    state.products.length > 1 ? ["both", ...state.products] : [...state.products];

  // products kan vara TOM sedan entitlements blev fail-closed (Fas 3). Utan
  // fallbacken här blir initialvärdet undefined, och shows() jämför mot det —
  // vilket ser ut som ett renderingsfel långt från orsaken.
  const [scope, setScopeState] = useState<Scope>(availableScopes[0] ?? "both");

  // Restore after mount rather than during render: reading localStorage while
  // rendering would desync the server and client markup.
  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return;
    const valid = stored === "both" || isProductKey(stored);
    if (valid && availableScopes.includes(stored as Scope)) {
      setScopeState(stored as Scope);
    }
    // availableScopes is derived from server state and stable for the session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setScope = useCallback((next: Scope) => {
    setScopeState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
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
    availableScopes: ["both", "leads", "support"],
    shows: () => true
  };
}
