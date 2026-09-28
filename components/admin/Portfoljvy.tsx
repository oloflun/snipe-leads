"use client";

import Link from "next/link";
import { Radgivare } from "@/components/admin/Radgivare";
import { Radmarke } from "@/components/admin/Radmarke";
import { Badge, Cell, Nyckeltal, Sektion, Sidhuvud, Tabell, Tomt, meta, tabellRad } from "@/components/ui";
import type { BerikadTenant } from "@/lib/admin/exempeldata";
import { a, antal } from "@/lib/admin/sprak";
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
  const ovriga = rader.filter(({ ekonomi }) => !kraverAtgard(ekonomi.halsa));
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

  return (
    <div>
      {/* "Översikt" och inte "Kunder": fliken heter Översikt, och NÄSTA flik
          heter Kunder och leder till en annan sida. Två flikar vars sidor båda
          rubricerades "Kunder" läste som samma vy renderad två gånger. */}
      <Sidhuvud title={a("oversiktRubrik", locale)} />

      <div className="mt-8">
        {rader.length === 0 ? (
          <Tomt>{a("ingaRegistrerade", locale)}</Tomt>
        ) : (
          <>
            <Sektion title={a("kraverAtgard", locale)}>
              {kraver.length > 0 ? (
                kundtabell(kraver)
              ) : (
                <Tomt>{text({ sv: "Ingen kund kräver åtgärd.", en: "No customer needs attention." })}</Tomt>
              )}
            </Sektion>

            <Sektion title={text({ sv: "Ekonomi", en: "Finances" })}>
              <Nyckeltal
                poster={[
                  {
                    etikett: a("manadsintakt", locale),
                    varde: formateraPris(p.mrr),
                    notis: text({
                      sv: `${p.antalBetalande} av ${p.antalKunder} kunder betalar`,
                      en: `${p.antalBetalande} of ${p.antalKunder} customers pay`
                    })
                  },
                  {
                    // Modellen och "listpris" i notisen: "en uppskattning" utan
                    // att säga av vad är ett förbehåll man inte kan kontrollera.
                    etikett: text({ sv: "Uppskattad tokenkostnad", en: "Estimated token cost" }),
                    varde: formateraPris(Math.round(p.kostnad)),
                    notis: text({
                      sv: `Listpris, ${TOKENKOSTNAD_MODELL}`,
                      en: `List price, ${TOKENKOSTNAD_MODELL}`
                    })
                  },
                  {
                    etikett: text({ sv: "Marginal efter tokenkostnad", en: "Margin after token cost" }),
                    varde: p.marginal === null ? "–" : `${Math.round(p.marginal * 100)} %`,
                    notis: p.marginal === null ? a("ingenIntakt", locale) : undefined
                  }
                ]}
              />
              {/* Exempelraderna räknas med i talen ovan, och det ska synas
                  innan någon läser månadsintäkten som ett utfall. */}
              {exempelrader > 0 ? (
                <p className="mt-4 max-w-[70ch] text-[0.9375rem] text-ink-muted">
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
            </Sektion>

            {ovriga.length > 0 ? (
              <Sektion title={text({ sv: "Övriga kunder", en: "Other customers" })}>
                {kundtabell(ovriga)}
              </Sektion>
            ) : null}
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
