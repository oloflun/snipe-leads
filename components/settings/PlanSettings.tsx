"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { KONTAKT_MEJL, mejlaOss } from "@/components/marketing/copy";
import { PAKET, PRIS_PREFIX, formateraPris } from "@/lib/pricing";
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

const PAKET_FOR_PRODUKTER: Record<string, string> = {
  "leads": "leads",
  "support": "support",
  "leads+support": "duo"
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
        <div className="mt-4 border-y border-ink/15 py-5">
          {paket ? (
            <>
              <p className="flex items-baseline gap-2">
                <span className="text-[1.0625rem] font-semibold">{paket.namn}</span>
                <span className="text-[0.9375rem] text-mineral">
                  {text(PRIS_PREFIX)} {formateraPris(paket.prisPerManad)}/mån
                </span>
              </p>
              <p className="mt-2 max-w-[58ch] text-[0.9375rem] leading-6 text-ink/65">
                {text(paket.beskrivning)}
              </p>
            </>
          ) : (
            <p className="max-w-[58ch] text-[0.9375rem] leading-6 text-ink/65">
              {products.length === 0
                ? "Arbetsytan har ingen aktiv produkt. Hör av er så reder vi ut det."
                : "Er plan är satt manuellt och matchar inget standardpaket. Hör av er om ni vill se villkoren."}
            </p>
          )}
        </div>
      </div>

      <div>
        <h2 className="kicker text-mineral">Det här ingår</h2>
        <ul className="mt-4 flex flex-col gap-2.5 border-y border-ink/15 py-5">
          {(paket?.ingar ?? []).map((rad, index) => (
            <li key={index} className="flex gap-2.5 text-[0.9375rem] leading-6 text-ink/85">
              <span aria-hidden className="mt-[0.55em] h-1 w-1 shrink-0 rounded-full bg-ochre" />
              {text(rad)}
            </li>
          ))}
          {addons.length > 0 ? (
            <li className="mt-2 text-[0.9375rem] leading-6 text-ink/65">
              Tillägg: {addons.join(", ")}
            </li>
          ) : null}
          {paket ? null : (
            <li className="text-[0.9375rem] leading-6 text-ink/65">
              {products.length ? products.join(", ") : "—"}
            </li>
          )}
        </ul>
      </div>

      <div>
        {/* Ingen förbrukningssiffra. Se docstringen: vi mäter den inte per
            arbetsyta ännu, och kunden är den enda som kan falsifiera en
            påhittad — på fakturan. */}
        <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink/65">
          Fakturan går till{" "}
          {workspaceName ? <strong className="font-semibold">{workspaceName}</strong> : "er arbetsyta"}.
          Vill ni byta paket, lägga till en produkt eller se er förbrukning, skriv till{" "}
          <a
            href={mejlaOss("Plan och fakturering")}
            className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
          >
            {KONTAKT_MEJL}
          </a>{" "}
          så svarar vi samma dag.
        </p>
      </div>
    </div>
  );
}
