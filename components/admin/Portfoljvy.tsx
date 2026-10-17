"use client";

import Link from "next/link";
import { Radgivare } from "@/components/admin/Radgivare";
import { Radmarke } from "@/components/admin/Radmarke";
import {
  Andelsring,
  KpiKort,
  Munkdiagram,
  Panelrubrik,
  Rangstaplar,
  type Andel,
  type Kpi,
  type Rang
} from "@/components/dashboard/OversiktPaneler";
import { Badge, Cell, Sidhuvud, Tabell, Tomt, meta, radLank, tabellRad, panelKort } from "@/components/ui";
import type { BerikadTenant } from "@/lib/admin/exempeldata";
import { ADMIN, a, antal, datum } from "@/lib/admin/sprak";
import { arTestyta } from "@/lib/admin/statistik";
import { useLocale, type Locale } from "@/lib/i18n";
import { formateraPris } from "@/lib/pricing";
import { cn } from "@/lib/utils";
import { type Halsa, TOKENKOSTNAD_MODELL, bedomKund, sammanfattaPortfolj } from "@/lib/admin/halsa";

/**
 * Adminöversikten: hela portföljen på en skärm.
 *
 * ## Ordningen är vad admin ska göra, inte vad som är störst
 *
 * Kunderna som kräver en åtgärd (låg marginal eller tysta) står först, i en
 * egen tabell. Ekonomin kommer sedan, övriga kunder efter den. Före
 * 2026-09-27 stod nyckeltalen överst och talet "Kräver åtgärd" i en ruta,
 * medan raderna det räknade låg längre ned i samma tabell som alla andra.
 * Nu ÄR sektionen listan, och rutan med talet finns inte längre: två ställen
 * som säger samma sak är två ställen som kan säga olika saker.
 *
 * Status är en `Badge` längst till höger. Symbolkolumnen med emoji som stod
 * här förut behövde en fotnot för att gå att läsa; ett ord gör det inte.
 *
 * ## Varför den är en klientkomponent
 *
 * Språkväxlaren i AdminShell är klientstate, och den här vyn är den textrikaste
 * i adminytan. Som server-komponent bytte allt runtomkring språk medan tabellen
 * stod kvar på svenska — en halvöversatt sida läser som en trasig sida. Datan
 * hämtas fortfarande på servern (`app/admin/page.tsx`) och skickas ned som
 * props; det är BARA renderingen som flyttat.
 *
 * ## Tre saker som INTE är mätvärden, och var det står
 *
 * Fotnoterna under tabellen togs bort 2026-09-27 (F-016: finstilt text om
 * sidan). Det de bar och som behövs står nu där talet står:
 *
 * 1. **Paketet kommer ur `workspaces.products`** när admin-API:t kan läsa
 *    det (sedan 2026-09-13). Saknas det härleds det ur aktivitet: ärenden =
 *    Support, körningar = Leads. Härledningen blir fel för en kund som betalar
 *    utan att använda och ger aldrig Trio, så paketcellen säger "härlett" på
 *    just de raderna.
 *
 * 2. **Tokenkostnaden är en uppskattning**, inte en faktura. Etiketten säger
 *    "Uppskattad" och notisen namnger modellen och att det är listpriset, så
 *    påståendet går att kontrollera. Priset och varför miljön inte faktureras
 *    står vid `TOKENKOSTNAD_PER_MILJON_SEK` i lib/admin/halsa.ts.
 *
 * 3. **Exempelrader är märkta.** Rader vars tal kommer ur
 *    `lib/admin/exempeldata.ts` bär märket Exempel, och en mening under
 *    nyckeltalen säger hur många av dem talen räknar med. Se den filen för
 *    varför de finns.
 */

/** Lagrade produkter om de finns, annars härledda ur aktivitet. En tom lista
 *  räknas som lagrad — en arbetsyta utan produkter ska inte få ett paket
 *  påhittat ur sina körningar. */
function harLagradeProdukter(rad: BerikadTenant): boolean {
  return Array.isArray(rad.products);
}

function harledProdukter(rad: BerikadTenant): string[] {
  if (Array.isArray(rad.products)) return rad.products;
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

/** Badge-ton per hälsoläge. Röd bara på det som kostar pengar nu. */
const HALSOTON: Record<Halsa, "neutral" | "good" | "warn" | "danger"> = {
  bra: "good",
  ok: "warn",
  dalig: "danger",
  tyst: "warn",
  okand: "neutral",
  test: "neutral"
};

/** Munkens färger per hälsoläge: grönt bra, ochre och rött det som kräver något. */
const HALSOFARG: Record<Halsa, string> = {
  bra: "oklch(var(--moss))",
  ok: "oklch(var(--chart-ochre))",
  dalig: "oklch(var(--danger))",
  tyst: "oklch(var(--chart-ramp-3))",
  okand: "oklch(var(--ink-subtle))",
  test: "oklch(var(--chart-ramp-1))"
};

const PAKETFARG = ["oklch(var(--chart-ramp-6))", "oklch(var(--chart-ramp-4))", "oklch(var(--chart-ramp-2))", "oklch(var(--moss))", "oklch(var(--chart-ochre))"];

/** Etiketten för ett hälsoläge. `test` står inline: sprak.ts ägs av en annan
 *  yta, och ett enda ord motiverar inte en nyckel där. */
function halsoetikett(halsa: Halsa, locale: Locale): string {
  if (halsa === "test") return locale === "sv" ? "Testarbetsyta" : "Test workspace";
  return a(HALSOETIKETT[halsa], locale);
}

/** Samma villkor som `sammanfattaPortfolj` räknar som "Kräver åtgärd". */
function kraverAtgard(halsa: Halsa): boolean {
  return halsa === "dalig" || halsa === "tyst";
}

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
      testkorningar: rad.test_runs ?? 0,
      arenden: rad.tickets ?? 0,
      senasteAktivitet: rad.last_activity,
      arTestyta: arTestyta(rad.slug),
      // Serverns klocka, inte besökarens — se `dagarSedan` i halsa.ts.
      nu
    })
  }));

  // Sämst först. Adminvyn finns för att hitta problem, inte för att bekräfta
  // att det mesta är bra — en lista sorterad på namn hade begravt den enda rad
  // som krävde en åtgärd.
  // Testarbetsytorna sist: de är inte kunder och ska inte konkurrera med de
  // rader som kräver en åtgärd.
  const ordning = { dalig: 0, tyst: 1, ok: 2, okand: 3, bra: 4, test: 5 } as const;
  // `x`/`y` och inte `a`/`b`: `a()` är språkuppslagningen i den här filen, och
  // en sorteringsparameter som skuggar den läser som ett anrop till fel sak.
  rader.sort(
    (x, y) =>
      ordning[x.ekonomi.halsa] - ordning[y.ekonomi.halsa] || y.ekonomi.intakt - x.ekonomi.intakt
  );

  const p = sammanfattaPortfolj(rader.map((r) => r.ekonomi));
  const kraver = rader.filter(({ ekonomi }) => kraverAtgard(ekonomi.halsa));
  const exempelrader = rader.filter(({ rad }) => rad.ar_exempel).length;

  // Samma tabell i två sektioner. En funktion i komponenten och inte en egen
  // komponent: den behöver `locale` och `text` och har ingen annan läsare.
  const kundtabell = (lista: typeof rader) => (
    <Tabell
      minBredd={960}
      kolumner={[
        { rubrik: a("kolKund", locale), bredd: "24%" },
        { rubrik: a("kolPaket", locale), bredd: "13%" },
        { rubrik: a("kolArenden", locale), bredd: "8%", hoger: true },
        { rubrik: a("kolKorningar", locale), bredd: "9%", hoger: true },
        { rubrik: a("kolTokens", locale), bredd: "10%", hoger: true },
        { rubrik: a("kolKostnad", locale), bredd: "9%", hoger: true },
        { rubrik: a("kolMarginal", locale), bredd: "8%", hoger: true },
        { rubrik: a("kolFel", locale), bredd: "6%", hoger: true },
        { rubrik: text({ sv: "Status", en: "Status" }), bredd: "13%", hoger: true }
      ]}
    >
      {lista.map(({ rad, ekonomi }) => (
        <tr key={rad.id} className={tabellRad}>
          <Cell titel>
            <span className="flex min-w-0 items-baseline gap-2">
              {/* Namnet leder till kundprofilen — agentinstruktioner och
                  tillägg. Förut var raden en återvändsgränd, och vägen
                  till tilläggen gick bara via en ikonknapp på en ANNAN
                  flik. */}
              <Link
                href={`/admin/kunder/${rad.id}`}
                className="focus-ring truncate rounded-input font-semibold underline decoration-ink/25 underline-offset-4 hover:text-ochre"
              >
                {rad.name}
              </Link>
              {/* Testarbetsytan får inget eget märke här: statusen säger
                  redan "Testarbetsyta" längst till höger på samma rad. */}
              {rad.active === false ? (
                <Radmarke>{text({ sv: "Inaktiv", en: "Inactive" })}</Radmarke>
              ) : null}
              {rad.ar_exempel ? (
                <Radmarke title={a("exempeldataMarkning", locale)}>{a("exempel", locale)}</Radmarke>
              ) : null}
            </span>
            <span className={cn(meta, "mt-1 line-clamp-2")}>{text(ekonomi.motivering)}</span>
          </Cell>
          <Cell className="text-ink-muted">
            {ekonomi.paketNamn ?? "–"}
            {ekonomi.paketNamn && !harLagradeProdukter(rad) ? (
              <span
                className="text-ink-subtle"
                title={text({
                  sv: "Härlett ur aktivitet, eftersom arbetsytans produkter inte gick att läsa.",
                  en: "Inferred from activity, because the workspace's products could not be read."
                })}
              >
                {text({ sv: ", härlett", en: ", inferred" })}
              </span>
            ) : null}
            {ekonomi.intakt > 0 ? (
              <span className={cn(meta, "num block")}>
                {formateraPris(ekonomi.intakt)}
                {a("perManad", locale)}
              </span>
            ) : null}
          </Cell>
          <Cell hoger className="text-ink-muted">
            {antal(rad.tickets, locale)}
          </Cell>
          <Cell hoger className="text-ink-muted">
            {antal(rad.runs, locale)}
            {/* Testkörningar göms inte, de räknas bara inte som kundvolym.
                En siffra som tyst blivit mindre är svårare att lita på än
                en siffra som säger vad den utelämnat. */}
            {rad.test_runs ? (
              <span className={cn(meta, "block")}>
                +{rad.test_runs} {a("test", locale)}
              </span>
            ) : null}
          </Cell>
          <Cell hoger className="text-ink-muted">
            {antal((rad.tokens_in ?? 0) + (rad.tokens_out ?? 0), locale)}
          </Cell>
          <Cell hoger className="text-ink-muted">
            {formateraPris(Math.round(ekonomi.kostnad))}
          </Cell>
          <Cell hoger className="text-ink-muted">
            {ekonomi.marginal === null ? "–" : `${Math.round(ekonomi.marginal * 100)} %`}
          </Cell>
          {/* Varningsfärg bara på avvikelsen. */}
          <Cell hoger className={rad.errors > 0 ? "text-warning" : "text-ink-subtle"}>
            {rad.errors}
          </Cell>
          <Cell hoger>
            <Badge tone={HALSOTON[ekonomi.halsa]}>{halsoetikett(ekonomi.halsa, locale)}</Badge>
          </Cell>
        </tr>
      ))}
    </Tabell>
  );

  // Diagramraden: hälsan, intäkten per paket och marginalen. Samma rader och
  // samma ekonomi som tabellen, så att diagrammen inte kan säga emot den.
  const halsodelar: Andel[] = (Object.keys(HALSOFARG) as Halsa[]).map((h) => ({
    id: h,
    etikett: { sv: halsoetikett(h, "sv"), en: halsoetikett(h, "en") },
    antal: p.fordelning[h],
    farg: HALSOFARG[h]
  }));
  const perPaket = new Map<string, number>();
  for (const { ekonomi } of rader) {
    if (ekonomi.intakt > 0 && ekonomi.paketNamn) {
      perPaket.set(ekonomi.paketNamn, (perPaket.get(ekonomi.paketNamn) ?? 0) + ekonomi.intakt);
    }
  }
  const paketdelar: Andel[] = [...perPaket.entries()]
    .sort((x, y) => y[1] - x[1])
    .map(([namn, summa], i) => ({ id: namn, etikett: { sv: namn, en: namn }, antal: summa, farg: PAKETFARG[i % PAKETFARG.length] }));

  // Topplistorna räknar bara kunder: testarbetsytan konkurrerar inte om
  // platserna med dem som betalar.
  const kunder = rader.filter(({ ekonomi }) => ekonomi.halsa !== "test");
  const kostsamma: Rang[] = kunder.map(({ rad, ekonomi }) => ({
    id: rad.id,
    namn: rad.name,
    varde: ekonomi.kostnad,
    visning: formateraPris(Math.round(ekonomi.kostnad)),
    under:
      ekonomi.marginal === null
        ? text({ sv: "ingen intäkt att räkna marginal på", en: "no revenue to measure margin against" })
        : text({ sv: `marginal ${Math.round(ekonomi.marginal * 100)} %`, en: `margin ${Math.round(ekonomi.marginal * 100)} %` }),
    href: `/admin/kunder/${rad.id}`
  }));
  const aktivast: Rang[] = kunder.map(({ rad }) => ({
    id: rad.id,
    namn: rad.name,
    varde: (rad.runs ?? 0) + (rad.tickets ?? 0),
    visning: antal((rad.runs ?? 0) + (rad.tickets ?? 0), locale),
    under: text({
      sv: `${antal(rad.runs ?? 0, "sv")} körningar · ${antal(rad.tickets ?? 0, "sv")} ärenden · senast ${datum(rad.last_activity, "sv")}`,
      en: `${antal(rad.runs ?? 0, "en")} runs · ${antal(rad.tickets ?? 0, "en")} cases · last ${datum(rad.last_activity, "en")}`
    }),
    href: `/admin/kunder/${rad.id}`
  }));

  const kpier: Kpi[] = [
    {
      id: "mrr",
      etikett: ADMIN.manadsintakt,
      varde: null,
      visning: formateraPris(p.mrr),
      detalj: {
        sv: `${p.antalBetalande} av ${p.antalKunder} kunder betalar`,
        en: `${p.antalBetalande} of ${p.antalKunder} customers pay`
      }
    },
    {
      // Modellen och "listpris" i detaljen: "en uppskattning" utan att säga av
      // vad är ett förbehåll man inte kan kontrollera.
      id: "kostnad",
      etikett: { sv: "Uppskattad tokenkostnad", en: "Estimated token cost" },
      varde: null,
      visning: formateraPris(Math.round(p.kostnad)),
      detalj: { sv: `Listpris, ${TOKENKOSTNAD_MODELL}`, en: `List price, ${TOKENKOSTNAD_MODELL}` }
    },
    {
      id: "marginal",
      etikett: { sv: "Marginal efter tokenkostnad", en: "Margin after token cost" },
      varde: null,
      visning: p.marginal === null ? "–" : `${Math.round(p.marginal * 100)} %`,
      detalj: p.marginal === null ? ADMIN.ingenIntakt : { sv: "av månadsintäkten blir kvar", en: "of the monthly revenue remains" }
    },
    {
      id: "kraver",
      etikett: ADMIN.kraverAtgard,
      varde: kraver.length,
      larm: kraver.length > 0,
      href: "#kraver-atgard",
      detalj: { sv: `av ${p.antalKunder} kunder`, en: `of ${p.antalKunder} customers` }
    }
  ];

  return (
    <div>
      {/* "Översikt" och inte "Kunder": fliken heter Översikt, och NÄSTA flik
          heter Kunder och leder till en annan sida. Två flikar vars sidor båda
          rubricerades "Kunder" läste som samma vy renderad två gånger. */}
      <Sidhuvud title={a("oversiktRubrik", locale)} />

      {/* Översikternas layout (Sebbe 2026-10-07): nyckeltalen som kort, en
          diagramrad, kunderna som kräver en åtgärd i ett eget kort och två
          kolumner för var kostnaden och aktiviteten finns. Nyckeltalen står
          först (Antons beställning 2026-10-03: "viktiga mätvärden gömda
          längre ned"). */}
      <div className="mt-6 flex min-w-0 flex-col gap-6">
        {rader.length === 0 ? (
          <Tomt>{a("ingaRegistrerade", locale)}</Tomt>
        ) : (
          <>
            <div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {kpier.map((k) => (
                  <KpiKort key={k.id} kpi={k} perioden={{ sv: "", en: "" }} />
                ))}
              </div>
              {/* Exempelraderna räknas med i talen ovan, och det ska synas
                  innan någon läser månadsintäkten som ett utfall. */}
              {exempelrader > 0 ? (
                <p className="mt-3 max-w-[70ch] text-[0.8125rem] text-ink-subtle">
                  {exempelrader === 1
                    ? text({
                        sv: "Nyckeltalen räknar med exempeldata från en kund.",
                        en: "The key figures include example data from one customer."
                      })
                    : text({
                        sv: `Nyckeltalen räknar med exempeldata från ${exempelrader} kunder.`,
                        en: `The key figures include example data from ${exempelrader} customers.`
                      })}
                </p>
              ) : null}
            </div>

            <div className="grid min-w-0 gap-4 lg:grid-cols-3">
              <section aria-labelledby="oversikt-halsa" className={cn(panelKort, "min-w-0")}>
                <Panelrubrik id="oversikt-halsa" titel={{ sv: "Kundernas hälsa", en: "Customer health" }} />
                <Munkdiagram
                  delar={halsodelar}
                  etikett={{ sv: "Status per kund", en: "Status per customer" }}
                  mitt={{ sv: "kunder", en: "customers" }}
                />
              </section>
              <section aria-labelledby="oversikt-paket" className={cn(panelKort, "min-w-0")}>
                <Panelrubrik id="oversikt-paket" titel={{ sv: "Intäkt per paket", en: "Revenue per plan" }} />
                <Munkdiagram
                  delar={paketdelar}
                  etikett={{ sv: "Kronor per månad", en: "SEK per month" }}
                  mitt={{ sv: "tkr/mån", en: "kSEK/mo" }}
                  mittVarde={antal(Math.round(p.mrr / 1000), locale)}
                />
              </section>
              <section aria-labelledby="oversikt-marginal" className={cn(panelKort, "min-w-0")}>
                <Panelrubrik id="oversikt-marginal" titel={{ sv: "Marginal efter tokenkostnad", en: "Margin after token cost" }} />
                <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
                  <Andelsring
                    andel={p.marginal}
                    etikett={text({ sv: "Marginal efter tokenkostnad", en: "Margin after token cost" })}
                  />
                  <dl className="min-w-[11rem] flex-1 space-y-2 text-[0.8125rem]">
                    <div className="flex items-baseline justify-between gap-3">
                      <dt className="text-ink-muted">{a("manadsintakt", locale)}</dt>
                      <dd className="num font-medium tabular-nums text-ink">{formateraPris(p.mrr)}</dd>
                    </div>
                    <div className="flex items-baseline justify-between gap-3">
                      <dt className="text-ink-muted">{text({ sv: "Uppskattad tokenkostnad", en: "Estimated token cost" })}</dt>
                      <dd className="num font-medium tabular-nums text-ink">− {formateraPris(Math.round(p.kostnad))}</dd>
                    </div>
                    <div className="flex items-baseline justify-between gap-3 border-t border-ink/10 pt-2">
                      <dt className="font-medium text-ink">{text({ sv: "Kvar efter kostnad", en: "Left after cost" })}</dt>
                      <dd className="num font-semibold tabular-nums text-ink">{formateraPris(Math.round(p.mrr - p.kostnad))}</dd>
                    </div>
                  </dl>
                </div>
                <p className={cn(meta, "mt-4")}>
                  {text({
                    sv: `Listpris, ${TOKENKOSTNAD_MODELL}. En uppskattning, inte en faktura.`,
                    en: `List price, ${TOKENKOSTNAD_MODELL}. An estimate, not an invoice.`
                  })}
                </p>
              </section>
            </div>

            {/* Bara kunder med en anledning. Hela kundtabellen bor i Kunder;
                "Övriga kunder" här var samma tabell en gång till. */}
            <section
              id="kraver-atgard"
              aria-labelledby="oversikt-kraver"
              className={cn(
                panelKort,
                "min-w-0 scroll-mt-24",
                kraver.length > 0 && "shadow-[inset_0_2px_0_0_oklch(var(--ochre))]"
              )}
            >
              <Panelrubrik
                id="oversikt-kraver"
                titel={ADMIN.kraverAtgard}
                antal={kraver.length}
                under={{
                  sv: "Låg marginal eller ingen aktivitet, sämst först. Namnet leder till kundens profil.",
                  en: "Low margin or no activity, worst first. The name leads to the customer's profile."
                }}
                action={
                  <Link href="/admin/kunder" className={radLank}>
                    {text({ sv: "Alla kunder", en: "All customers" })}
                  </Link>
                }
              />
              {kraver.length > 0 ? (
                kundtabell(kraver)
              ) : (
                <Tomt>{text({ sv: "Ingen kund kräver åtgärd.", en: "No customer needs attention." })}</Tomt>
              )}
            </section>

            <div className="grid min-w-0 gap-4 xl:grid-cols-2">
              <section aria-labelledby="oversikt-kostnad" className={cn(panelKort, "min-w-0")}>
                <Panelrubrik
                  id="oversikt-kostnad"
                  titel={{ sv: "Störst tokenkostnad", en: "Highest token cost" }}
                  under={{ sv: "Uppskattad kostnad per kund, med marginalen under.", en: "Estimated cost per customer, with the margin below." }}
                />
                <Rangstaplar
                  rader={kostsamma.sort((x, y) => y.varde - x.varde).slice(0, 6)}
                  tom={{ sv: "Ingen kund har någon tokenkostnad än.", en: "No customer has any token cost yet." }}
                  farg="oklch(var(--chart-ochre))"
                />
              </section>
              <section aria-labelledby="oversikt-aktivitet" className={cn(panelKort, "min-w-0")}>
                <Panelrubrik
                  id="oversikt-aktivitet"
                  titel={{ sv: "Mest aktivitet", en: "Most activity" }}
                  under={{
                    sv: "Körningar och ärenden per kund. Testkörningar räknas inte.",
                    en: "Runs and cases per customer. Test runs are not counted."
                  }}
                />
                <Rangstaplar
                  rader={aktivast.sort((x, y) => y.varde - x.varde).slice(0, 6)}
                  tom={{ sv: "Ingen kund har någon aktivitet än.", en: "No customer has any activity yet." }}
                />
              </section>
            </div>
          </>
        )}

        {/* Rådgivaren får SAMMA rader som tabellen räknat fram, inte en egen
            hämtning. Två uträkningar av samma tal är två tillfällen att räkna
            olika, och här skulle skillnaden synas som att sidan säger emot sig
            själv. */}
        <Radgivare rader={rader.map(({ rad, ekonomi }) => ({ namn: rad.name, ekonomi }))} />
      </div>
    </div>
  );
}
