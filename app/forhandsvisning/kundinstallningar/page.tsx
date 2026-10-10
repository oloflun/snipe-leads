"use client";

import { useState } from "react";
import { IrisProdukter } from "@/components/leads/IrisProdukter";
import { AgentOnskemal } from "@/components/settings/AgentOnskemal";

/**
 * Förhandsvisning av fas 8 (2026-10-06): kundens Produkter och målgrupp och
 * Era önskemål till agenten, med syntetiska svar i stället för backenden.
 *
 * Ingenting här når en databas. `fetch` mot `/api/snajp-support/...` fångas i
 * sidan och svarar med påhittade, uppenbart syntetiska värden, så att
 * panelerna kan granskas visuellt utan inloggning och utan lokal Postgres.
 */

const CONFIG = {
  produkter: [
    { namn: "Kundtjänstagent", nytta: "Svarar på kundmejl dygnet runt utifrån er kunskapsbas." },
    { namn: "Iris", nytta: "Hittar bolag som passar och skriver ett personligt första mejl." }
  ],
  segment: [
    { bransch: "Utbildningsföretag", varfor: "Många återkommande frågor om kurser och bokning." },
    { bransch: "Små e-handlare", varfor: "Hög andel ärenden om leverans och retur." }
  ],
  offentlig_sektor: false
};

const ONSKEMAL = {
  dokument: "Skriv kortare mejl, högst fem meningar.\nTilltala mottagaren med du.",
  max_tecken: 4000,
  historik: [
    { id: "v2", created_at: new Date(Date.now() - 36e5).toISOString(), content: "Skriv kortare mejl, högst fem meningar.\nTilltala mottagaren med du.", feedback: "Kortare mejl, och du-tilltal" },
    { id: "v1", created_at: new Date(Date.now() - 864e5).toISOString(), content: "Skriv kortare mejl, högst fem meningar.", feedback: "Kortare mejl tack" }
  ]
};

const BAKNING = {
  dokument: "Skriv kortare mejl, högst fem meningar.\nTilltala mottagaren med du.\nNämn aldrig priser i första mejlet.",
  andringar: [
    { typ: "lagg_till", ny: "Nämn aldrig priser i första mejlet.", skal: "Kunden vill inte ha priser i första kontakten." }
  ],
  sammanfattning: "En rad läggs till. Inget annat ändras."
};

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
    if (url.includes("/leads/config")) return svar(CONFIG);
    if (url.endsWith("/forhandsgranska")) return svar(BAKNING);
    if (url.includes("/agent/onskemal/")) return svar(ONSKEMAL);
    return svar({});
  };
}

export default function Kundinstallningar() {
  const [redo] = useState(() => {
    installeraFetch();
    return true;
  });
  if (!redo) return null;
  return (
    <main className="mx-auto grid max-w-3xl gap-12 px-4 py-10">
      <IrisProdukter />
      <div className="border-t border-ink/15 pt-8">
        <AgentOnskemal agent="leads" />
      </div>
    </main>
  );
}
