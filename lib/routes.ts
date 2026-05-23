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
  { href: "/analytics", labelKey: "nav.analytics", group: "workspace" },
  { href: "/inbox", labelKey: "nav.inbox", group: "workspace" },
  { href: "/settings", labelKey: "nav.settings", group: "admin" }
];

export const settingsRoutes = [
  { href: "/settings/mailboxes", label: { sv: "Mailboxes", en: "Mailboxes" } },
  { href: "/settings/team", label: { sv: "Team", en: "Team" } },
  { href: "/settings/billing", label: { sv: "Fakturering", en: "Billing" } }
] as const;
