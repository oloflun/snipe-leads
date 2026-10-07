"use client";

import { useState } from "react";
import { LeadslistorView } from "@/components/leads/LeadslistorView";

/**
 * Förhandsvisning (2026-10-07): listan "Utan webbplats" med "Skriv utkast
 * till N bolag", status per rad och köningen till VD:s adress. Syntetiska
 * bolag och svar, ingen databas; samma mönster som
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

const UTKAST = (namn: string, ort: string) => ({
  subject: `${namn} i ${ort}`,
  body: `Hej,\n\nVar kommer de flesta av era nya kunder ifrån i dag? Att hitta nya affärer tar ofta tid från det dagliga arbetet.\n\nSnajp har en agent som hittar bolag som passar er kundprofil och skriver ett första mejl som ni granskar innan det skickas.\n\nHör av er om ni vill se ett exempel.\n\nVänliga hälsningar,`
});

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

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  let skrivetAt = 0;
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    const metod = (init?.method ?? "GET").toUpperCase();
    if (metod === "POST" && url.endsWith(`/listor/${LISTA.id}/utkast`)) {
      skrivetAt = Date.now();
      return svar({ count: RADER.length }, 202);
    }
    if (metod === "POST" && url.endsWith("/koa")) {
      const id = url.split("/items/")[1]?.split("/")[0];
      const rad = RADER.find((r) => r.id === id);
      if (rad) rad.utkast = { ...(rad.utkast as object), queue_item_id: "q-1" };
      const u = UTKAST(String(rad?.company_name ?? ""), String(rad?.ort ?? ""));
      return svar({ queue_item_id: "q-1", prospect_id: "p-1", subject: u.subject, body: `${u.body}\nSebastian Bergman\nSnajp Support` });
    }
    if (url.endsWith(`/listor/${LISTA.id}`)) {
      // Utkasten "skrivs" en i taget, en per tre sekunder efter klicket.
      const klara = skrivetAt ? Math.min(RADER.length, Math.floor((Date.now() - skrivetAt) / 3000) + 1) : 0;
      RADER.forEach((r, i) => {
        if (i < klara && !r.utkast) r.utkast = UTKAST(String(r.company_name), String(r.ort));
      });
      return svar({ list: LISTA, items: RADER });
    }
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
