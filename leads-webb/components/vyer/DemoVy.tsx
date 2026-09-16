"use client";

import { CalendarCheck, Mail, RotateCcw, Search, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, btnSecondary } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * Se Iris arbeta — ett genomspelat flöde med fiktiv data: hitta, berika
 * (källorna synliga), skriva, hantera svaret, boka mötet.
 *
 * Allt innehåll är påhittat och märkt så (hederlighetsregeln i DESIGN.md):
 * demon visar HUR Iris arbetar, aldrig ett resultat som utger sig för att
 * vara verkligt. Bolaget, personerna och mejlen finns inte.
 *
 * Animationen är en stegräknare som tickar framåt; varje moment stiger in
 * med sajtens vanliga motion (300 ms, ease-out). Föredrar besökaren
 * reducerad rörelse visas allt på en gång, färdigt, utan tick.
 */

const STEG_MS = 1900;
const SISTA_STEGET = 8;

/** Fiktiva källorna, med vad Iris läste ut ur var och en. */
const KALLOR: ReadonlyArray<{ etikett: string; fynd: string }> = [
  { etikett: "Bolagets hemsida", fynd: "Bygger ut serviceverksamheten kring anläggningen i Holmsund" },
  { etikett: "Platsbanken", fynd: "Rekryterar två servicetekniker till fältteamet" },
  { etikett: "Lokal nyhetsartikel", fynd: "Invigde den nya anläggningen i augusti" },
  { etikett: "LinkedIn", fynd: "Karin Lindqvist är driftchef sedan i våras" }
];

const UTKAST_BROD =
  "Hej Karin,\n\nsåg att Fjällvind bygger upp serviceverksamheten kring nya anläggningen i Holmsund och tar in två tekniker till fältteamet. När fältstyrkan växer är planeringen ofta det som spricker först.\n\nVi hjälper bolag i er storlek att hålla ihop arbetsordrar och schemaläggning när teamet växer. Får jag visa hur det ser ut? Tjugo minuter räcker.";

function Moment({
  synligt,
  animera,
  Ikon,
  kicker,
  children
}: Readonly<{
  synligt: boolean;
  animera: boolean;
  Ikon: typeof Search;
  kicker: string;
  children: React.ReactNode;
}>) {
  return (
    <li
      aria-hidden={!synligt}
      className={cn(
        "grid grid-cols-[2rem_1fr] gap-x-4 py-5",
        animera && "transition-[opacity,transform] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
        synligt ? "opacity-100 translate-y-0" : "pointer-events-none opacity-0 translate-y-2"
      )}
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-paper">
        <Ikon className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-[0.8125rem] font-medium uppercase tracking-[0.1em] text-ink/45">
          {kicker}
        </p>
        <div className="mt-1.5">{children}</div>
      </div>
    </li>
  );
}

export function DemoVy() {
  // 0 = inget än; varje heltal däröver släpper fram nästa moment.
  const [steg, setSteg] = useState(0);
  const [stillsam, setStillsam] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  function stoppa() {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }

  function spela(franBorjan: boolean) {
    stoppa();
    if (franBorjan) setSteg(1);
    timer.current = setInterval(() => {
      setSteg((s) => {
        if (s >= SISTA_STEGET) {
          stoppa();
          return s;
        }
        return s + 1;
      });
    }, STEG_MS);
  }

  useEffect(() => {
    const vill = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setStillsam(vill);
    if (vill) {
      setSteg(SISTA_STEGET);
      return;
    }
    setSteg(1);
    spela(false);
    return stoppa;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const klar = steg >= SISTA_STEGET;
  // Utkastet skrivs fram tecken för tecken över två steg; i stillsamt läge
  // står det färdigt direkt.
  const utkastAndel = stillsam ? 1 : steg <= 3 ? 0 : steg === 4 ? 0.45 : 1;
  const utkastText = UTKAST_BROD.slice(0, Math.round(UTKAST_BROD.length * utkastAndel));

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Se Iris arbeta"
        beskrivning="Ett genomspelat flöde från hittat bolag till bokat möte, med varje källa synlig på vägen. Så här ser arbetet ut när du kör Iris på riktigt."
        actions={
          klar ? (
            <button type="button" onClick={() => spela(true)} className={btnSecondary}>
              <RotateCcw className="h-4 w-4" aria-hidden />
              Spela upp igen
            </button>
          ) : null
        }
      />

      <p className="max-w-[70ch] text-[0.8125rem] leading-5 text-ink/50">
        Fiktivt exempel: bolaget, personerna och meddelandena är påhittade. Ingenting här har
        skickats, och i skarp drift går varje utkast via din granskningskö.
      </p>

      <ol className="max-w-[46rem] divide-y divide-ink/12 border-y border-ink/15" aria-live="polite">
        <Moment synligt={steg >= 1} animera={!stillsam} Ikon={Search} kicker="Iris söker">
          <p className="text-[0.9375rem] leading-6 text-ink/70">
            Söker bolag som matchar målgruppen: industriservice i Norrland, 20 till 80 anställda.
          </p>
          <div
            className={cn(
              "mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-[8px] border border-ink/12 bg-paper2/60 px-4 py-3",
              !stillsam && "transition-opacity duration-300",
              steg >= 2 ? "opacity-100" : "opacity-0"
            )}
            aria-hidden={steg < 2}
          >
            <span className="text-[0.9375rem] font-semibold text-ink">Fjällvind Energi AB</span>
            <span className="text-[0.875rem] text-ink/50">Umeå</span>
            <span className="num text-[0.9375rem] text-ink/62" title="Träffsäkerhet mot målgruppen">
              87 %
            </span>
            <Badge tone="good">Kvalificerad</Badge>
          </div>
        </Moment>

        <Moment synligt={steg >= 3} animera={!stillsam} Ikon={Sparkles} kicker="Berikar med källor">
          <p className="text-[0.9375rem] leading-6 text-ink/70">
            Varje uppgift bär sin källa. Det Iris inte kan belägga skrivs inte.
          </p>
          <ul className="mt-3 space-y-2">
            {KALLOR.map((kalla) => (
              <li key={kalla.etikett} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <span className="rounded-[6px] border border-ink/10 bg-ink/[0.035] px-2.5 py-0.5 text-xs font-medium text-ink/70">
                  {kalla.etikett}
                </span>
                <span className="min-w-0 flex-1 basis-60 text-[0.875rem] leading-6 text-ink/62">
                  {kalla.fynd}
                </span>
              </li>
            ))}
          </ul>
        </Moment>

        <Moment synligt={steg >= 4} animera={!stillsam} Ikon={Mail} kicker="Skriver ett personligt utkast">
          <div className="rounded-[8px] border border-ink/12 bg-paper2/60 px-4 py-3">
            <p className="text-[0.875rem] text-ink/55">
              Till: karin.lindqvist@fjallvindenergi.example
            </p>
            <p className="mt-1 text-[0.9375rem] font-semibold text-ink">Serviceteamet i Holmsund</p>
            <p className="mt-2 min-h-[9.5rem] whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink/80">
              {utkastText}
              {utkastAndel < 1 ? <span className="text-ochre">▍</span> : null}
            </p>
          </div>
          <p
            className={cn(
              "mt-2 text-[0.875rem] leading-6 text-ink/60",
              !stillsam && "transition-opacity duration-300",
              steg >= 6 ? "opacity-100" : "opacity-0"
            )}
            aria-hidden={steg < 6}
          >
            Utkastet läggs i granskningskön. Du läser, godkänner, och först då skickas det.
          </p>
        </Moment>

        <Moment synligt={steg >= 7} animera={!stillsam} Ikon={Mail} kicker="Ett svar kommer in">
          <blockquote className="border-l-2 border-ink/20 pl-4 text-[0.9375rem] leading-7 text-ink/75">
            &ldquo;Hej! Vi känner igen oss i det där. Vad kostar det, och hinner ni ta ett möte
            nästa vecka?&rdquo;
          </blockquote>
          <p className="mt-2 max-w-[60ch] text-[0.875rem] leading-6 text-ink/60">
            Prisfrågan eskaleras till dig, enligt dina regler: Iris lämnar aldrig en siffra
            själv. Mötesförslaget förbereder hon med tre tider ur din kalender, och du
            bekräftar innan något bokas.
          </p>
        </Moment>

        <Moment synligt={steg >= 8} animera={!stillsam} Ikon={CalendarCheck} kicker="Mötet bokas">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-[8px] border border-moss/25 bg-moss/10 px-4 py-3">
            <span className="text-[0.9375rem] font-semibold text-ink">
              Möte: Fjällvind Energi AB
            </span>
            <span className="num text-[0.9375rem] text-ink/70">tis 22 sep, 10.00</span>
            <Badge tone="good">I din kalender</Badge>
          </div>
          <p className="mt-2 text-[0.875rem] leading-6 text-ink/60">
            Bokat efter din bekräftelse. Från första sökningen hit: två godkännanden från dig,
            noll meddelanden du inte sett.
          </p>
        </Moment>
      </ol>
    </div>
  );
}
