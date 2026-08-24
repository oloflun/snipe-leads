"use client";

import { ArrowRight, FileText, ShieldAlert } from "lucide-react";
import { useState } from "react";
import {
  AVLASNING,
  EXEMPELKVITTO,
  FRAGOR,
  PERIOD,
  VERIFIKAT
} from "@/lib/demo/bokforing";

/**
 * Bokföringen visad hela vägen, med ett påhittat kvitto.
 *
 * ## Varför den inte är kopplad till något
 *
 * Ingen LLM, ingen backend, ingen nyckel. Sidan är publik och anonym, och en
 * levande körning per besökare kostar pengar utan att visa mer — samma
 * avvägning som gjorde Email Studios demoläge `simulated: true`.
 *
 * Chatten längst ned SVARAR ändå. Besökaren klickar på en fråga och får svaret
 * — samtalet drivs alltså av den som läser, inte av en inspelning som rullar.
 * Svaren är konstanter, och ett test kontrollerar att varje krontal i dem finns
 * i periodrapporten ovanför. Det är samma krav som INV-BOOK-003 ställer på det
 * riktiga svaret, kontrollerat vid bygget i stället för vid körningen.
 *
 * Ett fritextfält vore nästa steg och kräver en modell. Det står utskrivet på
 * sidan i stället för att antydas med en ruta som inte går att skriva i.
 *
 * ## Siffrorna
 *
 * Handräknade konstanter i lib/demo/bokforing.ts, med facit i kommentarerna och
 * ett test som räknar om dem. Att räkna i webbläsaren hade betytt en andra
 * uträkning vid sidan av `bookkeeping/math.py`.
 */

/**
 * "1000.00" -> "1 000,00 kr".
 *
 * Konstanterna i lib/demo/bokforing.ts är MASKINLÄSBARA med flit: de speglar
 * vad backenden skickar (`kr()` i bookkeeping/period.ts), och
 * tests/test_demo_bokforing.py räknar om dem med Decimal. Att lagra dem
 * formaterade hade betytt att testet fick tolka svensk skrivning innan det kan
 * räkna.
 *
 * Formateringen hör alltså hemma här, vid renderingen. Utan den stod
 * "1 250,00 kr" i avläsningen och "1250.00" i verifikatet på samma sida —
 * två skrivsätt för pengar, varav det ena inte är svenskt.
 */
function kr(varde: string): string {
  const tal = Number(varde);
  if (!Number.isFinite(tal)) return varde;
  return `${new Intl.NumberFormat("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(tal)} kr`;
}

function Steg({
  nummer,
  rubrik,
  children
}: Readonly<{ nummer: number; rubrik: string; children: React.ReactNode }>) {
  return (
    <section className="grid grid-cols-12 gap-x-6 gap-y-3 border-t border-ink/15 py-7">
      <div className="col-span-12 md:col-span-3">
        <p className="flex items-baseline gap-2">
          <span className="font-mono text-[0.6875rem] text-ochre">
            {String(nummer).padStart(2, "0")}
          </span>
          <span className="kicker text-mineral">{rubrik}</span>
        </p>
      </div>
      <div className="col-span-12 md:col-span-9">{children}</div>
    </section>
  );
}

/**
 * Demons chatt. Besökaren väljer fråga, svaret fälls ut.
 *
 * Ingen modell, ingen backend, ingen kostnad per besökare — se filens
 * docstring. Ställda frågor försvinner ur listan så att det syns vad som är
 * kvar att prova.
 */
function DemoChatt() {
  const [stallda, setStallda] = useState<number[]>([]);
  const kvar = FRAGOR.map((_, i) => i).filter((i) => !stallda.includes(i));

  return (
    <div>
      <div className="grid gap-3">
        {stallda.map((i) => (
          <div key={i} className="grid gap-3">
            <p className="ml-auto max-w-[62ch] rounded-card bg-paper2 px-4 py-3 text-[0.9375rem] leading-6 text-ink">
              {FRAGOR[i].fraga}
            </p>
            <p className="max-w-[62ch] whitespace-pre-wrap rounded-card border border-ink/15 px-4 py-3 text-[0.9375rem] leading-6 text-ink/85">
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
                className="focus-ring rounded-input border border-ink/15 px-3 py-2 text-left text-[0.8125rem] text-ink/70 hover:border-ochre hover:text-ink"
              >
                {FRAGOR[i].fraga}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-5 text-[0.8125rem] text-mineral">
          Det var frågorna i exemplet. I produkten skriver du dina egna, och
          assistenten hämtar siffrorna ur din bokföring.
        </p>
      )}
    </div>
  );
}

export function BokforingDemo() {
  return (
    <div>
      {/* Märkningen står FÖRST och kan inte klickas bort. Samma regel som
          leads-agentens exempelbolag: en siffra som ser ut att komma ur en
          körning måste säga att den inte gör det. */}
      <p className="flex items-start gap-2 rounded-card border border-ochre/40 bg-ochre/10 px-4 py-3 text-[0.875rem] leading-6 text-ink/80">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        <span>
          <strong className="font-semibold">Exempel.</strong> Underlaget, bolaget och
          siffrorna är påhittade, och samtalet längst ned är skrivet i förväg. Ingen
          modell körs på den här sidan och ingen kunddata visas.
        </span>
      </p>

      <Steg nummer={1} rubrik="Underlaget">
        <p className="flex items-center gap-2 text-[0.9375rem] text-ink">
          <FileText className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          {EXEMPELKVITTO.filnamn}
        </p>
        <p className="mt-2 max-w-[60ch] text-[0.875rem] leading-6 text-ink/60">
          En drivmedelsfaktura från {EXEMPELKVITTO.motpart}. I produkten läses filen i
          minnet och kastas — det som sparas är fälten nedan plus en kontrollsumma.
        </p>
      </Steg>

      <Steg nummer={2} rubrik="Avläsningen">
        <dl className="divide-y divide-ink/10 border-y border-ink/10">
          {AVLASNING.map((rad) => (
            <div key={rad.falt} className="grid grid-cols-12 gap-x-4 py-2.5">
              <dt className="col-span-4 text-[0.8125rem] text-mineral md:col-span-3">
                {rad.falt}
              </dt>
              <dd className="col-span-8 text-[0.9375rem] text-ink md:col-span-4">{rad.varde}</dd>
              <dd className="col-span-12 mt-1 font-mono text-[0.75rem] text-ink/45 md:col-span-5 md:mt-0">
                “{rad.kalla}”
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 max-w-[60ch] text-[0.8125rem] leading-6 text-ink/55">
          Varje fält har en källa i texten. Ett fält som inte står på underlaget
          gissas inte — underlaget går till granskning i stället.
        </p>
      </Steg>

      <Steg nummer={3} rubrik="Verifikatet">
        <table className="w-full border-y border-ink/10 text-[0.875rem]">
          <thead>
            <tr className="text-left text-[0.75rem] text-mineral">
              <th className="py-2 font-normal">Konto</th>
              <th className="py-2 font-normal">Benämning</th>
              <th className="py-2 text-right font-normal">Debet</th>
              <th className="py-2 text-right font-normal">Kredit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/10">
            {VERIFIKAT.map((rad) => (
              <tr key={rad.konto}>
                <td className="py-2 font-mono text-[0.8125rem]">{rad.konto}</td>
                <td className="py-2 text-ink/75">{rad.kontonamn}</td>
                <td className="num py-2 text-right">{rad.debet ? kr(rad.debet) : ""}</td>
                <td className="num py-2 text-right">{rad.kredit ? kr(rad.kredit) : ""}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-ink/20 font-medium">
              <td className="py-2" colSpan={2}>
                Summa
              </td>
              <td className="num py-2 text-right">{kr("1250.00")}</td>
              <td className="num py-2 text-right">{kr("1250.00")}</td>
            </tr>
          </tfoot>
        </table>
        <p className="mt-3 max-w-[60ch] text-[0.8125rem] leading-6 text-ink/55">
          Modellen valde kategori. Koden valde konto ur BAS och byggde raderna, så
          debet och kredit är lika av konstruktion.
        </p>
      </Steg>

      <Steg nummer={4} rubrik="Perioden">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          {[
            ["Intäkter", PERIOD.summor.intakter],
            ["Kostnader", PERIOD.summor.kostnader],
            ["Utgående moms", PERIOD.summor.utgaende_moms],
            ["Ingående moms", PERIOD.summor.ingaende_moms],
            ["Resultat", PERIOD.summor.resultat_fore_skatt],
            ["Moms att betala", PERIOD.summor.moms_att_betala]
          ].map(([etikett, varde]) => (
            <div key={etikett}>
              <dt className="text-[0.75rem] text-mineral">{etikett}</dt>
              <dd className="num mt-0.5 text-[1.0625rem] text-ink">{kr(varde)}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 max-w-[60ch] text-[0.8125rem] leading-6 text-ink/55">
          {PERIOD.fran} till {PERIOD.till}. Perioden går ihop, alltså visas summorna.
          Gjorde den inte det hade du fått bristerna i stället.
        </p>
      </Steg>

      <Steg nummer={5} rubrik="Fråga assistenten">
        <DemoChatt />
        <p className="mt-4 flex items-start gap-2 max-w-[62ch] text-[0.8125rem] leading-6 text-ink/55">
          <ArrowRight className="mt-1 h-3.5 w-3.5 shrink-0 text-ochre" aria-hidden />
          <span>
            Varje belopp i svaret kommer från siffrorna ovanför. I produkten kontrolleras
            det maskinellt: ett svar som bär ett tal assistenten inte hämtat stoppas
            innan du ser det.
          </span>
        </p>
      </Steg>
    </div>
  );
}
