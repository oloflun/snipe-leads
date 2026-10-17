"use client";

/* design · pre-emit critique: P4 H4 E4 S4 R5 V3 — Operate-yta i det låsta systemet
   (DESIGN.md, Tier 0): husets flikar, Sektion, Tabell och knappar, ingen ny riktning. */

import { useEffect, useRef, useState, useTransition } from "react";

import {
  Badge,
  Cell,
  Sektion,
  Tabell,
  btnLiten,
  btnPrimary,
  btnSecondary,
  etikett,
  flik,
  flikAktiv,
  flikInaktiv,
  fliklista,
  meta
} from "@/components/ui";
import { ADMIN, a, ordagrant } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import {
  aterstallInstruktioner,
  forhandsgranskaInstruktioner,
  hamtaInstruktioner,
  sparaInstruktioner,
  type Agentlager,
  type Andring,
  type Bakning,
  type Instruktionslage
} from "@/lib/actions/agentinstruktioner";

const LAGER: { id: Agentlager; namn: keyof typeof ADMIN; om: keyof typeof ADMIN; fil: string }[] = [
  { id: "alla", namn: "lagerAlla", om: "lagerOmAlla", fil: "agent-core/AGENTS.md" },
  { id: "support", namn: "lagerSupport", om: "lagerOmSupport", fil: "agent-core/prompts/support-systemprompt.md" },
  { id: "leads", namn: "lagerLeads", om: "lagerOmLeads", fil: "agent-core/prompts/leads-systemprompt.md" }
];

const TYP: Record<Andring["typ"], { namn: keyof typeof ADMIN; ton: "good" | "warn" | "danger" }> = {
  lagg_till: { namn: "typLaggTill", ton: "good" },
  ersatt: { namn: "typErsatt", ton: "warn" },
  ta_bort: { namn: "typTaBort", ton: "danger" }
};

const KALLA: Record<string, keyof typeof ADMIN> = {
  ai: "strukturerad",
  manuell: "manuell",
  bakad: "kallaBakad",
  aterstalld: "kallaAterstalld"
};

/**
 * Agentinstruktionerna, ett lager per flik: det gemensamma (sanningsreglerna
 * för alla agenter) och varje agents grundprompt.
 *
 * ## Feedback bakas in, den ersätter aldrig
 *
 * Före 2026-10-06 strukturerades vänster ruta till ett NYTT dokument som
 * ersatte det som gällde. En inklistrad utkastmall blev fem rader regler och
 * sanningsreglerna försvann för alla agenter. Nu föreslår modellen ändringar i
 * dokumentet som gäller, koden tillämpar dem, och varje ändring visas här med
 * sitt skäl innan något sparas. Det som sparas är exakt det som visas.
 *
 * ## Stora borttagningar kräver ett extra klick
 *
 * Backenden varnar när ändringarna tar bort mycket. Då är Spara låst tills
 * rutan "Jag har läst borttagningarna" är ikryssad. Det är ett skyddsnät, inte
 * bedömningen: vad som är överflödigt avgör modellen, och godkännandet är ditt.
 */
export function Agentinstruktioner() {
  const [agent, setAgent] = useState<Agentlager>("alla");
  const [lage, setLage] = useState<Instruktionslage | null>(null);
  const [feedback, setFeedback] = useState("");
  const [bakning, setBakning] = useState<Bakning | null>(null);
  const [dokument, setDokument] = useState("");
  const [redigerat, setRedigerat] = useState(false);
  const [lastBorttagning, setLastBorttagning] = useState(false);
  const [fel, setFel] = useState<Localized | null>(null);
  const [meddelande, setMeddelande] = useState<Localized | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [vantar, startTransition] = useTransition();
  const flikRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const { locale, text } = useLocale();

  const lager = LAGER.find((l) => l.id === agent) ?? LAGER[0];
  const tak = lage?.tak ?? 12_000;

  useEffect(() => {
    let avbruten = false;
    setLaddar(true);
    setBakning(null);
    setDokument("");
    setRedigerat(false);
    setFel(null);
    setMeddelande(null);
    hamtaInstruktioner(agent).then(({ lage: hamtat, error }) => {
      if (avbruten) return;
      if (error) setFel(ordagrant(error));
      setLage(hamtat ?? null);
      setLaddar(false);
    });
    return () => {
      avbruten = true;
    };
  }, [agent]);

  function forhandsgranska() {
    setFel(null);
    setMeddelande(null);
    startTransition(async () => {
      const { bakning: svar, error } = await forhandsgranskaInstruktioner(agent, feedback);
      if (error || !svar) return setFel(error ? ordagrant(error) : ADMIN.kundeInteBakaIn);
      setBakning(svar);
      setDokument(svar.dokument);
      setRedigerat(false);
      setLastBorttagning(false);
      setMeddelande(svar.anmarkning ? ordagrant(svar.anmarkning) : ADMIN.forhandsgranskningEjSparad);
    });
  }

  function spara() {
    setFel(null);
    setMeddelande(null);
    startTransition(async () => {
      const svar = await sparaInstruktioner({ agent, feedback, dokument });
      if (!svar.success) return setFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteSpara);
      setFeedback("");
      setBakning(null);
      setDokument("");
      setMeddelande(svar.anmarkning ? ordagrant(svar.anmarkning) : ADMIN.sparatNastaKorning);
      const { lage: nytt } = await hamtaInstruktioner(agent);
      if (nytt) setLage(nytt);
    });
  }

  function aterstall(id: string) {
    setFel(null);
    setMeddelande(null);
    startTransition(async () => {
      const svar = await aterstallInstruktioner(id);
      if (!svar.success) return setFel(svar.error ? ordagrant(svar.error) : ADMIN.kundeInteSpara);
      setMeddelande(ADMIN.aterstalldNastaKorning);
      const { lage: nytt } = await hamtaInstruktioner(agent);
      if (nytt) setLage(nytt);
    });
  }

  const kraverBekraftelse = Boolean(bakning?.varning) && !lastBorttagning;
  const kanSpara = Boolean(bakning) && dokument.trim().length > 0 && dokument.length <= tak && !kraverBekraftelse;

  return (
    <div>
      {/* Flikar: samma understrukna mönster som Leads och Kundtjänst. */}
      <div
        role="tablist"
        aria-label={a("instruktionslager", locale)}
        className={fliklista}
        onKeyDown={(e) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
          e.preventDefault();
          const i = LAGER.findIndex((l) => l.id === agent);
          const nasta =
            e.key === "Home"
              ? LAGER[0]
              : e.key === "End"
                ? LAGER[LAGER.length - 1]
                : LAGER[(i + (e.key === "ArrowRight" ? 1 : LAGER.length - 1)) % LAGER.length];
          setAgent(nasta.id);
          flikRefs.current[nasta.id]?.focus();
        }}
      >
        {LAGER.map((l) => (
          <button
            key={l.id}
            ref={(el) => {
              flikRefs.current[l.id] = el;
            }}
            type="button"
            role="tab"
            id={`flik-${l.id}`}
            aria-selected={agent === l.id}
            aria-controls="lagerpanel"
            tabIndex={agent === l.id ? 0 : -1}
            onClick={() => setAgent(l.id)}
            className={cn(flik, agent === l.id ? flikAktiv : flikInaktiv)}
          >
            {a(l.namn, locale)}
          </button>
        ))}
      </div>

      <div id="lagerpanel" role="tabpanel" aria-labelledby={`flik-${agent}`} className="pt-6">
        <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">{a(lager.om, locale)}</p>

        {/* Felet först, och stort: en tom ruta som egentligen är ett
            rättighetsfel får någon att skriva om instruktionerna i onödan. */}
        {fel ? (
          <p role="alert" className="mt-5 border-t border-danger/40 pt-5 text-[0.9375rem] leading-7 text-ink">
            {a("instruktionernaKundeInteHamtas", locale)} {text(fel)}
          </p>
        ) : null}

        {laddar ? (
          <div className="mt-8 grid gap-8" aria-busy="true" aria-live="polite">
            <span className="sr-only">{a("hamtarInstruktionerna", locale)}</span>
            <div className="h-64 animate-pulse rounded-card bg-ink/[0.055]" />
            <div className="h-48 animate-pulse rounded-card bg-ink/[0.055]" />
          </div>
        ) : (
          <>
            <Sektion title={a("vadAgentenLaserNu", locale)}>
              <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">
                {!lage ? (
                  a("lagetKundeInteLasas", locale)
                ) : lage.fran_fil ? (
                  <>
                    {a("ingenVersionSparad", locale)}{" "}
                    <span className="font-mono text-[0.8125rem]">{lager.fil}</span>.
                  </>
                ) : (
                  `${a("sparad", locale)} ${
                    lage.uppdaterad ? new Date(lage.uppdaterad).toLocaleString("sv-SE") : a("oknatDatum", locale)
                  }, ${a(KALLA[lage.kalla] ?? "manuell", locale).toLowerCase()}.`
                )}
                {lage?.hash ? <span className="ml-2 font-mono text-[0.8125rem]">#{lage.hash}</span> : null}
              </p>
              <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-input border border-ink/15 bg-paper2/50 p-4 text-[0.8125rem] leading-6">
                {lage?.aktiv_text || a("tomtParentes", locale)}
              </pre>
            </Sektion>

            <section className="mt-12">
              <label htmlFor="feedback" className={cn(etikett, "block")}>
                {a("dinFeedback", locale)}
              </label>
              <textarea
                id="feedback"
                value={feedback}
                maxLength={20_000}
                onChange={(event) => {
                  setFeedback(event.target.value);
                  setBakning(null);
                }}
                rows={8}
                className="focus-ring mt-2 w-full max-w-[90ch] resize-y rounded-input border border-ink/15 bg-paper p-4 text-[1rem] leading-6"
                placeholder={text({
                  sv: "Utkasten öppnar för ofta med var bolaget ligger. Börja med något ur deras egna sidor.\nAnvänd den här mallen som struktur: …",
                  en: "The drafts too often open with where the company is located. Start with something from their own pages.\nUse this template as structure: …"
                })}
              />
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={forhandsgranska}
                  disabled={vantar || !feedback.trim()}
                  className={btnSecondary}
                >
                  {vantar && !bakning ? a("sparar", locale) : a("forhandsgranska", locale)}
                </button>
                {!bakning && feedback.trim() ? (
                  <span className={meta}>{a("forhandsgranskaForst", locale)}</span>
                ) : null}
              </div>
            </section>

            {bakning ? (
              <Sektion title={a("andringar", locale)}>
                {bakning.sammanfattning ? (
                  <p className="max-w-[70ch] text-[0.9375rem] leading-7 text-ink">{bakning.sammanfattning}</p>
                ) : null}
                <ol className="mt-4 divide-y divide-ink/12 border-y border-ink/12">
                  {bakning.andringar.map((andring, i) => (
                    <li key={i} className="py-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <Badge tone={TYP[andring.typ].ton}>{a(TYP[andring.typ].namn, locale)}</Badge>
                        {andring.skal ? (
                          <span className="text-[0.9375rem] text-ink-muted">
                            {a("skalKolon", locale)} {andring.skal}
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-3 grid gap-3 lg:grid-cols-2">
                        {andring.typ !== "lagg_till" ? (
                          <div className="min-w-0">
                            <p className={etikett}>{a("fore", locale)}</p>
                            <pre className="mt-1 whitespace-pre-wrap break-words rounded-input bg-danger/[0.06] p-3 text-[0.8125rem] leading-6 text-ink line-through decoration-danger/50">
                              {andring.befintlig}
                            </pre>
                          </div>
                        ) : null}
                        {andring.typ !== "ta_bort" ? (
                          <div className="min-w-0">
                            <p className={etikett}>{a("efter", locale)}</p>
                            <pre className="mt-1 whitespace-pre-wrap break-words rounded-input bg-moss/[0.08] p-3 text-[0.8125rem] leading-6 text-ink">
                              {andring.ny}
                            </pre>
                          </div>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ol>
                {bakning.ej_tillampade.length ? (
                  <div className="mt-6">
                    <p className={etikett}>{a("ejTillampade", locale)}</p>
                    <ul className="mt-2 space-y-2 text-[0.9375rem] leading-7 text-ink-muted">
                      {bakning.ej_tillampade.map((andring, i) => (
                        <li key={i}>
                          {andring.fel} {andring.skal ? `(${andring.skal})` : ""}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <label htmlFor="dokument" className={cn(etikett, "mt-8 block")}>
                  {a("dokumentetEfter", locale)}
                </label>
                <textarea
                  id="dokument"
                  value={dokument}
                  onChange={(event) => {
                    setDokument(event.target.value);
                    setRedigerat(true);
                  }}
                  rows={16}
                  className="focus-ring mt-2 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 font-mono text-[0.8125rem] leading-6"
                />
                <p className={cn(meta, "num mt-2")}>
                  {dokument.length} / {tak} {a("tecken", locale)}
                  {redigerat ? ` · ${a("redigeradForHand", locale)}` : ""}
                </p>

                {bakning.varning ? (
                  <div className="mt-6 border-t border-warning/50 pt-4">
                    <p role="alert" className="max-w-[70ch] text-[0.9375rem] leading-7 text-warning">
                      {bakning.varning}
                    </p>
                    <label className="mt-3 inline-flex min-h-11 items-center gap-3 text-[0.9375rem] text-ink">
                      <input
                        type="checkbox"
                        checked={lastBorttagning}
                        onChange={(event) => setLastBorttagning(event.target.checked)}
                        className="focus-ring size-5 accent-[var(--color-ink)]"
                      />
                      {a("lastBorttagningarna", locale)}
                    </label>
                  </div>
                ) : null}
              </Sektion>
            ) : null}

            <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-ink/15 pt-5">
              <button type="button" onClick={spara} disabled={vantar || !kanSpara} className={btnPrimary}>
                {vantar && bakning ? a("sparar", locale) : a("sparaOchAktivera", locale)}
              </button>
              {/* Kvittot renderas alltid: en region som tillkommer samtidigt
                  som sin text annonseras inte av alla skärmläsare. */}
              <span aria-live="polite" className="text-[0.9375rem] text-ink-muted">
                {meddelande ? text(meddelande) : ""}
              </span>
            </div>

            {lage?.historik?.length ? (
              <Sektion title={a("historik", locale)}>
                <Tabell
                  minBredd={560}
                  ariaLabel={a("historik", locale)}
                  kolumner={[
                    { rubrik: a("sparad", locale), bredd: "26%" },
                    { rubrik: a("kalla", locale), bredd: "22%" },
                    { rubrik: a("feedbackRubrik", locale), bredd: "22%" },
                    { rubrik: a("teckenRubrik", locale), bredd: "12%", hoger: true },
                    { rubrik: a("status", locale), bredd: "18%", hoger: true }
                  ]}
                >
                  {lage.historik.map((rad) => (
                    <tr key={rad.id}>
                      <Cell className="num">{new Date(rad.created_at).toLocaleString("sv-SE")}</Cell>
                      <Cell>{a(KALLA[rad.kalla] ?? "manuell", locale)}</Cell>
                      <Cell>
                        {rad.feedback ? (
                          <details>
                            <summary className="focus-ring cursor-pointer rounded-input text-ink-muted hover:text-ink">
                              {a("visa", locale)}
                            </summary>
                            <p className="mt-2 max-w-[48ch] whitespace-pre-wrap text-[0.875rem] leading-6">
                              {rad.feedback}
                            </p>
                          </details>
                        ) : (
                          "–"
                        )}
                      </Cell>
                      <Cell hoger>{rad.strukturerad_tecken}</Cell>
                      <Cell hoger>
                        {rad.aktiv ? (
                          <Badge tone="good">{a("aktiv", locale)}</Badge>
                        ) : (
                          <button
                            type="button"
                            onClick={() => aterstall(rad.id)}
                            disabled={vantar}
                            className={cn(btnSecondary, btnLiten)}
                          >
                            {a("aterstall", locale)}
                          </button>
                        )}
                      </Cell>
                    </tr>
                  ))}
                </Tabell>
              </Sektion>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
