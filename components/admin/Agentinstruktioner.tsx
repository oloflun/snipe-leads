"use client";

import { useEffect, useState, useTransition } from "react";

import {
  Badge,
  Cell,
  Sektion,
  Tabell,
  btnPrimary,
  btnSecondary,
  etikett,
  meta
} from "@/components/ui";
import { cn } from "@/lib/utils";
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
    <div>
      {/* Felet först, och stort. Låg det bara nere vid knapparna kunde sidan
          se ut att ha laddat tomt — och en tom ruta som egentligen är ett
          rättighetsfel får någon att skriva om instruktionerna i onödan. */}
      {fel ? (
        <p role="alert" className="border-t border-danger/40 pt-5 text-[0.9375rem] leading-7 text-ink">
          Instruktionerna kunde inte hämtas: {fel}
        </p>
      ) : null}

      <Sektion title="Vad agenten läser just nu">
        {/* `lage` är null när hämtningen föll. Den grenen MÅSTE finnas för sig:
            föll den ihop med "ingen rad sparad" påstod sidan "Sparad —, sparad
            som den skrevs" med ett tomt datum och ett ensamt brädgårdstecken.
            Trovärdigt, och osant. */}
        <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">
          {!lage ? (
            "Läget kunde inte läsas."
          ) : lage.fran_fil ? (
            <>
              Ingen instruktion är sparad. Agenten kör på den incheckade{" "}
              <span className="font-mono text-[0.8125rem]">agent-core/AGENTS.md</span>.
            </>
          ) : (
            `Sparad ${
              lage.uppdaterad ? new Date(lage.uppdaterad).toLocaleString("sv-SE") : "okänt datum"
            }, ${lage.kalla === "ai" ? "strukturerad av modellen" : "sparad som den skrevs"}.`
          )}
          {lage?.hash ? (
            <span className="ml-2 font-mono text-[0.8125rem] text-ink-muted">#{lage.hash}</span>
          ) : null}
        </p>
        <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-input border border-ink/15 bg-paper2/50 p-4 text-[0.8125rem] leading-6">
          {lage?.aktiv_text || "(tomt)"}
        </pre>
      </Sektion>

      {/* Inga förklarande rader under etiketterna (F-016). Att vänster ruta
          struktureras till den högra står i den högras platshållare, och att
          en handredigering sparas ordagrant står i statusraden under den, som
          ändras när man skriver. Det var samma sak sagt två gånger. */}
      {/* Den enda raden som styr VAD som skrivs här: ton och röst är kundens
          (SOUL, /settings/soul), plattformens instruktioner är policy. */}
      <p className="mt-12 max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">
        Här står policy och säkerhet. Ton och röst ställer varje kund in själv.
      </p>
      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        <section>
          <label htmlFor="rav" className={cn(etikett, "block")}>
            Dina instruktioner och din feedback
          </label>
          <textarea
            id="rav"
            value={rav}
            maxLength={MAX}
            onChange={(event) => setRav(event.target.value)}
            rows={18}
            className="focus-ring mt-2 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 text-[1rem] leading-6"
            placeholder={
              "Agenten svarar för långt i chatten.\nDen ska aldrig lova återbetalning. Det går alltid till en människa.\nSluta inleda varje replik med Hej."
            }
          />
          <p className={cn(meta, "num mt-2")}>
            {rav.length} / {MAX} tecken
          </p>
        </section>

        <section>
          <label htmlFor="dokument" className={cn(etikett, "block")}>
            Vad agenten kommer att läsa
          </label>
          <textarea
            id="dokument"
            value={dokument}
            maxLength={MAX}
            onChange={(event) => {
              setDokument(event.target.value);
              setRedigerat(true);
            }}
            rows={18}
            className="focus-ring mt-2 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 text-[1rem] leading-6"
            placeholder="(struktureras när du förhandsgranskar eller sparar)"
          />
          <p className={cn(meta, "mt-2")}>
            {redigerat ? "Redigerad för hand, sparas ordagrant." : "Struktureras av modellen."}
          </p>
        </section>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-ink/15 pt-5">
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
        <span aria-live="polite" className="text-[0.9375rem] text-ink-muted">
          {meddelande ?? ""}
        </span>
      </div>

      {/* Varje sparning är en ny version; de inaktiva finns kvar för att en
          körning ska gå att förklara i efterhand. Tabulär data, alltså Tabell. */}
      {lage?.historik?.length ? (
        <Sektion title="Historik">
          <Tabell
            minBredd={480}
            ariaLabel="Historik"
            kolumner={[
              { rubrik: "Sparad", bredd: "34%" },
              { rubrik: "Källa", bredd: "26%" },
              { rubrik: "Tecken", bredd: "20%", hoger: true },
              { rubrik: "Status", bredd: "20%", hoger: true }
            ]}
          >
            {lage.historik.map((rad) => (
              <tr key={rad.id}>
                <Cell className="num">{new Date(rad.created_at).toLocaleString("sv-SE")}</Cell>
                <Cell>{rad.kalla === "ai" ? "Strukturerad" : "Manuell"}</Cell>
                <Cell hoger>{rad.strukturerad_tecken}</Cell>
                <Cell hoger>{rad.aktiv ? <Badge tone="good">Aktiv</Badge> : "–"}</Cell>
              </tr>
            ))}
          </Tabell>
        </Sektion>
      ) : null}
    </div>
  );
}
