"use client";

import { AlertTriangle, ChevronDown, Mail, Phone, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MejlSvans } from "@/components/leads/IrisGranskning";
import { SkeletonRows, btnLiten, btnPrimary, btnSecondary, etikett, faltTatt, meta, rubrikPanel, rubrikSektion } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { delaCitat } from "@/lib/leads/konversation";
import {
  STEG,
  STEG_ETIKETT,
  STEG_PRICK,
  handelseText,
  meddelaNotiser,
  type Steg,
  type Trad
} from "@/lib/leads/konversationer";
import { UTFALL_ETIKETT, leadsAnrop, relativTid, type Utfall } from "@/lib/leads/suite";
import { meddelaLeadsUppdaterade } from "@/lib/leads/utkast";
import { cn } from "@/lib/utils";

/**
 * En konversation (Leads › Konversationer, Antons beställning 2026-11-22):
 * huvudet med steget, hela tråden i tidsordning och utkaststudion sist, där
 * man svarar. Backend: GET /api/leads/konversationer/{tråd} och åtgärderna
 * under den (app/api/leads_konversationer.py).
 *
 * Tråden: våra mejl, deras svar (citatet hopfällt), mejl skickade utanför
 * Snajp (ur citaten eller inlagda för hand), samtalen, och utkast som
 * kasserats, synliga och möjliga att återställa. Händelseloggen ligger
 * hopfälld under tråden.
 *
 * Utkaststudion: ämne och brödtext redigeras, signaturen och foten är kodens
 * text och visas som mottagaren ser dem. Påstår utkastet att något redan är
 * gjort måste människan bekräfta det innan Skicka går att trycka på.
 */

const T = {
  stegEtikett: { sv: "Steg", en: "Stage" },
  datum: { sv: "Återkom datum", en: "Follow-up date" },
  aterkontakt: { sv: "Återkontakt", en: "Recontact" },
  dagsText: {
    sv: "Dags att höra av sig igen. Datumet för återkontakt har passerat.",
    en: "Time to get back in touch. The recontact date has passed."
  },
  skrivAterkontakt: { sv: "Låt Iris skriva en återkontakt", en: "Let Iris draft a recontact" },
  // Önskemålet till Iris när återkontakten skrivs. Samma väg som Skriv om.
  aterkontaktOnskemal: {
    sv: "Det här är en återkontakt lång tid efter deras svar. Skriv kort. Knyt an till att de bad oss återkomma eller tackade nej då, ge en ny och konkret anledning ur kontextpaketet till att höra av sig nu, och fråga om läget har ändrats. Ingen press, och upprepa inte det förra erbjudandet ordagrant.",
    en: "This is a recontact long after their reply. Keep it short. Refer to them asking us to come back or declining then, give one new, concrete reason from the context pack to get in touch now, and ask whether things have changed. No pressure, and do not repeat the previous offer word for word."
  },
  sparaSteg: { sv: "Spara steg", en: "Save stage" },
  forslagMote: {
    sv: "Ett mejl i tråden säger att en inbjudan har skickats. Är mötet bokat?",
    en: "An email in the thread says an invitation was sent. Is the meeting booked?"
  },
  markeraMote: { sv: "Markera Möte bokat", en: "Mark Meeting booked" },
  vartMejl: { sv: "Vårt mejl", en: "Our email" },
  svarFran: { sv: "Svar från", en: "Reply from" },
  utanfor: { sv: "Skickat utanför Snajp", en: "Sent outside Snajp" },
  utanforIn: { sv: "Mottaget utanför Snajp", en: "Received outside Snajp" },
  urCitat: { sv: "hittat i citatet i ett svar", en: "found in the quote of a reply" },
  inlagt: { sv: "inlagt för hand", en: "added by hand" },
  visaCitat: { sv: "Visa citerad text", en: "Show quoted text" },
  kasserat: { sv: "Kasserat utkast", en: "Discarded draft" },
  aterstall: { sv: "Återställ", en: "Restore" },
  samtal: { sv: "Samtal", en: "Call" },
  handelser: { sv: "Händelselogg", en: "Event log" },
  studio: { sv: "Svarsutkast", en: "Reply draft" },
  amne: { sv: "Ämne", en: "Subject" },
  text: { sv: "Text", en: "Text" },
  skicka: { sv: "Skicka", en: "Send" },
  skickar: { sv: "Skickar…", en: "Sending…" },
  spara: { sv: "Spara", en: "Save" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  sparat: { sv: "Sparat.", en: "Saved." },
  skrivOm: { sv: "Skriv om", en: "Rewrite" },
  kassera: { sv: "Kassera", en: "Discard" },
  onskemal: { sv: "Önskemål till Iris (valfritt)", en: "Instruction for Iris (optional)" },
  starta: { sv: "Skriv ett nytt utkast", en: "Write a new draft" },
  skriver: {
    sv: "Iris skriver ett nytt utkast. Det brukar ta under en minut, och du kan lämna sidan under tiden.",
    en: "Iris is writing a new draft. It usually takes under a minute, and you can leave the page meanwhile."
  },
  handlingRubrik: { sv: "Kontrollera innan du skickar", en: "Check before you send" },
  handlingText: {
    sv: "Utkastet säger att något redan är gjort. Iris kan inte skicka inbjudningar eller bilagor, så det måste en människa ha gjort.",
    en: "The draft says something has already been done. Iris cannot send invitations or attachments, so a person must have done it."
  },
  bekrafta: { sv: "Jag har kontrollerat att det är gjort", en: "I have checked that it is done" },
  ingetUtkast: { sv: "Inget utkast väntar.", en: "No draft is waiting." },
  ingetUtkastText: {
    sv: "Svara från din egen mejl, eller låt Iris skriva ett utkast på det senaste svaret.",
    en: "Reply from your own email, or let Iris draft a reply to the latest one."
  },
  lagg: { sv: "Lägg in ett mejl skickat utanför Snajp", en: "Add an email sent outside Snajp" },
  riktning: { sv: "Riktning", en: "Direction" },
  fran: { sv: "Från oss", en: "From us" },
  till: { sv: "Från dem", en: "From them" },
  nar: { sv: "När", en: "When" },
  laggIn: { sv: "Lägg in", en: "Add" },
  bekraftaKassera: {
    sv: "Kassera utkastet? Det står kvar i tråden och går att återställa.",
    en: "Discard the draft? It stays in the thread and can be restored."
  }
} satisfies Record<string, Localized>;

function tidpunkt(iso: string | null, locale: string): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Stockholm"
  });
}

type Post =
  | { slag: "mejl"; tid: string; m: Trad["meddelanden"][number] }
  | { slag: "extern"; tid: string; e: Trad["externa"][number] }
  | { slag: "samtal"; tid: string; s: Trad["samtal"][number] };

export function KonversationsTrad({
  threadId,
  onAndrad
}: Readonly<{ threadId: string; onAndrad?: () => void }>) {
  const { text, locale } = useLocale();
  const [trad, setTrad] = useState<Trad | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    try {
      setTrad(await leadsAnrop<Trad>(`/leads/konversationer/${encodeURIComponent(threadId)}`));
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }, [threadId]);

  useEffect(() => {
    setTrad(null);
    void hamta();
    // Att öppna tråden är att läsa dess notiser.
    void leadsAnrop(`/leads/konversationer/${encodeURIComponent(threadId)}/last`, { method: "POST" })
      .then(() => {
        meddelaNotiser();
        onAndrad?.();
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  // En omskrivning pågår: hämta tills loggen säger att den är klar. Läget
  // kommer ur händelseloggen, så det står kvar efter en omladdning.
  const pagar = trad?.generering.pagar ?? false;
  useEffect(() => {
    if (!pagar) return;
    const id = window.setInterval(() => void hamta(), 3000);
    return () => window.clearInterval(id);
  }, [pagar, hamta]);

  const andrad = useCallback(async () => {
    await hamta();
    onAndrad?.();
    meddelaLeadsUppdaterade("konversation");
  }, [hamta, onAndrad]);

  const poster = useMemo<Post[]>(() => {
    if (!trad) return [];
    const ut: Post[] = [
      ...trad.meddelanden.filter((m) => m.typ !== "utkast").map((m) => ({ slag: "mejl" as const, tid: m.tid ?? "", m })),
      ...trad.externa.map((e) => ({ slag: "extern" as const, tid: e.tid, e })),
      ...trad.samtal.map((s) => ({ slag: "samtal" as const, tid: s.tid, s }))
    ];
    return ut.sort((a, b) => new Date(a.tid).getTime() - new Date(b.tid).getTime());
  }, [trad]);

  if (fel && !trad) {
    return (
      <p role="alert" className="text-[0.9375rem] text-danger">
        {fel}
      </p>
    );
  }
  if (!trad) return <SkeletonRows />;

  const bolag = trad.trad.company_name ?? trad.trad.contact_email ?? text({ sv: "bolaget", en: "the company" });

  return (
    <article aria-labelledby="konversation-rubrik" className="min-w-0">
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-b border-ink/12 pb-4">
        <div className="min-w-0">
          <h2 id="konversation-rubrik" className={cn(rubrikSektion, "break-words")}>
            {bolag}
          </h2>
          <p className={cn(meta, "mt-1 flex flex-wrap items-center gap-x-3 gap-y-1")}>
            {trad.trad.contact_name ? (
              <span className="text-ink-muted">
                {trad.trad.contact_name}
                {trad.trad.contact_role ? `, ${trad.trad.contact_role}` : ""}
              </span>
            ) : null}
            {trad.trad.contact_email ? (
              <a href={`mailto:${trad.trad.contact_email}`} className="focus-ring inline-flex items-center gap-1 rounded-input hover:text-ink">
                <Mail aria-hidden className="h-3.5 w-3.5" />
                {trad.trad.contact_email}
              </a>
            ) : null}
            {trad.trad.contact_phone ? (
              <a href={`tel:${trad.trad.contact_phone}`} className="focus-ring num inline-flex items-center gap-1 rounded-input tabular-nums hover:text-ink">
                <Phone aria-hidden className="h-3.5 w-3.5" />
                {trad.trad.contact_phone}
              </a>
            ) : null}
          </p>
        </div>
        <StegVal trad={trad} onAndrad={andrad} />
      </header>

      {trad.forslag_mote ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-input border border-ochre/40 bg-ochre/10 px-4 py-3 text-[0.9375rem]">
          <p className="min-w-0 text-ink">{text(T.forslagMote)}</p>
          <SnabbSteg threadId={threadId} steg="mote" etikett={text(T.markeraMote)} onAndrad={andrad} />
        </div>
      ) : null}

      {trad.aterkom_forfallet && !trad.utkast && !trad.generering.pagar ? (
        <Aterkontakt threadId={threadId} harSvar={trad.meddelanden.some((m) => m.typ === "svar")} onAndrad={andrad} />
      ) : null}

      <ol className="mt-5 space-y-3" aria-label={text({ sv: "Konversationen", en: "The conversation" })}>
        {poster.map((p) => (
          <li key={p.slag === "mejl" ? p.m.id : p.slag === "extern" ? p.e.nyckel : p.s.id}>
            {p.slag === "mejl" ? (
              <MejlPost m={p.m} bolag={bolag} till={trad.trad.contact_email} signatur={trad.signatur ?? null} threadId={threadId} onAndrad={andrad} />
            ) : p.slag === "extern" ? (
              <ExternPost e={p.e} />
            ) : (
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-l-2 border-ink/15 py-1 pl-4 text-[0.9375rem]">
                <p className="min-w-0 text-ink">
                  <Phone aria-hidden className="mr-1.5 inline h-3.5 w-3.5 text-ink-muted" />
                  <span className="font-medium">{text(T.samtal)}:</span>{" "}
                  {UTFALL_ETIKETT[p.s.utfall as Utfall] ? text(UTFALL_ETIKETT[p.s.utfall as Utfall]) : p.s.utfall}
                  {p.s.anteckning ? <span className="text-ink-muted"> · {p.s.anteckning}</span> : null}
                </p>
                <time dateTime={p.s.tid} className={cn(meta, "num tabular-nums")}>
                  {tidpunkt(p.s.tid, locale)}
                </time>
              </div>
            )}
          </li>
        ))}
      </ol>

      <UtkastStudio trad={trad} threadId={threadId} onAndrad={andrad} />

      <ExternFormular threadId={threadId} onAndrad={andrad} />

      {trad.handelser.length ? (
        <details className="mt-6 border-t border-ink/12 pt-4">
          <summary className={cn(etikett, "focus-ring w-fit cursor-pointer rounded-input hover:text-ink")}>
            {text(T.handelser)} <span className="num tabular-nums text-ink-subtle">{trad.handelser.length}</span>
          </summary>
          <ul className="mt-3 divide-y divide-ink/10">
            {[...trad.handelser].reverse().map((h) => (
              <li key={h.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 py-2 text-[0.875rem]">
                <span className="min-w-0 text-ink">
                  {h.olast ? <span aria-hidden className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-ochre align-middle" /> : null}
                  {handelseText(h, text)}
                  <span className="text-ink-subtle">
                    {" · "}
                    {h.kalla === "manuell" ? text({ sv: "människa", en: "person" }) : "Iris"}
                  </span>
                </span>
                <time dateTime={h.tid} className={cn(meta, "num tabular-nums")}>
                  {tidpunkt(h.tid, locale)}
                </time>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </article>
  );
}

function MejlPost({
  m,
  bolag,
  till,
  signatur,
  threadId,
  onAndrad
}: Readonly<{
  m: Trad["meddelanden"][number];
  bolag: string;
  till: string | null;
  signatur: Trad["signatur"] | null;
  threadId: string;
  onAndrad: () => Promise<void>;
}>) {
  const { text, locale } = useLocale();
  const [besked, setBesked] = useState<string | null>(null);
  const [arbetar, setArbetar] = useState(false);

  if (m.typ === "kasserat") {
    // Ett kasserat utkast: hopfällt, men synligt och möjligt att ta tillbaka
    // (Anton 2026-11-22: kasseringen ska synas och gå att ångra).
    return (
      <details className="rounded-card border border-dashed border-ink/20 px-4 py-3 sm:px-5">
        <summary className="focus-ring flex cursor-pointer flex-wrap items-baseline justify-between gap-x-4 gap-y-1 rounded-input">
          <span className="min-w-0 text-[0.875rem] text-ink-muted">
            <span className="font-medium text-ink">{text(T.kasserat)}</span>
            {m.subject ? ` · ${m.subject}` : ""}
          </span>
          <span className={cn(meta, "num tabular-nums")}>{tidpunkt(m.kasserad_at ?? m.tid, locale)}</span>
        </summary>
        <p className="mt-3 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink-muted">{m.body}</p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={arbetar}
            onClick={async () => {
              setArbetar(true);
              setBesked(null);
              try {
                await leadsAnrop(`/leads/konversationer/${encodeURIComponent(threadId)}/utkast/${encodeURIComponent(m.id)}/aterstall`, {
                  method: "POST"
                });
                await onAndrad();
              } catch (orsak) {
                setBesked(felmeddelande(orsak));
              } finally {
                setArbetar(false);
              }
            }}
            className={cn(btnSecondary, btnLiten)}
          >
            <RotateCcw aria-hidden className="h-3.5 w-3.5" />
            {text(T.aterstall)}
          </button>
          {besked ? (
            <p role="alert" className="text-[0.875rem] text-danger">
              {besked}
            </p>
          ) : null}
        </div>
      </details>
    );
  }

  const inkommet = m.typ === "svar";
  const [svar, citat] = inkommet ? delaCitat(m.body) : ["", ""];
  return (
    <div
      className={cn(
        "rounded-card border px-4 py-4 sm:px-5",
        inkommet ? "border-chart-blue/30 bg-chart-blue/[0.06]" : "border-ink/12 bg-paper"
      )}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="min-w-0 break-words text-[0.875rem] font-semibold text-ink">
          {inkommet ? `${text(T.svarFran)} ${bolag}` : `${text(T.vartMejl)}${till ? ` · ${till}` : ""}`}
        </p>
        <time dateTime={m.tid ?? undefined} title={relativTid(m.tid, locale)} className={cn(meta, "num tabular-nums")}>
          {tidpunkt(m.tid, locale)}
        </time>
      </div>
      {!inkommet && m.subject ? (
        <p className="mt-1 break-words text-[0.8125rem] text-ink-muted">
          {text(T.amne)}: {m.subject}
        </p>
      ) : null}
      {inkommet ? (
        <>
          <p className="mt-3 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">
            {svar || text({ sv: "Svaret har ingen text.", en: "The reply has no text." })}
          </p>
          {citat ? (
            <details className="mt-3">
              <summary className="focus-ring w-fit cursor-pointer rounded-input text-[0.8125rem] font-medium text-ink-muted hover:text-ink">
                {text(T.visaCitat)}
              </summary>
              <p className="mt-2 whitespace-pre-wrap break-words text-[0.875rem] leading-6 text-ink-muted">{citat}</p>
            </details>
          ) : null}
        </>
      ) : (
        <SkickatMejl body={m.body} signatur={signatur} />
      )}
    </div>
  );
}

/** Vårt skickade mejl: brödtexten, och signaturen och foten hopfällda. I en
 *  tråd står samma signatur under varje mejl; utfälld tog den halva tråden. */
function SkickatMejl({ body, signatur }: Readonly<{ body: string; signatur: Trad["signatur"] | null }>) {
  const { text } = useLocale();
  const sigtext = signatur?.text ?? "";
  const fot = body.indexOf("\n--\n");
  const start = Math.min(...[sigtext ? body.indexOf(sigtext) : -1, fot].filter((i) => i >= 0), body.length);
  const brodtext = body.slice(0, start).trimEnd();
  const svans = body.slice(start).replace(/^\n+/, "");
  return (
    <>
      <p className="mt-3 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{brodtext}</p>
      {svans ? (
        <details className="mt-2">
          <summary className="focus-ring w-fit cursor-pointer rounded-input text-[0.8125rem] font-medium text-ink-muted hover:text-ink">
            {text({ sv: "Visa signatur och fot", en: "Show signature and footer" })}
          </summary>
          <MejlSvans signatur={signatur ?? null} svans={svans} />
        </details>
      ) : null}
    </>
  );
}

function ExternPost({ e }: Readonly<{ e: Trad["externa"][number] }>) {
  const { text, locale } = useLocale();
  return (
    <div className="rounded-card border border-ink/12 bg-paper2/60 px-4 py-4 sm:px-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="min-w-0 break-words text-[0.875rem] font-semibold text-ink">
          {e.riktning === "outbound" ? text(T.utanfor) : text(T.utanforIn)}
          {e.avsandare ? <span className="font-normal text-ink-muted"> · {e.avsandare}</span> : null}
        </p>
        <time dateTime={e.tid} className={cn(meta, "num tabular-nums")}>
          {e.tid_ur_citat || e.kalla === "manuell" ? tidpunkt(e.tid, locale) : text({ sv: "tid okänd", en: "time unknown" })}
        </time>
      </div>
      <p className={cn(meta, "mt-0.5")}>{e.kalla === "citat" ? text(T.urCitat) : text(T.inlagt)}</p>
      {e.amne ? (
        <p className="mt-1 break-words text-[0.8125rem] text-ink-muted">
          {text(T.amne)}: {e.amne}
        </p>
      ) : null}
      <p className="mt-3 whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{e.text}</p>
    </div>
  );
}

function StegVal({ trad, onAndrad }: Readonly<{ trad: Trad; onAndrad: () => Promise<void> }>) {
  const { text } = useLocale();
  const [steg, setSteg] = useState<Steg>(trad.trad.steg);
  const [datum, setDatum] = useState(trad.trad.aterkom_datum ?? "");
  const [arbetar, setArbetar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    setSteg(trad.trad.steg);
    setDatum(trad.trad.aterkom_datum ?? "");
  }, [trad.trad.steg, trad.trad.aterkom_datum]);

  // Återkom kräver ett datum. Ej intresserad får ett av Snajp (sex månader
  // om inget annat valts, Anton 2026-11-23) som går att ändra här.
  const medDatum = steg === "aterkom" || steg === "ej_intresserad";
  const andrat = steg !== trad.trad.steg || (medDatum && datum !== (trad.trad.aterkom_datum ?? ""));

  async function spara() {
    setArbetar(true);
    setFel(null);
    try {
      await leadsAnrop(`/leads/konversationer/${encodeURIComponent(trad.trad.id)}/steg`, {
        method: "POST",
        body: JSON.stringify({ steg, aterkom_datum: medDatum ? datum || null : null })
      });
      await onAndrad();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setArbetar(false);
    }
  }

  return (
    <div className="flex min-w-0 flex-col items-start gap-1.5 sm:items-end">
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1">
          <span className={etikett}>{text(T.stegEtikett)}</span>
          <span className="relative inline-flex items-center">
            <span aria-hidden className={cn("pointer-events-none absolute left-2.5 h-2 w-2 rounded-full", STEG_PRICK[steg])} />
            <select value={steg} onChange={(e) => setSteg(e.target.value as Steg)} className={cn(faltTatt, "pl-6")}>
              {STEG.map((s) => (
                <option key={s} value={s}>
                  {text(STEG_ETIKETT[s])}
                </option>
              ))}
            </select>
          </span>
        </label>
        {medDatum ? (
          <label className="flex flex-col gap-1">
            <span className={etikett}>{text(steg === "aterkom" ? T.datum : T.aterkontakt)}</span>
            <input
              type="date"
              required={steg === "aterkom"}
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
              className={faltTatt}
            />
          </label>
        ) : null}
        {andrat ? (
          <button
            type="button"
            disabled={arbetar || (steg === "aterkom" && !datum)}
            onClick={() => void spara()}
            className={cn(btnPrimary, btnLiten)}
          >
            {arbetar ? text(T.sparar) : text(T.sparaSteg)}
          </button>
        ) : null}
      </div>
      {fel ? (
        <p role="alert" className="text-[0.8125rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}

/** Datumet för återkontakt har passerat: Iris skriver ett utkast på begäran,
 *  genom samma kedja som Skriv om. Inget skrivs eller skickas av sig självt. */
function Aterkontakt({
  threadId,
  harSvar,
  onAndrad
}: Readonly<{ threadId: string; harSvar: boolean; onAndrad: () => Promise<void> }>) {
  const { text } = useLocale();
  const [arbetar, setArbetar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-input border border-ochre/40 bg-ochre/10 px-4 py-3 text-[0.9375rem]">
      <p className="min-w-0 text-ink">{text(T.dagsText)}</p>
      {harSvar ? (
        <span className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={arbetar}
            onClick={async () => {
              setArbetar(true);
              setFel(null);
              try {
                await leadsAnrop(`/leads/konversationer/${encodeURIComponent(threadId)}/utkast/generera`, {
                  method: "POST",
                  body: JSON.stringify({ instruktion: text(T.aterkontaktOnskemal) })
                });
                await onAndrad();
              } catch (orsak) {
                setFel(felmeddelande(orsak));
              } finally {
                setArbetar(false);
              }
            }}
            className={cn(btnSecondary, btnLiten)}
          >
            {text(T.skrivAterkontakt)}
          </button>
          {fel ? <span className="text-[0.8125rem] text-danger">{fel}</span> : null}
        </span>
      ) : null}
    </div>
  );
}

function SnabbSteg({
  threadId,
  steg,
  etikett: knapptext,
  onAndrad
}: Readonly<{ threadId: string; steg: Steg; etikett: string; onAndrad: () => Promise<void> }>) {
  const [arbetar, setArbetar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  return (
    <span className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={arbetar}
        onClick={async () => {
          setArbetar(true);
          try {
            await leadsAnrop(`/leads/konversationer/${encodeURIComponent(threadId)}/steg`, {
              method: "POST",
              body: JSON.stringify({ steg })
            });
            await onAndrad();
          } catch (orsak) {
            setFel(felmeddelande(orsak));
          } finally {
            setArbetar(false);
          }
        }}
        className={cn(btnSecondary, btnLiten)}
      >
        {knapptext}
      </button>
      {fel ? <span className="text-[0.8125rem] text-danger">{fel}</span> : null}
    </span>
  );
}

function UtkastStudio({ trad, threadId, onAndrad }: Readonly<{ trad: Trad; threadId: string; onAndrad: () => Promise<void> }>) {
  const { text, locale } = useLocale();
  const utkast = trad.utkast;
  const [amne, setAmne] = useState(utkast?.subject ?? "");
  const [brodtext, setBrodtext] = useState(utkast?.brodtext ?? "");
  const [bekraftat, setBekraftat] = useState(false);
  const [atgard, setAtgard] = useState<"skicka" | "spara" | "kassera" | "generera" | null>(null);
  const [besked, setBesked] = useState<{ text: string; fel: boolean } | null>(null);
  const [skrivOmOppen, setSkrivOmOppen] = useState(false);
  const [onskemal, setOnskemal] = useState("");
  const [handlingar, setHandlingar] = useState<string[]>(utkast?.handlingar ?? []);
  const forra = useRef(utkast?.message_id);

  // Ett nytt utkast (omskrivet, återställt) ersätter fälten; en egen
  // redigering i samma utkast gör det inte.
  useEffect(() => {
    if (utkast?.message_id !== forra.current) {
      forra.current = utkast?.message_id;
      setAmne(utkast?.subject ?? "");
      setBrodtext(utkast?.brodtext ?? "");
      setHandlingar(utkast?.handlingar ?? []);
      setBekraftat(false);
    }
  }, [utkast]);

  const andrat = Boolean(utkast) && (amne !== utkast?.subject || brodtext !== utkast?.brodtext);
  const sokvag = `/leads/konversationer/${encodeURIComponent(threadId)}/utkast`;

  async function spara(): Promise<boolean> {
    if (!andrat) return true;
    setAtgard("spara");
    try {
      const svar = await leadsAnrop<{ handlingar?: string[] }>(sokvag, {
        method: "PUT",
        body: JSON.stringify({ subject: amne.trim(), brodtext: brodtext.trim() })
      });
      setHandlingar(svar.handlingar ?? []);
      setBesked({ text: text(T.sparat), fel: false });
      await onAndrad();
      return true;
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
      return false;
    } finally {
      setAtgard(null);
    }
  }

  async function skicka() {
    setBesked(null);
    if (!(await spara())) return;
    setAtgard("skicka");
    try {
      const svar = await leadsAnrop<{ utfall: string; besked: string }>(`${sokvag}/skicka`, {
        method: "POST",
        body: JSON.stringify({ bekraftat_handlingar: bekraftat })
      });
      setBesked({ text: svar.besked, fel: !["sent", "requeued"].includes(svar.utfall) });
      await onAndrad();
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  async function kassera() {
    if (!window.confirm(text(T.bekraftaKassera))) return;
    setAtgard("kassera");
    setBesked(null);
    try {
      await leadsAnrop(`${sokvag}/kassera`, { method: "POST" });
      await onAndrad();
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  async function generera() {
    setAtgard("generera");
    setBesked(null);
    try {
      await leadsAnrop(`${sokvag}/generera`, { method: "POST", body: JSON.stringify({ instruktion: onskemal.trim() || null }) });
      setSkrivOmOppen(false);
      setOnskemal("");
      await onAndrad();
    } catch (orsak) {
      setBesked({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  const harSvar = trad.meddelanden.some((m) => m.typ === "svar");
  const kravBekraftelse = handlingar.length > 0 && !bekraftat;

  return (
    <section aria-labelledby="utkaststudio" className="mt-6 rounded-card border border-ink/15 bg-paper p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 id="utkaststudio" className={rubrikPanel}>
          {text(T.studio)}
        </h3>
        {utkast?.tid ? (
          <time dateTime={utkast.tid} className={cn(meta, "num tabular-nums")}>
            {text({ sv: "Skrivet ", en: "Written " })}
            {relativTid(utkast.tid, locale)}
          </time>
        ) : null}
      </div>

      {trad.generering.pagar ? (
        <p role="status" className="mt-3 flex items-center gap-2 text-[0.9375rem] text-ink-muted">
          <span aria-hidden className="h-2 w-2 animate-pulse rounded-full bg-ochre" />
          {text(T.skriver)}
        </p>
      ) : trad.generering.fel ? (
        <p role="alert" className="mt-3 text-[0.9375rem] text-danger">
          {trad.generering.fel}
        </p>
      ) : null}

      {utkast ? (
        <div className="mt-4 grid gap-4">
          <label className="flex flex-col gap-1">
            <span className={etikett}>{text(T.amne)}</span>
            <input value={amne} maxLength={200} onChange={(e) => setAmne(e.target.value)} className={cn(faltTatt, "h-11 w-full")} />
          </label>
          <label className="flex flex-col gap-1">
            <span className={etikett}>{text(T.text)}</span>
            <textarea
              value={brodtext}
              maxLength={8000}
              rows={Math.min(18, Math.max(6, brodtext.split("\n").length + 1))}
              onChange={(e) => setBrodtext(e.target.value)}
              className="focus-ring w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[1rem] leading-7 text-ink hover:border-ink/30"
            />
          </label>
          {utkast.svans ? (
            <details>
              <summary className="focus-ring w-fit cursor-pointer rounded-input text-[0.8125rem] font-medium text-ink-muted hover:text-ink">
                {text({ sv: "Signatur och fot, läggs till av Snajp", en: "Signature and footer, added by Snajp" })}
              </summary>
              <MejlSvans signatur={trad.signatur ?? null} svans={utkast.svans} />
            </details>
          ) : null}

          {handlingar.length ? (
            <div className="rounded-input border border-copper/30 bg-copper/10 px-4 py-3">
              <p className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">
                <AlertTriangle aria-hidden className="h-4 w-4 shrink-0 text-warning" />
                {text(T.handlingRubrik)}
              </p>
              <p className="mt-1 max-w-[65ch] text-[0.875rem] leading-6 text-ink-muted">{text(T.handlingText)}</p>
              <ul className="mt-2 list-disc space-y-0.5 pl-5 text-[0.9375rem] text-ink">
                {handlingar.map((h) => (
                  <li key={h}>"{h}"</li>
                ))}
              </ul>
              <label className="mt-3 flex min-h-11 cursor-pointer items-center gap-2.5 text-[0.9375rem] text-ink">
                <input type="checkbox" checked={bekraftat} onChange={(e) => setBekraftat(e.target.checked)} className="h-4 w-4 accent-ink" />
                {text(T.bekrafta)}
              </label>
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={atgard !== null || kravBekraftelse || trad.generering.pagar}
              onClick={() => void skicka()}
              className={btnPrimary}
            >
              {atgard === "skicka" ? text(T.skickar) : text(T.skicka)}
            </button>
            <button type="button" disabled={!andrat || atgard !== null} onClick={() => void spara()} className={btnSecondary}>
              {atgard === "spara" ? text(T.sparar) : text(T.spara)}
            </button>
            <button
              type="button"
              aria-expanded={skrivOmOppen}
              disabled={atgard !== null || trad.generering.pagar}
              onClick={() => setSkrivOmOppen((v) => !v)}
              className={btnSecondary}
            >
              {text(T.skrivOm)}
              <ChevronDown aria-hidden className={cn("h-4 w-4 transition-transform", skrivOmOppen && "rotate-180")} />
            </button>
            <button
              type="button"
              disabled={atgard !== null}
              onClick={() => void kassera()}
              className="focus-ring ml-auto min-h-11 rounded-input px-2 text-[0.875rem] font-medium text-ink-muted underline underline-offset-4 hover:text-danger"
            >
              {atgard === "kassera" ? "…" : text(T.kassera)}
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[0.9375rem] text-ink">{text(T.ingetUtkast)}</p>
            <p className={cn(meta, "mt-0.5")}>{text(T.ingetUtkastText)}</p>
          </div>
          {harSvar ? (
            <button
              type="button"
              aria-expanded={skrivOmOppen}
              disabled={atgard !== null || trad.generering.pagar}
              onClick={() => setSkrivOmOppen((v) => !v)}
              className={btnSecondary}
            >
              {text(T.starta)}
            </button>
          ) : null}
        </div>
      )}

      {skrivOmOppen ? (
        <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-ink/10 pt-4">
          <label className="flex min-w-0 flex-1 flex-col gap-1">
            <span className={etikett}>{text(T.onskemal)}</span>
            <input
              value={onskemal}
              maxLength={1000}
              onChange={(e) => setOnskemal(e.target.value)}
              placeholder={text({ sv: "Till exempel: föreslå två tider nästa vecka", en: "For example: suggest two times next week" })}
              className={cn(faltTatt, "h-11 w-full")}
            />
          </label>
          <button type="button" disabled={atgard !== null} onClick={() => void generera()} className={btnPrimary}>
            {atgard === "generera" ? "…" : text(utkast ? T.skrivOm : T.starta)}
          </button>
        </div>
      ) : null}

      {besked ? (
        <p role={besked.fel ? "alert" : "status"} className={cn("mt-3 text-[0.9375rem]", besked.fel ? "text-danger" : "text-moss")}>
          {besked.text}
        </p>
      ) : null}
    </section>
  );
}

function ExternFormular({ threadId, onAndrad }: Readonly<{ threadId: string; onAndrad: () => Promise<void> }>) {
  const { text } = useLocale();
  const [oppen, setOppen] = useState(false);
  const [riktning, setRiktning] = useState<"outbound" | "inbound">("outbound");
  const [innehall, setInnehall] = useState("");
  const [nar, setNar] = useState("");
  const [arbetar, setArbetar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  async function lagg() {
    setArbetar(true);
    setFel(null);
    try {
      await leadsAnrop(`/leads/konversationer/${encodeURIComponent(threadId)}/extern`, {
        method: "POST",
        body: JSON.stringify({ riktning, text: innehall.trim(), tid: nar ? new Date(nar).toISOString() : null })
      });
      setInnehall("");
      setNar("");
      setOppen(false);
      await onAndrad();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setArbetar(false);
    }
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        aria-expanded={oppen}
        onClick={() => setOppen((v) => !v)}
        className="focus-ring min-h-9 rounded-input text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
      >
        {text(T.lagg)}
      </button>
      {oppen ? (
        <div className="mt-3 grid gap-3 rounded-card border border-ink/12 bg-paper2/40 p-4">
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col gap-1">
              <span className={etikett}>{text(T.riktning)}</span>
              <select value={riktning} onChange={(e) => setRiktning(e.target.value as "outbound" | "inbound")} className={faltTatt}>
                <option value="outbound">{text(T.fran)}</option>
                <option value="inbound">{text(T.till)}</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className={etikett}>{text(T.nar)}</span>
              <input type="datetime-local" value={nar} onChange={(e) => setNar(e.target.value)} className={faltTatt} />
            </label>
          </div>
          <label className="flex flex-col gap-1">
            <span className={etikett}>{text(T.text)}</span>
            <textarea
              rows={4}
              value={innehall}
              maxLength={8000}
              onChange={(e) => setInnehall(e.target.value)}
              className="focus-ring w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[1rem] leading-7 text-ink"
            />
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" disabled={arbetar || !innehall.trim()} onClick={() => void lagg()} className={cn(btnPrimary, btnLiten)}>
              {arbetar ? "…" : text(T.laggIn)}
            </button>
            {fel ? <span className="text-[0.875rem] text-danger">{fel}</span> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
