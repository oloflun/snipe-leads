"use client";

import { useState } from "react";
import { IrisGranskning } from "@/components/leads/IrisGranskning";
import { KorningensUtkast } from "@/components/leads/KorningensUtkast";

/**
 * Förhandsvisning (2026-10-07): en körnings leads och utkast med
 * "Godkänn och skicka alla" och "Skriv utkast till de som saknar", plus
 * översiktens kompakta granskningsruta. Syntetiska svar, ingen databas;
 * samma mönster som /forhandsvisning/kundinstallningar.
 */

const LEADS = [
  { prospect_id: "p1", company_name: "Provbygget", contact_email: "info@provbygget.example", kan_mejlas: true, status: "vantar", subject: "Nya kontoret i Holmsund", body: "Hej,\n\nJag såg att ni växer. Exempeltext i förhandsvisningen.\n\nVänliga hälsningar\nIris", notis: null },
  { prospect_id: "p2", company_name: "Exempelrör", contact_email: "anna@exempelror.example", kan_mejlas: true, status: "vantar", subject: "Två nya montörer i Luleå", body: "Hej,\n\nJag såg att ni växer. Exempeltext i förhandsvisningen.\n\nVänliga hälsningar\nIris", notis: null },
  { prospect_id: "p3", company_name: "Testmåleri", contact_email: "info@testmaleri.example", kan_mejlas: true, status: "skickat", subject: "Fasadsäsongen i Skellefteå", body: "Hej,\n\nJag såg att ni växer. Exempeltext i förhandsvisningen.\n\nVänliga hälsningar\nIris", notis: null },
  { prospect_id: "p4", company_name: "Demosnickarna", contact_email: "info@demosnickarna.example", kan_mejlas: true, status: "saknas", subject: null, notis: "Research klar, men utkastet stoppades före kön: faktagrinden." },
  { prospect_id: "p5", company_name: "Påhittat Golv", contact_email: null, kan_mejlas: false, status: "saknas", subject: null, notis: "Inget arbetsmejl hittades på bolagets sajt." }
];

const KO = {
  items: ["Nya kontoret i Holmsund", "Två nya montörer i Luleå", "Ny verkstad i Piteå", "Fasadsäsongen i Umeå"].map((amne, i) => ({
    id: `k${i}`,
    subject: amne,
    body: "Hej,\n\nExempeltext.",
    brodtext: "Hej,\n\nExempeltext.",
    svans: "",
    company_name: ["Provbygget", "Exempelrör", "Exempelverkstan", "Testfasad"][i],
    prospect_email: `info@exempel${i}.example`,
    created_at: new Date(Date.now() - i * 36e5).toISOString()
  }))
};

function svar(kropp: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } })
  );
}

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    if (url.endsWith("/utkast/skicka")) {
      for (const l of LEADS) if (l.status === "vantar") l.status = "skickat";
      return svar({ skickade: 2, vantar_pa_fonstret: 0, stoppade: [] });
    }
    if (url.endsWith("/utkast/skriv")) return svar({ count: 1, jobs: [] }, 202);
    if (url.endsWith("/utkast")) {
      const antal: Record<string, number> = {};
      for (const l of LEADS) antal[l.status] = (antal[l.status] ?? 0) + 1;
      antal.kan_skrivas = LEADS.filter((l) => l.status === "saknas" && l.kan_mejlas).length;
      return svar({ leads: LEADS, antal });
    }
    if (url.endsWith("/leads/queue")) return svar(KO);
    return svar({});
  };
}

export default function KorningensUtkastForhandsvisning() {
  const [redo] = useState(() => {
    installeraFetch();
    return true;
  });
  if (!redo) return null;
  return (
    <main className="mx-auto grid max-w-3xl gap-12 px-4 py-10">
      <KorningensUtkast jobId="forhandsvisning" />
      <div className="border-t border-ink/15 pt-8">
        <IrisGranskning kompakt max={3} />
      </div>
    </main>
  );
}
