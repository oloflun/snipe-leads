/**
 * VAD kostar på startsidan? Spelar in ett spår och summerar huvudtrådens tid
 * per sorts arbete, först under laddningen och sedan under scroll.
 *
 *   node scripts/mat_startsida_spar.mjs
 *   BASE=http://localhost:3100 SIDA=/ STRYP=4 node scripts/mat_startsida_spar.mjs
 *   CSS=".landing .light{display:none}" node scripts/mat_startsida_spar.mjs   # prova utan ett lager
 *
 * `mat_startsida_scroll.mjs` säger ATT bildrutor tappas. Det här skriptet säger
 * varför: skript, stilberäkning, layout, målning eller kompositering. Utan den
 * uppdelningen blir åtgärderna gissningar.
 *
 * `CSS` läggs in före första målningen och är till för att slå av en misstänkt
 * i taget (ett lager, en oskärpa) och se vad som händer med siffrorna.
 *
 *   npm i --no-save playwright
 */
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3100";
const SIDA = process.env.SIDA ?? "/";
const STRYP = Number(process.env.STRYP ?? 4);
const [VB, VH] = (process.env.VY ?? "1440x900").split("x").map(Number);
const KANAL = process.env.PW_KANAL ?? "chrome";
const CSS = process.env.CSS ?? "";
// OGILTIG=1: spela också in VILKA element som tvingar fram ommålning och ny stil
// under skrollen, och varför. Dyrt att spela in, så det är av som standard.
const OGILTIG = process.env.OGILTIG === "1";

// Händelsenamn i spåret → den rubrik DevTools visar dem under.
const SORT = {
  Skript: ["EvaluateScript", "v8.compile", "FunctionCall", "TimerFire", "FireAnimationFrame", "EventDispatch", "RunMicrotasks", "v8.run", "V8.GC_", "MinorGC", "MajorGC", "FireIdleCallback", "XHRReadyStateChange", "v8.callFunction"],
  Stil: ["UpdateLayoutTree", "RecalculateStyles", "ParseAuthorStyleSheet", "ScheduleStyleRecalculation"],
  Layout: ["Layout", "UpdateLayerTree", "IntersectionObserverController::computeIntersections"],
  Målning: ["Paint", "PaintImage", "PrePaint", "Layerize", "PaintArtifactCompositor::Update"],
  Kompositering: ["Commit", "CompositeLayers", "UpdateLayer", "Decode Image", "ImageDecodeTask", "RasterTask", "GPUTask"],
  Tolkning: ["ParseHTML"]
};
const sortFor = (namn) => {
  for (const [sort, lista] of Object.entries(SORT)) if (lista.some((n) => namn.startsWith(n))) return sort;
  return null;
};

async function spela(page, cdp, arbete) {
  const delar = [];
  cdp.on("Tracing.dataCollected", (e) => delar.push(...e.value));
  await cdp.send("Tracing.start", {
    transferMode: "ReportEvents",
    traceConfig: {
      includedCategories: [
        "devtools.timeline",
        "disabled-by-default-devtools.timeline",
        "v8.execute",
        "toplevel",
        ...(OGILTIG ? ["disabled-by-default-devtools.timeline.invalidationTracking"] : [])
      ]
    }
  });
  await arbete();
  const klar = new Promise((r) => cdp.once("Tracing.tracingComplete", r));
  await cdp.send("Tracing.end");
  await klar;
  cdp.removeAllListeners("Tracing.dataCollected");
  return delar;
}

/** Egentid per sort på renderarens huvudtråd, och de längsta uppgifterna. */
function summera(handelser) {
  // Huvudtråden: den tråd som bär flest RunTask bland renderarens trådar med layout.
  const perTrad = new Map();
  for (const e of handelser) {
    if (e.ph !== "X" || !e.dur) continue;
    if (e.name === "Layout" || e.name === "UpdateLayoutTree" || e.name === "FunctionCall") {
      const k = `${e.pid}:${e.tid}`;
      perTrad.set(k, (perTrad.get(k) ?? 0) + e.dur);
    }
  }
  const huvud = [...perTrad.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  const mina = handelser
    .filter((e) => e.ph === "X" && e.dur && `${e.pid}:${e.tid}` === huvud)
    .sort((a, b) => a.ts - b.ts || b.dur - a.dur);

  // Egentid: en händelses tid minus dess barns, så att inget räknas två gånger.
  const summa = Object.fromEntries(Object.keys(SORT).map((s) => [s, 0]));
  summa.Övrigt = 0;
  const stack = [];
  const langa = [];
  const perNamn = new Map();
  const stang = (e) => {
    const egen = e.dur - e._barn;
    const sort = sortFor(e.name);
    if (sort) {
      summa[sort] += egen;
      perNamn.set(e.name, (perNamn.get(e.name) ?? 0) + egen);
    } else if (e._medraknad) summa.Övrigt += egen;
  };
  for (const e of mina) {
    e._barn = 0;
    while (stack.length && stack[stack.length - 1].ts + stack[stack.length - 1].dur <= e.ts) stang(stack.pop());
    const foralder = stack[stack.length - 1];
    if (foralder) foralder._barn += e.dur;
    e._medraknad = e.name === "RunTask" || !!foralder;
    if (e.name === "RunTask" && e.dur >= 50000) langa.push(e);
    stack.push(e);
  }
  while (stack.length) stang(stack.pop());

  const ms = (us) => Math.round(us / 1000);
  const total = Object.values(summa).reduce((a, b) => a + b, 0);

  // VAD målas? Paint-händelserna bär noden de målar. Summan per nod pekar ut
  // det som ritas om bildruta efter bildruta.
  const malat = new Map();
  let malningar = 0;
  for (const e of mina) {
    if (e.name !== "Paint") continue;
    malningar += 1;
    const d = e.args?.data ?? {};
    const nyckel = d.nodeName ?? (d.nodeId != null ? `#${d.nodeId}` : "okänd");
    const post = malat.get(nyckel) ?? { us: 0, n: 0, nodeId: d.nodeId };
    post.us += e.dur;
    post.n += 1;
    malat.set(nyckel, post);
  }
  const bildrutor = mina.filter((e) => e.name === "BeginMainThreadFrame").length || null;
  const stilElement = mina
    .filter((e) => e.name === "UpdateLayoutTree")
    .reduce((a, e) => a + (e.args?.elementCount ?? 0), 0);
  const rader = Object.entries(summa)
    .sort((a, b) => b[1] - a[1])
    .map(([sort, us]) => `${sort} ${ms(us)} ms (${total ? Math.round((us / total) * 100) : 0} %)`);
  const topp = [...perNamn.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([n, us]) => `${n} ${ms(us)}`);
  // Vad BESTÅR de långa uppgifterna av? Egentid per händelse och skriptfil
  // inuti var och en av de längsta, så att "en sekund fryser" får ett namn.
  const innehall = langa
    .slice()
    .sort((a, b) => b.dur - a.dur)
    .slice(0, 4)
    .map((uppgift) => {
      const slut = uppgift.ts + uppgift.dur;
      const per = new Map();
      for (const e of mina) {
        if (e === uppgift || e.ts < uppgift.ts || e.ts + e.dur > slut) continue;
        const egen = e.dur - (e._barn ?? 0);
        if (egen < 1000) continue;
        const url = e.args?.data?.url ?? e.args?.data?.scriptName ?? "";
        const fil = url ? " " + url.split("/").pop().split("?")[0].slice(0, 22) : "";
        const fn = e.args?.data?.functionName ? ` ${e.args.data.functionName}` : "";
        const k = `${e.name}${fn}${fil}`;
        per.set(k, (per.get(k) ?? 0) + egen);
      }
      const delar = [...per.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, us]) => `${k} ${ms(us)}`);
      return `${ms(uppgift.dur)} ms vid ${ms(uppgift.ts - mina[0].ts)} ms: ${delar.join(", ")}`;
    });

  return {
    innehall,
    malat: [...malat.entries()]
      .sort((a, b) => b[1].us - a[1].us)
      .slice(0, 8)
      .map(([namn, v]) => ({ namn, ms: ms(v.us), n: v.n, nodeId: v.nodeId })),
    malningar,
    bildrutor,
    stilElement,
    spann: mina.length ? ms(mina[mina.length - 1].ts - mina[0].ts) : 0,
    rader,
    topp,
    totalMs: ms(total),
    langaAntal: langa.length,
    langaMs: ms(langa.reduce((a, e) => a + e.dur, 0)),
    langsta: langa.sort((a, b) => b.dur - a.dur).slice(0, 5).map((e) => ms(e.dur))
  };
}

async function namnge(cdp, poster) {
  // Äldre Chrome skriver bara nodens id i spåret; slå upp vad det är.
  for (const post of poster) {
    if (!post.namn.startsWith("#") || post.nodeId == null) continue;
    try {
      const { node } = await cdp.send("DOM.describeNode", { backendNodeId: post.nodeId });
      const attr = node.attributes ?? [];
      const hamta = (n) => {
        const i = attr.indexOf(n);
        return i >= 0 ? attr[i + 1] : "";
      };
      const klass = hamta("class").split(" ").filter(Boolean).slice(0, 3).join(".");
      post.namn = `${node.localName || node.nodeName}${hamta("data-mo") ? `[data-mo=${hamta("data-mo")}]` : ""}${klass ? "." + klass : ""}`;
    } catch {
      /* noden finns inte längre */
    }
  }
}

function skriv(rubrik, s) {
  console.log(`\n${rubrik}: huvudtråden arbetade ${s.totalMs} ms av ${s.spann} ms`);
  console.log(`  bildrutor med arbete: ${s.bildrutor ?? "?"} · målningar: ${s.malningar} · element i stilberäkning: ${s.stilElement}`);
  if (s.malat.length) console.log("  målas mest: " + s.malat.map((m) => `${m.namn} ${m.ms} ms/${m.n} ggr`).join(" | "));
  console.log("  " + s.rader.join(" · "));
  console.log("  störst: " + s.topp.join(", "));
  console.log(`  långa uppgifter (>50 ms): ${s.langaAntal} st, ${s.langaMs} ms; längsta ${s.langsta.join(", ") || "inga"} ms`);
  for (const rad of s.innehall) console.log("    " + rad);
}

const browser = await chromium.launch({ channel: KANAL, headless: true });
const context = await browser.newContext({ viewport: { width: VB, height: VH } });
const page = await context.newPage();
if (CSS) await page.addInitScript((css) => {
  const lagg = () => {
    const s = document.createElement("style");
    s.textContent = css;
    (document.head ?? document.documentElement).appendChild(s);
  };
  if (document.head) lagg(); else document.addEventListener("DOMContentLoaded", lagg);
}, CSS);
const cdp = await context.newCDPSession(page);
await cdp.send("Emulation.setCPUThrottlingRate", { rate: STRYP });

console.log(`${BASE}${SIDA}  ${VB}x${VH}  CPU ${STRYP}x${CSS ? `  CSS: ${CSS}` : ""}`);

const laddning = await spela(page, cdp, async () => {
  await page.goto(BASE + SIDA, { waitUntil: "load" });
  await page.waitForTimeout(5000);
});
const sl = summera(laddning);
await cdp.send("DOM.getDocument", { depth: 0 }).catch(() => {});
await namnge(cdp, sl.malat);
skriv("Laddning (till 5 s efter load)", sl);
const matt = await page.evaluate(() =>
  performance.getEntriesByType("measure").map((m) => `${m.name} ${Math.round(m.duration)} ms`)
);
if (matt.length) console.log("  egna mått: " + matt.join(", "));

const scroll = await spela(page, cdp, async () => {
  const hojd = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  await page.mouse.move(VB / 2, VH / 2);
  const tak = Math.ceil(hojd / 120) * 4 + 40;
  for (let i = 0; i < tak; i++) {
    await page.mouse.wheel(0, 120);
    await page.waitForTimeout(16);
    if (i % 15 === 14 && (await page.evaluate(() => Math.round(scrollY))) >= hojd - 4) break;
  }
  await page.waitForTimeout(1000);
});
if (OGILTIG) {
  for (const sort of ["PaintInvalidationTracking", "StyleRecalcInvalidationTracking", "LayoutInvalidationTracking"]) {
    const per = new Map();
    for (const e of scroll) {
      if (e.name !== sort) continue;
      const d = e.args?.data ?? {};
      const k = `${(d.nodeName ?? "?").slice(0, 80)} · ${d.reason ?? d.invalidationSet ?? d.changedClass ?? d.changedAttribute ?? ""}`;
      per.set(k, (per.get(k) ?? 0) + 1);
    }
    console.log(`
${sort}, vanligast:`);
    for (const [k, n] of [...per.entries()].sort((a, b) => b[1] - a[1]).slice(0, 14)) console.log(`  ${n} × ${k}`);
  }
}
const ss = summera(scroll);
await namnge(cdp, ss.malat);
skriv("Scroll uppifrån och ned", ss);

await browser.close();
