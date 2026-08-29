"use client";

import { a } from "@/lib/admin/sprak";
import type { Kundstatistik as Statistik } from "@/lib/admin/statistik";
import { useLocale } from "@/lib/i18n";

/**
 * Statistiksektionen i Kunder & Data: avtalstakt och kundtillväxt.
 *
 * Talen är räknade ur kundlistan som sidan redan hämtat — ingen egen hämtning.
 * Klientkomponent enbart för språkväxlarens skull; grafen har fortfarande ingen
 * interaktiv logik. Hovern är SVG:ns egna <title>-element: rätt nivå för en
 * intern vy med ensiffriga tal som dessutom står direktetiketterade ovanför
 * staplarna.
 *
 * ## Färgerna
 *
 * Två serier: kunder i ink, avtal i ochre — accentfärgen på det sektionen
 * finns för att visa. Identiteten bärs av legenden och direktetiketterna,
 * inte av färgen ensam, och ljushetsavståndet mellan ink (L 0.20) och ochre
 * (L 0.74) gör paret läsbart även utan färgseende.
 */

const STAPEL = { bredd: 14, gap: 2, grupp: 18 };
const HOJD = 150;
const MARG = { topp: 18, botten: 24, vanster: 8 };

/** "v.35" på svenska, "w.35" på engelska. */
function veckoetikett(vecka: number, locale: "sv" | "en"): string {
  return locale === "sv" ? `v.${vecka}` : `w.${vecka}`;
}

export function Kundstatistik({ stat }: Readonly<{ stat: Statistik }>) {
  const { locale, text } = useLocale();
  const max = Math.max(3, ...stat.veckor.map((v) => Math.max(v.nyaKunder, v.avtal)));
  const grupbredd = STAPEL.bredd * 2 + STAPEL.gap + STAPEL.grupp;
  const bredd = MARG.vanster + stat.veckor.length * grupbredd;
  const skala = (varde: number) => (varde / max) * (HOJD - MARG.topp);

  const taktText = text({
    sv: `${stat.takt.senaste.kunder} nya kunder och ${stat.takt.senaste.avtal} signerade avtal de senaste fyra veckorna, mot ${stat.takt.foregaende.kunder} respektive ${stat.takt.foregaende.avtal} de fyra veckorna före.`,
    en: `${stat.takt.senaste.kunder} new customers and ${stat.takt.senaste.avtal} signed contracts in the last four weeks, against ${stat.takt.foregaende.kunder} and ${stat.takt.foregaende.avtal} in the four weeks before.`
  });

  return (
    <section className="mt-10 border-t border-ink/15 pt-4">
      <h2 className="kicker text-mineral">{a("statistik", locale)}</h2>
      <p className="mt-1.5 max-w-[70ch] text-[0.875rem] leading-6 text-mineral">
        {a("statistikIngress", locale)}
      </p>

      <div className="mt-4 grid gap-px overflow-hidden rounded-input border border-ink/15 bg-ink/15 sm:grid-cols-2 lg:grid-cols-4">
        <Nyckeltal etikett={a("avtalIdag", locale)} varde={stat.avtal.idag} />
        <Nyckeltal etikett={a("avtalVeckan", locale)} varde={stat.avtal.veckan} />
        <Nyckeltal etikett={a("avtalManaden", locale)} varde={stat.avtal.manaden} />
        <Nyckeltal
          etikett={a("avtalAret", locale)}
          varde={stat.avtal.aret}
          rad={text({ sv: `${stat.avtal.totalt} totalt`, en: `${stat.avtal.totalt} in total` })}
        />
      </div>

      <p className="mt-3 max-w-[70ch] text-[0.875rem] leading-6 text-ink/70">
        {taktText}{" "}
        <span className="text-mineral">
          {text({
            sv: `${stat.nyaKunder.totalt} kunder och ${stat.avtal.totalt} registrerade avtal totalt.`,
            en: `${stat.nyaKunder.totalt} customers and ${stat.avtal.totalt} registered contracts in total.`
          })}
        </span>
      </p>

      {/* Grafen: grupperade staplar per vecka, 12 veckor. Direktetiketter på
          allt som inte är noll — talen är ensiffriga och etiketten är
          snabbare än en axel. Rutnätet är avsiktligt glest och hårfint. */}
      <figure className="mt-6">
        <figcaption className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[0.8125rem] text-ink/70">
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-ink" />
            {a("nyaKunder", locale)}
          </span>
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-ochre" />
            {a("signeradeAvtal", locale)}
          </span>
          <span className="text-mineral">{a("perVecka12", locale)}</span>
        </figcaption>

        <div className="mt-3 overflow-x-auto">
          <svg
            viewBox={`0 0 ${bredd} ${HOJD + MARG.botten}`}
            width={bredd}
            height={HOJD + MARG.botten}
            role="img"
            aria-label={`${a("nyaKunder", locale)} ${text({ sv: "och", en: "and" })} ${a("signeradeAvtal", locale)} ${a("perVecka12", locale)}. ${taktText}`}
            className="max-w-full"
          >
            {/* Baslinje + ett mellansteg. Fler linjer än talen förtjänar är
                bara brus. */}
            <line x1="0" y1={HOJD} x2={bredd} y2={HOJD} className="stroke-ink/25" strokeWidth="1" />
            <line
              x1="0"
              y1={HOJD - skala(max / 2)}
              x2={bredd}
              y2={HOJD - skala(max / 2)}
              className="stroke-ink/10"
              strokeWidth="1"
            />

            {stat.veckor.map((vecka, i) => {
              const x = MARG.vanster + i * grupbredd + STAPEL.grupp / 2;
              return (
                <g key={`${vecka.vecka}-${i}`}>
                  <title>
                    {text({
                      sv: `${veckoetikett(vecka.vecka, "sv")}: ${vecka.nyaKunder} nya kunder, ${vecka.avtal} signerade avtal`,
                      en: `${veckoetikett(vecka.vecka, "en")}: ${vecka.nyaKunder} new customers, ${vecka.avtal} signed contracts`
                    })}
                  </title>
                  <Stapel x={x} varde={vecka.nyaKunder} skala={skala} klass="fill-ink" />
                  <Stapel
                    x={x + STAPEL.bredd + STAPEL.gap}
                    varde={vecka.avtal}
                    skala={skala}
                    klass="fill-ochre"
                  />
                  <text
                    x={x + STAPEL.bredd + STAPEL.gap / 2}
                    y={HOJD + 16}
                    textAnchor="middle"
                    className="fill-mineral text-[11px]"
                  >
                    {veckoetikett(vecka.vecka, locale)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Tabellversionen av samma tal — för skärmläsare, och för den som
            hellre läser siffror än staplar. */}
        <details className="mt-2 text-[0.8125rem] text-ink/70">
          <summary className="focus-ring inline-flex min-h-11 cursor-pointer items-center rounded-input text-mineral hover:text-ink">
            {a("visaSomTabell", locale)}
          </summary>
          <table className="mt-2 border-collapse tabular-nums">
            <thead>
              <tr className="border-b border-ink/15 text-left">
                <th className="py-1.5 pr-6 font-medium text-mineral">{a("vecka", locale)}</th>
                <th className="py-1.5 pr-6 text-right font-medium text-mineral">
                  {a("nyaKunder", locale)}
                </th>
                <th className="py-1.5 text-right font-medium text-mineral">
                  {a("signeradeAvtal", locale)}
                </th>
              </tr>
            </thead>
            <tbody>
              {stat.veckor.map((vecka, i) => (
                <tr key={`tab-${vecka.vecka}-${i}`} className="border-b border-ink/8">
                  <td className="py-1.5 pr-6">{veckoetikett(vecka.vecka, locale)}</td>
                  <td className="py-1.5 pr-6 text-right">{vecka.nyaKunder}</td>
                  <td className="py-1.5 text-right">{vecka.avtal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </figure>

      {/* Exempelfotnoten står FÖRE bortfiltrerings-fotnoten: läsaren ska veta
          att kurvan innehåller påhittade tal innan hen läser vad som utelämnats.
          Utan den här raden ser 12 avtal ut som 12 sålda avtal. */}
      {stat.exempel > 0 ? (
        <p className="mt-4 max-w-[70ch] text-[0.8125rem] leading-6 text-mineral">
          {text({
            sv: `${stat.exempel} av raderna i talen och kurvan ovan är exempeldata — arbetsytor utan egen aktivitet, märkta med Exempel i tabellen. Nya kunder räknas ur deras verkliga registreringsdatum; avtalsdatumen är påhittade. Stäng av dem med NEXT_PUBLIC_ADMIN_EXEMPELDATA=av.`,
            en: `${stat.exempel} of the rows behind the figures and the chart above are example data — workspaces with no activity of their own, tagged Example in the table. New customers are counted from their real registration dates; the contract dates are fabricated. Turn them off with NEXT_PUBLIC_ADMIN_EXEMPELDATA=av.`
          })}
        </p>
      ) : null}

      {stat.bortfiltrerade > 0 ? (
        <p className="mt-4 max-w-[70ch] text-[0.8125rem] leading-6 text-mineral">
          {stat.bortfiltrerade === 1
            ? text({
                sv: "En demo- eller testarbetsyta ingår inte i talen ovan. Den räknas inte som kund, men den göms inte heller.",
                en: "One demo or test workspace is excluded from the figures above. It does not count as a customer, but it is not hidden either."
              })
            : text({
                sv: `${stat.bortfiltrerade} demo- och testarbetsytor ingår inte i talen ovan. De räknas inte som kunder, men de göms inte heller.`,
                en: `${stat.bortfiltrerade} demo and test workspaces are excluded from the figures above. They do not count as customers, but they are not hidden either.`
              })}
        </p>
      ) : null}
    </section>
  );
}

function Stapel({
  x,
  varde,
  skala,
  klass
}: Readonly<{ x: number; varde: number; skala: (v: number) => number; klass: string }>) {
  const hojd = skala(varde);
  return (
    <>
      {/* Rundad topp, rak fot: dataänden är mjuk, baslinjen är förankrad.
          Path i stället för rect+rx, som hade rundat även foten. */}
      {varde > 0 ? (
        <path
          d={`M ${x} ${HOJD}
              L ${x} ${HOJD - hojd + 4}
              Q ${x} ${HOJD - hojd} ${x + 4} ${HOJD - hojd}
              L ${x + STAPEL.bredd - 4} ${HOJD - hojd}
              Q ${x + STAPEL.bredd} ${HOJD - hojd} ${x + STAPEL.bredd} ${HOJD - hojd + 4}
              L ${x + STAPEL.bredd} ${HOJD} Z`}
          className={klass}
        />
      ) : null}
      {varde > 0 ? (
        <text
          x={x + STAPEL.bredd / 2}
          y={HOJD - hojd - 5}
          textAnchor="middle"
          className="fill-ink/70 text-[11px] tabular-nums"
        >
          {varde}
        </text>
      ) : null}
    </>
  );
}

function Nyckeltal({
  etikett,
  varde,
  rad
}: Readonly<{ etikett: string; varde: number; rad?: string }>) {
  return (
    <div className="bg-paper px-4 py-3">
      <p className="kicker text-mineral">{etikett}</p>
      <p className="mt-1 font-display text-[1.375rem] tabular-nums tracking-[-0.02em]">{varde}</p>
      {rad ? <p className="mt-0.5 text-[0.8125rem] leading-[1.45] text-ink/60">{rad}</p> : null}
    </div>
  );
}
