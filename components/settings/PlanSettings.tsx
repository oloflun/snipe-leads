"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Betalsatt } from "@/components/settings/Betalsatt";
import { Kortbetalning } from "@/components/settings/Kortbetalning";
import { Planvaljare } from "@/components/settings/Planvaljare";
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
        {/* Två kolumner: vad ni HAR till vänster, vad ni kan byta till höger.
            Väljaren låg först under texten, och då hamnade den under "Det här
            ingår" — alltså efter en lista som beskriver det paket man just
            funderar på att lämna. Sida vid sida läses de mot varandra, vilket
            är precis vad ett paketbyte är.

            Staplat under md: två kolumner à sex på en telefon ger ett prisfält
            på halva bredden, och det är samma fälla som gap-x-8 vid 320px
            (se WorkspaceViews). */}
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
                  : "Manuellt satt plan. Ett paketval ersätter den."}
              </p>
            )}
          </div>

          <div className="col-span-12 md:col-span-6">
            <Planvaljare aktivtPaket={paketId} />
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

      {/* Stripe-växeln (lib/billing/stripe.ts). Renderar ingenting förrän
          STRIPE_SECRET_KEY är satt i miljön — då står Betalsatt ensamt. */}
      <Kortbetalning paketId={paketId} />

      <div className="border-t border-ink/15 pt-7">
        <Betalsatt />
      </div>

      <div>
        {/* Ingen förbrukningssiffra. Se docstringen: vi mäter den inte per
            arbetsyta ännu, och kunden är den enda som kan falsifiera en
            påhittad — på fakturan. */}
        <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
          Fakturan går till{" "}
          {workspaceName ? <strong className="font-semibold">{workspaceName}</strong> : "er arbetsyta"}.
          Faktureringen justeras vid nästa period. Frågor:{" "}
          <a
            href={mejlaOss("Plan och fakturering")}
            className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
          >
            {KONTAKT_MEJL}
          </a>
        </p>
      </div>
    </div>
  );
}
