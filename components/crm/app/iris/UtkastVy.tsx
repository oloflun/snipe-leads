"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AtSign, Building2, CalendarClock, Clock, FilePen, FilePlus2, Inbox, SearchX, Send, Tag, Type, Undo2, X } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { DateTimeInput, type ISODateTimeString } from "@astryxdesign/core/DateTimeInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { List, ListItem } from "@astryxdesign/core/List";
import { Pagination } from "@astryxdesign/core/Pagination";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, TableSelectionToolbar, pixel, proportional, useTableSelection, useTableSelectionState, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { SIDSTORLEK, useSida, useSidaFor } from "@/components/leads/sidindelning";
import { Bekraftelse } from "@/components/crm/app/iris/Bekraftelse";
import { UtkastPanel, type Utkastpost } from "@/components/crm/app/iris/UtkastPanel";
import { Kolumnrubrik, Postchip, Prick, Tabellskelett, Vyval, grannfokus, tonFor, tonklass, useSkrivratt, useSmal, utanBolagsform } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { CrmFel } from "@/lib/crm/api";
import { LEADS_UPPDATERADE, irisAnrop, meddelaLeadsUppdaterade } from "@/lib/crm/iris/anrop";
import { UPPFOLJNING_HOPPAD, sandtid, type Utkastsvar } from "@/lib/crm/iris/lead";
import { forstaMening } from "@/lib/crm/iris/mejl";
import {
  SKICKATLAGE,
  UTAN_AMNE,
  skalUr,
  skickatlage,
  skickatton,
  type Besked,
  type Kopost,
  type Kosvar,
  type Sandutfall,
  type Signatur,
  type SkickatRad,
  type Skickatlage,
  type Skickatsvar
} from "@/lib/crm/iris/utkast";
import { delaCitat, senasteSvar } from "@/lib/leads/konversation";
import { offertForUtkast } from "@/lib/leads/offert";
import { useLocale, type Localized } from "@/lib/i18n";

type Vy = "granska" | "snart" | "skickat";
const VYER: Vy[] = ["granska", "snart", "skickat"];
type Lage = "" | Skickatlage;
type Atgard = "godkann" | "avvisa" | "skicka-nu" | "tid" | "tillbaka" | "uppfoljning";
type Bekraftas = { typ: "godkann" | "avvisa" | "skicka-nu" | "tillbaka"; ids: string[] };

/** En rad i listan, samma form i alla tre vyerna: kön och Skickat har olika fält. */
type Rad = {
  id: string;
  bolag: string;
  mottagare: string | null;
  amne: string | null;
  utdrag: string | null;
  tid: string | null;
  ko?: Kopost;
  skickat?: SkickatRad;
};

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });
const LAGEN: Skickatlage[] = ["vantar", "svarat", "mote", "ej"];
const vyUr = (v: string | null | undefined): Vy => (VYER.includes(v as Vy) ? (v as Vy) : "granska");

/** Källan vyn sänder med när den ändrat utkast: den har redan läst om och lyssnar inte på sin egen signal. */
const VYNS_KALLA = "crm-utkast";
/** Uppföljningarna Iris skriver följs så här ofta, högst så här många gånger (cirka fem minuter). */
const FOLJ_MS = 4000;
const FOLJ_MAX = 75;
/** Leadsen vars uppföljning skrivs, i webbläsaren, så att förloppet tas upp igen efter en omladdning. Läget läses alltid från backenden. */
const FOLJ_NYCKEL = "crm-iris-uppfoljningar";
type Foljning = { alla: string[]; kvar: string[] };
function lasFoljning(): Foljning | null {
  try {
    const f = JSON.parse(window.localStorage.getItem(FOLJ_NYCKEL) ?? "null") as Foljning | null;
    return f && Array.isArray(f.alla) && Array.isArray(f.kvar) && f.kvar.length ? f : null;
  } catch {
    return null;
  }
}
function sparaFoljning(f: Foljning | null) {
  try {
    if (f?.kvar.length) window.localStorage.setItem(FOLJ_NYCKEL, JSON.stringify(f));
    else window.localStorage.removeItem(FOLJ_NYCKEL);
  } catch {
    /* utan lagring följs förloppet bara tills sidan laddas om */
  }
}

/** Bolagen i en mening: högst tre namn, sedan hur många till. */
function namnlista(bolag: string[], text: (v: Localized) => string): string {
  return bolag.length <= 3 ? bolag.join(", ") : text({ sv: `${bolag.slice(0, 3).join(", ")} och ${bolag.length - 3} till`, en: `${bolag.slice(0, 3).join(", ")} and ${bolag.length - 3} more` });
}

/**
 * Iris › Utkast (steg 4.3, LU-030 till LU-088): mejlen från Iris i tre vyer.
 *
 * - Att granska: granskningskön (`GET /leads/queue`), nyast först. Utkastet öppnas
 *   i en panel med utkastredigeraren. Markerade godkänns eller avvisas i tur och
 *   ordning genom samma ändpunkt som ett enskilt klick, efter en bekräftelse med
 *   mottagarna (LU-036, LU-180).
 * - Skickas snart: godkända som väntar på sändfönstret (`GET /leads/skickat`,
 *   `schemalagt`), med Skicka nu, Ändra tid och Tillbaka till Iris (LU-084, LU-085).
 * - Skickat: varje skickat mejl med leadets läge nu, filtrerat på läget (LU-082,
 *   LU-083), och Skapa uppföljning för dem som väntar på svar (LU-086).
 *
 * Skickat och svar de senaste 28 dagarna står i vyraden, i räknefotens stil (LU-088).
 * Varför ett mejl inte gick ut säger backenden (sändspärrarna, LU-050 till LU-066):
 * skälet visas som det står, grupperat per skäl med bolagen.
 */
export function UtkastVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  // Agenternas data: under ett kundbesök märks det som test, läsrollen skriver inget.
  const skriv = useSkrivratt("test");
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);

  // ---- Adressen: vyn (`?vy=skickat`, länkar hit) och den öppna posten (`?utkast=`) -----
  const adressensVy = params?.get("vy");
  const [vy, setVyState] = useState<Vy>(vyUr(adressensVy));
  // Vyn följer adressen även när den byts utan omladdning (en länk, kommandopaletten).
  useEffect(() => {
    setVyState(vyUr(adressensVy));
  }, [adressensVy]);
  const adressensPost = params?.get("utkast") ?? null;
  const [postId, setPostId] = useState<string | null>(adressensPost);
  const postIdRef = useRef(postId);
  postIdRef.current = postId;
  useEffect(() => {
    setPostId(adressensPost);
  }, [adressensPost]);
  const skrivAdress = useCallback((andra: Record<string, string | null>) => {
    const q = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(andra)) {
      if (v) q.set(k, v);
      else q.delete(k);
    }
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);
  const sattPost = useCallback(
    (id: string | null) => {
      setPostId(id);
      skrivAdress({ utkast: id });
    },
    [skrivAdress]
  );
  const setVy = (v: Vy) => {
    setVyState(v);
    skrivAdress({ vy: v === "granska" ? null : v });
  };

  // ---- Hämtning ----------------------------------------------------------------------
  const [ko, setKo] = useState<Kopost[] | null>(null);
  const [koFel, setKoFel] = useState<unknown>(null);
  const [skickat, setSkickat] = useState<SkickatRad[] | null>(null);
  const [skickatFel, setSkickatFel] = useState<unknown>(null);
  const [signatur, setSignatur] = useState<Signatur | null>(null);
  const [antal28, setAntal28] = useState<{ skickat: number; svarat: number } | null>(null);
  const [offer, setOffer] = useState<string | null>(null);
  const koNr = useRef(0);
  const skickatNr = useRef(0);

  const hamtaKo = useCallback(async () => {
    const nr = ++koNr.current;
    try {
      const s = await irisAnrop<Kosvar>("/leads/queue");
      if (nr !== koNr.current) return;
      setKo(s?.items ?? []);
      if (s?.signatur) setSignatur(s.signatur);
      setKoFel(null);
    } catch (e) {
      if (nr !== koNr.current) return;
      setKoFel(e);
      setKo((k) => k ?? []);
    }
  }, []);
  const hamtaSkickat = useCallback(async () => {
    const nr = ++skickatNr.current;
    try {
      const [s, a] = await Promise.allSettled([irisAnrop<Skickatsvar>("/leads/skickat?limit=500"), irisAnrop<{ skickat?: number; svarat?: number }>("/leads/skickat/antal?dagar=28")]);
      if (nr !== skickatNr.current) return;
      if (s.status === "rejected") throw s.reason;
      setSkickat(s.value?.skickat ?? []);
      if (s.value?.signatur) setSignatur(s.value.signatur);
      setSkickatFel(null);
      // Nyckeltalen är en uppgift bredvid: faller de visas listan ändå.
      setAntal28(a.status === "fulfilled" ? { skickat: a.value?.skickat ?? 0, svarat: a.value?.svarat ?? 0 } : null);
    } catch (e) {
      if (nr !== skickatNr.current) return;
      setSkickatFel(e);
      setSkickat((k) => k ?? []);
    }
  }, []);
  const hamtaAllt = useCallback(() => {
    void hamtaKo();
    void hamtaSkickat();
  }, [hamtaKo, hamtaSkickat]);

  useEffect(() => {
    hamtaAllt();
    // Kundens erbjudande är bakgrunden AI:n skriver om utifrån. Saknas det körs AI:n utan.
    void offertForUtkast().then(setOffer, () => setOffer(null));
  }, [hamtaAllt]);

  // Ändras utkast någon annanstans (leadets panel, Iris-listan, dagens Leads) hämtas allt om.
  // Vyns egen signal hoppas över: den har redan läst om (klart()).
  useEffect(() => {
    const uppdatera = (e: Event) => {
      if ((e as CustomEvent).detail !== VYNS_KALLA) hamtaAllt();
    };
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    return () => window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
  }, [hamtaAllt]);

  // ---- Raderna ------------------------------------------------------------------------
  const [sok, setSok] = useState("");
  const sokFordrojd = useDeferredValue(sok);
  const [lage, setLage] = useState<Lage>("");

  const koRader = useMemo<Rad[]>(
    () =>
      (ko ?? []).map((k) => ({
        id: k.id,
        bolag: k.company_name || k.prospect_email || text({ sv: "Okänt bolag", en: "Unknown company" }),
        mottagare: k.prospect_email ?? null,
        amne: k.subject ?? null,
        utdrag: forstaMening(k.brodtext ?? k.body),
        tid: k.created_at ?? null,
        ko: k
      })),
    [ko, text]
  );
  const skickatRader = useMemo<Rad[]>(
    () =>
      (skickat ?? []).map((r) => {
        const svar = senasteSvar(r.konversation);
        return {
          id: r.id,
          bolag: r.company_name || r.prospect_email || text({ sv: "Okänt bolag", en: "Unknown company" }),
          mottagare: r.prospect_email,
          amne: r.subject,
          utdrag: svar ? delaCitat(svar.body)[0].replace(/\s+/g, " ") || null : null,
          tid: r.schemalagt ? (r.skickas_tidigast ?? null) : r.sent_at,
          skickat: r
        };
      }),
    [skickat, text]
  );
  const snart = useMemo(() => skickatRader.filter((r) => r.skickat?.schemalagt), [skickatRader]);
  const skickade = useMemo(() => skickatRader.filter((r) => !r.skickat?.schemalagt), [skickatRader]);

  const matchar = useCallback(
    (r: Rad) => {
      const s = sokFordrojd.trim().toLowerCase();
      if (!s) return true;
      return [r.bolag, r.mottagare, r.amne].some((v) => v?.toLowerCase().includes(s));
    },
    [sokFordrojd]
  );
  const lageAntal = useMemo(() => {
    const n: Record<Skickatlage, number> = { vantar: 0, svarat: 0, mote: 0, ej: 0 };
    for (const r of skickade) if (r.skickat && matchar(r)) n[skickatlage(r.skickat)] += 1;
    return n;
  }, [skickade, matchar]);

  const urval = useMemo(() => {
    if (vy === "granska") return koRader.filter(matchar);
    if (vy === "snart") return snart.filter(matchar);
    return skickade.filter((r) => matchar(r) && (!lage || (r.skickat && skickatlage(r.skickat) === lage)));
  }, [vy, koRader, snart, skickade, matchar, lage]);
  const filtrerar = Boolean(sokFordrojd.trim() || (vy === "skickat" && lage));

  // ---- Markering ------------------------------------------------------------------------
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [valjer, setValjer] = useState(false);
  useEffect(() => {
    setValda(new Set());
  }, [vy, lage, sokFordrojd]);
  // Kön och de schemalagda går att markera; i Skickat bara de som väntar på svar (Skapa uppföljning, LU-086).
  const markerbara = useMemo(
    () => (vy === "skickat" ? urval.filter((r) => r.skickat && r.skickat.prospect_id && skickatlage(r.skickat) === "vantar") : vy === "snart" ? urval.filter((r) => r.skickat?.queue_item_id) : urval),
    [vy, urval]
  );
  const { selectionConfig, selectionState } = useTableSelectionState<Rad>({ data: markerbara, idKey: "id", selectedKeys: valda, setSelectedKeys: setValda });
  const markering = useTableSelection<Rad>({ ...selectionConfig, getRowLabel: (r) => r.bolag });
  const valt = useMemo(() => markerbara.filter((r) => valda.has(r.id)), [markerbara, valda]);

  // ---- Sidindelning -------------------------------------------------------------------
  const sidor = useSida(urval.length, `${vy}|${lage}|${sokFordrojd}`);
  const sidansRader = useMemo(() => urval.slice(sidor.fran, sidor.till), [urval, sidor.fran, sidor.till]);
  const urvalIds = useMemo(() => urval.map((r) => r.id), [urval]);
  useSidaFor(postId, urvalIds, sidor.setSida);
  const listref = useRef<HTMLDivElement>(null);
  const bytSida = (n: number) => {
    sidor.setSida(n - 1);
    const el = listref.current;
    if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ block: "start" });
  };

  // ---- Handlingarna ---------------------------------------------------------------------
  const [atgard, setAtgard] = useState<Atgard | null>(null);
  const [framsteg, setFramsteg] = useState<{ klara: number; totalt: number } | null>(null);
  const [besked, setBesked] = useState<Besked | null>(null);
  const [statusbesked, setStatusbesked] = useState("");
  const [bekraftas, setBekraftas] = useState<Bekraftas | null>(null);
  const [tidFor, setTidFor] = useState<{ ids: string[]; tid: ISODateTimeString | undefined; fel: string | null } | null>(null);

  const klart = () => {
    hamtaAllt();
    meddelaLeadsUppdaterade(VYNS_KALLA);
  };

  // Förloppet för en åtgärd på flera sägs upp i den permanenta regionen (raden i åtgärdsraden visar det bara).
  useEffect(() => {
    if (!atgard || !framsteg) return;
    setStatusbesked(
      atgard === "avvisa"
        ? text({ sv: `Avvisar ${framsteg.klara} av ${framsteg.totalt}`, en: `Rejecting ${framsteg.klara} of ${framsteg.totalt}` })
        : text({ sv: `Skickar ${framsteg.klara} av ${framsteg.totalt}`, en: `Sending ${framsteg.klara} of ${framsteg.totalt}` })
    );
  }, [atgard, framsteg, text]);

  // ---- Uppföljningar som Iris skriver (LU-086): följs tills de står under Att granska ------------
  // Läget per lead läses från backenden (`GET /leads/prospects/{id}/utkast`, `skrivs` medan jobbet
  // står i kö eller körs). Vilka leads som följs sparas i webbläsaren, så att förloppet tas upp igen
  // efter en omladdning.
  const [foljning, setFoljningState] = useState<Foljning | null>(null);
  const setFoljning = useCallback((f: Foljning | null) => {
    setFoljningState(f);
    sparaFoljning(f);
  }, []);
  useEffect(() => {
    setFoljningState(lasFoljning());
  }, []);
  const foljKvar = foljning?.kvar.join(",") ?? "";
  useEffect(() => {
    if (!foljning?.kvar.length) return;
    let varv = 0;
    let avbruten = false;
    const t = window.setInterval(async () => {
      if (document.visibilityState !== "visible") return;
      varv += 1;
      if (varv > FOLJ_MAX) {
        window.clearInterval(t);
        setFoljning(null);
        visaBesked({ text: text({ sv: "Uppföljningarna tar längre tid än vanligt. De står under Att granska när de är klara.", en: "The follow-ups are taking longer than usual. They show under To review when done." }), fel: true });
        return;
      }
      const lagen = await Promise.allSettled(foljning.kvar.map((pid) => irisAnrop<Utkastsvar>(`/leads/prospects/${encodeURIComponent(pid)}/utkast`)));
      if (avbruten) return;
      // Ett lead som inte går att läsa räknas som klart: annars följs det i evighet.
      const kvar = foljning.kvar.filter((_, i) => {
        const l = lagen[i];
        return l.status === "fulfilled" && l.value?.utkast_status === "skrivs";
      });
      if (kvar.length === foljning.kvar.length) return;
      void hamtaKo();
      meddelaLeadsUppdaterade(VYNS_KALLA);
      if (kvar.length) {
        setFoljning({ alla: foljning.alla, kvar });
        return;
      }
      setFoljning(null);
      const n = foljning.alla.length;
      visaBesked({
        text: n === 1 ? text({ sv: "Uppföljningen är klar och står under Att granska.", en: "The follow-up is done and shows under To review." }) : text({ sv: `${n} uppföljningar är klara och står under Att granska.`, en: `${n} follow-ups are done and show under To review.` }),
        fel: false
      });
    }, FOLJ_MS);
    return () => {
      avbruten = true;
      window.clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- följningen startas om bara när leadsen som följs ändras
  }, [foljKvar]);
  const foljtext = foljning
    ? foljning.alla.length === 1
      ? text({ sv: "Iris skriver uppföljningen.", en: "Iris is writing the follow-up." })
      : text({ sv: `Iris skriver uppföljningar: ${foljning.alla.length - foljning.kvar.length} av ${foljning.alla.length} klara.`, en: `Iris is writing follow-ups: ${foljning.alla.length - foljning.kvar.length} of ${foljning.alla.length} done.` })
    : "";
  // Sägs upp när en blivit klar; starten sägs redan av handlingens besked.
  const foljKlara = foljning ? foljning.alla.length - foljning.kvar.length : 0;
  useEffect(() => {
    if (foljtext && foljKlara > 0) setStatusbesked(foljtext);
  }, [foljtext, foljKlara]);
  const visaBesked = (b: Besked) => {
    setBesked(b);
    setStatusbesked(b.text);
  };

  /** En åtgärd i taget: knapparna låses och utfallet står kvar i rutan ovanför listan. */
  async function utfor(vad: Atgard, fn: () => Promise<Besked>) {
    if (atgard) return;
    setAtgard(vad);
    setBesked(null);
    try {
      visaBesked(await fn());
      setValda(new Set());
    } catch (e) {
      visaBesked({ text: text(feltext(e)), fel: true });
    } finally {
      setAtgard(null);
      setFramsteg(null);
    }
  }

  /** Godkänn och skicka eller Skicka nu, en i taget genom samma ändpunkt som ett enskilt klick. Stoppen grupperas per skäl. */
  async function sandIOrdning(poster: { qid: string; bolag: string }[], vag: "approve" | "skicka-nu") {
    let skickade = 0;
    let iKon = 0;
    const stopp = new Map<string, string[]>();
    setFramsteg({ klara: 0, totalt: poster.length });
    for (const [i, p] of poster.entries()) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const s = await irisAnrop<Sandutfall>(`/leads/queue/${encodeURIComponent(p.qid)}/${vag}`, { method: "POST" });
        if (s.utfall === "sent") skickade += 1;
        else if (s.utfall === "requeued") iKon += 1;
        else {
          const skal = skalUr(s) || s.besked || s.utfall || text({ sv: "Okänt skäl", en: "Unknown reason" });
          stopp.set(skal, [...(stopp.get(skal) ?? []), p.bolag]);
        }
      } catch (e) {
        const skal = text(feltext(e));
        stopp.set(skal, [...(stopp.get(skal) ?? []), p.bolag]);
      }
      setFramsteg({ klara: i + 1, totalt: poster.length });
    }
    klart();
    const antalStopp = [...stopp.values()].reduce((n, b) => n + b.length, 0);
    const delar: (Localized | null)[] = [
      { sv: `${skickade} skickade`, en: `${skickade} sent` },
      iKon === 1
        ? { sv: "1 skickas i tur och ordning från kön (vardagar från 08:00)", en: "1 goes out in turn from the queue (weekdays from 08:00)" }
        : iKon
          ? { sv: `${iKon} skickas i tur och ordning från kön (vardagar från 08:00)`, en: `${iKon} go out in turn from the queue (weekdays from 08:00)` }
          : null,
      antalStopp === 1 ? { sv: "1 skickades inte", en: "1 was not sent" } : antalStopp ? { sv: `${antalStopp} skickades inte`, en: `${antalStopp} were not sent` } : null
    ];
    return {
      text: `${delar.filter((d): d is Localized => d != null).map((d) => text(d)).join(", ")}.`,
      fel: antalStopp > 0,
      orsaker: [...stopp.entries()].map(([skal, bolag]) => `${bolag.length} · ${skal} (${namnlista(bolag, text)})`)
    };
  }

  const kopost = (id: string) => ko?.find((k) => k.id === id) ?? null;
  const schemalagd = (id: string) => skickat?.find((r) => r.id === id) ?? null;

  const godkannValda = (ids: string[]) =>
    void utfor("godkann", () =>
      sandIOrdning(
        ids.map(kopost).filter((k): k is Kopost => k != null).map((k) => ({ qid: k.id, bolag: k.company_name ?? k.prospect_email ?? "" })),
        "approve"
      )
    );
  const skickaNuValda = (ids: string[]) =>
    void utfor("skicka-nu", () =>
      sandIOrdning(
        ids.map(schemalagd).filter((r): r is SkickatRad => Boolean(r?.queue_item_id)).map((r) => ({ qid: r.queue_item_id as string, bolag: r.company_name ?? r.prospect_email ?? "" })),
        "skicka-nu"
      )
    );
  const avvisaValda = (ids: string[]) =>
    void utfor("avvisa", async () => {
      let avvisade = 0;
      const fel = new Map<string, string[]>();
      setFramsteg({ klara: 0, totalt: ids.length });
      for (const [i, id] of ids.entries()) {
        try {
          // eslint-disable-next-line no-await-in-loop
          await irisAnrop(`/leads/queue/${encodeURIComponent(id)}/reject`, { method: "POST" });
          avvisade += 1;
        } catch (e) {
          const skal = text(feltext(e));
          fel.set(skal, [...(fel.get(skal) ?? []), kopost(id)?.company_name ?? ""]);
        }
        setFramsteg({ klara: i + 1, totalt: ids.length });
      }
      klart();
      const ej = ids.length - avvisade;
      return {
        text:
          (avvisade === 1 ? text({ sv: "1 utkast avvisat och skickas aldrig.", en: "1 draft rejected and never sent." }) : text({ sv: `${avvisade} utkast avvisade och skickas aldrig.`, en: `${avvisade} drafts rejected and never sent.` })) +
          (ej ? ` ${text({ sv: `${ej} gick inte att avvisa.`, en: `${ej} could not be rejected.` })}` : ""),
        fel: ej > 0,
        orsaker: [...fel.entries()].map(([skal, bolag]) => `${bolag.length} · ${skal} (${namnlista(bolag, text)})`)
      };
    });
  const tillbakaValda = (ids: string[]) =>
    void utfor("tillbaka", async () => {
      const qids = ids.map(schemalagd).map((r) => r?.queue_item_id).filter((q): q is string => Boolean(q));
      const s = await irisAnrop<{ count?: number }>("/leads/queue/tillbaka-till-iris", { method: "POST", body: JSON.stringify({ ids: qids }) });
      klart();
      const n = s?.count ?? 0;
      return {
        text:
          n === 1
            ? text({ sv: "1 lead är tillbaka hos Iris. Markera det i Iris-listan och välj Skapa utkast när du vill ha ett nytt utkast.", en: "1 lead is back with Iris. Select it in the Iris list and choose Create draft when you want a new draft." })
            : text({ sv: `${n} leads är tillbaka hos Iris. Markera dem i Iris-listan och välj Skapa utkast när du vill ha nya utkast.`, en: `${n} leads are back with Iris. Select them in the Iris list and choose Create draft when you want new drafts.` }),
        fel: false
      };
    });
  const uppfoljningValda = (rader: SkickatRad[]) =>
    void utfor("uppfoljning", async () => {
      // En uppföljning per bolag, hur många mejl till bolaget som än är markerade.
      const pids = [...new Set(rader.map((r) => r.prospect_id).filter((p): p is string => Boolean(p)))];
      const s = await irisAnrop<{ count: number; hoppade?: Record<string, string[]> }>("/leads/uppfoljningar/skapa", { method: "POST", body: JSON.stringify({ prospect_ids: pids }) });
      klart();
      // De som inte hoppades över skrivs nu: de följs tills de står under Att granska.
      const hoppadeIds = new Set(Object.values(s.hoppade ?? {}).flat());
      const skrivs = pids.filter((p) => !hoppadeIds.has(p));
      if (s.count > 0 && skrivs.length) {
        const forr = foljning?.kvar ?? [];
        setFoljning({ alla: [...new Set([...(foljning?.alla ?? []), ...skrivs])], kvar: [...new Set([...forr, ...skrivs])] });
      }
      const hoppade = Object.entries(s.hoppade ?? {})
        .filter(([, ids]) => ids.length)
        .map(([skal, ids]) => `${ids.length} ${text(UPPFOLJNING_HOPPAD[skal] ?? { sv: skal, en: skal })}`)
        .join(", ");
      return {
        text:
          (s.count === 1
            ? text({ sv: "Iris skriver 1 uppföljning. Den står under Att granska när den är klar.", en: "Iris is writing 1 follow-up. It shows under To review when done." })
            : text({ sv: `Iris skriver ${s.count} uppföljningar. De står under Att granska när de är klara.`, en: `Iris is writing ${s.count} follow-ups. They show under To review when done.` })) +
          (hoppade ? ` ${text({ sv: "Hoppade över:", en: "Skipped:" })} ${hoppade}.` : ""),
        fel: false
      };
    });

  async function sparaTid() {
    if (!tidFor || atgard) return;
    const nar = tidFor.tid ? new Date(tidFor.tid) : null;
    if (!nar || Number.isNaN(nar.getTime())) {
      setTidFor((t) => (t ? { ...t, fel: text({ sv: "Välj en dag och en tid.", en: "Choose a day and a time." }) } : t));
      return;
    }
    const qids = tidFor.ids.map(schemalagd).map((r) => r?.queue_item_id).filter((q): q is string => Boolean(q));
    setAtgard("tid");
    try {
      const s = await irisAnrop<{ andrade?: number; skickas_tidigast?: string | null }>("/leads/queue/schemalagg", { method: "POST", body: JSON.stringify({ ids: qids, tid: nar.toISOString() }) });
      const n = s?.andrade ?? 0;
      const tid = s?.skickas_tidigast ? sandtid(s.skickas_tidigast, locale) : "";
      setTidFor(null);
      setValda(new Set());
      klart();
      visaBesked({
        text:
          (n === 1
            ? text({ sv: `1 mejl fick ny tid${tid ? `, skickas ${tid}` : ""}.`, en: `1 email got a new time${tid ? `, sends ${tid}` : ""}.` })
            : text({ sv: `${n} mejl fick ny tid${tid ? `, skickas ${tid}` : ""}.`, en: `${n} emails got a new time${tid ? `, sending ${tid}` : ""}.` })) +
          ` ${text({ sv: "Övriga skickas på sin vanliga tid.", en: "The others keep their usual time." })}`,
        fel: false
      });
    } catch (e) {
      // 422 (utanför 60 dagar eller bakåt i tiden) står vid fältet.
      setTidFor((t) => (t ? { ...t, fel: text(feltext(e)) } : t));
    } finally {
      setAtgard(null);
    }
  }

  // ---- Panelens handlingar på ett utkast --------------------------------------------------
  /** Lämnar raden listan efter ett beslut i panelen: panelen stängs, utfallet sägs, fokus går till grannraden. */
  function lamnaRad(id: string, b: Besked) {
    // Har panelen bytts till ett annat utkast medan beslutet gick igenom står den kvar: utfallet sägs ändå.
    const oppenNu = postIdRef.current === id;
    const fran = document.querySelector(`[data-utkast-rad="${CSS.escape(id)}"]`);
    const fokus = grannfokus(fran, "button.crm-chip");
    if (oppenNu) sattPost(null);
    visa({ body: b.text, uniqueID: "iris-utkast" });
    setStatusbesked(b.text);
    klart();
    if (oppenNu) fokus();
  }
  async function godkannEtt(k: Kopost): Promise<Besked | null> {
    const s = await irisAnrop<Sandutfall>(`/leads/queue/${encodeURIComponent(k.id)}/approve`, { method: "POST" });
    const mottagare = k.prospect_email ?? k.company_name ?? "";
    if (s.utfall === "sent") lamnaRad(k.id, { text: text({ sv: `Skickat till ${mottagare}.`, en: `Sent to ${mottagare}.` }), fel: false });
    else if (s.utfall === "requeued")
      lamnaRad(k.id, { text: text({ sv: `Godkänt. Mejlet till ${mottagare} skickas i tur och ordning från kön (vardagar från 08:00).`, en: `Approved. The email to ${mottagare} goes out in turn from the queue (weekdays from 08:00).` }), fel: false });
    else {
      // Stoppat av en sändspärr: utkastet står kvar, och skälet står i panelen.
      klart();
      const skal = skalUr(s);
      return { text: skal ? text({ sv: `Inte skickat: ${skal}`, en: `Not sent: ${skal}` }) : text({ sv: "Inte skickat.", en: "Not sent." }), fel: true };
    }
    return null;
  }
  async function avvisaEtt(k: Kopost): Promise<Besked | null> {
    await irisAnrop(`/leads/queue/${encodeURIComponent(k.id)}/reject`, { method: "POST" });
    lamnaRad(k.id, { text: text({ sv: `Utkastet till ${k.company_name ?? k.prospect_email ?? ""} är avvisat och skickas aldrig.`, en: `The draft to ${k.company_name ?? k.prospect_email ?? ""} is rejected and never sent.` }), fel: false });
    return null;
  }
  async function sparaEtt(k: Kopost, amne: string, brodtext: string) {
    await irisAnrop(`/leads/queue/${encodeURIComponent(k.id)}`, { method: "PUT", body: JSON.stringify({ subject: amne, brodtext }) });
    // Kön läser om: backenden rättar hälsning och signatur, och panelen visar det som sparats.
    await hamtaKo();
  }

  // ---- Kolumnerna -------------------------------------------------------------------------
  const kolumner = useMemo<TableColumn<Rad>[]>(() => {
    const bolag: TableColumn<Rad> = {
      key: "bolag",
      header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Kolumnrubrik>,
      width: proportional(1.2, { minWidth: 190 }),
      renderCell: (r) => (
        <span data-utkast-rad={r.id} className="flex min-w-0">
          <Postchip namn={r.bolag} onClick={() => sattPost(r.id)} label={text({ sv: `Öppna utkastet till ${r.bolag}`, en: `Open the draft to ${r.bolag}` })} />
        </span>
      )
    };
    const mottagare: TableColumn<Rad> = {
      key: "mottagare",
      header: <Kolumnrubrik ikon={AtSign}>{text({ sv: "Mottagare", en: "Recipient" })}</Kolumnrubrik>,
      width: proportional(0.9, { minWidth: 150 }),
      renderCell: (r) => <span className="block truncate text-[0.875rem] text-ink2">{r.mottagare ?? text({ sv: "Okänd mottagare", en: "Unknown recipient" })}</span>
    };
    const amne: TableColumn<Rad> = {
      key: "amne",
      header: <Kolumnrubrik ikon={Type}>{text({ sv: "Ämne", en: "Subject" })}</Kolumnrubrik>,
      width: proportional(1.4, { minWidth: 200 }),
      renderCell: (r) => (
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-[0.875rem] text-ink" title={r.amne ?? undefined}>
            {r.amne || text(UTAN_AMNE)}
          </span>
          {r.utdrag ? (
            <span className="truncate text-[0.8125rem] text-ink-muted" title={r.utdrag}>
              {vy === "skickat" ? text({ sv: `Svar: ${r.utdrag}`, en: `Reply: ${r.utdrag}` }) : r.utdrag}
            </span>
          ) : null}
        </span>
      )
    };
    const tid = (rubrik: Localized, ikon = Clock): TableColumn<Rad> => ({
      key: "tid",
      header: <Kolumnrubrik ikon={ikon}>{text(rubrik)}</Kolumnrubrik>,
      width: pixel(vy === "snart" ? 160 : 150),
      renderCell: (r) =>
        vy === "snart" ? (
          <span className="inline-flex items-center gap-1.5 text-[0.875rem] text-ink2">
            <Icon icon={Clock} size="xsm" color="inherit" />
            {r.tid ? text({ sv: `Skickas ${sandtid(r.tid, locale)}`, en: `Sends ${sandtid(r.tid, locale)}` }) : text({ sv: "Skickas snart", en: "Sending soon" })}
          </span>
        ) : r.tid ? (
          <Timestamp value={r.tid} format="relative" color="secondary" />
        ) : null
    });
    if (vy === "granska") return [bolag, mottagare, amne, tid({ sv: "Skrivet", en: "Written" })];
    if (vy === "snart") return [bolag, mottagare, amne, tid({ sv: "Skickas", en: "Sends" }, CalendarClock)];
    return [
      bolag,
      amne,
      mottagare,
      {
        key: "lage",
        header: <Kolumnrubrik ikon={Tag}>{text({ sv: "Läge", en: "Stage" })}</Kolumnrubrik>,
        width: pixel(150),
        renderCell: (r) =>
          r.skickat ? (
            <span className="inline-flex items-center gap-1.5 text-[0.875rem] text-ink2">
              <Prick ton={skickatton(r.skickat)} />
              {text(SKICKATLAGE[skickatlage(r.skickat)])}
            </span>
          ) : null
      },
      tid({ sv: "Skickat", en: "Sent" }, Send)
    ];
  }, [text, locale, vy, sattPost]);

  // ---- Vyerna och delarna -------------------------------------------------------------------
  const vynamn: Record<Vy, Localized> = {
    granska: { sv: "Att granska", en: "To review" },
    snart: { sv: "Skickas snart", en: "Sending soon" },
    skickat: { sv: "Skickat", en: "Sent" }
  };
  const vyantal = (v: Vy) => {
    const n = v === "granska" ? ko?.length : v === "snart" ? (skickat ? snart.length : undefined) : skickat ? skickade.length : undefined;
    return n == null ? undefined : tal(n);
  };
  const laddar = vy === "granska" ? ko === null : skickat === null;
  const vyFel = vy === "granska" ? koFel : skickatFel;

  const rensa = () => {
    setSok("");
    setLage("");
  };
  const tomt = filtrerar ? (
    <EmptyState
      icon={<Icon icon={SearchX} size="lg" color="secondary" />}
      title={vy === "skickat" ? text({ sv: "Inga skickade mejl i det här filtret", en: "No sent emails in this filter" }) : text({ sv: "Inget matchar sökningen", en: "Nothing matches the search" })}
      description={text({ sv: "Sökningen går på bolag, mottagare och ämne.", en: "The search covers company, recipient and subject." })}
      actions={<Button label={text({ sv: "Rensa filtret", en: "Clear the filter" })} variant="secondary" onClick={rensa} />}
    />
  ) : vy === "granska" ? (
    <EmptyState
      icon={<Icon icon={FilePen} size="lg" color="secondary" />}
      title={text({ sv: "Inga utkast väntar på dig", en: "No drafts are waiting for you" })}
      description={text({ sv: "När Iris skrivit ett mejl står det här tills du godkänt eller avvisat det.", en: "When Iris has written an email it waits here until you approve or reject it." })}
      actions={<Button label={text({ sv: "Till leads", en: "To leads" })} variant="secondary" href={`${bas}/iris/leads`} />}
    />
  ) : vy === "snart" ? (
    <EmptyState
      icon={<Icon icon={CalendarClock} size="lg" color="secondary" />}
      title={text({ sv: "Inget väntar på sändfönstret", en: "Nothing is waiting for the sending window" })}
      description={text({ sv: "Godkända mejl står här tills de går ut, vardagar 08 till 16.", en: "Approved emails stand here until they go out, weekdays 08 to 16." })}
    />
  ) : (
    <EmptyState icon={<Icon icon={Inbox} size="lg" color="secondary" />} title={text({ sv: "Inga mejl skickade än", en: "No emails sent yet" })} description={text({ sv: "Mejlen Iris skickar står här med leadets läge nu.", en: "The emails Iris sends stand here with the lead's current stage." })} />
  );

  // Under lg står nyckeltalen (LU-088) i räknefoten, där vyraden inte rymmer dem.
  const fot = (
    <div className="crm-raknefot">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span>{" "}
        <span className="crm-raknefot-tal">{urval.length ? `${tal(sidor.fran + 1)}–${tal(sidor.till)}` : "0"}</span>{" "}
        <span className="crm-raknefot-etikett">{text({ sv: "av", en: "of" })}</span> <span className="crm-raknefot-tal">{tal(urval.length)}</span>
      </span>
      {antal28 ? (
        <span className="inline-flex items-center gap-x-5 lg:hidden" title={text({ sv: "De senaste 28 dagarna", en: "The last 28 days" })}>
          <span>
            <span className="crm-raknefot-etikett">{text({ sv: "Skickat 28 d", en: "Sent 28 d" })}</span> <span className="crm-raknefot-tal">{tal(antal28.skickat)}</span>
          </span>
          <span>
            <span className="crm-raknefot-etikett">{text({ sv: "Svar", en: "Replies" })}</span> <span className="crm-raknefot-tal">{tal(antal28.svarat)}</span>
          </span>
        </span>
      ) : null}
      {sidor.antalSidor > 1 ? (
        <span className="ml-auto">
          <Pagination page={sidor.sida + 1} onChange={bytSida} totalItems={urval.length} pageSize={SIDSTORLEK} variant="compact" size="sm" label={text({ sv: "Sidor", en: "Pages" })} />
        </span>
      ) : null}
    </div>
  );

  // Skickat och svar de senaste 28 dagarna (LU-088), i räknefotens stil bredvid vyerna.
  const nyckeltal = antal28 ? (
    <span className="ml-3 hidden items-center gap-x-5 text-[0.8125rem] lg:inline-flex" title={text({ sv: "De senaste 28 dagarna", en: "The last 28 days" })}>
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Skickat 28 d", en: "Sent 28 d" })}</span> <span className="crm-raknefot-tal">{tal(antal28.skickat)}</span>
      </span>
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Svar", en: "Replies" })}</span> <span className="crm-raknefot-tal">{tal(antal28.svarat)}</span>
      </span>
    </span>
  ) : null;

  // ---- Åtgärdsraden ------------------------------------------------------------------------
  const av = { isDisabled: !skriv.far || atgard != null, tooltip: skriv.skal ?? undefined };
  const atgardsrad =
    (!smal || valjer) && (selectionState.hasSelection || atgard) ? (
      <div className="crm-atgardsrad-plats">
        <div className="crm-atgardsrad">
          {atgard && framsteg ? (
            <div className="flex min-w-[300px] items-center gap-3 px-2">
              <span className="whitespace-nowrap text-[0.875rem] font-semibold tabular-nums text-ink">
                {atgard === "avvisa"
                  ? text({ sv: `Avvisar ${framsteg.klara} av ${framsteg.totalt}`, en: `Rejecting ${framsteg.klara} of ${framsteg.totalt}` })
                  : text({ sv: `Skickar ${framsteg.klara} av ${framsteg.totalt}`, en: `Sending ${framsteg.klara} of ${framsteg.totalt}` })}
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
              label={text({ sv: "Åtgärder för markerade utkast", en: "Actions for selected drafts" })}
              renderSelectionLabel={(n) => <span className="tabular-nums">{n === 1 ? text({ sv: "1 markerat", en: "1 selected" }) : text({ sv: `${n} markerade`, en: `${n} selected` })}</span>}
              clearLabel={text({ sv: "Avmarkera", en: "Unselect" })}
              startContent={
                vy === "granska" ? (
                  <>
                    <Button label={text({ sv: "Godkänn och skicka", en: "Approve and send" })} variant="primary" size="md" icon={<Icon icon={Send} size="sm" />} isLoading={atgard === "godkann"} {...av} onClick={() => setBekraftas({ typ: "godkann", ids: valt.map((r) => r.id) })} />
                    <Button label={text({ sv: "Avvisa", en: "Reject" })} variant="ghost" size="md" icon={<Icon icon={X} size="sm" />} className="crm-farlig" isLoading={atgard === "avvisa"} {...av} onClick={() => setBekraftas({ typ: "avvisa", ids: valt.map((r) => r.id) })} />
                  </>
                ) : vy === "snart" ? (
                  <>
                    <Button label={text({ sv: "Skicka nu", en: "Send now" })} variant="primary" size="md" icon={<Icon icon={Send} size="sm" />} isLoading={atgard === "skicka-nu"} {...av} onClick={() => setBekraftas({ typ: "skicka-nu", ids: valt.map((r) => r.id) })} />
                    <Button label={text({ sv: "Ändra tid", en: "Change time" })} variant="ghost" size="md" icon={<Icon icon={CalendarClock} size="sm" />} isLoading={atgard === "tid"} {...av} onClick={() => setTidFor({ ids: valt.map((r) => r.id), tid: undefined, fel: null })} />
                    <Button label={text({ sv: "Tillbaka till Iris", en: "Back to Iris" })} variant="ghost" size="md" icon={<Icon icon={Undo2} size="sm" />} isLoading={atgard === "tillbaka"} {...av} onClick={() => setBekraftas({ typ: "tillbaka", ids: valt.map((r) => r.id) })} />
                  </>
                ) : (
                  <Button
                    label={(() => {
                      const n = new Set(valt.map((r) => r.skickat?.prospect_id)).size;
                      return n === 1 ? text({ sv: "Skapa uppföljning (1)", en: "Create follow-up (1)" }) : text({ sv: `Skapa uppföljning (${n})`, en: `Create follow-ups (${n})` });
                    })()}
                    variant="primary"
                    size="md"
                    icon={<Icon icon={FilePlus2} size="sm" />}
                    isLoading={atgard === "uppfoljning"}
                    {...av}
                    onClick={() => uppfoljningValda(valt.map((r) => r.skickat).filter((r): r is SkickatRad => r != null))}
                  />
                )
              }
            />
          )}
        </div>
      </div>
    ) : null;

  // ---- Bekräftelsen (LU-036, LU-085, LU-180) ---------------------------------------------------
  const bekr = (() => {
    if (!bekraftas) return null;
    const n = bekraftas.ids.length;
    if (bekraftas.typ === "godkann" || bekraftas.typ === "avvisa") {
      const poster = bekraftas.ids.map(kopost).filter((k): k is Kopost => k != null);
      const lista = poster.map((k) => ({ id: k.id, namn: k.company_name || k.prospect_email || "", under: k.prospect_email ?? null, amne: k.subject ?? null, utdrag: forstaMening(k.brodtext ?? k.body) }));
      return bekraftas.typ === "godkann"
        ? {
            titel: n === 1 ? text({ sv: "1 mejl godkänns och skickas till:", en: "1 email is approved and sent to:" }) : text({ sv: `${n} mejl godkänns och skickas till:`, en: `${n} emails are approved and sent to:` }),
            poster: lista,
            forklaring: text({ sv: "Varje mejl går genom sändspärrarna och skickas i tur och ordning från kön, ett i minuten, vardagar från 08:00.", en: "Every email passes the send guards and goes out in turn from the queue, one a minute, weekdays from 08:00." }),
            handling: n === 1 ? text({ sv: "Skicka 1 mejl", en: "Send 1 email" }) : text({ sv: `Skicka ${n} mejl`, en: `Send ${n} emails` }),
            farlig: false,
            bekrafta: () => {
              setBekraftas(null);
              godkannValda(bekraftas.ids);
            }
          }
        : {
            titel: n === 1 ? text({ sv: "1 utkast avvisas och skickas aldrig:", en: "1 draft is rejected and never sent:" }) : text({ sv: `${n} utkast avvisas och skickas aldrig:`, en: `${n} drafts are rejected and never sent:` }),
            poster: lista,
            forklaring: text({ sv: "Leadet står kvar hos Iris och kan få ett nytt utkast.", en: "The lead stays with Iris and can get a new draft." }),
            handling: n === 1 ? text({ sv: "Avvisa 1 utkast", en: "Reject 1 draft" }) : text({ sv: `Avvisa ${n} utkast`, en: `Reject ${n} drafts` }),
            farlig: true,
            bekrafta: () => {
              setBekraftas(null);
              avvisaValda(bekraftas.ids);
            }
          };
    }
    const rader = bekraftas.ids.map(schemalagd).filter((r): r is SkickatRad => r != null);
    const lista = rader.map((r) => ({ id: r.id, namn: r.company_name || r.prospect_email || "", under: r.prospect_email, amne: r.subject }));
    return bekraftas.typ === "skicka-nu"
      ? {
          titel: n === 1 ? text({ sv: "1 mejl skickas nu till:", en: "1 email is sent now to:" }) : text({ sv: `${n} mejl skickas nu till:`, en: `${n} emails are sent now to:` }),
          poster: lista,
          forklaring: text({ sv: "De går ut direkt, även utanför sändfönstret. Sändspärrarna gäller som vanligt. Övriga schemalagda skickas på sin vanliga tid.", en: "They go out right away, even outside the sending window. The send guards apply as usual. Other scheduled emails keep their usual time." }),
          handling: n === 1 ? text({ sv: "Skicka 1 mejl nu", en: "Send 1 email now" }) : text({ sv: `Skicka ${n} mejl nu`, en: `Send ${n} emails now` }),
          farlig: false,
          bekrafta: () => {
            setBekraftas(null);
            skickaNuValda(bekraftas.ids);
          }
        }
      : {
          titel: n === 1 ? text({ sv: "1 utkast flyttas tillbaka till Iris:", en: "1 draft is moved back to Iris:" }) : text({ sv: `${n} utkast flyttas tillbaka till Iris:`, en: `${n} drafts are moved back to Iris:` }),
          poster: lista,
          forklaring: text({ sv: "De skickas inte. Inget skrivs om förrän du väljer det i Iris-listan.", en: "They are not sent. Nothing is rewritten until you choose that in the Iris list." }),
          handling: text({ sv: "Flytta tillbaka", en: "Move back" }),
          farlig: false,
          bekrafta: () => {
            setBekraftas(null);
            tillbakaValda(bekraftas.ids);
          }
        };
  })();

  // ---- Den öppna posten ----------------------------------------------------------------------
  const oppen: Utkastpost | null = (() => {
    if (!postId) return null;
    const k = ko?.find((x) => x.id === postId);
    if (k) return { slag: "granska", ko: k };
    const r = skickat?.find((x) => x.id === postId);
    if (r) return { slag: r.schemalagt ? "snart" : "skickat", rad: r };
    return null;
  })();

  return (
    <Sida
      objekt="utkast"
      rubrik={text({ sv: "Utkast", en: "Drafts" })}
      vyrad={
        smal ? (
          <Selector
            label={text({ sv: "Vy", en: "View" })}
            isLabelHidden
            variant="secondary"
            size="md"
            value={vy}
            onChange={(v) => v && setVy(v as Vy)}
            options={VYER.map((v) => ({ value: v, label: vyantal(v) ? `${text(vynamn[v])}  ${vyantal(v)}` : text(vynamn[v]) }))}
          />
        ) : (
          <>
            <Vyval value={vy} onChange={setVy} label={text({ sv: "Vy", en: "View" })} val={VYER.map((v) => ({ v, namn: text(vynamn[v]), antal: vyantal(v) }))} />
            {nyckeltal}
          </>
        )
      }
      vyradHoger={
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
          <div className="w-full min-w-0 sm:w-[220px] sm:flex-none">
            <TextInput
              type="search"
              label={text({ sv: "Sök utkast", en: "Search drafts" })}
              isLabelHidden
              placeholder={text({ sv: "Bolag, mottagare eller ämne", en: "Company, recipient or subject" })}
              startIcon="search"
              hasClear
              value={sok}
              onChange={(v) => setSok(v)}
              width="100%"
              controlClassName="crm-sokfalt"
            />
          </div>
          {vy === "skickat" ? (
            <Selector
              label={text({ sv: "Läge", en: "Stage" })}
              isLabelHidden
              variant={lage ? "secondary" : "ghost"}
              size="md"
              startIcon={Tag}
              value={lage || "alla"}
              onChange={(v) => setLage(v === "alla" || !v ? "" : (v as Skickatlage))}
              options={[
                { value: "alla", label: text({ sv: "Alla lägen", en: "All stages" }) },
                ...LAGEN.map((l) => ({ value: l, label: `${text(SKICKATLAGE[l])}  ${tal(lageAntal[l])}` }))
              ]}
            />
          ) : null}
          {smal && markerbara.length > 0 ? (
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
        </div>
      }
    >
      <div className="crm-bolag" ref={listref}>
        {/* Utfallen sägs upp här, i en region som finns hela tiden. */}
        <div role="status" className="sr-only">
          {statusbesked}
        </div>
        {besked ? (
          <div className="px-4 pt-3 sm:px-6">
            <Banner
              status={besked.fel ? "error" : "success"}
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
        {/* Förloppet för Skapa uppföljning, där handlingen startades, tills uppföljningarna står under Att granska. */}
        {foljning ? (
          <div className="px-4 pt-3 sm:px-6">
            <span className="inline-flex items-center gap-2 text-[0.875rem] text-ink2">
              <Prick ton="ockra" pulserar />
              {foljtext}
            </span>
          </div>
        ) : null}
        {vy === "snart" && snart.length > 0 ? (
          <p className="px-4 pb-1 pt-3 text-[0.875rem] text-ink-muted sm:px-6">
            {text({ sv: "Godkända mejl går ut ett i taget, ungefär ett i minuten, vardagar 08 till 16. Tiden är en uppskattning: en spärr eller ett svar däremellan flyttar resten.", en: "Approved emails go out one at a time, about one a minute, weekdays 08 to 16. The time is an estimate: a block or a reply in between moves the rest." })}
          </p>
        ) : null}

        {vyFel ? (
          <div className="p-4 sm:p-6">
            <Felruta fel={vyFel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => (vy === "granska" ? void hamtaKo() : void hamtaSkickat())} />} />
          </div>
        ) : laddar ? (
          <Tabellskelett rader={8} kolumner={smal ? 2 : 4} markering={!smal} label={text({ sv: "Hämtar utkasten", en: "Loading the drafts" })} />
        ) : smal ? (
          urval.length === 0 ? (
            <>
              <div className="py-10">{tomt}</div>
              {antal28 ? fot : null}
            </>
          ) : (
            <>
              <div className="px-2">
                <List hasDividers density="balanced" edge="padded">
                  {sidansRader.map((r) => {
                    const markerbar = markerbara.some((m) => m.id === r.id);
                    const vald = valda.has(r.id);
                    const vaxla = (pa: boolean) =>
                      setValda((forr) => {
                        const ny = new Set(forr);
                        if (pa) ny.add(r.id);
                        else ny.delete(r.id);
                        return ny;
                      });
                    const hoger =
                      vy === "snart" ? (r.tid ? sandtid(r.tid, locale) : text({ sv: "Snart", en: "Soon" })) : vy === "skickat" && r.skickat ? text(SKICKATLAGE[skickatlage(r.skickat)]) : null;
                    return (
                      <ListItem
                        key={r.id}
                        label={<span className="font-semibold text-ink">{r.bolag}</span>}
                        description={[r.amne || text(UTAN_AMNE), r.mottagare].filter(Boolean).join(" · ")}
                        startContent={
                          valjer && markerbar ? (
                            <span className="-my-1 inline-flex size-11 items-center justify-center" onClick={(e) => e.stopPropagation()}>
                              <CheckboxInput label={text({ sv: `Markera ${r.bolag}`, en: `Select ${r.bolag}` })} isLabelHidden value={vald} onChange={vaxla} />
                            </span>
                          ) : (
                            <span aria-hidden className="inline-flex">
                              <Avatar name={utanBolagsform(r.bolag)} size={32} shape="rounded" tooltip={false} className={`crm-avatar ${tonklass(tonFor(utanBolagsform(r.bolag)))}`} />
                            </span>
                          )
                        }
                        endContent={
                          hoger ? (
                            <span className="inline-flex max-w-[8rem] items-center gap-1.5 text-right text-[0.75rem] text-ink-muted">
                              {vy === "skickat" && r.skickat ? <Prick ton={skickatton(r.skickat)} /> : null}
                              <span className="truncate">{hoger}</span>
                            </span>
                          ) : r.tid ? (
                            <Timestamp value={r.tid} format="relative" color="secondary" />
                          ) : undefined
                        }
                        onClick={() => (valjer && markerbar ? vaxla(!vald) : sattPost(r.id))}
                        isSelected={valjer ? false : postId === r.id}
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
            <Table<Rad>
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
            {urval.length > 0 ? fot : antal28 ? <div className="lg:hidden">{fot}</div> : null}
          </div>
        )}

        {atgardsrad}
      </div>

      <UtkastPanel
        post={oppen}
        signatur={signatur}
        offer={offer}
        bas={bas}
        skriv={skriv}
        stang={() => sattPost(null)}
        spara={sparaEtt}
        godkann={godkannEtt}
        avvisa={avvisaEtt}
        skickaNu={(r) => setBekraftas({ typ: "skicka-nu", ids: [r.id] })}
        andraTid={(r) => setTidFor({ ids: [r.id], tid: undefined, fel: null })}
        tillbaka={(r) => setBekraftas({ typ: "tillbaka", ids: [r.id] })}
        uppfoljning={(r) => uppfoljningValda([r])}
      />

      {bekr ? (
        <Bekraftelse
          oppen
          titel={bekr.titel}
          poster={bekr.poster}
          forklaring={bekr.forklaring}
          handling={bekr.handling}
          farlig={bekr.farlig}
          upptagen={atgard != null}
          bekrafta={bekr.bekrafta}
          stang={() => setBekraftas(null)}
        />
      ) : null}

      {/* Ändra tid (LU-067, LU-085): ny tid för de markerade, inom 60 dagar. Felet från backenden står vid fältet. */}
      <Dialog isOpen={tidFor != null} onOpenChange={(o) => !o && atgard !== "tid" && setTidFor(null)} purpose="form" width={480}>
        <Layout
          header={
            <DialogHeader
              title={tidFor?.ids.length === 1 ? text({ sv: "Ny tid för 1 mejl", en: "New time for 1 email" }) : text({ sv: `Ny tid för ${tidFor?.ids.length ?? 0} mejl`, en: `New time for ${tidFor?.ids.length ?? 0} emails` })}
              onOpenChange={(o) => !o && atgard !== "tid" && setTidFor(null)}
            />
          }
          content={
            <LayoutContent>
              <form
                id="iris-andra-tid"
                noValidate
                onSubmit={(e) => {
                  e.preventDefault();
                  void sparaTid();
                }}
                className="flex flex-col gap-3"
              >
                <DateTimeInput
                  label={text({ sv: "Skickas tidigast", en: "Sends at the earliest" })}
                  value={tidFor?.tid}
                  onChange={(v) => setTidFor((t) => (t ? { ...t, tid: v, fel: null } : t))}
                  hourFormat="24h"
                  timeIncrement={15}
                  width="100%"
                  status={tidFor?.fel ? { type: "error", message: tidFor.fel } : undefined}
                />
                <Text type="supporting" color="secondary">
                  {text({ sv: "Gäller bara de markerade, inom 60 dagar. Övriga skickas på sin vanliga tid. En tid utanför sändfönstret (vardagar 08 till 16) går ut när fönstret öppnar.", en: "Applies only to the selected, within 60 days. The others keep their usual time. A time outside the sending window (weekdays 08 to 16) goes out when the window opens." })}
                </Text>
              </form>
            </LayoutContent>
          }
          footer={
            <LayoutFooter>
              <HStack justify="end" gap={2}>
                <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" isDisabled={atgard === "tid"} onClick={() => setTidFor(null)} />
                <Button type="submit" form="iris-andra-tid" variant="primary" label={text({ sv: "Spara ny tid", en: "Save new time" })} isLoading={atgard === "tid"} isDisabled={!skriv.far} tooltip={skriv.skal ?? undefined} />
              </HStack>
            </LayoutFooter>
          }
        />
      </Dialog>
    </Sida>
  );
}
