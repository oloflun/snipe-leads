"use client";

import { useEffect, useState } from "react";
import { KunskapsbasPanel } from "@/components/settings/Kunskapsbas";
import { useLocale } from "@/lib/i18n";

/**
 * Förhandsvisning (2026-11-25): Inställningar › Kunskapsbas, utan databas och
 * utan inloggning. Anropen mot /api/snajp-support/kb besvaras här i
 * webbläsaren med påhittade värden.
 *
 * Artikellistan har en supportartikel, en säljfakta-artikel och en kvarvarande
 * exempelartikel (etiketten "Exempel"). Förslagslistan har ett skanningsförslag
 * i kategorin säljfakta och ett förslag från Hjälprutan. Med ?lage=utan-skanning
 * har ingen skanning körts: förslaget ur Hjälprutan och startformuläret under det.
 *
 * I en riktig bas står exempel och egna artiklar aldrig sida vid sida: exemplen
 * raderas när eget innehåll läggs till. Här visas de ihop bara för att alla
 * etiketter ska gå att se i en och samma bild.
 */

// Fast tid: Date.now() vid rendering ger olika värden på servern och i
// webbläsaren, och sidan hydrerar om med fel.
const TID = "2026-11-25T08:00:00.000Z";

const ARTIKLAR = [
  {
    id: "00000000-0000-4000-c000-0000000000a1",
    title: "Leveranstider",
    content:
      "Exempel: vi skickar inom två arbetsdagar med PostNord. Frakten är fri över 500 kronor, annars 49 kronor.",
    category: "leverans",
    source_url: null,
    giltig_till: null,
    is_placeholder: false,
    created_at: TID
  },
  {
    id: "00000000-0000-4000-c000-0000000000a2",
    title: "Våra tjänster",
    content:
      "Exempel: vi bygger och sköter webbutiker åt små företag, med fast månadspris och support på svenska.",
    category: "salj",
    source_url: "https://exempelbolaget.example/tjanster",
    giltig_till: null,
    is_placeholder: false,
    created_at: TID
  },
  {
    id: "00000000-0000-4000-c000-0000000000a3",
    title: "Så gör du en retur",
    content: "Du har 30 dagars öppet köp. Fyll i returblanketten och skicka varan med den förbetalda etiketten.",
    category: "retur_reklamation",
    source_url: null,
    giltig_till: null,
    is_placeholder: true,
    created_at: TID
  }
];

const SKANNING = {
  id: "00000000-0000-4000-c000-0000000000b1",
  webbplats: "https://exempelbolaget.example",
  status: "klar",
  startad_av: "onboarding",
  sidor: 12,
  lasbara_sidor: 11,
  forslag: 1,
  redan_fanns: 0,
  fel: null,
  startad_at: TID,
  klar_at: TID
};

const FORSLAG = [
  {
    id: "00000000-0000-4000-c000-0000000000c1",
    title: "Priser och paket",
    content:
      "Exempel: **Bas** kostar 1 900 kronor i månaden och **Plus** 3 400 kronor.",
    category: "salj",
    source_url: "https://exempelbolaget.example/priser",
    confidence: 0.8,
    varningar: [],
    kalla: "skanning"
  },
  {
    id: "00000000-0000-4000-c000-0000000000c2",
    title: "Öppettider i butiken",
    content: "Exempel: butiken har öppet vardagar 10 till 18 och lördagar 10 till 15. Söndagar har vi stängt.",
    category: "ovrigt",
    source_url: null,
    confidence: null,
    varningar: [],
    kalla: "chatt"
  }
];

function json(kropp: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } })
  );
}

type Fonster = Window & { __kbForhand?: boolean };

function installeraFetch() {
  const w = window as Fonster;
  if (w.__kbForhand) return;
  w.__kbForhand = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    const metod = (init?.method ?? "GET").toUpperCase();
    if (url.endsWith("/kb/forslag/beslut")) return json({ tillagda: [], avvisade: [], fanns_redan: [] });
    if (url.endsWith("/kb/forslag")) {
      // ?lage=utan-skanning: ingen skanning körd, bara förslaget ur
      // Hjälprutan. Startformuläret står då under listan i samma panel.
      const utanSkanning = new URLSearchParams(window.location.search).get("lage") === "utan-skanning";
      return utanSkanning
        ? json({ skanning: null, forslag: FORSLAG.filter((f) => f.kalla === "chatt") })
        : json({ skanning: SKANNING, forslag: FORSLAG });
    }
    if (url.endsWith("/api/snajp-support/kb") && metod === "POST") {
      return json({ created: [], embeddings: 0, utan_vektor: 0 }, 201);
    }
    if (url.endsWith("/api/snajp-support/kb")) return json({ tenant_name: "Exempelbolaget AB", articles: ARTIKLAR });
    return json({});
  };
}

export default function KunskapsbasForhandsvisning() {
  const { text } = useLocale();
  const [redo, setRedo] = useState(false);

  useEffect(() => {
    installeraFetch();
    setRedo(true);
  }, []);

  if (!redo) return null;

  return (
    <main className="appyta min-h-dvh bg-paper px-4 py-8 text-ink">
      <div className="mx-auto max-w-[860px]">
        <h1 className="text-[1.375rem] font-semibold">{text({ sv: "Kunskapsbas", en: "Knowledge base" })}</h1>
        <div className="mt-6">
          <KunskapsbasPanel />
        </div>
      </div>
    </main>
  );
}
