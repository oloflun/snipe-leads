"use client";

/* Snajp · genre: nordic-editorial · design-system: DESIGN.md · designed-as-app */
/* design · pre-emit critique: P4 H4 E4 S5 R5 V4 */

import Link from "next/link";
import { KNAPP_PRIMAR, KNAPP_SEKUNDAR, SidAvslut } from "@/components/marketing/InnehallsSida";
import { PRODUKTYTOR } from "@/components/marketing/ProduktBilder";
import { mejlaOss, shared } from "@/components/marketing/copy";
import { useLocale, type Localized } from "@/lib/i18n";
import { landningsPost, smulspar } from "@/lib/landningar";
import type { Landning } from "@/lib/landningssidor";
import { versal } from "@/lib/seo";
import { BINDNING, PAKET, PER_MANAD, PRIS_PREFIX, PRIS_SAKNAS, UPPSTARTSAVGIFT, formateraPris, type Paket } from "@/lib/pricing";

/**
 * Mallen för sökordssidorna (lib/landningar.ts). Skalet runt den, sidhuvud,
 * meny och sidfot, lägger LandningsRutt på servern.
 *
 * ## Vilken yta den ärver
 *
 * Innehållssidornas skal, samma som /faq och /vart-team. Sidorna är en del av
 * den ytan och startar ingen egen identitet (design-skillens arvsregel). Det
 * som skiljer dem från FAQ:n är att de ska bära en hel fråga på egen hand,
 * eftersom besökaren kommer direkt från ett sökresultat och aldrig har sett
 * startsidan.
 *
 * ## Ordningen
 *
 * Rubrik, sedan det korta svaret: den som sökte på "vad är en AI-SDR" ska ha
 * svaret innan första skrollen. Därefter hur det går till, hur det ser ut,
 * vad agenten INTE gör (sidans enda bläckplatta), jämförelsen, priset,
 * frågorna och vägarna vidare. Frågorna är synliga i sin helhet, inte ett
 * dragspel: de står också i sidans FAQPage-schema, och schemat får bara
 * beskriva text som besökaren kan läsa.
 */

const COPY = {
  brodsmulor: { sv: "Brödsmulor", en: "Breadcrumb" },
  pris: { sv: "Pris", en: "Price" },
  ingar: { sv: "Ingår", en: "Included" },
  allaPaket: { sv: "Alla paket och priser", en: "All packages and prices" },
  fragor: { sv: "Frågor och svar", en: "Questions and answers" },
  lasVidare: { sv: "Läs vidare", en: "Read on" },
  // Egen rad och inte EXEMPELRAD ur ProduktBilder: den säger "ytorna ovan",
  // och här står ytan bredvid texten på en bred skärm.
  exempel: {
    sv: "Ytan är produktens egen, återgiven med exempeldata.",
    en: "The surface is the product's own, shown with example data."
  }
} satisfies Record<string, Localized>;

const BOKA_DEMO = { etikett: shared.menyBokaDemo, href: "/boka-demo" };

/**
 * Rubrikradens knappar per paket: demon för sidans produkt först, en bokning
 * därefter. Duo har ingen gemensam demo, så där är bokningen den primära.
 */
const KNAPPAR: Record<Paket["id"], [{ etikett: Localized; href: string }, { etikett: Localized; href: string }]> = {
  leads: [{ etikett: { sv: "Prova Iris", en: "Try Iris" }, href: "/demo/leads" }, BOKA_DEMO],
  support: [{ etikett: { sv: "Prova supportagenten", en: "Try the support agent" }, href: "/demo/support" }, BOKA_DEMO],
  duo: [BOKA_DEMO, { etikett: shared.secondaryCta, href: mejlaOss() }]
};

const AVSLUT: Record<Paket["id"], { rubrik: Localized; text: Localized }> = {
  leads: {
    rubrik: { sv: "Se Iris arbeta med era egna kunder.", en: "See Iris work with your own customers." },
    text: {
      sv: "Boka en demo på 15 till 20 minuter. Vi kör Iris mot er målgrupp och säger rakt ut om vi tror att det passar er.",
      en: "Book a 15 to 20 minute demo. We run Iris against your target market and tell you plainly whether we think it fits."
    }
  },
  support: {
    rubrik: { sv: "Se agenten svara på era egna ärenden.", en: "See the agent answer your own cases." },
    text: {
      sv: "Boka en demo på 15 till 20 minuter. Vi kör agenten mot era vanligaste frågor och säger rakt ut om vi tror att det passar er.",
      en: "Book a 15 to 20 minute demo. We run the agent against your most common questions and tell you plainly whether we think it fits."
    }
  },
  duo: {
    rubrik: { sv: "Se agenterna arbeta med er verksamhet.", en: "See the agents work with your business." },
    text: {
      sv: "Boka en demo på 15 till 20 minuter. Vi visar båda agenterna mot era egna kunder och ärenden, och säger rakt ut vad som passar er.",
      en: "Book a 15 to 20 minute demo. We show both agents against your own customers and cases, and tell you plainly what fits."
    }
  }
};

/** `*ord*` i en rubrik blir det markerade ordet i textsäker ockra. */
function Markerad({ text: varde }: Readonly<{ text: string }>) {
  return (
    <>
      {varde.split(/\*([^*]+)\*/g).map((del, i) =>
        i % 2 === 1 ? (
          <span key={i} className="italic-disp text-warning">
            {del}
          </span>
        ) : (
          <span key={i}>{del}</span>
        )
      )}
    </>
  );
}

const H2 = "font-display text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.08] tracking-[-0.025em]";
/** En ledgerrad med rubriken i en smal vänsterspalt: det korta svaret, priset. */
const LEDGERRAD = "mt-24 grid grid-cols-12 border-t border-ink/15 pt-8 lg:gap-x-12";
const H_RAD = "col-span-12 font-display text-[1.375rem] font-semibold leading-snug tracking-[-0.015em] lg:col-span-4";

/**
 * Jämförelsetabellens brytpunkt. Tre kolumner ryms som tabell från md; en
 * leverantörsjämförelse med fem värden per rad blir för trång där och staplas
 * till lg. Två fullständiga klassuppsättningar, eftersom Tailwind bara hittar
 * klasser som står utskrivna i källan.
 */
const TABELL_SMAL = {
  table: "md:table",
  thead: "sr-only md:not-sr-only md:table-header-group",
  huvudrad: "md:border-b md:border-ink/15",
  tbody: "block md:table-row-group",
  rad: "md:table-row md:py-0",
  etikett: "md:table-cell md:w-[28%] md:py-5 md:align-top",
  cell: "text-[1rem] md:table-cell md:py-5 md:align-top",
  cellEtikett: "md:hidden"
} as const;
const TABELL_BRED = {
  table: "lg:table",
  thead: "sr-only lg:not-sr-only lg:table-header-group",
  huvudrad: "lg:border-b lg:border-ink/15",
  tbody: "block lg:table-row-group",
  rad: "lg:table-row lg:py-0",
  etikett: "lg:table-cell lg:w-[17%] lg:py-5 lg:align-top",
  cell: "text-[1rem] lg:table-cell lg:py-5 lg:align-top lg:text-[0.9375rem]",
  cellEtikett: "lg:hidden"
} as const;

export function Landningssida({ sida }: Readonly<{ sida: Landning }>) {
  const { text, locale } = useLocale();
  const post = landningsPost(sida.vag);
  const paket = PAKET.find((p) => p.id === post.produkt);
  const Yta = PRODUKTYTOR[sida.yta.typ];
  const avslut = AVSLUT[post.produkt];
  const [primar, sekundar] = KNAPPAR[post.produkt];
  const smulor = smulspar(sida.vag);
  const tabell = (sida.jamforelse?.kolumner.length ?? 0) > 4 ? TABELL_BRED : TABELL_SMAL;

  return (
    <>
      {/* BRÖDSMULAN: säger var sidan ligger för den som kom från en sökning.
          En fungerande väg upp, INTE en dekorativ etikett. Samma spår som
          BreadcrumbList i schemat (lib/landningar.ts, smulspar). */}
      <nav aria-label={text(COPY.brodsmulor)}>
        <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.875rem] text-ink-subtle">
          {smulor.map((smula, i) => (
            <li key={smula.vag} className="flex items-center gap-x-2">
              {i > 0 ? <span aria-hidden="true">/</span> : null}
              {i === smulor.length - 1 ? (
                <span aria-current="page" className="text-ink-muted">
                  {text(smula.namn)}
                </span>
              ) : (
                <Link href={smula.vag} className="focus-ring rounded-input hover:text-ink">
                  {text(smula.namn)}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>

      {/* RUBRIKEN: display-typ med ett markerat ord, INTE en hjältebild med kort. */}
      <h1 className="mt-10 max-w-[18ch] font-display text-[clamp(2.5rem,6.2vw,4.75rem)] font-semibold leading-[0.98] tracking-[-0.035em]">
        <Markerad text={text(sida.rubrik)} />
      </h1>
      <p className="mt-7 max-w-[58ch] text-[1.125rem] leading-[1.7] text-ink-muted">{text(sida.ingress)}</p>
      <div className="mt-9 flex flex-wrap gap-3">
        <Link href={primar.href} className={KNAPP_PRIMAR}>
          {text(primar.etikett)}
        </Link>
        <a href={sekundar.href} className={KNAPP_SEKUNDAR}>
          {text(sekundar.etikett)}
        </a>
      </div>

      {/* DET KORTA SVARET: definitionen på egna ben, så att en AI-översikt kan
          citera den. Hårlinje och delad rad, INTE en färgad faktaruta. */}
      <section className={`${LEDGERRAD} gap-y-5`}>
        <h2 className={H_RAD}>{text(sida.kortSvar.fraga)}</h2>
        <p className="col-span-12 font-display text-[clamp(1.25rem,2.2vw,1.625rem)] leading-[1.45] tracking-[-0.01em] text-ink lg:col-span-8">
          {text(sida.kortSvar.svar)}
        </p>
      </section>

      {/* STEGEN: numrerad ledger med ockra siffror, INTE en rad ikonkort. */}
      <section className="mt-24">
        <h2 className={H2}>{text(sida.stegRubrik)}</h2>
        <ol className="mt-10 border-t border-ink/15">
          {sida.steg.map((steg, i) => (
            <li
              key={steg.rubrik.sv}
              className="grid grid-cols-[3.5rem_minmax(0,1fr)] gap-x-5 gap-y-2 border-b border-ink/12 py-7 md:grid-cols-[4.5rem_minmax(0,0.75fr)_minmax(0,1.6fr)] md:gap-x-8"
            >
              <span aria-hidden="true" className="row-span-2 font-display text-[2.5rem] font-semibold leading-none text-warning [font-variant-numeric:tabular-nums] md:row-span-1">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="font-display text-[1.25rem] font-semibold leading-snug tracking-[-0.015em]">
                {text(steg.rubrik)}
              </h3>
              <p className="max-w-[60ch] text-[1rem] leading-[1.7] text-ink-muted">{text(steg.text)}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* PRODUKTYTAN: konstruerad med exempeldata i sidans egna tokens, INTE en
          skärmdump och ingen ritad webbläsarram. Bildtexten bredvid, i
          läsgrad, och raden som säger att datan är exempel. */}
      <figure className="mt-24 grid grid-cols-12 items-end gap-y-6 lg:gap-x-12">
        <div className="col-span-12 overflow-hidden rounded-panel border border-ink/12 bg-paper lg:col-span-7">
          <Yta locale={locale} />
        </div>
        <figcaption className="col-span-12 lg:col-span-5 lg:pb-2">
          <p className="font-display text-[1.375rem] font-semibold leading-snug tracking-[-0.015em]">
            {text(sida.yta.rubrik)}
          </p>
          <p className="mt-2 max-w-[44ch] text-[1rem] leading-[1.65] text-ink-muted">{text(sida.yta.text)}</p>
          <p className="mt-4 text-[0.8125rem] text-ink-subtle">{text(COPY.exempel)}</p>
        </figcaption>
      </figure>

      {/* GRÄNSERNA: sidans enda tonala inversion, INTE en varningsruta. */}
      <section className="mt-24 rounded-panel bg-ink px-7 py-12 text-paper md:px-12 md:py-16">
        <h2 className={`max-w-[22ch] ${H2}`}>{text(sida.granser.rubrik)}</h2>
        <ul className="mt-10 grid grid-cols-1 gap-x-12 md:grid-cols-2">
          {sida.granser.punkter.map((punkt) => (
            <li key={punkt.sv} className="flex items-start gap-4 border-t border-paper/15 py-5">
              <span aria-hidden="true" className="mt-[0.6em] h-1.5 w-1.5 shrink-0 rounded-full bg-ochre" />
              <span className="text-[1rem] leading-[1.6] text-paper-muted">{text(punkt)}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* JÄMFÖRELSEN: typsatt tabell med hårlinjer, INTE en bock-matris. Under
          md staplas raderna med kolumnnamnet framför varje värde: en tabell
          som skrollar i sidled på en telefon döljer halva jämförelsen. */}
      {sida.jamforelse ? (
        <section className="mt-24">
          <h2 className={H2}>{text(sida.jamforelse.rubrik)}</h2>
          <table className={`mt-10 block w-full border-t border-ink/15 text-left ${tabell.table}`}>
            <thead className={tabell.thead}>
              <tr className={tabell.huvudrad}>
                {sida.jamforelse.kolumner.map((kolumn, i) => (
                  <th
                    key={i}
                    scope="col"
                    className="py-4 pr-6 align-bottom text-[0.8125rem] font-medium text-ink-subtle"
                  >
                    {text(kolumn)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className={tabell.tbody}>
              {sida.jamforelse.rader.map(([etikett, ...varden]) => (
                <tr key={etikett.sv} className={`block border-b border-ink/12 py-5 ${tabell.rad}`}>
                  <th
                    scope="row"
                    className={`block pb-2 pr-6 font-display text-[1.125rem] font-semibold leading-snug ${tabell.etikett}`}
                  >
                    {text(etikett)}
                  </th>
                  {varden.map((varde, i) => (
                    <td key={i} className={`block py-1 pr-6 leading-[1.6] text-ink-muted ${tabell.cell}`}>
                      <span className={`block text-[0.8125rem] text-ink-subtle ${tabell.cellEtikett}`}>
                        {text(sida.jamforelse!.kolumner[i + 1])}
                      </span>
                      {text(varde)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {/* Källorna: varje uppgift om en annan leverantör ska gå att kontrollera
              (jämförande reklam, marknadsföringslagen). nofollow: länken är en
              källhänvisning, inte en rekommendation. */}
          {sida.jamforelse.kallor ? (
            <div className="mt-8 max-w-[68ch]">
              {sida.jamforelse.kontrollerad ? (
                <p className="text-[0.875rem] leading-[1.6] text-ink-subtle">{text(sida.jamforelse.kontrollerad)}</p>
              ) : null}
              <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[0.875rem]">
                {sida.jamforelse.kallor.map((kalla) => (
                  <li key={kalla.url}>
                    <a
                      href={kalla.url}
                      rel="nofollow noopener"
                      className="focus-ring rounded-input whitespace-nowrap text-ink-muted underline decoration-ink/25 underline-offset-4 hover:text-ink"
                    >
                      {kalla.namn}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {/* PRISET: en ledgerrad med beloppet i display-grad, INTE ett priskort.
          Allt ur lib/pricing.ts, ingen siffra i den här filen. */}
      {paket ? (
        <section className={`${LEDGERRAD} gap-y-6`}>
          <h2 className={H_RAD}>{text(COPY.pris)}</h2>
          <div className="col-span-12 lg:col-span-8">
            <p className="text-[0.9375rem] font-medium text-ink-muted">{paket.namn}</p>
            <p className="mt-2 flex flex-wrap items-baseline gap-x-2">
              {paket.prisPerManad === null ? (
                <span className="font-display text-[2.5rem] font-semibold leading-none tracking-[-0.03em]">
                  {text(PRIS_SAKNAS)}
                </span>
              ) : (
                <>
                  <span className="text-[1rem] text-mineral">{text(PRIS_PREFIX)}</span>
                  <span className="font-display text-[clamp(2.75rem,5vw,3.75rem)] font-semibold leading-none tracking-[-0.03em] [font-variant-numeric:tabular-nums]">
                    {formateraPris(paket.prisPerManad)}
                  </span>
                  <span className="text-[1rem] text-mineral">{text(PER_MANAD)}</span>
                </>
              )}
            </p>
            <p className="mt-6 text-[0.8125rem] font-medium text-ink-subtle">{text(COPY.ingar)}</p>
            <ul className="mt-2 flex flex-wrap gap-x-6 gap-y-2">
              {paket.ingar.map((rad) => (
                <li key={rad.sv} className="flex items-center gap-2 text-[0.9375rem] text-ink-muted">
                  <span aria-hidden="true" className="h-1 w-1 shrink-0 rounded-full bg-ochre" />
                  {text(rad)}
                </li>
              ))}
            </ul>
            <p className="mt-6 max-w-[58ch] text-[0.9375rem] leading-[1.6] text-ink-muted">
              {text({
                sv: `Uppstart ${PRIS_PREFIX.sv} ${formateraPris(UPPSTARTSAVGIFT)}, engångs.`,
                en: `Onboarding ${PRIS_PREFIX.en} ${formateraPris(UPPSTARTSAVGIFT)}, one-off.`
              })}{" "}
              {versal(text(BINDNING))}.
            </p>
            <Link
              href="/#priser"
              className="focus-ring mt-5 inline-block text-[0.9375rem] font-medium underline underline-offset-4 hover:text-warning"
            >
              {text(COPY.allaPaket)}
            </Link>
          </div>
        </section>
      ) : null}

      {/* FRÅGORNA: hela svaren synliga, samma text som FAQPage-schemat.
          INTE ett dragspel: schemat får bara beskriva det besökaren kan läsa. */}
      <section className="mt-24 grid grid-cols-12 gap-y-6 lg:gap-x-12">
        {/* Rubriken följer med i sin kolumn, så att den smala spalten bär
            något hela vägen ned och inte bara överst. */}
        <h2 className={`col-span-12 lg:sticky lg:top-24 lg:col-span-4 lg:self-start ${H2}`}>{text(COPY.fragor)}</h2>
        <dl className="col-span-12 lg:col-span-8">
          {sida.fragor.map((f) => (
            <div key={f.fraga.sv} className="border-t border-ink/15 py-6 first:border-t-0 first:pt-0 lg:first:border-t lg:first:pt-6">
              <dt className="font-display text-[1.1875rem] font-semibold leading-snug tracking-[-0.015em]">
                {text(f.fraga)}
              </dt>
              <dd className="mt-3 max-w-[62ch] text-[1rem] leading-[1.7] text-ink-muted">{text(f.svar)}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* LÄS VIDARE: klustrets interna länkar, en ledger, INTE en kortrad. */}
      <nav aria-labelledby="las-vidare" className="mt-24">
        <h2 id="las-vidare" className={H2}>
          {text(COPY.lasVidare)}
        </h2>
        <ul className="mt-8 border-t border-ink/15">
          {sida.relaterade.map((vag) => {
            const relaterad = landningsPost(vag);
            return (
              <li key={vag} className="border-b border-ink/12">
                <Link
                  href={vag}
                  className="focus-ring group grid gap-x-8 gap-y-1 py-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]"
                >
                  <span className="font-display text-[1.25rem] font-semibold leading-snug tracking-[-0.015em] transition-colors group-hover:text-warning">
                    {text(relaterad.namn)}
                  </span>
                  <span className="text-[1rem] leading-[1.6] text-ink-muted">{text(relaterad.kort)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <SidAvslut
        rubrik={text(avslut.rubrik)}
        text={text(avslut.text)}
        primar={{ etikett: text(BOKA_DEMO.etikett), href: BOKA_DEMO.href }}
        sekundar={{ etikett: text(shared.secondaryCta), href: mejlaOss() }}
      />
    </>
  );
}
