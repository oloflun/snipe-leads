/**
 * Förhandsvisningens svar för Iris körningar (steg 4.4), i leads-API:ts form:
 *
 * - `GET  /leads/korningar?limit=` → `{ korningar }`, sammandraget (listvy.korning_sammandrag: `tratt_antal`, `jobs_antal`)
 * - `GET  /leads/korningar/{id}` → en körning med tratt och barnjobb, 404 `Körningen finns inte.`
 * - `POST /leads/korningar/{id}/pausa|aterupta|avbryt|fortsatt` (leads.py:styr_korning, 409-texterna)
 * - `GET  /leads/korningar/{id}/utkast` → `{ leads, antal, signatur }` (leads.py:_korningens_leads)
 * - `POST /leads/korningar/{id}/utkast/skriv` (202 `{ count, jobs }`), `/utkast/skicka-jobb` (202 `{ job_id, pagar }`)
 * - `POST /leads/runs/batch` (202 `fase: soker`, pydantic-422 med `loc`, storleksfelet som text)
 * - `GET  /leads/jobb/{id}`: sökjobbet, egna bolags researchjobb och utskicket med `forlopp`
 *
 * Leadsen är samma påhittade bolag som Iris leads och utkast (svar/iris.ts), så att
 * ett godkännande här syns i Utkast och i leadets panel. Den pågående körningen
 * rör sig av sig själv medan sidan är öppen. Bortvalda bolag och skäl är påhittade
 * (domänen .test), märkta som exempel här och bara här. Skrivningar ändrar datan
 * tills sidan laddas om.
 */
import { RADER, framat, type Rad } from "./iris";

type Tratt = { namn: string; steg: string; skal: string; belagg?: string | null };
type Korning = Record<string, unknown> & { mal: number; levererade: number; undersokta: number; pagaende: number; klar: boolean; tratt: Tratt[]; jobs: { job_id: string; prospect_id: string; company_name: string }[] };
type Liggarrad = { job_id: string; status: string; scope: string; is_test: boolean; created_at: string; updated_at: string; completed_at: string | null; error: string | null; korning: Korning | null };

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();
let lopnr = 500;
const nyttId = () => `00000000-0000-4000-7000-${String(100000000000 + lopnr++).slice(-12)}`;

// Exempel: påhittade bolag som valdes bort, med steget och skälet som motorn skriver dem.
const BORTVALDA: [string, string, string, string | null][] = [
  ["Låtsasbygget i Norr AB", "register", "Storlek 1 anställd, er gräns är minst 5.", null],
  ["Exempelfrakt Syd AB", "förfilter", "Utanför målområdet: ligger i Malmö.", null],
  ["Prov & Partner HB", "jev", "Bemanningsbolag, ni undviker bemanning.", "Vi hyr ut personal till industrin."],
  ["Skissade Lösningar AB", "existens", "Sajten bär inte bolagets namn.", null],
  ["Attrappgruppen AB", "research", "Under tröskeln: träffsäkerhet 41 av 60 krävda.", null],
  ["Fiktivia Konsult AB", "research", "Ingen kontaktmejl till bolaget.", null],
  ["Mockupstudion AB", "listspår", "Bara telefon: till ringlistan.", null],
  ["Hittepå Maskin AB", "dubblett", "Finns redan: bolaget står redan i en lista eller som lead.", null],
  ["Kulisskontoret AB", "jev", "Offentlig verksamhet, utesluts.", "Kommunens servicekontor."],
  ["Testbolaget Öst AB", "register", "Branschen ingår inte i målgruppen.", null],
  ["Exempelverkstan AB", "förfilter", "Storlek 240 anställda, er gräns är högst 50.", null],
  ["Låtsasdata AB", "research", "Uppfyller inte målgruppens kriterier.", null],
  ["Provhuset AB", "existens", "Ingen sajt svarade.", null],
  ["Modellbolaget Väst AB", "register", "Avregistrerat i registret.", null]
];
const tratt = (antal: number, fran = 0): Tratt[] =>
  Array.from({ length: antal }, (_, i) => {
    const [namn, steg, skal, belagg] = BORTVALDA[(fran + i) % BORTVALDA.length];
    const varv = Math.floor((fran + i) / BORTVALDA.length);
    return { namn: varv ? namn.replace(" AB", ` ${varv + 1} AB`) : namn, steg, skal, belagg };
  });
const jobb = (index: number[]) => index.map((i) => ({ job_id: nyttId(), prospect_id: RADER[i].id, company_name: RADER[i].company_name }));

function korning(k: Partial<Korning> & { mal: number }): Korning {
  return { levererade: 0, undersokta: 0, pagaende: 0, rundor: 0, tak: k.mal * 12, klar: false, slut_orsak: null, flaskhals: null, sammanfattning: null, scope: "research_and_draft", struktur: "a", overrides: null, is_test: false, tratt: [], jobs: [], styrning: null, ...k } as Korning;
}

/** Den pågående körningen rör sig av sig själv: ett lead var åttonde sekund. */
let paborjad = Date.now();
const LIGGAREN: Liggarrad[] = [
  {
    job_id: "00000000-0000-4000-7000-000000000001",
    status: "processing",
    scope: "batch",
    is_test: false,
    created_at: iso(0.4),
    updated_at: iso(0.01),
    completed_at: null,
    error: null,
    korning: korning({ mal: 10, levererade: 4, undersokta: 23, pagaende: 2, rundor: 3, overrides: { geography: ["Umeå", "Luleå"], anstallda_min: 5 }, tratt: tratt(9), jobs: jobb([1, 3, 6, 9, 11, 0]) })
  },
  {
    job_id: "00000000-0000-4000-7000-000000000002",
    status: "processing",
    scope: "batch",
    is_test: false,
    created_at: iso(30),
    updated_at: iso(6),
    completed_at: null,
    error: null,
    korning: korning({ mal: 8, levererade: 5, undersokta: 96, rundor: 12, struktur: "b", vilande: { sedan: iso(6), skal: "registret" }, overrides: { industries: ["Bygg", "Fastighet"] }, tratt: tratt(41, 3), jobs: jobb([17, 18, 21, 24, 26]) })
  },
  {
    job_id: "00000000-0000-4000-7000-000000000003",
    status: "completed",
    scope: "batch",
    is_test: false,
    created_at: iso(52),
    updated_at: iso(50),
    completed_at: iso(50),
    error: null,
    korning: korning({
      mal: 5,
      levererade: 5,
      undersokta: 18,
      rundor: 4,
      klar: true,
      slut_orsak: "klar",
      sammanfattning: "18 undersökta, 13 bortvalda: utanför målområdet, fel storlek, ingen kontaktmejl → 5 Iris-leads, 2 till ringlistan, 1 ej kvalificerad. 41 betalda sidhämtningar, 12 ur cachen.",
      tratt: tratt(13, 1),
      jobs: jobb([2, 5, 13, 14, 15])
    })
  },
  {
    job_id: "00000000-0000-4000-7000-000000000004",
    status: "completed",
    scope: "batch",
    is_test: false,
    created_at: iso(170),
    updated_at: iso(168),
    completed_at: iso(168),
    error: null,
    korning: korning({
      mal: 6,
      levererade: 3,
      undersokta: 40,
      rundor: 9,
      klar: true,
      slut_orsak: "slut_pa_kandidater",
      flaskhals: "Utanför målområdet",
      sammanfattning: "40 undersökta, 37 bortvalda: utanför målområdet, fel storlek → 3 Iris-leads, 4 till ringlistan. Det som strypte mest: utanför målområdet. 88 betalda sidhämtningar, 30 ur cachen.",
      overrides: { geography: ["Kiruna"], roles: ["VD"] },
      tratt: tratt(37, 5),
      jobs: jobb([4, 7, 30, 32])
    })
  },
  {
    job_id: "00000000-0000-4000-7000-000000000005",
    status: "failed",
    scope: "batch",
    is_test: false,
    created_at: iso(200),
    updated_at: iso(199),
    completed_at: iso(199),
    error: "Körningen avbröts innan den blev klar, troligen av en omstart hos oss, och har markerats som misslyckad. Kör om den.",
    korning: korning({ mal: 4, levererade: 0, undersokta: 2, rundor: 1, tratt: tratt(2, 8) })
  },
  // Egna bolag: sökjobbet lade ett researchjobb per bolag och raden har inget motortillstånd (leads.py:_run_batch).
  { job_id: "00000000-0000-4000-7000-000000000009", status: "completed", scope: "batch", is_test: false, created_at: iso(220), updated_at: iso(219), completed_at: iso(219), error: null, korning: null },
  { job_id: "00000000-0000-4000-7000-000000000006", status: "completed", scope: "lista", is_test: false, created_at: iso(240), updated_at: iso(239), completed_at: iso(239), error: null, korning: null },
  {
    job_id: "00000000-0000-4000-7000-000000000007",
    status: "completed",
    scope: "batch",
    is_test: true,
    created_at: iso(300),
    updated_at: iso(299),
    completed_at: iso(299),
    error: null,
    korning: korning({ mal: 2, levererade: 2, undersokta: 6, rundor: 1, klar: true, slut_orsak: "klar", scope: "research", is_test: true, sammanfattning: "6 undersökta, 4 bortvalda: fel storlek → 2 Iris-leads.", tratt: tratt(4, 9), jobs: jobb([29, 31]) })
  },
  {
    job_id: "00000000-0000-4000-7000-000000000008",
    status: "completed",
    scope: "batch",
    is_test: false,
    created_at: iso(320),
    updated_at: iso(319),
    completed_at: iso(319),
    error: null,
    korning: korning({ mal: 20, levererade: 2, undersokta: 11, rundor: 2, klar: true, slut_orsak: "avbruten", styrning: "avbruten", sammanfattning: "11 undersökta, 9 bortvalda → 2 Iris-leads. Avbruten av er.", tratt: tratt(9, 2), jobs: jobb([28, 20]) })
  }
];

/** Jobben `GET /leads/jobb/{id}` svarar för: sökjobb, researchjobb och utskick. */
type Jobb = { klart: number; status?: "failed"; error?: string; result: () => Record<string, unknown>; forlopp?: { klara: number; totalt: number }; steg?: () => void };
const JOBB = new Map<string, Jobb>();

const STOPP = new Set(["Fiktiv Telefoni AB", "Kuliss Event AB"]);
const SIGNATUR = {
  namn: "Kim Exempel",
  titel: "Säljansvarig",
  text: "Kim Exempel\nSäljansvarig\nExempelbolaget AB | Telefoni för företag\n070-174 06 01\nkim@exempelbolaget.test\n\nUmeå\nexempelbolaget.test\nExempelbolaget AB"
};

function json(kropp: unknown, status = 200) {
  return new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

/** Den pågående körningen tar ett steg för varje åtta sekunder sedan förra hämtningen. */
function rora() {
  for (const r of LIGGAREN) {
    const k = r.korning;
    if (!k || k.klar || r.status === "failed" || k.vilande) continue;
    const steg = Math.floor((Date.now() - paborjad) / 8000);
    if (steg < 1) continue;
    if (k.styrning === "avbruten") {
      Object.assign(k, { klar: true, slut_orsak: "avbruten", pagaende: 0, sammanfattning: `${k.undersokta} undersökta, ${k.tratt.length} bortvalda → ${k.levererade} Iris-leads. Avbruten av er.` });
      Object.assign(r, { status: "completed", completed_at: new Date().toISOString(), updated_at: new Date().toISOString() });
      continue;
    }
    if (k.styrning === "paus") continue;
    k.levererade = Math.min(k.mal, k.levererade + steg);
    k.undersokta += steg * 3;
    k.rundor = (k.rundor as number) + 1;
    k.tratt.push(...tratt(steg * 2, k.tratt.length));
    r.updated_at = new Date().toISOString();
    if (k.levererade >= k.mal) {
      Object.assign(k, {
        klar: true,
        pagaende: 0,
        slut_orsak: "klar",
        sammanfattning: `${k.undersokta} undersökta, ${k.tratt.length} bortvalda: utanför målområdet, fel storlek → ${k.levererade} Iris-leads, 3 till ringlistan. 64 betalda sidhämtningar, 20 ur cachen.`
      });
      Object.assign(r, { status: "completed", completed_at: r.updated_at });
    }
  }
  paborjad = Date.now() - ((Date.now() - paborjad) % 8000);
}

const utanListor = (k: Korning | null) => {
  if (!k) return k;
  const { tratt: t, jobs: j, ...resten } = k;
  return { ...resten, tratt_antal: t.length, jobs_antal: j.length };
};

/** Körningens leads som backenden härleder dem: bortvalda i researchen (nivå C utan utkast) står inte här. */
function leadsFor(k: Korning) {
  const leads = k.jobs
    .map((j) => RADER.find((r) => r.id === j.prospect_id))
    .filter((r): r is Rad => Boolean(r) && !(r!.niva === "C" && r!.utkast_status === "saknas"))
    .map((r) => {
      const skrivs = r.jobb != null;
      const status = skrivs ? "saknas" : r.utkast_status === "skrivs" ? "saknas" : r.utkast_status;
      const kanMejlas = Boolean(r.contact_email) && !skrivs;
      return {
        prospect_id: r.id,
        company_name: r.company_name,
        contact_email: r.contact_email,
        kan_mejlas: kanMejlas,
        status,
        queue_item_id: status === "vantar" ? r.queue_item_id : null,
        skal: r.utkast_skal,
        skickas_tidigast: r.skickas_tidigast,
        subject: r.amne,
        body: r.brodtext,
        notis: status === "saknas" ? (skrivs ? (r.jobb === "research" ? "Researchen pågår." : "Iris skriver utkastet nu.") : r.contact_email ? "Inget utkast skrevs i körningen." : "Inget arbetsmejl hittades på bolagets sajt.") : null
      };
    });
  const antal: Record<string, number> = {};
  for (const l of leads) antal[l.status] = (antal[l.status] ?? 0) + 1;
  antal.kan_skrivas = leads.filter((l) => l.status === "saknas" && l.kan_mejlas).length;
  return { leads, antal };
}

/** Svarar på körningarnas vägar, och `null` för allt annat. */
export function svaraKorningar(url: URL, init?: RequestInit): Promise<Response> | null {
  const vag = url.pathname;
  if (!vag.startsWith("/api/snajp-support/leads/")) return null;
  const v = vag.replace("/api/snajp-support/leads", "");
  if (!v.startsWith("/korningar") && v !== "/runs/batch" && !v.startsWith("/jobb/")) return null;
  const metod = (init?.method ?? "GET").toUpperCase();
  const kropp = (() => {
    try {
      return typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  })();
  const vanta = (svar: () => Response, ms = 220) => new Promise<Response>((r) => setTimeout(() => r(svar()), ms));
  framat();
  rora();

  if (v === "/korningar" && metod === "GET") {
    const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit") ?? 20)));
    return vanta(() => json({ korningar: LIGGAREN.slice(0, limit).map((r) => ({ ...r, korning: utanListor(r.korning) })) }));
  }

  // Starten: 202 innan sökningen, sökjobbet blir klart efter några sekunder.
  if (v === "/runs/batch" && metod === "POST") {
    return vanta(() => {
      const limit = Number(kropp.limit);
      if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
        return json({ detail: [{ loc: ["body", "limit"], msg: "Antal leads måste vara mellan 1 och 200.", type: "value_error" }] }, 422);
      }
      const namn = (kropp.company_names as string[] | undefined) ?? [];
      if (namn.length > 50) return json({ detail: [{ loc: ["body", "company_names"], msg: "Högst 50 bolag per körning.", type: "value_error" }] }, 422);
      const o = (kropp.overrides ?? null) as Record<string, unknown> | null;
      if (o && typeof o.anstallda_min === "number" && typeof o.anstallda_max === "number" && o.anstallda_min > o.anstallda_max) {
        return json({ detail: `Minsta antal anställda (${o.anstallda_min}) är större än största (${o.anstallda_max}). Rätta filtret och kör igen.` }, 422);
      }
      const id = nyttId();
      const nu_ = new Date().toISOString();
      const rad: Liggarrad = { job_id: id, status: "queued", scope: "batch", is_test: false, created_at: nu_, updated_at: nu_, completed_at: null, error: null, korning: null };
      LIGGAREN.unshift(rad);
      const ingenstans = Array.isArray(o?.geography) && (o!.geography as string[]).some((g) => /ingenstans/i.test(g));
      if (ingenstans) {
        JOBB.set(id, {
          klart: Date.now() + 5000,
          status: "failed",
          error: "Sökningen hittade inga bolag i målgruppen. Kontrollera stavningen på orterna eller bredda bransch eller område och kör igen.",
          result: () => ({}),
          steg: () => Object.assign(rad, { status: "failed", error: "Sökningen hittade inga bolag i målgruppen. Kontrollera stavningen på orterna eller bredda bransch eller område och kör igen.", completed_at: new Date().toISOString() })
        });
      } else if (namn.length) {
        // Egna bolag går den gamla vägen: ett researchjobb per bolag (LK-005).
        const barn = namn.slice(0, limit).map((n, i) => {
          const bid = nyttId();
          JOBB.set(bid, { klart: Date.now() + 9000 + i * 4000, result: () => ({ prospect_id: n }) });
          return { job_id: bid, prospect_id: nyttId() };
        });
        JOBB.set(id, { klart: Date.now() + 3000, result: () => ({ jobs: barn }), steg: () => Object.assign(rad, { status: "completed", completed_at: new Date().toISOString() }) });
      } else {
        const k = korning({ mal: limit, scope: String(kropp.scope ?? "research_and_draft"), struktur: kropp.struktur === "b" ? "b" : "a", overrides: o, undersokta: 0, jobs: [] });
        JOBB.set(id, {
          klart: Date.now() + 6000,
          result: () => ({ korning: k, jobs: [] }),
          steg: () => {
            Object.assign(k, { undersokta: 4, pagaende: 2, rundor: 1, jobs: jobb([16, 23]), tratt: tratt(2, 4) });
            Object.assign(rad, { status: "processing", korning: k, updated_at: new Date().toISOString() });
          }
        });
      }
      return json({ jobs: [{ job_id: id }], scope: kropp.scope, count: 0, overrides: o, is_test: false, struktur: kropp.struktur, fase: "soker" }, 202);
    }, 600);
  }

  const jobbvag = v.match(/^\/jobb\/([^/]+)$/);
  if (jobbvag && metod === "GET") {
    return vanta(() => {
      const j = JOBB.get(jobbvag[1]);
      if (!j) return json({ detail: "Jobbet finns inte eller har städats bort." }, 404);
      if (j.forlopp) {
        // Utskicket stegar ett mejl per hämtning.
        if (j.forlopp.klara < j.forlopp.totalt) {
          j.forlopp.klara += 1;
          return json({ status: "processing", forlopp: j.forlopp, result: null, error: null });
        }
        return json({ status: "completed", forlopp: j.forlopp, result: j.result(), error: null });
      }
      if (Date.now() < j.klart) return json({ status: "processing", result: null, error: null });
      if (j.steg) {
        j.steg();
        j.steg = undefined;
      }
      if (j.status === "failed") return json({ status: "failed", result: null, error: j.error });
      return json({ status: "completed", result: j.result(), error: null });
    });
  }

  const m = v.match(/^\/korningar\/([^/]+)(?:\/(utkast|utkast\/skriv|utkast\/skicka-jobb|pausa|aterupta|avbryt|fortsatt))?$/);
  if (!m) return null;
  const rad = LIGGAREN.find((r) => r.job_id === m[1]);
  if (!rad) return vanta(() => json({ detail: "Körningen finns inte." }, 404));
  const k = rad.korning;
  const del = m[2];

  if (!del && metod === "GET") return vanta(() => json(rad));
  if (del === "utkast" && metod === "GET") return vanta(() => json({ ...(k ? leadsFor(k) : { leads: [], antal: { kan_skrivas: 0 } }), signatur: SIGNATUR }));

  if (del === "utkast/skriv" && metod === "POST") {
    return vanta(() => {
      if (!k) return json({ count: 0, jobs: [] }, 202);
      const att = leadsFor(k).leads.filter((l) => l.status === "saknas" && l.kan_mejlas);
      att.forEach((l, n) => {
        const r = RADER.find((x) => x.id === l.prospect_id)!;
        Object.assign(r, { jobb: "utkast", klart_vid: Date.now() + 7000 + n * 3000 });
      });
      return json({ count: att.length, jobs: att.map((l) => ({ job_id: nyttId(), prospect_id: l.prospect_id })) }, 202);
    });
  }

  if (del === "utkast/skicka-jobb" && metod === "POST") {
    return vanta(() => {
      if (!k) return json({ detail: "Körningen finns inte." }, 404);
      const vantande = leadsFor(k).leads.filter((l) => l.status === "vantar");
      const id = nyttId();
      JOBB.set(id, {
        klart: 0,
        forlopp: { klara: 0, totalt: vantande.length },
        result: () => {
          const stoppade: { company_name: string; skal: string }[] = [];
          let skickade = 0;
          let vantar = 0;
          for (const l of vantande) {
            const r = RADER.find((x) => x.id === l.prospect_id)!;
            if (r.utkast_status !== "vantar") continue;
            if (STOPP.has(r.company_name)) {
              const skal = `${r.contact_email ?? r.company_name} har avregistrerat sig. Avregistreringen gäller hela tenanten och är permanent.`;
              Object.assign(r, { utkast_status: "stoppat", utkast_skal: skal });
              stoppade.push({ company_name: r.company_name, skal });
            } else if (skickade === 0) {
              Object.assign(r, { status: "contacted", utkast_status: "skickat", skickat_at: new Date().toISOString(), queue_item_id: null });
              skickade++;
            } else {
              Object.assign(r, { utkast_status: "godkant", skickas_tidigast: new Date(Date.now() + 15 * 36e5).toISOString() });
              vantar++;
            }
          }
          return { skickade, vantar_pa_fonstret: vantar, stoppade };
        }
      });
      return json({ job_id: id, pagar: false }, 202);
    });
  }

  if (metod === "POST" && (del === "pausa" || del === "aterupta" || del === "avbryt")) {
    return vanta(() => {
      const gar = k && !k.klar && rad.status !== "failed";
      // Som storage.set_korning_styrning: en pågående (också vilande) körning går att styra; en klar svarar 409.
      if (!gar) return json({ detail: "Körningen pågår inte och kan inte styras." }, 409);
      k.styrning = del === "pausa" ? "paus" : del === "avbryt" ? "avbruten" : null;
      if (del === "avbryt" && k.vilande) {
        Object.assign(k, { vilande: null, klar: true, slut_orsak: "avbruten" });
        Object.assign(rad, { status: "completed", completed_at: new Date().toISOString() });
      }
      if (del === "aterupta") paborjad = Date.now();
      rad.updated_at = new Date().toISOString();
      return json({ job_id: rad.job_id, styrning: k.styrning });
    });
  }
  if (metod === "POST" && del === "fortsatt") {
    return vanta(() => {
      const kan = rad.scope === "batch" && (rad.status === "completed" || rad.status === "failed") && k && k.mal && k.levererade < k.mal && k.slut_orsak !== "avbruten" && k.kalla !== "lista";
      if (!kan) return json({ detail: "Körningen kan inte fortsätta: den pågår, nådde målet eller avbröts." }, 409);
      Object.assign(k, { klar: false, slut_orsak: null, flaskhals: null, sammanfattning: null, rundor: 0, pagaende: 1, styrning: null, fortsatt: Number(k.fortsatt ?? 0) + 1 });
      Object.assign(rad, { status: "processing", error: null, completed_at: null, updated_at: new Date().toISOString() });
      paborjad = Date.now();
      return json({ job_id: rad.job_id, fortsatt: k.fortsatt });
    });
  }
  return null;
}
