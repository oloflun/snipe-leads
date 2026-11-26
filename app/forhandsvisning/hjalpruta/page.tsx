"use client";

import { useEffect, useState } from "react";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import {
  HjalpRuta,
  glomHjalpArenden,
  type Arende,
  type HjalpRutaStart
} from "@/components/snajp/HjalpRuta";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Förhandsvisning av Hjälprutan (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 1, 5
 * och 8), utan databas och utan inloggning.
 *
 * `fetch` mot `/api/snajp-support/...` fångas i sidan och besvaras med
 * påhittade, uppenbart syntetiska värden. Varje läge nås med `?lage=`:
 *
 *   tomt      tomt samtal med de tre startvalen
 *   fraga     en fråga som pågår (agentens fasvisning)
 *   kunskap   kunskapskortet med rubrik och text att granska
 *   lasroll   samma kort för läsrollen: knappen avstängd, förklaringen synlig
 *   fel       felkortet med de tre fälten och det som skickas med
 *   kvitto    ett kvitterat ärende
 *   arenden   Mina ärenden med ett ärende i varje kundläge
 *   av        hjälpen är inte påslagen (503)
 *
 * Sidomenyn till vänster är en kuliss med den riktiga Meny-knappen, så att
 * pricken och ingången "Hjälp och fel" går att se.
 */

type Lage = "tomt" | "fraga" | "kunskap" | "lasroll" | "fel" | "kvitto" | "arenden" | "av";

const LAGEN: { lage: Lage; namn: Localized }[] = [
  { lage: "tomt", namn: { sv: "Tomt", en: "Empty" } },
  { lage: "fraga", namn: { sv: "Pågående fråga", en: "Question in progress" } },
  { lage: "kunskap", namn: { sv: "Kunskapskort", en: "Knowledge card" } },
  { lage: "lasroll", namn: { sv: "Läsrollen", en: "Read access" } },
  { lage: "fel", namn: { sv: "Felkort", en: "Issue card" } },
  { lage: "kvitto", namn: { sv: "Kvitterat ärende", en: "Acknowledged case" } },
  { lage: "arenden", namn: { sv: "Mina ärenden", en: "My cases" } },
  { lage: "av", namn: { sv: "Inte påslagen (503)", en: "Not switched on (503)" } }
];

const nu = Date.now();
const iso = (minuterSedan: number) => new Date(nu - minuterSedan * 60_000).toISOString();

function arende(
  nummer: string,
  status: Arende["status"],
  gjorde: string,
  handelser: Arende["handelser"],
  extra: Partial<Arende> = {}
): Arende {
  return {
    id: `00000000-0000-4000-8000-0000000000${nummer.slice(-2)}`,
    nummer,
    status,
    sida: "/dashboard/leads",
    gjorde,
    created_at: handelser[0]?.tid ?? iso(60),
    updated_at: handelser[handelser.length - 1]?.tid ?? iso(60),
    vantar_pa_kund: status === "behover_mer" || status === "redo_att_testa",
    testversion_url: null,
    handelser,
    ...extra
  };
}

const ARENDEN: Arende[] = [
  arende("F-0046", "redo_att_testa", "Exempel: startade en körning med tio bolag.", [
    { tid: iso(4320), typ: "skapad", status: "mottagen", meddelande: null },
    { tid: iso(2900), typ: "status", status: "rattning_pagar", meddelande: null },
    {
      tid: iso(30),
      typ: "status",
      status: "redo_att_testa",
      meddelande: "Exempel: rättningen ligger i en testversion med bara er arbetsyta. Prova samma körning där."
    }
  ], { testversion_url: "https://forhand.example.com/arende/F-0046" }),
  arende("F-0045", "behover_mer", "Exempel: öppnade Kunskapsbas på mobilen.", [
    { tid: iso(1500), typ: "skapad", status: "mottagen", meddelande: null },
    { tid: iso(90), typ: "status", status: "behover_mer", meddelande: "Exempel: vilken telefon och webbläsare använde du?" }
  ], { sida: "/settings/kunskapsbas" }),
  arende("F-0044", "mottagen", "Exempel: klickade på Skicka utkast.", [
    { tid: iso(12), typ: "skapad", status: "mottagen", meddelande: null }
  ]),
  arende("F-0043", "undersoks", "Exempel: bytte språk till engelska.", [
    { tid: iso(2000), typ: "skapad", status: "mottagen", meddelande: null },
    { tid: iso(1800), typ: "status", status: "undersoks", meddelande: null }
  ], { sida: "/dashboard" }),
  arende("F-0042", "i_main", "Exempel: laddade upp en PDF i kunskapsbasen.", [
    { tid: iso(14000), typ: "skapad", status: "mottagen", meddelande: null },
    { tid: iso(9000), typ: "status", status: "kund_godkand", meddelande: null },
    { tid: iso(7000), typ: "status", status: "i_main", meddelande: "Exempel: rättningen är ute för alla." }
  ], { sida: "/settings/kunskapsbas" }),
  arende("F-0041", "stangd", "Exempel: sökte efter bolag i Gotland.", [
    { tid: iso(20000), typ: "skapad", status: "mottagen", meddelande: null },
    {
      tid: iso(19000),
      typ: "status",
      status: "stangd",
      meddelande: "Exempel: registret har inga bolag som matchar filtret. Det är inte ett fel, men vi har gjort texten tydligare."
    }
  ], { sida: "/dashboard/leads/korning" })
];

function json(kropp: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } })
  );
}

type Fonster = Window & { __hjalpForhand?: boolean; __hjalpLage?: Lage };

function installeraFetch() {
  const w = window as Fonster;
  if (w.__hjalpForhand) return;
  w.__hjalpForhand = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    const lage = w.__hjalpLage ?? "tomt";
    const metod = (init?.method ?? "GET").toUpperCase();
    if (lage === "av" && url.includes("/hjalp")) {
      return json({ error: "Hjälpen är inte påslagen.", kod: "hjalp_av" }, 503);
    }
    if (url.endsWith("/hjalp/samtal")) {
      return json({ overlamnad: false, meddelanden: [] });
    }
    if (url.includes("/hjalp/jobb/")) {
      // Frågan blir aldrig klar här: fasvisningen ska gå att se.
      return json({ status: "running", fas: "soker" });
    }
    if (url.endsWith("/api/snajp-support/hjalp")) {
      return json({ job_id: "00000000-0000-4000-8000-00000000f001" });
    }
    if (url.endsWith("/hjalp/arenden") && metod === "POST") {
      return json({ id: "00000000-0000-4000-8000-000000000047", nummer: "F-0047", status: "mottagen", created_at: iso(0) }, 201);
    }
    if (url.endsWith("/hjalp/arenden")) {
      return json({ arenden: lage === "tomt" || lage === "fraga" ? [] : ARENDEN });
    }
    const atgard = url.match(/\/hjalp\/arenden\/([^/]+)\/(svar|utslag)$/);
    if (atgard) {
      const fore = ARENDEN.find((a) => a.id === atgard[1]) ?? ARENDEN[0];
      return json({
        ...fore,
        status: atgard[2] === "svar" ? "undersoks" : "kund_godkand",
        vantar_pa_kund: false,
        handelser: [...fore.handelser, { tid: iso(0), typ: atgard[2], status: null, meddelande: null }]
      });
    }
    if (url.includes("/kb")) return json({ ok: true });
    return json({});
  };
}

function startFor(lage: Lage): HjalpRutaStart {
  switch (lage) {
    case "fraga":
      return { fraga: "Hur lägger jag till en kollega i arbetsytan?" };
    case "kunskap":
    case "lasroll":
      return {
        lasare: lage === "lasroll",
        kort: [
          {
            typ: "kunskap",
            steg: "granska",
            utkast: "",
            titel: "Öppettider i butiken",
            innehall:
              "Exempel: butiken på Storgatan har öppet vardagar 10 till 18 och lördagar 10 till 15. Söndagar har vi stängt. Kunder kan alltid hämta beställningar i kassan.",
            fel: null
          }
        ]
      };
    case "fel":
      return {
        kort: [
          {
            typ: "fel",
            steg: "fyll",
            gjorde: "Exempel: startade en körning med tio bolag i Västerbotten.",
            hande: "Exempel: körningen stod still på noll i tio minuter.",
            vantade: "",
            bild: null,
            nummer: null,
            fel: null
          }
        ]
      };
    case "kvitto":
      return {
        kort: [
          { typ: "fel", steg: "kvitterad", gjorde: "", hande: "", vantade: "", bild: null, nummer: "F-0047", fel: null }
        ]
      };
    case "arenden":
      return { flik: "arenden" };
    default:
      return {};
  }
}

export default function HjalprutaForhandsvisning() {
  const { text } = useLocale();
  const [lage, setLage] = useState<Lage | null>(null);

  useEffect(() => {
    installeraFetch();
    const fran = new URLSearchParams(window.location.search).get("lage");
    const giltigt = LAGEN.find((l) => l.lage === fran)?.lage ?? "tomt";
    (window as Fonster).__hjalpLage = giltigt;
    setLage(giltigt);
  }, []);

  const valj = (nytt: Lage) => {
    (window as Fonster).__hjalpLage = nytt;
    glomHjalpArenden();
    window.history.replaceState(null, "", `?lage=${nytt}`);
    setLage(nytt);
  };

  if (!lage) return null;

  return (
    <div className="appyta flex min-h-dvh bg-paper text-ink">
      {/* Kuliss: sidomenyn, med den riktiga Meny-knappen i foten. */}
      <aside className="hidden w-[260px] shrink-0 flex-col justify-end bg-ink px-3 pb-4 text-paper lg:flex">
        <AgentMenu yta="leads" kontext="forhandsvisning" ton="rail" hjalp key={`meny-${lage}`} />
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 lg:pl-[30rem]">
        <div className="flex items-center justify-between gap-3 lg:hidden">
          <span className="text-[13px] font-medium text-ink-subtle">Exempelbolaget AB</span>
          <AgentMenu yta="leads" kontext="forhandsvisning" hjalp key={`mobil-${lage}`} />
        </div>
        <p className="mt-4 text-[0.8125rem] font-medium text-ink-muted">
          {text({ sv: "Läge i förhandsvisningen", en: "Preview state" })}
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {LAGEN.map((l) => (
            <button
              key={l.lage}
              type="button"
              onClick={() => valj(l.lage)}
              aria-pressed={lage === l.lage}
              className={cn(
                "focus-ring inline-flex min-h-9 items-center rounded-full px-3 text-[0.8125rem] font-medium",
                lage === l.lage ? "bg-ink text-paper" : "text-ink-muted hover:bg-paper2"
              )}
            >
              {text(l.namn)}
            </button>
          ))}
        </div>
      </main>
      <HjalpRuta key={lage} start={startFor(lage)} onStang={() => undefined} />
    </div>
  );
}
