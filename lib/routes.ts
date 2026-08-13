import type { CopyKey } from "@/lib/i18n";

export type AppRoute = {
  href: string;
  labelKey: CopyKey;
  group: "sales" | "workspace" | "admin";
};

export const appRoutes: AppRoute[] = [
  { href: "/dashboard", labelKey: "nav.dashboard", group: "workspace" },
  { href: "/assistant", labelKey: "nav.assistant", group: "workspace" },
  { href: "/leads", labelKey: "nav.leads", group: "sales" },
  { href: "/companies", labelKey: "nav.companies", group: "sales" },
  { href: "/contacts", labelKey: "nav.contacts", group: "sales" },
  { href: "/campaigns", labelKey: "nav.campaigns", group: "sales" },
  { href: "/emails", labelKey: "nav.emails", group: "sales" },
  { href: "/kundtjanst", labelKey: "nav.kundtjanst", group: "workspace" },
  { href: "/snajp-support", labelKey: "nav.snajpSupport", group: "workspace" },
  { href: "/analytics", labelKey: "nav.analytics", group: "workspace" },
  { href: "/inbox", labelKey: "nav.inbox", group: "workspace" },
  { href: "/settings", labelKey: "nav.settings", group: "admin" }
];

export const settingsRoutes = [
  { href: "/settings/mailboxes", label: { sv: "Mailboxes", en: "Mailboxes" } },
  { href: "/settings/team", label: { sv: "Team", en: "Team" } },
  { href: "/settings/billing", label: { sv: "Fakturering", en: "Billing" } }
] as const;

// Auth route guards (pure, no server dependencies — safe for middleware)
export const protectedRoutePrefixes = [
  "/dashboard",
  "/assistant",
  "/leads",
  "/companies",
  "/contacts",
  "/campaigns",
  "/emails",
  "/analytics",
  "/inbox",
  "/settings",
  "/onboarding",
  "/kundtjanst",
  // Kundens egen Snajp-arbetsyta. Den publika demon ligger på /demo/snajp och
  // är avsiktligt INTE med här.
  "/snajp-support"
] as const;

export const authRoutes = ["/login", "/auth/callback"] as const;

export function isProtectedRoute(pathname: string): boolean {
  return protectedRoutePrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export function isAuthRoute(pathname: string): boolean {
  return authRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}
