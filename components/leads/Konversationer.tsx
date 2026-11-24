"use client";

import { ArrowLeft, Bell } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { KonversationsTrad } from "@/components/leads/KonversationsTrad";
import { SkeletonRows, Tomt, btnSecondary, chip, chipAktiv, chipInaktiv, chiplista, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import {
  notisEtikett,
  STEG,
  STEG_ETIKETT,
  STEG_PRICK,
  klassText,
  meddelaNotiser,
  NOTISER_UPPDATERADE,
  type Konversationslista,
  type Konversationsrad,
  type Notis
} from "@/lib/leads/konversationer";
import { leadsAnrop, relativTid } from "@/lib/leads/suite";
import { LEADS_UPPDATERADE } from "@/lib/leads/utkast";
import { cn } from "@/lib/utils";

/**
 * Leads › Konversationer (Antons beställning 2026-11-22): det kunderna i
 * första hand köper, de nya konversationerna, på en egen flik i stället för
 * som filtret "Svarat" under Inkorg › Skickat.
 *
 * Listan till vänster med filter (Att göra först), tråden till höger. Under
 * lg står listan ensam och tråden tar hela bredden med en tillbaka-länk.
 * Den öppna tråden står i adressen (`?vy=konversationer&trad=`), så att en
 * notis eller översiktsrutan kan länka hit och en omladdning landar rätt.
 */

type Filter = "att_gora" | "alla" | "utkast" | (typeof STEG)[number];

const FILTER: { id: Filter; etikett: Localized }[] = [
  { id: "att_gora", etikett: { sv: "Att göra", en: "To do" } },
  { id: "alla", etikett: { sv: "Alla", en: "All" } },
  { id: "utkast", etikett: { sv: "Utkast väntar", en: "Drafts waiting" } },
  ...STEG.map((s) => ({ id: s, etikett: STEG_ETIKETT[s] }))
];

function passar(r: Konversationsrad, filter: Filter): boolean {
  if (filter === "alla") return true;
  if (filter === "att_gora") return r.att_gora;
  if (filter === "utkast") return r.utkast !== null;
  return r.steg === filter;
}

/** Listan, hämtad en gång och om när något i Leads ändrats. */
export function useKonversationer(aktiv = true) {
  const [lista, setLista] = useState<Konversationslista | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const hamta = useCallback(async () => {
    try {
      setLista(await leadsAnrop<Konversationslista>("/leads/konversationer"));
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setLista((nu) => nu ?? { konversationer: [], antal: {}, sammanfattning: { nya_svar: 0, utkast_vantar: 0, moten: 0, aterkom_idag: 0 } });
    }
  }, []);
  useEffect(() => {
    if (!aktiv) return;
    void hamta();
    const uppdatera = () => void hamta();
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    window.addEventListener(NOTISER_UPPDATERADE, uppdatera);
    return () => {
      window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
      window.removeEventListener(NOTISER_UPPDATERADE, uppdatera);
    };
  }, [aktiv, hamta]);
  return { lista, fel, hamta };
}

function Rad({ r, vald, onValj }: Readonly<{ r: Konversationsrad; vald: boolean; onValj: () => void }>) {
  const { text, locale } = useLocale();
  return (
    <li>
      <button
        type="button"
        id={`konversation-${r.thread_id}`}
        aria-current={vald ? "true" : undefined}
        onClick={onValj}
        className={cn(
          "focus-ring relative block w-full rounded-input px-3 py-3 text-left transition-colors",
          vald ? "bg-paper2" : "hover:bg-paper2/60"
        )}
      >
        <span className="flex items-start justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2">
            {r.olasta ? (
              <span aria-label={text({ sv: "Oläst", en: "Unread" })} className="h-2 w-2 shrink-0 rounded-full bg-ochre" />
            ) : null}
            <span className={cn("truncate text-[0.9375rem] text-ink", r.olasta ? "font-semibold" : "font-medium")}>
              {r.company_name ?? r.contact_email ?? text({ sv: "Okänt bolag", en: "Unknown company" })}
            </span>
          </span>
          <time dateTime={r.senast ?? undefined} className={cn(meta, "num shrink-0 tabular-nums")}>
            {relativTid(r.senast, locale)}
          </time>
        </span>
        {r.senaste_svar?.utdrag ? (
          <span className="mt-0.5 line-clamp-2 block text-[0.875rem] leading-6 text-ink-muted">{r.senaste_svar.utdrag}</span>
        ) : null}
        <span className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.8125rem]">
          <span className="inline-flex items-center gap-1.5 text-ink-muted">
            <span aria-hidden className={cn("h-1.5 w-1.5 rounded-full", STEG_PRICK[r.steg])} />
            {text(STEG_ETIKETT[r.steg])}
            {r.steg === "aterkom" && r.aterkom_datum ? ` ${r.aterkom_datum}` : ""}
            {/* Ett nej följs upp en gång längre fram (Anton 2026-11-23). */}
            {r.steg === "ej_intresserad" && r.aterkom_datum
              ? text({ sv: `, återkontakt ${r.aterkom_datum}`, en: `, recontact ${r.aterkom_datum}` })
              : ""}
          </span>
          {r.utkast ? (
            <span className="font-medium text-warning">
              {r.utkast.flaggat
                ? text({ sv: "Utkast väntar, kontrollera", en: "Draft waiting, check it" })
                : text({ sv: "Utkast väntar", en: "Draft waiting" })}
            </span>
          ) : null}
          {r.aterkom_forfallet ? (
            <span className="font-medium text-warning">{text({ sv: "Dags att återkomma", en: "Time to follow up" })}</span>
          ) : null}
        </span>
      </button>
    </li>
  );
}

export function Konversationer({
  trad,
  onTrad
}: Readonly<{ trad: string | null; onTrad: (threadId: string | null) => void }>) {
  const { text } = useLocale();
  const { lista, fel, hamta } = useKonversationer();
  const [filter, setFilter] = useState<Filter>("att_gora");
  const forsta = useRef(true);

  // Första gången: finns inget att göra visas alla, inte en tom lista.
  useEffect(() => {
    if (lista && forsta.current) {
      forsta.current = false;
      if (!lista.antal.att_gora && lista.antal.alla) setFilter("alla");
    }
  }, [lista]);

  const synliga = useMemo(() => (lista?.konversationer ?? []).filter((r) => passar(r, filter)), [lista, filter]);

  if (lista === null) return <SkeletonRows />;

  const listdel = (
    <div className={cn("min-w-0", trad && "hidden lg:block")}>
      <ul className={chiplista} aria-label={text({ sv: "Filtrera konversationer", en: "Filter conversations" })}>
        {FILTER.filter((f) => f.id === "att_gora" || f.id === "alla" || (lista.antal[f.id] ?? 0) > 0 || filter === f.id).map((f) => (
          <li key={f.id}>
            <button
              type="button"
              aria-pressed={filter === f.id}
              onClick={() => setFilter(f.id)}
              className={cn(chip, filter === f.id ? chipAktiv : chipInaktiv)}
            >
              {text(f.etikett)}{" "}
              <span className={cn("num tabular-nums", filter === f.id ? "text-paper-muted" : "text-ink-subtle")}>
                {lista.antal[f.id] ?? 0}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {fel ? (
        <p role="alert" className="mt-3 text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
      <div className="mt-3">
        {lista.konversationer.length === 0 ? (
          <Tomt>
            {text({
              sv: "Inga konversationer än. När ett bolag svarar på ett mejl från Iris hamnar svaret här, med ett utkast till svar.",
              en: "No conversations yet. When a company replies to an email from Iris, the reply lands here with a draft answer."
            })}
          </Tomt>
        ) : synliga.length === 0 ? (
          <Tomt>{text({ sv: "Inget att göra just nu.", en: "Nothing to do right now." })}</Tomt>
        ) : (
          <ul className="-mx-1 divide-y divide-ink/10" aria-label={text({ sv: "Konversationer", en: "Conversations" })}>
            {synliga.map((r) => (
              <Rad key={r.thread_id} r={r} vald={trad === r.thread_id} onValj={() => onTrad(r.thread_id)} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );

  return (
    <div className="grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(0,21rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,24rem)_minmax(0,1fr)]">
      {listdel}
      <div className={cn("min-w-0", !trad && "hidden lg:block")}>
        {trad ? (
          <>
            <button
              type="button"
              onClick={() => onTrad(null)}
              className="focus-ring mb-3 inline-flex min-h-11 items-center gap-1.5 rounded-input text-[0.875rem] font-medium text-ink-muted hover:text-ink lg:hidden"
            >
              <ArrowLeft aria-hidden className="h-4 w-4" />
              {text({ sv: "Alla konversationer", en: "All conversations" })}
            </button>
            <KonversationsTrad key={trad} threadId={trad} onAndrad={() => void hamta()} />
          </>
        ) : (
          <Tomt>{text({ sv: "Välj en konversation i listan.", en: "Pick a conversation in the list." })}</Tomt>
        )}
      </div>
    </div>
  );
}

/** Talen ur konversationerna som Leads › Översikt visar i sin rad nyckeltal. */
export type Konversationstal = Konversationslista["sammanfattning"];

/**
 * Panelen i Leads › Översikt: de tre konversationer som behöver någon först.
 *
 * Talen (nya svar, bokade möten, återkomster i dag) står INTE här. De hör till
 * översiktens enda rad nyckeltal och lämnas dit med `onTal`, samma mönster som
 * utkastrutans `onAntal` och körningsrutans `onPagaende`. Första versionen
 * (2026-11-22) hade en egen rad med fyra tal ovanpå översiktens fyra: två
 * sifferrader i två stilar, där "Utkast väntar 3" stod över "Utkast att
 * godkänna 200" (Anton 2026-11-24: "byggts fult ovanpå").
 */
export function KonversationsRuta({
  onOppna,
  onTal
}: Readonly<{ onOppna: (threadId: string | null) => void; onTal?: (tal: Konversationstal) => void }>) {
  const { text } = useLocale();
  const { lista } = useKonversationer();
  const s = lista?.sammanfattning;
  const vantar = (lista?.konversationer ?? []).filter((r) => r.att_gora);
  const forst = vantar.slice(0, 3);

  useEffect(() => {
    if (s) onTal?.(s);
    // Bara när talen ändras: föräldern skickar en ny funktion vid varje rendering.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s?.nya_svar, s?.utkast_vantar, s?.moten, s?.aterkom_idag]);

  return (
    <section aria-labelledby="leads-konversationsruta" className="rounded-card border border-ink/12 bg-paper p-4 sm:p-5">
      {/* Samma huvud som panelerna bredvid (Senaste utkasten, Senaste
          körningen): rubrik med antalet, och vägen till hela vyn som en stilla
          länk. Sidans enda knapp är Kör Iris. */}
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="leads-konversationsruta" className={rubrikPanel}>
          {text({ sv: "Konversationer som väntar", en: "Conversations waiting" })}
          {vantar.length ? <>{" "}<span className="num ml-1 font-normal tabular-nums text-ink-subtle">{vantar.length}</span></> : null}
        </h2>
        <button
          type="button"
          onClick={() => onOppna(null)}
          className="focus-ring rounded-input text-[0.875rem] font-medium text-ink underline underline-offset-4 hover:text-warning"
        >
          {text({ sv: "Alla konversationer", en: "All conversations" })}
        </button>
      </div>
      {lista === null ? null : forst.length === 0 ? (
        <p className={meta}>
          {lista.konversationer.length
            ? text({ sv: "Inget väntar på dig just nu.", en: "Nothing is waiting for you right now." })
            : text({ sv: "Inga svar från leads än.", en: "No replies from leads yet." })}
        </p>
      ) : (
        <ul className="divide-y divide-ink/10 border-t border-ink/10">
          {forst.map((r) => (
            <li key={r.thread_id}>
              <button
                type="button"
                onClick={() => onOppna(r.thread_id)}
                className="focus-ring flex w-full flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 rounded-input py-2.5 text-left hover:bg-paper2/60"
              >
                <span className="min-w-0">
                  <span className={cn("text-[0.9375rem] text-ink", r.olasta ? "font-semibold" : "font-medium")}>
                    {r.company_name ?? r.contact_email}
                  </span>
                  {r.senaste_svar?.utdrag ? (
                    <span className="ml-2 text-[0.875rem] text-ink-muted">{r.senaste_svar.utdrag.slice(0, 90)}</span>
                  ) : null}
                </span>
                <span className="shrink-0 text-[0.8125rem] font-medium text-warning">
                  {r.utkast
                    ? text({ sv: "Utkast väntar", en: "Draft waiting" })
                    : r.aterkom_forfallet
                      ? text({ sv: "Återkom i dag", en: "Follow up today" })
                      : text({ sv: "Nytt svar", en: "New reply" })}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Notiserna i Snajp: klockan i Leads sidhuvud, med antalet olästa. Listan står
 * kvar efter en omladdning (den är databasens, migration 149). Ett klick
 * öppnar konversationen och markerar dess notiser lästa.
 */
export function NotisKnapp({ antal, onOppna }: Readonly<{ antal: number; onOppna: (threadId: string | null) => void }>) {
  const { text, locale } = useLocale();
  const [oppen, setOppen] = useState(false);
  const [notiser, setNotiser] = useState<Notis[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const yta = useRef<HTMLDivElement>(null);

  const hamta = useCallback(async () => {
    try {
      const svar = await leadsAnrop<{ notiser: Notis[] }>("/leads/notiser?limit=30");
      setNotiser(svar.notiser);
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setNotiser((nu) => nu ?? []);
    }
  }, []);

  useEffect(() => {
    if (!oppen) return;
    void hamta();
    const stang = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !yta.current?.contains(e.target as Node)) setOppen(false);
    };
    document.addEventListener("mousedown", stang);
    document.addEventListener("keydown", stang);
    return () => {
      document.removeEventListener("mousedown", stang);
      document.removeEventListener("keydown", stang);
    };
  }, [oppen, hamta]);

  async function allaLasta() {
    try {
      await leadsAnrop("/leads/notiser/last", { method: "POST", body: JSON.stringify({}) });
      meddelaNotiser();
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }

  return (
    <div ref={yta} className="relative">
      <button
        type="button"
        aria-expanded={oppen}
        aria-haspopup="true"
        onClick={() => setOppen((v) => !v)}
        className={cn(btnSecondary, "relative px-3")}
        aria-label={text({ sv: `Notiser, ${antal} olästa`, en: `Notifications, ${antal} unread` })}
      >
        <Bell aria-hidden className="h-4 w-4" />
        <span className="hidden sm:inline">{text({ sv: "Notiser", en: "Notifications" })}</span>
        {antal > 0 ? (
          <span className="num inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-ochre px-1.5 text-[0.75rem] font-semibold leading-5 tabular-nums text-ink">
            {antal}
          </span>
        ) : null}
      </button>
      {oppen ? (
        <div
          role="dialog"
          aria-label={text({ sv: "Notiser", en: "Notifications" })}
          className="fixed inset-x-4 top-20 z-40 max-h-[70dvh] overflow-y-auto rounded-card border border-ink/12 bg-paper p-2 shadow-lift sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:mt-2 sm:w-[24rem]"
        >
          <div className="flex items-center justify-between gap-3 px-2 py-1.5">
            <p className={rubrikPanel}>{text({ sv: "Notiser", en: "Notifications" })}</p>
            {notiser?.some((n) => !n.last) ? (
              <button
                type="button"
                onClick={() => void allaLasta()}
                className="focus-ring min-h-9 rounded-input text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
              >
                {text({ sv: "Markera alla som lästa", en: "Mark all as read" })}
              </button>
            ) : null}
          </div>
          {fel ? <p className="px-2 py-1 text-[0.875rem] text-danger">{fel}</p> : null}
          {notiser === null ? (
            <p className={cn(meta, "px-2 py-3")}>…</p>
          ) : notiser.length === 0 ? (
            <p className="px-2 py-3 text-[0.9375rem] text-ink-muted">
              {text({ sv: "Inga notiser än. Nya svar, utkast och möten hamnar här.", en: "No notifications yet. New replies, drafts and meetings land here." })}
            </p>
          ) : (
            <ul className="divide-y divide-ink/10">
              {notiser.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setOppen(false);
                      onOppna(n.thread_id);
                    }}
                    className="focus-ring flex w-full items-start gap-2.5 rounded-input px-2 py-2.5 text-left hover:bg-paper2/60"
                  >
                    <span
                      aria-hidden
                      className={cn("mt-2 h-1.5 w-1.5 shrink-0 rounded-full", n.last ? "bg-transparent" : "bg-ochre")}
                    />
                    <span className="min-w-0 flex-1">
                      <span className={cn("block text-[0.9375rem] text-ink", !n.last && "font-semibold")}>
                        {text(notisEtikett(n))}
                        {n.company_name ? <span className="font-normal text-ink-muted"> · {n.company_name}</span> : null}
                      </span>
                      <span className={cn(meta, "block")}>
                        {relativTid(n.tid, locale)}
                        {n.klass ? ` · ${klassText(n.klass, text)}` : ""}
                        {n.last ? "" : text({ sv: " · oläst", en: " · unread" })}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
