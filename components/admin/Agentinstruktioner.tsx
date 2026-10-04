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
import { ADMIN, a, ordagrant } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";
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
  const [fel, setFel] = useState<Localized | null>(null);
  const [meddelande, setMeddelande] = useState<Localized | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [vantar, startTransition] = useTransition();
  const { locale, text } = useLocale();

  useEffect(() => {
    let avbruten = false;
    hamtaInstruktioner().then(({ lage: hamtat, error }) => {
      if (avbruten) return;
      if (error) setFel(ordagrant(error));
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
      if (!svar.success)
        return setFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteStrukturera);
      setDokument(svar.dokument ?? "");
      setRedigerat(false);
      setMeddelande(svar.anmarkning ? ordagrant(svar.anmarkning) : ADMIN.forhandsgranskningEjSparad);
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
      if (!svar.success) return setFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteSpara);
      setDokument(svar.dokument ?? "");
      setRedigerat(false);
      setMeddelande(svar.anmarkning ? ordagrant(svar.anmarkning) : ADMIN.sparatAllaKunder);
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
        <span className="sr-only">{a("hamtarInstruktionerna", locale)}</span>
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
          {a("instruktionernaKundeInteHamtas", locale)} {text(fel)}
        </p>
      ) : null}

      <Sektion title={a("vadAgentenLaserNu", locale)}>
        {/* `lage` är null när hämtningen föll. Den grenen MÅSTE finnas för sig:
            föll den ihop med "ingen rad sparad" påstod sidan "Sparad —, sparad
            som den skrevs" med ett tomt datum och ett ensamt brädgårdstecken.
            Trovärdigt, och osant. */}
        <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">
          {!lage ? (
            a("lagetKundeInteLasas", locale)
          ) : lage.fran_fil ? (
            <>
              {a("ingenInstruktionSparad", locale)}{" "}
              <span className="font-mono text-[0.8125rem]">agent-core/AGENTS.md</span>.
            </>
          ) : (
            `${a("sparad", locale)} ${
              lage.uppdaterad
                ? new Date(lage.uppdaterad).toLocaleString("sv-SE")
                : a("oknatDatum", locale)
            }, ${lage.kalla === "ai" ? a("struktureradAvModellen", locale) : a("sparadSomDenSkrevs", locale)}.`
          )}
          {lage?.hash ? (
            <span className="ml-2 font-mono text-[0.8125rem] text-ink-muted">#{lage.hash}</span>
          ) : null}
        </p>
        <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-input border border-ink/15 bg-paper2/50 p-4 text-[0.8125rem] leading-6">
          {lage?.aktiv_text || a("tomtParentes", locale)}
        </pre>
      </Sektion>

      {/* Inga förklarande rader under etiketterna (F-016). Att vänster ruta
          struktureras till den högra står i den högras platshållare, och att
          en handredigering sparas ordagrant står i statusraden under den, som
          ändras när man skriver. Det var samma sak sagt två gånger. */}
      {/* Den enda raden som styr VAD som skrivs här: ton och röst är kundens
          (SOUL, /settings/soul), plattformens instruktioner är policy. */}
      <p className="mt-12 max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">
        {a("policyOchSakerhet", locale)}
      </p>
      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        <section>
          <label htmlFor="rav" className={cn(etikett, "block")}>
            {a("dinaInstruktioner", locale)}
          </label>
          <textarea
            id="rav"
            value={rav}
            maxLength={MAX}
            onChange={(event) => setRav(event.target.value)}
            rows={18}
            className="focus-ring mt-2 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 text-[1rem] leading-6"
            placeholder={text({
              sv: "Agenten svarar för långt i chatten.\nDen ska aldrig lova återbetalning. Det går alltid till en människa.\nSluta inleda varje replik med Hej.",
              en: "The agent answers too long in the chat.\nIt must never promise a refund. That always goes to a person.\nStop opening every reply with Hi."
            })}
          />
          <p className={cn(meta, "num mt-2")}>
            {rav.length} / {MAX} {a("tecken", locale)}
          </p>
        </section>

        <section>
          <label htmlFor="dokument" className={cn(etikett, "block")}>
            {a("vadAgentenKommerLasa", locale)}
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
            placeholder={a("strukturerasNar", locale)}
          />
          <p className={cn(meta, "mt-2")}>
            {redigerat ? a("redigeradForHand", locale) : a("strukturerasAvModellen", locale)}
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
          {a("forhandsgranska", locale)}
        </button>
        <button
          type="button"
          onClick={spara}
          disabled={vantar}
          className={btnPrimary}
        >
          {vantar ? a("sparar", locale) : a("sparaOchAktivera", locale)}
        </button>
        {/* Felet renderas i toppen, inte här: två röda rader för samma fel
            läser som två fel. */}
        {/* aria-live av samma skäl som i Kundprofil: kvittot är enda beskedet
            om att sparandet gick vägen, och utbytt text i en vanlig span läses
            aldrig upp. Elementet renderas ALLTID — en region som tillkommer
            samtidigt som sin text annonseras inte av alla skärmläsare. */}
        <span aria-live="polite" className="text-[0.9375rem] text-ink-muted">
          {meddelande ? text(meddelande) : ""}
        </span>
      </div>

      {/* Varje sparning är en ny version; de inaktiva finns kvar för att en
          körning ska gå att förklara i efterhand. Tabulär data, alltså Tabell. */}
      {lage?.historik?.length ? (
        <Sektion title={a("historik", locale)}>
          <Tabell
            minBredd={480}
            ariaLabel={a("historik", locale)}
            kolumner={[
              { rubrik: a("sparad", locale), bredd: "34%" },
              { rubrik: a("kalla", locale), bredd: "26%" },
              { rubrik: a("teckenRubrik", locale), bredd: "20%", hoger: true },
              { rubrik: a("status", locale), bredd: "20%", hoger: true }
            ]}
          >
            {lage.historik.map((rad) => (
              <tr key={rad.id}>
                <Cell className="num">{new Date(rad.created_at).toLocaleString("sv-SE")}</Cell>
                <Cell>{rad.kalla === "ai" ? a("strukturerad", locale) : a("manuell", locale)}</Cell>
                <Cell hoger>{rad.strukturerad_tecken}</Cell>
                <Cell hoger>{rad.aktiv ? <Badge tone="good">{a("aktiv", locale)}</Badge> : "–"}</Cell>
              </tr>
            ))}
          </Tabell>
        </Sektion>
      ) : null}
    </div>
  );
}
