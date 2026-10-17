"use client";

import { flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export type KvittoFlik = "oversikt" | "kvitton";

const FLIKAR: [KvittoFlik, Localized][] = [
  ["oversikt", { sv: "Översikt", en: "Overview" }],
  ["kvitton", { sv: "Kvitton", en: "Receipts" }]
];

/** Kvittohanterarens flikrad, samma mönster som Kundtjänstens (components/ui.tsx `flik`). */
export function KvittoFlikar({
  vald,
  onValj,
  etiketter
}: Readonly<{ vald: KvittoFlik; onValj: (flik: KvittoFlik) => void; etiketter?: Partial<Record<KvittoFlik, Localized>> }>) {
  const { text } = useLocale();
  return (
    <div className={fliklista} role="tablist" aria-label={text({ sv: "Kvittohanterarens ytor", en: "Receipt handler areas" })}>
      {FLIKAR.map(([id, etikett]) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={vald === id}
          onClick={() => onValj(id)}
          className={cn(flik, vald === id ? flikAktiv : flikInaktiv)}
        >
          {text(etiketter?.[id] ?? etikett)}
        </button>
      ))}
    </div>
  );
}
