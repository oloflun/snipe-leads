/**
 * Förhandsvisningens svar för skalet (steg 4.1): leadsnotiserna och Byt kunds
 * kundlista. Samma form som backenden:
 *
 * - `GET  /api/snajp-support/leads/notiser/antal` → `{ olasta }`
 * - `GET  /api/snajp-support/leads/notiser?limit=` → `{ notiser, olasta }`
 *   (snajp-support/app/api/leads_konversationer.py: notiser)
 * - `POST /api/snajp-support/leads/notiser/last` `{ ids? }` → `{ lasta, olasta }`
 * - `GET  /api/admin/kunder` → `{ tenants: [{ slug, name }] }` (app/api/admin/kunder/route.ts)
 *
 * Påhittade bolag, märkta som exempel här och bara här. Markera som lästa ändrar
 * datan, så att räknaren och listan följer med tills sidan laddas om.
 */

type Notis = {
  id: string;
  typ: "svar" | "utkast" | "mote" | "overlamnat";
  tid: string;
  last: boolean;
  thread_id: string | null;
  prospect_id: string;
  company_name: string | null;
  klass: string | null;
  oppnat: boolean;
};

const nu = Date.now();
const iso = (minuter: number) => new Date(nu - minuter * 6e4).toISOString();

// Exempel: inga riktiga bolag.
const NOTISER: Notis[] = [
  { id: "00000000-0000-4000-8000-0000000000a1", typ: "svar", tid: iso(12), last: false, thread_id: "t1", prospect_id: "p1", company_name: "Exempelbolaget AB", klass: "positivt", oppnat: false },
  { id: "00000000-0000-4000-8000-0000000000a2", typ: "utkast", tid: iso(14), last: false, thread_id: "t1", prospect_id: "p1", company_name: "Exempelbolaget AB", klass: null, oppnat: false },
  { id: "00000000-0000-4000-8000-0000000000a3", typ: "mote", tid: iso(95), last: false, thread_id: "t2", prospect_id: "p2", company_name: "Hittepå Bygg AB", klass: null, oppnat: false },
  { id: "00000000-0000-4000-8000-0000000000a4", typ: "utkast", tid: iso(60 * 26), last: true, thread_id: "t3", prospect_id: "p3", company_name: "Låtsas Logistik AB", klass: null, oppnat: true },
  { id: "00000000-0000-4000-8000-0000000000a5", typ: "svar", tid: iso(60 * 50), last: true, thread_id: "t4", prospect_id: "p4", company_name: "Attrapp Energi AB", klass: "fraga", oppnat: false }
];

const KUNDER = [
  { slug: "exempelbolaget", name: "Exempelbolaget AB" },
  { slug: "hittepa-bygg", name: "Hittepå Bygg AB" },
  { slug: "latsas-logistik", name: "Låtsas Logistik AB" },
  { slug: "attrapp-energi", name: "Attrapp Energi AB" },
  { slug: "skissad-verkstad", name: "Skissad Verkstad AB" },
  { slug: "demokontot", name: "Demokontot" }
];

const olasta = () => NOTISER.filter((n) => !n.last).length;

function json(kropp: unknown, status = 200) {
  return new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

/** Svarar på skalets vägar, och `null` för allt annat. */
export function svaraSkalet(url: URL, init?: RequestInit): Promise<Response> | null {
  const metod = (init?.method ?? "GET").toUpperCase();
  const vag = url.pathname;
  const vanta = <T,>(svar: () => T) => new Promise<T>((r) => setTimeout(() => r(svar()), 160));

  if (vag === "/api/snajp-support/leads/notiser/antal" && metod === "GET") {
    return vanta(() => json({ olasta: olasta() }));
  }
  if (vag === "/api/snajp-support/leads/notiser" && metod === "GET") {
    const grans = Math.max(1, Math.min(Number(url.searchParams.get("limit") ?? 30) || 30, 100));
    return vanta(() => json({ notiser: NOTISER.slice(0, grans), olasta: olasta() }));
  }
  if (vag === "/api/snajp-support/leads/notiser/last" && metod === "POST") {
    return vanta(() => {
      const kropp = (() => {
        try {
          return JSON.parse(String(init?.body ?? "{}")) as { ids?: string[] | null };
        } catch {
          return {};
        }
      })();
      let lasta = 0;
      for (const n of NOTISER) {
        if (!n.last && (!kropp.ids || kropp.ids.includes(n.id))) {
          n.last = true;
          lasta++;
        }
      }
      return json({ lasta, olasta: olasta() });
    });
  }
  if (vag === "/api/admin/kunder" && metod === "GET") {
    return vanta(() => json({ tenants: KUNDER }));
  }
  return null;
}
