"use client";

import { useState } from "react";
import { LeadslistorView } from "@/components/leads/LeadslistorView";

/**
 * Förhandsvisning (2026-10-07, omgjord 2026-10-10): en lista med markering,
 * Skapa utkast och Processa om, förloppet i listan och status per rad.
 * Syntetiska bolag och svar, ingen databas; samma mönster som
 * /forhandsvisning/kundinstallningar.
 */

const LISTA = {
  id: "00000000-0000-4000-a000-0000000000aa",
  titel: "Utan webbplats, Iris 2026-10-07",
  antal: 3,
  status: "klar",
  item_count: 3,
  kalla: "sok",
  created_at: new Date().toISOString(),
  completed_at: new Date().toISOString()
};

const RADER = [
  { id: "00000000-0000-4000-a000-0000000000b1", company_name: "Provsnickarn i Holmsund AB", ort: "Holmsund", signal: "Byggnadssnickerier, 1 anställd", source_name: "merinfo", contact_phone: "+46 70 000 00 01", contact_name: "VD", contact_role: "VD" },
  { id: "00000000-0000-4000-a000-0000000000b2", company_name: "Exempelrör Norr AB", ort: "Luleå", signal: "VVS-installationer, 4 anställda", source_name: "merinfo" },
  { id: "00000000-0000-4000-a000-0000000000b3", company_name: "Testmåleri AB", ort: "Umeå", signal: "Måleri, 2 anställda", source_name: "merinfo" }
] as Record<string, unknown>[];

function svar(kropp: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } })
  );
}

/** Förloppet "går" en rad per två sekunder efter klicket. */
let forlopp: { typ: "processa" | "utkast"; startad: number; rader: string[] } | null = null;

function processering() {
  if (!forlopp) return null;
  const klara = Math.min(forlopp.rader.length, Math.floor((Date.now() - forlopp.startad) / 2000));
  const klar = klara >= forlopp.rader.length;
  const startad = new Date(forlopp.startad).toISOString();
  forlopp.rader.slice(0, klara).forEach((id, i) => {
    const rad = RADER.find((r) => r.id === id);
    if (!rad) return;
    if (forlopp?.typ === "processa") rad.processad_at = new Date().toISOString();
    else rad.utkast_status = { utkast_status: i % 3 === 2 ? "stoppat" : "vantar", queue_item_id: `q-${i}` };
  });
  return {
    typ: forlopp.typ,
    status: klar ? "klar" : "pagar",
    startad,
    senast: new Date().toISOString(),
    klar_at: klar ? new Date().toISOString() : null,
    totalt: forlopp.rader.length,
    klara,
    utfall: forlopp.typ === "processa" ? { mejl: Math.min(klara, 1), telefon: Math.max(0, klara - 1), utan: 0 } : undefined,
    levererade: forlopp.typ === "utkast" ? klara : undefined,
    job_id: forlopp.typ === "utkast" ? "00000000-0000-4000-a000-0000000000cc" : undefined,
    rader: forlopp.rader
  };
}

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    const metod = (init?.method ?? "GET").toUpperCase();
    const typ = url.endsWith(`/listor/${LISTA.id}/utkast`) ? "utkast" : url.endsWith(`/listor/${LISTA.id}/omprova`) ? "processa" : null;
    if (metod === "POST" && typ) {
      const ids = (JSON.parse(String(init?.body ?? "{}")) as { item_ids?: string[] }).item_ids ?? [];
      forlopp = { typ, startad: Date.now(), rader: ids };
      return svar({ count: ids.length, rader: ids.length, processering: processering() }, 202);
    }
    if (url.endsWith(`/listor/${LISTA.id}`)) return svar({ list: { ...LISTA, processering: processering() }, items: RADER });
    if (url.endsWith("/leads/listor")) return svar({ lists: [LISTA] });
    return svar({});
  };
}

export default function ListutkastForhandsvisning() {
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
