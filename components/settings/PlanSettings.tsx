"use client";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Betalsatt } from "@/components/settings/Betalsatt";
import { Planvaljare } from "@/components/settings/Planvaljare";
import { KONTAKT_MEJL, mejlaOss } from "@/components/marketing/copy";
import { Rad, Radlista, Sektion, btnSecondary, rubrikPanel } from "@/components/ui";
import { PAKET } from "@/lib/pricing";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** Radformen, samma som i resten av inställningarna. Under sm staplas den. */
const radform = "grid gap-x-6 gap-y-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center";

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
    <div>
      {/* Ett paket, visat EN gång. Här stod tidigare det aktiva paketets namn,
          pris och beskrivning i en vänsterspalt, och samma tre saker igen i
          väljaren bredvid, där det aktiva paketet redan är markerat. Nu är
          väljaren ensam, och texten ovanför finns bara när inget paket matchar. */}
      <Sektion title="Paket">
        {paket ? null : (
          <p className="mb-4 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
            {products.length === 0
              ? "Arbetsytan har ingen aktiv produkt. Välj ett paket nedan."
              : "Er plan är satt manuellt och matchar inget standardpaket. Väljer ni ett paket nedan ersätts den."}
          </p>
        )}
        <Planvaljare aktivtPaket={paketId} />
      </Sektion>

      <Sektion title={paket ? `Det här ingår i ${paket.namn}` : "Det här ingår"}>
        <ul className="flex flex-col gap-2.5 border-y border-ink/15 py-5">
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
              {products.length ? products.join(", ") : "–"}
            </li>
          )}
        </ul>
      </Sektion>

      <Betalsatt />

      {/* Ingen förbrukningssiffra. Se docstringen: vi mäter den inte per
          arbetsyta ännu, och kunden är den enda som kan falsifiera en
          påhittad, på fakturan. Stycket som stod här är nu två rader i samma
          radform som resten av inställningarna; meningen om när ett paketbyte
          gäller står vid väljaren. */}
      <Sektion title="Fakturering">
        <Radlista ariaLabel="Fakturering">
          <Rad className={radform}>
            <span className={rubrikPanel}>Fakturamottagare</span>
            <span className="text-[0.9375rem] sm:text-right">{workspaceName ?? "–"}</span>
          </Rad>
          <Rad className={radform}>
            <span className="min-w-0">
              <span className={cn(rubrikPanel, "block")}>Förbrukning och villkor</span>
              <span id="fakturering-hjalp" className="mt-1 block text-[0.9375rem] leading-6 text-ink-muted">
                Vi svarar samma dag.
              </span>
            </span>
            <a
              href={mejlaOss("Plan och fakturering")}
              aria-describedby="fakturering-hjalp"
              className={cn(btnSecondary, "justify-self-start sm:justify-self-end")}
            >
              Skriv till {KONTAKT_MEJL}
            </a>
          </Rad>
        </Radlista>
      </Sektion>
    </div>
  );
}
