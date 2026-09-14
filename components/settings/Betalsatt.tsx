"use client";

import { CreditCard, Loader2, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { hamtaBetalsatt, sparaBetalsatt, taBortBetalsatt } from "@/lib/actions/betalsatt";
import {
  TESTKORT,
  bararSiffror,
  formateraKortnummer,
  kortfel,
  tillKortuppgifter,
  type Betalsatt as BetalsattTyp
} from "@/lib/betalning";

/**
 * Betalsätt — flödet, i testläge.
 *
 * ## Vad som är på riktigt här och vad som inte är det
 *
 * Formuläret, valideringen, felvägen och det sparade kortets rad är riktiga.
 * Det som INTE finns är en betalväxel: ingenting debiteras, och ingen faktura
 * skapas. Raden i databasen är ett sparat val, inte ett betalningsmedel.
 *
 * Det står utskrivet i gränssnittet också, och det är avsiktligt. En
 * betalningsvy som ser skarp ut men inte är det är den sortens yta någon
 * längre fram tar för given.
 *
 * ## Varför bara testkort accepteras
 *
 * Ett kortfält som sväljer vilket nummer som helst lär kunden att skriva sitt
 * riktiga kort här — och då ligger ett PAN i en request mot en server som
 * varken är PCI-granskad eller byggd för det. Spärren mot testkortslistan gör
 * det omöjligt, inte olämpligt. Motiveringen i sin helhet: lib/betalning.ts.
 *
 * ## Vad som lämnar webbläsaren
 *
 * Märke, fyra sista och giltighetstid. Kortnumret och CVC finns bara i det här
 * komponenttillståndet och skickas aldrig vidare — se `spara()`, där
 * `tillKortuppgifter` plockar ut de tre fälten och resten kastas med state.
 */

export function Betalsatt() {
  const [befintligt, setBefintligt] = useState<BetalsattTyp | null | undefined>(undefined);
  const [oppen, setOppen] = useState(false);

  const [nummer, setNummer] = useState("");
  const [manad, setManad] = useState("");
  const [ar, setAr] = useState("");
  const [cvc, setCvc] = useState("");

  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [klart, setKlart] = useState<string | null>(null);

  useEffect(() => {
    let avbruten = false;
    void hamtaBetalsatt().then((rad) => {
      if (!avbruten) setBefintligt(rad);
    });
    return () => {
      avbruten = true;
    };
  }, []);

  function nollstall() {
    setNummer("");
    setManad("");
    setAr("");
    setCvc("");
  }

  async function spara(event: React.FormEvent) {
    event.preventDefault();
    setFel(null);
    setKlart(null);

    const problem = kortfel(nummer, manad, ar, cvc);
    if (problem) {
      setFel(problem);
      return;
    }

    const uppgifter = tillKortuppgifter(nummer, manad, ar);
    if (!uppgifter) {
      setFel("Kortet gick inte att läsa.");
      return;
    }

    setBusy(true);
    try {
      const svar = await sparaBetalsatt(uppgifter);
      if (!svar.success) {
        setFel(svar.error ?? "Kunde inte spara betalsättet.");
        return;
      }
      setBefintligt(svar.betalsatt ?? null);
      setOppen(false);
      // Kortnumret och CVC kastas här, inte när formuläret stängs: stängningen
      // är ett annat klick och kan hoppas över.
      nollstall();
      setKlart("Betalsättet är sparat. Inget har debiterats — testläge.");
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte spara betalsättet.");
    } finally {
      setBusy(false);
    }
  }

  async function taBort() {
    setBusy(true);
    setFel(null);
    setKlart(null);
    try {
      const svar = await taBortBetalsatt();
      if (!svar.success) {
        setFel(svar.error ?? "Kunde inte ta bort betalsättet.");
        return;
      }
      setBefintligt(null);
      setKlart("Betalsättet är borttaget.");
    } finally {
      setBusy(false);
    }
  }

  if (befintligt === undefined) {
    return <div className="h-24 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h2 className="kicker text-mineral">Betalsätt</h2>
        <span className="rounded-input border border-warning/40 bg-warning/10 px-2 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-warning">
          Testläge
        </span>
      </div>

      <p className="max-w-[62ch] text-[0.875rem] leading-6 text-ink/60">
        Ingen betalväxel är inkopplad ännu. Flödet nedan är det riktiga —
        formulär, validering och felväg — men <strong className="font-semibold">
        ingenting debiteras</strong>, och bara testkort tas emot. Skriv aldrig in
        ett riktigt kortnummer här.
      </p>

      {befintligt ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-card border border-ink/15 bg-paper2/50 px-4 py-3.5">
          <CreditCard className="h-5 w-5 shrink-0 text-mineral" aria-hidden />
          <span className="text-[0.9375rem] text-ink">
            {befintligt.brand} •••• {befintligt.last4}
          </span>
          <span className="text-[0.8125rem] text-mineral">
            Giltigt t.o.m. {String(befintligt.exp_month).padStart(2, "0")}/{befintligt.exp_year}
          </span>
          {befintligt.is_test ? (
            <span className="text-[0.75rem] uppercase tracking-[0.14em] text-warning">Test</span>
          ) : null}
          <span className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={() => {
                setOppen(true);
                setKlart(null);
              }}
              className="focus-ring rounded-input px-3 py-1.5 text-[0.8125rem] text-ink/70 hover:bg-paper2 hover:text-ink"
            >
              Byt kort
            </button>
            <button
              type="button"
              onClick={() => void taBort()}
              disabled={busy}
              className="focus-ring inline-flex items-center gap-1.5 rounded-input px-3 py-1.5 text-[0.8125rem] text-danger hover:bg-danger/10"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
              Ta bort
            </button>
          </span>
        </div>
      ) : oppen ? null : (
        <div>
          <button type="button" onClick={() => setOppen(true)} className={btnPrimary}>
            Lägg till kort
          </button>
        </div>
      )}

      {oppen ? (
        <form onSubmit={spara} className="rounded-panel border border-ink/15 bg-paper2/40 p-5">
          <div className="grid grid-cols-12 gap-x-4 gap-y-4">
            <Falt
              label="Kortnummer"
              span="col-span-12"
              value={formateraKortnummer(nummer)}
              onChange={(v) => setNummer(bararSiffror(v).slice(0, 16))}
              placeholder="4242 4242 4242 4242"
              inputMode="numeric"
            />
            <Falt
              label="Månad"
              span="col-span-4"
              value={manad}
              onChange={(v) => setManad(bararSiffror(v).slice(0, 2))}
              placeholder="04"
              inputMode="numeric"
            />
            <Falt
              label="År"
              span="col-span-4"
              value={ar}
              onChange={(v) => setAr(bararSiffror(v).slice(0, 4))}
              placeholder="2030"
              inputMode="numeric"
            />
            {/* CVC skickas ALDRIG till servern. Fältet finns för att flödet ska
                likna det riktiga; värdet lever i state och kastas vid sparning. */}
            <Falt
              label="CVC"
              span="col-span-4"
              value={cvc}
              onChange={(v) => setCvc(bararSiffror(v).slice(0, 4))}
              placeholder="123"
              inputMode="numeric"
            />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button type="submit" disabled={busy} className={btnPrimary}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
              {busy ? "Sparar…" : "Spara kortet"}
            </button>
            <button
              type="button"
              onClick={() => {
                setOppen(false);
                setFel(null);
                nollstall();
              }}
              className={btnSecondary}
            >
              Avbryt
            </button>
          </div>

          {/* Testkorten står UTSKRIVNA. Alternativet är ett fält som avvisar
              allt utan att säga vad det vill ha — och den enda utvägen ur det
              är att prova sitt riktiga kort, vilket är precis det som inte får
              hända. Numren är Stripes publicerade testnummer och kan inte
              debitera någon. */}
          <div className="mt-6 border-t border-ink/15 pt-4">
            <p className="kicker text-mineral">Kort att prova med</p>
            <ul className="mt-3 grid gap-1.5">
              {TESTKORT.map((k) => (
                <li key={k.nummer} className="flex flex-wrap items-baseline gap-x-3 text-[0.8125rem]">
                  <button
                    type="button"
                    onClick={() => setNummer(k.nummer)}
                    className="focus-ring rounded-input font-mono text-ink underline underline-offset-4 hover:text-ochre"
                  >
                    {formateraKortnummer(k.nummer)}
                  </button>
                  <span className="text-mineral">
                    {k.marke} — {k.not}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[0.8125rem] leading-5 text-ink/50">
              Vilken framtida giltighetstid och vilken CVC som helst fungerar.
            </p>
          </div>
        </form>
      ) : null}

      {klart ? (
        <p role="status" className="text-[0.875rem] text-moss">
          {klart}
        </p>
      ) : null}
      {fel ? (
        <p role="alert" className="max-w-[62ch] break-words text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}

function Falt({
  label,
  span,
  value,
  onChange,
  placeholder,
  inputMode
}: Readonly<{
  label: string;
  span: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  inputMode?: "numeric" | "text";
}>) {
  return (
    <label className={`grid gap-2 ${span}`}>
      <span className="kicker text-mineral">{label}</span>
      <input
        className="h-12 rounded-input border border-ink/15 bg-paper px-3 text-[16px] focus:border-ochre"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        inputMode={inputMode}
        // Aldrig autofyll. Webbläsarens sparade kort är kundens RIKTIGA kort,
        // och hela poängen med den här ytan är att ett sådant inte ska kunna
        // hamna i fältet — allra minst utan att någon skrev det.
        autoComplete="off"
      />
    </label>
  );
}
