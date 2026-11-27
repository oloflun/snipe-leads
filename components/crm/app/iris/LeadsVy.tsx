"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Archive,
  ArchiveRestore,
  ArrowRightLeft,
  Bookmark,
  Building2,
  Clock,
  FilePen,
  FlaskConical,
  Gauge,
  Globe,
  ListFilter,
  ListTodo,
  MoreHorizontal,
  PhoneCall,
  Plug,
  RefreshCw,
  SearchX,
  Send,
  Sparkles,
  Tag,
  Target,
  Trash2,
  Truck
} from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { DropdownMenu, type DropdownMenuOption } from "@astryxdesign/core/DropdownMenu";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { List, ListItem } from "@astryxdesign/core/List";
import { Pagination } from "@astryxdesign/core/Pagination";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, TableSelectionToolbar, pixel, proportional, useTableSelection, useTableSelectionState, type TableColumn } from "@astryxdesign/core/Table";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { SIDSTORLEK, useSida, useSidaFor } from "@/components/leads/sidindelning";
import { pafyllnadSkal } from "@/components/leads/pafyllnad";
import { Bekraftelse } from "@/components/crm/app/iris/Bekraftelse";
import { LeadPanel } from "@/components/crm/app/iris/LeadPanel";
import { Kallpiller, Kolumnrubrik, Postchip, Prick, Tabellskelett, Vyval, grannfokus, tonFor, tonklass, useSkrivratt, useSmal, utanBolagsform } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { CrmFel } from "@/lib/crm/api";
import { LEADS_UPPDATERADE, PROCESSA_OMGANG, allaLeads, irisAnrop, meddelaLeadsUppdaterade } from "@/lib/crm/iris/anrop";
import {
  FORE_UTSKICK,
  KONTAKTVAG,
  LEAD_TYP_ETIKETT,
  STATUSTON,
  STATUS_ETIKETT,
  SYSTEMSTATUS,
  UPPFOLJNING_HOPPAD,
  UTAN_UTKAST,
  UTKASTTON,
  VALBARA,
  domanAv,
  forstaMening,
  harFattMejl,
  kanSkickas,
  kontaktvag,
  leadTyp,
  matcharSok,
  nivaEtikett,
  nyastForst,
  obedomd,
  poang,
  sortera,
  utkastText,
  iResearch,
  type Lead,
  type LeadTyp,
  type Leaduppgift,
  type Sparadvy,
  type Vyfilter
} from "@/lib/crm/iris/lead";
import { band, betyg, forstaBrist, nagonHarBetyg, type Betygsband } from "@/lib/crm/iris/webb";
import { useLocale, type Localized } from "@/lib/i18n";

/** Vyerna i vyraden: Att bearbeta per status, Testyta, Bortvalda och Arkiverade. */
type Vy = "alla" | "researching" | "new" | "ready" | "testyta" | "bortvalda" | "arkiverade";
type Sortering = "nyast" | "poang" | "webb";
type Atgard = "skicka" | "skapa" | "skapa-om" | "uppfoljning" | "arkivera" | "aterstall" | "ta-bort" | "testyta" | "skarp" | "bearbeta" | "main";
type Bekraftas = { typ: "skicka" | "skapa-om" | "ta-bort" | "bearbeta"; rader: Lead[] };

/** Medan något researchas eller ett utkast skrivs hämtas listan tyst så här ofta (LR-038). */
const LIVE_MS = 4000;

const NIVAER: { v: "" | "A" | "B"; namn: Localized }[] = [
  { v: "", namn: { sv: "Alla nivåer", en: "All levels" } },
  { v: "A", namn: { sv: "Stark", en: "Strong" } },
  { v: "B", namn: { sv: "Möjlig", en: "Possible" } }
];
const TYPER: ("" | LeadTyp)[] = ["", "iris", "lista", "import", "inkorg"];
const BETYGSBAND: { v: "" | Betygsband; namn: Localized }[] = [
  { v: "", namn: { sv: "Alla betyg", en: "All scores" } },
  { v: "lag", namn: { sv: "Betyg 1 till 4", en: "Score 1 to 4" } },
  { v: "mellan", namn: { sv: "Betyg 5 till 6", en: "Score 5 to 6" } },
  { v: "hog", namn: { sv: "Betyg 7 till 10", en: "Score 7 to 10" } }
];

/** Kort tid för tabellen (LR-036): "nu", "12 min", "20 h", "3 d" upp till 29 dagar, sedan datum. Hela tiden står i title. */
function kortTid(iso: string, locale: "sv" | "en"): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (!Number.isFinite(ms)) return "";
  const min = Math.floor(ms / 60_000);
  if (min < 1) return locale === "en" ? "now" : "nu";
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} h`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} d`;
  return new Date(iso).toLocaleDateString(locale === "en" ? "en-GB" : "sv-SE", { day: "numeric", month: "short" });
}

/** Ett fel som en kort mening, för utfallet efter en åtgärd. */
const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Iris leads (steg 4.2, LR-030 till LR-059): leads före utskick som en lista i
 * CRM:ets form (BolagVy), statusremsan som vyer med antal, och leadet i en
 * panel från höger (`?lead=<id>`). Allt läses och skrivs genom leads-API:t,
 * samma ändpunkter som dagens Leads (lib/crm/iris/anrop.ts).
 *
 * Webbplatsbedömningen syns bara när svaret bär den (lib/crm/iris/webb.ts).
 */
export function LeadsVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const { isPlatformAdmin, vy: dashboardvy, impersonation, isDemo } = useDashboard();
  // Agenternas data: under ett kundbesök skrivs det som test (LR-094), läsrollen skriver inget (LR-093).
  const skriv = useSkrivratt("test");
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);
  // Flytta till main (LR-048, LR-097): plattformsadmin i den egna arbetsytan, aldrig under kundbesök eller i demon.
  const flyttbar = isPlatformAdmin && dashboardvy === "admin" && !impersonation && !isDemo;

  // ---- Adressen styr panelen (LR-008) ---------------------------------------
  const adressensPost = params?.get("lead") ?? null;
  const [postId, setPostId] = useState<string | null>(adressensPost);
  useEffect(() => {
    setPostId(adressensPost);
  }, [adressensPost]);
  const sattPost = useCallback((id: string | null) => {
    setPostId(id);
    const q = new URLSearchParams(window.location.search);
    if (id) q.set("lead", id);
    else q.delete("lead");
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);

  // ---- Hämtning --------------------------------------------------------------
  const [aktiva, setAktiva] = useState<Lead[] | null>(null);
  const [bortvalda, setBortvalda] = useState<Lead[] | null>(null);
  const [arkiverade, setArkiverade] = useState<Lead[] | null>(null);
  const [uppgifter, setUppgifter] = useState<Leaduppgift[]>([]);
  const [sparade, setSparade] = useState<Sparadvy[]>([]);
  const [fel, setFel] = useState<unknown>(null);
  const [undanFel, setUndanFel] = useState<unknown>(null);
  const [sidofel, setSidofel] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    try {
      const [l, u, v] = await Promise.allSettled([
        allaLeads<Lead>(),
        irisAnrop<{ uppgifter?: Leaduppgift[] }>("/leads/uppgifter?oppna=1"),
        irisAnrop<{ vyer?: Sparadvy[] }>("/leads/vyer")
      ]);
      if (l.status === "rejected") throw l.reason;
      setAktiva(l.value);
      setUppgifter(u.status === "fulfilled" ? (u.value.uppgifter ?? []) : []);
      setSparade(v.status === "fulfilled" ? (v.value.vyer ?? []) : []);
      const sido = [u, v].find((r) => r.status === "rejected") as PromiseRejectedResult | undefined;
      setSidofel(sido ? text(feltext(sido.reason)) : null);
    } catch (e) {
      setFel(e);
    }
  }, [text]);

  /** Bara leadsen, tyst: livetakten ska inte blinka fram fel eller skelett. */
  const hamtaTyst = useCallback(async () => {
    try {
      setAktiva(await allaLeads<Lead>());
    } catch {
      /* nästa varv försöker igen */
    }
  }, []);

  const hamtaUndan = useCallback(async (vilka: "bortvalda" | "arkiverade") => {
    setUndanFel(null);
    try {
      const rader = nyastForst(await allaLeads<Lead>(`${vilka}=1`));
      (vilka === "bortvalda" ? setBortvalda : setArkiverade)(rader);
    } catch (e) {
      setUndanFel(e);
      (vilka === "bortvalda" ? setBortvalda : setArkiverade)((nu) => nu ?? []);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // ---- Vy, filter och sök ----------------------------------------------------
  const [vy, setVy] = useState<Vy>("alla");
  const [niva, setNiva] = useState<"" | "A" | "B">("");
  const [typ, setTyp] = useState<"" | LeadTyp>("");
  const [webbband, setWebbband] = useState<"" | Betygsband>("");
  const [sortering, setSortering] = useState<Sortering>("nyast");
  const [sok, setSok] = useState("");
  const sokFordrojd = useDeferredValue(sok);
  const iUndan = vy === "bortvalda" || vy === "arkiverade";

  // Bortvalda och arkiverade hämtas först när vyn öppnas (LR-050, LR-051).
  useEffect(() => {
    if (vy === "bortvalda" && bortvalda === null) void hamtaUndan("bortvalda");
    if (vy === "arkiverade" && arkiverade === null) void hamtaUndan("arkiverade");
  }, [vy, bortvalda, arkiverade, hamtaUndan]);

  // Efter en åtgärd här, i panelen eller i dagens Leads: allt hämtas om, så att allt säger samma sak (LR-071).
  const harBortvalda = bortvalda !== null;
  const harArkiverade = arkiverade !== null;
  useEffect(() => {
    const uppdatera = () => {
      void hamta();
      if (harBortvalda) void hamtaUndan("bortvalda");
      if (harArkiverade) void hamtaUndan("arkiverade");
    };
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    window.addEventListener("snipra:leads-korning-steg", uppdatera);
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => {
      window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
      window.removeEventListener("snipra:leads-korning-steg", uppdatera);
      window.removeEventListener("snipra:leads-korning-klar", uppdatera);
    };
  }, [hamta, hamtaUndan, harBortvalda, harArkiverade]);

  // Live (LR-038): medan något researchas eller ett utkast skrivs, var fjärde sekund när fliken syns.
  const live = (aktiva ?? []).some((p) => iResearch(p) || p.utkast_status === "skrivs");
  const varLive = useRef(false);
  useEffect(() => {
    if (!live) {
      if (varLive.current) void hamta();
      varLive.current = false;
      return;
    }
    varLive.current = true;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void hamtaTyst();
    }, LIVE_MS);
    return () => window.clearInterval(id);
  }, [live, hamta, hamtaTyst]);

  // Bara leads före utskick, och inte de vars utkast är godkänt: de bor under Skickat (LR-031, LR-033).
  const foreUtskick = useMemo(
    () => sortera((aktiva ?? []).filter((p) => (FORE_UTSKICK as readonly string[]).includes(p.status) && p.utkast_status !== "godkant")),
    [aktiva]
  );
  const skarpa = useMemo(() => foreUtskick.filter((p) => p.origin !== "test"), [foreUtskick]);
  const provade = useMemo(() => foreUtskick.filter((p) => p.origin === "test"), [foreUtskick]);

  // Webbplatsens betyg: kolumnen, filtret och sorteringen finns bara när svaret bär det (LR-090).
  const visarWebb = useMemo(() => nagonHarBetyg(foreUtskick) || nagonHarBetyg(bortvalda ?? []) || nagonHarBetyg(arkiverade ?? []), [foreUtskick, bortvalda, arkiverade]);
  useEffect(() => {
    if (visarWebb) return;
    setWebbband("");
    setSortering((s) => (s === "webb" ? "nyast" : s));
  }, [visarWebb]);

  const filtrerar = Boolean(niva || typ || webbband || sokFordrojd.trim());
  const matchar = useCallback(
    (p: Lead) => {
      if (niva && p.niva !== niva) return false;
      if (typ && leadTyp(p.origin) !== typ) return false;
      if (webbband) {
        const m = betyg(p);
        if (m == null || band(m) !== webbband) return false;
      }
      return matcharSok(p, sokFordrojd);
    },
    [niva, typ, webbband, sokFordrojd]
  );

  const ordna = useCallback(
    (rader: Lead[]) => {
      if (sortering === "poang") return [...rader].sort((a, b) => (poang(b) ?? -1) - (poang(a) ?? -1));
      if (sortering === "webb") return [...rader].sort((a, b) => (betyg(a) ?? 99) - (betyg(b) ?? 99));
      return rader;
    },
    [sortering]
  );

  const iFiltret = useMemo(() => skarpa.filter(matchar), [skarpa, matchar]);
  const antal = useMemo(() => {
    const per = (s: string) => iFiltret.filter((p) => p.status === s).length;
    return {
      alla: iFiltret.length,
      researching: per("researching"),
      new: per("new"),
      ready: per("ready"),
      testyta: provade.filter(matchar).length,
      bortvalda: bortvalda ? bortvalda.filter(matchar).length : null,
      arkiverade: arkiverade ? arkiverade.filter(matchar).length : null
    };
  }, [iFiltret, provade, bortvalda, arkiverade, matchar]);

  const urvalSorterat = useMemo(() => {
    if (vy === "bortvalda") return ordna((bortvalda ?? []).filter(matchar));
    if (vy === "arkiverade") return ordna((arkiverade ?? []).filter(matchar));
    if (vy === "testyta") return ordna(provade.filter(matchar));
    if (vy === "alla") return ordna(iFiltret);
    return ordna(iFiltret.filter((p) => p.status === vy));
  }, [vy, bortvalda, arkiverade, provade, iFiltret, matchar, ordna]);

  // ---- Markering (LR-041) ----------------------------------------------------
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [valjer, setValjer] = useState(false);
  // Medan något är markerat står ordningen still, så att raden man siktar på inte flyttar (LR-032).
  const frys = useRef<Map<string, number> | null>(null);
  const markerar = valda.size > 0;
  if (!markerar) frys.current = null;
  else if (!frys.current) frys.current = new Map(urvalSorterat.map((p, i) => [p.id, i]));
  const urval = useMemo(() => {
    const karta = frys.current;
    if (!markerar || !karta) return urvalSorterat;
    return [...urvalSorterat].sort((a, b) => (karta.get(a.id) ?? -1) - (karta.get(b.id) ?? -1));
  }, [urvalSorterat, markerar]);
  const ordningFryst = markerar && urval.some((p, i) => urvalSorterat[i]?.id !== p.id);

  // En ny vy eller ett nytt filter är ett nytt urval: markeringen gäller inte längre.
  useEffect(() => {
    setValda(new Set());
  }, [vy, niva, typ, webbband, sokFordrojd]);

  // Exempelbolag är demons och går inte att markera (LR-041).
  const markerbara = useMemo(() => urval.filter((p) => p.origin !== "example"), [urval]);
  const { selectionConfig, selectionState } = useTableSelectionState<Lead>({ data: markerbara, idKey: "id", selectedKeys: valda, setSelectedKeys: setValda });
  const markering = useTableSelection<Lead>({ ...selectionConfig, getRowLabel: (p) => p.company_name });

  // ---- Sidindelning (LR-037, LR-058) ------------------------------------------
  const sidor = useSida(urval.length, `${vy}|${niva}|${typ}|${webbband}|${sokFordrojd}|${sortering}`);
  const sidansRader = useMemo(() => urval.slice(sidor.fran, sidor.till), [urval, sidor.fran, sidor.till]);
  const urvalIds = useMemo(() => urval.map((p) => p.id), [urval]);
  useSidaFor(postId, urvalIds, sidor.setSida);
  const listref = useRef<HTMLDivElement>(null);
  const bytSida = (n: number) => {
    sidor.setSida(n - 1);
    const el = listref.current;
    if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ block: "start" });
  };

  const nastaUppgift = useMemo(() => {
    const karta = new Map<string, Leaduppgift>();
    for (const u of uppgifter) if (!u.klar && !karta.has(u.prospect_id)) karta.set(u.prospect_id, u);
    return karta;
  }, [uppgifter]);

  // ---- Status i raden (LR-039) -------------------------------------------------
  const [statusbesked, setStatusbesked] = useState("");
  const bytStatus = useCallback(
    async (p: Lead, status: string, angra = false) => {
      const forra = p.status;
      if (forra === status) return;
      setAktiva((rader) => rader?.map((r) => (r.id === p.id ? { ...r, status } : r)) ?? null);
      const ny = text(STATUS_ETIKETT[status] ?? { sv: status, en: status });
      const nyLiten = ny.toLocaleLowerCase(sprak);
      setStatusbesked(text({ sv: `${p.company_name}: status ändrad till ${ny}`, en: `${p.company_name}: status changed to ${ny}` }));
      try {
        await irisAnrop(`/leads/prospects/${encodeURIComponent(p.id)}`, { method: "PATCH", body: JSON.stringify({ status }) });
        setAktiva((rader) => rader?.map((r) => (r.id === p.id ? { ...r, senaste_handelse_at: new Date().toISOString() } : r)) ?? null);
        if (!angra) {
          visa({
            body: text({ sv: `${p.company_name} står nu som ${nyLiten}.`, en: `${p.company_name} is now ${nyLiten}.` }),
            endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void bytStatus({ ...p, status }, forra, true)} />,
            autoHideDuration: 10000,
            uniqueID: "iris-status"
          });
        }
      } catch (e) {
        setAktiva((rader) => rader?.map((r) => (r.id === p.id ? { ...r, status: forra } : r)) ?? null);
        const orsak = text(feltext(e));
        visa({ type: "error", body: text({ sv: `Statusen sparades inte: ${orsak}`, en: `The status was not saved: ${orsak}` }), uniqueID: "iris-status" });
      }
    },
    [text, sprak, visa]
  );

  // ---- Massåtgärderna (LR-042 till LR-048, LR-102 till LR-106) ----------------
  const [atgard, setAtgard] = useState<Atgard | null>(null);
  const [framsteg, setFramsteg] = useState<{ klara: number; totalt: number } | null>(null);
  const [besked, setBesked] = useState<{ text: string; fel: boolean; orsaker?: string[] } | null>(null);
  const [bekraftas, setBekraftas] = useState<Bekraftas | null>(null);
  const [flyttaProv, setFlyttaProv] = useState(false);
  const [struktur, setStruktur] = useState<"a" | "b">("a");
  useEffect(() => {
    void import("@/lib/leads/struktur").then((m) => setStruktur(m.lasStruktur()));
  }, []);

  const valt = useMemo(() => urval.filter((p) => valda.has(p.id)), [urval, valda]);

  /** En massåtgärd i taget (LR-047). `gor` returnerar beskedet. */
  async function utfor(namn: Atgard, gor: () => Promise<{ text: string; fel: boolean; orsaker?: string[]; angra?: () => void } | null>) {
    if (atgard) return;
    setAtgard(namn);
    setBesked(null);
    try {
      const ut = await gor();
      if (ut) {
        if (ut.orsaker?.length) setBesked(ut);
        else
          visa({
            type: ut.fel ? "error" : "info",
            body: ut.text,
            endContent: ut.angra ? <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={ut.angra} /> : undefined,
            autoHideDuration: ut.angra ? 10000 : undefined,
            uniqueID: "iris-atgard"
          });
        setStatusbesked(ut.text);
      }
    } catch (e) {
      visa({ type: "error", body: text(feltext(e)), uniqueID: "iris-atgard" });
      setStatusbesked(text(feltext(e)));
    } finally {
      setAtgard(null);
      setFramsteg(null);
      setBekraftas(null);
    }
  }

  const klart = () => {
    setValda(new Set());
    meddelaLeadsUppdaterade("crm-iris");
  };

  /** Skapa utkast (bara de utan) och Skapa om utkast (alla, ersätter). Ur sparad research, scope `utkast` (LR-042, LR-096). */
  async function skapaUtkast(rader: Lead[], ersatt: boolean) {
    const urvalet = ersatt ? rader : rader.filter((p) => UTAN_UTKAST.has(p.utkast_status ?? "saknas"));
    if (!urvalet.length) return;
    await utfor(ersatt ? "skapa-om" : "skapa", async () => {
      let koade = 0;
      const hoppade: string[] = [];
      const pagar: string[] = [];
      for (let i = 0; i < urvalet.length; i += PROCESSA_OMGANG) {
        const svar = await irisAnrop<{ count?: number; hoppade_over?: string[]; pagar_redan?: string[] }>("/leads/prospects/processa-om", {
          method: "POST",
          body: JSON.stringify({ prospect_ids: urvalet.slice(i, i + PROCESSA_OMGANG).map((p) => p.id), scope: "utkast", ersatt })
        });
        koade += svar.count ?? 0;
        hoppade.push(...(svar.hoppade_over ?? []));
        pagar.push(...(svar.pagar_redan ?? []));
      }
      klart();
      const delar = [
        text({ sv: `Utkast skrivs för ${koade} leads ur den research som redan finns. De står som Skriver utkast tills de är klara.`, en: `Drafts are being written for ${koade} leads from their existing research. They show as Writing draft until they are done.` }),
        hoppade.length ? text({ sv: `${hoppade.length} har redan fått mejl utan någon uppföljning som väntar och hoppades över.`, en: `${hoppade.length} already emailed with no follow-up pending were skipped.` }) : null,
        pagar.length ? text({ sv: `${pagar.length} bearbetas redan och hoppades över.`, en: `${pagar.length} already being processed were skipped.` }) : null
      ];
      return { text: delar.filter(Boolean).join(" "), fel: false };
    });
  }

  /** Bearbeta om (LR-106): ny research och nytt utkast i vald struktur. */
  async function bearbetaOm(rader: Lead[]) {
    await utfor("bearbeta", async () => {
      const svar = await irisAnrop<{ count?: number; pagar_redan?: string[] }>("/leads/prospects/processa-om", {
        method: "POST",
        body: JSON.stringify({ prospect_ids: rader.map((p) => p.id), scope: "research_and_draft", struktur })
      });
      klart();
      return {
        text:
          text({ sv: `Iris researchar ${svar.count ?? 0} bolag igen och skriver nya utkast.`, en: `Iris is researching ${svar.count ?? 0} companies again and writing new drafts.` }) +
          (svar.pagar_redan?.length ? ` ${text({ sv: `${svar.pagar_redan.length} bearbetas redan och hoppades över.`, en: `${svar.pagar_redan.length} already being processed were skipped.` })}` : ""),
        fel: false
      };
    });
  }

  /** Skicka utkast (LR-043): befordrar provkörningens bolag om det kryssats, och godkänner varje väntande utkast i tur och ordning. */
  async function skicka(rader: Lead[]) {
    await utfor("skicka", async () => {
      const skickbara = rader.filter(kanSkickas);
      const prov = skickbara.filter((p) => p.origin === "test");
      const flyttade: Lead[] = [];
      const ejFlyttade: string[] = [];
      let orgnrHamtade = 0;
      if (flyttaProv) {
        for (const p of prov) {
          try {
            const svar = await irisAnrop<{ orgnr_hamtat?: boolean }>(`/leads/prospects/${encodeURIComponent(p.id)}/befordra`, { method: "POST" });
            if (svar.orgnr_hamtat) orgnrHamtade += 1;
            flyttade.push(p);
          } catch (e) {
            ejFlyttade.push(`${p.company_name}: ${text(feltext(e))}`);
          }
        }
      }
      const poster = skickbara.filter((p) => p.origin !== "test" || flyttade.includes(p));
      const kvarProv = prov.length - flyttade.length - ejFlyttade.length;
      const godkanda = rader.filter((p) => p.utkast_status === "godkant").length;
      const utan = rader.length - skickbara.length - godkanda;
      let skickade = 0;
      let vantar = 0;
      const stopp = new Map<string, string[]>();
      for (const [i, p] of poster.entries()) {
        setFramsteg({ klara: i, totalt: poster.length });
        try {
          const svar = await irisAnrop<{ utfall?: string; besked?: string; skal?: string | null }>(`/leads/queue/${encodeURIComponent(p.queue_item_id ?? "")}/approve`, { method: "POST" });
          if (svar.utfall === "sent") skickade += 1;
          else if (svar.utfall === "requeued") vantar += 1;
          else {
            const skal = svar.skal || svar.besked || svar.utfall || "";
            stopp.set(skal, [...(stopp.get(skal) ?? []), p.company_name]);
          }
        } catch (e) {
          const skal = text(feltext(e));
          stopp.set(skal, [...(stopp.get(skal) ?? []), p.company_name]);
        }
      }
      setFramsteg({ klara: poster.length, totalt: poster.length });
      klart();
      const namn = (bolag: string[]) =>
        bolag.length <= 3 ? bolag.join(", ") : text({ sv: `${bolag.slice(0, 3).join(", ")} och ${bolag.length - 3} till`, en: `${bolag.slice(0, 3).join(", ")} and ${bolag.length - 3} more` });
      const fyll = text({
        sv: "Fyll i avsändarens org.nr, postadress och integritetspolicy i kundregistret och skicka igen.",
        en: "Fill in the sender's company number, postal address and privacy policy in the customer register and send again."
      });
      const orsaker = [
        ...[...stopp.entries()].map(([skal, bolag]) => `${bolag.length} · ${skal}${/organisationsnummer|postadress|integritetspolicy|policy/i.test(skal) ? ` ${fyll}` : ""} (${namn(bolag)})`),
        ...ejFlyttade.map((r) => `1 · ${text({ sv: "Kunde inte flyttas över från provkörningen", en: "Could not be moved over from the test run" })}. ${r}`),
        ...(kvarProv ? [text({ sv: `${kvarProv} · Kommer från en provkörning och skickades inte. Kryssa i Flytta över i bekräftelsen för att skicka dem.`, en: `${kvarProv} · From a test run and not sent. Tick Move over in the confirmation to send them.` })] : [])
      ];
      const antalStopp = [...stopp.values()].reduce((n, b) => n + b.length, 0) + ejFlyttade.length + kvarProv;
      const iKon = vantar + godkanda;
      const delar: (Localized | null)[] = [
        { sv: `${skickade} skickade`, en: `${skickade} sent` },
        iKon ? { sv: `${iKon} skickas i tur och ordning från kön (vardagar från 08:00)`, en: `${iKon} go out in turn from the queue (weekdays from 08:00)` } : null,
        flyttade.length ? { sv: `${flyttade.length} flyttades över från provkörningen`, en: `${flyttade.length} moved over from the test run` } : null,
        orgnrHamtade ? { sv: `org.nr hämtades från ${orgnrHamtade} webbplatser`, en: `company number found on ${orgnrHamtade} websites` } : null,
        antalStopp ? { sv: `${antalStopp} skickades inte`, en: `${antalStopp} were not sent` } : null,
        utan ? { sv: `${utan} saknade utkast`, en: `${utan} had no draft` } : null
      ];
      return { text: `${delar.filter((d): d is Localized => d != null).map((d) => text(d)).join(", ")}.`, fel: antalStopp > 0, orsaker };
    });
  }

  /** Arkivera eller återställ (LR-045, LR-054). Ångra går åt andra hållet. */
  async function arkivera(rader: Lead[], pa: boolean, fran?: Element | null) {
    const fokus = grannfokus(fran, "input[type=checkbox]");
    await utfor(pa ? "arkivera" : "aterstall", async () => {
      const svar = await irisAnrop<{ ids?: string[]; installda_utskick?: number }>("/leads/prospects/arkivera", { method: "POST", body: JSON.stringify({ ids: rader.map((p) => p.id), arkivera: pa }) });
      klart();
      fokus();
      const ids = svar.ids ?? [];
      const stoppade = svar.installda_utskick ?? 0;
      return {
        text: pa
          ? text({ sv: `${ids.length} arkiverade.`, en: `${ids.length} archived.` }) + (stoppade ? ` ${text({ sv: `${stoppade} väntande utkast ställdes in och skickas inte.`, en: `${stoppade} pending drafts were cancelled and will not be sent.` })}` : "")
          : text({ sv: `${ids.length} återställda till listan.`, en: `${ids.length} restored to the list.` }),
        fel: false,
        angra: ids.length
          ? () => {
              void irisAnrop("/leads/prospects/arkivera", { method: "POST", body: JSON.stringify({ ids, arkivera: !pa }) }).then(
                () => meddelaLeadsUppdaterade("crm-iris"),
                (e) => visa({ type: "error", body: text(feltext(e)), uniqueID: "iris-atgard" })
              );
            }
          : undefined
      };
    });
  }

  /** Ta bort för gott (LR-046, LR-055): bara leads som aldrig fått mejl. */
  async function taBort(rader: Lead[]) {
    await utfor("ta-bort", async () => {
      const svar = await irisAnrop<{ raderade?: string[]; vagrade?: { id: string; skal: string }[] }>("/leads/prospects/radera", { method: "POST", body: JSON.stringify({ ids: rader.map((p) => p.id) }) });
      if (postId && svar.raderade?.includes(postId)) sattPost(null);
      klart();
      const kontaktade = (svar.vagrade ?? []).filter((v) => v.skal === "kontaktad").length;
      return {
        text:
          text({ sv: `${svar.raderade?.length ?? 0} borttagna.`, en: `${svar.raderade?.length ?? 0} deleted.` }) +
          (kontaktade ? ` ${text({ sv: `${kontaktade} har fått mejl och kan bara arkiveras.`, en: `${kontaktade} have been emailed and can only be archived.` })}` : ""),
        fel: kontaktade > 0
      };
    });
  }

  /** Skapa uppföljning (LR-044) för markerade som fått mejl. */
  async function uppfoljning(rader: Lead[]) {
    await utfor("uppfoljning", async () => {
      const svar = await irisAnrop<{ count: number; hoppade?: Record<string, string[]> }>("/leads/uppfoljningar/skapa", { method: "POST", body: JSON.stringify({ prospect_ids: rader.filter(harFattMejl).map((p) => p.id) }) });
      klart();
      const hoppade = Object.entries(svar.hoppade ?? {})
        .filter(([, ids]) => ids.length)
        .map(([skal, ids]) => `${ids.length} ${text(UPPFOLJNING_HOPPAD[skal] ?? { sv: skal, en: skal })}`)
        .join(", ");
      return {
        text:
          (svar.count === 1
            ? text({ sv: "Iris skriver 1 uppföljning. Den väntar på ditt ja när den är klar.", en: "Iris is writing 1 follow-up. It waits for your yes when done." })
            : text({ sv: `Iris skriver ${svar.count} uppföljningar. De väntar på ditt ja när de är klara.`, en: `Iris is writing ${svar.count} follow-ups. They wait for your yes when done.` })) +
          (hoppade ? ` ${text({ sv: "Hoppade över:", en: "Skipped:" })} ${hoppade}.` : ""),
        fel: false
      };
    });
  }

  /** Flytta till testytan (LR-102) eller till skarpa listan (LR-103, LR-104). */
  const [ifyllnad, setIfyllnad] = useState<{ lead: Lead; saknas: string[]; orgnr: string; website: string; contact_email: string; fel: string | null; sparar: boolean }[] | null>(null);
  async function flytta(rader: Lead[], till: "test" | "skarp") {
    await utfor(till === "test" ? "testyta" : "skarp", async () => {
      let andrade = 0;
      const fall: { lead: Lead; fel: unknown }[] = [];
      for (const [i, p] of rader.entries()) {
        setFramsteg({ klara: i, totalt: rader.length });
        try {
          const svar = await irisAnrop<{ andrad?: boolean }>(`/leads/prospects/${encodeURIComponent(p.id)}/${till === "test" ? "degradera" : "befordra"}`, { method: "POST" });
          if (svar.andrad) andrade += 1;
        } catch (e) {
          fall.push({ lead: p, fel: e });
        }
      }
      klart();
      const saknade = fall.filter((f) => f.fel instanceof CrmFel && f.fel.status === 422);
      if (saknade.length) {
        setIfyllnad(
          saknade.map((f) => ({
            lead: f.lead,
            saknas: (f.fel as { saknas?: string[] }).saknas ?? [],
            orgnr: "",
            website: f.lead.website ?? "",
            contact_email: f.lead.contact_email ?? "",
            fel: text(feltext(f.fel)),
            sparar: false
          }))
        );
      }
      return {
        text:
          till === "test"
            ? text({ sv: `${andrade} flyttades till testytan och kan inte längre skickas.`, en: `${andrade} moved to the test area and can no longer be sent.` })
            : text({ sv: `${andrade} flyttades till skarpa listan.`, en: `${andrade} moved to the live list.` }) +
              (fall.length ? ` ${text({ sv: `${fall.length} kunde inte flyttas.`, en: `${fall.length} could not be moved.` })}` : ""),
        fel: fall.length > 0
      };
    });
  }

  async function befordraMedIfyllnad(i: number) {
    const rad = ifyllnad?.[i];
    if (!rad) return;
    setIfyllnad((l) => l?.map((r, k) => (k === i ? { ...r, sparar: true, fel: null } : r)) ?? null);
    const kropp = Object.fromEntries(Object.entries({ orgnr: rad.orgnr.trim(), website: rad.website.trim(), contact_email: rad.contact_email.trim() }).filter(([, v]) => v));
    try {
      await irisAnrop(`/leads/prospects/${encodeURIComponent(rad.lead.id)}/befordra`, { method: "POST", body: JSON.stringify(kropp) });
      setIfyllnad((l) => {
        const kvar = l?.filter((_, k) => k !== i) ?? [];
        return kvar.length ? kvar : null;
      });
      visa({ body: text({ sv: `${rad.lead.company_name} flyttades till skarpa listan.`, en: `${rad.lead.company_name} moved to the live list.` }), uniqueID: "iris-atgard" });
      meddelaLeadsUppdaterade("crm-iris");
    } catch (e) {
      setIfyllnad((l) => l?.map((r, k) => (k === i ? { ...r, sparar: false, fel: text(feltext(e)), saknas: (e as { saknas?: string[] }).saknas ?? r.saknas } : r)) ?? null);
    }
  }

  async function tillMain(rader: Lead[]) {
    await utfor("main", async () => {
      const { flyttaProspektTillMain } = await import("@/lib/actions/flytt");
      const svar = await flyttaProspektTillMain(rader.map((p) => p.id));
      if (svar.error) {
        const kand: Record<string, Localized> = {
          miljo: { sv: "Flytt till main går bara från development.", en: "Moving to main only works from development." },
          arbetsyta: { sv: "Arbetsytan gick inte att läsa.", en: "The workspace could not be read." },
          antal: { sv: "Markera 1 till 50 leads.", en: "Select 1 to 50 leads." }
        };
        return { text: svar.felkod ? text(kand[svar.felkod]) : svar.error, fel: true };
      }
      const ok = (svar.rader ?? []).filter((r) => r.resultat === "importerad").length;
      const redan = (svar.rader ?? []).filter((r) => r.resultat === "redan_flyttad").length;
      const foll = (svar.rader ?? []).filter((r) => r.resultat === "fel").length;
      if (foll === 0) setValda(new Set());
      return {
        text: text({ sv: `Flytt till main: ${ok} flyttade, ${redan} fanns redan, ${foll} föll.`, en: `Move to main: ${ok} moved, ${redan} already there, ${foll} failed.` }),
        fel: foll > 0
      };
    });
  }

  // ---- Sparade vyer (LR-035) ---------------------------------------------------
  const [sparaVy, setSparaVy] = useState<{ namn: string; sparar: boolean; fel: string | null } | null>(null);
  const aktivtFilter: Vyfilter = useMemo(() => {
    const f: Vyfilter = {};
    if (vy === "researching" || vy === "new" || vy === "ready") f.status = vy;
    if (niva) f.niva = niva;
    if (typ) f.typ = typ;
    if (sok.trim()) f.sok = sok.trim();
    return f;
  }, [vy, niva, typ, sok]);
  const nyckel = (f: Vyfilter) => JSON.stringify(Object.entries(f).filter(([, v]) => v).sort());
  const aktivVy = sparade.find((s) => nyckel(s.filter) === nyckel(aktivtFilter) && Object.keys(aktivtFilter).length > 0);
  const anvandVy = (s: Sparadvy | null) => {
    const f = s?.filter ?? {};
    setVy(f.status === "researching" || f.status === "new" || f.status === "ready" ? f.status : "alla");
    setNiva(f.niva === "A" || f.niva === "B" ? f.niva : "");
    setTyp((TYPER as string[]).includes(f.typ ?? "") ? ((f.typ ?? "") as "" | LeadTyp) : "");
    setSok(f.sok ?? "");
  };
  async function sparaDenna() {
    if (!sparaVy) return;
    const namn = sparaVy.namn.trim();
    if (!namn) {
      setSparaVy({ ...sparaVy, fel: text({ sv: "Ge vyn ett namn.", en: "Give the view a name." }) });
      return;
    }
    setSparaVy({ ...sparaVy, sparar: true, fel: null });
    try {
      const svar = await irisAnrop<{ vy: Sparadvy }>("/leads/vyer", { method: "POST", body: JSON.stringify({ namn, filter: aktivtFilter }) });
      setSparade((v) => [...v, svar.vy]);
      setSparaVy(null);
      visa({ body: text({ sv: `Vyn ${namn} är sparad.`, en: `The view ${namn} is saved.` }), uniqueID: "iris-vy" });
    } catch (e) {
      setSparaVy({ ...sparaVy, sparar: false, fel: text(feltext(e)) });
    }
  }
  async function raderaVy(s: Sparadvy) {
    const forr = sparade;
    setSparade((v) => v.filter((x) => x.id !== s.id));
    try {
      await irisAnrop(`/leads/vyer/${encodeURIComponent(s.id)}`, { method: "DELETE" });
      visa({ body: text({ sv: `Vyn ${s.namn} är borttagen.`, en: `The view ${s.namn} is deleted.` }), uniqueID: "iris-vy" });
    } catch (e) {
      setSparade(forr);
      visa({ type: "error", body: text(feltext(e)), uniqueID: "iris-vy" });
    }
  }

  // ---- Kolumnerna (LR-036, LR-040, LR-090) -------------------------------------
  const visarUppgift = sidansRader.some((p) => nastaUppgift.has(p.id));
  const visarWebbkolumn = visarWebb && urval.some((p) => betyg(p) != null);
  const statusval = useCallback(
    (p: Lead) => {
      const etikett = text(STATUS_ETIKETT[p.status] ?? { sv: p.status, en: p.status });
      const ton = STATUSTON[p.status] ?? null;
      const last = p.origin === "example" || iUndan;
      if (last || !skriv.far) {
        return (
          <span className="inline-flex items-center gap-1.5 text-[0.875rem] text-ink2" title={!skriv.far ? (skriv.skal ?? undefined) : undefined}>
            <Prick ton={ton} />
            {etikett}
          </span>
        );
      }
      const val: DropdownMenuOption[] = [
        ...(SYSTEMSTATUS.has(p.status) ? [{ label: etikett, icon: <Prick ton={null} />, isDisabled: true, description: text({ sv: "Sätts av systemet", en: "Set by the system" }) }] : []),
        ...VALBARA.map((s) => ({ label: text(STATUS_ETIKETT[s]), icon: <Prick ton={STATUSTON[s] ?? null} />, onClick: () => void bytStatus(p, s) }))
      ];
      return (
        <DropdownMenu
          button={{ label: etikett, variant: "ghost", size: "sm", icon: <Prick ton={ton} />, "aria-label": text({ sv: `Status för ${p.company_name}: ${etikett}`, en: `Status for ${p.company_name}: ${etikett}` }) }}
          items={val}
        />
      );
    },
    [text, iUndan, skriv.far, skriv.skal, bytStatus]
  );

  const kolumner = useMemo<TableColumn<Lead>[]>(() => {
    const k: TableColumn<Lead>[] = [
      {
        key: "company_name",
        header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Kolumnrubrik>,
        width: proportional(1.2, { minWidth: 180 }),
        renderCell: (p) => (
          <span className="flex min-w-0 items-center gap-2">
            <Postchip namn={p.company_name || text({ sv: "Namnlöst bolag", en: "Unnamed company" })} onClick={() => sattPost(p.id)} label={text({ sv: `Öppna ${p.company_name}`, en: `Open ${p.company_name}` })} />
            {p.origin === "example" ? <Badge variant="neutral" label={text({ sv: "Exempel", en: "Example" })} /> : null}
          </span>
        )
      },
      {
        key: "status",
        header: <Kolumnrubrik ikon={Tag}>{text({ sv: "Status", en: "Status" })}</Kolumnrubrik>,
        width: pixel(168),
        renderCell: (p) => statusval(p)
      },
      {
        key: "poang",
        header: <Kolumnrubrik ikon={Gauge}>{text({ sv: "Poäng", en: "Score" })}</Kolumnrubrik>,
        width: pixel(100),
        renderCell: (p) => {
          const n = poang(p);
          if (obedomd(p) || n == null) return <span className="text-ink-muted" title={text({ sv: "Ingen poäng än", en: "No score yet" })}>-</span>;
          return (
            <span className="inline-flex items-baseline gap-1.5 tabular-nums">
              <span className="font-semibold text-ink">{n}</span>
              {p.niva ? <span className={`text-[0.8125rem] ${p.niva === "C" ? "text-danger" : "text-ink-muted"}`}>{nivaEtikett(p.niva, locale)}</span> : null}
            </span>
          );
        }
      },
      {
        key: "signal",
        header: <Kolumnrubrik ikon={Sparkles}>{text({ sv: "Signal", en: "Signal" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 130 }),
        renderCell: (p) => {
          const pafyllt = p.pafylld ? pafyllnadSkal(p.pafylld_skal) : null;
          const skal = p.pafylld ? (pafyllt ? text(pafyllt) : "") : null;
          const rad = skal != null ? (skal ? text({ sv: `Påfyllt: ${skal}`, en: `Filled in: ${skal}` }) : text({ sv: "Påfyllt", en: "Filled in" })) : forstaMening(p);
          return rad ? (
            <span className="block truncate text-[0.875rem] text-ink2" title={rad}>
              {rad}
            </span>
          ) : null;
        }
      }
    ];
    if (visarWebbkolumn) {
      k.push({
        key: "webb",
        header: <Kolumnrubrik ikon={Globe}>{text({ sv: "Webbplats", en: "Website" })}</Kolumnrubrik>,
        width: pixel(96),
        renderCell: (p) => {
          const m = betyg(p);
          if (m == null) return null;
          const b = band(m);
          return (
            <span className="inline-flex min-w-0 items-center gap-1.5" title={forstaBrist(p) ?? undefined}>
              <Badge variant={b === "lag" ? "green" : b === "mellan" ? "yellow" : "neutral"} label={<span className="tabular-nums">{`${m}/10`}</span>} />
              <span className="sr-only">{text({ sv: "Modernitet", en: "Modernity" })}</span>
            </span>
          );
        }
      });
    }
    k.push(
      {
        key: "utkast",
        header: <Kolumnrubrik ikon={FilePen}>{text({ sv: "Utkast", en: "Draft" })}</Kolumnrubrik>,
        width: pixel(150),
        renderCell: (p) => {
          const etikett = utkastText(p, locale, text);
          if (!etikett || !p.utkast_status) return <span className="text-ink-muted">-</span>;
          const ton = UTKASTTON[p.utkast_status];
          const klass = ton === "varning" ? "text-warning" : ton === "mossa" ? "text-moss" : ton === "fara" ? "text-danger" : "text-ink-muted";
          const skal = (p.utkast_status === "stoppat" || p.utkast_status === "saknas" || p.utkast_status === "avvisat") && p.utkast_skal ? p.utkast_skal : null;
          return (
            <span className={`block truncate text-[0.875rem] ${klass}`} title={skal ?? undefined}>
              {etikett}
            </span>
          );
        }
      },
      {
        key: "kontakt",
        header: <Kolumnrubrik ikon={PhoneCall}>{text({ sv: "Kontakt", en: "Contact" })}</Kolumnrubrik>,
        width: pixel(112),
        renderCell: (p) => {
          const v = kontaktvag(p);
          return <Badge variant={v === "saknas" ? "yellow" : v === "bada" ? "green" : "neutral"} label={text(KONTAKTVAG[v])} />;
        }
      },
      {
        key: "kalla",
        header: <Kolumnrubrik ikon={Plug}>{text({ sv: "Källa", en: "Source" })}</Kolumnrubrik>,
        width: pixel(84),
        renderCell: (p) => <Kallpiller kalla={text(LEAD_TYP_ETIKETT[leadTyp(p.origin)])} />
      },
      {
        key: "senast",
        header: <Kolumnrubrik ikon={Clock}>{iUndan && vy === "arkiverade" ? text({ sv: "Arkiverad", en: "Archived" }) : text({ sv: "Ändrad", en: "Updated" })}</Kolumnrubrik>,
        width: pixel(84),
        renderCell: (p) => {
          const t = (vy === "arkiverade" ? p.arkiverad_at : null) ?? p.senaste_handelse_at ?? p.created_at;
          return t ? (
            <span className="tabular-nums text-ink2" title={new Date(t).toLocaleString(sprak, { dateStyle: "medium", timeStyle: "short" })}>
              {kortTid(t, locale)}
            </span>
          ) : null;
        }
      }
    );
    if (visarUppgift) {
      k.push({
        key: "uppgift",
        header: <Kolumnrubrik ikon={ListTodo}>{text({ sv: "Nästa uppgift", en: "Next task" })}</Kolumnrubrik>,
        width: pixel(140),
        renderCell: (p) => {
          const u = nastaUppgift.get(p.id);
          return u ? (
            <span className="block truncate text-[0.875rem] text-ink2" title={u.forfaller ? `${u.titel} (${u.forfaller})` : u.titel}>
              {u.titel}
            </span>
          ) : null;
        }
      });
    }
    return k;
  }, [text, locale, sattPost, statusval, visarWebbkolumn, visarUppgift, nastaUppgift, iUndan, vy]);

  // ---- Vyerna i vyraden ----------------------------------------------------------
  const vynamn: Record<Vy, Localized> = {
    alla: { sv: "Att bearbeta", en: "To work on" },
    researching: STATUS_ETIKETT.researching,
    new: STATUS_ETIKETT.new,
    ready: STATUS_ETIKETT.ready,
    testyta: { sv: "Testyta", en: "Test area" },
    bortvalda: { sv: "Bortvalda", en: "Ruled out" },
    arkiverade: { sv: "Arkiverade", en: "Archived" }
  };
  // Research pågår syns när något researchas eller den är vald (LR-033). Testytan när den har något.
  const vyer: Vy[] = [
    "alla",
    ...(antal.researching > 0 || vy === "researching" ? (["researching"] as Vy[]) : []),
    "new",
    "ready",
    ...(provade.length > 0 || vy === "testyta" ? (["testyta"] as Vy[]) : []),
    "bortvalda",
    "arkiverade"
  ];
  const vyantal = (v: Vy) => {
    const n = antal[v];
    return n == null ? undefined : tal(n);
  };

  const filterval: DropdownMenuOption[] = [
    {
      type: "section",
      title: text({ sv: "Nivå", en: "Level" }),
      items: NIVAER.map((n) => ({ label: text(n.namn), icon: <Prick ton={niva === n.v ? "ockra" : null} />, onClick: () => setNiva(n.v) }))
    },
    {
      type: "section",
      title: text({ sv: "Typ", en: "Type" }),
      items: TYPER.map((t) => ({ label: t ? text(LEAD_TYP_ETIKETT[t]) : text({ sv: "Alla typer", en: "All types" }), icon: <Prick ton={typ === t ? "ockra" : null} />, onClick: () => setTyp(t) }))
    },
    ...(visarWebb
      ? [
          {
            type: "section" as const,
            title: text({ sv: "Webbplats", en: "Website" }),
            items: BETYGSBAND.map((b) => ({ label: text(b.namn), icon: <Prick ton={webbband === b.v ? "ockra" : null} />, onClick: () => setWebbband(b.v) }))
          }
        ]
      : [])
  ];
  const antalFilter = [niva, typ, webbband].filter(Boolean).length;

  const vyval: DropdownMenuOption[] = [
    ...(sparade.length
      ? [
          {
            type: "section" as const,
            title: text({ sv: "Använd", en: "Use" }),
            items: sparade.map((s) => ({ label: s.namn, icon: <Prick ton={aktivVy?.id === s.id ? "ockra" : null} />, onClick: () => anvandVy(aktivVy?.id === s.id ? null : s) }))
          },
          { type: "divider" as const }
        ]
      : []),
    {
      label: text({ sv: "Spara filtret som vy", en: "Save the filter as a view" }),
      icon: <Icon icon={Bookmark} size="sm" />,
      isDisabled: Object.keys(aktivtFilter).length === 0 || !skriv.far,
      description: !skriv.far ? (skriv.skal ?? undefined) : Object.keys(aktivtFilter).length === 0 ? text({ sv: "Välj ett filter, en status eller sök först", en: "Choose a filter, a status or a search first" }) : undefined,
      onClick: () => setSparaVy({ namn: "", sparar: false, fel: null })
    },
    ...(sparade.length && skriv.far
      ? [
          {
            label: text({ sv: "Ta bort en vy", en: "Delete a view" }),
            icon: <Icon icon={Trash2} size="sm" />,
            items: sparade.map((s) => ({ label: s.namn, onClick: () => void raderaVy(s) }))
          }
        ]
      : [])
  ];

  // ---- Delarna -------------------------------------------------------------------
  const rensa = () => {
    setNiva("");
    setTyp("");
    setWebbband("");
    setSok("");
  };
  const vynamnLiten = text(vynamn[vy]).toLocaleLowerCase(sprak);
  const laddar = vy === "bortvalda" ? bortvalda === null : vy === "arkiverade" ? arkiverade === null : aktiva === null;
  const vyFel = iUndan ? undanFel : fel;

  const tomt = filtrerar ? (
    <EmptyState
      icon={<Icon icon={SearchX} size="lg" color="secondary" />}
      title={text({ sv: "Inga leads matchar filtret", en: "No leads match the filter" })}
      description={text({ sv: "Sökningen går på bolag, kontaktnamn och kontaktens mejl.", en: "The search covers company, contact name and the contact's email." })}
      actions={<Button label={text({ sv: "Rensa filtret", en: "Clear the filter" })} variant="secondary" onClick={rensa} />}
    />
  ) : vy === "bortvalda" ? (
    <EmptyState icon={<Icon icon={Target} size="lg" color="secondary" />} title={text({ sv: "Inga bortvalda bolag", en: "No ruled-out companies" })} description={text({ sv: "Bolag Iris väljer bort hamnar här. Inget raderas av sig självt.", en: "Companies Iris rules out land here. Nothing is deleted by itself." })} />
  ) : vy === "arkiverade" ? (
    <EmptyState icon={<Icon icon={Archive} size="lg" color="secondary" />} title={text({ sv: "Inga arkiverade leads", en: "No archived leads" })} description={text({ sv: "Arkiverade leads får inga mejl och går att återställa härifrån.", en: "Archived leads get no emails and can be restored from here." })} actions={<Button label={text({ sv: "Visa att bearbeta", en: "Show to work on" })} variant="secondary" onClick={() => setVy("alla")} />} />
  ) : vy === "testyta" ? (
    <EmptyState icon={<Icon icon={FlaskConical} size="lg" color="secondary" />} title={text({ sv: "Testytan är tom", en: "The test area is empty" })} description={text({ sv: "Leads från provkörningar står här och mejlas aldrig förrän de flyttas till skarpa listan.", en: "Leads from test runs stand here and are never emailed until moved to the live list." })} />
  ) : (aktiva?.length ?? 0) > 0 ? (
    <EmptyState
      icon={<Icon icon={Send} size="lg" color="secondary" />}
      title={vy === "alla" ? text({ sv: "Inga leads väntar på utskick", en: "No leads are waiting to be sent" }) : text({ sv: `Inga leads står som ${vynamnLiten}`, en: `No leads are ${vynamnLiten}` })}
      description={text({ sv: "De kontaktade finns under Skickat i dagens Leads.", en: "The contacted ones are under Sent in today's Leads." })}
      actions={vy !== "alla" ? <Button label={text({ sv: "Visa alla att bearbeta", en: "Show all to work on" })} variant="secondary" onClick={() => setVy("alla")} /> : undefined}
    />
  ) : (
    <EmptyState
      icon={<Icon icon={Target} size="lg" color="secondary" />}
      title={text({ sv: "Inga leads ännu", en: "No leads yet" })}
      description={text({ sv: "Kör Iris eller importera en lista, så hamnar bolagen här.", en: "Run Iris or import a list, and the companies land here." })}
      actions={<Button label={text({ sv: "Kör Iris i Leads", en: "Run Iris in Leads" })} variant="secondary" href="/dashboard/leads" />}
    />
  );

  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span>{" "}
        <span className="crm-raknefot-tal">{urval.length ? `${tal(sidor.fran + 1)}–${tal(sidor.till)}` : "0"}</span>{" "}
        <span className="crm-raknefot-etikett">{text({ sv: "av", en: "of" })}</span> <span className="crm-raknefot-tal">{tal(urval.length)}</span>
      </span>
      {!iUndan && vy !== "testyta" ? (
        <>
          <span>
            <span className="crm-raknefot-etikett">{text(STATUS_ETIKETT.new)}</span> <span className="crm-raknefot-tal">{tal(antal.new)}</span>
          </span>
          <span>
            <span className="crm-raknefot-etikett">{text(STATUS_ETIKETT.ready)}</span> <span className="crm-raknefot-tal">{tal(antal.ready)}</span>
          </span>
        </>
      ) : null}
      {sidor.antalSidor > 1 ? (
        <span className="ml-auto">
          <Pagination page={sidor.sida + 1} onChange={bytSida} totalItems={urval.length} pageSize={SIDSTORLEK} variant="compact" size="sm" label={text({ sv: "Sidor", en: "Pages" })} />
        </span>
      ) : null}
    </div>
  );

  // ---- Åtgärdsraden ----------------------------------------------------------------
  const utan = valt.filter((p) => UTAN_UTKAST.has(p.utkast_status ?? "saknas")).length;
  const av = { isDisabled: !skriv.far || atgard != null, tooltip: skriv.skal ?? undefined };
  const fler: DropdownMenuOption[] =
    vy === "bortvalda" || vy === "arkiverade"
      ? []
      : vy === "testyta"
        ? [
            { label: text({ sv: "Skapa utkast", en: "Create drafts" }), icon: <Icon icon={FilePen} size="sm" />, isDisabled: utan === 0 || !skriv.far, onClick: () => void skapaUtkast(valt, false) },
            { label: text({ sv: "Bearbeta om", en: "Process again" }), icon: <Icon icon={RefreshCw} size="sm" />, isDisabled: !skriv.far, description: text({ sv: "Ny research och nytt utkast", en: "New research and a new draft" }), onClick: () => setBekraftas({ typ: "bearbeta", rader: valt }) }
          ]
        : [
            { label: text({ sv: "Skapa om utkast", en: "Recreate drafts" }), icon: <Icon icon={RefreshCw} size="sm" />, isDisabled: !skriv.far, onClick: () => setBekraftas({ typ: "skapa-om", rader: valt }) },
            ...(valt.some(harFattMejl) ? [{ label: text({ sv: "Skapa uppföljning", en: "Create follow-up" }), icon: <Icon icon={Send} size="sm" />, isDisabled: !skriv.far, onClick: () => void uppfoljning(valt) }] : []),
            { label: text({ sv: "Flytta till testytan", en: "Move to the test area" }), icon: <Icon icon={FlaskConical} size="sm" />, isDisabled: !skriv.far, description: text({ sv: "Kan då inte skickas", en: "Can then not be sent" }), onClick: () => void flytta(valt, "test") },
            ...(flyttbar ? [{ label: text({ sv: "Flytta till main", en: "Move to main" }), icon: <Icon icon={Truck} size="sm" />, onClick: () => void tillMain(valt) }] : [])
          ];

  const atgardsrad =
    (!smal || valjer) && (selectionState.hasSelection || atgard) ? (
      <div className="crm-atgardsrad-plats">
        <div className="crm-atgardsrad">
          {atgard && framsteg ? (
            <div className="flex min-w-[320px] items-center gap-3 px-2" role="status" aria-live="polite">
              <span className="whitespace-nowrap text-[0.875rem] font-semibold tabular-nums text-ink">
                {atgard === "skicka" ? text({ sv: `Skickar ${framsteg.klara} av ${framsteg.totalt}`, en: `Sending ${framsteg.klara} of ${framsteg.totalt}` }) : text({ sv: `Flyttar ${framsteg.klara} av ${framsteg.totalt}`, en: `Moving ${framsteg.klara} of ${framsteg.totalt}` })}
              </span>
              <div className="flex-1">
                <ProgressBar label={text({ sv: "Förlopp", en: "Progress" })} isLabelHidden value={framsteg.klara} max={framsteg.totalt} />
              </div>
            </div>
          ) : (
            <TableSelectionToolbar
              selection={selectionState}
              size="md"
              variant="transparent"
              label={text({ sv: "Åtgärder för markerade leads", en: "Actions for selected leads" })}
              renderSelectionLabel={(n) => <span className="tabular-nums">{n === 1 ? text({ sv: "1 markerat", en: "1 selected" }) : text({ sv: `${n} markerade`, en: `${n} selected` })}</span>}
              clearLabel={text({ sv: "Avmarkera", en: "Unselect" })}
              startContent={
                <>
                  {vy === "arkiverade" ? (
                    <Button label={text({ sv: "Återställ", en: "Restore" })} variant="ghost" size="md" icon={<Icon icon={ArchiveRestore} size="sm" />} isLoading={atgard === "aterstall"} {...av} onClick={(e) => void arkivera(valt, false, e.currentTarget)} />
                  ) : null}
                  {vy === "testyta" ? (
                    <Button label={text({ sv: "Flytta till skarpa listan", en: "Move to the live list" })} variant="ghost" size="md" icon={<Icon icon={ArrowRightLeft} size="sm" />} isLoading={atgard === "skarp"} {...av} onClick={() => void flytta(valt, "skarp")} />
                  ) : null}
                  {!iUndan && vy !== "testyta" ? (
                    <>
                      <Button label={text({ sv: "Skicka utkast", en: "Send drafts" })} variant="primary" size="md" icon={<Icon icon={Send} size="sm" />} isLoading={atgard === "skicka"} {...av} onClick={() => {
                        if (valt.some(kanSkickas)) {
                          setFlyttaProv(false);
                          setBekraftas({ typ: "skicka", rader: valt });
                        } else {
                          const godkanda = valt.filter((p) => p.utkast_status === "godkant").length;
                          visa({
                            type: godkanda ? "info" : "error",
                            body: godkanda
                              ? text({ sv: `De ${godkanda} markerade utkasten är redan godkända och skickas i tur och ordning från kön.`, en: `The ${godkanda} selected drafts are already approved and go out in turn from the queue.` })
                              : text({ sv: "Inget av de markerade bolagen har ett utkast som väntar. Välj Skapa utkast först.", en: "None of the selected companies has a draft waiting. Choose Create drafts first." }),
                            uniqueID: "iris-atgard"
                          });
                        }
                      }} />
                      <Button label={text({ sv: `Skapa utkast (${utan})`, en: `Create drafts (${utan})` })} variant="ghost" size="md" icon={<Icon icon={FilePen} size="sm" />} isLoading={atgard === "skapa"} isDisabled={av.isDisabled || utan === 0} tooltip={av.tooltip} onClick={() => void skapaUtkast(valt, false)} />
                    </>
                  ) : null}
                  {vy !== "arkiverade" ? (
                    <Button label={text({ sv: "Arkivera", en: "Archive" })} variant="ghost" size="md" icon={<Icon icon={Archive} size="sm" />} isLoading={atgard === "arkivera"} {...av} onClick={(e) => void arkivera(valt, true, e.currentTarget)} />
                  ) : null}
                  {fler.length ? (
                    <DropdownMenu button={{ label: text({ sv: "Fler", en: "More" }), variant: "ghost", size: "md", icon: <Icon icon={MoreHorizontal} size="sm" />, isDisabled: av.isDisabled, tooltip: av.tooltip }} items={fler} placement="above" />
                  ) : null}
                  <Button label={text({ sv: "Ta bort", en: "Delete" })} variant="ghost" size="md" icon={<Icon icon={Trash2} size="sm" />} className="crm-farlig" isLoading={atgard === "ta-bort"} {...av} onClick={() => setBekraftas({ typ: "ta-bort", rader: valt })} />
                </>
              }
            />
          )}
        </div>
      </div>
    ) : null;

  // ---- Bekräftelsen (LR-057) ---------------------------------------------------------
  const bekr = (() => {
    if (!bekraftas) return null;
    const r = bekraftas.rader;
    if (bekraftas.typ === "skicka") {
      const skickbara = r.filter(kanSkickas);
      const prov = skickbara.filter((p) => p.origin === "test");
      const berorda = flyttaProv ? skickbara : skickbara.filter((p) => !prov.includes(p));
      const godkanda = r.filter((p) => p.utkast_status === "godkant").length;
      return {
        titel: berorda.length === 1 ? text({ sv: "1 mejl godkänns och skickas till:", en: "1 email is approved and sent to:" }) : text({ sv: `${berorda.length} mejl godkänns och skickas till:`, en: `${berorda.length} emails are approved and sent to:` }),
        poster: berorda.map((p) => ({ id: p.id, namn: p.company_name, under: p.contact_email ?? null })),
        overhoppade: r.length - skickbara.length - godkanda,
        tillagg: prov.length ? (
          <div className="crm-kallkort rounded-[16px] p-3">
            <CheckboxInput
              label={text({ sv: `Flytta över ${prov.length} från provkörningar till dina riktiga leads och skicka dem också`, en: `Move ${prov.length} from test runs to your real leads and send them too` })}
              description={text({ sv: "Annars skickas de inte: en provkörnings bolag mejlas aldrig av misstag.", en: "Otherwise they are not sent: a test run's companies are never emailed by mistake." })}
              value={flyttaProv}
              onChange={setFlyttaProv}
            />
          </div>
        ) : undefined,
        forklaring: text({ sv: "Varje mejl går genom sändspärrarna och skickas i tur och ordning från kön, ett i minuten, vardagar från 08:00.", en: "Every email passes the send guards and goes out in turn from the queue, one a minute, weekdays from 08:00." }),
        handling: berorda.length === 1 ? text({ sv: "Skicka 1 mejl", en: "Send 1 email" }) : text({ sv: `Skicka ${berorda.length} mejl`, en: `Send ${berorda.length} emails` }),
        farlig: false,
        bekrafta: () => void skicka(r)
      };
    }
    if (bekraftas.typ === "skapa-om") {
      return {
        titel: text({ sv: `Utkasten skrivs om för ${r.length} leads:`, en: `The drafts are rewritten for ${r.length} leads:` }),
        poster: r.map((p) => ({ id: p.id, namn: p.company_name, under: utkastText(p, locale, text) })),
        overhoppade: 0,
        tillagg: undefined,
        forklaring: text({ sv: "Väntande och godkända utkast ersätts och skickas aldrig. De nya skrivs ur den research som redan finns, så bedömningen av bolagen ändras inte.", en: "Pending and approved drafts are replaced and never sent. The new ones are written from the existing research, so the assessment of the companies does not change." }),
        handling: text({ sv: `Skriv om ${r.length} utkast`, en: `Rewrite ${r.length} drafts` }),
        farlig: false,
        bekrafta: () => void skapaUtkast(r, true)
      };
    }
    if (bekraftas.typ === "bearbeta") {
      return {
        titel: text({ sv: `${r.length} bolag researchas om och får nya utkast:`, en: `${r.length} companies are researched again and get new drafts:` }),
        poster: r.map((p) => ({ id: p.id, namn: p.company_name, under: p.ort ?? null })),
        overhoppade: 0,
        tillagg: (
          <Selector
            label={text({ sv: "Utkastets struktur", en: "Draft structure" })}
            value={struktur}
            onChange={(v) => {
              if (v !== "a" && v !== "b") return;
              setStruktur(v);
              void import("@/lib/leads/struktur").then((m) => m.sparaStruktur(v));
            }}
            options={[
              { value: "a", label: text({ sv: "A, standardmejlet", en: "A, the standard email" }) },
              { value: "b", label: text({ sv: "B, kort med en fråga", en: "B, short with a question" }) }
            ]}
            width="100%"
          />
        ),
        forklaring: text({ sv: "Researchen körs om och räknas mot er leadsbudget. Bedömningen kan ändras.", en: "The research runs again and counts against your leads budget. The assessment may change." }),
        handling: text({ sv: `Bearbeta om ${r.length}`, en: `Process ${r.length} again` }),
        farlig: false,
        bekrafta: () => void bearbetaOm(r)
      };
    }
    return {
      titel: r.length === 1 ? text({ sv: "1 lead tas bort för gott:", en: "1 lead is deleted for good:" }) : text({ sv: `${r.length} leads tas bort för gott:`, en: `${r.length} leads are deleted for good:` }),
      poster: r.map((p) => ({ id: p.id, namn: p.company_name, under: p.contact_email ?? null })),
      overhoppade: 0,
      tillagg: undefined,
      forklaring: text({ sv: "Det går inte att ångra. Leads som redan fått mejl tas inte bort; arkivera dem i stället.", en: "This cannot be undone. Leads that have been emailed are not deleted; archive them instead." }),
      handling: r.length === 1 ? text({ sv: "Ta bort 1 lead", en: "Delete 1 lead" }) : text({ sv: `Ta bort ${r.length} leads`, en: `Delete ${r.length} leads` }),
      farlig: true,
      bekrafta: () => void taBort(r)
    };
  })();

  const postrad = postId ? (aktiva?.find((p) => p.id === postId) ?? bortvalda?.find((p) => p.id === postId) ?? arkiverade?.find((p) => p.id === postId) ?? null) : null;

  return (
    <Sida
      objekt="leads"
      rubrik={text({ sv: "Leads", en: "Leads" })}
      antal={aktiva == null ? undefined : tal(skarpa.length)}
      vyrad={
        smal ? (
          <Selector
            label={text({ sv: "Vy", en: "View" })}
            isLabelHidden
            variant="secondary"
            size="md"
            value={vy}
            onChange={(v) => v && setVy(v as Vy)}
            options={vyer.map((v) => ({ value: v, label: vyantal(v) ? `${text(vynamn[v])}  ${vyantal(v)}` : text(vynamn[v]) }))}
          />
        ) : (
          <>
            <Vyval value={vy} onChange={setVy} label={text({ sv: "Vy", en: "View" })} val={vyer.map((v) => ({ v, namn: text(vynamn[v]), antal: vyantal(v) }))} />
            {live ? (
              <span className="inline-flex shrink-0 items-center gap-1.5 text-[0.8125rem] text-ink-muted">
                <Prick ton="ockra" pulserar />
                {text({ sv: "Uppdateras live", en: "Updating live" })}
              </span>
            ) : null}
          </>
        )
      }
      vyradHoger={
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
          <div className="w-full min-w-0 sm:w-[240px] sm:flex-none">
            <TextInput
              type="search"
              label={text({ sv: "Sök leads", en: "Search leads" })}
              isLabelHidden
              placeholder={text({ sv: "Bolag eller kontakt", en: "Company or contact" })}
              startIcon="search"
              hasClear
              value={sok}
              onChange={(v) => setSok(v)}
              width="100%"
              controlClassName="crm-sokfalt"
            />
          </div>
          {smal ? (
            <Button
              variant={valjer ? "secondary" : "ghost"}
              size="md"
              label={valjer ? text({ sv: "Klar", en: "Done" }) : text({ sv: "Välj", en: "Select" })}
              onClick={() => {
                if (valjer) setValda(new Set());
                setValjer(!valjer);
              }}
            />
          ) : null}
          <DropdownMenu
            button={{ label: antalFilter ? text({ sv: `Filter ${antalFilter}`, en: `Filter ${antalFilter}` }) : text({ sv: "Filter", en: "Filter" }), variant: antalFilter ? "secondary" : "ghost", size: "md", icon: <Icon icon={ListFilter} size="sm" /> }}
            items={filterval}
          />
          <DropdownMenu button={{ label: aktivVy ? aktivVy.namn : text({ sv: "Vyer", en: "Views" }), variant: aktivVy ? "secondary" : "ghost", size: "md", icon: <Icon icon={Bookmark} size="sm" /> }} items={vyval} />
          <Selector
            label={text({ sv: "Sortera", en: "Sort" })}
            isLabelHidden
            variant="ghost"
            size="md"
            startIcon={sortering === "webb" ? Globe : sortering === "poang" ? Gauge : Clock}
            value={sortering}
            onChange={(v) => v && setSortering(v as Sortering)}
            options={[
              { value: "nyast", label: text({ sv: "Nyaste först", en: "Newest first" }), description: text({ sv: "Under research först, sedan senaste händelse", en: "Being researched first, then latest event" }) },
              { value: "poang", label: text({ sv: "Högst poäng", en: "Highest score" }), description: text({ sv: "Bäst passande bolag först", en: "Best-fitting companies first" }) },
              ...(visarWebb ? [{ value: "webb", label: text({ sv: "Webbplats, lägst betyg", en: "Website, lowest score" }), description: text({ sv: "Sämst sajt först", en: "Weakest site first" }) }] : [])
            ]}
          />
        </div>
      }
    >
      <div className="crm-bolag" ref={listref}>
        {/* Utfallen sägs upp här, i en region som finns hela tiden. */}
        <div role="status" className="sr-only">
          {statusbesked}
        </div>
        {sidofel ? (
          <div className="px-4 pt-3 sm:px-6">
            <Banner status="warning" container="card" title={text({ sv: "Uppgifter eller sparade vyer kunde inte hämtas", en: "Tasks or saved views could not be loaded" })} description={sidofel} />
          </div>
        ) : null}
        {besked ? (
          <div className="px-4 pt-3 sm:px-6">
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
          </div>
        ) : null}
        {vy === "bortvalda" || vy === "arkiverade" ? (
          <p className="px-4 pb-1 pt-3 text-[0.875rem] text-ink-muted sm:px-6">
            {vy === "bortvalda"
              ? text({ sv: "Bolag Iris valde bort. Inget raderas av sig självt: markera och välj Ta bort för att radera dem för gott.", en: "Companies Iris ruled out. Nothing is deleted by itself: select and choose Delete to remove them for good." })
              : text({ sv: "Arkiverade leads får inga mejl, behåller sin historik och hoppas över av nästa sökning.", en: "Archived leads get no emails, keep their history and are skipped by the next search." })}
          </p>
        ) : null}
        {ordningFryst ? (
          <p className="px-4 pt-2 text-[0.8125rem] text-ink-muted sm:px-6">{text({ sv: "Ordningen står still medan du markerar.", en: "The order holds still while you select." })}</p>
        ) : null}

        {vyFel ? (
          <div className="p-4 sm:p-6">
            <Felruta fel={vyFel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => (iUndan ? void hamtaUndan(vy as "bortvalda" | "arkiverade") : void hamta())} />} />
          </div>
        ) : laddar ? (
          <Tabellskelett rader={10} kolumner={smal ? 2 : 7} markering={!smal} label={text({ sv: "Hämtar leads", en: "Loading leads" })} />
        ) : smal ? (
          urval.length === 0 ? (
            <div className="py-10">{tomt}</div>
          ) : (
            <>
              <div className="px-2">
                <List hasDividers density="balanced" edge="padded">
                  {sidansRader.map((p) => {
                    const namn = p.company_name || text({ sv: "Namnlöst bolag", en: "Unnamed company" });
                    const vald = valda.has(p.id);
                    const vaxla = (pa: boolean) =>
                      setValda((forr) => {
                        const ny = new Set(forr);
                        if (pa) ny.add(p.id);
                        else ny.delete(p.id);
                        return ny;
                      });
                    const n = poang(p);
                    const under = [text(STATUS_ETIKETT[p.status] ?? { sv: p.status, en: p.status }), n != null && !obedomd(p) ? text({ sv: `${n} poäng`, en: `${n} points` }) : null, p.ort, domanAv(p.website)].filter(Boolean).join(" · ");
                    const ut = p.utkast_status ? utkastText(p, locale, text) : null;
                    const m = betyg(p);
                    return (
                      <ListItem
                        key={p.id}
                        label={<span className="font-semibold text-ink">{namn}</span>}
                        description={under}
                        startContent={
                          valjer && p.origin !== "example" ? (
                            <span className="-my-1 inline-flex size-11 items-center justify-center" onClick={(e) => e.stopPropagation()}>
                              <CheckboxInput label={text({ sv: `Markera ${namn}`, en: `Select ${namn}` })} isLabelHidden value={vald} onChange={vaxla} />
                            </span>
                          ) : (
                            <span aria-hidden className="inline-flex">
                              <Avatar name={utanBolagsform(namn)} size={32} shape="rounded" tooltip={false} className={`crm-avatar ${tonklass(tonFor(utanBolagsform(namn)))}`} />
                            </span>
                          )
                        }
                        endContent={
                          <span className="flex flex-col items-end gap-1">
                            {m != null ? <Badge variant={band(m) === "lag" ? "green" : band(m) === "mellan" ? "yellow" : "neutral"} label={`${m}/10`} /> : null}
                            {ut ? <span className="max-w-[9rem] truncate text-right text-[0.75rem] text-ink-muted">{ut}</span> : null}
                          </span>
                        }
                        onClick={() => (valjer ? vaxla(!vald) : sattPost(p.id))}
                        isSelected={valjer ? false : postId === p.id}
                      />
                    );
                  })}
                </List>
              </div>
              {fot}
            </>
          )
        ) : (
          <div className="crm-tabell">
            <Table<Lead>
              data={sidansRader}
              columns={kolumner}
              idKey="id"
              density="balanced"
              dividers="rows"
              hasHover
              textOverflow="truncate"
              plugins={{ selection: markering }}
              emptyState={<div className="py-12">{tomt}</div>}
            />
            {urval.length > 0 ? fot : null}
          </div>
        )}

        {atgardsrad}
      </div>

      <LeadPanel
        id={postId}
        listrad={postrad}
        bas={bas}
        stang={() => sattPost(null)}
        andrat={() => meddelaLeadsUppdaterade("crm-iris")}
      />

      {bekr ? (
        <Bekraftelse
          oppen
          titel={bekr.titel}
          poster={bekr.poster}
          overhoppade={bekr.overhoppade}
          tillagg={bekr.tillagg}
          forklaring={bekr.forklaring}
          handling={bekr.handling}
          farlig={bekr.farlig}
          upptagen={atgard != null}
          bekrafta={bekr.bekrafta}
          stang={() => setBekraftas(null)}
        />
      ) : null}

      {/* Spara vy (LR-035): ett namn, högst 80 tecken i fältet (servern tar 100). */}
      <Dialog isOpen={sparaVy != null} onOpenChange={(o) => !o && !sparaVy?.sparar && setSparaVy(null)} purpose="form" width={480}>
        <Layout
          header={<DialogHeader title={text({ sv: "Spara filtret som vy", en: "Save the filter as a view" })} onOpenChange={(o) => !o && !sparaVy?.sparar && setSparaVy(null)} />}
          content={
            <LayoutContent>
              <form
                id="iris-spara-vy"
                noValidate
                onSubmit={(e) => {
                  e.preventDefault();
                  void sparaDenna();
                }}
              >
                <TextInput
                  label={text({ sv: "Vyns namn", en: "The view's name" })}
                  placeholder={text({ sv: "Heta leads i Göteborg", en: "Hot leads in Gothenburg" })}
                  value={sparaVy?.namn ?? ""}
                  onChange={(v) => setSparaVy((s) => (s ? { ...s, namn: v.slice(0, 80), fel: null } : s))}
                  width="100%"
                  status={sparaVy?.fel ? { type: "error", message: sparaVy.fel } : undefined}
                  hasAutoFocus
                />
              </form>
            </LayoutContent>
          }
          footer={
            <LayoutFooter>
              <HStack justify="end" gap={2}>
                <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" isDisabled={sparaVy?.sparar} onClick={() => setSparaVy(null)} />
                <Button type="submit" form="iris-spara-vy" variant="primary" label={text({ sv: "Spara vyn", en: "Save the view" })} isLoading={sparaVy?.sparar} />
              </HStack>
            </LayoutFooter>
          }
        />
      </Dialog>

      {/* Ifyllnaden vid befordran (LR-104): det som saknas, i samma anrop som flytten. */}
      <Dialog isOpen={ifyllnad != null} onOpenChange={(o) => !o && setIfyllnad(null)} purpose="form" width={640}>
        <Layout
          header={<DialogHeader title={text({ sv: "Fyll i det som saknas", en: "Fill in what is missing" })} onOpenChange={(o) => !o && setIfyllnad(null)} />}
          content={
            <LayoutContent>
              <div className="flex flex-col gap-6">
                <p className="text-[0.875rem] text-ink2">
                  {text({ sv: "För att flyttas till skarpa listan behöver bolaget organisationsnummer, webbplats och en mejladress.", en: "To move to the live list the company needs a company number, a website and an email address." })}
                </p>
                {(ifyllnad ?? []).map((r, i) => (
                  <form
                    key={r.lead.id}
                    noValidate
                    className="crm-kallkort flex flex-col gap-3 rounded-[16px] p-4"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void befordraMedIfyllnad(i);
                    }}
                  >
                    <Postchip namn={r.lead.company_name} />
                    {r.fel ? <p className="text-[0.8125rem] text-danger">{r.fel}</p> : null}
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <TextInput label={text({ sv: "Organisationsnummer", en: "Company number" })} value={r.orgnr} onChange={(v) => setIfyllnad((l) => l?.map((x, k) => (k === i ? { ...x, orgnr: v } : x)) ?? null)} width="100%" isOptional />
                      <TextInput label={text({ sv: "Webbplats", en: "Website" })} value={r.website} onChange={(v) => setIfyllnad((l) => l?.map((x, k) => (k === i ? { ...x, website: v } : x)) ?? null)} width="100%" isOptional status={r.saknas.includes("website") ? { type: "error", message: text({ sv: "Saknas", en: "Missing" }) } : undefined} />
                      <TextInput label={text({ sv: "E-post", en: "Email" })} type="email" value={r.contact_email} onChange={(v) => setIfyllnad((l) => l?.map((x, k) => (k === i ? { ...x, contact_email: v } : x)) ?? null)} width="100%" isOptional status={r.saknas.includes("contact_email") ? { type: "error", message: text({ sv: "Saknas", en: "Missing" }) } : undefined} />
                    </div>
                    <div className="flex justify-end">
                      <Button type="submit" size="sm" variant="primary" label={text({ sv: "Flytta till skarpa listan", en: "Move to the live list" })} isLoading={r.sparar} isDisabled={!skriv.far} tooltip={skriv.skal ?? undefined} />
                    </div>
                  </form>
                ))}
              </div>
            </LayoutContent>
          }
          footer={
            <LayoutFooter>
              <HStack justify="end" gap={2}>
                <Button label={text({ sv: "Stäng", en: "Close" })} variant="ghost" onClick={() => setIfyllnad(null)} />
              </HStack>
            </LayoutFooter>
          }
        />
      </Dialog>
    </Sida>
  );
}
