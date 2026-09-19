"use client";

import { CheckCircle2, Loader2, Mail, Play, RotateCcw, ShieldQuestion } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui";
import { Integritetsnotis } from "@/components/kvitton/Integritetsnotis";
import { FRAGOR, MEJL, SAMMANFATTNING, SAMMANFATTNINGSTEXT } from "@/lib/demo/kvitton";
import { cn } from "@/lib/utils";

/**
 * Kvittohanteraren visad hela vägen: inkorgen rullar in, agenten plockar ut
 * beloppen i realtid, resultatet och sammanfattningen växer fram.
 *
 * ## Varför den inte är kopplad till något
 *
 * Ingen LLM, ingen backend, ingen nyckel. Sidan är publik och anonym — samma
 * avvägning som varje annan /demo-sektion. Mejlen speglar backendens
 * mock-inkorg (kvitton/mejl.py), så den inloggade körningen visar samma
 * berättelse på riktigt.
 *
 * ## Animationen är en UPPSPELNING, inte en simulering
 *
 * Varje steg visar ett förberett facit — inget räknas i webbläsaren, av samma
 * skäl som den gamla bokföringsdemon angav: en andra uträkning vid sidan av
 * backendens glider isär, och den enda som märker det är en besökare som
 * räknar efter. `prefers-reduced-motion` hoppar direkt till slutläget: rörelsen
 * är retorik, innehållet är detsamma utan den.
 */

const STEG_MS = 520;

function kr(varde: string): string {
  const tal = Number(varde);
  if (!Number.isFinite(tal)) return varde;
  return `${new Intl.NumberFormat("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(tal)} kr`;
}

/** Demons chatt — besökaren väljer fråga, svaret fälls ut. Konstanter. */
function DemoChatt() {
  const [stallda, setStallda] = useState<number[]>([]);
  const kvar = FRAGOR.map((_, i) => i).filter((i) => !stallda.includes(i));
  const sista = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const svar = sista.current;
    if (!svar || stallda.length === 0) return;
    const ruta = svar.closest<HTMLElement>("[data-rullyta]");
    if (!ruta) return;
    ruta.scrollTop += svar.getBoundingClientRect().top - ruta.getBoundingClientRect().top;
  }, [stallda.length]);

  return (
    <div>
      <div className="grid gap-3">
        {stallda.map((i, index) => (
          <div key={i} ref={index === stallda.length - 1 ? sista : null} className="grid gap-3">
            <p className="ml-auto max-w-[92%] rounded-card bg-paper2 px-3.5 py-2.5 text-[0.875rem] leading-6 text-ink">
              {FRAGOR[i].fraga}
            </p>
            <p className="max-w-[92%] whitespace-pre-wrap rounded-card border border-ink/15 px-3.5 py-2.5 text-[0.875rem] leading-6 text-ink-muted">
              {FRAGOR[i].svar}
            </p>
          </div>
        ))}
      </div>

      {kvar.length ? (
        <div className={stallda.length ? "mt-5" : ""}>
          <p className="text-[0.8125rem] text-mineral">
            {stallda.length ? "Fråga något mer:" : "Klicka på en fråga:"}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {kvar.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => setStallda((f) => [...f, i])}
                className="focus-ring rounded-input border border-ink/15 px-3 py-2 text-left text-[0.8125rem] text-ink-muted hover:border-ochre hover:text-ink"
              >
                {FRAGOR[i].fraga}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-5 text-[0.8125rem] text-mineral">
          Det var frågorna i exemplet. I produkten skriver du dina egna, och
          assistenten hämtar siffrorna ur dina kvitton.
        </p>
      )}
    </div>
  );
}

export function KvittoDemo() {
  /**
   * -1 = inte startad. 0..MEJL.length = så många mejl som hunnit läsas.
   * Två faser per mejl: det GLIDER IN (syns i inkorgen) i steg n, och
   * avläses (belopp markeras, badge sätts) ett halvt steg senare — det är
   * markeringen i det ögonblicket som är hela demons poäng.
   */
  const [steg, setSteg] = useState(-1);
  const [avlasta, setAvlasta] = useState(0);
  const kor = steg >= 0 && steg < MEJL.length;
  const klar = steg >= MEJL.length;

  useEffect(() => {
    if (!kor) return;
    const timer = window.setInterval(() => setSteg((s) => s + 1), STEG_MS);
    return () => window.clearInterval(timer);
  }, [kor]);

  // Avläsningen släpar ett halvt steg efter inglidningen, så att ögat hinner
  // se mejlet FÖRE markeringen. Vid reduced motion sätts båda direkt.
  useEffect(() => {
    if (steg < 0) return;
    const timer = window.setTimeout(() => setAvlasta(steg), STEG_MS / 2);
    return () => window.clearTimeout(timer);
  }, [steg]);

  function starta() {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setSteg(MEJL.length);
      setAvlasta(MEJL.length);
      return;
    }
    setSteg(0);
    setAvlasta(0);
  }

  function nollstall() {
    setSteg(-1);
    setAvlasta(0);
  }

  const synliga = steg < 0 ? [] : MEJL.slice(0, Math.min(steg + 1, MEJL.length));
  const kvitton = MEJL.filter(
    (m, i) => i < avlasta && (m.utfall === "kvitto" || m.utfall === "kvitto_granska")
  );
  const hittadeKlara = kvitton.filter((m) => m.utfall === "kvitto");

  return (
    <div className="mx-auto max-w-[1160px]">
      <p className="mb-4 text-[0.8125rem] leading-6 text-ink-subtle">
        <strong className="font-semibold text-ink-muted">Exempel.</strong> Inkorgen,
        bolagen och siffrorna är påhittade och svaren skrivna i förväg — ingen
        modell körs på den här sidan. I produkten läser agenten din riktiga
        inkorg, med samma kontroller.
      </p>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        {steg < 0 ? (
          <button
            type="button"
            onClick={starta}
            className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-input bg-ink px-5 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
          >
            <Play className="h-4 w-4 text-warning" aria-hidden />
            Skanna inkorgen
          </button>
        ) : (
          <button
            type="button"
            onClick={nollstall}
            className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-input bg-paper2 px-5 text-[0.9375rem] font-semibold text-ink transition-colors hover:bg-paper2/70"
          >
            <RotateCcw className="h-4 w-4" aria-hidden />
            Kör igen
          </button>
        )}
        {kor ? (
          <p className="flex items-center gap-2 text-[0.875rem] text-mineral" role="status">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Läser mejl {Math.min(steg + 1, MEJL.length)} av {MEJL.length}…
          </p>
        ) : null}
        {klar ? (
          <p className="flex items-center gap-2 text-[0.875rem] text-moss" role="status">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            {SAMMANFATTNING.antal} kvitton hittade, {SAMMANFATTNING.antalGranska} att granska
          </p>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* VÄNSTER: inkorgen som läses, sedan resultatet. */}
        <div className="min-w-0 lg:col-span-7">
          <div className="rounded-card border border-ink/12 bg-paper2/30 p-5">
            <div className="flex items-baseline justify-between gap-4">
              <p className="kicker text-mineral">Inkorgen</p>
              <p className="text-[0.75rem] tabular-nums text-mineral">
                {synliga.length} av {MEJL.length} mejl
              </p>
            </div>

            {steg < 0 ? (
              <p className="mt-4 flex items-center gap-2 border-t border-ink/10 pt-4 text-[0.875rem] leading-6 text-ink-subtle">
                <Mail className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
                Tryck på Skanna inkorgen, så läser agenten mejlen ett i taget och
                plockar ut beloppen medan du tittar på.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-ink/10 border-t border-ink/10">
                {synliga.map((mejl, i) => {
                  const last = i < avlasta;
                  return (
                    <li
                      key={mejl.id}
                      className="animate-mejl-in py-2.5"
                      style={{ animationDelay: "0ms" }}
                    >
                      <div className="flex min-w-0 items-baseline justify-between gap-3">
                        <p className="min-w-0 truncate text-[0.875rem] font-medium text-ink">
                          {mejl.avsandare}
                          <span className="ml-2 font-normal text-ink-subtle">{mejl.amne}</span>
                        </p>
                        <span className="shrink-0">
                          {!last ? (
                            <span className="text-[0.75rem] text-mineral">läser…</span>
                          ) : mejl.utfall === "kvitto" ? (
                            <Badge tone="good">Kvitto</Badge>
                          ) : mejl.utfall === "kvitto_granska" ? (
                            <Badge tone="warn">Granska</Badge>
                          ) : (
                            <span className="text-[0.75rem] text-mineral">inte ett kvitto</span>
                          )}
                        </span>
                      </div>
                      <p className="mt-1 truncate font-mono text-[0.75rem] text-ink-subtle">
                        {last && mejl.belopp ? (
                          <>
                            {mejl.rad.split(/Totalt: |Total: /)[0]}
                            {mejl.rad.includes("Totalt: ") ? "Totalt: " : ""}
                            {/* Beloppet LYFTS när det identifieras — demons
                                kärnögonblick, DESIGN.md:s "current selection". */}
                            <mark className="animate-belopp rounded-[3px] bg-ochre/25 px-1 py-0.5 font-semibold text-ink">
                              {kr(mejl.belopp)}
                            </mark>
                          </>
                        ) : last && mejl.beloppOriginal ? (
                          <>
                            {mejl.rad.split(/Total: /)[0]}Total:{" "}
                            <mark className="animate-belopp rounded-[3px] bg-copper/20 px-1 py-0.5 font-semibold text-ink">
                              {mejl.beloppOriginal}
                            </mark>
                          </>
                        ) : (
                          mejl.rad
                        )}
                      </p>
                      {last && mejl.anmarkning ? (
                        <p className="mt-1 flex items-start gap-1.5 text-[0.75rem] leading-5 text-ink-subtle">
                          <ShieldQuestion className="mt-0.5 h-3 w-3 shrink-0 text-warning" aria-hidden />
                          {mejl.anmarkning}
                        </p>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Resultatet — raderna landar i takt med avläsningen. */}
          {kvitton.length ? (
            <div className="mt-6">
              <p className="kicker text-mineral">Utplockade kvitton</p>
              {/* Internscroll under 560px — samma regel som Tabell i
                  components/ui.tsx: under minbredden scrollar tabellen i
                  stället för att klämmas. Uppmätt på 375: utan detta trycktes
                  kategorikolumnen in i beloppskolumnen. */}
              <div className="thin-scrollbar mt-2 overflow-x-auto">
              <table className="w-full table-fixed border-collapse text-[15px]" style={{ minWidth: "560px" }}>
                <colgroup>
                  <col style={{ width: "18%" }} />
                  <col style={{ width: "40%" }} />
                  <col style={{ width: "22%" }} />
                  <col style={{ width: "20%" }} />
                </colgroup>
                <thead>
                  <tr className="border-b border-ink/15 text-left">
                    <th className="kicker py-2.5 pr-4 font-medium text-mineral">Datum</th>
                    <th className="kicker py-2.5 pr-4 font-medium text-mineral">Butik</th>
                    <th className="kicker py-2.5 pr-4 font-medium text-mineral">Kategori</th>
                    <th className="kicker py-2.5 text-right font-medium text-mineral">Belopp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/12 border-b border-ink/15">
                  {kvitton.map((mejl) => (
                    <tr key={mejl.id} className="animate-mejl-in">
                      <td className="py-2.5 pr-4 align-top">
                        <span className="text-[0.8125rem] tabular-nums text-ink-muted">
                          {mejl.datum.slice(5)}
                        </span>
                      </td>
                      <td className="min-w-0 py-2.5 pr-4 align-top">
                        <p className="truncate text-[0.875rem]">{mejl.avsandare}</p>
                      </td>
                      <td className="py-2.5 pr-4 align-top">
                        <span className="text-[0.8125rem] text-ink-muted">
                          {mejl.kategoriEtikett ?? "—"}
                        </span>
                      </td>
                      <td className="py-2.5 text-right align-top">
                        {mejl.belopp ? (
                          <span className="num text-[0.875rem] font-medium">{kr(mejl.belopp)}</span>
                        ) : (
                          <Badge tone="warn">Granska</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <p className="mt-2 text-[0.75rem] text-mineral">
                {hittadeKlara.length} avlästa kvitton hittills
                {klar ? " — klart." : "…"}
              </p>
            </div>
          ) : null}
        </div>

        {/* HÖGER: sammanfattningen och assistenten, klistrade. */}
        <div className="min-w-0 lg:col-span-5">
          <div className="lg:sticky lg:top-6 space-y-6">
            <div className="rounded-card border border-ink/12 bg-paper p-5">
              <p className="kicker text-mineral">Sammanfattning</p>
              {klar ? (
                <>
                  <p className="mt-3 font-display text-[2.25rem] leading-none tracking-[-0.01em]">
                    {kr(SAMMANFATTNING.totalt)}
                  </p>
                  <p className="mt-1 text-[0.8125rem] text-ink-subtle">
                    {SAMMANFATTNING.antalKlara} avlästa kvitton · ingående moms{" "}
                    {kr(SAMMANFATTNING.moms)}
                  </p>
                  <dl className="mt-4 divide-y divide-ink/10 border-y border-ink/10">
                    {SAMMANFATTNING.perKategori.map((rad) => (
                      <div key={rad.etikett} className="flex items-baseline justify-between gap-4 py-2">
                        <dt className="text-[0.875rem] text-ink-muted">
                          {rad.etikett}
                          <span className="ml-1.5 text-[0.75rem] text-mineral">×{rad.antal}</span>
                        </dt>
                        <dd className="num text-[0.875rem]">{kr(rad.summa)}</dd>
                      </div>
                    ))}
                  </dl>
                  <p className="mt-4 text-[0.875rem] leading-6 text-ink-muted">
                    {SAMMANFATTNINGSTEXT}
                  </p>
                </>
              ) : (
                <p className="mt-3 text-[0.875rem] leading-6 text-ink-subtle">
                  {kor
                    ? "Summorna skrivs när alla mejl är lästa — inga halva sanningar."
                    : "Kör skanningen, så landar periodens summor och en sammanfattning här."}
                </p>
              )}
            </div>

            <div className="rounded-card border border-ink/12 bg-paper p-5">
              <p className="kicker text-mineral">Fråga kvitto-assistenten</p>
              <p className="mt-2 text-[0.8125rem] leading-6 text-ink-muted">
                Klicka på en fråga så svarar den utifrån kvittona till vänster.
              </p>
              <div data-rullyta className="mt-4 lg:max-h-[24rem] lg:overflow-y-auto lg:pr-3">
                <DemoChatt />
              </div>
            </div>

            <Integritetsnotis />
          </div>
        </div>
      </div>
    </div>
  );
}
