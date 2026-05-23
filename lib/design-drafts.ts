import { campaigns, companies, contacts } from "@/lib/mock-data";

export type DraftVariant = "editorial-clean" | "modern-blend";

export const draftVariants = ["editorial-clean", "modern-blend"] as const;

export function isDraftVariant(value: string): value is DraftVariant {
  return draftVariants.includes(value as DraftVariant);
}

export const showcaseStaticSlugs = [
  [],
  ["assistant"],
  ["leads"],
  ["companies"],
  ["companies", companies[0].id],
  ["contacts"],
  ["contacts", contacts[0].id],
  ["campaigns"],
  ["campaigns", campaigns[0].id],
  ["emails"],
  ["analytics"],
  ["inbox"],
  ["settings"],
  ["settings", "mailboxes"],
  ["settings", "team"],
  ["settings", "billing"]
];
