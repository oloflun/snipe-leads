"use client";

import { Check, Hand, Loader2, Scissors, Smile, Sparkles, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS, kategori, type Inkorgssvar, type Mail } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Inkorgen: listan till vänster i flödet, valt ärende med agentens utkast
 * under. Utkastet går att redigera innan Godkänn — det som skickas är det
 * du ser i rutan, inte en osynlig originalversion.
 */

/**
 * Omformuleringsknapparna vid Godkänn & skicka. Varje knapp skriver om texten
 * SOM DEN STÅR I RUTAN (inklusive egna redigeringar) via
 * /drafts/{id}/omformulera — inget skickas och det sparade utkastet rörs
 * inte; resultatet landar i rutan och blir verkligt först vid Godkänn.
 */
const OMFORMULERINGAR = [
  { lage: "forbattra", etikett: "Förbättra", Ikon: Sparkles },
  { lage: "kortare", etikett: "Kortare", Ikon: Scissors },
  { lage: "personligare", etikett: "Mer personlig", Ikon: Smile }
] as const;

const STATUSETIKETT: Record<string, string> = {
  // Backendens status är awaiting_approval (email_pipeline/processor.py) —
  // vyn testade länge mot "awaiting_review", som är LEADS-kös status, och
  // Godkänn-knappen var därför alltid avstängd. Etiketten står kvar för
  // båda ifall gamla svar cachats.
  awaiting_approval: "Väntar på dig",
  awaiting_review: "Väntar på dig",
  new: "Ny",
  processing: "Bearbetas",
  sent: "Skickat",
  rejected: "Avvisat",
  auto_sent: "Skickat",
  approved_and_sent: "Godkänt & skickat",
  escalated: "Eskalerat",
  taken_over: "Övertaget",
  failed: "Föll"
};

function Inkorg() {
  const valtId = useSearchParams().get("id");
  const [mail, setMail] = useState<Mail[] | null>(null);
  const [valt, setValt] = useState<Mail | null>(null);
  const [utkastText, setUtkastText] = useState("");
  const [fel, setFel] = useState<string | null>(null);
  const [pagar, setPagar] = useState<string | null>(null);

  async function hamtaLista() {
    try {
      const svar = await fetch(`${BAS}/inbox?limit=100`).then((s) => readJson<Inkorgssvar>(s));
      setMail(svar?.emails ?? []);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setMail([]);
    }
  }

  async function valj(id: string) {
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/inbox/${id}`).then((s) => readJson<Mail>(s));
      setValt(svar);
      setUtkastText(svar?.draft?.content ?? "");
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }

  useEffect(() => {
    void hamtaLista();
  }, []);

  useEffect(() => {
    if (valtId) void valj(valtId);
  }, [valtId]);

  async function handling(namn: string, gor: () => Promise<Response>) {
    setPagar(namn);
    setFel(null);
    try {
      await readJson(await gor());
      await Promise.all([hamtaLista(), valt ? valj(valt.id) : Promise.resolve()]);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  const kanGodkanna = valt?.draft && valt.status === "awaiting_approval";

  /** Skriv om rutans text i vald riktning. Egen väg i stället för handling():
   *  den hämtar om både listan och ärendet, och en omhämtning här hade
   *  skrivit över precis den text kunden just fick omformulerad. */
  async function omformulera(lage: string) {
    if (!valt?.draft) return;
    setPagar(`omformulera-${lage}`);
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/drafts/${valt.draft.id}/omformulera`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lage, content: utkastText })
      }).then((s) => readJson<{ content: string }>(s));
      if (svar?.content) setUtkastText(svar.content);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader rubrik="Inkorg" />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {mail === null ? (
        <SkeletonRows />
      ) : mail.length === 0 ? (
        <EmptyState title="Inkorgen är tom" />
      ) : (
        <div className="grid gap-10 lg:grid-cols-12">
          <section className="lg:col-span-5" aria-label="Ärendelista">
            <div className="divide-y divide-ink/12 border-y border-ink/15">
              {mail.map((rad) => (
                <button
                  key={rad.id}
                  type="button"
                  onClick={() => void valj(rad.id)}
                  className={cn(
                    "focus-ring block w-full rounded-[4px] py-3 text-left transition-colors hover:bg-paper2/50",
                    valt?.id === rad.id && "bg-paper2/60"
                  )}
                >
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate text-[0.9375rem] font-medium">
                      {rad.subject || "Utan ämnesrad"}
                    </span>
                    <Badge tone={rad.status === "awaiting_approval" ? "warn" : "neutral"}>
                      {STATUSETIKETT[rad.status ?? ""] ?? rad.status ?? "—"}
                    </Badge>
                  </span>
                  <span className="mt-0.5 block truncate text-[0.875rem] text-ink/55">
                    {rad.from_name || rad.from_email || "—"}
                    {rad.classification?.category ? ` · ${kategori(rad.classification.category)}` : ""}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="lg:col-span-7" aria-label="Valt ärende">
            {!valt ? (
              <p className="border-y border-ink/15 py-8 text-[0.9375rem] text-ink-muted">Välj ett ärende.</p>
            ) : (
              <article className="border-y border-ink/15 py-5">
                <h2 className="text-[1.0625rem] font-semibold text-ink">
                  {valt.subject || "Utan ämnesrad"}
                </h2>
                <p className="mt-0.5 text-[0.875rem] text-ink/55">
                  Från: {valt.from_name || "—"}{" "}
                  {valt.from_email ? `<${valt.from_email}>` : ""}
                </p>
                {valt.body ? (
                  <p className="mt-3 max-w-[72ch] whitespace-pre-wrap border-l-[1px] border-ink/15 pl-4 text-[0.9375rem] leading-7 text-ink/70">
                    {valt.body}
                  </p>
                ) : null}

                <h3 className="mt-6 font-display text-[1.125rem]">Agentens utkast</h3>
                {valt.draft ? (
                  <>
                    <textarea
                      value={utkastText}
                      onChange={(e) => setUtkastText(e.target.value)}
                      rows={8}
                      disabled={!kanGodkanna}
                      className="focus-ring mt-2 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6 disabled:opacity-60"
                    />
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        disabled={!kanGodkanna || pagar !== null}
                        onClick={() =>
                          void handling("godkann", () =>
                            fetch(`${BAS}/drafts/${valt.draft!.id}/approve`, {
                              method: "POST",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify(
                                utkastText !== valt.draft!.content
                                  ? { edited_content: utkastText }
                                  : {}
                              )
                            })
                          )
                        }
                        className={cn(btnPrimary, btnLiten)}
                      >
                        {pagar === "godkann" ? (
                          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                        ) : (
                          <Check className="h-4 w-4" aria-hidden />
                        )}
                        Godkänn & skicka
                      </button>
                      <button
                        type="button"
                        disabled={!kanGodkanna || pagar !== null}
                        onClick={() =>
                          void handling("avvisa", () =>
                            fetch(`${BAS}/drafts/${valt.draft!.id}/reject`, { method: "POST" })
                          )
                        }
                        className={cn(btnSecondary, btnLiten)}
                      >
                        <X className="h-4 w-4" aria-hidden />
                        Avvisa
                      </button>
                      <button
                        type="button"
                        disabled={pagar !== null || valt.status === "taken_over"}
                        onClick={() =>
                          void handling("taover", () =>
                            fetch(`${BAS}/inbox/${valt.id}/takeover`, { method: "POST" })
                          )
                        }
                        title="Ta över ärendet och svara själv — agenten rör det inte mer."
                        className={cn(btnSecondary, btnLiten)}
                      >
                        <Hand className="h-4 w-4" aria-hidden />
                        Ta över
                      </button>

                      {/* Omformuleringarna, avskilda från skicka/avvisa med en
                          tunn linje: de ändrar bara texten i rutan, aldrig
                          ärendets tillstånd. */}
                      <span aria-hidden className="mx-1 hidden h-5 w-px bg-ink/15 sm:block" />
                      {OMFORMULERINGAR.map(({ lage, etikett, Ikon }) => (
                        <button
                          key={lage}
                          type="button"
                          disabled={!kanGodkanna || pagar !== null}
                          onClick={() => void omformulera(lage)}
                          title={`Skriv om utkastet: ${etikett.toLowerCase()}. Inget skickas förrän du godkänner.`}
                          className={cn(btnSecondary, btnLiten)}
                        >
                          {pagar === `omformulera-${lage}` ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                          ) : (
                            <Ikon className="h-3.5 w-3.5" aria-hidden />
                          )}
                          {etikett}
                        </button>
                      ))}
                    </div>
                    {!kanGodkanna ? (
                      <p className="mt-2 text-[0.8125rem] text-ink-subtle">Ärendet är redan hanterat.</p>
                    ) : null}
                  </>
                ) : (
                  <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">Inget utkast.</p>
                )}
              </article>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export function InkorgVy() {
  // useSearchParams kräver en Suspense-gräns vid statisk rendering.
  return (
    <Suspense fallback={<SkeletonRows />}>
      <Inkorg />
    </Suspense>
  );
}
