"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, FilePen } from "lucide-react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { Utkastredigerare } from "@/components/crm/app/iris/Utkastredigerare";
import { useSkrivratt } from "@/components/crm/app/kit";
import { StrukturVal } from "@/components/crm/app/iris/StrukturVal";
import { CrmFel } from "@/lib/crm/api";
import { irisAnrop } from "@/lib/crm/iris/anrop";
import { UTKASTTON, kanSkickas, obedomd, utkastText, type Lead, type LeadPost, type Utkastsvar } from "@/lib/crm/iris/lead";
import { signalUr, skalUr, type Besked, type Sandutfall } from "@/lib/crm/iris/utkast";
import { offertForUtkast } from "@/lib/leads/offert";
import { lasStruktur, sparaStruktur, type Struktur } from "@/lib/leads/struktur";
import { useLocale, type Localized } from "@/lib/i18n";

/** Medan utkastet skrivs läses det om så här ofta, högst så här många gånger (cirka tre minuter). */
const POLL_MS = 4000;
const POLL_MAX = 45;

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Mejlutkastet i leadets panel (LR-065 till LR-074, LR-112): utkastets riktiga
 * status (`GET /leads/prospects/{id}/utkast`, utkaststatus.harled) och utkastet
 * i utkastredigeraren (steg 4.3): ämne och text som går att ändra medan det
 * väntar, signatur och fot som mottagaren ser dem, Godkänn och skicka, Avvisa,
 * Skriv om, AI:n och provmejlet. Utan utkast: Skapa utkast.
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
  const [skapar, setSkapar] = useState(false);
  const [besked, setBesked] = useState<Besked | null>(null);
  const [godkant, setGodkant] = useState(false);
  const [auto, setAuto] = useState<{ pa: boolean; sparar: boolean; besked: string | null; fel: boolean }>({ pa: false, sparar: false, besked: null, fel: false });
  const [struktur, setStruktur] = useState<Struktur>("a");
  const [offer, setOffer] = useState<string | null>(null);
  const varv = useRef(0);

  useEffect(() => {
    setStruktur(lasStruktur());
    // Kundens erbjudande är bakgrunden AI:n skriver om utifrån. Saknas det körs AI:n utan.
    void offertForUtkast().then(setOffer, () => setOffer(null));
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
  const qid = svar?.queue_item_id ?? null;
  const kanAvvisas = Boolean(qid) && (status === "vantar" || status === "koad" || status === "godkant");
  const kanSkrivasOm = status === "vantar" || status === "koad" || status === "godkant" || status === "stoppat";
  // Backenden tar emot en ändring medan köposten väntar eller är godkänd (leads.update_queue_item_text).
  const redigerbar = Boolean(qid) && (status === "vantar" || status === "koad" || status === "godkant");
  const utanUtkast = !svar?.utkast && status !== "skrivs";

  async function godkann(): Promise<Besked> {
    if (!qid) return { text: text({ sv: "Utkastet finns inte längre.", en: "The draft no longer exists." }), fel: true };
    const s = await irisAnrop<Sandutfall>(`/leads/queue/${encodeURIComponent(qid)}/approve`, { method: "POST" });
    const skal = skalUr(s);
    andrat();
    await hamta();
    if (s.utfall === "sent" || s.utfall === "requeued") setGodkant(true);
    if (s.utfall === "sent") return { text: text({ sv: "Skickat.", en: "Sent." }), fel: false };
    if (s.utfall === "requeued") return { text: text({ sv: "Godkänt. Mejlet skickas i tur och ordning från kön (vardagar från 08:00).", en: "Approved. The email goes out in turn from the queue (weekdays from 08:00)." }), fel: false };
    if (s.utfall === "redan_hanterad") return { text: text({ sv: "Utkastet är redan hanterat.", en: "The draft has already been handled." }), fel: true };
    return { text: skal ? text({ sv: `Inte skickat: ${skal}`, en: `Not sent: ${skal}` }) : text({ sv: "Inte skickat.", en: "Not sent." }), fel: true };
  }

  async function avvisaUtkast(): Promise<Besked> {
    if (!qid) return { text: text({ sv: "Utkastet finns inte längre.", en: "The draft no longer exists." }), fel: true };
    await irisAnrop(`/leads/queue/${encodeURIComponent(qid)}/reject`, { method: "POST" });
    andrat();
    await hamta();
    return { text: text({ sv: "Utkastet är avvisat och skickas aldrig.", en: "The draft is rejected and will never be sent." }), fel: false };
  }

  /** Skapa (utan utkast) eller Skriv om (ersätter det väntande). */
  async function skrivUtkast(ersatt: boolean, st: Struktur): Promise<Besked> {
    // Utan mejladress eller bedömning letar researchen först upp kontakten (kontaktjakten, LR-068).
    const scope = !lead.contact_email || obedomd(lead) ? "research_and_draft" : "utkast";
    const s = await irisAnrop<{ count?: number; hoppade_over?: string[]; pagar_redan?: string[] }>("/leads/prospects/processa-om", {
      method: "POST",
      body: JSON.stringify({ prospect_ids: [id], scope, ersatt, struktur: st })
    });
    andrat();
    await hamta();
    if (s.pagar_redan?.length) return { text: text({ sv: "Leadet bearbetas redan. Utkastet visas här när det är klart.", en: "The lead is already being processed. The draft shows here when done." }), fel: false };
    if (s.hoppade_over?.length)
      return { text: text({ sv: "Leadet har redan fått mejl utan någon uppföljning som väntar, så inget nytt första mejl skrivs.", en: "The lead has already been emailed with no follow-up pending, so no new first email is written." }), fel: true };
    return {
      text:
        scope === "research_and_draft"
          ? text({ sv: "Iris letar kontaktadress på bolagets sajt och skriver utkastet direkt efteråt. Det tar ungefär en minut.", en: "Iris is looking for a contact address on the company's site and writes the draft right after. It takes about a minute." })
          : text({ sv: "Iris skriver utkastet ur den research som redan finns.", en: "Iris is writing the draft from the existing research." }),
      fel: false
    };
  }

  /**
   * Handlingar som byter utkastets nyckel: utfallet står i panelens region (som
   * finns kvar), inte i redigerarens, som börjar om när nyckeln byts. Ett fel
   * kastas vidare och står i redigeraren, där nyckeln inte hunnit bytas.
   */
  async function egetBesked(fn: () => Promise<Besked>): Promise<null> {
    setBesked(null);
    setBesked(await fn());
    return null;
  }

  async function skapa() {
    setSkapar(true);
    setBesked(null);
    try {
      setBesked(await skrivUtkast(false, struktur));
    } catch (e) {
      setBesked({ text: text(feltext(e)), fel: true });
    } finally {
      setSkapar(false);
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
  const post = lead as LeadPost;

  return (
    <div className="flex flex-col gap-4">
      {raden ? (
        <div className="flex flex-col gap-1">
          <span className={`text-[0.875rem] font-semibold ${tonklass}`}>{raden}</span>
          {/* Varför utkastet inte skickats (LU-050 till LU-062): skälet backenden lämnar, som det står. */}
          {svar.utkast_skal && (status === "stoppat" || status === "vantar" || status === "saknas" || status === "avvisat") ? (
            <span className="max-w-[65ch] text-[0.8125rem] leading-6 text-ink-muted">{svar.utkast_skal}</span>
          ) : null}
        </div>
      ) : null}

      {svar.utkast || status === "skrivs" ? (
        // key: ett annat lead får en ny redigerare, så att ett svar som pågår aldrig hamnar i fel leads utkast.
        // Godkänn, Avvisa och Skriv om byter nyckel (köposten blir ett skickat mejl, eller ett nytt utkast), så
        // deras utfall står i panelens egen region nedan, inte i redigerarens.
        <Utkastredigerare
          key={id}
          nyckel={qid ?? svar.utkast?.id ?? id}
          amne={svar.utkast?.subject ?? null}
          brodtext={svar.utkast?.brodtext ?? svar.utkast?.body ?? ""}
          svans={svar.utkast?.svans ?? null}
          signatur={svar.signatur ?? null}
          mottagare={lead.contact_email ?? null}
          redigerbar={redigerbar}
          skrivs={status === "skrivs"}
          kontext={{ companyName: lead.company_name, contactName: lead.contact_name, signal: signalUr(post.lagesbeskrivning, post.signaler), offer }}
          spara={
            qid
              ? async (a, b) => {
                  await irisAnrop(`/leads/queue/${encodeURIComponent(qid)}`, { method: "PUT", body: JSON.stringify({ subject: a, brodtext: b }) });
                  await hamta();
                }
              : undefined
          }
          godkann={kanSkickas(svar) ? { gor: () => egetBesked(godkann) } : undefined}
          avvisa={kanAvvisas ? { gor: () => egetBesked(avvisaUtkast) } : undefined}
          skrivOm={kanSkrivasOm ? { onskemal: false, struktur: true, gor: (_o, st) => egetBesked(() => skrivUtkast(true, st)) } : undefined}
          provmejl={qid && status !== "skickat" ? { queueItemId: qid } : status === "skickat" && svar.utkast?.id ? { messageId: svar.utkast.id } : null}
          skriv={skriv}
        />
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

      {utanUtkast || status === "avvisat" ? (
        <div className="flex flex-col gap-3">
          <div className="max-w-[280px]">
            <StrukturVal
              value={struktur}
              onChange={(v) => {
                setStruktur(v);
                sparaStruktur(v);
              }}
            />
          </div>
          <div>
            <Button
              label={status === "avvisat" ? text({ sv: "Skapa nytt utkast", en: "Create a new draft" }) : text({ sv: "Skapa utkast", en: "Create draft" })}
              variant="primary"
              icon={<Icon icon={FilePen} size="sm" />}
              isLoading={skapar}
              isDisabled={!skriv.far || skapar}
              tooltip={skriv.skal ?? undefined}
              onClick={() => void skapa()}
            />
          </div>
        </div>
      ) : null}

      {/* Utfallet av Skapa utkast och pollningen sägs upp i en region som finns hela tiden. */}
      <div role="status">{besked ? <Banner status={besked.fel ? "error" : "success"} container="card" title={besked.text} /> : null}</div>

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
    </div>
  );
}
