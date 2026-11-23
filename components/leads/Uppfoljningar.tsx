"use client";

import { ChevronDown } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { SkeletonRows, Talrad, Tomt, btnLiten, btnPrimary, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop, relativTid } from "@/lib/leads/suite";
import { LEADS_UPPDATERADE, meddelaLeadsUppdaterade } from "@/lib/leads/utkast";
import { cn } from "@/lib/utils";

/**
 * Leads › Uppföljningar (Antons beställning 2026-11-22): när uppföljningarna
 * skrivs och var de hamnar. Förut stod de i samma granskningskö som
 * körningarnas första mejl och gick inte att skilja ut. Backend:
 * GET /api/leads/uppfoljningar och POST …/skapa (app/api/leads_uppfoljningar.py).
 *
 * Ordningen är arbetets: det som väntar på ditt ja, det Iris skriver nu, det
 * som är dags, det som kommer, och det som gått ut. Skapa uppföljning skriver
 * en nu för de markerade, genom samma kedja som svepet och alltid till
 * granskning. Förloppet är jobbliggarens, så "Skrivs nu" står kvar efter en
 * omladdning och listan hämtas om tills de är klara.
 */

type Rad = {
  prospect_id: string;
  thread_id: string;
  company_name: string | null;
  contact_email: string | null;
  skickade: number;
  senast_skickat: string | null;
  nummer: number;
  av: number;
  nasta?: string;
  avstangd?: boolean;
  queue_item_id?: string | null;
  ko_status?: string | null;
  subject?: string | null;
  body?: string;
  fel?: string;
};

type Skickad = {
  message_id: string;
  prospect_id: string;
  company_name: string | null;
  contact_email: string | null;
  subject: string | null;
  body: string;
  skickat_at: string;
  nummer: number;
  av: number;
  svarat: boolean;
};

type Lista = {
  vantar: Rad[];
  skrivs: Rad[];
  forfallna: Rad[];
  kommande: Rad[];
  fel: Rad[];
  skickade: Skickad[];
  automatiskt: boolean;
};

const HOPPAD: Record<string, Localized> = {
  inget_skickat: { sv: "har inte fått något mejl än", en: "have not been emailed yet" },
  avslutad: { sv: "har svarat eller är avslutade", en: "have replied or are closed" },
  sekvensen_klar: { sv: "har fått alla uppföljningar", en: "have had every follow-up" },
  skrivs_redan: { sv: "får redan en uppföljning skriven", en: "already have one being written" },
  har_utkast: { sv: "har redan en uppföljning som väntar", en: "already have one waiting" }
};

/** "tors 27 nov.": en uppföljning blir aktuell en dag, inte ett klockslag
 *  (svepet går varje timme, och tiden räknas från förra mejlets minut). */
function datum(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale === "en" ? "en-GB" : "sv-SE", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "Europe/Stockholm"
  });
}

function nummerText(r: { nummer: number; av: number }, text: (v: Localized) => string): string {
  return r.nummer >= r.av
    ? text({ sv: "Sista mejlet", en: "Final email" })
    : text({ sv: `Uppföljning ${r.nummer} av ${r.av - 1}`, en: `Follow-up ${r.nummer} of ${r.av - 1}` });
}

/** Skapa uppföljning för markerade leads. Delas av fliken och listorna. */
export async function skapaUppfoljningar(
  prospektIds: string[],
  text: (v: Localized) => string
): Promise<{ text: string; fel: boolean }> {
  const svar = await leadsAnrop<{ count: number; hoppade: Record<string, string[]> }>("/leads/uppfoljningar/skapa", {
    method: "POST",
    body: JSON.stringify({ prospect_ids: prospektIds })
  });
  meddelaLeadsUppdaterade("uppfoljningar");
  const hoppade = Object.entries(svar.hoppade ?? {})
    .map(([skal, ids]) => `${ids.length} ${text(HOPPAD[skal] ?? { sv: skal, en: skal })}`)
    .join(", ");
  return {
    text:
      text({
        sv: `Iris skriver ${svar.count} ${svar.count === 1 ? "uppföljning" : "uppföljningar"}. De står under Skrivs nu tills de väntar på ditt ja.`,
        en: `Iris is writing ${svar.count} ${svar.count === 1 ? "follow-up" : "follow-ups"}. They show under Writing now until they wait for your yes.`
      }) + (hoppade ? ` ${text({ sv: "Hoppade över:", en: "Skipped:" })} ${hoppade}.` : ""),
    fel: false
  };
}

export function Uppfoljningar({ onValjLead }: Readonly<{ onValjLead?: (prospektId: string) => void }>) {
  const { text, locale } = useLocale();
  const [lista, setLista] = useState<Lista | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [atgard, setAtgard] = useState<string | null>(null);
  const [besked, setBesked] = useState<{ text: string; fel: boolean } | null>(null);
  const [oppen, setOppen] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    try {
      setLista(await leadsAnrop<Lista>("/leads/uppfoljningar"));
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }, []);

  useEffect(() => {
    void hamta();
    const uppdatera = () => void hamta();
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    return () => window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
  }, [hamta]);

  // Medan Iris skriver: hämta om tills de står som väntande.
  const skrivs = lista?.skrivs.length ?? 0;
  useEffect(() => {
    if (!skrivs) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void hamta();
    }, 5000);
    return () => window.clearInterval(id);
  }, [skrivs, hamta]);

  const markerbara = useMemo(() => [...(lista?.forfallna ?? []), ...(lista?.fel ?? []), ...(lista?.kommande ?? [])], [lista]);

  async function skapa() {
    const ids = [...valda];
    if (!ids.length || atgard) return;
    setAtgard("skapa");
    setBesked(null);
    try {
      setBesked(await skapaUppfoljningar(ids, text));
      setValda(new Set());
      await hamta();
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  async function koAtgard(r: Rad, vag: "approve" | "reject") {
    if (!r.queue_item_id || atgard) return;
    setAtgard(`${vag}:${r.prospect_id}`);
    setBesked(null);
    try {
      const svar = await leadsAnrop<{ besked?: string; utfall?: string }>(
        `/leads/queue/${encodeURIComponent(r.queue_item_id)}/${vag}`,
        { method: "POST" }
      );
      setBesked({
        text: vag === "reject" ? text({ sv: "Uppföljningen avvisades.", en: "The follow-up was rejected." }) : (svar.besked ?? ""),
        fel: vag === "approve" && !["sent", "requeued"].includes(svar.utfall ?? "")
      });
      meddelaLeadsUppdaterade("uppfoljningar");
      await hamta();
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  if (lista === null) {
    return fel ? (
      <p role="alert" className="text-[0.9375rem] text-danger">
        {fel}
      </p>
    ) : (
      <SkeletonRows />
    );
  }

  const markerad = (r: Rad) => (
    <label className="-m-2 inline-flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center">
      <input
        type="checkbox"
        checked={valda.has(r.prospect_id)}
        onChange={() =>
          setValda((nu) => {
            const nasta = new Set(nu);
            if (nasta.has(r.prospect_id)) nasta.delete(r.prospect_id);
            else nasta.add(r.prospect_id);
            return nasta;
          })
        }
        aria-label={text({ sv: `Markera ${r.company_name ?? ""}`, en: `Select ${r.company_name ?? ""}` })}
        className="h-4 w-4 accent-ink"
      />
    </label>
  );

  const bolag = (r: { prospect_id: string; company_name: string | null; contact_email: string | null }) => (
    <button
      type="button"
      onClick={() => onValjLead?.(r.prospect_id)}
      className="focus-ring min-w-0 truncate rounded-input text-left text-[0.9375rem] font-medium text-ink hover:underline"
    >
      {r.company_name ?? r.contact_email ?? text({ sv: "Okänt bolag", en: "Unknown company" })}
    </button>
  );

  const allaValda = markerbara.length > 0 && markerbara.every((r) => valda.has(r.prospect_id));

  return (
    <div className="grid gap-8">
      <div>
        <Talrad
          poster={[
            { etikett: text({ sv: "Väntar på ditt ja", en: "Waiting for your yes" }), varde: lista.vantar.length },
            { etikett: text({ sv: "Skrivs nu", en: "Writing now" }), varde: lista.skrivs.length },
            { etikett: text({ sv: "Dags att följa upp", en: "Due now" }), varde: lista.forfallna.length },
            { etikett: text({ sv: "Skickade, 30 dagar", en: "Sent, 30 days" }), varde: lista.skickade.length }
          ]}
        />
        <p className={cn(meta, "mt-3 max-w-[75ch] leading-5")}>
          {lista.automatiskt
            ? text({
                sv: "Iris skriver förfallna uppföljningar en gång i timmen. Varje uppföljning väntar på ditt ja innan den skickas, och ett svar stoppar resten.",
                en: "Iris writes due follow-ups once an hour. Every follow-up waits for your yes before it is sent, and a reply stops the rest."
              })
            : text({
                sv: "Uppföljningar skrivs när du väljer Skapa uppföljning. Varje uppföljning väntar på ditt ja innan den skickas, och ett svar stoppar resten.",
                en: "Follow-ups are written when you choose Create follow-up. Every follow-up waits for your yes before it is sent, and a reply stops the rest."
              })}
        </p>
      </div>

      {besked ? (
        <p role={besked.fel ? "alert" : "status"} className={cn("text-[0.9375rem] leading-6", besked.fel ? "text-danger" : "text-moss")}>
          {besked.text}
        </p>
      ) : null}

      <section aria-labelledby="uppf-vantar">
        <h2 id="uppf-vantar" className={cn(rubrikPanel, "mb-2")}>
          {text({ sv: "Väntar på ditt ja", en: "Waiting for your yes" })}
        </h2>
        {lista.vantar.length === 0 ? (
          <Tomt>{text({ sv: "Ingen uppföljning väntar på granskning.", en: "No follow-up is waiting for review." })}</Tomt>
        ) : (
          <ul className="divide-y divide-ink/12 border-y border-ink/15">
            {lista.vantar.map((r) => (
              <li key={r.prospect_id} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                  <div className="min-w-0">
                    {bolag(r)}
                    <p className={cn(meta, "mt-0.5 truncate")}>
                      {nummerText(r, text)}
                      {r.subject ? ` · ${r.subject}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <button
                      type="button"
                      aria-expanded={oppen === r.prospect_id}
                      onClick={() => setOppen(oppen === r.prospect_id ? null : r.prospect_id)}
                      className={cn(btnSecondary, btnLiten)}
                    >
                      {text({ sv: "Läs", en: "Read" })}
                      <ChevronDown aria-hidden className={cn("h-4 w-4 transition-transform", oppen === r.prospect_id && "rotate-180")} />
                    </button>
                    <button
                      type="button"
                      disabled={atgard !== null || !r.queue_item_id}
                      onClick={() => void koAtgard(r, "approve")}
                      className={cn(btnPrimary, btnLiten)}
                    >
                      {atgard === `approve:${r.prospect_id}` ? text({ sv: "Skickar…", en: "Sending…" }) : text({ sv: "Godkänn och skicka", en: "Approve and send" })}
                    </button>
                    <button
                      type="button"
                      disabled={atgard !== null || !r.queue_item_id}
                      onClick={() => void koAtgard(r, "reject")}
                      className="focus-ring min-h-9 rounded-input px-1 text-[0.875rem] font-medium text-ink-muted underline underline-offset-4 hover:text-danger"
                    >
                      {text({ sv: "Avvisa", en: "Reject" })}
                    </button>
                  </div>
                </div>
                {oppen === r.prospect_id ? (
                  <div className="mt-3 rounded-card border border-ink/12 bg-paper px-4 py-4 sm:px-5">
                    <p className="text-[0.8125rem] text-ink-muted">
                      {text({ sv: "Ämne", en: "Subject" })}: {r.subject || "–"}
                    </p>
                    <p className="mt-3 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{r.body}</p>
                    <button
                      type="button"
                      onClick={() => onValjLead?.(r.prospect_id)}
                      className="focus-ring mt-3 min-h-9 rounded-input text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
                    >
                      {text({ sv: "Redigera i bolagets utkast", en: "Edit in the company's draft" })}
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {lista.skrivs.length ? (
        <section aria-labelledby="uppf-skrivs">
          <h2 id="uppf-skrivs" className={cn(rubrikPanel, "mb-2")}>
            {text({ sv: "Skrivs nu", en: "Writing now" })}
          </h2>
          <ul className="divide-y divide-ink/12 border-y border-ink/15" aria-live="polite">
            {lista.skrivs.map((r) => (
              <li key={r.prospect_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                {bolag(r)}
                <span className="inline-flex items-center gap-2 text-[0.8125rem] text-ink-muted">
                  <span aria-hidden className="h-2 w-2 animate-pulse rounded-full bg-ochre" />
                  {nummerText(r, text)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="uppf-planerade">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h2 id="uppf-planerade" className={rubrikPanel}>
            {text({ sv: "Nästa uppföljning", en: "Next follow-up" })}
          </h2>
          {markerbara.length ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setValda(allaValda ? new Set() : new Set(markerbara.map((r) => r.prospect_id)))}
                className={cn(btnSecondary, btnLiten)}
              >
                {allaValda
                  ? text({ sv: "Avmarkera alla", en: "Clear all" })
                  : text({ sv: `Markera alla (${markerbara.length})`, en: `Select all (${markerbara.length})` })}
              </button>
              <button
                type="button"
                disabled={!valda.size || atgard !== null}
                onClick={() => void skapa()}
                className={cn(btnPrimary, btnLiten)}
              >
                {atgard === "skapa"
                  ? text({ sv: "Skapar…", en: "Creating…" })
                  : text({ sv: `Skapa uppföljning (${valda.size})`, en: `Create follow-up (${valda.size})` })}
              </button>
            </div>
          ) : null}
        </div>
        {markerbara.length === 0 ? (
          <Tomt>
            {text({
              sv: "Inga leads väntar på en uppföljning. När Iris mejl gått ut utan svar står bolagen här, med datumet för nästa.",
              en: "No leads are waiting for a follow-up. When Iris emails go unanswered, the companies show here with the date of the next one."
            })}
          </Tomt>
        ) : (
          <ul className="divide-y divide-ink/12 border-y border-ink/15">
            {markerbara.map((r) => {
              const dags = lista.forfallna.includes(r);
              return (
                <li key={r.prospect_id} className="flex items-start gap-3 py-3">
                  {markerad(r)}
                  <div className="flex min-w-0 flex-1 flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <div className="min-w-0">
                      {bolag(r)}
                      <p className={cn(meta, "mt-0.5")}>
                        {nummerText(r, text)}
                        {r.senast_skickat
                          ? ` · ${text({ sv: "senaste mejlet", en: "last email" })} ${relativTid(r.senast_skickat, locale)}`
                          : ""}
                      </p>
                      {r.fel ? <p className="mt-1 text-[0.8125rem] text-danger">{r.fel}</p> : null}
                    </div>
                    <span className={cn("shrink-0 text-[0.8125rem]", dags ? "font-medium text-warning" : "text-ink-muted")}>
                      {r.avstangd
                        ? text({ sv: "Automatiska uppföljningar av", en: "Automatic follow-ups off" })
                        : dags
                          ? text({ sv: "Dags nu", en: "Due now" })
                          : r.nasta
                            ? text({ sv: `Dags ${datum(r.nasta, locale)}`, en: `Due ${datum(r.nasta, locale)}` })
                            : null}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <details className="border-t border-ink/12 pt-4">
        <summary className={cn(rubrikPanel, "focus-ring w-fit cursor-pointer rounded-input")}>
          {text({ sv: "Skickade uppföljningar", en: "Sent follow-ups" })}{" "}
          <span className="num font-normal tabular-nums text-ink-subtle">{lista.skickade.length}</span>
        </summary>
        {lista.skickade.length === 0 ? (
          <p className={cn(meta, "mt-3")}>{text({ sv: "Inga de senaste 30 dagarna.", en: "None in the last 30 days." })}</p>
        ) : (
          <ul className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {lista.skickade.map((r) => (
              <li key={r.message_id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3">
                <div className="min-w-0">
                  {bolag(r)}
                  <p className={cn(meta, "mt-0.5 truncate")}>
                    {nummerText(r, text)}
                    {r.subject ? ` · ${r.subject}` : ""}
                  </p>
                </div>
                <span className="shrink-0 text-[0.8125rem] text-ink-muted">
                  {r.svarat ? <span className="mr-2 font-medium text-moss">{text({ sv: "Svarat", en: "Replied" })}</span> : null}
                  <time dateTime={r.skickat_at} className="num tabular-nums">
                    {relativTid(r.skickat_at, locale)}
                  </time>
                </span>
              </li>
            ))}
          </ul>
        )}
      </details>
    </div>
  );
}
