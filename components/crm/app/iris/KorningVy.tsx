"use client";

import "@/components/crm/app/crm-vyer.css";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, AtSign, Building2, Check, CircleDot, FilePen, Filter, Pause, PenLine, Play, Radar, RotateCw, SearchX, Square, Type } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { List, ListItem } from "@astryxdesign/core/List";
import { Pagination } from "@astryxdesign/core/Pagination";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { SIDSTORLEK, useSida } from "@/components/leads/sidindelning";
import { pafyllnadSkal } from "@/components/leads/pafyllnad";
import { Bekraftelse } from "@/components/crm/app/iris/Bekraftelse";
import { KORNINGARNAS_KALLA, Korningsstatus, korningstid } from "@/components/crm/app/iris/KorningarVy";
import { LeadPanel } from "@/components/crm/app/iris/LeadPanel";
import { UtkastPanel } from "@/components/crm/app/iris/UtkastPanel";
import { Kolumnrubrik, Kopierbar, Panelkort, Postchip, Tabellskelett, Vyval, useSkrivratt, useSmal } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { CrmFel } from "@/lib/crm/api";
import { LEADS_UPPDATERADE, PANELENS_KALLA, allaLeads, irisAnrop, meddelaLeadsUppdaterade } from "@/lib/crm/iris/anrop";
import type { Lead } from "@/lib/crm/iris/lead";
import { forstaMening } from "@/lib/crm/iris/mejl";
import {
  LETAR_FRASER,
  RESEARCH_FRASER,
  SLUT_ETIKETT,
  STEG,
  STEGORDNING,
  STEG_VAD,
  UTKASTSTATUS,
  antalBortvalda,
  antalJobb,
  arbetar,
  kanFortsatta,
  kanStyras,
  korningsTyp,
  pagar,
  vilaText,
  type KorningsLead,
  type KorningsRad,
  type KorningsUtkastSvar,
  type Tratt
} from "@/lib/crm/iris/korning";
import { skalUr, type Besked, type Kopost, type Kosvar, type Sandutfall, type Signatur } from "@/lib/crm/iris/utkast";
import { offertForUtkast } from "@/lib/leads/offert";
import { icpEtiketter } from "@/lib/leads/icpLabels";
import { foljUtskick, mindUtskick, minnsUtskick, startaUtskick, type Utskicksforlopp } from "@/lib/leads/utskicksjobb";
import { useLocale, type Localized } from "@/lib/i18n";

type Flik = "oversikt" | "leads" | "bortvalda";
const FLIKAR: Flik[] = ["oversikt", "leads", "bortvalda"];
const flikUr = (v: string | null | undefined): Flik => (FLIKAR.includes(v as Flik) ? (v as Flik) : "oversikt");
type Atgard = "pausa" | "aterupta" | "avbryt" | "fortsatt";

const PULS = 3000;
/** Utkasten Iris skriver följs så här ofta och så länge (LK-037: var femte sekund, högst 60 varv). */
const SKRIV_MS = 5000;
const SKRIV_VARV = 60;
const skrivnyckel = (id: string) => `crm-iris-skriver:${id}`;
const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : e instanceof Error ? { sv: e.message, en: e.message } : { sv: "Okänt fel.", en: "Unknown error." });

/** Lägesfraserna roterar var tionde sekund (LK-027). Bytet sägs inte upp: regionen bredvid bär talen. */
function Roterande({ fraser }: Readonly<{ fraser: Localized[] }>) {
  const { text } = useLocale();
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setI((v) => (v + 1) % fraser.length), 10_000);
    return () => window.clearInterval(t);
  }, [fraser.length]);
  return (
    <span key={i} className="animate-statusbyte" aria-hidden>
      {text(fraser[i % fraser.length])}
    </span>
  );
}

/**
 * Körningens sida (steg 4.4), `/crm/iris/korningar/<id>`: en sida och inte en
 * panel, för att den själv öppnar två paneler (leadet `?lead=` och utkastet
 * `?utkast=`), och för att körningens leads och bortvalda bolag kan vara hundratals
 * rader som behöver hela bredden. En panel i en panel finns inte i mönstren.
 *
 * - Översikt: förloppet medan den går (LK-027), styrningen (LK-028, LK-029),
 *   utfallet, sammanfattningen och flaskhalsen (LK-044, LK-047), en vilande
 *   körning i klartext (regel 23), Fortsätt under målet (LK-030), tratten per
 *   steg (LK-042) och vad den kördes med (LK-013).
 * - Leads: körningens leads med utkastets läge (LK-034). Leadet öppnas i
 *   LeadPanel, ett väntande utkast i utkastredigeraren (LK-035, LK-036). Skriv
 *   utkast till dem som saknar (LK-037) och Godkänn och skicka alla (LK-038).
 *   Påfyllda leads är märkta med skälet.
 * - Bortvalda: tratten rad för rad, med steg, skäl och belägg (LK-031).
 *
 * Arbetsminnet (kandidater, webbpoolen med län, listspår) lämnar aldrig API:t (LK-033).
 */
export function KorningVy({ id, bas = "/crm" }: Readonly<{ id: string; bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const skriv = useSkrivratt("test");
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);
  const listvag = `${bas}/iris/korningar`;

  // ---- Adressen: fliken (`?vy=`), leadets panel (`?lead=`) och utkastets (`?utkast=`) ----------
  const skrivAdress = useCallback((andra: Record<string, string | null>) => {
    const q = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(andra)) {
      if (v) q.set(k, v);
      else q.delete(k);
    }
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);
  const [flik, setFlikState] = useState<Flik>(flikUr(params?.get("vy")));
  const adressensLead = params?.get("lead") ?? null;
  const adressensUtkast = params?.get("utkast") ?? null;
  const [leadId, setLeadId] = useState<string | null>(adressensLead);
  const [utkastId, setUtkastId] = useState<string | null>(adressensUtkast);
  useEffect(() => setLeadId(adressensLead), [adressensLead]);
  useEffect(() => setUtkastId(adressensUtkast), [adressensUtkast]);
  const setFlik = (f: Flik) => {
    setFlikState(f);
    skrivAdress({ vy: f === "oversikt" ? null : f });
  };
  const oppnaLead = (pid: string | null) => {
    setUtkastId(null);
    setLeadId(pid);
    skrivAdress({ lead: pid, utkast: null });
  };
  const oppnaUtkast = (qid: string | null) => {
    setLeadId(null);
    setUtkastId(qid);
    skrivAdress({ utkast: qid, lead: null });
  };

  // ---- Körningen -----------------------------------------------------------------------
  const [rad, setRad] = useState<KorningsRad | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const nr = useRef(0);
  const hamta = useCallback(async () => {
    const mitt = ++nr.current;
    try {
      const r = await irisAnrop<KorningsRad>(`/leads/korningar/${encodeURIComponent(id)}`);
      if (mitt !== nr.current) return;
      setRad(r);
      setFel(null);
    } catch (e) {
      if (mitt !== nr.current) return;
      setFel(e);
    }
  }, [id]);
  useEffect(() => {
    void hamta();
  }, [hamta]);

  const gar = rad ? arbetar(rad) : false;
  const stoppad = fel instanceof CrmFel && [401, 403, 404].includes(fel.status);
  useEffect(() => {
    if (!gar || stoppad) return;
    let aktiv = true;
    let timer = 0;
    const varv = async () => {
      if (document.visibilityState === "visible") await hamta();
      if (aktiv) timer = window.setTimeout(() => void varv(), PULS);
    };
    const synlig = () => {
      if (document.visibilityState === "visible") void hamta();
    };
    timer = window.setTimeout(() => void varv(), PULS);
    document.addEventListener("visibilitychange", synlig);
    return () => {
      aktiv = false;
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", synlig);
    };
  }, [gar, stoppad, hamta]);

  // ---- Körningens leads och utkast (LK-034) -----------------------------------------------
  const [utkast, setUtkast] = useState<(KorningsUtkastSvar & { signatur?: Signatur | null }) | null>(null);
  const [utkastFel, setUtkastFel] = useState<unknown>(null);
  const [leadrader, setLeadrader] = useState<Map<string, Lead> | null>(null);
  const harJobb = rad?.scope === "batch" && antalJobb(rad.korning) > 0;
  const hamtaUtkast = useCallback(async () => {
    try {
      const s = await irisAnrop<KorningsUtkastSvar & { signatur?: Signatur | null }>(`/leads/korningar/${encodeURIComponent(id)}/utkast`);
      setUtkast(s);
      setUtkastFel(null);
      return s;
    } catch (e) {
      setUtkastFel(e);
      return null;
    }
  }, [id]);
  // Iris-listans rader bär påfyllnaden och ger leadets panel ett huvud direkt. Körningens utkastsvar bär den inte.
  const hamtaLeadrader = useCallback(async () => {
    try {
      const alla = await allaLeads<Lead>();
      setLeadrader(new Map(alla.map((p) => [p.id, p])));
    } catch {
      setLeadrader((m) => m ?? new Map());
    }
  }, []);
  const behoverLeads = flik === "leads" || leadId != null || utkastId != null;
  useEffect(() => {
    if (!harJobb || !behoverLeads) return;
    void hamtaUtkast();
    // Läses om när körningen rört sig, så att en pågående körnings leads fylls på medan man tittar.
  }, [harJobb, behoverLeads, hamtaUtkast, rad?.updated_at]);
  useEffect(() => {
    if (behoverLeads && leadrader == null) void hamtaLeadrader();
  }, [behoverLeads, leadrader, hamtaLeadrader]);

  // Ändras leads eller utkast någon annanstans (panelen, Iris-listan, Utkast) läses allt om.
  useEffect(() => {
    const uppdatera = (e: Event) => {
      if ((e as CustomEvent).detail === KORNINGARNAS_KALLA) return;
      void hamta();
      if (harJobb) void hamtaUtkast();
      void hamtaLeadrader();
    };
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => {
      window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
      window.removeEventListener("snipra:leads-korning-klar", uppdatera);
    };
  }, [hamta, hamtaUtkast, hamtaLeadrader, harJobb]);

  // ---- Utfall och besked ----------------------------------------------------------------------
  const [besked, setBesked] = useState<Besked | null>(null);
  const [statusbesked, setStatusbesked] = useState("");
  const saga = (b: Besked) => {
    setBesked(b);
    setStatusbesked(b.text);
    visa({ type: b.fel ? "error" : undefined, body: b.text, uniqueID: "crm-korning" });
  };

  // ---- Styrningen (LK-028, LK-029, LK-030) ------------------------------------------------
  const [styr, setStyr] = useState<Atgard | null>(null);
  const [fragaAvbryt, setFragaAvbryt] = useState(false);
  async function styrKorning(a: Atgard) {
    setFragaAvbryt(false);
    setStyr(a);
    try {
      await irisAnrop(`/leads/korningar/${encodeURIComponent(id)}/${a}`, { method: "POST" });
      saga({
        fel: false,
        text:
          a === "pausa"
            ? text({ sv: "Pausad. Inga nya bolag startas; de som redan researchas blir klara.", en: "Paused. No new companies start; those already in research finish." })
            : a === "aterupta"
              ? text({ sv: "Återupptagen. Iris letar vidare.", en: "Resumed. Iris keeps looking." })
              : a === "avbryt"
                ? text({ sv: "Avbryts. Körningen avslutas när bolagen som redan researchas är klara.", en: "Cancelling. The run ends once the companies already in research are done." })
                : text({ sv: "Körningen fortsätter. Iris letar efter de leads som återstår.", en: "The run continues. Iris is looking for the remaining leads." })
      });
      window.dispatchEvent(new CustomEvent("snipra:leads-korning-steg", { detail: "crm-iris-korning" }));
    } catch (e) {
      const t = e instanceof CrmFel && e.status === 404 ? { sv: "Körningen finns inte.", en: "The run does not exist." } : feltext(e);
      saga({ fel: true, text: a === "fortsatt" ? text({ sv: `Körningen gick inte att fortsätta. ${text(t)}`, en: `The run could not be continued. ${text(t)}` }) : text({ sv: `Körningen gick inte att styra. ${text(t)}`, en: `The run could not be controlled. ${text(t)}` }) });
    } finally {
      setStyr(null);
      await hamta();
    }
  }

  // ---- Skriv utkast till dem som saknar (LK-037) -------------------------------------------
  const [skriver, setSkriver] = useState(false);
  const skrivVarv = useRef(0);
  const foljSkrivningen = useCallback(async () => {
    const mitt = ++skrivVarv.current;
    setSkriver(true);
    for (let varv = 0; varv < SKRIV_VARV && mitt === skrivVarv.current; varv++) {
      await new Promise((r) => window.setTimeout(r, SKRIV_MS));
      if (mitt !== skrivVarv.current) return;
      const s = await hamtaUtkast();
      if (s && (s.antal.kan_skrivas ?? 0) === 0) break;
    }
    if (mitt !== skrivVarv.current) return;
    setSkriver(false);
    try {
      window.localStorage.removeItem(skrivnyckel(id));
    } catch {
      /* inget att glömma */
    }
    meddelaLeadsUppdaterade("crm-iris-korning");
  }, [hamtaUtkast, id]);
  // Skrivningen som pågick före en omladdning följs vidare (högst fem minuter gammal).
  useEffect(() => {
    try {
      const t = Number(window.localStorage.getItem(skrivnyckel(id)) ?? 0);
      if (t && Date.now() - t < SKRIV_MS * SKRIV_VARV) void foljSkrivningen();
    } catch {
      /* utan lagring följs skrivningen bara tills sidan laddas om */
    }
    return () => {
      skrivVarv.current += 1;
    };
  }, [id, foljSkrivningen]);
  async function skrivUtkast() {
    setSkriver(true);
    try {
      const s = await irisAnrop<{ count?: number }>(`/leads/korningar/${encodeURIComponent(id)}/utkast/skriv`, { method: "POST" });
      const n = s?.count ?? 0;
      saga({
        fel: false,
        text:
          n === 0
            ? text({ sv: "Inget utkast att skriva: alla leads med kontaktmejl har ett.", en: "No draft to write: every lead with a contact email has one." })
            : n === 1
              ? text({ sv: "Iris skriver 1 utkast. Det dyker upp här när det är klart, några minuter.", en: "Iris is writing 1 draft. It appears here when done, a few minutes." })
              : text({ sv: `Iris skriver ${n} utkast. De dyker upp här när de är klara, några minuter per bolag.`, en: `Iris is writing ${n} drafts. They appear here when done, a few minutes per company.` })
      });
      if (n > 0) {
        try {
          window.localStorage.setItem(skrivnyckel(id), String(Date.now()));
        } catch {
          /* följs ändå tills sidan laddas om */
        }
        void foljSkrivningen();
      } else setSkriver(false);
    } catch (e) {
      setSkriver(false);
      saga({ fel: true, text: text({ sv: `Utkasten kunde inte startas. ${text(feltext(e))}`, en: `The drafts could not be started. ${text(feltext(e))}` }) });
    }
  }

  // ---- Godkänn och skicka alla (LK-038) ----------------------------------------------------
  const [bekrafta, setBekrafta] = useState(false);
  const [utskick, setUtskick] = useState<Utskicksforlopp | null>(null);
  const [skickar, setSkickar] = useState(false);
  const foljUtskicket = useCallback(
    async (jobb: string) => {
      setSkickar(true);
      try {
        const u = await foljUtskick(jobb, setUtskick);
        const delar = [
          u.skickade === 1 ? text({ sv: "1 skickat", en: "1 sent" }) : text({ sv: `${u.skickade} skickade`, en: `${u.skickade} sent` }),
          u.vantar_pa_fonstret ? text({ sv: `${u.vantar_pa_fonstret} skickas i tur och ordning från kön (vardagar från 08:00)`, en: `${u.vantar_pa_fonstret} go out in turn from the queue (weekdays from 08:00)` }) : null
        ].filter(Boolean);
        const stoppade = u.stoppade.map((s) => `${s.company_name ?? "?"}${s.skal ? `: ${s.skal}` : ""}`);
        saga({
          fel: stoppade.length > 0,
          text: stoppade.length
            ? text({ sv: `${delar.join(", ")}. ${stoppade.length} skickades inte.`, en: `${delar.join(", ")}. ${stoppade.length} were not sent.` })
            : `${delar.join(", ")}.`,
          orsaker: stoppade
        });
        meddelaLeadsUppdaterade("crm-iris-korning");
      } catch (e) {
        saga({ fel: true, text: text(feltext(e)) });
      } finally {
        minnsUtskick(`korning:${id}`, null);
        setUtskick(null);
        setSkickar(false);
        void hamtaUtkast();
      }
    },
    [id, hamtaUtkast, text] // eslint-disable-line react-hooks/exhaustive-deps
  );
  useEffect(() => {
    const pagaende = mindUtskick(`korning:${id}`);
    if (pagaende) void foljUtskicket(pagaende);
  }, [id, foljUtskicket]);
  async function skickaAlla() {
    setBekrafta(false);
    setSkickar(true);
    try {
      const jobb = await startaUtskick(`/leads/korningar/${encodeURIComponent(id)}/utkast/skicka-jobb`);
      minnsUtskick(`korning:${id}`, jobb);
      await foljUtskicket(jobb);
    } catch (e) {
      setSkickar(false);
      saga({ fel: true, text: text(feltext(e)) });
    }
  }

  // ---- Utkastets panel (LK-035, LK-036): kön har texten utan signatur och svansen ----------
  const [kopost, setKopost] = useState<Kopost | null>(null);
  const [koSignatur, setKoSignatur] = useState<Signatur | null>(null);
  const [offer, setOffer] = useState<string | null>(null);
  useEffect(() => {
    void offertForUtkast().then(setOffer, () => setOffer(null));
  }, []);
  useEffect(() => {
    setKopost(null);
    if (!utkastId) return;
    let aktuell = true;
    irisAnrop<Kosvar>("/leads/queue")
      .then((s) => {
        if (!aktuell) return;
        const k = (s?.items ?? []).find((x) => x.id === utkastId) ?? null;
        if (s?.signatur) setKoSignatur(s.signatur);
        if (k) setKopost(k);
        else {
          oppnaUtkast(null);
          visa({ type: "error", body: text({ sv: "Utkastet väntar inte längre på granskning.", en: "The draft is no longer awaiting review." }), uniqueID: "crm-korning" });
        }
      })
      .catch((e) => aktuell && saga({ fel: true, text: text(feltext(e)) }));
    return () => {
      aktuell = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [utkastId]);
  const efterUtkast = () => {
    void hamtaUtkast();
    meddelaLeadsUppdaterade("crm-iris-korning");
  };
  async function godkann(k: Kopost): Promise<Besked | null> {
    const s = await irisAnrop<Sandutfall>(`/leads/queue/${encodeURIComponent(k.id)}/approve`, { method: "POST" });
    const mottagare = k.prospect_email ?? k.company_name ?? "";
    if (s.utfall === "sent" || s.utfall === "requeued") {
      oppnaUtkast(null);
      saga({
        fel: false,
        text:
          s.utfall === "sent"
            ? text({ sv: `Skickat till ${mottagare}.`, en: `Sent to ${mottagare}.` })
            : text({ sv: `Godkänt. Mejlet till ${mottagare} skickas i tur och ordning från kön (vardagar från 08:00).`, en: `Approved. The email to ${mottagare} goes out in turn from the queue (weekdays from 08:00).` })
      });
      efterUtkast();
      return null;
    }
    efterUtkast();
    const skal = skalUr(s);
    return { text: skal ? text({ sv: `Inte skickat: ${skal}`, en: `Not sent: ${skal}` }) : text({ sv: "Inte skickat.", en: "Not sent." }), fel: true };
  }
  async function avvisa(k: Kopost): Promise<Besked | null> {
    await irisAnrop(`/leads/queue/${encodeURIComponent(k.id)}/reject`, { method: "POST" });
    oppnaUtkast(null);
    saga({ fel: false, text: text({ sv: `Utkastet till ${k.company_name ?? k.prospect_email ?? ""} är avvisat och skickas inte.`, en: `The draft to ${k.company_name ?? k.prospect_email ?? ""} is rejected and will not be sent.` }) });
    efterUtkast();
    return null;
  }
  async function spara(k: Kopost, amne: string, brodtext: string) {
    await irisAnrop(`/leads/queue/${encodeURIComponent(k.id)}`, { method: "PUT", body: JSON.stringify({ subject: amne, brodtext }) });
    const s = await irisAnrop<Kosvar>("/leads/queue");
    const ny = (s?.items ?? []).find((x) => x.id === k.id);
    if (ny) setKopost(ny);
    efterUtkast();
  }

  // ---- Bortvalda (LK-031) -----------------------------------------------------------------
  const [sok, setSok] = useState("");
  const sokF = useDeferredValue(sok);
  const [steg, setSteg] = useState("");
  const tratt = useMemo(() => rad?.korning?.tratt ?? [], [rad]);
  const stegAntal = useMemo(() => {
    const n = new Map<string, number>();
    for (const t of tratt) n.set(t.steg, (n.get(t.steg) ?? 0) + 1);
    return n;
  }, [tratt]);
  const stegen = useMemo(() => [...STEGORDNING.filter((s) => stegAntal.has(s)), ...[...stegAntal.keys()].filter((s) => !STEGORDNING.includes(s))], [stegAntal]);
  const bortvalda = useMemo(() => {
    const s = sokF.trim().toLowerCase();
    return tratt.filter((t) => (!steg || t.steg === steg) && (!s || t.namn.toLowerCase().includes(s) || t.skal.toLowerCase().includes(s)));
  }, [tratt, steg, sokF]);
  const sidor = useSida(bortvalda.length, `${steg}|${sokF}`);
  const stegnamn = (s: string) => (STEG[s] ? text(STEG[s]) : s);

  // ---- Tabellerna ---------------------------------------------------------------------------
  const leads = useMemo(() => utkast?.leads ?? [], [utkast]);
  const vantar = leads.filter((l) => l.status === "vantar");
  const kanSkrivas = utkast?.antal.kan_skrivas ?? 0;

  const leadKolumner = useMemo<TableColumn<KorningsLead>[]>(
    () => [
      {
        key: "bolag",
        header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Kolumnrubrik>,
        width: proportional(1.3, { minWidth: 220 }),
        renderCell: (l) => {
          const namn = l.company_name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" });
          const p = leadrader?.get(l.prospect_id);
          const pafyllt = p?.pafylld ? pafyllnadSkal(p.pafylld_skal) : null;
          return (
            <span className="flex min-w-0 items-center gap-2">
              <Postchip namn={namn} onClick={() => oppnaLead(l.prospect_id)} label={text({ sv: `Öppna leadet ${namn}`, en: `Open the lead ${namn}` })} />
              {p?.pafylld ? (
                <span title={pafyllt ? text(pafyllt) : undefined} className="inline-flex shrink-0">
                  <Badge variant="yellow" label={text({ sv: "Påfyllt", en: "Filled in" })} />
                </span>
              ) : null}
            </span>
          );
        }
      },
      {
        key: "status",
        header: <Kolumnrubrik ikon={CircleDot}>{text({ sv: "Utkast", en: "Draft" })}</Kolumnrubrik>,
        width: pixel(196),
        renderCell: (l) => <Badge variant={UTKASTSTATUS[l.status].badge} label={text(UTKASTSTATUS[l.status].namn)} />
      },
      {
        key: "amne",
        header: <Kolumnrubrik ikon={Type}>{text({ sv: "Ämne eller skäl", en: "Subject or reason" })}</Kolumnrubrik>,
        width: proportional(2, { minWidth: 240 }),
        renderCell: (l) => {
          const t = l.status === "saknas" ? (l.notis ?? "") : l.status === "stoppat" && l.skal ? l.skal : (l.subject ?? "");
          return (
            <span title={t} className={l.status === "saknas" || l.status === "stoppat" ? "text-ink-muted" : "text-ink2"}>
              {t}
            </span>
          );
        }
      },
      {
        key: "mottagare",
        header: <Kolumnrubrik ikon={AtSign}>{text({ sv: "Mottagare", en: "Recipient" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 180 }),
        renderCell: (l) => <span className="text-ink-muted">{l.contact_email ?? text({ sv: "Ingen kontaktmejl", en: "No contact email" })}</span>
      },
      {
        key: "granska",
        header: <span className="sr-only">{text({ sv: "Handling", en: "Action" })}</span>,
        width: pixel(140),
        renderCell: (l) =>
          l.status === "vantar" && l.queue_item_id ? (
            <Button size="sm" variant="secondary" label={text({ sv: "Granska", en: "Review" })} icon={<Icon icon={FilePen} size="sm" />} onClick={() => oppnaUtkast(l.queue_item_id ?? null)} />
          ) : null
      }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, leadrader]
  );

  const bortvaldaKolumner = useMemo<TableColumn<Tratt & { nr: number }>[]>(
    () => [
      {
        key: "namn",
        header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 200 }),
        renderCell: (t) => <span className="font-semibold text-ink">{t.namn}</span>
      },
      {
        key: "steg",
        header: <Kolumnrubrik ikon={Filter}>{text({ sv: "Steg", en: "Step" })}</Kolumnrubrik>,
        width: pixel(176),
        renderCell: (t) => <Badge variant="neutral" label={stegnamn(t.steg)} />
      },
      {
        key: "skal",
        header: <Kolumnrubrik ikon={SearchX}>{text({ sv: "Skäl", en: "Reason" })}</Kolumnrubrik>,
        width: proportional(2.4, { minWidth: 280 }),
        renderCell: (t) => (
          <span className="flex min-w-0 flex-col gap-0.5 py-1">
            <span className="text-ink2">{t.skal}</span>
            {t.belagg ? <span className="text-[0.8125rem] text-ink-muted">{t.belagg}</span> : null}
          </span>
        )
      }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text]
  );

  // ---- Delarna ------------------------------------------------------------------------------
  const k = rad?.korning ?? null;
  // På telefon står bara tiden: "Körning" och tiden ryms inte på en rad i Fraunces.
  const rubrik = rad && smal ? korningstid(rad.created_at, locale) : rad ? text({ sv: `Körning ${korningstid(rad.created_at, locale)}`, en: `Run ${korningstid(rad.created_at, locale)}` }) : text({ sv: "Körning", en: "Run" });
  const nBortvalda = antalBortvalda(k);
  const nLeads = utkast ? leads.length : antalJobb(k);
  const av = { isDisabled: !skriv.far, tooltip: skriv.skal ?? undefined };
  const tillbaka = <Button variant="ghost" label={text({ sv: "Alla körningar", en: "All runs" })} icon={<Icon icon={ArrowLeft} size="sm" />} href={listvag} />;
  const vyer: { v: Flik; namn: Localized; antal?: number }[] = [
    { v: "oversikt", namn: { sv: "Översikt", en: "Overview" } },
    { v: "leads", namn: { sv: "Leads", en: "Leads" }, antal: rad?.scope === "batch" ? nLeads : undefined },
    { v: "bortvalda", namn: { sv: "Bortvalda", en: "Dropped" }, antal: nBortvalda }
  ];

  const talruta = (etikett: Localized, varde: string, under?: string | null) => (
    <div className="crm-talruta">
      <div className="text-[0.8125rem] text-ink-muted">{text(etikett)}</div>
      <div className="crm-tal text-[1.5rem] leading-tight tabular-nums text-ink">{varde}</div>
      {under ? <div className="text-[0.75rem] text-ink-muted">{under}</div> : null}
    </div>
  );

  const besketsRuta = besked ? (
    <Banner
      status={besked.fel ? "error" : "info"}
      container="card"
      title={besked.text}
      description={
        besked.orsaker?.length ? (
          <ul className="mt-1 flex flex-col gap-1">
            {besked.orsaker.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        ) : undefined
      }
      endContent={<Button size="sm" variant="ghost" label={text({ sv: "Stäng", en: "Close" })} onClick={() => setBesked(null)} />}
    />
  ) : null;

  // Översikten: förloppet eller utfallet, tratten och vad körningen kördes med.
  const oversikt = rad ? (
    <div className="flex flex-col gap-4 pt-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[0.875rem] text-ink-muted">
        <Korningsstatus rad={rad} />
        <span className="text-ink2">{text(korningsTyp(rad))}</span>
        {rad.is_test ? <Badge variant="neutral" label={text({ sv: "Test", en: "Test" })} /> : null}
        {k?.fortsatt ? <span>{k.fortsatt === 1 ? text({ sv: "Fortsatt en gång", en: "Continued once" }) : text({ sv: `Fortsatt ${k.fortsatt} gånger`, en: `Continued ${k.fortsatt} times` })}</span> : null}
      </div>
      {besketsRuta}
      {rad.status === "failed" ? (
        <Banner status="error" container="card" title={text({ sv: "Körningen misslyckades", en: "The run failed" })} description={rad.error ?? text({ sv: "Körningen avbröts.", en: "The run was aborted." })} />
      ) : null}
      {k?.vilande && pagar(rad) ? (
        // Regel 23: Iris levererar aldrig under beställt antal. Körningen vilar och letar vidare en gång per dygn.
        <Banner
          status="warning"
          container="card"
          title={text({ sv: "Iris letar vidare", en: "Iris keeps looking" })}
          description={`${vilaText(k, text) ?? ""}. ${text({ sv: "Körningen levererar aldrig under beställt antal. Den vilar nu och letar vidare en gång per dygn, och leads som hittas läggs till här.", en: "The run never delivers under the ordered number. It is resting now and keeps looking once a day, and leads it finds are added here." })}`}
        />
      ) : null}
      {kanFortsatta(rad) && k ? (
        <Banner
          status="warning"
          container="card"
          title={text({ sv: `Körningen levererade ${k.levererade} av ${k.mal}`, en: `The run delivered ${k.levererade} of ${k.mal}` })}
          description={text({
            sv: `Fortsätt så letar Iris vidare efter de ${Math.max(0, k.mal - k.levererade)} som återstår, utan att pröva samma bolag igen.`,
            en: `Continue and Iris keeps looking for the remaining ${Math.max(0, k.mal - k.levererade)}, without trying the same companies again.`
          })}
          endContent={<Button size="sm" variant="primary" label={text({ sv: "Fortsätt körningen", en: "Continue the run" })} icon={<Icon icon={RotateCw} size="sm" />} isLoading={styr === "fortsatt"} {...av} onClick={() => void styrKorning("fortsatt")} />}
        />
      ) : null}

      {k ? (
        <Panelkort
          id="crm-korning-forlopp"
          titel={pagar(rad) ? text({ sv: "Förlopp", en: "Progress" }) : text({ sv: "Utfall", en: "Outcome" })}
          hoger={<span className="text-[0.875rem] tabular-nums text-ink-muted">{text({ sv: `${tal(k.levererade)} av ${tal(k.mal)} leads`, en: `${tal(k.levererade)} of ${tal(k.mal)} leads` })}</span>}
        >
          <div className="flex flex-col gap-4">
            <ProgressBar label={text({ sv: "Leads klara av beställt antal", en: "Leads done of the ordered number" })} isLabelHidden value={k.levererade} max={Math.max(k.mal, 1)} />
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="status" aria-live="polite">
              {talruta({ sv: "Leads klara", en: "Leads done" }, text({ sv: `${tal(k.levererade)} av ${tal(k.mal)}`, en: `${tal(k.levererade)} of ${tal(k.mal)}` }))}
              {talruta({ sv: "Bolag undersökta", en: "Companies researched" }, tal(k.undersokta), k.tak ? text({ sv: `tak ${tal(k.tak)}`, en: `cap ${tal(k.tak)}` }) : null)}
              {talruta({ sv: "Bortvalda", en: "Dropped" }, tal(nBortvalda))}
              {gar ? (
                <div className="crm-talruta">
                  <div className="text-[0.8125rem] text-ink-muted">{text({ sv: "Just nu", en: "Right now" })}</div>
                  <div className="text-[1rem] font-semibold leading-tight text-ink">
                    {k.styrning === "paus" ? text({ sv: "Pausad", en: "Paused" }) : k.styrning === "avbruten" ? text({ sv: "Avbryts", en: "Cancelling" }) : <Roterande fraser={k.pagaende ? RESEARCH_FRASER : LETAR_FRASER} />}
                  </div>
                  <div className="text-[0.75rem] text-ink-muted">
                    {k.pagaende ? text({ sv: `${tal(k.pagaende)} under research`, en: `${tal(k.pagaende)} in research` }) : text({ sv: `sökrunda ${tal((k.rundor ?? 0) + 1)}`, en: `search round ${tal((k.rundor ?? 0) + 1)}` })}
                  </div>
                </div>
              ) : (
                talruta({ sv: "Sökrundor", en: "Search rounds" }, tal(k.rundor ?? 0))
              )}
            </div>
            {gar ? (
              <p className="text-[0.875rem] text-ink-muted">
                {k.styrning === "paus"
                  ? text({ sv: "Pausad. Inga nya bolag startas; de som redan researchas blir klara.", en: "Paused. No new companies start; those already in research finish." })
                  : k.styrning === "avbruten"
                    ? text({ sv: "Avbryts. Körningen avslutas när bolagen som redan researchas är klara.", en: "Cancelling. The run ends once the companies already in research are done." })
                    : text({ sv: "Körningen fortsätter på servern. Du kan lämna sidan och komma tillbaka hit.", en: "The run continues on the server. You can leave this page and come back." })}
              </p>
            ) : null}
            {k.klar && k.sammanfattning ? <p className="max-w-[80ch] text-[0.9375rem] leading-relaxed text-ink">{k.sammanfattning}</p> : null}
            {k.klar && k.slut_orsak ? (
              <p className="text-[0.875rem] text-ink-muted">
                {SLUT_ETIKETT[k.slut_orsak] ? text(SLUT_ETIKETT[k.slut_orsak]) : k.slut_orsak}
                {k.flaskhals && k.levererade < k.mal ? text({ sv: `. Det som strypte mest: ${k.flaskhals.toLocaleLowerCase("sv")}.`, en: `. The biggest bottleneck: ${k.flaskhals.toLocaleLowerCase("sv")}.` }) : null}
              </p>
            ) : null}
            {kanStyras(rad) ? (
              <div role="group" aria-label={text({ sv: "Styr körningen", en: "Control the run" })} className="flex flex-wrap gap-2">
                {k.styrning === "paus" ? (
                  <Button variant="secondary" size="md" label={text({ sv: "Återuppta", en: "Resume" })} icon={<Icon icon={Play} size="sm" />} isLoading={styr === "aterupta"} {...av} isDisabled={av.isDisabled || styr != null} onClick={() => void styrKorning("aterupta")} />
                ) : (
                  <Button variant="secondary" size="md" label={text({ sv: "Pausa", en: "Pause" })} icon={<Icon icon={Pause} size="sm" />} isLoading={styr === "pausa"} {...av} isDisabled={av.isDisabled || styr != null} onClick={() => void styrKorning("pausa")} />
                )}
                <Button variant="secondary" size="md" className="crm-farlig" label={text({ sv: "Avbryt körningen", en: "Cancel the run" })} icon={<Icon icon={Square} size="sm" />} isLoading={styr === "avbryt"} {...av} isDisabled={av.isDisabled || styr != null} onClick={() => setFragaAvbryt(true)} />
              </div>
            ) : null}
          </div>
        </Panelkort>
      ) : rad.scope === "lista" ? (
        <Banner status="info" container="card" title={text({ sv: "En leadslista", en: "A lead list" })} description={text({ sv: "Listans rader står under Listor, inte här.", en: "The list's rows are under Lists, not here." })} />
      ) : pagar(rad) ? (
        <Panelkort id="crm-korning-forlopp" titel={text({ sv: "Förlopp", en: "Progress" })}>
          <div className="flex flex-col gap-3" role="status">
            <ProgressBar label={text({ sv: "Körningens förlopp", en: "Progress of the run" })} isLabelHidden isIndeterminate />
            <p className="text-[0.875rem] text-ink-muted">{text({ sv: "Iris letar bolag som matchar målgruppen. Sökningen tar oftast en till tre minuter.", en: "Iris is looking for companies that match the target group. The search usually takes one to three minutes." })}</p>
          </div>
        </Panelkort>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {k ? (
          <Panelkort
            id="crm-korning-tratt"
            titel={text({ sv: "Tratten", en: "The funnel" })}
            hoger={nBortvalda > 0 ? <Button size="sm" variant="ghost" label={text({ sv: "Se de bortvalda", en: "See the dropped" })} onClick={() => setFlik("bortvalda")} /> : undefined}
            fot={text({ sv: "Registrets och Jevs bortval kostar inget. Ett bolag prövas aldrig två gånger.", en: "The register's and Jev's drops cost nothing. A company is never tried twice." })}
          >
            <ul className="flex flex-col">
              <li className="flex items-baseline justify-between gap-3 border-b border-ink/[0.07] py-2">
                <span className="text-[0.875rem] font-semibold text-ink">{text({ sv: "Undersökta bolag", en: "Companies researched" })}</span>
                <span className="text-[0.875rem] tabular-nums text-ink">{tal(k.undersokta)}</span>
              </li>
              {stegen.map((s) => (
                <li key={s} className="flex flex-col gap-1.5 border-b border-ink/[0.07] py-2">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="text-[0.875rem] text-ink2">{stegnamn(s)}</span>
                    <span className="text-[0.875rem] tabular-nums text-ink">{tal(stegAntal.get(s) ?? 0)}</span>
                  </span>
                  <ProgressBar label={stegnamn(s)} isLabelHidden value={stegAntal.get(s) ?? 0} max={Math.max(tratt.length, 1)} />
                  {STEG_VAD[s] ? <span className="text-[0.8125rem] text-ink-muted">{text(STEG_VAD[s])}</span> : null}
                </li>
              ))}
              {tratt.length === 0 ? <li className="border-b border-ink/[0.07] py-2 text-[0.875rem] text-ink-muted">{text({ sv: "Inget bolag valdes bort.", en: "No company was dropped." })}</li> : null}
              <li className="flex items-baseline justify-between gap-3 py-2">
                <span className="text-[0.875rem] font-semibold text-ink">{text({ sv: "Leads klara", en: "Leads done" })}</span>
                <span className="text-[0.875rem] tabular-nums text-ink">{text({ sv: `${tal(k.levererade)} av ${tal(k.mal)}`, en: `${tal(k.levererade)} of ${tal(k.mal)}` })}</span>
              </li>
            </ul>
          </Panelkort>
        ) : null}
        {k ? <KordesMed rad={rad} /> : null}
      </div>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.8125rem] text-ink-muted">
        <Kopierbar varde={rad.job_id} label={text({ sv: "Kopiera körningens id", en: "Copy the run's id" })} />
        {rad.updated_at ? (
          <span>
            {text({ sv: "Uppdaterad ", en: "Updated " })}
            <Timestamp value={rad.updated_at} format="relative" isLive={gar} />
          </span>
        ) : null}
      </p>
    </div>
  ) : null;

  // Leads: körningens leads med utkastets läge och de två handlingarna för alla.
  const sammanfattning = (
    [
      ["vantar", { sv: "väntar på dig", en: "waiting for you" }],
      ["skickat", { sv: "skickade", en: "sent" }],
      ["godkant", { sv: "godkända", en: "approved" }],
      ["saknas", { sv: "utan utkast", en: "without a draft" }]
    ] as [keyof KorningsUtkastSvar["antal"], Localized][]
  ).filter(([s]) => (utkast?.antal[s] ?? 0) > 0);

  const leadsFot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-tal">{tal(leads.length)}</span> <span className="crm-raknefot-etikett">{leads.length === 1 ? text({ sv: "lead", en: "lead" }) : text({ sv: "leads", en: "leads" })}</span>
      </span>
      {sammanfattning.map(([s, namn]) => (
        <span key={s}>
          <span className="crm-raknefot-tal">{tal(utkast?.antal[s] ?? 0)}</span> <span className="crm-raknefot-etikett">{text(namn)}</span>
        </span>
      ))}
      {skriver ? (
        <span className="inline-flex items-center gap-2">
          <span className="crm-raknefot-etikett">{text({ sv: "Iris skriver, listan uppdateras var femte sekund", en: "Iris is writing, the list updates every five seconds" })}</span>
        </span>
      ) : null}
    </div>
  );

  const leadsInnehall = !rad ? null : rad.scope === "lista" ? (
    <div className="py-10">
      <EmptyState icon={<Icon icon={Radar} size="lg" color="secondary" />} title={text({ sv: "Raderna finns under Listor", en: "The rows are under Lists" })} description={text({ sv: "En leadslista har inga leads i körningen. Listan öppnas under Listor.", en: "A lead list has no leads in the run. The list opens under Lists." })} />
    </div>
  ) : !harJobb ? (
    <div className="py-10">
      <EmptyState
        icon={<Icon icon={Radar} size="lg" color="secondary" />}
        title={gar ? text({ sv: "Inga leads än", en: "No leads yet" }) : text({ sv: "Inga leads i körningen", en: "No leads in the run" })}
        description={gar ? text({ sv: "Leads dyker upp här bolag för bolag medan Iris researchar.", en: "Leads show up here company by company while Iris researches." }) : text({ sv: "Inga bolag undersöktes i körningen.", en: "No companies were researched in the run." })}
      />
    </div>
  ) : utkastFel && !utkast ? (
    <div className="p-4 sm:p-6">
      <Felruta fel={utkastFel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamtaUtkast()} />} />
    </div>
  ) : !utkast ? (
    <Tabellskelett rader={6} kolumner={smal ? 2 : 5} markering={false} label={text({ sv: "Hämtar körningens leads", en: "Loading the run's leads" })} />
  ) : (
    <>
      {vantar.length > 0 || kanSkrivas > 0 || besked ? (
        <div className="flex flex-col gap-3 px-4 py-3 sm:px-6">
          {besketsRuta}
          {vantar.length > 0 || kanSkrivas > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              {vantar.length > 0 ? (
                <Button
                  variant="primary"
                  size="md"
                  icon={<Icon icon={Check} size="sm" />}
                  label={
                    skickar && utskick?.totalt
                      ? text({ sv: `Skickar ${utskick.klara} av ${utskick.totalt}`, en: `Sending ${utskick.klara} of ${utskick.totalt}` })
                      : text({ sv: `Godkänn och skicka alla ${vantar.length}`, en: `Approve and send all ${vantar.length}` })
                  }
                  isLoading={skickar}
                  {...av}
                  isDisabled={av.isDisabled || skickar || skriver}
                  onClick={() => setBekrafta(true)}
                />
              ) : null}
              {kanSkrivas > 0 ? (
                <Button
                  variant="secondary"
                  size="md"
                  icon={<Icon icon={PenLine} size="sm" />}
                  label={skriver ? text({ sv: "Iris skriver", en: "Iris is writing" }) : kanSkrivas === 1 ? text({ sv: "Skriv utkast till 1 som saknar", en: "Write a draft for 1 missing" }) : text({ sv: `Skriv utkast till ${kanSkrivas} som saknar`, en: `Write drafts for ${kanSkrivas} missing` })}
                  isLoading={skriver}
                  {...av}
                  isDisabled={av.isDisabled || skickar || skriver}
                  onClick={() => void skrivUtkast()}
                />
              ) : null}
              {vantar.length > 0 ? <span className="text-[0.8125rem] text-ink-muted">{text({ sv: "Går genom sändspärrarna och skickas i tur och ordning från kön, vardagar från 08:00.", en: "Passes the send guards and goes out in turn from the queue, weekdays from 08:00." })}</span> : null}
            </div>
          ) : null}
          {skickar && utskick?.totalt ? <ProgressBar label={text({ sv: "Utskickets förlopp", en: "Progress of the send" })} isLabelHidden value={utskick.klara} max={Math.max(utskick.totalt, 1)} /> : null}
        </div>
      ) : null}
      {leads.length === 0 ? (
        <div className="py-10">
          <EmptyState icon={<Icon icon={Radar} size="lg" color="secondary" />} title={text({ sv: "Inga leads i körningen", en: "No leads in the run" })} description={text({ sv: "Bolag som researchen valde bort står under Bortvalda.", en: "Companies the research dropped are under Dropped." })} />
        </div>
      ) : smal ? (
        <>
          <div className="px-2">
            <List hasDividers density="balanced" edge="padded">
              {leads.map((l) => {
                const namn = l.company_name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" });
                const p = leadrader?.get(l.prospect_id);
                return (
                  <ListItem
                    key={l.prospect_id}
                    label={
                      <span className="inline-flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">{namn}</span>
                        {p?.pafylld ? <Badge variant="yellow" label={text({ sv: "Påfyllt", en: "Filled in" })} /> : null}
                      </span>
                    }
                    description={l.status === "saknas" ? (l.notis ?? "") : (l.subject ?? l.contact_email ?? "")}
                    endContent={<Badge variant={UTKASTSTATUS[l.status].badge} label={text(UTKASTSTATUS[l.status].namn)} />}
                    onClick={() => (l.status === "vantar" && l.queue_item_id ? oppnaUtkast(l.queue_item_id) : oppnaLead(l.prospect_id))}
                    isSelected={leadId === l.prospect_id || (l.queue_item_id != null && utkastId === l.queue_item_id)}
                  />
                );
              })}
            </List>
          </div>
          {leadsFot}
        </>
      ) : (
        <div className="crm-tabell crm-tabell-utan-val">
          <Table<KorningsLead> data={leads} columns={leadKolumner} idKey="prospect_id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
          {leadsFot}
        </div>
      )}
    </>
  );

  const bortvaldaFot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span>{" "}
        <span className="crm-raknefot-tal">{bortvalda.length ? `${tal(sidor.fran + 1)}–${tal(sidor.till)}` : "0"}</span>{" "}
        <span className="crm-raknefot-etikett">{text({ sv: "av", en: "of" })}</span> <span className="crm-raknefot-tal">{tal(bortvalda.length)}</span>
      </span>
      {sidor.antalSidor > 1 ? (
        <span className="ml-auto">
          <Pagination page={sidor.sida + 1} onChange={(n) => sidor.setSida(n - 1)} totalItems={bortvalda.length} pageSize={SIDSTORLEK} variant="compact" size="sm" label={text({ sv: "Sidor", en: "Pages" })} />
        </span>
      ) : null}
    </div>
  );
  const sidansBortvalda = bortvalda.slice(sidor.fran, sidor.till).map((t, i) => ({ ...t, nr: sidor.fran + i }));
  const bortvaldaInnehall =
    tratt.length === 0 ? (
      <div className="py-10">
        <EmptyState icon={<Icon icon={SearchX} size="lg" color="secondary" />} title={text({ sv: "Inget bolag valdes bort", en: "No company was dropped" })} description={gar ? text({ sv: "Bortvalda bolag står här med steg och skäl medan körningen går.", en: "Dropped companies show here with step and reason while the run goes on." }) : text({ sv: "Varje bolag körningen prövade gick vidare.", en: "Every company the run tried went through." })} />
      </div>
    ) : bortvalda.length === 0 ? (
      <div className="py-10">
        <EmptyState icon={<Icon icon={SearchX} size="lg" color="secondary" />} title={text({ sv: "Inga bortvalda i urvalet", en: "No dropped companies in the selection" })} actions={<Button variant="secondary" label={text({ sv: "Visa alla", en: "Show all" })} onClick={() => { setSok(""); setSteg(""); }} />} />
      </div>
    ) : smal ? (
      <>
        <div className="px-2">
          <List hasDividers density="balanced" edge="padded">
            {sidansBortvalda.map((t) => (
              <ListItem key={`${t.namn}-${t.nr}`} label={<span className="font-semibold text-ink">{t.namn}</span>} description={[t.skal, t.belagg].filter(Boolean).join(" ")} endContent={<Badge variant="neutral" label={stegnamn(t.steg)} />} />
            ))}
          </List>
        </div>
        {bortvaldaFot}
      </>
    ) : (
      <div className="crm-tabell crm-tabell-utan-val">
        <Table<Tratt & { nr: number }> data={sidansBortvalda} columns={bortvaldaKolumner} idKey="nr" density="balanced" dividers="rows" hasHover textOverflow="wrap" />
        {bortvaldaFot}
      </div>
    );

  const laddar = rad == null && !fel;
  return (
    <Sida
      objekt="korningar"
      rubrik={rubrik}
      atgarder={tillbaka}
      utfyllnad={flik === "oversikt" ? "sida" : "tabell"}
      vyrad={
        rad ? (
          smal ? (
            <Selector label={text({ sv: "Visa", en: "Show" })} isLabelHidden variant="secondary" size="md" value={flik} onChange={(v) => v && setFlik(v as Flik)} options={vyer.map((v) => ({ value: v.v, label: v.antal != null ? `${text(v.namn)}  ${tal(v.antal)}` : text(v.namn) }))} />
          ) : (
            <Vyval value={flik} onChange={setFlik} label={text({ sv: "Visa", en: "Show" })} val={vyer.map((v) => ({ v: v.v, namn: text(v.namn), antal: v.antal != null ? tal(v.antal) : undefined }))} />
          )
        ) : undefined
      }
      vyradHoger={
        rad && flik === "bortvalda" && tratt.length > 0 ? (
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
            <div className="w-full min-w-0 sm:w-[220px] sm:flex-none">
              <TextInput type="search" label={text({ sv: "Sök bland de bortvalda", en: "Search the dropped" })} isLabelHidden placeholder={text({ sv: "Bolag eller skäl", en: "Company or reason" })} startIcon="search" hasClear value={sok} onChange={setSok} width="100%" controlClassName="crm-sokfalt" />
            </div>
            <Selector
              label={text({ sv: "Steg", en: "Step" })}
              isLabelHidden
              variant="ghost"
              size="md"
              startIcon={Filter}
              value={steg || "alla"}
              onChange={(v) => setSteg(!v || v === "alla" ? "" : String(v))}
              options={[{ value: "alla", label: text({ sv: "Alla steg", en: "All steps" }) }, ...stegen.map((s) => ({ value: s, label: `${stegnamn(s)}  ${tal(stegAntal.get(s) ?? 0)}` }))]}
            />
          </div>
        ) : undefined
      }
    >
      <div role="status" className="sr-only">
        {statusbesked}
      </div>
      {fel && !rad ? (
        <div className="p-4 sm:p-6">
          {fel instanceof CrmFel && fel.status === 404 ? (
            <EmptyState icon={<Icon icon={Radar} size="lg" color="secondary" />} title={text({ sv: "Körningen finns inte", en: "The run does not exist" })} description={text({ sv: "Den kan ha städats bort, eller hör till en annan arbetsyta.", en: "It may have been cleaned up, or belongs to another workspace." })} actions={tillbaka} />
          ) : (
            <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
          )}
        </div>
      ) : laddar ? (
        <div className="flex flex-col gap-4 pt-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar körningen", en: "Loading the run" })}>
          <Skeleton width={220} height={22} radius="rounded" />
          <Skeleton width="100%" height={140} radius={4} />
          <Skeleton width="100%" height={200} radius={4} />
        </div>
      ) : flik === "oversikt" ? (
        oversikt
      ) : flik === "leads" ? (
        leadsInnehall
      ) : (
        bortvaldaInnehall
      )}

      <LeadPanel id={leadId} listrad={leadId ? (leadrader?.get(leadId) ?? null) : null} bas={bas} stang={() => oppnaLead(null)} andrat={() => meddelaLeadsUppdaterade(PANELENS_KALLA)} />
      <UtkastPanel
        post={kopost ? { slag: "granska", ko: kopost } : null}
        signatur={koSignatur ?? utkast?.signatur ?? null}
        offer={offer}
        bas={bas}
        skriv={skriv}
        stang={() => oppnaUtkast(null)}
        spara={spara}
        godkann={godkann}
        avvisa={avvisa}
        skickaNu={() => undefined}
        andraTid={() => undefined}
        tillbaka={() => undefined}
        uppfoljning={() => undefined}
      />
      <Bekraftelse
        oppen={bekrafta}
        titel={vantar.length === 1 ? text({ sv: "Godkänn och skicka 1 utkast", en: "Approve and send 1 draft" }) : text({ sv: `Godkänn och skicka ${vantar.length} utkast`, en: `Approve and send ${vantar.length} drafts` })}
        poster={vantar.map((l) => ({ id: l.prospect_id, namn: l.company_name ?? l.contact_email ?? "?", under: l.contact_email, amne: l.subject, utdrag: forstaMening(l.body) }))}
        forklaring={text({
          sv: "Varje mejl går genom sändspärrarna och skickas i tur och ordning från kön, vardagar från 08:00. Ett mejl som en spärr stoppar står kvar med skälet.",
          en: "Every email passes the send guards and goes out in turn from the queue, weekdays from 08:00. An email a guard stops stays with the reason."
        })}
        handling={text({ sv: "Godkänn och skicka", en: "Approve and send" })}
        upptagen={skickar}
        bekrafta={() => void skickaAlla()}
        stang={() => setBekrafta(false)}
      />
      <AlertDialog
        isOpen={fragaAvbryt}
        onOpenChange={(o) => !o && setFragaAvbryt(false)}
        title={text({ sv: "Avbryta körningen?", en: "Cancel the run?" })}
        description={text({ sv: "Bolag som redan researchas blir klara, inga nya startas. Det går inte att ångra.", en: "Companies already in research finish, no new ones start. This cannot be undone." })}
        actionLabel={text({ sv: "Avbryt körningen", en: "Cancel the run" })}
        cancelLabel={text({ sv: "Behåll körningen", en: "Keep the run" })}
        onAction={() => void styrKorning("avbryt")}
      />
    </Sida>
  );
}

/** Vad körningen kördes med (LK-013): beställt antal, omfattning, struktur och filtret, med formulärets ord. */
function KordesMed({ rad }: Readonly<{ rad: KorningsRad }>) {
  const { text, locale } = useLocale();
  const k = rad.korning;
  if (!k) return null;
  const etik = icpEtiketter(locale);
  const o = k.overrides ?? null;
  const rader: [string, string][] = [
    [text({ sv: "Beställt", en: "Ordered" }), k.mal === 1 ? text({ sv: "1 lead", en: "1 lead" }) : text({ sv: `${k.mal} leads`, en: `${k.mal} leads` })],
    [text({ sv: "Omfattning", en: "Scope" }), k.scope === "research_and_draft" ? text({ sv: "Research och utkast", en: "Research and drafts" }) : text({ sv: "Bara research", en: "Research only" })],
    ...(k.scope === "research_and_draft" ? ([[text({ sv: "Mejlens struktur", en: "Email structure" }), k.struktur === "b" ? text({ sv: "B, kort och rakt på", en: "B, short and direct" }) : text({ sv: "A, utförlig", en: "A, detailed" })]] as [string, string][]) : []),
    ...(rad.is_test ? ([[text({ sv: "Märkt", en: "Marked" }), text({ sv: "Testkörning", en: "Test run" })]] as [string, string][]) : [])
  ];
  const filter: [string, string][] = o
    ? ([
        ["industries", etik.industries.label],
        ["exclude_industries", etik.exclude_industries.label],
        ["geography", etik.geography.label],
        ["roles", etik.roles.label],
        ["must_have", etik.must_have.label],
        ["deal_breakers", etik.deal_breakers.label],
        ["anstallda_min", text({ sv: "Anställda, minst", en: "Employees, at least" })],
        ["anstallda_max", text({ sv: "Anställda, högst", en: "Employees, at most" })]
      ] as [keyof typeof o, string][])
        .filter(([n]) => o[n] != null)
        .map(([n, etikett]) => [etikett, Array.isArray(o[n]) ? (o[n] as string[]).join(", ") : String(o[n])])
    : [];
  return (
    <Panelkort id="crm-korning-med" titel={text({ sv: "Kördes med", en: "Run with" })} fot={o ? text({ sv: "Filtret gällde bara den här körningen.", en: "The filter applied to this run only." }) : text({ sv: "Sparad målgrupp användes.", en: "The saved target group was used." })}>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2 text-[0.875rem]">
        {[...rader, ...filter].map(([e, v]) => (
          <div key={e} className="contents">
            <dt className="text-ink-muted">{e}</dt>
            <dd className="min-w-0 break-words text-ink">{v}</dd>
          </div>
        ))}
      </dl>
    </Panelkort>
  );
}

