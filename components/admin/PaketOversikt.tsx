"use client";

import { KpiKort, Munkdiagram, Panelrubrik, type Andel, type Kpi } from "@/components/dashboard/OversiktPaneler";
import { panelKort } from "@/components/ui";
import type { TenantRow } from "@/lib/data/admin";
import { ADMIN } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";
import { paketForProdukter } from "@/lib/paket";
import { formateraPris } from "@/lib/pricing";
import { cn } from "@/lib/utils";

/**
 * Kunder › Paket och avtal, överdelen (Sebbe 2026-10-07: översikternas layout).
 *
 * Samma fyra tal som förut (aktiva, pausade, avslutade, paketvärde per månad)
 * som kort, och två munkar: vilka paket de aktiva kunderna har och hur
 * kontolägena fördelar sig. Paketvärdet räknar bara AKTIVA kunder med ett
 * exakt paket; ett eget urval utan paketpris räknas inte, hellre en siffra
 * som är för låg och sann än en som gissar.
 */

const PAKETFARG = ["oklch(var(--chart-ramp-6))", "oklch(var(--chart-ramp-4))", "oklch(var(--chart-ramp-2))", "oklch(var(--moss))", "oklch(var(--chart-ochre))"];

const EGET: Localized = { sv: "Eget urval", en: "Custom selection" };

function lage(rad: TenantRow): "aktiv" | "pausad" | "avstangd" {
  return rad.status ?? (rad.active === false ? "avstangd" : "aktiv");
}

export function PaketOversikt({ kunder }: Readonly<{ kunder: TenantRow[] }>) {
  const { text } = useLocale();
  const aktiva = kunder.filter((r) => lage(r) === "aktiv");
  const pausade = kunder.filter((r) => lage(r) === "pausad").length;
  const avstangda = kunder.filter((r) => lage(r) === "avstangd").length;

  const perPaket = new Map<string, { etikett: Localized; antal: number; varde: number }>();
  for (const rad of aktiva) {
    const paket = paketForProdukter(rad.products);
    const nyckel = paket?.namn ?? "eget";
    const post = perPaket.get(nyckel) ?? { etikett: paket ? { sv: paket.namn, en: paket.namn } : EGET, antal: 0, varde: 0 };
    post.antal += 1;
    post.varde += paket?.prisPerManad ?? 0;
    perPaket.set(nyckel, post);
  }
  const manadsintakt = [...perPaket.values()].reduce((s, p) => s + p.varde, 0);
  const paketdelar: Andel[] = [...perPaket.entries()]
    .sort((x, y) => y[1].antal - x[1].antal)
    .map(([id, p], i) => ({ id, etikett: p.etikett, antal: p.antal, farg: id === "eget" ? "oklch(var(--ink-subtle))" : PAKETFARG[i % PAKETFARG.length] }));

  const kpier: Kpi[] = [
    { id: "aktiva", etikett: ADMIN.aktivaKunder, varde: aktiva.length, detalj: { sv: `av ${kunder.length} kunder`, en: `of ${kunder.length} customers` } },
    { id: "pausade", etikett: ADMIN.pausade, varde: pausade, detalj: { sv: "fakturering och agenter pausade", en: "billing and agents paused" } },
    { id: "avslutade", etikett: ADMIN.avslutade, varde: avstangda, detalj: { sv: "kontot avslutat", en: "account closed" } },
    { id: "varde", etikett: ADMIN.paketvardePerManad, varde: null, visning: formateraPris(manadsintakt), detalj: ADMIN.aktivaMedExaktPaket }
  ];

  return (
    <div className="mt-8 flex min-w-0 flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={{ sv: "", en: "" }} />
        ))}
      </div>
      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <section aria-labelledby="paket-fordelning" className={cn(panelKort, "min-w-0")}>
          <Panelrubrik id="paket-fordelning" titel={{ sv: "Paket bland aktiva kunder", en: "Plans among active customers" }} />
          <Munkdiagram delar={paketdelar} etikett={{ sv: "Kunder per paket", en: "Customers per plan" }} mitt={{ sv: "aktiva", en: "active" }} />
        </section>
        <section aria-labelledby="paket-lage" className={cn(panelKort, "min-w-0")}>
          <Panelrubrik id="paket-lage" titel={{ sv: "Kontoläge", en: "Account status" }} />
          <Munkdiagram
            delar={[
              { id: "aktiv", etikett: ADMIN.aktivaKunder, antal: aktiva.length, farg: "oklch(var(--moss))" },
              { id: "pausad", etikett: ADMIN.pausade, antal: pausade, farg: "oklch(var(--chart-ochre))" },
              { id: "avstangd", etikett: ADMIN.avslutade, antal: avstangda, farg: "oklch(var(--danger))" }
            ]}
            etikett={{ sv: "Kunder per läge", en: "Customers per status" }}
            mitt={{ sv: "kunder", en: "customers" }}
          />
          <p className="mt-4 text-[0.8125rem] text-ink-subtle">
            {text({ sv: "Testkunderna står inte med: de har inget paket att fakturera.", en: "Test customers are not included: they have no plan to bill." })}
          </p>
        </section>
      </div>
    </div>
  );
}
