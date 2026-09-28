"use client";

import { Mail } from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { btnLiten, btnSecondary } from "@/components/ui";
import { cn } from "@/lib/utils";
import { KONTAKT_MEJL, mejlaOss } from "@/components/marketing/copy";
import { PAKET, PRIS_PREFIX, PRIS_SAKNAS, formateraPris } from "@/lib/pricing";
import { useLocale } from "@/lib/i18n";

/**
 * Inställningar → Plan och fakturering.
 *
 * ## Vad som stod här förut
 *
 * Tre påhittade rader: "Plan · Team · 14 900 kr/mån", "Leads · 312 av 1000
 * denna månad", "Seats · 4 av 8 aktiva användare". Ingen av siffrorna kom från
 * kundens arbetsyta, planen "Team" har aldrig funnits i prislistan, och
 * 14 900 kr är inte ett pris vi tar. En kund som läste sidan fick alltså ett
 * felaktigt belopp på sin egen faktureringssida.
 *
 * ## Vad den gör nu
 *
 * Visar det vi FAKTISKT vet: vilka produkter arbetsytan har (samma
 * `products` som grindar varje flik, härlett ur entitlements på servern) och
 * vad de paketen kostar enligt `lib/pricing.ts` — samma källa som prislistan
 * på webbplatsen, så de två aldrig kan säga olika saker.
 *
 * Förbrukning står INTE här. Vi mäter den inte per arbetsyta ännu, och en
 * uppmätt-ser-ut-siffra är värre än ingen: den enda som kan falsifiera den är
 * kunden, och de gör det på fakturan.
 */

/**
 * Produktuppsättning → paketnamn.
 *
 * Kartan är AVSIKTLIGT gles. Med tre produkter finns sju kombinationer, och
 * bara fem av dem är paket vi säljer. Resten faller igenom till "er plan är
 * satt manuellt", vilket är sant: en arbetsyta med leads och bokföring men
 * inte support har fått den uppsättningen av en människa, inte av prislistan.
 *
 * Att hitta på ett paketnamn för varje kombination hade betytt fyra namn som
 * ingen prislista känner igen, och ett pris kunden inte kan slå upp.
 */
const PAKET_FOR_PRODUKTER: Record<string, string> = {
  "leads": "leads",
  "support": "support",
  "bookkeeping": "bookkeeping",
  "leads+support": "duo",
  // Nyckeln är produkterna SORTERADE och hopfogade — se `nyckel` nedan.
  "bookkeeping+leads+support": "trio"
};

export function PlanSettings() {
  const { products, addons, workspaceName } = useDashboard();
  const { text } = useLocale();

  const nyckel = [...products].sort().join("+");
  const paketId = PAKET_FOR_PRODUKTER[nyckel];
  const paket = PAKET.find((p) => p.id === paketId);

  return (
    <div className="grid gap-8">
      <div>
        <h2 className="kicker text-mineral">Er plan</h2>
        {/* Två kolumner: vad ni HAR till vänster, hur ni byter till höger.
            Staplat under md: två kolumner à sex på en telefon ger ett prisfält
            på halva bredden, samma fälla som gap-x-8 vid 320px (se
            WorkspaceViews). */}
        <div className="mt-4 grid grid-cols-12 gap-x-0 gap-y-8 border-y border-ink/15 py-5 md:gap-x-10">
          <div className="col-span-12 md:col-span-6">
            {paket ? (
              <>
                <p className="flex items-baseline gap-2">
                  <span className="text-[1.0625rem] font-semibold">{paket.namn}</span>
                  <span className="text-[0.9375rem] text-mineral">
                    {paket.prisPerManad === null
                      ? text(PRIS_SAKNAS)
                      : `${text(PRIS_PREFIX)} ${formateraPris(paket.prisPerManad)}/mån`}
                  </span>
                </p>
                <p className="mt-2 max-w-[58ch] text-[0.9375rem] leading-6 text-ink-muted">
                  {text(paket.beskrivning)}
                </p>
              </>
            ) : (
              <p className="max-w-[58ch] text-[0.9375rem] leading-6 text-ink-muted">
                {products.length === 0
                  ? "Ingen aktiv produkt."
                  : "Manuellt satt plan. Kontakta oss om ni vill byta."}
              </p>
            )}
          </div>

          {/* Paketbyte via kontakt (beslut 2026-09-21), inte en väljare: vi
              fakturerar personligen, så ett byte är något vi ordnar med
              kunden. Knappen öppnar kundens mejlprogram med vår adress i
              Till-fältet. */}
          <div className="col-span-12 md:col-span-6">
            <h3 className="kicker text-mineral">Byt paket</h3>
            <p className="mt-3 max-w-[46ch] text-[0.9375rem] leading-6 text-ink-muted">
              Vill du uppgradera eller byta paket, kontakta oss nedan.
            </p>
            <a
              href={mejlaOss(`Byte av paket${workspaceName ? `: ${workspaceName}` : ""}`)}
              className={cn(btnSecondary, btnLiten, "mt-4 border border-ink/15 hover:border-ink/30")}
            >
              <Mail className="h-3.5 w-3.5" aria-hidden />
              Kontakta oss
            </a>
          </div>
        </div>
      </div>

      <div>
        <h2 className="kicker text-mineral">Det här ingår</h2>
        <ul className="mt-4 flex flex-col gap-2.5 border-y border-ink/15 py-5">
          {(paket?.ingar ?? []).map((rad, index) => (
            <li key={index} className="flex gap-2.5 text-[0.9375rem] leading-6 text-ink-muted">
              <span aria-hidden className="mt-[0.55em] h-1 w-1 shrink-0 rounded-full bg-ochre" />
              {text(rad)}
            </li>
          ))}
          {addons.length > 0 ? (
            <li className="mt-2 text-[0.9375rem] leading-6 text-ink-muted">
              Tillägg: {addons.join(", ")}
            </li>
          ) : null}
          {paket ? null : (
            <li className="text-[0.9375rem] leading-6 text-ink-muted">
              {products.length ? products.join(", ") : "—"}
            </li>
          )}
        </ul>
      </div>

      {/* Fakturering. Kunderna faktureras av oss personligen (beslut
          2026-09-21): ingen kortbetalning och ingen betalväxel i appen, så här
          finns inget kortformulär. Allt som rör betalning går via kontakt.
          Ingen förbrukningssiffra heller, se docstringen. */}
      <div>
        <h2 className="kicker text-mineral">Fakturering</h2>
        <div className="mt-4 border-y border-ink/15 py-5">
          <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
            Vi skickar e-faktura till{" "}
            {workspaceName ? <strong className="font-semibold text-ink">{workspaceName}</strong> : "er arbetsyta"}
            . Ingen kortbetalning görs här i appen.
          </p>
          <p className="mt-3 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
            Vill ni ändra fakturauppgifter eller säga upp, hör av er till oss så ordnar vi det.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-3">
            <a href={mejlaOss("Fakturering")} className={cn(btnSecondary, btnLiten, "border border-ink/15 hover:border-ink/30")}>
              <Mail className="h-3.5 w-3.5" aria-hidden />
              Kontakta oss
            </a>
            <span className="text-[0.875rem] text-ink-subtle">{KONTAKT_MEJL}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
