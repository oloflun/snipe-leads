"use client";

import { CreditCard, Loader2, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Sektion, btnPrimary, btnSecondary, etikett, meta } from "@/components/ui";
import { cn } from "@/lib/utils";
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
      setKlart("Betalsättet är sparat. Inget har debiterats, eftersom det är testläge.");
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

  // Sektionen omsluter även laddningsläget, så att rubriken inte hoppar in
  // när kortet väl är hämtat.
  if (befintligt === undefined) {
    return (
      <Sektion title="Betalsätt">
        <div className="h-24 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />
      </Sektion>
    );
  }

  return (
    <Sektion title="Betalsätt" action={<Badge tone="warn">Testläge</Badge>}>
    <div className="grid gap-4">
      {/* EN mening: det användaren måste veta innan hen skriver något. Stycket
          som stod här beskrev dessutom flödet ("formulär, validering och
          felväg"), vilket är sidan som talar om sig själv. */}
      <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
        Vi debiterar ingenting och tar bara emot testkort, så skriv aldrig in ett riktigt
        kortnummer här.
      </p>

      {befintligt ? (
        // Ingen platta under kortraden: knapparna är bg-paper2 och försvann
        // mot en paper2-yta. Hårlinjen räcker för att göra raden till ett objekt.
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-card border border-ink/15 px-4 py-3.5">
          <CreditCard className="h-5 w-5 shrink-0 text-ink-subtle" aria-hidden />
          <span className="text-[0.9375rem] text-ink">
            {befintligt.brand} •••• {befintligt.last4}
          </span>
          <span className={cn(meta, "num")}>
            Giltigt t.o.m. {String(befintligt.exp_month).padStart(2, "0")}/{befintligt.exp_year}
          </span>
          {befintligt.is_test ? <Badge tone="warn">Testkort</Badge> : null}
          <span className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={() => {
                setOppen(true);
                setKlart(null);
              }}
              className={btnSecondary}
            >
              Byt kort
            </button>
            <button
              type="button"
              onClick={() => void taBort()}
              disabled={busy}
              className={btnSecondary}
            >
              <Trash2 className="h-4 w-4" aria-hidden />
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
        <form onSubmit={spara} className="rounded-panel border border-ink/15 p-5">
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
            <p id="testkort-etikett" className={etikett}>
              Kort att prova med
            </p>
            {/* Kortnumret är ett maskin-id och får mono; resten är brödtext. */}
            <ul aria-labelledby="testkort-etikett" className="mt-2 grid gap-1">
              {TESTKORT.map((k) => (
                <li key={k.nummer} className="flex flex-wrap items-center gap-x-3 text-[0.9375rem]">
                  <button
                    type="button"
                    onClick={() => setNummer(k.nummer)}
                    className="focus-ring inline-flex min-h-11 items-center rounded-input font-mono text-[0.8125rem] text-ink underline underline-offset-4 hover:text-ochre"
                  >
                    {formateraKortnummer(k.nummer)}
                  </button>
                  <span className="text-ink-muted">
                    {k.marke}, {k.not}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
              Vilken framtida giltighetstid och vilken CVC som helst fungerar.
            </p>
          </div>
        </form>
      ) : null}

      {klart ? (
        <p role="status" className="text-[0.9375rem] text-moss">
          {klart}
        </p>
      ) : null}
      {fel ? (
        <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
    </Sektion>
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
      <span className={etikett}>{label}</span>
      <input
        className="focus-ring min-h-11 w-full min-w-0 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
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
