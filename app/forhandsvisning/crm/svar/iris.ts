/**
 * Förhandsvisningens svar för Iris leads (steg 4.2), i leads-API:ts form:
 *
 * - `GET    /leads/prospects?lista=1[&bortvalda=1|&arkiverade=1]` → `{ prospects, fler, nasta }` (leads.py:list_prospects, listvy.listrad)
 * - `GET    /leads/prospects/{id}` → `{ prospect, sources }`, `.../utkast`, `.../tidslinje`
 * - `PATCH  /leads/prospects/{id}` → `{ prospect }`
 * - `POST   /leads/prospects/arkivera` `{ ids, arkivera }`, `/radera` `{ ids }`, `/processa-om`
 * - `POST   /leads/prospects/{id}/befordra`, `/degradera`, `/samtal`, `/anteckningar`, `/uppgifter`
 * - `PATCH  /leads/uppgifter/{id}`, `GET /leads/uppgifter?oppna=1`, `GET|POST|DELETE /leads/vyer`
 * - `PUT    /leads/queue/{id}`, `POST /leads/queue/{id}/approve`, `/reject`
 * - `POST   /leads/uppfoljningar/skapa`, `PUT /leads/config`
 *
 * Webbgrinden: utan `?webb=1` i sidans adress saknas `webbrevision` i varje svar,
 * som när backenden (webbpool.dolj) döljer bedömningen för en kund. Med `?webb=1`
 * bär raderna den, som hos en webbyrå.
 *
 * Påhittade bolag, personer och adresser (domänen .test, numren 070-174 06 xx),
 * märkta som exempel här och bara här. Skrivningar ändrar datan tills sidan
 * laddas om, så att flödet går att följa.
 */

type Rad = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_role: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  status: string;
  origin: string;
  niva: "A" | "B" | "C" | null;
  qualified: boolean | null;
  score_total: number | null;
  icp_fit: number | null;
  created_at: string;
  senaste_handelse_at: string;
  website: string | null;
  ort: string | null;
  orgnr: string | null;
  sni: string | null;
  anstallda: number | null;
  motivering: string | null;
  disqualifiers: string[] | null;
  arkiverad_at: string | null;
  pafylld: boolean;
  pafylld_skal: string | null;
  webbrevision: { modernitet: number; brister: string[]; layout_era: string; pagespeed: { mobil: { prestanda: number; lcp_s: number } } } | null;
  // Utkastets härledda läge (utkaststatus.harled) och det förhandsvisningen behöver för texten.
  utkast_status: string;
  utkast_skal: string | null;
  queue_item_id: string | null;
  skickas_tidigast: string | null;
  skickat_at: string | null;
  amne: string | null;
  brodtext: string | null;
  /** När ett pågående jobb (research eller utkast) blir klart, i ms sedan epoken. */
  klart_vid: number | null;
  jobb: "research" | "utkast" | null;
};

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();

// Exempel: inga riktiga bolag.
const BOLAG = [
  ["Exempelbolaget AB", "Umeå", "Kim Exempel", "VD"],
  ["Hittepå Bygg AB", "Göteborg", "Robin Prov", "Ägare"],
  ["Låtsas Logistik AB", "Halmstad", null, null],
  ["Attrapp Energi AB", "Luleå", "Alex Test", "Driftchef"],
  ["Skissad Verkstad AB", "Örebro", "Sam Påhittsson", "VD"],
  ["Modellverket AB", "Uppsala", null, null],
  ["Prototyp Livsmedel AB", "Malmö", "Noor Exempeldotter", "Inköpschef"],
  ["Kuliss Event AB", "Stockholm", "Viktor Provström", "VD"],
  ["Övningsbolaget AB", "Umeå", "Elin Testberg", "Ekonomichef"],
  ["Mockup Mode AB", "Göteborg", null, null],
  ["Skenet Konsult AB", "Stockholm", "Jonas Skisslund", "Delägare"],
  ["Testgränd Fastigheter AB", "Uppsala", "Maja Låtsasson", "VD"],
  ["Utkast Arkitekter AB", "Luleå", "Ola Modellén", "Kontorschef"],
  ["Dummy Transport AB", "Halmstad", null, null],
  ["Nordisk Påhitt AB", "Umeå", "Sara Attrappius", "VD"],
  ["Fiktiv Telefoni AB", "Malmö", "Karim Utkastare", "IT-ansvarig"],
  ["Provkörning Media AB", "Örebro", "Linnea Exempelsson", "VD"],
  ["Skenbar Redovisning AB", "Stockholm", "Erik Påhittsdotter", "Ägare"],
  ["Kulissbygg Norr AB", "Luleå", "Anna Provström", "VD"],
  ["Hittepå Måleri AB", "Göteborg", null, null],
  ["Låtsas Café AB", "Uppsala", "Johan Testberg", "Ägare"],
  ["Attrapp Tryck AB", "Umeå", "Kim Skisslund", "VD"],
  ["Modell Städ AB", "Halmstad", "Robin Låtsasson", "VD"],
  ["Exempel Elteknik AB", "Örebro", "Alex Modellén", "Ägare"],
  ["Prototyp Plåt AB", "Malmö", null, null],
  ["Skiss Snickeri AB", "Luleå", "Sam Attrappius", "VD"],
  ["Påhitt Juridik AB", "Stockholm", "Noor Utkastare", "Delägare"],
  ["Övning Bilvård AB", "Göteborg", "Viktor Exempelsson", "VD"],
  ["Dummy Däck AB", "Umeå", "Elin Påhittsdotter", "Ägare"],
  ["Mockup Möbler AB", "Uppsala", null, null],
  ["Fiktiv Frakt AB", "Halmstad", "Jonas Provström", "VD"],
  ["Skenbar Säkerhet AB", "Örebro", "Maja Testberg", "VD"],
  ["Testvägen Måleri AB", "Malmö", "Ola Skisslund", "Ägare"]
] as const;

const MOTIVERINGAR = [
  "Bolaget öppnar ett nytt kontor i vår och söker leverantör för telefoni. Storleken passar er målgrupp.",
  "Växande bolag med tolv anställda och en egen säljavdelning. De nämner kundservice som ett fokusområde.",
  "Familjeföretag i tredje generation med kontor i två städer. Inga tecken på en befintlig leverantör.",
  "Har nyligen anställt en driftchef och annonserar efter fler tekniker.",
  "Passar på bransch och storlek. Webbplatsen beskriver ett behov av bättre kundkontakt.",
  "Bolaget har vuxit snabbt de senaste två åren och har öppnat en ny filial."
];
const BRISTER = ["Liten text i menyn", "Ingen mobilanpassning", "Bilderna laddar långsamt", "Kontaktuppgifter syns inte på startsidan", "Föråldrad layout med tabeller"];

const ascii = (s: string) => s.toLowerCase().replace(/[åä]/g, "a").replace(/ö/g, "o").replace(/é/g, "e").replace(/[^a-z]+/g, "");

function rad(i: number): Rad {
  const [namn, ort, kontakt, roll] = BOLAG[i];
  const doman = `${ascii(namn.replace(/ AB$/, ""))}.test`;
  const utanSajt = i % 11 === 6;
  const status = i === 0 ? "researching" : i % 3 === 0 ? "ready" : "new";
  const niva = i % 4 === 1 ? "B" : "A";
  const bedomd = status !== "researching";
  const harMejl = kontakt !== null || i % 2 === 0;
  const utkast = !bedomd ? "saknas" : i % 7 === 3 ? "stoppat" : i % 5 === 2 ? "saknas" : i % 9 === 4 ? "avvisat" : "vantar";
  const forman = kontakt ? kontakt.split(" ")[0] : null;
  return {
    id: `00000000-0000-4000-8000-${String(100000000000 + i).slice(-12)}`,
    company_name: namn,
    contact_name: kontakt,
    contact_role: roll,
    contact_email: harMejl ? (kontakt ? `${ascii(kontakt.split(" ")[0])}@${doman}` : `info@${doman}`) : null,
    contact_phone: i % 3 === 1 ? `+467017406${String(10 + i).slice(-2)}` : null,
    status,
    origin: i >= 29 ? "test" : i % 6 === 5 ? "lista" : i % 8 === 7 ? "import" : "manual",
    niva: bedomd ? niva : null,
    qualified: bedomd ? true : null,
    score_total: bedomd ? 92 - ((i * 7) % 40) : null,
    icp_fit: null,
    created_at: iso(2 + i * 9),
    senaste_handelse_at: iso(i === 0 ? 0.05 : 1 + i * 7),
    website: utanSajt ? null : `https://${doman}`,
    ort,
    orgnr: `55990${String(10000 + i * 137).slice(-5)}`,
    sni: i % 2 ? "43341" : "62010",
    anstallda: 3 + ((i * 11) % 60),
    motivering: bedomd ? MOTIVERINGAR[i % MOTIVERINGAR.length] : null,
    disqualifiers: null,
    arkiverad_at: null,
    pafylld: i === 14,
    pafylld_skal: i === 14 ? "c" : null,
    webbrevision: utanSajt ? null : { modernitet: 1 + ((i * 3) % 10), brister: [BRISTER[i % BRISTER.length]], layout_era: i % 2 ? "tabeller" : "tidig responsiv", pagespeed: { mobil: { prestanda: 30 + ((i * 13) % 60), lcp_s: 2 + ((i * 7) % 60) / 10 } } },
    utkast_status: utkast,
    utkast_skal: utkast === "stoppat" ? "Mottagarens domän saknar MX-post." : utkast === "avvisat" ? null : null,
    queue_item_id: utkast === "vantar" || utkast === "stoppat" ? `00000000-0000-4000-9000-${String(100000000000 + i).slice(-12)}` : null,
    skickas_tidigast: null,
    skickat_at: null,
    amne: utkast === "saknas" ? null : `Telefonin hos ${namn.replace(/ AB$/, "")}`,
    brodtext:
      utkast === "saknas"
        ? null
        : `Hej${forman ? ` ${forman}` : ""},\n\nJag såg att ni på ${namn.replace(/ AB$/, "")} växer i ${ort}. Många bolag i er storlek samlar växel och mobiler hos en leverantör när de öppnar nya kontor.\n\nVill du att jag skickar ett förslag som passar er?`,
    klart_vid: i === 0 ? nu + 15_000 : null,
    jobb: i === 0 ? "research" : null
  };
}

const RADER: Rad[] = Array.from({ length: BOLAG.length }, (_, i) => rad(i));
// Kontaktade: står inte i Att bearbeta (de bor under Skickat), men syns i bolagets panel och sök.
for (const i of [8, 16]) Object.assign(RADER[i], { status: "contacted", utkast_status: "skickat", skickat_at: iso(30 + i), queue_item_id: null });
// Ett godkänt utkast väntar på sändfönstret: det räknas som skickat för kunden och står inte i listan.
Object.assign(RADER[10], { utkast_status: "godkant", skickas_tidigast: new Date(nu + 15 * 36e5).toISOString() });
// Bortvalda (nivå C, LR-050).
for (const i of [19, 22, 25]) {
  Object.assign(RADER[i], { niva: "C", qualified: false, score_total: 22 + i, disqualifiers: ["Enskild firma utan anställda.", "Ingen webbplats som bär en kontaktväg."], motivering: "Uppfyller inte kravet på storlek." });
}
// Arkiverade (LR-051).
for (const i of [12, 27]) Object.assign(RADER[i], { arkiverad_at: iso(20 + i) });

const TIDSLINJE: Record<string, { typ: string; nar: string; rubrik: string; text: string | null; id: string | null; klar: boolean | null }[]> = {};
const UPPGIFTER: { id: string; prospect_id: string; titel: string; forfaller: string | null; klar: boolean }[] = [
  { id: "00000000-0000-4000-a000-000000000001", prospect_id: RADER[3].id, titel: "Ring och fråga om växeln", forfaller: new Date(nu + 2 * 864e5).toISOString().slice(0, 10), klar: false },
  { id: "00000000-0000-4000-a000-000000000002", prospect_id: RADER[5].id, titel: "Skicka referenskunder", forfaller: new Date(nu - 864e5).toISOString().slice(0, 10), klar: false }
];
let VYER: { id: string; namn: string; filter: Record<string, string>; created_at: string }[] = [
  { id: "00000000-0000-4000-b000-000000000001", namn: "Starka i Umeå", filter: { niva: "A", sok: "" }, created_at: iso(200) }
];
let lopnr = 1000;
const nyttId = (serie: string) => `00000000-0000-4000-${serie}-${String(100000000000 + lopnr++).slice(-12)}`;

/** Den förvalda tidslinjen för ett lead, nyast först. */
function tidslinje(r: Rad) {
  const egna = TIDSLINJE[r.id] ?? [];
  const bas = [
    ...(r.skickat_at ? [{ typ: "mejl_ut", nar: r.skickat_at, rubrik: r.amne ?? "", text: (r.brodtext ?? "").slice(0, 200), id: `m-${r.id}`, klar: null }] : []),
    ...(r.status !== "new" && r.status !== "researching" ? [{ typ: "status", nar: r.senaste_handelse_at, rubrik: `new → ${r.status}`, text: null, id: `s-${r.id}`, klar: null }] : []),
    ...UPPGIFTER.filter((u) => u.prospect_id === r.id).map((u) => ({ typ: "uppgift", nar: iso(5), rubrik: u.titel, text: u.forfaller, id: u.id, klar: u.klar })),
    { typ: "skapad", nar: r.created_at, rubrik: r.company_name, text: null, id: null, klar: null }
  ];
  return [...egna, ...bas].sort((a, b) => (a.nar < b.nar ? 1 : -1));
}

/** Gör färdigt ett jobb som hunnit bli klart (research eller utkast), som jobbkön hade gjort. */
function framat() {
  for (const r of RADER) {
    if (!r.klart_vid || r.klart_vid > Date.now()) continue;
    if (r.jobb === "research") {
      Object.assign(r, { status: "new", niva: "A", qualified: true, score_total: 81, motivering: MOTIVERINGAR[0], senaste_handelse_at: new Date().toISOString() });
    }
    if (r.jobb === "research" || r.jobb === "utkast") {
      const forman = r.contact_name?.split(" ")[0];
      Object.assign(r, {
        utkast_status: "vantar",
        utkast_skal: null,
        queue_item_id: nyttId("9000"),
        amne: `Telefonin hos ${r.company_name.replace(/ AB$/, "")}`,
        brodtext: `Hej${forman ? ` ${forman}` : ""},\n\nJag läste om ${r.company_name.replace(/ AB$/, "")} och er nya satsning i ${r.ort}. Får jag visa hur andra i er storlek samlat telefonin?\n\nKan det vara intressant?`
      });
    }
    r.klart_vid = null;
    r.jobb = null;
  }
}

const webbSynlig = () => typeof window !== "undefined" && new URLSearchParams(window.location.search).get("webb") === "1";

/** Det listläget bär per rad (listvy.listrad): tomma fält utelämnas, bedömningen bara när den får synas. */
function listrad(r: Rad): Record<string, unknown> {
  const ut: Record<string, unknown> = {};
  const status = r.jobb === "research" ? "researching" : r.status;
  const fullt: Record<string, unknown> = {
    id: r.id,
    company_name: r.company_name,
    contact_name: r.contact_name,
    contact_email: r.contact_email,
    contact_phone: r.contact_phone,
    status,
    origin: r.origin,
    niva: r.niva,
    score_total: r.score_total,
    icp_fit: r.icp_fit,
    created_at: r.created_at,
    website: r.website,
    ort: r.ort,
    arkiverad_at: r.arkiverad_at,
    pafylld: r.pafylld || null,
    pafylld_skal: r.pafylld_skal,
    utkast_status: r.jobb === "utkast" ? "skrivs" : r.utkast_status,
    utkast_skal: r.utkast_skal,
    queue_item_id: r.queue_item_id,
    skickas_tidigast: r.skickas_tidigast,
    skickat_at: r.skickat_at,
    senaste_handelse_at: r.senaste_handelse_at
  };
  for (const [k, v] of Object.entries(fullt)) if (v != null) ut[k] = v;
  if (r.motivering) ut.motivering = r.motivering.split(/(?<=[.!?])\s/)[0];
  if (r.disqualifiers?.length) ut.disqualifiers = [r.disqualifiers[0]];
  if (webbSynlig() && r.webbrevision) ut.webbrevision = { modernitet: r.webbrevision.modernitet, brister: r.webbrevision.brister.slice(0, 1) };
  return ut;
}

/** Hela prospektet (get_prospect): webbfälten bara när de får synas. */
function heltProspekt(r: Rad): Record<string, unknown> {
  const { amne: _a, brodtext: _b, klart_vid: _k, jobb, webbrevision, ...resten } = r;
  return {
    ...resten,
    status: jobb === "research" ? "researching" : r.status,
    utkast_status: jobb === "utkast" ? "skrivs" : r.utkast_status,
    score_breakdown: r.niva
      ? [
          { etikett: "Storlek", utfall: "träff", motivering: `${r.anstallda} anställda, inom er gräns.`, hart: true, belagg: [{ url: r.website ?? "https://exempel.test", citat: `Vi är ${r.anstallda} medarbetare` }] }, // inte-copy: fixturens utfallsnyckel
          { etikett: "Bransch", utfall: r.niva === "C" ? "miss" : "träff", motivering: "Branschen passar det ni säljer.", hart: true }, // inte-copy: fixturens utfallsnyckel
          { etikett: "Behov", utfall: r.niva === "B" ? "delvis" : "träff", motivering: "Nämner kundkontakt som ett fokusområde.", hart: false } // inte-copy: fixturens utfallsnyckel
        ]
      : [],
    jev: r.niva ? { triage: { fit: r.niva === "A" ? 2.6 : 1.8, skulle_falla: r.niva === "C", fall_skal: r.niva === "C" ? ["för litet"] : [], stodrad: "Vi växer och söker fler kollegor." }, klassning: { sannolikhet: r.niva === "A" ? 0.71 : 0.44, trafikniva: r.niva === "A" ? "hog" : "medel" } } : null,
    ...(webbSynlig() && webbrevision ? { webbrevision, webbniva: webbrevision.modernitet <= 2 ? "akut" : webbrevision.modernitet <= 5 ? "dalig" : webbrevision.modernitet <= 8 ? "bra" : "mycket_bra" } : {})
  };
}

function json(kropp: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

const synlig = (r: Rad, bortvalda: boolean, arkiverade: boolean) => {
  if (Boolean(r.arkiverad_at) !== arkiverade) return false;
  if (arkiverade) return true;
  const bortvald = (r.niva === "C" || r.qualified === false) && !r.pafylld;
  return bortvald === bortvalda;
};

/** Svarar på Iris-vägarna, och `null` för allt annat. */
export function svaraIris(url: URL, init?: RequestInit): Promise<Response> | null {
  const vag = url.pathname;
  if (!vag.startsWith("/api/snajp-support/leads/")) return null;
  const v = vag.replace("/api/snajp-support/leads", "");
  const metod = (init?.method ?? "GET").toUpperCase();
  const kropp = (() => {
    try {
      return typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  })();
  const vanta = (svar: () => Response) => new Promise<Response>((r) => setTimeout(() => r(svar()), 160));
  framat();
  const hitta = (id: string) => RADER.find((r) => r.id === id);
  const saknas = () => json({ detail: "Prospektet finns inte." }, 404);

  if (v === "/prospects" && metod === "GET") {
    return vanta(() => {
      const bort = url.searchParams.get("bortvalda") === "1";
      const ark = url.searchParams.get("arkiverade") === "1";
      return json({ prospects: RADER.filter((r) => synlig(r, bort, ark)).map(listrad), fler: false, nasta: RADER.length });
    });
  }
  if (v === "/uppgifter" && metod === "GET") return vanta(() => json({ uppgifter: UPPGIFTER.filter((u) => !u.klar) }));
  if (v === "/vyer" && metod === "GET") return vanta(() => json({ vyer: VYER }));
  if (v === "/vyer" && metod === "POST") {
    return vanta(() => {
      const namn = String(kropp.namn ?? "").trim();
      if (!namn) return json({ detail: "Vyn saknar namn." }, 422);
      const ny = { id: nyttId("b000"), namn, filter: (kropp.filter ?? {}) as Record<string, string>, created_at: new Date().toISOString() };
      VYER = [...VYER, ny];
      return json({ vy: ny }, 201);
    });
  }
  const vy = v.match(/^\/vyer\/([^/]+)$/);
  if (vy && metod === "DELETE") {
    return vanta(() => {
      VYER = VYER.filter((x) => x.id !== vy[1]);
      return json(null, 204);
    });
  }
  if (v === "/prospects/arkivera" && metod === "POST") {
    return vanta(() => {
      const ids = (kropp.ids as string[]) ?? [];
      const arkivera = kropp.arkivera !== false;
      let installda = 0;
      const traffar = RADER.filter((r) => ids.includes(r.id));
      for (const r of traffar) {
        r.arkiverad_at = arkivera ? new Date().toISOString() : null;
        if (arkivera && (r.utkast_status === "vantar" || r.utkast_status === "godkant")) {
          r.utkast_status = "avvisat";
          r.queue_item_id = null;
          installda++;
        }
      }
      return json({ ids: traffar.map((r) => r.id), arkiverad: arkivera, installda_utskick: installda });
    });
  }
  if (v === "/prospects/radera" && metod === "POST") {
    return vanta(() => {
      const ids = (kropp.ids as string[]) ?? [];
      const raderade: string[] = [];
      const vagrade: { id: string; skal: string }[] = [];
      for (const id of ids) {
        const r = hitta(id);
        if (!r) vagrade.push({ id, skal: "finns_inte" });
        else if (r.skickat_at) vagrade.push({ id, skal: "kontaktad" });
        else {
          RADER.splice(RADER.indexOf(r), 1);
          raderade.push(id);
        }
      }
      return json({ raderade, vagrade });
    });
  }
  if (v === "/prospects/processa-om" && metod === "POST") {
    return vanta(() => {
      const ids = [...new Set((kropp.prospect_ids as string[]) ?? [])];
      const scope = String(kropp.scope ?? "research_and_draft");
      const hittade = ids.map(hitta).filter((r): r is Rad => Boolean(r));
      if (!hittade.length) return json({ detail: "Inga av de valda prospekten finns." }, 404);
      const pagar = hittade.filter((r) => r.jobb).map((r) => r.id);
      const hoppade = scope === "utkast" || kropp.ersatt ? hittade.filter((r) => r.skickat_at && !r.jobb).map((r) => r.id) : [];
      const koa = hittade.filter((r) => !pagar.includes(r.id) && !hoppade.includes(r.id));
      for (const [n, r] of koa.entries()) {
        r.jobb = scope === "utkast" ? "utkast" : "research";
        r.klart_vid = Date.now() + 6000 + n * 1500;
        if (r.jobb === "utkast") r.queue_item_id = null;
      }
      return json({ jobs: koa.map((r) => ({ job_id: nyttId("c000"), prospect_id: r.id })), scope, count: koa.length, fase: scope === "utkast" ? "skriver" : "research", hoppade_over: hoppade, pagar_redan: pagar }, 202);
    });
  }
  if (v === "/uppfoljningar/skapa" && metod === "POST") {
    return vanta(() => {
      const ids = (kropp.prospect_ids as string[]) ?? [];
      const skickade = ids.filter((id) => hitta(id)?.skickat_at);
      return json({ count: skickade.length, hoppade: { inget_skickat: ids.filter((id) => !skickade.includes(id)) } });
    });
  }
  if (v === "/config" && metod === "PUT") return vanta(() => json({ ok: true, autonomy: kropp.autonomy }));

  const uppgift = v.match(/^\/uppgifter\/([^/]+)$/);
  if (uppgift && metod === "PATCH") {
    return vanta(() => {
      const u = UPPGIFTER.find((x) => x.id === uppgift[1]);
      if (!u) return json({ detail: "Uppgiften finns inte." }, 404);
      u.klar = kropp.klar === true;
      return json({ uppgift: u });
    });
  }

  const ko = v.match(/^\/queue\/([^/]+)(\/approve|\/reject)?$/);
  if (ko) {
    const r = RADER.find((x) => x.queue_item_id === ko[1]);
    if (!r) return vanta(() => json({ detail: "Utkastet finns inte." }, 404));
    if (metod === "PUT" && !ko[2]) {
      return vanta(() => {
        const amne = String(kropp.subject ?? "").trim();
        const text = String(kropp.brodtext ?? "").trim();
        if (!amne || !text) return json({ detail: "Ämnesrad och text får inte vara tomma." }, 422);
        Object.assign(r, { amne, brodtext: text });
        return json({ id: ko[1], subject: amne });
      });
    }
    if (ko[2] === "/approve" && metod === "POST") {
      return vanta(() => {
        if (r.utkast_status === "stoppat") return json({ id: ko[1], status: "blocked", utfall: "blocked", besked: `Stoppat av en sändspärr: ${r.utkast_skal}`, skal: r.utkast_skal });
        Object.assign(r, { utkast_status: "godkant", skickas_tidigast: new Date(nu + 15 * 36e5).toISOString() });
        return json({ id: ko[1], status: "queued", utfall: "requeued", besked: "Godkänt. Mejlet skickas i tur och ordning från kön, vardagar från 08:00.", skal: null });
      });
    }
    if (ko[2] === "/reject" && metod === "POST") {
      return vanta(() => {
        if (!["vantar", "godkant", "koad"].includes(r.utkast_status)) return json({ detail: "Utkastet är redan hanterat." }, 409);
        Object.assign(r, { utkast_status: "avvisat", queue_item_id: null });
        return json({ id: ko[1], status: "cancelled" });
      });
    }
  }

  const post = v.match(/^\/prospects\/([^/]+)(?:\/(utkast|tidslinje|befordra|degradera|samtal|anteckningar|uppgifter))?$/);
  if (post) {
    const r = hitta(post[1]);
    const del = post[2];
    if (!r) return vanta(saknas);
    if (!del && metod === "GET") return vanta(() => json({ prospect: heltProspekt(r), sources: r.website ? [r.website, `${r.website}/om-oss`] : [] }));
    if (!del && metod === "PATCH") {
      return vanta(() => {
        if ("status" in kropp) {
          const forra = r.status;
          r.status = String(kropp.status);
          r.senaste_handelse_at = new Date().toISOString();
          (TIDSLINJE[r.id] ??= []).unshift({ typ: "status", nar: r.senaste_handelse_at, rubrik: `${forra} → ${r.status}`, text: null, id: nyttId("d000"), klar: null });
        }
        if ("qualified" in kropp) r.qualified = kropp.qualified as boolean;
        return json({ prospect: heltProspekt(r) });
      });
    }
    if (del === "utkast") {
      return vanta(() => {
        const status = r.jobb === "utkast" ? "skrivs" : r.utkast_status;
        const bas = { utkast_status: status, utkast_skal: r.utkast_skal, queue_item_id: r.queue_item_id, skickas_tidigast: r.skickas_tidigast, skickat_at: r.skickat_at, utkast_regel: null };
        if (!r.brodtext || r.jobb === "utkast") return json({ utkast: null, thread_id: null, ...bas });
        const svans = "Med vänliga hälsningar\nKim Exempel\nExempelbolaget AB\n\nExempelbolaget AB, 559900-0000, Exempelgatan 1, 901 00 Umeå. Vill du inte få fler mejl? Svara Avregistrera.";
        return json({ utkast: { id: nyttId("e000"), subject: r.amne, body: `${r.brodtext}\n\n${svans}`, brodtext: r.brodtext, svans }, thread_id: nyttId("f000"), signatur: { text: "Kim Exempel\nExempelbolaget AB" }, ...bas });
      });
    }
    if (del === "tidslinje") return vanta(() => json({ handelser: tidslinje(r) }));
    if (del === "anteckningar" && metod === "POST") {
      return vanta(() => {
        const text = String(kropp.text ?? "").trim();
        if (!text) return json({ detail: "Anteckningen är tom." }, 422);
        const h = { typ: "anteckning", nar: new Date().toISOString(), rubrik: "", text, id: nyttId("d000"), klar: null };
        (TIDSLINJE[r.id] ??= []).unshift(h);
        return json({ anteckning: { id: h.id, text } }, 201);
      });
    }
    if (del === "uppgifter" && metod === "POST") {
      return vanta(() => {
        const titel = String(kropp.titel ?? "").trim();
        if (!titel) return json({ detail: "Uppgiften saknar titel." }, 422);
        const u = { id: nyttId("a000"), prospect_id: r.id, titel, forfaller: (kropp.forfaller as string | null) ?? null, klar: false };
        UPPGIFTER.push(u);
        return json({ uppgift: u }, 201);
      });
    }
    if (del === "samtal" && metod === "POST") {
      return vanta(() => {
        const utfall = String(kropp.utfall ?? "");
        if (utfall === "kontakta_inte") Object.assign(r, { status: "suppressed", utkast_status: r.utkast_status === "vantar" ? "avvisat" : r.utkast_status, queue_item_id: null });
        (TIDSLINJE[r.id] ??= []).unshift({ typ: "samtal", nar: new Date().toISOString(), rubrik: utfall, text: (kropp.anteckning as string) ?? null, id: nyttId("d000"), klar: null });
        return json({ samtal: { id: nyttId("d000"), utfall } }, 201);
      });
    }
    if (del === "degradera" && metod === "POST") {
      return vanta(() => {
        const andrad = r.origin !== "test" && r.origin !== "example";
        if (andrad) r.origin = "test";
        return json({ prospect: heltProspekt(r), andrad });
      });
    }
    if (del === "befordra" && metod === "POST") {
      return vanta(() => {
        if (r.origin !== "test" && r.origin !== "example") return json({ prospect: heltProspekt(r), andrad: false });
        Object.assign(r, Object.fromEntries(Object.entries({ orgnr: kropp.orgnr, website: kropp.website, contact_email: kropp.contact_email }).filter(([, x]) => x)));
        const brister = [!r.website ? "website" : null, !r.contact_email ? "contact_email" : null].filter(Boolean);
        if (brister.length) return json({ detail: { message: "Prospektet saknar det som krävs för att flyttas över.", saknas: brister } }, 422);
        r.origin = "manual";
        return json({ prospect: heltProspekt(r), andrad: true, orgnr_hamtat: false });
      });
    }
  }
  return null;
}
