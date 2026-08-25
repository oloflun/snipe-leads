"use client";

import { useEffect, useState, useTransition } from "react";

import { btnPrimary, btnSecondary } from "@/components/ui";
import {
  forhandsgranskaInstruktioner,
  hamtaInstruktioner,
  sparaInstruktioner,
  type Instruktionslage
} from "@/lib/actions/agentinstruktioner";

const MAX = 12_000;

/**
 * Globala agentinstruktioner.
 *
 * ## Två rutor, inte en
 *
 * Vänster: vad du skriver — löpande text, feedback, "agenten sa X och det var
 * fel". Höger: vad AGENTEN läser — samma innehåll som imperativa regler under
 * fasta rubriker.
 *
 * Två rutor för att de två sakerna faktiskt är olika, och att låtsas att de är
 * samma sak har ett pris: en modell som får en dagbok följer en dagbok. Den
 * högra går att redigera för hand, och gör man det struktureras den inte om —
 * annars hade varje handpåläggning skrivits över nästa gång man sparade.
 *
 * ## Varför "vad agenten läser just nu" står separat
 *
 * Har ingen sparat någon instruktion gäller den incheckade
 * `agent-core/AGENTS.md`. Utan den raden ser en tom vy likadan ut oavsett om
 * agenten körs utan regler eller med filens — och bara det ena är ett problem.
 */
export function Agentinstruktioner() {
  const [lage, setLage] = useState<Instruktionslage | null>(null);
  const [rav, setRav] = useState("");
  const [dokument, setDokument] = useState("");
  const [redigerat, setRedigerat] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [meddelande, setMeddelande] = useState<string | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [vantar, startTransition] = useTransition();

  useEffect(() => {
    let avbruten = false;
    hamtaInstruktioner().then(({ lage: hamtat, error }) => {
      if (avbruten) return;
      if (error) setFel(error);
      if (hamtat) {
        setLage(hamtat);
        setRav(hamtat.ravtext);
        setDokument(hamtat.strukturerad_md);
      }
      setLaddar(false);
    });
    return () => {
      avbruten = true;
    };
  }, []);

  function forhandsgranska() {
    setFel(null);
    setMeddelande(null);
    startTransition(async () => {
      const svar = await forhandsgranskaInstruktioner(rav);
      if (!svar.success) return setFel(svar.error ?? "Kunde inte strukturera texten.");
      setDokument(svar.dokument ?? "");
      setRedigerat(false);
      setMeddelande(svar.anmarkning ?? "Förhandsgranskning. Ingenting är sparat ännu.");
    });
  }

  function spara() {
    setFel(null);
    setMeddelande(null);
    startTransition(async () => {
      // `strukturerad_md` skickas BARA när dokumentet redigerats för hand.
      // Annars strukturerar backenden om råtexten, vilket är det man vill när
      // man ändrat anteckningarna och inte utkastet.
      const svar = await sparaInstruktioner({
        ravtext: rav,
        strukturerad_md: redigerat ? dokument : undefined
      });
      if (!svar.success) return setFel(svar.error ?? "Kunde inte spara.");
      setDokument(svar.dokument ?? "");
      setRedigerat(false);
      setMeddelande(svar.anmarkning ?? "Sparat. Gäller nästa körning, för alla kunder.");
      const { lage: nytt } = await hamtaInstruktioner();
      if (nytt) setLage(nytt);
    });
  }

  if (laddar) {
    // Skelettet speglar den riktiga layouten: statusblock, två fältkolumner,
    // knapprad. En ensam textrad hade krympt ytan till en rad och flyttat
    // allt nedanför när innehållet landade.
    return (
      <div className="grid gap-8" aria-busy="true" aria-live="polite">
        <span className="sr-only">Hämtar instruktionerna</span>
        <div className="h-24 animate-pulse rounded-card bg-ink/[0.055]" />
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="h-96 animate-pulse rounded-card bg-ink/[0.055]" />
          <div className="h-96 animate-pulse rounded-card bg-ink/[0.055]" />
        </div>
        <div className="h-11 w-64 animate-pulse rounded-input bg-ink/[0.055]" />
      </div>
    );
  }

  return (
    <div className="grid gap-8">
      {/* Felet först, och stort. Låg det bara nere vid knapparna kunde sidan
          se ut att ha laddat tomt — och en tom ruta som egentligen är ett
          rättighetsfel får någon att skriva om instruktionerna i onödan. */}
      {fel ? (
        <p role="alert" className="border-t border-danger/40 pt-5 text-[0.9375rem] leading-7 text-ink">
          Instruktionerna kunde inte hämtas: {fel}
        </p>
      ) : null}

      <section className="border-t border-ink/15 pt-5">
        <h2 className="kicker text-mineral">Vad agenten läser just nu</h2>
        {/* `lage` är null när hämtningen föll. Den grenen MÅSTE finnas för sig:
            föll den ihop med "ingen rad sparad" påstod sidan "Sparad —, sparad
            som den skrevs" med ett tomt datum och ett ensamt brädgårdstecken.
            Trovärdigt, och osant. */}
        <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-7 text-ink/65">
          {!lage
            ? "Läget kunde inte läsas."
            : lage.fran_fil
              ? "Ingen instruktion är sparad. Agenten kör på den incheckade agent-core/AGENTS.md."
              : `Sparad ${
                  lage.uppdaterad ? new Date(lage.uppdaterad).toLocaleString("sv-SE") : "okänt datum"
                }, ${lage.kalla === "ai" ? "strukturerad av modellen" : "sparad som den skrevs"}.`}
          {lage?.hash ? (
            <span className="ml-2 font-mono text-[0.8125rem] text-ink/60">#{lage.hash}</span>
          ) : null}
        </p>
        <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-input border border-ink/15 bg-paper2/50 p-4 text-[0.8125rem] leading-6">
          {lage?.aktiv_text || "(tomt)"}
        </pre>
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <label htmlFor="rav" className="kicker text-mineral">
            Dina instruktioner och din feedback
          </label>
          <p className="mt-2 max-w-[60ch] text-[0.9375rem] leading-7 text-ink/65">
            Skriv fritt. Vad agenterna ska och inte ska göra, och vad som gått fel.
            Modellen gör om det till regler när du sparar.
          </p>
          <textarea
            id="rav"
            value={rav}
            maxLength={MAX}
            onChange={(event) => setRav(event.target.value)}
            rows={18}
            className="focus-ring mt-4 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 font-mono text-[1rem] leading-6"
            placeholder={
              "Agenten svarar för långt i chatten.\nDen ska aldrig lova återbetalning. Det går alltid till en människa.\nSluta inleda varje replik med Hej."
            }
          />
          <p className="mt-2 text-[0.8125rem] text-ink/60">
            {rav.length} / {MAX} tecken
          </p>
        </section>

        <section>
          <label htmlFor="dokument" className="kicker text-mineral">
            Vad agenten kommer att läsa
          </label>
          <p className="mt-2 max-w-[60ch] text-[0.9375rem] leading-7 text-ink/65">
            Går att redigera. Rör du texten här sparas den precis som du skrev den.
            Den struktureras inte om.
          </p>
          <textarea
            id="dokument"
            value={dokument}
            maxLength={MAX}
            onChange={(event) => {
              setDokument(event.target.value);
              setRedigerat(true);
            }}
            rows={18}
            className="focus-ring mt-4 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 font-mono text-[1rem] leading-6"
            placeholder="(struktureras när du förhandsgranskar eller sparar)"
          />
          <p className="mt-2 text-[0.8125rem] text-ink/60">
            {redigerat ? "Redigerad för hand, sparas ordagrant." : "Struktureras av modellen."}
          </p>
        </section>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-ink/15 pt-5">
        <button
          type="button"
          onClick={forhandsgranska}
          disabled={vantar || !rav.trim()}
          className={btnSecondary}
        >
          Förhandsgranska
        </button>
        <button
          type="button"
          onClick={spara}
          disabled={vantar}
          className={btnPrimary}
        >
          {vantar ? "Sparar…" : "Spara och aktivera"}
        </button>
        {/* Felet renderas i toppen, inte här: två röda rader för samma fel
            läser som två fel. */}
        {/* aria-live av samma skäl som i Kundprofil: kvittot är enda beskedet
            om att sparandet gick vägen, och utbytt text i en vanlig span läses
            aldrig upp. Elementet renderas ALLTID — en region som tillkommer
            samtidigt som sin text annonseras inte av alla skärmläsare. */}
        <span aria-live="polite" className="text-[0.875rem] text-mineral">
          {meddelande ?? ""}
        </span>
      </div>

      {lage?.historik?.length ? (
        <section className="border-t border-ink/15 pt-5">
          <h2 className="kicker text-mineral">Historik</h2>
          <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-7 text-ink/65">
            Varje sparning är en ny version. Den som är aktiv är den agenten läser;
            de andra finns kvar för att en körning ska gå att förklara i efterhand.
          </p>
          <ul className="mt-4 grid gap-2 text-[0.8125rem]">
            {lage.historik.map((rad) => (
              <li key={rad.id} className="flex flex-wrap gap-x-4 text-ink/65">
                <span className="tabular-nums">
                  {new Date(rad.created_at).toLocaleString("sv-SE")}
                </span>
                <span>{rad.kalla === "ai" ? "strukturerad" : "manuell"}</span>
                <span className="tabular-nums">{rad.strukturerad_tecken} tecken</span>
                {rad.aktiv ? <span className="text-ochre">aktiv</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
