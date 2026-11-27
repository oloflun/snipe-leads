"use client";

import { useState } from "react";
import { FelOchEskaleringar } from "@/components/admin/FelOchEskaleringar";
import type { AdminArende, AdminHandelse, Arendestatus } from "@/lib/admin/plattformsarenden";
import type { EventRow, TenantRow } from "@/lib/data/admin";

/**
 * Förhandsvisning (2026-11-25): Kunder › Fel & eskaleringar med felrapporterna
 * från Hjälprutan (PLAN-HJALPRUTAN-2026-11-25, del 5). Syntetiska kunder och
 * rapporter, ingen databas: anropen mot /api/admin/plattformsarenden besvaras
 * här i webbläsaren, och ett lägesbyte sparas i webbläsarens minne så att det
 * står kvar efter en omladdning, som det gör mot backenden.
 *
 *   ?lage=tomt   inga rapporter
 *   ?lage=fel    backenden svarar med fel
 *   ?lage=nollstall  börja om från de påhittade rapporterna
 *   ?lage=bildfel    listan går bra men bilden går inte att hämta
 *
 * Bilden (F-0007) hämtas som i adminytan: först när Visa bilden trycks, från
 * .../{id}/bild, och svaret är en liten PNG som ritas här i webbläsaren.
 */

// v2: vy, roll och aktör med backendens egna värden (egen/kund, owner/member/viewer, admin:<uuid>).
const NYCKEL = "forhandsvisning-felrapporter-v2";
const ADMIN_ANTON = "admin:00000000-0000-4000-d000-000000000001";
const ADMIN_SEBBE = "admin:00000000-0000-4000-d000-000000000002";
// Fast tid: Date.now() gav olika klockslag på servern och i webbläsaren, och
// sidan hydrerade om med fel.
const nu = Date.parse("2026-11-25T04:00:00Z");
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();

const handelse = (
  timmar: number,
  typ: string,
  status: Arendestatus | null,
  meddelande: string | null,
  synlig_for_kund: boolean,
  aktor: string | null
): AdminHandelse => ({ tid: iso(timmar), typ, status, meddelande, synlig_for_kund, aktor });

const BAS = {
  vantar_pa_kund: false,
  testversion_url: null,
  har_bild: false,
  besok_av_admin: false,
  vy: "egen",
  roll: "owner"
};

const START: AdminArende[] = [
  // Ett ärende som CRM:ets synk skapat själv (app/crm/supportrapport.py): ingen användare, bara koder och tal.
  {
    ...BAS,
    id: "00000000-0000-4000-a000-0000000000f8",
    nummer: "F-0008",
    status: "mottagen",
    sida: "/crm/synk",
    gjorde: "Synk från HubSpot (delta)",
    hande: "Körning 7c1e, status completed_with_errors.\nTotalt 240, skapade 3, uppdaterade 221, hoppade 16.\nFelkoder, störst först:\n- telefon_ogiltig: 9\n- orgnr_kontrollsiffra: 4\n- epost_ogiltig: 3",
    vantade: "Att alla poster kom in.",
    created_at: iso(1),
    updated_at: iso(0.4),
    rapportor_user_id: "00000000-0000-4000-b000-0000000000c5",
    rapportor_namn: "Snajp CRM, synken",
    kund_workspace_id: "00000000-0000-4000-c000-000000000001",
    kund_tenant_slug: "exempelbolaget",
    vy: "crm",
    roll: "system",
    handelser: [
      handelse(1, "skapad", "mottagen", null, false, "system"),
      handelse(0.4, "synk", null, "Samma anslutning föll igen i körning 9a40: 12 poster", false, "system")
    ]
  },
  {
    ...BAS,
    id: "00000000-0000-4000-a000-0000000000f1",
    nummer: "F-0007",
    status: "mottagen",
    sida: "/dashboard/leads?vy=korningar",
    gjorde: "Startade en körning med 50 bolag i Västra Götaland.",
    hande: "Körningen stod på 0 av 50 i över en timme och sedan försvann den ur listan.",
    vantade: "Att körningen skulle bli klar eller säga varför den stannade.",
    created_at: iso(2),
    updated_at: iso(2),
    rapportor_user_id: "00000000-0000-4000-b000-000000000001",
    rapportor_namn: "Kim Exempel",
    kund_workspace_id: "00000000-0000-4000-c000-000000000001",
    kund_tenant_slug: "exempelbolaget",
    har_bild: true,
    handelser: [handelse(2, "skapad", "mottagen", null, true, "kund")]
  },
  {
    ...BAS,
    id: "00000000-0000-4000-a000-0000000000f2",
    nummer: "F-0006",
    status: "redo_att_testa",
    vantar_pa_kund: true,
    testversion_url: "https://forhand.example/arende/f-0006",
    sida: "/settings/kunskapsbas",
    gjorde: "Klistrade in en text om vår returpolicy och tryckte Spara.",
    hande: "Texten sparades men rubriken blev tom.",
    vantade: "Att rubriken skulle följa med.",
    created_at: iso(50),
    updated_at: iso(5),
    rapportor_user_id: "00000000-0000-4000-b000-000000000002",
    rapportor_namn: null,
    kund_workspace_id: "00000000-0000-4000-c000-000000000002",
    kund_tenant_slug: "provbygg-vast",
    besok_av_admin: true,
    vy: "kund",
    roll: "owner",
    handelser: [
      handelse(50, "skapad", "mottagen", null, true, "kund"),
      handelse(30, "status", "undersoks", null, true, ADMIN_ANTON),
      handelse(29, "anteckning", null, "Rubriken tappas i kb_skanning när texten saknar radbrytning.", false, ADMIN_ANTON),
      handelse(12, "status", "rattning_pagar", null, true, ADMIN_ANTON),
      handelse(5, "status", "redo_att_testa", "Nu går det att prova i testversionen.", true, ADMIN_ANTON)
    ]
  },
  {
    ...BAS,
    id: "00000000-0000-4000-a000-0000000000f3",
    nummer: "F-0005",
    status: "behover_mer",
    vantar_pa_kund: true,
    sida: "/dashboard/support",
    gjorde: "Öppnade ett ärende i inkorgen.",
    hande: "Sidan blev vit.",
    vantade: "Att ärendet skulle öppnas.",
    created_at: iso(80),
    updated_at: iso(70),
    rapportor_user_id: "00000000-0000-4000-b000-000000000003",
    rapportor_namn: "Alex Prov",
    kund_workspace_id: "00000000-0000-4000-c000-000000000003",
    kund_tenant_slug: "testgolv",
    roll: "member",
    handelser: [
      handelse(80, "skapad", "mottagen", null, true, "kund"),
      handelse(70, "status", "behover_mer", "Vilken webbläsare använde du, och händer det med alla ärenden?", true, ADMIN_SEBBE)
    ]
  },
  {
    ...BAS,
    id: "00000000-0000-4000-a000-0000000000f4",
    nummer: "F-0003",
    status: "stangd",
    sida: "/dashboard/leads",
    gjorde: "Letade efter knappen för att exportera.",
    hande: "Hittade den inte.",
    vantade: "En exportknapp.",
    created_at: iso(200),
    updated_at: iso(190),
    rapportor_user_id: "00000000-0000-4000-b000-000000000001",
    rapportor_namn: "Kim Exempel",
    kund_workspace_id: "00000000-0000-4000-c000-000000000001",
    kund_tenant_slug: "exempelbolaget",
    handelser: [
      handelse(200, "skapad", "mottagen", null, true, "kund"),
      handelse(190, "status", "stangd", "Exporten ligger under Listor, högst upp till höger.", true, ADMIN_ANTON)
    ]
  }
];

const TENANTS = [
  { id: "t1", slug: "exempelbolaget", name: "Exempelbolaget AB", tickets: 12, escalated: 1, runs: 4, tokens_in: 0, tokens_out: 0 },
  { id: "t2", slug: "provbygg-vast", name: "Provbygg Väst AB", tickets: 3, escalated: 0, runs: 2, tokens_in: 0, tokens_out: 0 }
] as unknown as TenantRow[];

const EVENTS: EventRow[] = [
  {
    id: "e1",
    tenant_slug: "exempelbolaget",
    level: "error",
    source: "leads.korning",
    message: "Körningen avbröts: tidsgränsen nåddes.",
    detail: {},
    run_id: null,
    created_at: iso(3)
  }
];

function las(): AdminArende[] {
  try {
    const sparat = window.localStorage.getItem(NYCKEL);
    if (sparat) return JSON.parse(sparat) as AdminArende[];
  } catch {
    // Privat fönster eller blockerat minne: börja från de påhittade.
  }
  return START;
}

function spara(arenden: AdminArende[]) {
  try {
    window.localStorage.setItem(NYCKEL, JSON.stringify(arenden));
  } catch {
    // Utan minne står bytet kvar tills sidan laddas om.
  }
}

function svar(kropp: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } }));
}

/** En liten skärmbild av en körning som står still, ritad som PNG. */
function ritadBild(): string {
  const canvas = document.createElement("canvas");
  canvas.width = 480;
  canvas.height = 200;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";
  ctx.fillStyle = "#f3efe6";
  ctx.fillRect(0, 0, 480, 200);
  ctx.fillStyle = "#ddd5c4";
  ctx.fillRect(24, 40, 432, 24);
  ctx.fillStyle = "#b5651d";
  ctx.fillRect(24, 80, 6, 24);
  ctx.fillStyle = "#333333";
  ctx.font = "16px sans-serif";
  ctx.fillText("0 / 50", 40, 98);
  return canvas.toDataURL("image/png");
}

function installeraFetch(lage: string | null) {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  if (lage === "nollstall") spara(START);
  const riktig = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/admin/plattformsarenden")) return riktig(input, init);
    await new Promise((r) => setTimeout(r, 250));
    if (lage === "fel") return svar({ error: "Backenden svarade inte (förhandsvisning)." }, 502);
    if (lage === "tomt") return svar({ arenden: [] });

    const bildMatch = url.match(/plattformsarenden\/([^/?]+)\/bild/);
    if (bildMatch) {
      if (lage === "bildfel") return svar({ error: "Backenden svarade inte (förhandsvisning)." }, 502);
      const arende = las().find((x) => x.id === decodeURIComponent(bildMatch[1]));
      if (!arende?.har_bild) return svar({ error: "Ärendet har ingen bild." }, 404);
      return svar({ bild: ritadBild() });
    }

    const statusMatch = url.match(/plattformsarenden\/([^/?]+)\/status/);
    if (statusMatch && init?.method === "POST") {
      const kropp = JSON.parse(String(init.body)) as {
        status: Arendestatus;
        meddelande_till_kund: string | null;
        testversion_url: string | null;
      };
      const arenden = las();
      const gammalt = arenden.find((x) => x.id === decodeURIComponent(statusMatch[1]));
      if (!gammalt) return svar({ error: "Hittades inte." }, 404);
      const tid = new Date().toISOString();
      const nya: AdminHandelse[] = [
        { tid, typ: "status", status: kropp.status, meddelande: kropp.meddelande_till_kund, synlig_for_kund: kropp.status !== "i_development", aktor: ADMIN_ANTON }
      ];
      const nytt: AdminArende = {
        ...gammalt,
        status: kropp.status,
        vantar_pa_kund: kropp.status === "behover_mer" || kropp.status === "redo_att_testa",
        testversion_url: kropp.testversion_url ?? gammalt.testversion_url,
        updated_at: tid,
        handelser: [...gammalt.handelser, ...nya]
      };
      spara(arenden.map((x) => (x.id === nytt.id ? nytt : x)));
      return svar(nytt);
    }
    return svar({ arenden: las() });
  };
}

export default function FelrapporterForhandsvisning() {
  const [redo] = useState(() => {
    if (typeof window !== "undefined") installeraFetch(new URLSearchParams(window.location.search).get("lage"));
    return true;
  });
  if (!redo) return null;
  return (
    <main className="appyta mx-auto min-h-dvh max-w-6xl bg-paper px-4 py-10 text-ink sm:px-8">
      <div className="grid min-w-0 items-start gap-4 xl:grid-cols-2">
        <FelOchEskaleringar tenants={TENANTS} events={EVENTS} taketNaddes={false} nu={nu} />
      </div>
    </main>
  );
}
