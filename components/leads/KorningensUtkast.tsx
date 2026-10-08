"use client";

import { Check, ChevronDown, Loader2, PenLine, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { btnLiten, btnPrimary, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { BekraftaUtskick, forstaMening } from "@/components/leads/BekraftaUtskick";

/**
 * En körnings leads med utkaststatus, och två knappar: skriv utkast till de
 * som saknar, och godkänn och skicka alla som väntar.
 *
 * Sebbe 2026-10-07: "Gör det enkelt att skicka utkasten till företagen i
 * listan ... Det ska inte vara svårt." Förut stod körningens leads bara som
 * namn här; utkasten låg i granskningskön utan koppling till körningen och
 * gick att skicka en i taget.
 *
 * Backend: GET/POST /api/leads/korningar/{id}/utkast(/skriv|/skicka).
 * Skicka går genom samma sändspärrar som ett enskilt "Godkänn och skicka".
 *
 * Sebbe 2026-10-07: klicka på ett lead i listan och se dess utkast. Raden
 * fäller ut ämne, mottagare och text på plats; ett lead utan utkast har
 * inget att fälla ut och är ingen knapp. Ett väntande utkast godkänns och
 * skickas därifrån, ett i taget, genom samma väg som granskningen
 * (POST /leads/queue/{id}/approve: tidsgrinden och sändspärrarna), eller
 * avvisas (POST /leads/queue/{id}/reject: utkastet skickas aldrig).
 */

/** Samma härledning som Iris-listan och lådan (snajp-support/app/leads/utkaststatus.py).
 *  `koad`: köat utan mänskligt godkännande (äldre utkast). */
type Status = "vantar" | "godkant" | "koad" | "skickat" | "avvisat" | "stoppat" | "saknas";

type Lead = {
  prospect_id: string;
  company_name: string | null;
  contact_email: string | null;
  kan_mejlas: boolean;
  status: Status;
  /** Granskningskölens post för ett väntande utkast: det som godkänns. */
  queue_item_id?: string | null;
  subject: string | null;
  /** Utkastets text: det väntande utkastet, annars senaste meddelandet. */
  body?: string | null;
  notis: string | null;
};

type Svar = { leads: Lead[]; antal: Partial<Record<Status | "kan_skrivas", number>> };

const STATUS: Record<Status, { etikett: Localized; ton: string }> = {
  vantar: { etikett: { sv: "Utkast väntar", en: "Draft waiting" }, ton: "text-warning" },
  godkant: { etikett: { sv: "Godkänt, skickas 08–16", en: "Approved, sends 08–16" }, ton: "text-ink-muted" },
  koad: { etikett: { sv: "Köat, ej granskat", en: "Queued, not reviewed" }, ton: "text-warning" },
  skickat: { etikett: { sv: "Skickat", en: "Sent" }, ton: "text-moss" },
  avvisat: { etikett: { sv: "Avvisat", en: "Rejected" }, ton: "text-ink-subtle" },
  stoppat: { etikett: { sv: "Stoppat av sändspärr", en: "Stopped by a send guard" }, ton: "text-danger" },
  saknas: { etikett: { sv: "Inget utkast", en: "No draft" }, ton: "text-ink-subtle" }
};

/** Skrivningen tar några minuter per bolag; vyn frågar om läget så länge. */
const POLL_MS = 5000;
const POLL_TAK = 60;

export function KorningensUtkast({ jobId }: Readonly<{ jobId: string }>) {
  const { text } = useLocale();
  const [svar, setSvar] = useState<Svar | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [besked, setBesked] = useState<Localized | null>(null);
  const [pagar, setPagar] = useState<"skriv" | "skicka" | null>(null);
  const [skriver, setSkriver] = useState(0);
  const [oppen, setOppen] = useState<string | null>(null);
  // Vilket utkast som hanteras just nu, och hur: knapparna låses under tiden.
  const [hanterar, setHanterar] = useState<{ id: string; hur: "godkann" | "avvisa" } | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  const bas = `/api/snajp-support/leads/korningar/${encodeURIComponent(jobId)}/utkast`;

  const hamta = useCallback(async (): Promise<Svar | null> => {
    try {
      const response = await fetch(bas, { cache: "no-store" });
      const data = await readJsonBody<Svar & { detail?: string }>(response);
      if (!response.ok || !data) {
        setFel({
          sv: `Utkasten kunde inte hämtas (status ${response.status}).`,
          en: `The drafts could not be loaded (status ${response.status}).`
        });
        return null;
      }
      setSvar(data);
      return data;
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
      return null;
    }
  }, [bas]);

  useEffect(() => {
    void hamta();
    return () => {
      if (poll.current) clearTimeout(poll.current);
    };
  }, [hamta]);

  function pollaTillsKlart(forsok = 0) {
    poll.current = setTimeout(async () => {
      const data = await hamta();
      const kvar = data?.antal.kan_skrivas ?? 0;
      if (kvar > 0 && forsok < POLL_TAK) pollaTillsKlart(forsok + 1);
      else setSkriver(0);
    }, POLL_MS);
  }

  async function skriv() {
    setPagar("skriv");
    setFel(null);
    setBesked(null);
    try {
      const response = await fetch(`${bas}/skriv`, { method: "POST" });
      const data = await readJsonBody<{ count?: number; detail?: string }>(response);
      if (!response.ok) {
        const orsak = typeof data?.detail === "string" ? data.detail : `status ${response.status}`;
        setFel({ sv: `Utkasten kunde inte startas (${orsak}).`, en: `The drafts could not be started (${orsak}).` });
        return;
      }
      const antal = data?.count ?? 0;
      setSkriver(antal);
      setBesked({
        sv: `Iris skriver ${antal} utkast. De dyker upp här när de är klara, några minuter per bolag.`,
        en: `Iris is writing ${antal} drafts. They appear here when done, a few minutes per company.`
      });
      if (antal > 0) pollaTillsKlart();
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
    } finally {
      setPagar(null);
    }
  }

  // Bekräftelsen med mottagarlistan (kritik 3) i stället för confirm-rutan.
  const [bekrafta, setBekrafta] = useState(false);

  async function skicka() {
    setBekrafta(false);
    setPagar("skicka");
    setFel(null);
    setBesked(null);
    try {
      const response = await fetch(`${bas}/skicka`, { method: "POST" });
      const data = await readJsonBody<{
        skickade?: number;
        vantar_pa_fonstret?: number;
        stoppade?: { company_name: string | null; skal: string | null }[];
        detail?: string;
      }>(response);
      if (!response.ok || !data) {
        const orsak = typeof data?.detail === "string" ? data.detail : `status ${response.status}`;
        setFel({ sv: `Utkasten kunde inte skickas (${orsak}).`, en: `The drafts could not be sent (${orsak}).` });
        return;
      }
      const skickade = data.skickade ?? 0;
      const vantar = data.vantar_pa_fonstret ?? 0;
      const stoppade = data.stoppade ?? [];
      setBesked({
        sv: [
          `${skickade} skickade`,
          vantar ? `${vantar} skickas när sändfönstret öppnar (vardagar 08–16)` : null
        ]
          .filter(Boolean)
          .join(", ") + ".",
        en: [`${skickade} sent`, vantar ? `${vantar} go out when the sending window opens (weekdays 08–16)` : null]
          .filter(Boolean)
          .join(", ") + "."
      });
      if (stoppade.length) {
        const lista = stoppade.map((s) => `${s.company_name ?? "?"}${s.skal ? `: ${s.skal}` : ""}`).join("; ");
        setFel({
          sv: `${stoppade.length} stoppades av en sändspärr. ${lista}`,
          en: `${stoppade.length} were stopped by a send guard. ${lista}`
        });
      }
      await hamta();
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
    } finally {
      setPagar(null);
    }
  }

  async function godkann(l: Lead) {
    if (!l.queue_item_id) return;
    setHanterar({ id: l.prospect_id, hur: "godkann" });
    setFel(null);
    setBesked(null);
    const mottagare = l.contact_email ?? l.company_name ?? "";
    try {
      const response = await fetch(`/api/snajp-support/leads/queue/${encodeURIComponent(l.queue_item_id)}/approve`, {
        method: "POST"
      });
      const data = await readJsonBody<{ utfall?: string; besked?: string; detail?: string }>(response);
      if (!response.ok || !data) {
        const orsak = typeof data?.detail === "string" ? data.detail : `status ${response.status}`;
        setFel({ sv: `Utkastet kunde inte skickas (${orsak}).`, en: `The draft could not be sent (${orsak}).` });
        return;
      }
      if (data.utfall === "sent") {
        setBesked({ sv: `Skickat till ${mottagare}.`, en: `Sent to ${mottagare}.` });
      } else if (data.utfall === "requeued") {
        setBesked({
          sv: `Godkänt. Mejlet till ${mottagare} skickas när sändfönstret öppnar (vardagar 08–16).`,
          en: `Approved. The email to ${mottagare} goes out when the sending window opens (weekdays 08–16).`
        });
      } else {
        const skal = data.besked?.split(": ").slice(1).join(": ");
        setFel({ sv: `Inte skickat${skal ? `: ${skal}` : "."}`, en: `Not sent${skal ? `: ${skal}` : "."}` });
      }
      setOppen(null);
      await hamta();
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
    } finally {
      setHanterar(null);
    }
  }

  async function avvisa(l: Lead) {
    if (!l.queue_item_id) return;
    setHanterar({ id: l.prospect_id, hur: "avvisa" });
    setFel(null);
    setBesked(null);
    const bolag = l.company_name ?? l.contact_email ?? "";
    try {
      const response = await fetch(`/api/snajp-support/leads/queue/${encodeURIComponent(l.queue_item_id)}/reject`, {
        method: "POST"
      });
      if (!response.ok) {
        setFel({
          sv: `Utkastet kunde inte avvisas (status ${response.status}).`,
          en: `The draft could not be rejected (status ${response.status}).`
        });
        return;
      }
      setBesked({ sv: `Utkastet till ${bolag} är avvisat och skickas inte.`, en: `The draft to ${bolag} is rejected and will not be sent.` });
      setOppen(null);
      await hamta();
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
    } finally {
      setHanterar(null);
    }
  }

  const antal = svar?.antal ?? {};
  const vantar = antal.vantar ?? 0;
  const kanSkrivas = antal.kan_skrivas ?? 0;
  const sammanfattning = (
    [
      ["vantar", { sv: "väntar på dig", en: "waiting for you" }],
      ["skickat", { sv: "skickade", en: "sent" }],
      ["godkant", { sv: "godkända", en: "approved" }],
      ["saknas", { sv: "utan utkast", en: "without a draft" }]
    ] as [Status, Localized][]
  )
    .filter(([s]) => (antal[s] ?? 0) > 0)
    .map(([s, etikett]) => `${antal[s]} ${text(etikett)}`)
    .join(" · ");

  return (
    <section aria-labelledby={`utkast-${jobId}`}>
      <h3 id={`utkast-${jobId}`} className={rubrikPanel}>
        {text({ sv: "Leads och utkast", en: "Leads and drafts" })}
      </h3>
      {svar && sammanfattning ? <p className={cn(meta, "mt-1")}>{sammanfattning}</p> : null}

      {svar && (vantar > 0 || kanSkrivas > 0) ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {vantar > 0 ? (
            <button
              type="button"
              disabled={pagar !== null}
              onClick={() => setBekrafta(true)}
              className={cn(btnPrimary, btnLiten)}
            >
              {pagar === "skicka" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Check className="h-4 w-4" aria-hidden />
              )}
              {text({ sv: `Godkänn och skicka alla ${vantar}`, en: `Approve and send all ${vantar}` })}
            </button>
          ) : null}
          {kanSkrivas > 0 ? (
            <button
              type="button"
              disabled={pagar !== null || skriver > 0}
              onClick={() => void skriv()}
              className={cn(btnSecondary, btnLiten)}
            >
              {pagar === "skriv" || skriver > 0 ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <PenLine className="h-4 w-4" aria-hidden />
              )}
              {skriver > 0
                ? text({ sv: "Iris skriver…", en: "Iris is writing…" })
                : text({ sv: `Skriv utkast till ${kanSkrivas} som saknar utkast`, en: `Write drafts for ${kanSkrivas} missing` })}
            </button>
          ) : null}
        </div>
      ) : null}

      {bekrafta && svar ? (
        <div className="mt-3">
          <BekraftaUtskick
            poster={svar.leads
              .filter((l) => l.status === "vantar")
              .map((l) => ({
                id: l.prospect_id,
                bolag: l.company_name,
                mottagare: l.contact_email,
                amne: l.subject,
                utdrag: forstaMening(l.body)
              }))}
            upptagen={pagar === "skicka"}
            onBekrafta={() => void skicka()}
            onAvbryt={() => setBekrafta(false)}
          />
        </div>
      ) : null}

      <div aria-live="polite">
        {besked ? <p className="mt-3 max-w-[70ch] text-[0.875rem] text-moss">{text(besked)}</p> : null}
        {fel ? (
          <p role="alert" className="mt-3 max-w-[70ch] text-[0.875rem] text-danger">
            {text(fel)}
          </p>
        ) : null}
      </div>

      {svar === null && !fel ? (
        <p className={cn(meta, "mt-3")}>{text({ sv: "Hämtar utkasten…", en: "Loading the drafts…" })}</p>
      ) : svar && svar.leads.length === 0 ? (
        <p className={cn(meta, "mt-3")}>{text({ sv: "Inga leads i körningen.", en: "No leads in this run." })}</p>
      ) : svar ? (
        <ul className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
          {svar.leads.map((l) => {
            const harUtkast = Boolean(l.subject || l.body);
            const oppnad = harUtkast && oppen === l.prospect_id;
            const rubrikrad = (
              <div className="flex items-baseline justify-between gap-3">
                <span className="flex min-w-0 items-baseline gap-1.5">
                  <span className="min-w-0 truncate font-medium">{l.company_name ?? l.prospect_id}</span>
                  {harUtkast ? (
                    <ChevronDown
                      aria-hidden
                      className={cn("h-3.5 w-3.5 shrink-0 self-center text-ink-subtle transition-transform", oppnad && "rotate-180")}
                    />
                  ) : null}
                </span>{" "}
                <span className={cn("shrink-0 text-[0.8125rem] font-medium", STATUS[l.status].ton)}>
                  {text(STATUS[l.status].etikett)}
                </span>
              </div>
            );
            const undertext =
              l.status === "saknas" ? (
                l.notis ? <p className={cn(meta, "mt-0.5")}>{l.notis}</p> : null
              ) : l.subject && !oppnad ? (
                <p className={cn(meta, "mt-0.5 truncate")}>
                  {l.subject}
                  {l.contact_email ? ` · ${l.contact_email}` : ""}
                </p>
              ) : null;
            return (
              <li key={l.prospect_id} className="py-2.5">
                {harUtkast ? (
                  <button
                    type="button"
                    aria-expanded={oppnad}
                    aria-controls={`utkast-${jobId}-${l.prospect_id}`}
                    onClick={() => setOppen(oppnad ? null : l.prospect_id)}
                    className="focus-ring -mx-1 block w-[calc(100%+0.5rem)] rounded-input px-1 text-left hover:bg-paper2"
                  >
                    {rubrikrad}
                    {undertext}
                  </button>
                ) : (
                  <>
                    {rubrikrad}
                    {undertext}
                  </>
                )}
                {oppnad ? (
                  <div
                    id={`utkast-${jobId}-${l.prospect_id}`}
                    className="mt-2 rounded-input border border-ink/10 bg-paper2 px-4 py-3"
                  >
                    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[0.875rem]">
                      {l.contact_email ? (
                        <>
                          <dt className="text-ink-subtle">{text({ sv: "Till", en: "To" })}</dt>
                          <dd className="min-w-0 break-words">{l.contact_email}</dd>
                        </>
                      ) : null}
                      {l.subject ? (
                        <>
                          <dt className="text-ink-subtle">{text({ sv: "Ämne", en: "Subject" })}</dt>
                          <dd className="min-w-0 break-words font-medium">{l.subject}</dd>
                        </>
                      ) : null}
                    </dl>
                    {l.body ? (
                      <p className="mt-3 max-w-[70ch] whitespace-pre-wrap border-t border-ink/10 pt-3 text-[0.9375rem] leading-6 text-ink">
                        {l.body}
                      </p>
                    ) : (
                      <p className={cn(meta, "mt-3")}>
                        {text({ sv: "Utkastets text gick inte att läsa.", en: "The draft text could not be read." })}
                      </p>
                    )}
                    {l.status === "vantar" && l.queue_item_id ? (
                      <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-ink/10 pt-3">
                        <button
                          type="button"
                          disabled={hanterar !== null || pagar !== null}
                          onClick={() => void godkann(l)}
                          className={cn(btnPrimary, btnLiten)}
                        >
                          {hanterar?.id === l.prospect_id && hanterar.hur === "godkann" ? (
                            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                          ) : (
                            <Check className="h-4 w-4" aria-hidden />
                          )}
                          {text({ sv: "Godkänn och skicka", en: "Approve and send" })}
                        </button>
                        <button
                          type="button"
                          disabled={hanterar !== null || pagar !== null}
                          onClick={() => void avvisa(l)}
                          className={cn(btnSecondary, btnLiten)}
                        >
                          {hanterar?.id === l.prospect_id && hanterar.hur === "avvisa" ? (
                            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                          ) : (
                            <X className="h-4 w-4" aria-hidden />
                          )}
                          {text({ sv: "Avvisa", en: "Reject" })}
                        </button>
                        <span className={meta}>
                          {text({
                            sv: "Går genom sändspärrarna; utanför vardagar 08–16 skickas det när fönstret öppnar.",
                            en: "Passes the send guards; outside weekdays 08–16 it goes out when the window opens."
                          })}
                        </span>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
