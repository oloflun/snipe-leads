/**
 * Förhandsvisningens svar för Iris utkast (steg 4.3), i leads-API:ts form:
 *
 * - `GET  /leads/queue` → `{ items, signatur }` (leads.py:list_review_queue, med `brodtext` och `svans`)
 * - `POST /leads/queue/{id}/approve` för de bolag en sändspärr stoppar (resten svarar svar/iris.ts)
 * - `POST /leads/queue/{id}/skicka-nu`, `/leads/queue/schemalagg`, `/leads/queue/tillbaka-till-iris`
 * - `GET  /leads/skickat?limit=` → `{ skickat, signatur }` (schemalagda överst), `/leads/skickat/antal?dagar=`
 * - `GET  /leads/provmejl/mottagare`, `POST /leads/provmejl`
 * - `GET  /leads/prospects/{id}/utkast` med hela signaturen (leadets panel)
 * - `POST /api/email-studio` (Next, AP15): förskrivna omskrivningar, ingen modell
 *
 * Samma påhittade bolag som Iris leads (svar/iris.ts), så att ett godkännande här
 * syns i leadets panel och tvärtom. Exempel, märkta som sådana här och bara här:
 * domänen .test och numren 070-174 06 xx. Skrivningar ändrar datan tills sidan
 * laddas om.
 */
import { RADER, framat, type Rad } from "./iris";

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();
const HALSNING = "Vänliga hälsningar";

/** Exempelkundens signatur, som backenden normaliserar den (signatur.normalisera, bygg_signaturtext). */
const SIG = {
  namn: "Kim Exempel",
  titel: "Säljansvarig",
  verksamhet: "Exempelbolaget AB | Telefoni för företag",
  telefon: "070-174 06 01",
  epost: "kim@exempelbolaget.test",
  ort: "Umeå",
  webb: "exempelbolaget.test",
  bolag: "Exempelbolaget AB"
};
const SIGNATUR = { ...SIG, text: [SIG.namn, SIG.titel, SIG.verksamhet, SIG.telefon, SIG.epost, "", SIG.ort, SIG.webb, SIG.bolag].join("\n") };
const FOT =
  "--\nExempelbolaget AB, org.nr 559900-0000, Exempelgatan 1, 901 00 Umeå.\nVill du inte få fler mejl från oss? Avregistrera dig här: https://exempelbolaget.test/avregistrera/exempel";
const SVANS = `${SIGNATUR.text}\n\n${FOT}`;

/** Bolagen en sändspärr stoppar vid Godkänn och skicka eller Skicka nu, med spärrens egen mening. */
const STOPP: Record<string, string> = {
  "Fiktiv Telefoni AB": "karim@fiktivtelefoni.test har avregistrerat sig. Avregistreringen gäller hela tenanten och är permanent.",
  "Kuliss Event AB": "kulissevent.test kontaktades för 34 dagar sedan. Karenstiden är 90 dagar per företag."
};

const meddelandeId = (r: Rad) => r.id.replace("-8000-", "-e000-");
const brod = (r: Rad) => {
  const b = r.brodtext ?? "";
  return b.trimEnd().endsWith(HALSNING) ? b : `${b.trimEnd()}\n\n${HALSNING}`;
};

// Mejl som redan gått ut, med leadets läge efteråt (LU-082, LU-083). Två har fått svar.
const SKICKADE: [number, string, number][] = [
  [2, "contacted", 60],
  [5, "replied", 140],
  [13, "meeting", 220],
  [20, "lost", 300],
  [23, "contacted", 30]
];
for (const [i, status, timmar] of SKICKADE) {
  const r = RADER[i];
  const forman = r.contact_name?.split(" ")[0];
  Object.assign(r, {
    status,
    utkast_status: "skickat",
    skickat_at: iso(timmar),
    queue_item_id: null,
    amne: r.amne ?? `Telefonin hos ${r.company_name.replace(/ AB$/, "")}`,
    brodtext:
      r.brodtext ??
      `Hej${forman ? ` ${forman}` : ""},\n\nJag såg att ni på ${r.company_name.replace(/ AB$/, "")} har vuxit i ${r.ort}. Många i er storlek samlar växel och mobiler hos en leverantör.\n\nJag skickar gärna ett förslag som passar er.`
  });
}
// Godkända som väntar på sändfönstret (LU-084): utöver det i svar/iris.ts, två till.
for (const [i, timmar] of [
  [4, -17],
  [7, -18]
] as const) {
  Object.assign(RADER[i], { utkast_status: "godkant", skickas_tidigast: new Date(nu - timmar * 36e5).toISOString(), queue_item_id: `00000000-0000-4000-9000-${String(100000000000 + i).slice(-12)}`, utkast_skal: null });
  if (!RADER[i].brodtext) {
    Object.assign(RADER[i], {
      amne: `Växeln hos ${RADER[i].company_name.replace(/ AB$/, "")}`,
      brodtext: `Hej,\n\nNi har öppnat ett nytt kontor i ${RADER[i].ort}. Får jag visa hur andra i er storlek samlat telefonin hos en leverantör?\n\nJag skickar gärna ett förslag.`
    });
  }
}

/** Svaren i konversationen för de leads som svarat. */
const SVAR: Record<number, string> = {
  5: "Hej Kim,\n\nTack för mejlet. Det låter intressant, vi ser över växeln efter sommaren. Kan du skicka ett prisexempel för tolv användare?\n\nMvh Sam\n\nDen 12 nov. 2026 skrev Kim Exempel <kim@exempelbolaget.test>:\n> Hej Sam,\n> Jag såg att ni har vuxit i Örebro.",
  13: "Hej!\n\nGärna ett möte. Tisdag kl. 10 passar bra, skicka en inbjudan.\n\nHälsningar Maja"
};

function konversation(r: Rad, i: number) {
  const svar = SVAR[i];
  if (!svar || !r.skickat_at) return undefined;
  return [
    { id: meddelandeId(r), direction: "outbound", subject: r.amne, body: `${brod(r)}\n\n${SVANS}`, sent_at: r.skickat_at },
    { id: meddelandeId(r).replace("-e000-", "-e100-"), direction: "inbound", subject: `Sv: ${r.amne}`, body: svar, sent_at: new Date(new Date(r.skickat_at).getTime() + 20 * 36e5).toISOString() }
  ];
}

function kopost(r: Rad) {
  return {
    id: r.queue_item_id,
    status: "awaiting_review",
    subject: r.amne,
    body: `${brod(r)}\n\n${SVANS}`,
    brodtext: brod(r),
    svans: SVANS,
    message_id: meddelandeId(r),
    prospect_id: r.id,
    prospect_email: r.contact_email,
    company_name: r.company_name,
    contact_name: r.contact_name,
    contact_role: r.contact_role,
    website: r.website,
    lagesbeskrivning: r.motivering,
    signaler: null,
    created_at: r.senaste_handelse_at
  };
}

function skickatrader() {
  const schemalagda = RADER.filter((r) => r.utkast_status === "godkant" && !r.arkiverad_at && r.queue_item_id)
    .map((r) => ({
      id: `ko-${r.queue_item_id}`,
      queue_item_id: r.queue_item_id,
      subject: r.amne,
      body: `${brod(r)}\n\n${SVANS}`,
      sent_at: null,
      skickas_tidigast: r.skickas_tidigast,
      schemalagt: true,
      svarat: false,
      thread_id: null,
      prospect_id: r.id,
      company_name: r.company_name,
      contact_name: r.contact_name,
      prospect_email: r.contact_email,
      status: r.status
    }))
    .sort((a, b) => String(a.skickas_tidigast).localeCompare(String(b.skickas_tidigast)));
  const skickade = RADER.map((r, i) => ({ r, i }))
    .filter(({ r }) => r.skickat_at)
    .map(({ r, i }) => {
      const konv = konversation(r, i);
      return {
        id: meddelandeId(r),
        subject: r.amne,
        body: `${brod(r)}\n\n${SVANS}`,
        sent_at: r.skickat_at,
        thread_id: null,
        prospect_id: r.id,
        company_name: r.company_name,
        contact_name: r.contact_name,
        prospect_email: r.contact_email,
        status: r.status,
        svarat: Boolean(konv),
        schemalagt: false,
        ...(konv ? { konversation: konv } : {})
      };
    })
    .sort((a, b) => String(b.sent_at).localeCompare(String(a.sent_at)));
  return [...schemalagda, ...skickade];
}

function json(kropp: unknown, status = 200) {
  return new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

/** Förskrivna omskrivningar för Email Studio: inga anrop till en modell i förhandsvisningen. */
function studiosvar(kropp: Record<string, unknown>) {
  const action = String(kropp.action ?? "improve");
  const utkast = String(kropp.draft ?? "");
  const amne = String(kropp.subject ?? "");
  const bolag = String((kropp.context as { companyName?: string } | undefined)?.companyName ?? "bolaget").replace(/ AB$/, "");
  const stycken = utkast.split(/\n{2,}/);
  const halsning = stycken[0] ?? "Hej,";
  const slut = stycken.at(-1) === HALSNING ? HALSNING : "";
  const ny: Record<string, string> = {
    shorter: [halsning, `Många i er storlek samlar telefonin hos en leverantör. Jag skickar gärna ett förslag till ${bolag}.`, slut].filter(Boolean).join("\n\n"),
    improve: [halsning, `${bolag} växer, och med fler medarbetare blir växel och mobiler snabbt ett lapptäcke. Vi samlar allt i ett abonnemang som går att ändra själv.`, "Jag skickar gärna ett förslag som passar er storlek.", slut].filter(Boolean).join("\n\n"),
    personalize: [halsning, `Grattis till det nya kontoret. När ${bolag} nu sitter på två orter brukar frågan om en gemensam växel komma upp.`, "Jag skickar gärna ett förslag som passar er.", slut].filter(Boolean).join("\n\n"),
    rewrite: [halsning, `Hur hanterar ${bolag} samtalen till det nya kontoret i dag? Många i er storlek tappar samtal i början.`, "Jag visar gärna hur andra löst det.", slut].filter(Boolean).join("\n\n"),
    translate: ["Hi,", `I saw that ${bolag} is growing. Many companies your size bring their switchboard and mobiles together with one provider.`, "I would be happy to send you a proposal.", "Best regards"].join("\n\n")
  };
  const direkt = ny[action];
  if (direkt) {
    return { success: true, data: { new_version: direkt, explanation: "Kortare stycken och ett tydligare nästa steg. Fakta oförändrade.", subject_suggestions: action === "translate" ? [`Telephony at ${bolag}`] : [amne], simulated: false } };
  }
  if (action === "analyze") {
    return { success: true, data: { new_version: utkast, explanation: "Ingången bygger på bolagets eget läge och handlingen är en mening. Ämnesraden är kort och utan bolagets namn.", confidence_tips: "Säkerhet: hög. Tips: nämn en konkret siffra ur deras sajt i andra stycket.", subject_suggestions: [amne], simulated: false } };
  }
  if (action === "ab_variants") {
    return { success: true, data: { new_version: `${halsning}\n\nVad skulle en gemensam växel betyda för ${bolag}?\n\n${slut}`.trim(), explanation: "Variant B: kortare, och slutar med en fråga.", subject_suggestions: [amne, `En växel för ${bolag}`, "Samtalen till nya kontoret"], simulated: false } };
  }
  return { success: true, data: { new_version: `${halsning}\n\nJag skrev förra veckan om telefonin hos ${bolag}. Är det något ni tittar på i höst?\n\n${slut}`.trim(), explanation: "En kort uppföljning som knyter an till förra mejlet.", subject_suggestions: [`Sv: ${amne}`], simulated: false } };
}

/** Svarar på utkastens vägar, och `null` för allt annat (då svarar svar/iris.ts). */
export function svaraUtkast(url: URL, init?: RequestInit): Promise<Response> | null {
  const vag = url.pathname;
  const metod = (init?.method ?? "GET").toUpperCase();
  const kropp = (() => {
    try {
      return typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  })();
  const vanta = (svar: () => Response, ms = 220) => new Promise<Response>((r) => setTimeout(() => r(svar()), ms));

  if (vag === "/api/email-studio" && metod === "POST") return vanta(() => json(studiosvar(kropp)), 900);
  if (!vag.startsWith("/api/snajp-support/leads/")) return null;
  const v = vag.replace("/api/snajp-support/leads", "");
  framat();
  const viaKo = (id: string) => RADER.find((r) => r.queue_item_id === id);

  if (v === "/queue" && metod === "GET") {
    return vanta(() => json({ items: RADER.filter((r) => r.utkast_status === "vantar" && !r.arkiverad_at && r.queue_item_id && r.brodtext && !r.jobb).map(kopost), signatur: SIGNATUR }));
  }
  if (v === "/skickat" && metod === "GET") return vanta(() => json({ skickat: skickatrader(), signatur: SIGNATUR }));
  if (v === "/skickat/antal" && metod === "GET") {
    return vanta(() => {
      const dagar = Math.max(1, Math.min(366, Number(url.searchParams.get("dagar") ?? 28)));
      const sedan = Date.now() - dagar * 864e5;
      const inom = RADER.map((r, i) => ({ r, i })).filter(({ r }) => r.skickat_at && new Date(r.skickat_at).getTime() >= sedan);
      return json({ dagar, skickat: inom.length, svarat: inom.filter(({ i }) => SVAR[i]).length });
    });
  }
  if (v === "/provmejl/mottagare" && metod === "GET") return vanta(() => json({ mottagare: ["kim@exempelbolaget.test", "info@exempelbolaget.test"] }));
  if (v === "/provmejl" && metod === "POST") return vanta(() => json({ till: kropp.till, saknar_fot: false }), 700);
  if (v === "/queue/schemalagg" && metod === "POST") {
    return vanta(() => {
      const tid = new Date(String(kropp.tid ?? ""));
      if (Number.isNaN(tid.getTime()) || tid.getTime() <= Date.now() || tid.getTime() > Date.now() + 60 * 864e5) return json({ detail: "Välj en tid från nu och högst 60 dagar fram." }, 422);
      const ids = (kropp.ids as string[]) ?? [];
      let andrade = 0;
      for (const r of RADER) {
        if (r.queue_item_id && ids.includes(r.queue_item_id) && r.utkast_status === "godkant") {
          r.skickas_tidigast = tid.toISOString();
          andrade++;
        }
      }
      return json({ andrade, skickas_tidigast: tid.toISOString() });
    });
  }
  if (v === "/queue/tillbaka-till-iris" && metod === "POST") {
    return vanta(() => {
      const ids = (kropp.ids as string[]) ?? [];
      const traffar = RADER.filter((r) => r.queue_item_id && ids.includes(r.queue_item_id) && (r.utkast_status === "vantar" || r.utkast_status === "godkant"));
      for (const r of traffar) Object.assign(r, { status: "new", utkast_status: "avvisat", queue_item_id: null, skickas_tidigast: null });
      return json({ count: traffar.length, jobs: [] }, 202);
    });
  }
  const ko = v.match(/^\/queue\/([^/]+)\/(skicka-nu|approve)$/);
  if (ko && metod === "POST") {
    const r = viaKo(ko[1]);
    if (!r) return ko[2] === "skicka-nu" ? vanta(() => json({ detail: "Utkastet finns inte." }, 404)) : null;
    const stopp = STOPP[r.company_name];
    if (stopp) {
      return vanta(() => {
        Object.assign(r, { utkast_status: "stoppat", utkast_skal: stopp });
        return json({ id: ko[1], status: "blocked", utfall: "blocked", besked: `Stoppat av en sändspärr: ${stopp}`, skal: stopp });
      }, 500);
    }
    if (ko[2] === "approve") return null;
    return vanta(() => {
      Object.assign(r, { status: r.status === "new" || r.status === "ready" ? "contacted" : r.status, utkast_status: "skickat", skickat_at: new Date().toISOString(), skickas_tidigast: null, queue_item_id: null });
      return json({ id: ko[1], status: "sent", utfall: "sent", besked: "Skickat.", skal: null });
    }, 500);
  }
  const utkast = v.match(/^\/prospects\/([^/]+)\/utkast$/);
  if (utkast && metod === "GET") {
    const r = RADER.find((x) => x.id === utkast[1]);
    if (!r) return null;
    return vanta(() => {
      const status = r.jobb === "utkast" ? "skrivs" : r.utkast_status;
      const bas = { utkast_status: status, utkast_skal: r.utkast_skal, queue_item_id: r.queue_item_id, skickas_tidigast: r.skickas_tidigast, skickat_at: r.skickat_at, utkast_regel: null };
      if (!r.brodtext || r.jobb === "utkast") return json({ utkast: null, thread_id: null, ...bas });
      return json({ utkast: { id: meddelandeId(r), subject: r.amne, body: `${brod(r)}\n\n${SVANS}`, brodtext: brod(r), svans: SVANS }, thread_id: null, signatur: SIGNATUR, ...bas });
    });
  }
  return null;
}
