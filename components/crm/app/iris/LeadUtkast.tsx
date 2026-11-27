"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, FilePen, RefreshCw, Send, X } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { useSkrivratt } from "@/components/crm/app/kit";
import { CrmFel } from "@/lib/crm/api";
import { irisAnrop } from "@/lib/crm/iris/anrop";
import { UTKASTTON, kanSkickas, obedomd, utkastText, type Lead, type Utkastsvar } from "@/lib/crm/iris/lead";
import { lasStruktur, sparaStruktur, type Struktur } from "@/lib/leads/struktur";
import { useLocale, type Localized } from "@/lib/i18n";

/** Medan utkastet skrivs läses det om så här ofta, högst så här många gånger (cirka tre minuter). */
const POLL_MS = 4000;
const POLL_MAX = 45;

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Mejlutkastet i leadets panel (LR-065, LR-067, LR-068, LR-071, LR-073, LR-074,
 * LR-112): som mottagaren ser det, med utkastets riktiga status
 * (`GET /leads/prospects/{id}/utkast`, utkaststatus.harled) och handlingarna som
 * inte kräver redigeraren: Godkänn och skicka, Avvisa, Skriv om och Skapa utkast.
 *
 * Skapa och Skriv om går genom `POST /leads/prospects/processa-om`, samma väg
 * som listans Skapa utkast: ur sparad research (`utkast`), eller med en ny
 * research först när leadet saknar mejladress eller bedömning (`research_and_draft`,
 * kontaktjakten). Utkastet läses om tills det inte längre skrivs.
 */
export function LeadUtkast({
  id,
  lead,
  andrat,
  lasOm
}: Readonly<{
  id: string;
  lead: Lead;
  /** Utkastet ändrades: panelen hämtar om och listan bakom får veta det. */
  andrat: () => void;
  /** Bara leadet läses om, utan att listan meddelas (pollningen medan utkastet skrivs). */
  lasOm: () => void;
}>) {
  const { text, locale } = useLocale();
  const skriv = useSkrivratt("test");
  // Autonomin är kundens inställning, inte agentens data: den ändras aldrig under ett kundbesök.
  const installning = useSkrivratt("stangt");
  const [svar, setSvar] = useState<Utkastsvar | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [upptagen, setUpptagen] = useState<"godkann" | "avvisa" | "skriv" | null>(null);
  const [besked, setBesked] = useState<{ text: string; fel: boolean } | null>(null);
  const [avvisa, setAvvisa] = useState(false);
  const [godkant, setGodkant] = useState(false);
  const [auto, setAuto] = useState<{ pa: boolean; sparar: boolean; besked: string | null; fel: boolean }>({ pa: false, sparar: false, besked: null, fel: false });
  const [struktur, setStruktur] = useState<Struktur>("a");
  const varv = useRef(0);

  useEffect(() => {
    setStruktur(lasStruktur());
  }, []);

  // Ordningsskydd: bara den senaste hämtningen skrivs in (byte av lead, pollning, omläsning efter en handling).
  const hamtNr = useRef(0);
  const hamta = useCallback(async () => {
    const nr = ++hamtNr.current;
    try {
      const s = await irisAnrop<Utkastsvar>(`/leads/prospects/${encodeURIComponent(id)}/utkast`);
      if (nr !== hamtNr.current) return;
      setSvar(s);
      setFel(null);
    } catch (e) {
      if (nr !== hamtNr.current) return;
      setFel(e);
    }
  }, [id]);

  useEffect(() => {
    hamtNr.current += 1;
    setSvar(null);
    setBesked(null);
    setGodkant(false);
    void hamta();
  }, [hamta]);

  // Förlopp: medan utkastet skrivs läses utkastet och leadet om, och listan bakom får veta
  // det EN gång, när det är klart (listan har sin egen livetakt under tiden).
  const skrivs = svar?.utkast_status === "skrivs" || lead.status === "researching";
  const andratRef = useRef(andrat);
  andratRef.current = andrat;
  const lasOmRef = useRef(lasOm);
  lasOmRef.current = lasOm;
  useEffect(() => {
    if (!skrivs) {
      if (varv.current > 0) andratRef.current();
      varv.current = 0;
      return;
    }
    const t = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      varv.current += 1;
      if (varv.current > POLL_MAX) {
        window.clearInterval(t);
        setBesked({ text: text({ sv: "Utkastet tog för lång tid. Försök igen om en stund.", en: "The draft took too long. Try again in a moment." }), fel: true });
        return;
      }
      // Leadet läses också om: under kontaktjakten är det leadets status (Research pågår) som säger att arbetet pågår.
      void hamta();
      lasOmRef.current();
    }, POLL_MS);
    return () => window.clearInterval(t);
  }, [skrivs, hamta, text]);

  const status = svar?.utkast_status ?? null;
  const kanAvvisas = Boolean(svar?.queue_item_id) && (status === "vantar" || status === "koad" || status === "godkant");
  const kanSkrivasOm = status === "vantar" || status === "koad" || status === "godkant" || status === "stoppat";
  const utanUtkast = !svar?.utkast && status !== "skrivs";

  async function godkann() {
    if (!svar?.queue_item_id) return;
    setUpptagen("godkann");
    setBesked(null);
    try {
      const s = await irisAnrop<{ utfall?: string; besked?: string; skal?: string | null }>(`/leads/queue/${encodeURIComponent(svar.queue_item_id)}/approve`, { method: "POST" });
      const skal = s.skal ?? s.besked?.split(": ").slice(1).join(": ") ?? "";
      if (s.utfall === "sent") setBesked({ text: text({ sv: "Skickat.", en: "Sent." }), fel: false });
      else if (s.utfall === "requeued") setBesked({ text: text({ sv: "Godkänt. Mejlet skickas i tur och ordning från kön (vardagar från 08:00).", en: "Approved. The email goes out in turn from the queue (weekdays from 08:00)." }), fel: false });
      else if (s.utfall === "redan_hanterad") setBesked({ text: text({ sv: "Utkastet är redan hanterat.", en: "The draft has already been handled." }), fel: true });
      else setBesked({ text: skal ? text({ sv: `Inte skickat: ${skal}`, en: `Not sent: ${skal}` }) : text({ sv: "Inte skickat.", en: "Not sent." }), fel: true });
      if (s.utfall === "sent" || s.utfall === "requeued") setGodkant(true);
      andrat();
      await hamta();
    } catch (e) {
      setBesked({ text: text(feltext(e)), fel: true });
    } finally {
      setUpptagen(null);
    }
  }

  async function avvisaUtkast() {
    if (!svar?.queue_item_id) return;
    setUpptagen("avvisa");
    try {
      await irisAnrop(`/leads/queue/${encodeURIComponent(svar.queue_item_id)}/reject`, { method: "POST" });
      setBesked({ text: text({ sv: "Utkastet är avvisat och skickas aldrig.", en: "The draft is rejected and will never be sent." }), fel: false });
      andrat();
      await hamta();
    } catch (e) {
      setBesked({ text: text(feltext(e)), fel: true });
    } finally {
      setUpptagen(null);
      setAvvisa(false);
    }
  }

  /** Skapa (utan utkast) eller Skriv om (ersätter det väntande). */
  async function skrivUtkast(ersatt: boolean) {
    setUpptagen("skriv");
    setBesked(null);
    // Utan mejladress eller bedömning letar researchen först upp kontakten (kontaktjakten, LR-068).
    const scope = !lead.contact_email || obedomd(lead) ? "research_and_draft" : "utkast";
    try {
      const s = await irisAnrop<{ count?: number; hoppade_over?: string[]; pagar_redan?: string[] }>("/leads/prospects/processa-om", {
        method: "POST",
        body: JSON.stringify({ prospect_ids: [id], scope, ersatt, struktur })
      });
      if (s.pagar_redan?.length) setBesked({ text: text({ sv: "Leadet bearbetas redan. Utkastet visas här när det är klart.", en: "The lead is already being processed. The draft shows here when done." }), fel: false });
      else if (s.hoppade_over?.length) setBesked({ text: text({ sv: "Leadet har redan fått mejl utan någon uppföljning som väntar, så inget nytt första mejl skrivs.", en: "The lead has already been emailed with no follow-up pending, so no new first email is written." }), fel: true });
      else
        setBesked({
          text:
            scope === "research_and_draft"
              ? text({ sv: "Iris letar kontaktadress på bolagets sajt och skriver utkastet direkt efteråt. Det tar ungefär en minut.", en: "Iris is looking for a contact address on the company's site and writes the draft right after. It takes about a minute." })
              : text({ sv: "Iris skriver utkastet ur den research som redan finns.", en: "Iris is writing the draft from the existing research." }),
          fel: false
        });
      andrat();
      await hamta();
    } catch (e) {
      setBesked({ text: text(feltext(e)), fel: true });
    } finally {
      setUpptagen(null);
    }
  }

  async function sattAuto(pa: boolean) {
    setAuto({ pa, sparar: true, besked: null, fel: false });
    try {
      await irisAnrop("/leads/config", { method: "PUT", body: JSON.stringify({ autonomy: pa ? "auto_send" : "draft" }) });
      setAuto({ pa, sparar: false, besked: text({ sv: "Sparat.", en: "Saved." }), fel: false });
    } catch (e) {
      // Faller sparningen står rutan kvar på värdet före försöket: det är det servern har.
      setAuto({ pa: !pa, sparar: false, besked: text(feltext(e)), fel: true });
    }
  }

  const strukturval = (
    <Selector
      label={text({ sv: "Struktur", en: "Structure" })}
      value={struktur}
      onChange={(v) => {
        if (v !== "a" && v !== "b") return;
        setStruktur(v);
        sparaStruktur(v);
      }}
      options={[
        { value: "a", label: text({ sv: "A, standardmejlet", en: "A, the standard email" }) },
        { value: "b", label: text({ sv: "B, kort med en fråga", en: "B, short with a question" }) }
      ]}
      width="100%"
    />
  );

  if (fel && !svar) {
    return (
      <div className="flex flex-col items-start gap-3 py-2">
        <Text color="secondary">{text(feltext(fel))}</Text>
        <Button size="sm" variant="secondary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />
      </div>
    );
  }
  if (!svar) {
    return (
      <div className="flex flex-col gap-3" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar utkastet", en: "Loading the draft" })}>
        <Skeleton width="40%" height={12} radius="rounded" />
        <Skeleton width="100%" height={120} radius={3} />
      </div>
    );
  }

  const ton = status ? UTKASTTON[status] : "dampad";
  const tonklass = ton === "varning" ? "text-warning" : ton === "mossa" ? "text-moss" : ton === "fara" ? "text-danger" : "text-ink-muted";
  const raden = utkastText(svar, locale, text);

  return (
    <div className="flex flex-col gap-4">
      {raden ? (
        <div className="flex flex-col gap-1">
          <span className={`text-[0.875rem] font-semibold ${tonklass}`}>{raden}</span>
          {svar.utkast_skal && (status === "stoppat" || status === "vantar" || status === "saknas" || status === "avvisat") ? (
            <span className="max-w-[65ch] text-[0.8125rem] leading-6 text-ink-muted">{svar.utkast_skal}</span>
          ) : null}
        </div>
      ) : null}

      {svar.utkast ? (
        /* Steg 4.3: utkastredigeraren (LR-065, LR-066, LR-070, LR-072) ersätter det här kortet för väntande,
           köade och godkända utkast. Ändpunkten för att spara är PUT /leads/queue/{queue_item_id} {subject, brodtext}. */
        <article className="crm-kallkort flex flex-col gap-3 rounded-[16px] p-4" aria-label={text({ sv: "Mejlet som mottagaren ser det", en: "The email as the recipient sees it" })}>
          <dl className="flex flex-col gap-1 border-b border-ink/[0.08] pb-3 text-[0.8125rem]">
            <div className="flex gap-2">
              <dt className="w-12 shrink-0 text-ink-muted">{text({ sv: "Till", en: "To" })}</dt>
              <dd className="min-w-0 truncate text-ink2">{lead.contact_email ?? text({ sv: "Ingen mottagare än", en: "No recipient yet" })}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-12 shrink-0 text-ink-muted">{text({ sv: "Ämne", en: "Subject" })}</dt>
              <dd className="min-w-0 font-semibold text-ink">{svar.utkast.subject}</dd>
            </div>
          </dl>
          <p className="whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{svar.utkast.brodtext ?? svar.utkast.body}</p>
          {svar.utkast.svans ? <p className="whitespace-pre-wrap break-words border-t border-ink/[0.08] pt-3 text-[0.8125rem] leading-6 text-ink-muted">{svar.utkast.svans}</p> : null}
        </article>
      ) : status === "skrivs" ? (
        <div className="crm-kallkort flex flex-col gap-3 rounded-[16px] p-4" role="status">
          <span className="text-[0.875rem] text-ink2">{text({ sv: "Iris skriver utkastet. Det visas här när det är klart.", en: "Iris is writing the draft. It shows here when done." })}</span>
          <Skeleton width="100%" height={10} radius="rounded" />
          <Skeleton width="85%" height={10} radius="rounded" />
        </div>
      ) : (
        <EmptyState
          isCompact
          icon={<Icon icon={FilePen} size="lg" color="secondary" />}
          title={text({ sv: "Inget utkast ännu", en: "No draft yet" })}
          description={
            lead.contact_email
              ? text({ sv: "Iris skriver ett första mejl ur den research som redan finns.", en: "Iris writes a first email from the existing research." })
              : text({ sv: "Bolaget saknar mejladress. Iris letar först upp den på bolagets sajt.", en: "The company has no email address. Iris first looks for it on the company's site." })
          }
        />
      )}

      {utanUtkast || status === "avvisat" ? <div className="max-w-[280px]">{strukturval}</div> : null}

      <div className="flex flex-wrap items-center gap-2">
        {kanSkickas(svar) ? (
          <Button label={text({ sv: "Godkänn och skicka", en: "Approve and send" })} variant="primary" icon={<Icon icon={Send} size="sm" />} isLoading={upptagen === "godkann"} isDisabled={!skriv.far || upptagen != null} tooltip={skriv.skal ?? undefined} onClick={() => void godkann()} />
        ) : null}
        {utanUtkast || status === "avvisat" ? (
          <Button
            label={status === "avvisat" ? text({ sv: "Skapa nytt utkast", en: "Create a new draft" }) : text({ sv: "Skapa utkast", en: "Create draft" })}
            variant={kanSkickas(svar) ? "secondary" : "primary"}
            icon={<Icon icon={FilePen} size="sm" />}
            isLoading={upptagen === "skriv"}
            isDisabled={!skriv.far || upptagen != null}
            tooltip={skriv.skal ?? undefined}
            onClick={() => void skrivUtkast(false)}
          />
        ) : null}
        {kanSkrivasOm ? (
          <Button label={text({ sv: "Skriv om", en: "Rewrite" })} variant="secondary" icon={<Icon icon={RefreshCw} size="sm" />} isLoading={upptagen === "skriv"} isDisabled={!skriv.far || upptagen != null} tooltip={skriv.skal ?? undefined} onClick={() => void skrivUtkast(true)} />
        ) : null}
        {kanAvvisas ? (
          <Button label={text({ sv: "Avvisa", en: "Reject" })} variant="ghost" icon={<Icon icon={X} size="sm" />} className="crm-farlig" isDisabled={!skriv.far || upptagen != null} tooltip={skriv.skal ?? undefined} onClick={() => setAvvisa(true)} />
        ) : null}
      </div>

      {/* Utfallet sägs upp i en region som finns hela tiden. */}
      <div role="status">
        {besked ? <Banner status={besked.fel ? "error" : "success"} container="card" title={besked.text} /> : null}
      </div>

      {/* LR-112: efter ett lyckat godkännande, frågan om Iris ska skicka själv framöver. */}
      {godkant ? (
        <div className="crm-kallkort flex flex-col gap-2 rounded-[16px] p-4">
          <CheckboxInput label={text({ sv: "Iris skriver utkast automatiskt framöver", en: "Iris writes drafts automatically from now on" })} value isDisabled disabledMessage={text({ sv: "Redan på", en: "Already on" })} />
          <CheckboxInput
            label={text({ sv: "och skickar dem automatiskt, utan granskning", en: "and sends them automatically, without review" })}
            description={text({ sv: "Varje mejl går fortfarande genom sändspärrarna.", en: "Every email still passes the send guards." })}
            value={auto.pa}
            isDisabled={!installning.far || auto.sparar}
            disabledMessage={installning.skal ?? undefined}
            onChange={(v) => void sattAuto(v)}
          />
          {auto.besked ? (
            <span className={`inline-flex items-center gap-1 text-[0.8125rem] ${auto.fel ? "text-danger" : "text-moss"}`}>
              {auto.fel ? null : <Icon icon={Check} size="xsm" color="inherit" />}
              {auto.besked}
            </span>
          ) : null}
        </div>
      ) : null}

      <AlertDialog
        isOpen={avvisa}
        onOpenChange={(o) => !o && upptagen == null && setAvvisa(false)}
        title={text({ sv: "Avvisa utkastet?", en: "Reject the draft?" })}
        description={text({ sv: "Utkastet skickas aldrig. Du kan skapa ett nytt efteråt.", en: "The draft is never sent. You can create a new one afterwards." })}
        actionLabel={text({ sv: "Avvisa", en: "Reject" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        isActionLoading={upptagen === "avvisa"}
        onAction={() => void avvisaUtkast()}
      />
    </div>
  );
}
