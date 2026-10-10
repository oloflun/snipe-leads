"use client";

import { ChevronDown, Clock } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge, SkeletonRows, Tomt, btnPrimary, btnSecondary, chip, chipAktiv, chipInaktiv, chiplista, meta } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop, relativTid } from "@/lib/leads/suite";
import { meddelaLeadsUppdaterade, sandtid } from "@/lib/leads/utkast";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { cn } from "@/lib/utils";
import { ProvmejlKnapp } from "@/components/leads/ProvmejlKnapp";
import { MejlMedSignatur, type Signatur } from "@/components/leads/IrisGranskning";

/**
 * Skickat (Sebbe 2026-10-07, flyttad till Leads › Inkorg › Skickat av Fas 4
 * 2026-10-08): varje leadsmejl som gått ut, med bolaget, mottagaren och hela
 * texten så som den skickades (signatur och lagstadgad fot ingår). Backend:
 * GET /api/leads/skickat.
 *
 * Överst står de godkända som väntar på sändfönstret (`schemalagt`, Sebbe
 * 2026-10-08): Godkänn och skicka flyttar leadet hit direkt, även efter 16:00,
 * med tiden mejlet går ut.
 *
 * De schemalagda går att markera (Anton 2026-10-10): Skicka nu (samma väg som
 * POST /leads/queue/{id}/skicka-nu, går direkt även utanför sändfönstret) eller Ändra tid
 * (POST /leads/queue/schemalagg) för just dem; övrigas tid rörs inte.
 *
 * Varje rad bär leadets NUVARANDE status. Svarshanteringen
 * (snajp-support/app/leads/svar.py) och samtalsutfallen flyttar statusen, så
 * raden byter filter av sig själv: Väntar på svar (kontaktad), Svarat, Möte
 * (möte, vunnen) och Ej intresserad (förlorad, spärrad).
 */

export type SkickatRad = {
  id: string;
  subject: string | null;
  body: string;
  /** null för ett schemalagt utkast: det har inte gått ut än. */
  sent_at: string | null;
  /** Godkänt, väntar på sändfönstret (vardagar 08–16). */
  schemalagt?: boolean;
  /** När ett schemalagt utkast tidigast går ut. */
  skickas_tidigast?: string | null;
  /** Köposten bakom ett schemalagt utkast (provmejlet går på den). */
  queue_item_id?: string | null;
  prospect_id: string | null;
  company_name: string | null;
  contact_name: string | null;
  prospect_email: string | null;
  svarat: boolean;
  /** Leadets nuvarande status (prospects.status). */
  status?: string | null;
};

type Filter = "alla" | "schemalagt" | "vantar" | "svarat" | "mote" | "ej";

const FILTER: { id: Exclude<Filter, "alla">; etikett: Localized; statusar: string[] }[] = [
  { id: "schemalagt", etikett: { sv: "Skickas snart", en: "Scheduled" }, statusar: [] },
  { id: "vantar", etikett: { sv: "Väntar på svar", en: "Awaiting reply" }, statusar: ["contacted"] },
  { id: "svarat", etikett: { sv: "Svarat", en: "Replied" }, statusar: ["replied"] },
  { id: "mote", etikett: { sv: "Möte", en: "Meeting" }, statusar: ["meeting", "won"] },
  { id: "ej", etikett: { sv: "Ej intresserad", en: "Not interested" }, statusar: ["lost", "suppressed"] }
];

/** Filtret en rad hör till. Ett lead vars status inte flyttats (äldre utskick
 *  före 2026-10-07 satte ingen status) väntar fortfarande på svar. */
function filterFor(r: SkickatRad): Exclude<Filter, "alla"> {
  if (r.schemalagt) return "schemalagt";
  return FILTER.find((f) => f.statusar.includes(r.status ?? ""))?.id ?? "vantar";
}

/** Samma färger som Iris-listans statusprick (LeadsTabell.STATUSPRICK):
 *  grönt i hamn, blått på väg mot affär, rött nej, gult kontaktad utan svar. */
const PRICK: Record<string, string> = {
  contacted: "bg-ochre",
  replied: "bg-chart-blue",
  meeting: "bg-chart-blue",
  won: "bg-moss",
  lost: "bg-danger",
  suppressed: "bg-danger"
};

function Antal({ aktiv, children }: Readonly<{ aktiv: boolean; children: React.ReactNode }>) {
  return <span className={cn("num tabular-nums", aktiv ? "text-paper-muted" : "text-ink-subtle")}>{children}</span>;
}

export function SkickatLista({
  rader,
  fel,
  onValj,
  filtrerbar = false,
  provmejl = true,
  signatur = null
}: Readonly<{
  rader: SkickatRad[] | null;
  fel: string | null;
  onValj?: (prospektId: string) => void;
  /** Statusfiltren (Inkorg › Skickat). Demons lista i Iris-listan har dem inte. */
  filtrerbar?: boolean;
  /** Knappen Skicka provmejl på varje rad. Demon har den inte: den skickar på riktigt. */
  provmejl?: boolean;
  /** Signaturen med logotypen, så att mejlet visas så som mottagaren såg det. */
  signatur?: Signatur | null;
}>) {
  const { locale, text } = useLocale();
  const [oppen, setOppen] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("alla");
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [atgard, setAtgard] = useState<{ namn: "skicka" | "tid"; klara?: number } | null>(null);
  const [tidOppen, setTidOppen] = useState(false);
  const [nyTid, setNyTid] = useState("");
  const [besked, setBesked] = useState<{ text: string; orsaker?: string[]; fel: boolean } | null>(null);

  const antal = useMemo(() => {
    const karta = new Map<Filter, number>([["alla", rader?.length ?? 0]]);
    for (const r of rader ?? []) karta.set(filterFor(r), (karta.get(filterFor(r)) ?? 0) + 1);
    return karta;
  }, [rader]);
  const synliga = useMemo(
    () => (rader ?? []).filter((r) => filter === "alla" || filterFor(r) === filter),
    [rader, filter]
  );

  // Bara schemalagda med köpost går att markera, och bara de som syns räknas.
  // `provmejl` är av i demon: där skickas ingenting på riktigt.
  const markerbara = provmejl ? synliga.filter((r) => r.schemalagt && r.queue_item_id) : [];
  const valt = markerbara.filter((r) => valda.has(r.id));
  const allaValda = markerbara.length > 0 && valt.length === markerbara.length;

  function vaxlaVald(id: string) {
    setValda((nu) => {
      const nasta = new Set(nu);
      if (nasta.has(id)) nasta.delete(id);
      else nasta.add(id);
      return nasta;
    });
  }

  /** Skicka nu: en i taget, direkt även utanför sändfönstret (Anton
   *  2026-10-10). Övriga spärrar gäller; ett stopp kommer tillbaka med skäl. */
  async function skickaNu() {
    const poster = valt;
    if (!poster.length || atgard) return;
    if (
      !window.confirm(
        text({
          sv: `Skicka ${poster.length} mejl nu? De går ut direkt, även utanför sändfönstret. Övriga schemalagda skickas på sin vanliga tid.`,
          en: `Send ${poster.length} emails now? They go out right away, even outside the sending window. Other scheduled emails keep their usual time.`
        })
      )
    ) {
      return;
    }
    setBesked(null);
    let skickade = 0;
    let vantar = 0;
    // Stoppen grupperade per orsak, som Iris-listans Skicka utkast.
    const stopp = new Map<string, string[]>();
    for (const [i, r] of poster.entries()) {
      setAtgard({ namn: "skicka", klara: i });
      const bolag = r.company_name ?? r.prospect_email ?? "";
      try {
        const svar = await leadsAnrop<{ utfall?: string; besked?: string; skal?: string | null }>(
          `/leads/queue/${encodeURIComponent(r.queue_item_id ?? "")}/skicka-nu`,
          { method: "POST" }
        );
        if (svar.utfall === "sent") skickade += 1;
        else if (svar.utfall === "requeued") vantar += 1;
        else {
          const skal = svar.skal || svar.besked || svar.utfall || "";
          stopp.set(skal, [...(stopp.get(skal) ?? []), bolag]);
        }
      } catch (orsak) {
        const skal = felmeddelande(orsak);
        stopp.set(skal, [...(stopp.get(skal) ?? []), bolag]);
      }
    }
    const stoppade = [...stopp.values()].reduce((n, b) => n + b.length, 0);
    setAtgard(null);
    setValda(new Set());
    setBesked({
      text: text({
        sv: [
          `${skickade} skickade`,
          vantar ? `${vantar} väntar på sändfönstret (vardagar 08–16)` : null,
          stoppade ? `${stoppade} stoppade` : null
        ].filter(Boolean).join(", ") + ".",
        en: [
          `${skickade} sent`,
          vantar ? `${vantar} waiting for the sending window (weekdays 08–16)` : null,
          stoppade ? `${stoppade} stopped` : null
        ].filter(Boolean).join(", ") + "."
      }),
      orsaker: [...stopp.entries()].map(([skal, bolag]) => `${bolag.length} · ${skal} (${bolag.join(", ")})`),
      fel: stoppade > 0
    });
    meddelaLeadsUppdaterade("skickat");
  }

  /** Ändra tid för de markerade. Tidsgrinden gäller fortfarande: en tid
   *  utanför sändfönstret går ut när fönstret öppnar. */
  async function andraTid() {
    if (!valt.length || !nyTid || atgard) return;
    const tid = new Date(nyTid);
    if (Number.isNaN(tid.getTime())) return;
    setAtgard({ namn: "tid" });
    setBesked(null);
    try {
      const svar = await leadsAnrop<{ andrade?: number; skickas_tidigast?: string | null }>("/leads/queue/schemalagg", {
        method: "POST",
        body: JSON.stringify({ ids: valt.map((r) => r.queue_item_id), tid: tid.toISOString() })
      });
      const nar = svar.skickas_tidigast ? sandtid(svar.skickas_tidigast, locale) : "";
      const andrade = svar.andrade ?? 0;
      setBesked({
        text: text({
          sv: `${andrade} mejl fick ny tid${nar ? `, skickas ${nar}` : ""}. Övriga skickas på sin vanliga tid.`,
          en: `${andrade} emails got a new time${nar ? `, sending ${nar}` : ""}. The others keep their usual time.`
        }),
        fel: false
      });
      setValda(new Set());
      setTidOppen(false);
      setNyTid("");
      meddelaLeadsUppdaterade("skickat");
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  if (fel) {
    return (
      <p role="alert" className="text-[14px] text-danger">
        {fel}
      </p>
    );
  }
  if (rader === null) return <SkeletonRows />;
  if (rader.length === 0) {
    return <Tomt>{text({ sv: "Inga mejl skickade än.", en: "No emails sent yet." })}</Tomt>;
  }

  return (
    <div className="space-y-4">
      {filtrerbar ? (
        <ul className={chiplista} aria-label={text({ sv: "Filtrera skickade mejl", en: "Filter sent emails" })}>
          {([{ id: "alla", etikett: { sv: "Alla", en: "All" } }, ...FILTER] as { id: Filter; etikett: Localized }[])
            // Skickas snart bara när något väntar: annars en nolla som aldrig ändras.
            .filter((f) => f.id !== "schemalagt" || (antal.get("schemalagt") ?? 0) > 0 || filter === "schemalagt")
            .map((f) => (
            <li key={f.id}>
              <button
                type="button"
                aria-pressed={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cn(chip, filter === f.id ? chipAktiv : chipInaktiv)}
              >
                {text(f.etikett)} <Antal aktiv={filter === f.id}>{antal.get(f.id) ?? 0}</Antal>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {markerbara.length > 0 ? (
        <div
          className={cn(
            "flex flex-col gap-3",
            valt.length > 0 && "sticky top-14 z-20 -mx-1 border-b border-ink/12 bg-paper px-1 py-2 lg:top-0"
          )}
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <button
              type="button"
              onClick={() => setValda(allaValda ? new Set() : new Set(markerbara.map((r) => r.id)))}
              className={btnSecondary}
            >
              {allaValda
                ? text({ sv: "Avmarkera alla", en: "Clear all" })
                : text({ sv: `Markera alla schemalagda (${markerbara.length})`, en: `Select all scheduled (${markerbara.length})` })}
            </button>
            {valt.length > 0 ? (
              <>
                <span className="num text-[0.875rem] font-medium">
                  {text({ sv: `${valt.length} markerade`, en: `${valt.length} selected` })}
                </span>
                <button
                  type="button"
                  disabled={atgard !== null}
                  onClick={() => void skickaNu()}
                  className={cn(btnPrimary, "disabled:opacity-60")}
                >
                  {atgard?.namn === "skicka"
                    ? text({ sv: `Skickar ${(atgard.klara ?? 0) + 1} av ${valt.length}…`, en: `Sending ${(atgard.klara ?? 0) + 1} of ${valt.length}…` })
                    : text({ sv: `Skicka nu (${valt.length})`, en: `Send now (${valt.length})` })}
                </button>
                <button
                  type="button"
                  aria-expanded={tidOppen}
                  disabled={atgard !== null}
                  onClick={() => setTidOppen((v) => !v)}
                  className={cn(btnSecondary, "disabled:opacity-60")}
                >
                  {text({ sv: "Ändra tid", en: "Change time" })}
                </button>
              </>
            ) : null}
          </div>
          {tidOppen && valt.length > 0 ? (
            <div className="rounded-card border border-ink/12 bg-paper2/40 p-4">
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex flex-col gap-1 text-[13px] text-ink-muted">
                  {text({ sv: "Ny tid för de markerade", en: "New time for the selected" })}
                  <input
                    type="datetime-local"
                    value={nyTid}
                    onChange={(e) => setNyTid(e.target.value)}
                    className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[15px] text-ink"
                  />
                </label>
                <button
                  type="button"
                  disabled={!nyTid || atgard !== null}
                  onClick={() => void andraTid()}
                  className={cn(btnPrimary, "disabled:opacity-60")}
                >
                  {atgard?.namn === "tid"
                    ? text({ sv: "Sparar…", en: "Saving…" })
                    : text({ sv: `Spara ny tid (${valt.length})`, en: `Save new time (${valt.length})` })}
                </button>
                <button type="button" onClick={() => setTidOppen(false)} className={btnSecondary}>
                  {text({ sv: "Avbryt", en: "Cancel" })}
                </button>
              </div>
              <p className={cn(meta, "mt-2 max-w-[70ch] leading-5")}>
                {text({
                  sv: "Gäller bara de markerade, inom 60 dagar. Övriga skickas på sin vanliga tid. En tid utanför sändfönstret (vardagar 08–16) går ut när fönstret öppnar.",
                  en: "Applies only to the selected, within 60 days. The others keep their usual time. A time outside the sending window (weekdays 08–16) goes out when the window opens."
                })}
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
      {besked ? (
        <div role={besked.fel ? "alert" : "status"} className={cn("text-[0.875rem] leading-6", besked.fel ? "text-danger" : "text-moss")}>
          <p>{besked.text}</p>
          {besked.orsaker?.length ? (
            <ul className="mt-1 list-disc pl-5">
              {besked.orsaker.map((o) => (
                <li key={o}>{o}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {synliga.length === 0 ? (
        <Tomt>{text({ sv: "Inga skickade mejl i det här filtret.", en: "No sent emails in this filter." })}</Tomt>
      ) : (
        <ul className="divide-y divide-ink/12 border-y border-ink/15" aria-label={text({ sv: "Skickade mejl", en: "Sent emails" })}>
          {synliga.map((r) => {
            const oppnad = oppen === r.id;
            const nar = r.sent_at ? new Date(r.sent_at) : null;
            const skickas = r.schemalagt && r.skickas_tidigast ? sandtid(r.skickas_tidigast, locale) : "";
            return (
              <li key={r.id} className="py-3">
                <div className="flex items-start gap-3">
                {markerbara.includes(r) ? (
                  <label className="-m-2 inline-flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center">
                    <input
                      type="checkbox"
                      checked={valda.has(r.id)}
                      onChange={() => vaxlaVald(r.id)}
                      aria-label={text({
                        sv: `Markera ${r.company_name ?? r.prospect_email ?? ""}`,
                        en: `Select ${r.company_name ?? r.prospect_email ?? ""}`
                      })}
                      className="h-4 w-4 accent-ink"
                    />
                  </label>
                ) : null}
                <button
                  type="button"
                  aria-expanded={oppnad}
                  onClick={() => setOppen(oppnad ? null : r.id)}
                  className="focus-ring block min-w-0 flex-1 rounded-input text-left"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="truncate text-[0.9375rem] font-semibold text-ink">
                        {r.company_name ?? text({ sv: "Okänt bolag", en: "Unknown company" })}
                      </p>
                      <p className="mt-0.5 truncate text-[0.875rem] text-ink-muted">
                        {r.subject || text({ sv: "Utan ämnesrad", en: "No subject line" })}
                      </p>
                      <p className={cn(meta, "mt-0.5 truncate")}>
                        {/* Datum och klockslag på raden (Sebbe 2026-10-09: "se när det
                            skickades ut"), den relativa tiden i title. */}
                        {[r.prospect_email].filter(Boolean).join("")}
                        {r.sent_at ? (
                          <>
                            {r.prospect_email ? " · " : null}
                            <time dateTime={r.sent_at} title={relativTid(r.sent_at, locale)} className="num tabular-nums">
                              {text({ sv: "Skickat ", en: "Sent " })}
                              {new Date(r.sent_at).toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
                                day: "numeric",
                                month: "short",
                                hour: "2-digit",
                                minute: "2-digit",
                                timeZone: "Europe/Stockholm"
                              })}
                            </time>
                          </>
                        ) : null}
                      </p>
                    </div>
                    <span className="flex shrink-0 items-center gap-2">
                      {r.schemalagt ? (
                        <span className="inline-flex items-center gap-1.5 text-[0.8125rem] text-ink-muted">
                          <Clock aria-hidden className="h-3.5 w-3.5 shrink-0 text-ochre" />
                          {skickas
                            ? text({ sv: `Skickas ${skickas}`, en: `Sends ${skickas}` })
                            : text({ sv: "Skickas snart", en: "Sending soon" })}
                        </span>
                      ) : r.status && STATUS_ETIKETT[r.status] ? (
                        <span className="inline-flex items-center gap-1.5 text-[0.8125rem] text-ink-muted">
                          <span aria-hidden className={cn("h-2 w-2 shrink-0 rounded-full", PRICK[r.status] ?? "bg-ochre")} />
                          {text(STATUS_ETIKETT[r.status])}
                        </span>
                      ) : r.svarat ? (
                        <Badge tone="good">{text({ sv: "Svarat", en: "Replied" })}</Badge>
                      ) : null}
                      <ChevronDown
                        aria-hidden
                        className={cn("h-4 w-4 text-ink-muted transition-transform", oppnad && "rotate-180")}
                      />
                    </span>
                  </div>
                </button>
                </div>
                {oppnad ? (
                  <div className="mt-3 rounded-card border border-ink/12 bg-paper px-4 py-4 sm:px-5">
                    <dl className="grid gap-1 text-[0.8125rem] sm:grid-cols-[auto_1fr] sm:gap-x-4">
                      <dt className="text-ink-subtle">{text({ sv: "Till", en: "To" })}</dt>
                      <dd className="break-all text-ink">{r.prospect_email ?? "–"}</dd>
                      <dt className="text-ink-subtle">
                        {r.schemalagt ? text({ sv: "Skickas", en: "Sends" }) : text({ sv: "Skickat", en: "Sent" })}
                      </dt>
                      <dd className="num tabular-nums text-ink">
                        {nar
                          ? nar.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
                              dateStyle: "medium",
                              timeStyle: "short",
                              timeZone: "Europe/Stockholm"
                            })
                          : r.skickas_tidigast
                            ? `${new Date(r.skickas_tidigast).toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
                                dateStyle: "medium",
                                timeStyle: "short",
                                timeZone: "Europe/Stockholm"
                              })} ${text({ sv: "(nästa sändfönster, vardagar 08–16)", en: "(next sending window, weekdays 08–16)" })}`
                            : "–"}
                      </dd>
                      <dt className="text-ink-subtle">{text({ sv: "Ämne", en: "Subject" })}</dt>
                      <dd className="text-ink">{r.subject || "–"}</dd>
                    </dl>
                    <MejlMedSignatur
                      body={r.body}
                      signatur={signatur}
                      className="mt-4 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink"
                    />
                    {provmejl ? (
                      <ProvmejlKnapp
                        className="mt-4"
                        queueItemId={r.schemalagt ? (r.queue_item_id ?? null) : null}
                        messageId={r.schemalagt ? null : r.id}
                      />
                    ) : null}
                    {r.prospect_id && onValj ? (
                      <button
                        type="button"
                        onClick={() => onValj(r.prospect_id!)}
                        className="focus-ring mt-4 text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
                      >
                        {text({ sv: "Öppna bolaget", en: "Open the company" })}
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
