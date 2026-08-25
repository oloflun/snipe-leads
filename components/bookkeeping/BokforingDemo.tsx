"use client";

import { ArrowRight, FileText, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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

/**
 * Etiketten ligger OVANFÖR innehållet, inte i en egen kolumn bredvid.
 *
 * Den satt i ett 3/9-rutnät när demon var sidbred. I den smalare vänsterrutan
 * blev de tre kolumnerna omkring 140px, alltså en etikettspalt som åt en
 * fjärdedel av bredden för fem ord — och tvingade tabellen i steg 3 att
 * trängas på resten.
 */
function Steg({
  nummer,
  rubrik,
  children
}: Readonly<{ nummer: number; rubrik: string; children: React.ReactNode }>) {
  return (
    <section className="border-t border-ink/12 py-5 first:border-t-0 first:pt-0">
      <p className="flex items-baseline gap-2">
        <span className="font-mono text-[0.6875rem] text-ochre">
          {String(nummer).padStart(2, "0")}
        </span>
        <span className="kicker text-mineral">{rubrik}</span>
      </p>
      <div className="mt-3">{children}</div>
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
  const sista = useRef<HTMLDivElement | null>(null);

  /**
   * Rulla fram det nya svaret i rutan.
   *
   * Utan det här ser ett klick ut som att ingenting händer: svaret läggs till
   * längst ned i en ruta med tak, alltså utanför det synliga, och besökaren
   * sitter kvar med samma vy och drar slutsatsen att knappen är trasig. Det
   * var demons enda interaktion, så felet hade kostat hela poängen med den.
   *
   * Rullar RUTAN och inte sidan: `scrollIntoView` hade flyttat hela
   * dokumentet när sidan också kan rullas.
   */
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
            <p className="max-w-[92%] whitespace-pre-wrap rounded-card border border-ink/15 px-3.5 py-2.5 text-[0.875rem] leading-6 text-ink/85">
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

/**
 * Två rutor sida vid sida: genomgången till vänster, assistenten till höger.
 *
 * ## Varför inte en spalt rakt ned
 *
 * Fem sidbreda steg staplade på varandra gjorde demon till sidans längsta
 * sektion — omkring 1 300px bred och över tvåtusen hög — för innehåll som är
 * fyra korta tabeller och en chatt. Bredden var det värsta av det: en
 * avläsningsrad med tre fält drogs ut över hela fönstret, så ögat fick vandra
 * en decimeter mellan etikett och värde.
 *
 * Nu är genomgången en smal ruta som växer NEDÅT, med tak och egen rullning så
 * att den inte kan bli hur lång som helst, och assistenten en egen ruta
 * bredvid. Att de ligger sida vid sida är inte bara en yteffekt: chatten
 * svarar med siffror ur periodrapporten, och nu går de att läsa samtidigt.
 *
 * ## Taket och rullningen
 *
 * `max-h` + `overflow-y-auto` gäller bara från lg och uppåt. På en telefon är
 * spalterna staplade ändå, och en rullyta inuti en sida som redan rullar är
 * ett känt sätt att göra innehåll oåtkomligt med tummen.
 */
export function BokforingDemo() {
  return (
    <div className="mx-auto max-w-[1120px]">
      {/* Märkningen står FÖRST och kan inte klickas bort. Samma regel som
          leads-agentens exempelbolag: en siffra som ser ut att komma ur en
          körning måste säga att den inte gör det.
          Den ligger utanför båda rutorna: den gäller siffrorna i vänstra OCH
          samtalet i högra, och en kopia i varje ruta hade sagt samma sak två
          gånger. */}
      <p className="flex items-start gap-2 rounded-card border border-ochre/40 bg-ochre/10 px-4 py-2.5 text-[0.8125rem] leading-6 text-ink/80">
        <ShieldAlert className="mt-1 h-3.5 w-3.5 shrink-0 text-warning" aria-hidden />
        <span>
          <strong className="font-semibold">Exempel.</strong> Underlaget, bolaget och
          siffrorna är påhittade, och svaren till höger är skrivna i förväg. Ingen
          modell körs på den här sidan och ingen kunddata visas.
        </span>
      </p>

      <div className="mt-5 grid gap-5 lg:grid-cols-12 lg:gap-6">
        {/* VÄNSTER: vägen från kvitto till periodrapport. */}
        <div className="lg:col-span-7">
          <div className="rounded-card border border-ink/12 bg-paper2/30 p-5">
            <p className="kicker text-mineral">Från kvitto till underlag</p>
            <div className="mt-4 lg:max-h-[30rem] lg:overflow-y-auto lg:pr-4">

      <Steg nummer={1} rubrik="Underlaget">
        <p className="flex items-center gap-2 text-[0.9375rem] text-ink">
          <FileText className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          {EXEMPELKVITTO.filnamn}
        </p>
        <p className="mt-2 text-[0.875rem] leading-6 text-ink/60">
          En drivmedelsfaktura från {EXEMPELKVITTO.motpart}. I produkten läses filen i
          minnet och kastas — det som sparas är fälten nedan plus en kontrollsumma.
        </p>
      </Steg>

      <Steg nummer={2} rubrik="Avläsningen">
        {/* Två spalter, inte tre. Källcitatet låg i en egen tredje spalt när
            demon var sidbred; i den smalare rutan blev den omkring 230px och
            bröt monotexten mitt i fakturaraden. Nu står citatet under värdet,
            där det ändå hör hemma: det är belägget FÖR värdet. */}
        <dl className="divide-y divide-ink/10 border-y border-ink/10">
          {AVLASNING.map((rad) => (
            <div key={rad.falt} className="py-2.5">
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-[0.8125rem] text-mineral">{rad.falt}</dt>
                <dd className="text-right text-[0.9375rem] text-ink">{rad.varde}</dd>
              </div>
              <dd className="mt-1 truncate font-mono text-[0.75rem] text-ink/45" title={rad.kalla}>
                “{rad.kalla}”
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-[0.8125rem] leading-6 text-ink/55">
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
        <p className="mt-3 text-[0.8125rem] leading-6 text-ink/55">
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
        <p className="mt-4 text-[0.8125rem] leading-6 text-ink/55">
          {PERIOD.fran} till {PERIOD.till}. Perioden går ihop, alltså visas summorna.
          Gjorde den inte det hade du fått bristerna i stället.
        </p>
      </Steg>

            </div>
          </div>
        </div>

        {/* HÖGER: assistenten, i en ruta man kan prova.
            `lg:sticky` gör att den följer med när vänsterrutans innehåll
            rullas — annars hade svaret glidit ur bild precis när besökaren
            letade upp siffran det bygger på. */}
        <div className="lg:col-span-5">
          <div className="rounded-card border border-ink/12 bg-paper p-5 lg:sticky lg:top-6">
            <p className="kicker text-mineral">Fråga assistenten</p>
            <p className="mt-2 text-[0.8125rem] leading-6 text-ink/60">
              Klicka på en fråga så svarar den utifrån siffrorna till vänster.
            </p>
            <div data-rullyta className="mt-4 lg:max-h-[22rem] lg:overflow-y-auto lg:pr-3">
              <DemoChatt />
            </div>
            <p className="mt-4 flex items-start gap-2 border-t border-ink/12 pt-4 text-[0.75rem] leading-5 text-ink/55">
              <ArrowRight className="mt-0.5 h-3 w-3 shrink-0 text-ochre" aria-hidden />
              <span>
                Varje belopp i svaret kommer från siffrorna till vänster. I produkten
                kontrolleras det maskinellt: ett svar som bär ett tal assistenten inte
                hämtat stoppas innan du ser det.
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
