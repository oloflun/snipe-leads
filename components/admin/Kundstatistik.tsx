"use client";

import { Cell, Nyckeltal, Sektion, Tabell, meta } from "@/components/ui";
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
 *
 * ## Vad som togs bort 2026-09-27
 *
 * Ingressen under rubriken, meningen med totalerna (avtalen stod redan i
 * nyckeltalet "Avtal i år") och fotnoten om bortfiltrerade test- och
 * demoytor (F-016: finstilt text om sidan). Testytorna är märkta i tabellen
 * ovanför; att de inte räknas som kunder är regeln, inte ett undantag att
 * redovisa. Exempelraderna räknas däremot med, och det står kvar som en
 * mening, eftersom kurvan annars ser ut som verklig försäljning.
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
    <Sektion title={a("statistik", locale)}>
      <Nyckeltal
        poster={[
          { etikett: a("avtalIdag", locale), varde: stat.avtal.idag },
          { etikett: a("avtalVeckan", locale), varde: stat.avtal.veckan },
          { etikett: a("avtalManaden", locale), varde: stat.avtal.manaden },
          {
            etikett: a("avtalAret", locale),
            varde: stat.avtal.aret,
            notis: text({ sv: `${stat.avtal.totalt} totalt`, en: `${stat.avtal.totalt} in total` })
          }
        ]}
      />

      <p className="mt-4 max-w-[70ch] text-[0.9375rem] text-ink-muted">{taktText}</p>

      {/* Exempelraderna ingår i talen och i kurvan. Utan den här meningen
          ser 12 avtal ut som 12 sålda avtal. */}
      {stat.exempel > 0 ? (
        <p className="mt-2 max-w-[70ch] text-[0.9375rem] text-ink-muted">
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

      {/* Grafen: grupperade staplar per vecka, 12 veckor. Direktetiketter på
          allt som inte är noll — talen är ensiffriga och etiketten är
          snabbare än en axel. Rutnätet är avsiktligt glest och hårfint. */}
      <figure className="mt-6">
        <figcaption className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[0.8125rem] text-ink-muted">
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-ink" />
            {a("nyaKunder", locale)}
          </span>
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-ochre" />
            {a("signeradeAvtal", locale)}
          </span>
          <span className={meta}>{a("perVecka12", locale)}</span>
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
        <details className="mt-2 text-[0.8125rem] text-ink-muted">
          <summary className="focus-ring inline-flex min-h-11 cursor-pointer items-center rounded-input text-mineral hover:text-ink">
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
      </figure>
    </Sektion>
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
