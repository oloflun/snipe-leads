"use client";

import { useEffect, useState } from "react";
import { LeadDetail } from "@/components/leads/IrisBolag";
import { IrisGranskning } from "@/components/leads/IrisGranskning";
import { KorningensUtkast } from "@/components/leads/KorningensUtkast";

/**
 * Förhandsvisning (2026-10-07): en körnings leads och utkast med
 * "Godkänn och skicka alla" och "Skriv utkast till de som saknar", plus
 * översiktens kompakta granskningsruta. Syntetiska svar, ingen databas;
 * samma mönster som /forhandsvisning/kundinstallningar.
 */

const LEADS = [
  { prospect_id: "p1", company_name: "Provbygget", contact_email: "info@provbygget.example", kan_mejlas: true, status: "vantar", queue_item_id: "q1", subject: "Nya kontoret i Holmsund", body: "Hej,\n\nJag såg att ni växer. Exempeltext i förhandsvisningen.\n\nVänliga hälsningar\nIris", notis: null },
  { prospect_id: "p2", company_name: "Exempelrör", contact_email: "anna@exempelror.example", kan_mejlas: true, status: "vantar", queue_item_id: "q2", subject: "Två nya montörer i Luleå", body: "Hej,\n\nJag såg att ni växer. Exempeltext i förhandsvisningen.\n\nVänliga hälsningar\nIris", notis: null },
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

let utskicksvarv = 0;

/**
 * Läget "fallet utkastjobb" (2026-11-25): `?lage=fallet-utkastjobb` visar
 * Iris-bolagets ruta (LeadDetail) där "Skapa utkast" startar ett jobb som
 * faller. `&kod=` väljer felkoden i jobbsvaret (standard saknar_produkt;
 * `kod=okand` ger en kod tabellen inte känner). Byt språk för att se att den
 * engelska rutan aldrig får backendens svenska text (lib/leads/felkoder.ts).
 */
const FALLET_PROSPEKT = {
  id: "p-fel",
  company_name: "Provbygget AB",
  contact_name: null,
  contact_email: "info@provbygget.example",
  status: "ready",
  origin: null,
  ort: "Umeå",
  sni: null,
  website: "https://provbygget.example",
  orgnr: null,
  score_total: 72,
  icp_fit: 0.7,
  qualified: true,
  disqualifiers: null,
  score_breakdown: null,
  niva: "B",
  motivering: "Exempeltext i förhandsvisningen."
};

/** Backendens svenska text för koden, så som jobbposten lagrar den. */
const FALLET_TEXT: Record<string, string> = {
  saknar_produkt:
    "Iris vet inte vilken av era produkter mejlen ska sälja. Lägg till minst en produkt under Inställningar › Målgrupp och automation innan Iris skriver utkast.",
  okand: "Ett internt fel som ytan inte har någon kod för."
};

let fallKod: string | null = null;

/** Next skickar en server action som en POST med rubriken Next-Action. */
function arServerAction(init?: RequestInit): boolean {
  try {
    return new Headers(init?.headers).has("next-action");
  } catch {
    return false;
  }
}

/**
 * Erbjudandet (lasOffertForUtkast) läses med en server action före utkastet.
 * Utan inloggning svarar den ok: false; svaret skickas vidare med resultatet
 * utbytt, så att flödet når jobbet. Raden i flight-formatet är vanlig JSON.
 */
async function offertUtanInloggning(riktigt: Promise<Response>): Promise<Response> {
  const res = await riktigt;
  const kropp = await res.text();
  const ersatt = kropp.replace(
    /\{"ok":false,"fel":\{"sv":"[^"]*","en":"[^"]*"\}\}/,
    JSON.stringify({ ok: true, text: "Exempelerbjudande i förhandsvisningen." })
  );
  return new Response(ersatt, { status: res.status, headers: res.headers });
}

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
    if (fallKod && arServerAction(init)) return offertUtanInloggning(riktig(input, init));
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    if (fallKod) {
      if (url.endsWith("/leads/prospects/p-fel")) return svar({ prospect: FALLET_PROSPEKT, sources: [] });
      if (url.endsWith("/leads/prospects/p-fel/utkast")) return svar({ utkast: null });
      if (url.endsWith("/leads/outreach/draft")) return svar({ job_id: "utkast-fel", fase: "skriver" }, 202);
      if (url.endsWith("/leads/jobb/utkast-fel")) {
        return svar({
          status: "failed",
          result: null,
          error: FALLET_TEXT[fallKod] ?? FALLET_TEXT.okand,
          ...(fallKod === "okand" ? {} : { error_kod: fallKod })
        });
      }
    }
    // Massutskicket går som ett jobb (lib/leads/utskicksjobb.ts): starten
    // svarar med ett id, och pollningen visar förloppet i tre varv.
    if (url.endsWith("/utkast/skicka-jobb")) {
      utskicksvarv = 0;
      return svar({ job_id: "utskick-1", pagar: false }, 202);
    }
    if (url.endsWith("/leads/jobb/utskick-1")) {
      utskicksvarv += 1;
      if (utskicksvarv < 4) {
        return svar({ status: "processing", forlopp: { klara: Math.min(utskicksvarv - 1, 2), totalt: 2 } });
      }
      for (const l of LEADS) if (l.status === "vantar") l.status = "skickat";
      return svar({
        status: "completed",
        forlopp: { klara: 2, totalt: 2 },
        result: { skickade: 2, vantar_pa_fonstret: 0, stoppade: [] }
      });
    }
    if (url.endsWith("/utkast/skriv")) return svar({ count: 1, jobs: [] }, 202);
    if (url.endsWith("/reject")) {
      const id = url.split("/").at(-2);
      for (const l of LEADS) if ((l as { queue_item_id?: string }).queue_item_id === id) l.status = "avvisat";
      return svar({ id, status: "cancelled" });
    }
    if (url.endsWith("/approve")) {
      const id = url.split("/").at(-2);
      for (const l of LEADS) if ((l as { queue_item_id?: string }).queue_item_id === id) l.status = "skickat";
      return svar({ id, status: "sent", utfall: "sent", besked: "Skickat" });
    }
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
  // Läget läses efter hydreringen, så att servern och klienten renderar lika.
  const [fallet, setFallet] = useState(false);
  useEffect(() => {
    const parametrar = new URLSearchParams(window.location.search);
    if (parametrar.get("lage") !== "fallet-utkastjobb") return;
    fallKod = parametrar.get("kod") || "saknar_produkt";
    setFallet(true);
  }, []);
  if (!redo) return null;
  if (fallet) {
    return (
      <main className="mx-auto grid max-w-3xl gap-12 px-4 py-10">
        <LeadDetail id="p-fel" demo={false} />
      </main>
    );
  }
  return (
    <main className="mx-auto grid max-w-3xl gap-12 px-4 py-10">
      <KorningensUtkast jobId="forhandsvisning" />
      <div className="border-t border-ink/15 pt-8">
        <IrisGranskning kompakt max={3} />
      </div>
    </main>
  );
}
