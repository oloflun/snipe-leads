"use client";

import { useState } from "react";
import { IrisInkorg } from "@/components/leads/IrisInkorg";
import { LeadsTabell } from "@/components/leads/LeadsTabell";

/**
 * Förhandsvisning (2026-10-07, utökad 2026-10-08): Iris-leads med kolumnen
 * Utkast (en status per lead) och Leads › Inkorg › Skickat med statusfilter.
 * Syntetiska bolag och mejl, ingen databas; samma mönster som
 * /forhandsvisning/kundinstallningar.
 */

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();

const imorgon = new Date(nu + 864e5);
imorgon.setUTCHours(6, 0, 0, 0);

const PROSPEKT = [
  { id: "p1", company_name: "Provbygget AB", status: "contacted", niva: "A", score_total: 82, ort: "Umeå", origin: "iris", created_at: iso(30), utkast_status: "skickat" },
  { id: "p2", company_name: "Exempelrör Norr AB", status: "replied", niva: "B", score_total: 71, ort: "Luleå", origin: "iris", created_at: iso(28), utkast_status: "skickat" },
  { id: "p3", company_name: "Testmåleri AB", status: "new", niva: "A", score_total: 77, ort: "Umeå", origin: "iris", created_at: iso(3), contact_email: "info@testmaleri.example", utkast_status: "vantar", queue_item_id: "q3" },
  { id: "p4", company_name: "Fiktiva Fönster AB", status: "ready", niva: "A", score_total: 74, ort: "Skellefteå", origin: "iris", created_at: iso(5), contact_email: "info@fonster.example", utkast_status: "godkant", queue_item_id: "q4", skickas_tidigast: imorgon.toISOString() },
  { id: "p5", company_name: "Låtsasel i Norr AB", status: "new", niva: "B", score_total: 63, ort: "Piteå", origin: "iris", created_at: iso(6), contact_email: "kontakt@latsasel.example", utkast_status: "stoppat", utkast_skal: "Klockan är 03:14 svensk tid. Utskick sker 8–17 på vardagar." },
  { id: "p6", company_name: "Påhittat Plåt AB", status: "new", niva: "B", score_total: 58, ort: "Luleå", origin: "iris", created_at: iso(8), utkast_status: "saknas" }
];

const SIGNATUR = "Vänliga hälsningar,\nSebastian Bergman\nSnajp Support | AI för leads och kundtjänst\n\nUmeå & Göteborg\nwww.snajp.se\n\nSnajp AB";

const SKICKAT = [
  {
    id: "m1",
    subject: "Nya kontoret i Holmsund",
    body: `Hej,\n\nNi rekryterar två snickare till det nya kontoret i Holmsund. När en byggfirma växer så snabbt brukar orderboken behöva fyllas på i samma takt.\n\nSnajp hittar bolag som passar er kundprofil och skriver ett första mejl som ni granskar innan det skickas.\n\nHör av er om ni vill se två konkreta exempel.\n\n${SIGNATUR}\n\n--\nSnajp AB, org.nr 559000-0000\nExempelgatan 1, 903 26 Umeå\n\nVill du inte få fler mejl från oss: https://snajp.example/avregistrera/exempel`,
    sent_at: iso(2),
    prospect_id: "p1",
    company_name: "Provbygget AB",
    contact_name: null,
    prospect_email: "info@provbygget.example",
    svarat: false,
    status: "contacted"
  },
  {
    id: "m2",
    subject: "Två nya montörer i Luleå",
    body: `Hej Anna,\n\nTvå nya montörer på kort tid. Då brukar frågan snart bli var nästa uppdrag kommer ifrån.\n\nHör av dig om du vill se ett exempel.\n\n${SIGNATUR}`,
    sent_at: iso(26),
    prospect_id: "p2",
    company_name: "Exempelrör Norr AB",
    contact_name: "Anna",
    prospect_email: "anna@exempelror.example",
    svarat: true,
    status: "replied"
  },
  {
    id: "m3",
    subject: "Er nya verkstad",
    body: `Hej,\n\nEn kort fråga om er nya verkstad.\n\n${SIGNATUR}`,
    sent_at: iso(80),
    prospect_id: "p7",
    company_name: "Testtak Väst AB",
    contact_name: null,
    prospect_email: "info@testtak.example",
    svarat: true,
    status: "lost"
  }
];

function svar(kropp: unknown) {
  return Promise.resolve(new Response(JSON.stringify(kropp), { status: 200, headers: { "Content-Type": "application/json" } }));
}

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    if (url.includes("/leads/skickat")) return svar({ skickat: SKICKAT });
    if (url.includes("/leads/prospects")) {
      return svar({ prospects: url.includes("bortvalda") || url.includes("arkiverade") ? [] : PROSPEKT });
    }
    if (url.includes("/leads/uppgifter")) return svar({ uppgifter: [] });
    return svar({});
  };
}

export default function LeadsSkickatForhandsvisning() {
  const [redo] = useState(() => {
    installeraFetch();
    return true;
  });
  const [flik, setFlik] = useState<"inkommande" | "skickat">("skickat");
  if (!redo) return null;
  return (
    <main className="mx-auto max-w-6xl space-y-16 px-4 py-10">
      <LeadsTabell />
      {/* Inkommande kräver arbetsytans inkorg; förhandsvisningen visar Skickat. */}
      <IrisInkorg flik={flik} onFlik={(f) => setFlik(f === "skickat" ? "skickat" : flik)} />
    </main>
  );
}
