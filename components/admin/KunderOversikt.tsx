"use client";

import Link from "next/link";
import { FelOchEskaleringar } from "@/components/admin/FelOchEskaleringar";
import { Kundtabell, trialDagar, trialStatus } from "@/components/admin/Kundtabell";
import {
  Aktivitetsgraf,
  KpiKort,
  Munkdiagram,
  Panelrubrik,
  forandring,
  type Andel,
  type Kpi,
  type Vecka
} from "@/components/dashboard/OversiktPaneler";
import { Badge, Cell, Tabell, etikett, meta, panelKort } from "@/components/ui";
import type { BerikadTenant } from "@/lib/admin/exempeldata";
import { ADMIN, a, datum } from "@/lib/admin/sprak";
import { arTestyta, type Kundstatistik } from "@/lib/admin/statistik";
import type { EventRow } from "@/lib/data/admin";
import { useLocale, type Localized } from "@/lib/i18n";
import { paketForProdukter } from "@/lib/paket";
import { cn } from "@/lib/utils";

/**
 * Kunder › Alla kunder i översikternas layout (Sebbes beställning 2026-10-07).
 *
 *   nyckeltal: kunder, avtal i år, nya kunder (fyra veckor), provperioder som slutar
 *   nya kunder och signerade avtal per vecka · kontoläge och avtal (munkar)
 *   alla kunder (tabellen, oförändrad)
 *   fel och eskaleringar | provperioder   (split view)
 *
 * Inget nytt räknas här. Statistiken är `beraknaKundstatistik` (servern, samma
 * klocka som resten av sidan), felen är FelOchEskaleringar och tabellen är
 * Kundtabell. Det som tidigare var Kundstatistiks egna SVG-staplar är nu
 * Aktivitetsgrafen, med taktmeningen, perioderna och tabellvyn kvar.
 *
 * Intäkter och utgifter har MEDVETET ingen plats här: se app/admin/kunder/page.tsx.
 */

const T = {
  kunder: { sv: "Kunder", en: "Customers" },
  medAvtal: { sv: "med avtal", en: "with a contract" },
  iTrial: { sv: "i provperiod", en: "on trial" },
  senasteFyra: { sv: "de senaste fyra veckorna", en: "the last four weeks" },
  fyraFore: { sv: "de fyra veckorna före", en: "the four weeks before" },
  trialSlutar: { sv: "Provperioder som slutar", en: "Trials ending" },
  inomSju: { sv: "inom sju dagar, utan avtal", en: "within seven days, without a contract" },
  fordelning: { sv: "Fördelning", en: "Breakdown" },
  kontolage: { sv: "Kontoläge", en: "Account status" },
  avtalOchTrial: { sv: "Avtal och provperiod", en: "Contract and trial" },
  kunderMitt: { sv: "kunder", en: "customers" },
  aktiv: { sv: "Aktiv", en: "Active" },
  pausad: { sv: "Pausad", en: "Paused" },
  avstangd: { sv: "Avslutad", en: "Closed" },
  testyta: { sv: "Testarbetsyta", en: "Test workspace" },
  avtal: { sv: "Avtal signerat", en: "Contract signed" },
  trial: { sv: "I provperiod", en: "On trial" },
  trialSlut: { sv: "Provperiod slut, inget avtal", en: "Trial ended, no contract" },
  ingetAvtal: { sv: "Inget avtal, ingen provperiod", en: "No contract, no trial" },
  allaKunder: { sv: "Alla kunder", en: "All customers" },
  provperioder: { sv: "Provperioder", en: "Trials" },
  provperioderText: {
    sv: "Kunder utan avtal, den som slutar först överst. Slutade perioder står kvar i fyra veckor.",
    en: "Customers without a contract, the one ending first on top. Ended trials stay for four weeks."
  },
  ingaProvperioder: { sv: "Ingen kund är i provperiod just nu.", en: "No customer is on trial right now." },
  totalt: { sv: "totalt", en: "in total" },
  paket: { sv: "Paket", en: "Plan" },
  egetUrval: { sv: "Eget urval", en: "Custom selection" },
  ingetPaket: { sv: "Inget paket", en: "No plan" }
} satisfies Record<string, Localized>;

/** Samma paketfärger som Översiktens munk: nyanser långt nog isär för att skiljas åt. */
const PAKETFARG = ["oklch(var(--chart-ramp-6))", "oklch(var(--chart-ramp-4))", "oklch(var(--chart-ramp-2))", "oklch(var(--moss))", "oklch(var(--chart-ochre))"];

/** "v.35" på svenska, "w.35" på engelska, som Kundstatistik hade dem. */
function veckoetikett(vecka: number, locale: "sv" | "en"): string {
  return locale === "sv" ? `v.${vecka}` : `w.${vecka}`;
}

function kontolage(k: BerikadTenant): "aktiv" | "pausad" | "avstangd" | "testyta" {
  if (arTestyta(k.slug)) return "testyta";
  return k.status ?? (k.active === false ? "avstangd" : "aktiv");
}

export function KunderOversikt({
  kunder,
  events,
  taketNaddes,
  nu,
  stat
}: Readonly<{
  kunder: BerikadTenant[];
  events: EventRow[];
  taketNaddes: boolean;
  nu: number;
  stat: Kundstatistik;
}>) {
  const { locale, text } = useLocale();

  const riktiga = kunder.filter((k) => !arTestyta(k.slug));
  const medAvtal = riktiga.filter((k) => k.avtal_signerat).length;
  const iTrial = riktiga.filter((k) => !k.avtal_signerat && k.trial_slut && trialDagar(k.trial_slut) >= 0);
  const trialSnart = iTrial.filter((k) => trialDagar(k.trial_slut as string) <= 7);

  const kpier: Kpi[] = [
    {
      id: "kunder",
      etikett: T.kunder,
      varde: riktiga.length,
      detalj: {
        sv: `${medAvtal} ${T.medAvtal.sv} · ${iTrial.length} ${T.iTrial.sv}`,
        en: `${medAvtal} ${T.medAvtal.en} · ${iTrial.length} ${T.iTrial.en}`
      }
    },
    {
      id: "avtal",
      etikett: ADMIN.avtalAret,
      varde: stat.avtal.aret,
      detalj: { sv: `${stat.avtal.totalt} ${T.totalt.sv}`, en: `${stat.avtal.totalt} ${T.totalt.en}` }
    },
    {
      id: "nya",
      etikett: ADMIN.nyaKunder,
      varde: stat.takt.senaste.kunder,
      forandring: forandring(stat.takt.senaste.kunder, stat.takt.foregaende.kunder),
      detalj: T.senasteFyra
    },
    {
      id: "trial",
      etikett: T.trialSlutar,
      varde: trialSnart.length,
      larm: trialSnart.length > 0,
      href: "#provperioder",
      detalj: T.inomSju
    }
  ];

  const taktText = text({
    sv: `${stat.takt.senaste.kunder} nya kunder och ${stat.takt.senaste.avtal} signerade avtal de senaste fyra veckorna, mot ${stat.takt.foregaende.kunder} respektive ${stat.takt.foregaende.avtal} de fyra veckorna före.`,
    en: `${stat.takt.senaste.kunder} new customers and ${stat.takt.senaste.avtal} signed contracts in the last four weeks, against ${stat.takt.foregaende.kunder} and ${stat.takt.foregaende.avtal} in the four weeks before.`
  });

  const graf: Vecka[] = stat.veckor.map((v) => ({ week: veckoetikett(v.vecka, locale), nya_kunder: v.nyaKunder, avtal: v.avtal }));

  const lage = { aktiv: 0, pausad: 0, avstangd: 0, testyta: 0 };
  for (const k of kunder) lage[kontolage(k)] += 1;
  const lagedelar: Andel[] = [
    { id: "aktiv", etikett: T.aktiv, antal: lage.aktiv, farg: "oklch(var(--moss))" },
    { id: "pausad", etikett: T.pausad, antal: lage.pausad, farg: "oklch(var(--chart-ochre))" },
    { id: "avstangd", etikett: T.avstangd, antal: lage.avstangd, farg: "oklch(var(--danger))" },
    { id: "testyta", etikett: T.testyta, antal: lage.testyta, farg: "oklch(var(--ink-subtle))" }
  ];
  const trialSlut = riktiga.filter((k) => !k.avtal_signerat && k.trial_slut && trialDagar(k.trial_slut) < 0).length;
  const avtalsdelar: Andel[] = [
    { id: "avtal", etikett: T.avtal, antal: medAvtal, farg: "oklch(var(--chart-ramp-6))" },
    { id: "trial", etikett: T.trial, antal: iTrial.length, farg: "oklch(var(--chart-ramp-3))" },
    { id: "slut", etikett: T.trialSlut, antal: trialSlut, farg: "oklch(var(--chart-ochre))" },
    {
      id: "inget",
      etikett: T.ingetAvtal,
      antal: riktiga.length - medAvtal - iTrial.length - trialSlut,
      farg: "oklch(var(--ink-subtle))"
    }
  ];

  // Paketen ur workspaces.products, samma uppslag som Översikten. En kund utan
  // exakt paket står som "Eget urval" eller "Inget paket".
  const perPaket = new Map<string, number>();
  for (const k of riktiga) {
    const namn = paketForProdukter(k.products)?.namn ?? (k.products?.length ? "eget" : "inget");
    perPaket.set(namn, (perPaket.get(namn) ?? 0) + 1);
  }
  const paketdelar: Andel[] = [...perPaket.entries()]
    .sort((x, y) => y[1] - x[1])
    .map(([namn, n], i) => ({
      id: namn,
      etikett: namn === "eget" ? T.egetUrval : namn === "inget" ? T.ingetPaket : { sv: namn, en: namn },
      antal: n,
      farg: namn === "eget" || namn === "inget" ? "oklch(var(--ink-subtle))" : PAKETFARG[i % PAKETFARG.length]
    }));

  // Provperioderna: pågående först (den som slutar först överst), sedan de
  // som slutat de senaste fyra veckorna utan att ett avtal kom in.
  const provperioder = riktiga
    .filter((k) => !k.avtal_signerat && k.trial_slut && trialDagar(k.trial_slut) >= -28)
    .sort((x, y) => {
      const dx = trialDagar(x.trial_slut as string);
      const dy = trialDagar(y.trial_slut as string);
      if ((dx < 0) !== (dy < 0)) return dx < 0 ? 1 : -1;
      return dx < 0 ? dy - dx : dx - dy;
    });

  const perioder: { id: string; n: string; varde: number }[] = [
    { id: "idag", n: "avtalIdag", varde: stat.avtal.idag },
    { id: "veckan", n: "avtalVeckan", varde: stat.avtal.veckan },
    { id: "manaden", n: "avtalManaden", varde: stat.avtal.manaden },
    { id: "aret", n: "avtalAret", varde: stat.avtal.aret }
  ];

  return (
    <div className="mt-8 flex min-w-0 flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={T.fyraFore} />
        ))}
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="kunder-statistik" className={cn(panelKort, "min-w-0 lg:col-span-7")}>
          <Panelrubrik
            id="kunder-statistik"
            titel={{
              sv: `${a("nyaKunder", "sv")} och ${a("signeradeAvtal", "sv").toLowerCase()}`,
              en: `${a("nyaKunder", "en")} and ${a("signeradeAvtal", "en").toLowerCase()}`
            }}
            under={{ sv: a("perVecka12", "sv"), en: a("perVecka12", "en") }}
          />
          <Aktivitetsgraf
            typ="staplar"
            veckor={graf}
            serier={[
              { nyckel: "nya_kunder", etikett: ADMIN.nyaKunder, ton: "chart-blue" },
              { nyckel: "avtal", etikett: ADMIN.signeradeAvtal, ton: "chart-ochre" }
            ]}
          />
          <p className="mt-4 max-w-[70ch] text-[0.875rem] leading-6 text-ink-muted">{taktText}</p>
          {/* Exempelraderna ingår i talen och i kurvan. Utan den här meningen
              ser 12 avtal ut som 12 sålda avtal. */}
          {stat.exempel > 0 ? (
            <p className={cn(meta, "mt-1 max-w-[70ch]")}>
              {stat.exempel === 1
                ? text({
                    sv: "Talen och kurvan räknar med exempeldata från en kund, och dess datum är påhittade.",
                    en: "The figures and the chart include example data from one customer, and its dates are invented."
                  })
                : text({
                    sv: `Talen och kurvan räknar med exempeldata från ${stat.exempel} kunder, och deras datum är påhittade.`,
                    en: `The figures and the chart include example data from ${stat.exempel} customers, and their dates are invented.`
                  })}
            </p>
          ) : null}
          <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-ink/10 pt-4 sm:grid-cols-4 sm:gap-4">
            {perioder.map((x) => (
              <div key={x.id}>
                <dt className={etikett}>{a(x.n, locale)}</dt>
                <dd className="num mt-1 text-[1.25rem] font-semibold tabular-nums text-ink">{x.varde}</dd>
              </div>
            ))}
          </dl>
          {/* Tabellversionen av samma tal, för den som hellre läser siffror än kurvor. */}
          <details className="mt-3 text-[0.8125rem] text-ink-muted">
            <summary className="focus-ring inline-flex min-h-9 cursor-pointer items-center rounded-input text-mineral hover:text-ink">
              {a("visaSomTabell", locale)}
            </summary>
            <div className="mt-2">
              <Tabell
                minBredd={320}
                kolumner={[
                  { rubrik: a("vecka", locale), bredd: "34%" },
                  { rubrik: a("nyaKunder", locale), bredd: "33%", hoger: true },
                  { rubrik: a("signeradeAvtal", locale), bredd: "33%", hoger: true }
                ]}
              >
                {stat.veckor.map((vecka, i) => (
                  <tr key={`tab-${vecka.vecka}-${i}`}>
                    <Cell>{veckoetikett(vecka.vecka, locale)}</Cell>
                    <Cell hoger>{vecka.nyaKunder}</Cell>
                    <Cell hoger>{vecka.avtal}</Cell>
                  </tr>
                ))}
              </Tabell>
            </div>
          </details>
        </section>

        <section aria-labelledby="kunder-fordelning" className={cn(panelKort, "min-w-0 lg:col-span-5")}>
          <Panelrubrik id="kunder-fordelning" titel={T.fordelning} />
          <div className="grid gap-6">
            <Munkdiagram delar={lagedelar} etikett={T.kontolage} mitt={T.kunderMitt} />
            <Munkdiagram delar={avtalsdelar} etikett={T.avtalOchTrial} mitt={T.kunderMitt} />
            <Munkdiagram delar={paketdelar} etikett={T.paket} mitt={T.kunderMitt} />
          </div>
        </section>
      </div>

      <section aria-labelledby="kunder-alla" className={cn(panelKort, "min-w-0")}>
        <Panelrubrik id="kunder-alla" titel={T.allaKunder} antal={kunder.length} under={ADMIN.kunderIngress} />
        <Kundtabell kunder={kunder} />
      </section>

      <div className="grid min-w-0 items-start gap-4 xl:grid-cols-2">
        <FelOchEskaleringar tenants={kunder} events={events} taketNaddes={taketNaddes} nu={nu} />
        <section id="provperioder" aria-labelledby="kunder-provperioder" className={cn(panelKort, "min-w-0 scroll-mt-24")}>
          <Panelrubrik id="kunder-provperioder" titel={T.provperioder} antal={iTrial.length} under={T.provperioderText} />
          {provperioder.length === 0 ? (
            <p className={meta}>{text(T.ingaProvperioder)}</p>
          ) : (
            <ul className="divide-y divide-ink/10">
              {provperioder.map((k) => {
                const dagar = trialDagar(k.trial_slut as string);
                return (
                  <li key={k.id} className="flex items-center justify-between gap-4 py-2.5">
                    <span className="min-w-0">
                      <Link
                        href={`/admin/kunder/${k.id}/data`}
                        className="focus-ring block truncate rounded-input text-[0.9375rem] font-medium underline decoration-ink/20 underline-offset-4 hover:text-ochre"
                      >
                        {k.name}
                      </Link>
                      <span className={cn(meta, "block truncate")}>
                        {text({ sv: "kund sedan", en: "customer since" })} {datum(k.kund_sedan, locale)}
                      </span>
                    </span>
                    <Badge tone={dagar < 0 ? "neutral" : dagar <= 7 ? "danger" : dagar <= 14 ? "warn" : "good"}>
                      {trialStatus(k, locale, text)}
                    </Badge>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
