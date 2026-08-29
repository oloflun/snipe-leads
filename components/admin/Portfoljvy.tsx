"use client";

import Link from "next/link";
import { Radgivare } from "@/components/admin/Radgivare";
import type { BerikadTenant } from "@/lib/admin/exempeldata";
import { a, antal } from "@/lib/admin/sprak";
import { useLocale } from "@/lib/i18n";
import { formateraPris } from "@/lib/pricing";
import {
  MARGINAL_GRON,
  MARGINAL_ROD,
  TOKENKOSTNAD_IN_PER_MILJON_SEK,
  TOKENKOSTNAD_MODELL,
  TOKENKOSTNAD_UT_PER_MILJON_SEK,
  TYST_EFTER_DAGAR,
  bedomKund,
  sammanfattaPortfolj
} from "@/lib/admin/halsa";

/**
 * Adminöversikten: hela portföljen på en skärm.
 *
 * Ledger, inte kort — en rad per kund, hairline mellan, tabularsiffror så
 * kolumnerna går att jämföra vertikalt. Symbolen längst till vänster är det
 * enda som får färg; hade varje kolumn haft en accent hade ingen av dem varit
 * en.
 *
 * ## Varför den är en klientkomponent
 *
 * Språkväxlaren i AdminShell är klientstate, och den här vyn är den textrikaste
 * i adminytan. Som server-komponent bytte allt runtomkring språk medan tabellen
 * stod kvar på svenska — en halvöversatt sida läser som en trasig sida. Datan
 * hämtas fortfarande på servern (`app/admin/page.tsx`) och skickas ned som
 * props; det är BARA renderingen som flyttat.
 *
 * ## Två saker som INTE är mätvärden, och som därför står utskrivna
 *
 * 1. **Paketet härleds ur aktivitet.** `listTenants()` returnerar inte vilka
 *    produkter arbetsytan äger, så en kund med ärenden räknas som Support och
 *    en med körningar som Leads. Det stämmer för en kund som använder det den
 *    betalar för och blir fel för en som betalar utan att använda — vilket är
 *    precis den kund raden ska varna för. Kopplas `workspaces.products` in i
 *    admin-API:t ska härledningen bort.
 *
 * 2. **Tokenkostnaden är en uppskattning**, inte en faktura. Se
 *    `TOKENKOSTNAD_PER_MILJON_SEK`. Fotnoten under tabellen säger det till
 *    läsaren, eftersom en marginal som presenteras utan förbehåll blir ett
 *    beslutsunderlag den inte är.
 *
 * 3. **Exempelrader är märkta.** Rader vars tal kommer ur
 *    `lib/admin/exempeldata.ts` bär en synlig etikett och räknas i fotnoten.
 *    Se den filen för varför de finns.
 */

function harledProdukter(rad: BerikadTenant): string[] {
  const produkter: string[] = [];
  // Provkörningar räknas MED här, till skillnad från i volymkolumnen. Frågan
  // är vilken produkt tenanten använder, och en testkörning är leads-agenten
  // som kört — annars tappade demokontot sin leads-halva i samma sekund som
  // is_test började fyllas i.
  if (rad.runs + (rad.test_runs ?? 0) > 0) produkter.push("leads");
  if (rad.tickets > 0) produkter.push("support");
  return produkter;
}

const HALSOETIKETT = {
  bra: "halsaBra",
  ok: "halsaOk",
  dalig: "halsaDalig",
  tyst: "halsaTyst",
  okand: "halsaOkand"
} as const;

export function Portfoljvy({
  tenants,
  nu
}: Readonly<{ tenants: BerikadTenant[]; nu: number }>) {
  const { locale, text } = useLocale();

  const rader = tenants.map((rad) => ({
    rad,
    ekonomi: bedomKund({
      produkter: harledProdukter(rad),
      tokensIn: rad.tokens_in ?? 0,
      tokensUt: rad.tokens_out ?? 0,
      korningar: rad.runs ?? 0,
      arenden: rad.tickets ?? 0,
      senasteAktivitet: rad.last_activity,
      // Serverns klocka, inte besökarens — se `dagarSedan` i halsa.ts.
      nu
    })
  }));

  // Sämst först. Adminvyn finns för att hitta problem, inte för att bekräfta
  // att det mesta är bra — en lista sorterad på namn hade begravt den enda rad
  // som krävde en åtgärd.
  const ordning = { dalig: 0, tyst: 1, ok: 2, okand: 3, bra: 4 } as const;
  // `x`/`y` och inte `a`/`b`: `a()` är språkuppslagningen i den här filen, och
  // en sorteringsparameter som skuggar den läser som ett anrop till fel sak.
  rader.sort(
    (x, y) =>
      ordning[x.ekonomi.halsa] - ordning[y.ekonomi.halsa] || y.ekonomi.intakt - x.ekonomi.intakt
  );

  const p = sammanfattaPortfolj(rader.map((r) => r.ekonomi));

  // Decimaltecknet foljer spraket: 7,14 kr pa svenska, 7.14 kr pa engelska.
  // Rakt interpolerade JS-tal ger alltid punkt, och en svensk driftvy som
  // skriver "7.14 kr" ser ut att ha rott ihop tusental med decimaler.
  const kr = (v: number) => v.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  const exempelrader = rader.filter(({ rad }) => rad.ar_exempel).length;

  return (
    <div>
      {/* "Översikt" och inte "Kunder": fliken heter Översikt, och NÄSTA flik
          heter Kunder och leder till en annan sida. Två flikar vars sidor båda
          rubricerades "Kunder" läste som samma vy renderad två gånger. */}
      <h1 className="font-display text-4xl tracking-[-0.03em]">{a("oversiktRubrik", locale)}</h1>

      <div className="mt-8 grid gap-px overflow-hidden rounded-input border border-ink/15 bg-ink/15 sm:grid-cols-2 lg:grid-cols-4">
        <Nyckeltal
          etikett={a("manadsintakt", locale)}
          varde={formateraPris(p.mrr)}
          rad={text({
            sv: `${p.antalBetalande} av ${p.antalKunder} kunder betalar`,
            en: `${p.antalBetalande} of ${p.antalKunder} customers pay`
          })}
        />
        <Nyckeltal
          etikett={a("uppskattadKostnad", locale)}
          varde={formateraPris(Math.round(p.kostnad))}
          rad={a("tokensAllaKunder", locale)}
        />
        <Nyckeltal
          etikett={a("marginal", locale)}
          varde={p.marginal === null ? "—" : `${Math.round(p.marginal * 100)} %`}
          rad={
            p.marginal === null ? a("ingenIntakt", locale) : a("intaktMinusToken", locale)
          }
        />
        <Nyckeltal
          etikett={a("kraverAtgard", locale)}
          varde={String(p.fordelning.dalig + p.fordelning.tyst)}
          rad={text({
            sv: `${p.fordelning.dalig} med låg marginal, ${p.fordelning.tyst} tysta`,
            en: `${p.fordelning.dalig} on thin margin, ${p.fordelning.tyst} dormant`
          })}
        />
      </div>

      <div className="mt-10 overflow-x-auto">
        <div className="min-w-[900px]">
          <div className="grid grid-cols-12 gap-x-4 border-b border-ink/15 pb-3">
            {[
              ["", "col-span-1"],
              [a("kolKund", locale), "col-span-3"],
              [a("kolPaket", locale), "col-span-2"],
              [a("kolArenden", locale), "col-span-1 text-right"],
              [a("kolKorningar", locale), "col-span-1 text-right"],
              [a("kolTokens", locale), "col-span-1 text-right"],
              [a("kolKostnad", locale), "col-span-1 text-right"],
              [a("kolMarginal", locale), "col-span-1 text-right"],
              [a("kolFel", locale), "col-span-1 text-right"]
            ].map(([rubrik, kl]) => (
              <div key={String(rubrik) || "symbol"} className={`kicker text-mineral ${kl}`}>
                {rubrik}
              </div>
            ))}
          </div>

          <div className="divide-y divide-ink/15">
            {rader.map(({ rad, ekonomi }) => (
              <div key={rad.id} className="grid grid-cols-12 items-baseline gap-x-4 py-4">
                <div
                  className="col-span-1 text-[1.25rem]"
                  title={a(HALSOETIKETT[ekonomi.halsa], locale)}
                >
                  <span aria-hidden="true">{ekonomi.symbol}</span>
                  <span className="sr-only">{a(HALSOETIKETT[ekonomi.halsa], locale)}</span>
                </div>
                <div className="col-span-3 min-w-0">
                  <p className="flex min-w-0 items-baseline gap-2 text-[1rem] font-semibold">
                    <span className="truncate">{rad.name}</span>
                    {rad.ar_exempel ? <Exempelmarke /> : null}
                  </p>
                  <p className="mt-0.5 truncate text-[0.8125rem] text-ink/60">
                    {text(ekonomi.motivering)}
                  </p>
                </div>
                <div className="col-span-2 text-[0.875rem] text-ink/70">
                  {ekonomi.paketNamn ?? "—"}
                  {ekonomi.intakt > 0 ? (
                    <span className="block text-[0.8125rem] text-mineral">
                      {formateraPris(ekonomi.intakt)}
                      {a("perManad", locale)}
                    </span>
                  ) : null}
                </div>
                <Tal>{antal(rad.tickets, locale)}</Tal>
                <Tal>
                  {antal(rad.runs, locale)}
                  {/* Testkörningar göms inte, de räknas bara inte som kundvolym.
                      En siffra som tyst blivit mindre är svårare att lita på än
                      en siffra som säger vad den utelämnat. */}
                  {rad.test_runs ? (
                    <span className="block text-[0.8125rem] text-ink/40">
                      +{rad.test_runs} {a("test", locale)}
                    </span>
                  ) : null}
                </Tal>
                <Tal>{antal((rad.tokens_in ?? 0) + (rad.tokens_out ?? 0), locale)}</Tal>
                <Tal>{formateraPris(Math.round(ekonomi.kostnad))}</Tal>
                <Tal>
                  {ekonomi.marginal === null ? "—" : `${Math.round(ekonomi.marginal * 100)} %`}
                </Tal>
                {/* Ochre bara på avvikelsen. */}
                <div
                  className={`col-span-1 text-right tabular-nums text-[0.9375rem] ${
                    rad.errors > 0 ? "text-ochre" : "text-ink/45"
                  }`}
                >
                  {rad.errors}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {rader.length === 0 ? (
        <p className="mt-8 text-[15px] text-ink/60">{a("ingaKunder", locale)}</p>
      ) : null}

      <div className="mt-10 max-w-[80ch] space-y-2 border-t border-ink/15 pt-5 text-[0.8125rem] leading-[1.6] text-mineral">
        {/* Exempelfotnoten står FÖRST av fotnoterna när den finns. Läsaren ska
            veta att en del av tabellen är påhittad innan hen läser hur
            marginalen räknas, inte efter. */}
        {exempelrader > 0 ? (
          <p>
            <strong className="text-ink/70">
              {text({
                sv: `${exempelrader} av ${rader.length} rader visar exempeldata`,
                en: `${exempelrader} of ${rader.length} rows show example data`
              })}
            </strong>{" "}
            {text({
              sv: "och är märkta med Exempel. De arbetsytorna har ingen egen aktivitet — talen finns för att vyn ska gå att bedöma, och de räknas med i nyckeltalen ovan. Stäng av dem med NEXT_PUBLIC_ADMIN_EXEMPELDATA=av.",
              en: "and carry an Example tag. Those workspaces have no activity of their own — the figures exist so the view can be evaluated, and they are included in the key figures above. Turn them off with NEXT_PUBLIC_ADMIN_EXEMPELDATA=av."
            })}
          </p>
        ) : null}
{/* Fotnoten namnger MODELLEN och nivån. "En uppskattning" utan att säga
            av vad är ett förbehåll man inte kan kontrollera; med modellnamnet
            och gratisnivån utskriven går påståendet att falsifiera på en
            minut. */}
        <p>
          <strong className="text-ink/70">
            {text({
              sv: "Kostnaden är leverantörens listpris",
              en: "The cost is the provider's list price"
            })}
          </strong>
          {text({
            sv: `, inte en faktura: ${kr(TOKENKOSTNAD_IN_PER_MILJON_SEK)} kr per miljon ingående och ${kr(TOKENKOSTNAD_UT_PER_MILJON_SEK)} kr per miljon utgående tokens för ${TOKENKOSTNAD_MODELL}. Någon faktura finns inte — miljön kör på Geminis gratisnivå, så det verkliga utfallet i kronor är noll tills faktureringen slås på. Talen visar vad det kostar då. Priset dubblas 2027-01-01; ändra i `,
            en: `, not an invoice: ${kr(TOKENKOSTNAD_IN_PER_MILJON_SEK)} kr per million input and ${kr(TOKENKOSTNAD_UT_PER_MILJON_SEK)} kr per million output tokens for ${TOKENKOSTNAD_MODELL}. There is no invoice — this environment runs on Gemini's free tier, so the real outcome in kronor is zero until billing is switched on. These figures show what it costs then. The price doubles on 2027-01-01; change it in `
          })}
          <code>lib/admin/halsa.ts</code>.
        </p>
        <p>
          {text({
            sv: `Grönt över ${Math.round(MARGINAL_GRON * 100)} % marginal, gult över ${Math.round(MARGINAL_ROD * 100)} %. En kund utan aktivitet på ${TYST_EFTER_DAGAR} dagar visas som tyst`,
            en: `Green above ${Math.round(MARGINAL_GRON * 100)} % margin, amber above ${Math.round(MARGINAL_ROD * 100)} %. A customer with no activity for ${TYST_EFTER_DAGAR} days shows as dormant`
          })}{" "}
          <span aria-hidden="true">😴</span>{" "}
          {text({
            sv: "oavsett marginal — den som inte använder tjänsten har låg kostnad och ser lönsam ut precis innan den säger upp sig.",
            en: "regardless of margin — a customer who has stopped using the service has low costs and looks profitable right up until they cancel."
          })}
        </p>
        <p>
          {text({
            sv: "Paketet härleds ur aktivitet, eftersom admin-API:t ännu inte returnerar ",
            en: "The plan is inferred from activity, because the admin API does not yet return "
          })}
          <code>workspaces.products</code>
          {text({
            sv: ". En kund som betalar utan att använda får därför fel paket i tabellen — och är samtidigt precis den kund raden ska varna för.",
            en: ". A customer who pays without using therefore gets the wrong plan in the table — and is exactly the customer the row exists to flag."
          })}
        </p>
      </div>

      {/* Rådgivaren får SAMMA rader som tabellen räknat fram, inte en egen
          hämtning. Två uträkningar av samma tal är två tillfällen att räkna
          olika, och här skulle skillnaden synas som att sidan säger emot sig
          själv. */}
      <Radgivare rader={rader.map(({ rad, ekonomi }) => ({ namn: rad.name, ekonomi }))} />

      <p className="mt-8">
        <Link
          href="/admin/korningar"
          className="focus-ring text-[15px] text-ochre underline underline-offset-4"
        >
          {a("seAllaKorningar", locale)}
        </Link>
      </p>
    </div>
  );
}

/**
 * Märket som skiljer en påhittad rad från en mätt.
 *
 * Hairline och mineral, inte ochre: accenten i den här vyn är reserverad för
 * avvikelser man ska agera på, och en exempelrad är inte en avvikelse — den är
 * ett förbehåll. Syns tydligt, ropar inte.
 */
function Exempelmarke() {
  const { locale } = useLocale();
  return (
    <span
      title={a("exempeldataMarkning", locale)}
      className="shrink-0 rounded-[3px] border border-ink/20 px-1.5 py-px font-mono text-[10px] uppercase tracking-[0.14em] text-mineral"
    >
      {a("exempel", locale)}
    </span>
  );
}

function Nyckeltal({
  etikett,
  varde,
  rad
}: Readonly<{ etikett: string; varde: string; rad: string }>) {
  return (
    <div className="bg-paper px-5 py-4">
      <p className="kicker text-mineral">{etikett}</p>
      <p className="mt-1.5 font-display text-[1.75rem] tabular-nums tracking-[-0.02em]">{varde}</p>
      <p className="mt-1 text-[0.8125rem] leading-[1.45] text-ink/60">{rad}</p>
    </div>
  );
}

function Tal({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="col-span-1 text-right tabular-nums text-[0.9375rem] text-ink/75">
      {children}
    </div>
  );
}
