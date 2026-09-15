"use client";

import { Check, Hand, Loader2, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS, type Inkorgssvar, type Mail } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Inkorgen: listan till vänster i flödet, valt ärende med agentens utkast
 * under. Utkastet går att redigera innan Godkänn — det som skickas är det
 * du ser i rutan, inte en osynlig originalversion.
 */

const STATUSETIKETT: Record<string, string> = {
  awaiting_review: "Väntar på dig",
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

  const kanGodkanna = valt?.draft && valt.status === "awaiting_review";

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Inkorg"
        beskrivning="Kundmejlen med agentens föreslagna svar. Godkänn, redigera först, avvisa, eller ta över ärendet helt — sändknappen är alltid din."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {mail === null ? (
        <SkeletonRows />
      ) : mail.length === 0 ? (
        <EmptyState
          title="Inkorgen är tom"
          body="När kundmejl kommer in sorterar agenten dem och lägger sina utkast här."
        />
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
                    <Badge tone={rad.status === "awaiting_review" ? "warn" : "neutral"}>
                      {STATUSETIKETT[rad.status ?? ""] ?? rad.status ?? "—"}
                    </Badge>
                  </span>
                  <span className="mt-0.5 block truncate text-[0.875rem] text-ink/55">
                    {rad.from_name || rad.from_email || "—"}
                    {rad.classification?.category ? ` · ${rad.classification.category}` : ""}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="lg:col-span-7" aria-label="Valt ärende">
            {!valt ? (
              <p className="border-y border-ink/15 py-8 text-[0.9375rem] text-ink/55">
                Välj ett ärende i listan så visas mejlet och agentens utkast här.
              </p>
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
                    </div>
                    {!kanGodkanna ? (
                      <p className="mt-2 text-[0.8125rem] text-ink/50">
                        Ärendet är redan hanterat — utkastet visas som det stod.
                      </p>
                    ) : null}
                  </>
                ) : (
                  <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/55">
                    Inget utkast på det här ärendet — det är eskalerat till en
                    människa eller hanterat på annat håll.
                  </p>
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
