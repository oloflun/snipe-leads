"use client";

import { useLocale } from "@/lib/i18n";
import { EXEMPELRAD } from "@/components/marketing/ProduktBilder";

/**
 * Översikten, isärtagen (Antons beställning 2026-10-18: "någon enstaka
 * dynamisk bild av dashboarden med uppdelning av elementen likt Isärtagning,
 * men utan lutning").
 *
 * En riktig skärmdump av produktens egen översikt (demo, exempeldata, inga
 * kunduppgifter: public/produkt/oversikt*.webp, kopierad ur
 * koncept/_delat/app) och fyra delar beskurna ur SAMMA bild: rälen,
 * nyckeltalen, pågår-raden och diagramytan. Rörelsen (useLandingMotion)
 * lyfter delarna rakt mot betraktaren med translateZ medan en förblurrad
 * tvilling av grundbilden tonas in (oskärpan är rastrerad en gång, inte per
 * bildruta), ritar en linje från var förklaring till sin del, och sätter ihop
 * allt igen. Ingen rotateX/rotateZ: det är en frontal sprängskiss.
 *
 * Texten står INNE i det pinnade blocket, till vänster om bilden, så att
 * förklaringen följer med under hela akten (Anton: "ingen tydlighet, det
 * känns inte intentionellt" när bilden stod ensam).
 *
 * Beskärningarna är andelar av bilden (2880 x 1920), uppmätta i
 * koncept/_delat/panel-offsets.json och koncept/10-isartaget.
 */

const DELAR = [
  { namn: "rail", cx: 0, cy: 0, cw: 0.180556, ch: 1 },
  { namn: "kpi", cx: 0.20208, cy: 0.09375, cw: 0.77639, ch: 0.16771 },
  { namn: "pagar", cx: 0.20208, cy: 0.28438, cw: 0.77639, ch: 0.15521 },
  { namn: "diagram", cx: 0.201389, cy: 0.534375, cw: 0.777778, ch: 0.465625 }
] as const;

const ALT = {
  sv: "Snajps översikt med exempeldata: körningar, levererade leads, ärenden till en människa och kostnad",
  en: "Snajp's overview with example data: runs, delivered leads, cases handed to a person, and cost"
};

/**
 * NY COPY 2026-10-18, skriven på Antons begäran ("lägg även till någon
 * text där, nu ligger den tomt"), inte godkänd än. Rubrik, ingress och en
 * förklaring per lyft del: beskriver vad översikten visar, utan siffror eller
 * löften (honest-proof). Stjärnorna markerar accentordet, som i resten av
 * sidan. Förklaringarnas ord är produktens egna paneltitlar.
 */
const COPY = {
  rubrik: { sv: "Hela dagen på *en skärm*.", en: "The whole day on *one screen*." },
  lede: {
    sv: "Översikten visar vad agenterna gjort och vad som väntar på dig. Varje del uppdateras medan Iris arbetar.",
    en: "The overview shows what the agents have done and what is waiting for you. Each part updates while Iris works."
  },
  delar: [
    {
      rubrik: { sv: "Nyckeltalen", en: "The key figures" },
      text: { sv: "Körningar, levererade leads, det som väntar på en människa och vad det kostat.", en: "Runs, delivered leads, what is waiting for a person, and what it has cost." }
    },
    {
      rubrik: { sv: "Pågår just nu", en: "Running now" },
      text: { sv: "Körningen fortsätter på servern. Du kan lämna sidan och komma tillbaka.", en: "The run continues on the server. You can leave the page and come back." }
    },
    {
      rubrik: { sv: "Iris, leadsagenten", en: "Iris, the leads agent" },
      text: { sv: "Beställt och levererat per vecka, och hur körningarna slutade.", en: "Ordered and delivered per week, and how the runs ended." }
    }
  ]
};

function Accent({ text: value }: Readonly<{ text: string }>) {
  return (
    <>
      {value.split(/\*([^*]+)\*/g).map((part, i) =>
        i % 2 === 1 ? (
          <span key={i} className="italic-disp text-warning">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

export function DashboardIsar() {
  const { text, locale } = useLocale();

  return (
    <section aria-labelledby="isar-rubrik" className="relative overflow-hidden">
      <i aria-hidden="true" data-mo="rule" className="mo-rule" />
      {/* Kort botten: pinnens spacer lämnar redan luft efter akten. */}
      <div className="mx-auto max-w-[1480px] px-6 pb-10 pt-24 md:px-10 md:pb-12 md:pt-28">
        {/* Pinnas på desktop av rörelsen, med det yttre elementet som
            färdigt pin-spacer så att ScrollTrigger aldrig flyttar noder React
            äger; på mobil skrubbas bilden i sin egen färd. */}
        <div data-isar-spacer>
          {/* Texten står till HÖGER om bilden på desktop: rälen sitter längst till
              vänster i översikten, och linjer dragna från vänster försvann mot
              den mörka rälen. I DOM:en kommer texten först, för läsordningen och
              för mobilen, där den står ovanför bilden. */}
          {/* data-case: översikten glider in från vänster och fjädrar tillbaka,
              och rubriken och ingressen avtäcks när den landat (useLandingMotion,
              caseEntry), innan pinnen och sprängskissen tar över. */}
          <div data-isar-pin data-case className="isar relative grid grid-cols-12 gap-y-10 lg:items-center lg:gap-x-10">
            <div className="col-span-12 lg:col-span-4 lg:col-start-9 lg:row-start-1">
              {/* key per språk: rubriken och ingressen radspaltas av SplitText. */}
              <h2
                id="isar-rubrik"
                key={`h-${locale}`}
                data-case-text
                className="max-w-[14ch] font-display text-[clamp(1.875rem,3.4vw,2.75rem)] font-semibold leading-[1.06] tracking-[-0.028em]"
              >
                <Accent text={text(COPY.rubrik)} />
              </h2>
              <p key={`p-${locale}`} data-case-text className="mt-4 max-w-[40ch] text-[1.0625rem] leading-[1.65] text-ink-muted">
                {text(COPY.lede)}
              </p>
              {/* Förklaringarna tänds av rörelsen (--on) i takt med att delen
                  lyfts och linjen ritas; på mobil står de som en vanlig lista. */}
              <ol className="isar__pts mt-8 border-t border-ink/12">
                {COPY.delar.map((d) => (
                  <li key={d.rubrik.sv} data-isar-pt className="isar__pt border-b border-ink/12 py-4">
                    <p className="text-[1rem] font-semibold tracking-[-0.01em]">{text(d.rubrik)}</p>
                    <p className="mt-1 max-w-[36ch] text-[0.9375rem] leading-[1.55] text-ink-muted">{text(d.text)}</p>
                  </li>
                ))}
              </ol>
              {/* "Ytorna ovan": på desktop står raden bredvid bilden, på mobil
                  under den (se figurens kolumn), aldrig ovanför. */}
              <p data-mo="up" className="mt-5 hidden text-[0.8125rem] text-ink-subtle lg:block">
                {text(EXEMPELRAD)}
              </p>
            </div>

            {/* Sju kolumner, inte åtta: de lyfta delarna växer utanför bilden och
                gick annars ihop med textspalten; den tomma kolumnen bär linjerna. */}
            <div data-case-box data-from="left" className="col-span-12 lg:col-span-7 lg:col-start-1 lg:row-start-1">
              {/* data-hole: ytan och delarna lyfts ur dygnsljuset. */}
              <figure data-isar data-hole className="isar__stage">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  data-isar-base
                  src="/produkt/oversikt-1400.webp"
                  srcSet="/produkt/oversikt-1400.webp 1400w, /produkt/oversikt.webp 2880w"
                  sizes="(min-width: 1280px) 940px, 92vw"
                  width={1400}
                  height={933}
                  alt={text(ALT)}
                  loading="lazy"
                  decoding="async"
                  className="isar__base"
                />
                {/* Den förblurrade tvillingen: samma bild, oskärpa i CSS en gång. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  data-isar-blur
                  src="/produkt/oversikt-1400.webp"
                  width={1400}
                  height={933}
                  alt=""
                  aria-hidden="true"
                  loading="lazy"
                  decoding="async"
                  className="isar__blur"
                />
                {DELAR.map((d) => (
                  <div
                    key={d.namn}
                    data-isar-part={d.namn}
                    data-hole
                    aria-hidden="true"
                    className="isar__part"
                    style={{ "--cx": d.cx, "--cy": d.cy, "--cw": d.cw, "--ch": d.ch } as React.CSSProperties}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/produkt/oversikt-1400.webp"
                      srcSet="/produkt/oversikt-1400.webp 1400w, /produkt/oversikt.webp 2880w"
                      sizes="(min-width: 1280px) 940px, 92vw"
                      width={1400}
                      height={933}
                      alt=""
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                ))}
              </figure>
              <p data-mo="up" className="mt-4 text-[0.8125rem] text-ink-subtle lg:hidden">
                {text(EXEMPELRAD)}
              </p>
            </div>

            {/* Linjerna från förklaring till del. Ritas av rörelsen
                (pathLength 1 gör dashoffset till en 0..1-ritning). */}
            <svg data-isar-lines aria-hidden="true" className="isar__lines">
              {COPY.delar.map((d) => (
                <g key={d.rubrik.sv}>
                  <line pathLength={1} className="isar__line" />
                  <circle r={3.5} className="isar__dot" />
                </g>
              ))}
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
