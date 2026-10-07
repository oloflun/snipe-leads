"use client";

import {
  ArrowRight,
  CheckCircle2,
  Inbox,
  PenLine,
  Receipt,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import {
  Fordelningsstaplar,
  KpiKort,
  Munkdiagram,
  type Andel,
  type Kpi,
  type Stapel,
} from "@/components/dashboard/OversiktPaneler";
import { SmalKolumn } from "@/components/leads/smal";
import type { Kvitto } from "@/components/kvitton/KvittoYta";
import { Dashboard } from "@/components/snajp/Dashboard";
import { btnLiten, btnSecondary, meta } from "@/components/ui";
import { demoKvitton } from "@/lib/demo/kvitto-oversikt";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Att göra — det som väntar på ett beslut från dig, i viktordning (plan
 * 2026-10-05, fas 5), i översikternas layout sedan 2026-10-07 (Sebbes
 * beställning: samma kort, ringar och kolumner som Leads, Kundtjänst och
 * Kvitton, anpassat för en kö).
 *
 *   nyckeltal: väntar totalt (med det äldsta) och per agent
 *   vad som väntar (munk) · hur länge det väntat (åldershinkar)
 *   eskalerat | svar att godkänna      (köerna i kolumner)
 *   larm | leads (svar och utkast) | kvitton att granska
 *
 * Kundtjänstens köer är Dashboard i köläge, som förut: fem rader var, resten
 * bakom "Visa alla", likadana larm som en rad med räknare. De står i en smal
 * kolumn (SmalKolumn), så ett öppnat ärende fälls ut under listan. Antal och
 * ålder kommer ur samma rader via onAntal, ingen extra hämtning.
 *
 * Leadsinkorgen och Iris utkast bor under Leads; här står hur många som
 * väntar och sedan när, med en länk dit. Kvitton att granska räknas med samma
 * regel som Kvitton › Översikt (status inte "klar").
 */

const TAK = 5;
const TIMME = 3_600_000;
const DYGN = 24 * TIMME;

type Ko = "eskalerade" | "vantar" | "larm" | "leadsvar" | "utkast" | "kvitton";

/** Antal och ankomsttider per kö. null = inte hämtat än (eller ej tillgängligt). */
type Lage = Record<Ko, { antal: number; tider: number[] } | null>;

type KvittoRad = Pick<
  Kvitto,
  | "id"
  | "datum"
  | "motpart"
  | "brutto"
  | "valuta"
  | "status"
  | "kategorietikett"
  | "filnamn"
>;

const T = {
  vantarTotalt: { sv: "Väntar på dig", en: "Waiting for you" },
  allaHanterat: { sv: "allt är hanterat", en: "everything is handled" },
  aldst: { sv: "äldst", en: "oldest" },
  kundtjanst: { sv: "Kundtjänst", en: "Customer service" },
  leads: { sv: "Leads", en: "Leads" },
  kvitton: { sv: "Kvitton", en: "Receipts" },
  attGranska: { sv: "att granska i Kvitton", en: "to review in Receipts" },
  fordelning: { sv: "Vad som väntar", en: "What is waiting" },
  fordelningEtikett: { sv: "Per kö", en: "Per queue" },
  vantarMitt: { sv: "väntar", en: "waiting" },
  alder: { sv: "Hur länge det väntat", en: "How long it has waited" },
  alderText: {
    sv: "Ärenden, svar och utkast efter tid sedan de kom in.",
    en: "Cases, replies and drafts by time since they arrived.",
  },
  alderKvitton: {
    sv: "Kvitton bär kvittots datum, inte ankomsten, och räknas inte här.",
    en: "Receipts carry the receipt date, not the arrival, and are not counted here.",
  },
  ingetMedTid: {
    sv: "Inget med en ankomsttid väntar.",
    en: "Nothing with an arrival time is waiting.",
  },
  tomtRubrik: { sv: "Inget väntar på dig", en: "Nothing is waiting for you" },
  tomtText: {
    sv: "Agenterna sköter resten. Nya beslut dyker upp här när de behöver ditt ja.",
    en: "The agents handle the rest. New decisions show up here when they need your yes.",
  },
  eskalerat: { sv: "Eskalerat till dig", en: "Escalated to you" },
  eskaleratText: {
    sv: "Ärenden agenten lämnat över till en människa.",
    en: "Cases the agent handed over to a human.",
  },
  svarAttGodkanna: { sv: "Svar att godkänna", en: "Replies to approve" },
  svarText: {
    sv: "Agentens svar som väntar på ditt ja innan de skickas.",
    en: "The agent's replies waiting for your yes before they are sent.",
  },
  larm: { sv: "Larm", en: "Alerts" },
  larmText: {
    sv: "Avvisade utskick och systemfel. Likadana larm står som en rad.",
    en: "Rejected sends and system errors. Identical alerts show as one row.",
  },
  leadsText: {
    sv: "Svar från dina leads och Iris utkast. Båda hanteras under Leads.",
    en: "Replies from your leads and Iris drafts. Both are handled under Leads.",
  },
  svarFranLeads: { sv: "Svar från leads", en: "Replies from leads" },
  leadsutkast: { sv: "Utkast att godkänna", en: "Drafts to approve" },
  oppnaInkorgen: { sv: "Öppna inkorgen", en: "Open the inbox" },
  oppnaUtkasten: { sv: "Öppna utkasten", en: "Open the drafts" },
  kvittonText: {
    sv: "Underlag Kvittohanteraren vill att du tittar på.",
    en: "Documents the receipt manager wants you to look at.",
  },
  ingaKvitton: {
    sv: "Inga kvitton väntar på granskning.",
    en: "No receipts are waiting for review.",
  },
  oppnaKvitton: { sv: "Öppna Kvitton", en: "Open Receipts" },
  ingetVantar: { sv: "Inget väntar.", en: "Nothing is waiting." },
  sedan: { sv: "senast", en: "latest" },
  ingenAtkomst: {
    sv: "Gick inte att hämta just nu.",
    en: "Could not be loaded right now.",
  },
} satisfies Record<string, Localized>;

const KOER: { id: Ko; etikett: Localized; farg: string }[] = [
  {
    id: "eskalerade",
    etikett: { sv: "Eskalerade ärenden", en: "Escalated cases" },
    farg: "oklch(var(--danger))",
  },
  {
    id: "vantar",
    etikett: { sv: "Svar att godkänna", en: "Replies to approve" },
    farg: "oklch(var(--chart-ochre))",
  },
  {
    id: "larm",
    etikett: { sv: "Larm", en: "Alerts" },
    farg: "oklch(var(--ink))",
  },
  {
    id: "leadsvar",
    etikett: { sv: "Svar från leads", en: "Replies from leads" },
    farg: "oklch(var(--chart-blue))",
  },
  {
    id: "utkast",
    etikett: { sv: "Leadsutkast", en: "Lead drafts" },
    farg: "oklch(var(--chart-ramp-6))",
  },
  {
    id: "kvitton",
    etikett: { sv: "Kvitton att granska", en: "Receipts to review" },
    farg: "oklch(var(--chart-ramp-2))",
  },
];

/** Åldershinkarna: färgen går från lugn till brådskande, och etiketten bär alltid budskapet. */
const HINKAR: { id: string; etikett: Localized; tak: number; farg: string }[] =
  [
    {
      id: "timme",
      etikett: { sv: "Under en timme", en: "Under an hour" },
      tak: TIMME,
      farg: "oklch(var(--chart-ramp-6))",
    },
    {
      id: "dygn",
      etikett: { sv: "1–24 timmar", en: "1–24 hours" },
      tak: DYGN,
      farg: "oklch(var(--chart-ramp-3))",
    },
    {
      id: "tre",
      etikett: { sv: "1–3 dygn", en: "1–3 days" },
      tak: 3 * DYGN,
      farg: "oklch(var(--chart-ochre))",
    },
    {
      id: "mer",
      etikett: { sv: "Mer än 3 dygn", en: "More than 3 days" },
      tak: Infinity,
      farg: "oklch(var(--danger))",
    },
  ];

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";
const rubrik = "text-[1rem] font-semibold";

function tid(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? null : t;
}

function sedan(t: number, locale: "sv" | "en"): string {
  const minuter = Math.max(1, Math.round((Date.now() - t) / 60_000));
  const rtf = new Intl.RelativeTimeFormat(locale === "en" ? "en-GB" : "sv-SE", {
    numeric: "auto",
  });
  if (minuter < 60) return rtf.format(-minuter, "minute");
  if (minuter < 1440) return rtf.format(-Math.round(minuter / 60), "hour");
  return rtf.format(-Math.round(minuter / 1440), "day");
}

function idagLokalt(forskjutning = 0): string {
  const d = new Date(Date.now() + forskjutning);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function belopp(k: KvittoRad, locale: "sv" | "en"): string {
  const n = Number(k.brutto);
  if (!k.brutto || Number.isNaN(n))
    return locale === "en" ? "No amount" : "Belopp saknas";
  return `${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)} ${k.valuta || "SEK"}`;
}

/** Leads- och kvittodelen räknas här, inte genom att rendera listorna: de bor på sina sidor. */
function useOvrigaKoer(demo: boolean, iris: boolean, kvitton: boolean) {
  const [lage, setLage] = useState<
    Pick<Lage, "leadsvar" | "utkast" | "kvitton">
  >({ leadsvar: null, utkast: null, kvitton: null });
  const [kvittorader, setKvittorader] = useState<KvittoRad[] | null>(null);
  // Hämtningen är klar (lyckad eller inte). En kö som är null efter det gick inte att hämta.
  const [klar, setKlar] = useState(false);

  const ladda = useCallback(async () => {
    type Svar = {
      emails?: { received_at?: string; hanterad_at?: string | null }[];
    };
    type Utkast = { items?: { created_at?: string; scheduled_at?: string }[] };
    if (demo) {
      // Samma fixturer som demons Leads och Kvitton (lib/demo/oversikt.ts,
      // lib/demo/kvitto-oversikt.ts), så att antalen motsvarar de sidorna.
      const svar = demoOversiktSvar("/leads/svar") as
        { replies?: { sent_at?: string; status?: string }[] } | undefined;
      const ko = demoOversiktSvar("/leads/queue") as Utkast | undefined;
      const obesvarade = (svar?.replies ?? []).filter(
        (r) => r.status === "replied" || r.status === "meeting",
      );
      const granska = demoKvitton().filter((k) => k.status !== "klar");
      setLage({
        leadsvar: iris
          ? {
              antal: obesvarade.length,
              tider: obesvarade
                .map((r) => tid(r.sent_at))
                .filter((t): t is number => t !== null),
            }
          : null,
        utkast: iris
          ? {
              antal: ko?.items?.length ?? 0,
              tider: (ko?.items ?? [])
                .map((i) => tid(i.created_at ?? i.scheduled_at))
                .filter((t): t is number => t !== null),
            }
          : null,
        kvitton: kvitton ? { antal: granska.length, tider: [] } : null,
      });
      setKvittorader(kvitton ? granska : []);
      setKlar(true);
      return;
    }
    const hamta = async <R,>(path: string): Promise<R | null> => {
      try {
        const response = await fetch(`/api/snajp-support${path}`, {
          cache: "no-store",
        });
        if (!response.ok) return null;
        return await readJsonBody<R>(response);
      } catch {
        return null;
      }
    };
    const [svar, ko, kv] = await Promise.all([
      iris ? hamta<Svar>("/inbox?klass=lead&limit=200") : Promise.resolve(null),
      iris ? hamta<Utkast>("/leads/queue") : Promise.resolve(null),
      // Ett år bakåt: ett kvitto att granska äldre än så är inte längre ett beslut som väntar.
      kvitton
        ? hamta<{ kvitton?: KvittoRad[] }>(
            `/kvitton?fran=${idagLokalt(-365 * DYGN)}&till=${idagLokalt()}`,
          )
        : Promise.resolve(null),
    ]);
    const ohanterade = (svar?.emails ?? []).filter((e) => !e.hanterad_at);
    const granska = (kv?.kvitton ?? []).filter((k) => k.status !== "klar");
    setLage({
      leadsvar: svar
        ? {
            antal: ohanterade.length,
            tider: ohanterade
              .map((e) => tid(e.received_at))
              .filter((t): t is number => t !== null),
          }
        : null,
      utkast: ko
        ? {
            antal: (ko.items ?? []).length,
            tider: (ko.items ?? [])
              .map((i) => tid(i.created_at ?? i.scheduled_at))
              .filter((t): t is number => t !== null),
          }
        : null,
      kvitton: kv ? { antal: granska.length, tider: [] } : null,
    });
    setKvittorader(kv ? granska : null);
    setKlar(true);
  }, [demo, iris, kvitton]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  return { lage, kvittorader, klar };
}

export function AttGora({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { products } = useDashboard();
  const { text, locale } = useLocale();
  const vag = useArbetsvag();
  const iris = products.includes("leads");
  const support = products.includes("support");
  const harKvitton = products.includes("bookkeeping");
  const [supportKo, setSupportKo] = useState<
    Pick<Lage, "eskalerade" | "vantar" | "larm">
  >({ eskalerade: null, vantar: null, larm: null });
  const {
    lage: ovriga,
    kvittorader,
    klar: ovrigaKlara,
  } = useOvrigaKoer(demo, iris, harKvitton);

  const fran =
    (ko: "eskalerade" | "vantar" | "larm") =>
    (antal: number, rader: { received_at: string }[]) =>
      setSupportKo((s) => ({
        ...s,
        [ko]: {
          antal,
          tider: rader
            .map((r) => tid(r.received_at))
            .filter((t): t is number => t !== null),
        },
      }));

  const lage: Lage = { ...supportKo, ...ovriga };
  const aktuella = KOER.filter((k) =>
    k.id === "eskalerade" || k.id === "vantar" || k.id === "larm"
      ? support
      : k.id === "kvitton"
        ? harKvitton
        : iris,
  );
  // Kundtjänstens köer svarar via onAntal efter sin första hämtning; övriga
  // köer är klara när deras hämtning är det, även om en av dem misslyckades.
  const laddat = aktuella.every((k) =>
    ["eskalerade", "vantar", "larm"].includes(k.id)
      ? lage[k.id] !== null
      : ovrigaKlara,
  );
  const total = aktuella.reduce((s, k) => s + (lage[k.id]?.antal ?? 0), 0);
  const tider = aktuella.flatMap((k) => lage[k.id]?.tider ?? []);
  const aldsta = tider.length ? Math.min(...tider) : null;
  const antal = (ko: Ko) => lage[ko]?.antal ?? null;
  const summa = (...koer: Ko[]) =>
    koer.every((k) => lage[k] !== null)
      ? koer.reduce((s, k) => s + (lage[k]?.antal ?? 0), 0)
      : null;

  // -- Nyckeltalen ------------------------------------------------------------
  const kpier: Kpi[] = [
    {
      id: "totalt",
      etikett: T.vantarTotalt,
      varde: laddat ? total : null,
      larm: total > 0,
      detalj:
        laddat && total === 0
          ? T.allaHanterat
          : aldsta !== null
            ? {
                sv: `${T.aldst.sv} ${sedan(aldsta, "sv")}`,
                en: `${T.aldst.en} ${sedan(aldsta, "en")}`,
              }
            : {
                sv: "beslut som väntar på ditt ja",
                en: "decisions waiting for your yes",
              },
    },
    ...(support
      ? [
          {
            id: "kundtjanst",
            etikett: T.kundtjanst,
            varde: summa("eskalerade", "vantar", "larm"),
            larm: (antal("eskalerade") ?? 0) > 0,
            href: "#kundtjanst-eskalerat",
            detalj: {
              sv: `${antal("eskalerade") ?? "…"} eskalerade · ${antal("vantar") ?? "…"} svar · ${antal("larm") ?? "…"} larm`,
              en: `${antal("eskalerade") ?? "…"} escalated · ${antal("vantar") ?? "…"} replies · ${antal("larm") ?? "…"} alerts`,
            },
          } satisfies Kpi,
        ]
      : []),
    ...(iris
      ? [
          {
            id: "leads",
            etikett: T.leads,
            varde: summa("leadsvar", "utkast"),
            href: "#leads",
            detalj: {
              sv: `${antal("leadsvar") ?? "…"} svar från leads · ${antal("utkast") ?? "…"} utkast`,
              en: `${antal("leadsvar") ?? "…"} replies from leads · ${antal("utkast") ?? "…"} drafts`,
            },
          } satisfies Kpi,
        ]
      : []),
    ...(harKvitton
      ? [
          {
            id: "kvitton",
            etikett: T.kvitton,
            varde: antal("kvitton"),
            href: "#kvitton",
            detalj: T.attGranska,
          } satisfies Kpi,
        ]
      : []),
  ];

  const delar: Andel[] = aktuella.map((k) => ({
    id: k.id,
    etikett: k.etikett,
    antal: lage[k.id]?.antal ?? 0,
    farg: k.farg,
  }));
  const nu = Date.now();
  const staplar: Stapel[] = HINKAR.map((h, i) => ({
    id: h.id,
    etikett: h.etikett,
    farg: h.farg,
    antal: tider.filter((t) => {
      const alder = Math.max(0, nu - t);
      return alder < h.tak && (i === 0 || alder >= HINKAR[i - 1].tak);
    }).length,
  }));

  const kolumner =
    kpier.length >= 4
      ? "xl:grid-cols-4"
      : kpier.length === 3
        ? "xl:grid-cols-3"
        : "xl:grid-cols-2";

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <div className={cn("grid grid-cols-1 gap-4 sm:grid-cols-2", kolumner)}>
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={{ sv: "", en: "" }} />
        ))}
      </div>

      {laddat && total === 0 ? (
        <section
          className={cn(kort, "flex items-center gap-4")}
          aria-live="polite"
        >
          <CheckCircle2 className="h-8 w-8 shrink-0 text-moss" aria-hidden />
          <div>
            <h2 className={rubrik}>{text(T.tomtRubrik)}</h2>
            <p className={cn(meta, "mt-0.5")}>{text(T.tomtText)}</p>
          </div>
        </section>
      ) : (
        <div className="grid min-w-0 gap-4 lg:grid-cols-12">
          <section
            aria-labelledby="attgora-fordelning"
            className={cn(kort, "min-w-0 lg:col-span-5")}
          >
            <h2 id="attgora-fordelning" className={cn(rubrik, "mb-4")}>
              {text(T.fordelning)}
            </h2>
            {laddat ? (
              <Munkdiagram
                delar={delar}
                etikett={T.fordelningEtikett}
                mitt={T.vantarMitt}
              />
            ) : (
              <div
                className="h-28 animate-pulse rounded-input bg-ink/[0.05]"
                aria-hidden
              />
            )}
          </section>
          <section
            aria-labelledby="attgora-alder"
            className={cn(kort, "min-w-0 lg:col-span-7")}
          >
            <h2 id="attgora-alder" className={rubrik}>
              {text(T.alder)}
            </h2>
            <p className={cn(meta, "mb-4 mt-1 max-w-[70ch]")}>
              {text(T.alderText)}
              {harKvitton ? ` ${text(T.alderKvitton)}` : null}
            </p>
            {!laddat ? (
              <div
                className="h-28 animate-pulse rounded-input bg-ink/[0.05]"
                aria-hidden
              />
            ) : tider.length === 0 ? (
              <p className={meta}>{text(T.ingetMedTid)}</p>
            ) : (
              <Fordelningsstaplar staplar={staplar} />
            )}
          </section>
        </div>
      )}

      <SmalKolumn value>
        {/* Två staplar per agent i stället för ett rutnät: köerna har olika
            höjd, och ett rutnät lämnade hål under den kortaste. Kundtjänstens
            köer till vänster, Leads och Kvitton till höger. */}
        <div
          className={cn(
            "grid min-w-0 items-start gap-4",
            support && (iris || harKvitton) && "xl:grid-cols-2",
          )}
        >
          {support ? (
            <div className="flex min-w-0 flex-col gap-4">
              {support ? (
                <Ruta
                  id="kundtjanst-eskalerat"
                  rubrik={T.eskalerat}
                  text={T.eskaleratText}
                  antal={antal("eskalerade")}
                  larm
                >
                  <Dashboard
                    lager="eskalerade"
                    demo={demo}
                    tak={TAK}
                    onAntal={fran("eskalerade")}
                  />
                </Ruta>
              ) : null}
              {support ? (
                <Ruta
                  id="kundtjanst-utkast"
                  rubrik={T.svarAttGodkanna}
                  text={T.svarText}
                  antal={antal("vantar")}
                >
                  <Dashboard
                    lager="vantar"
                    demo={demo}
                    tak={TAK}
                    onAntal={fran("vantar")}
                  />
                </Ruta>
              ) : null}
              {/* Larmen (migration 078): avvisade utskick, systemfel. Skilda från
              eskaleringarna, som är kundärenden agenten lämnat över. */}
              {support ? (
                <Ruta
                  id="kundtjanst-larm"
                  rubrik={T.larm}
                  text={T.larmText}
                  antal={antal("larm")}
                >
                  <Dashboard
                    lager="att_hantera"
                    demo={demo}
                    tak={TAK}
                    onAntal={fran("larm")}
                  />
                </Ruta>
              ) : null}
            </div>
          ) : null}
          {iris || harKvitton ? (
            <div
              className={cn(
                "grid min-w-0 items-start gap-4",
                !support && "xl:grid-cols-2",
              )}
            >
              {iris ? (
                <Ruta
                  id="leads"
                  rubrik={T.leads}
                  text={T.leadsText}
                  antal={summa("leadsvar", "utkast")}
                >
                  <ul className="divide-y divide-ink/10">
                    <Lankrad
                      ikon={<Inbox className="h-4 w-4" aria-hidden />}
                      etikett={T.svarFranLeads}
                      ko={lage.leadsvar}
                      klar={ovrigaKlara}
                      href={vag("/dashboard/leads?vy=inkorg")}
                      knapp={T.oppnaInkorgen}
                    />
                    <Lankrad
                      ikon={<PenLine className="h-4 w-4" aria-hidden />}
                      etikett={T.leadsutkast}
                      ko={lage.utkast}
                      klar={ovrigaKlara}
                      href={vag("/dashboard/leads")}
                      knapp={T.oppnaUtkasten}
                    />
                  </ul>
                </Ruta>
              ) : null}
              {harKvitton ? (
                <Ruta
                  id="kvitton"
                  rubrik={T.kvitton}
                  text={T.kvittonText}
                  antal={antal("kvitton")}
                >
                  {kvittorader === null ? (
                    !ovrigaKlara ? (
                      <div
                        className="h-24 animate-pulse rounded-input bg-ink/[0.05]"
                        aria-hidden
                      />
                    ) : (
                      <p className={meta}>{text(T.ingenAtkomst)}</p>
                    )
                  ) : kvittorader.length === 0 ? (
                    <p className={meta}>{text(T.ingaKvitton)}</p>
                  ) : (
                    <ul className="divide-y divide-ink/10">
                      {kvittorader.slice(0, TAK).map((k) => (
                        <li
                          key={k.id}
                          className="flex items-center gap-3 py-2.5"
                        >
                          <Receipt
                            className="h-4 w-4 shrink-0 text-ink-subtle"
                            aria-hidden
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[0.9375rem] font-medium">
                              {k.motpart || k.filnamn || "–"}
                            </span>
                            <span className={cn(meta, "block truncate")}>
                              {[k.kategorietikett, k.datum]
                                .filter(Boolean)
                                .join(" · ")}
                            </span>
                          </span>
                          <span className="num shrink-0 text-[0.875rem] tabular-nums text-ink">
                            {belopp(k, locale)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <Link
                    href={vag("/dashboard/kvitton")}
                    className={cn(btnSecondary, btnLiten, "mt-3")}
                  >
                    {text(T.oppnaKvitton)}
                    {kvittorader && kvittorader.length > TAK ? (
                      <span className="num tabular-nums text-ink-subtle">
                        ({kvittorader.length})
                      </span>
                    ) : null}
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                </Ruta>
              ) : null}
            </div>
          ) : null}
        </div>
      </SmalKolumn>
    </div>
  );
}

function Ruta({
  id,
  rubrik: titel,
  text: undertext,
  antal,
  larm = false,
  children,
}: Readonly<{
  id: string;
  rubrik: Localized;
  text: Localized;
  antal: number | null;
  larm?: boolean;
  children: React.ReactNode;
}>) {
  const { text } = useLocale();
  return (
    <section
      aria-labelledby={`${id}-rubrik`}
      id={id}
      className={cn(
        kort,
        "min-w-0 scroll-mt-24",
        larm &&
          (antal ?? 0) > 0 &&
          "shadow-[inset_0_2px_0_0_oklch(var(--ochre))]",
      )}
    >
      <h2
        id={`${id}-rubrik`}
        className="text-[1.0625rem] font-semibold tracking-[-0.01em]"
      >
        {text(titel)}
        {antal ? (
          <span className="num ml-2 font-normal tabular-nums text-ink-subtle">
            {antal}
          </span>
        ) : null}
      </h2>
      <p className={cn(meta, "mb-3 mt-1")}>{text(undertext)}</p>
      {children}
    </section>
  );
}

function Lankrad({
  ikon,
  etikett,
  ko,
  klar,
  href,
  knapp,
}: Readonly<{
  ikon: React.ReactNode;
  etikett: Localized;
  ko: { antal: number; tider: number[] } | null;
  klar: boolean;
  href: string;
  knapp: Localized;
}>) {
  const { text, locale } = useLocale();
  const senast = ko?.tider.length ? Math.max(...ko.tider) : null;
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-paper2 text-ink-muted">
        {ikon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[0.9375rem] font-medium">
          <span className="num mr-1.5 tabular-nums">{ko ? ko.antal : "…"}</span>
          {text(etikett).toLowerCase()}
        </span>
        <span className={meta}>
          {ko === null
            ? klar
              ? text(T.ingenAtkomst)
              : "…"
            : ko.antal === 0
              ? text(T.ingetVantar)
              : senast !== null
                ? `${text(T.sedan)} ${sedan(senast, locale)}`
                : ""}
        </span>
      </span>
      <Link href={href} className={cn(btnSecondary, btnLiten, "shrink-0")}>
        {text(knapp)}
        <ArrowRight className="h-3.5 w-3.5" aria-hidden />
      </Link>
    </li>
  );
}
