import type { Kundstatistik as Statistik } from "@/lib/admin/statistik";

/**
 * Statistiksektionen i Kunder & Data: avtalstakt och kundtillväxt.
 *
 * Server-renderad med flit — talen är räknade ur kundlistan som sidan redan
 * hämtat, och en graf över ett dussin veckor behöver ingen klientkod. Hovern
 * är SVG:ns egna <title>-element: rätt nivå för en intern vy med ensiffriga
 * tal som dessutom står direktetiketterade ovanför staplarna.
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

export function Kundstatistik({ stat }: Readonly<{ stat: Statistik }>) {
  const max = Math.max(3, ...stat.veckor.map((v) => Math.max(v.nyaKunder, v.avtal)));
  const grupbredd = STAPEL.bredd * 2 + STAPEL.gap + STAPEL.grupp;
  const bredd = MARG.vanster + stat.veckor.length * grupbredd;
  const skala = (varde: number) => (varde / max) * (HOJD - MARG.topp);

  const taktText = `${stat.takt.senaste.kunder} nya kunder och ${stat.takt.senaste.avtal} signerade avtal de senaste fyra veckorna, mot ${stat.takt.foregaende.kunder} respektive ${stat.takt.foregaende.avtal} de fyra veckorna före.`;

  return (
    <section className="mt-10 border-t border-ink/15 pt-4">
      <h2 className="kicker text-mineral">Statistik</h2>
      <p className="mt-1.5 max-w-[70ch] text-[0.875rem] leading-6 text-mineral">
        Signerade avtal och nya kunder över tid. Försäljningstakten nedan är
        definierad som nya kunder och signerade avtal per vecka — säg till om den
        ska mäta något annat.
      </p>

      <div className="mt-4 grid gap-px overflow-hidden rounded-input border border-ink/15 bg-ink/15 sm:grid-cols-2 lg:grid-cols-4">
        <Nyckeltal etikett="Avtal i dag" varde={stat.avtal.idag} />
        <Nyckeltal etikett="Avtal denna vecka" varde={stat.avtal.veckan} />
        <Nyckeltal etikett="Avtal denna månad" varde={stat.avtal.manaden} />
        <Nyckeltal etikett="Avtal i år" varde={stat.avtal.aret} rad={`${stat.avtal.totalt} totalt`} />
      </div>

      <p className="mt-3 max-w-[70ch] text-[0.875rem] leading-6 text-ink/70">
        {taktText}{" "}
        <span className="text-mineral">
          {stat.nyaKunder.totalt} kunder och {stat.avtal.totalt} registrerade avtal totalt.
        </span>
      </p>

      {/* Grafen: grupperade staplar per vecka, 12 veckor. Direktetiketter på
          allt som inte är noll — talen är ensiffriga och etiketten är
          snabbare än en axel. Rutnätet är avsiktligt glest och hårfint. */}
      <figure className="mt-6">
        <figcaption className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[0.8125rem] text-ink/70">
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-ink" />
            Nya kunder
          </span>
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-ochre" />
            Signerade avtal
          </span>
          <span className="text-mineral">per vecka, senaste 12 veckorna</span>
        </figcaption>

        <div className="mt-3 overflow-x-auto">
          <svg
            viewBox={`0 0 ${bredd} ${HOJD + MARG.botten}`}
            width={bredd}
            height={HOJD + MARG.botten}
            role="img"
            aria-label={`Nya kunder och signerade avtal per vecka. ${taktText}`}
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
                <g key={`${vecka.etikett}-${i}`}>
                  <title>{`${vecka.etikett}: ${vecka.nyaKunder} nya kunder, ${vecka.avtal} signerade avtal`}</title>
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
                    {vecka.etikett}
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
            Visa som tabell
          </summary>
          <table className="mt-2 border-collapse tabular-nums">
            <thead>
              <tr className="border-b border-ink/15 text-left">
                <th className="py-1.5 pr-6 font-medium text-mineral">Vecka</th>
                <th className="py-1.5 pr-6 text-right font-medium text-mineral">Nya kunder</th>
                <th className="py-1.5 text-right font-medium text-mineral">Signerade avtal</th>
              </tr>
            </thead>
            <tbody>
              {stat.veckor.map((vecka, i) => (
                <tr key={`tab-${vecka.etikett}-${i}`} className="border-b border-ink/8">
                  <td className="py-1.5 pr-6">{vecka.etikett}</td>
                  <td className="py-1.5 pr-6 text-right">{vecka.nyaKunder}</td>
                  <td className="py-1.5 text-right">{vecka.avtal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </figure>

      {stat.bortfiltrerade > 0 ? (
        <p className="mt-4 max-w-[70ch] text-[0.8125rem] leading-6 text-mineral">
          {stat.bortfiltrerade === 1
            ? "En demo- eller testarbetsyta ingår inte i talen ovan. Den räknas inte som kund, men den göms inte heller."
            : `${stat.bortfiltrerade} demo- och testarbetsytor ingår inte i talen ovan. De räknas inte som kunder, men de göms inte heller.`}
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
