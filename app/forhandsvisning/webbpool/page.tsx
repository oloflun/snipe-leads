"use client";

import { useState } from "react";
import { LeadslistorView } from "@/components/leads/LeadslistorView";

/**
 * Förhandsvisning (2026-10-08): en webbpoollista hos en webbyrå, med
 * filtren webbplats, webbnivå och län och sorteringen "akut först"
 * (app/leads/webbpool.py, migration 108). Syntetiska bolag, ingen databas;
 * samma mönster som /forhandsvisning/listutkast.
 */

const LISTA = {
  id: "00000000-0000-4000-a000-0000000000c1",
  titel: "Webbleads vecka 41, 2026",
  antal: 200,
  status: "klar",
  item_count: 6,
  kalla: "webbpool",
  created_at: new Date().toISOString(),
  completed_at: new Date().toISOString()
};

// Raderna bär revisionen som webbpoolen skriver den (app/leads/webbpool.py):
// bristerna eller platshållarskälet ligger i webbrevision, och signal_detalj
// är backendens svenska sammanfattning för CSV och mejlbron.
const RAD = (id: string, namn: string, ort: string, lan: string, webbniva: string, modernitet: number | null,
  website: string | null, detalj: string) => {
  const brist = detalj.split(" · ").slice(-1)[0];
  const platshallare = modernitet === null ? brist : null;
  return {
    id: `00000000-0000-4000-a000-0000000000${id}`, company_name: namn, ort, lan, webbniva, website,
    webbrevision: { modernitet, brister: platshallare || webbniva === "mycket_bra" ? [] : [brist], platshallare },
    source_name: "webbpool", signal_detalj: detalj
  };
};

const RADER = [
  RAD("d1", "Provbygg Väst AB", "Göteborg", "vastra-gotalands-lan", "dalig", 4, "https://provbygg.example",
    "Dålig · modernitet 4/10 · Liten text och boxad layout"),
  RAD("d2", "Exempelmåleri AB", "Mölndal", "vastra-gotalands-lan", "akut", null, "https://exempelmaleri.example",
    "Akut · parkerad domän"),
  RAD("d3", "Testgolv i Halmstad AB", "Halmstad", "hallands-lan", "dalig", 3, "https://testgolv.example",
    "Dålig · modernitet 3/10 · Tabellbaserad layout"),
  RAD("d4", "Kuströr Exempel AB", "Varberg", "hallands-lan", "akut", 1, "https://kustror.example",
    "Akut · modernitet 1/10 · Bara en logga och en kontaktrad"),
  RAD("d5", "Fyrstudio Prov AB", "Göteborg", "vastra-gotalands-lan", "mycket_bra", 9, "https://fyrstudio.example",
    "Inspiration · modernitet 9/10"),
  RAD("d6", "Utan Sajt Bygg AB", "Kungälv", "vastra-gotalands-lan", "akut", null, null, "Akut · felsida (404)")
] as Record<string, unknown>[];

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
    if (url.endsWith(`/listor/${LISTA.id}`)) return svar({ list: LISTA, items: RADER });
    if (url.endsWith("/leads/listor")) return svar({ lists: [LISTA] });
    return svar({});
  };
}

export default function WebbpoolForhandsvisning() {
  const [redo] = useState(() => {
    installeraFetch();
    return true;
  });
  if (!redo) return null;
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <LeadslistorView />
    </main>
  );
}
