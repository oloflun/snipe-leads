"use client";

import { useEffect, useRef, type MutableRefObject, type RefObject } from "react";
import type Lenis from "lenis";

/**
 * Startsidans rörelse: dörren, dygnsljuset, sektionsövergångarna, showcase-
 * rutornas liv och den isärtagna översikten. GSAP 3.15 + Lenis, bara via
 * repots två centralfiler (gsap.js, smooth-scroll.js), importerade DYNAMISKT:
 * båda rör `window` redan vid import, och en klientkomponent renderas också
 * på servern.
 *
 * ## Avslöjandena är idempotenta (2026-10-18, efter att rubriker fastnat dolda)
 *
 * Första versionen byggde varje avslöjande som en `gsap.from` med en
 * engångs-ScrollTrigger, skapad på nytt i SplitTexts `onSplit`. Varje
 * omspaltning (fontbyte, storleksändring, HMR) dolde då ett redan visat
 * element igen, och en trigger vars start redan passerats spelar inte.
 * Resultatet hos Anton: rubrikerna "Tre paket.", "Frågor och Svar" och
 * showcase-rutornas delar stod på opacity 0 över hela sidan.
 *
 * Nu: ett element döljs av `arm()` högst en gång och visas av `play()`, som
 * stämplar `data-rv="1"` och är en no-op andra gången. Tre vägar kan kalla
 * play: ScrollTrigger (top 88 %), en IntersectionObserver (oberoende av
 * Lenis och GSAP:s skrollräkning) och en timer efter 2,5 s för det som står
 * i vyn. En omspaltning av ett visat element lämnar raderna i vila.
 *
 * Husets regler (design-skillen, koncept/_delat/KONTRAKT.md): scrub: true,
 * aldrig ett tal; en pin per uppsättning; startlägen sätts av JS och sidan
 * står synlig utan JS; opacity, inte autoAlpha, där länkar finns; en ägare
 * per egenskap; rörelsen spelar alltid (F-011).
 *
 * Uppsättningen görs om när produkt eller språk byts (deps), eftersom
 * SplitText flyttar textnoder och React därför måste få nya nyckelsatta
 * rubriker (key per produkt+språk i markupen) i stället för att diffa gamla.
 */

type Gsap = typeof import("@/gsap.js");

type DomRefs = {
  root: RefObject<HTMLElement | null>;
  lenis: MutableRefObject<Lenis | null>;
};

const DOOR_FAILSAFE_MS = 2500;
const REVEAL_FAILSAFE_MS = 2500;

// Ljusets dygn, ankrat i sidans sektioner (se computeKeys). Mark och skugga i
// oklch [L, C, H]; `str` är skuggans avsedda styrka, capStr sänker den så att
// det mörkaste bandet aldrig tar marken under L 0.90. Soluppgången matchar det
// gyllene hjältefotot och håller i sig över hela övre halvan; först vid priset
// är marken varmvit, samma som --paper.
//              cx    cy    w     h     rot  skx  gap blur  str   shade               ground
const STATES: Record<string, [number, number, number, number, number, number, number, number, number, [number, number, number], [number, number, number]]> = {
  soluppgang: [0.62, 0.48, 1.25, 1.15, -12, -22, 64, 26, 0.55, [0.86, 0.045, 55], [0.955, 0.03, 65]],
  morgon: [0.6, 0.45, 1.1, 1.05, -8, -14, 56, 16, 0.6, [0.87, 0.036, 62], [0.957, 0.027, 69]],
  formiddag: [0.52, 0.44, 1.0, 0.95, -3, -5, 44, 6, 0.7, [0.88, 0.026, 70], [0.961, 0.021, 74]],
  middag: [0.48, 0.5, 1.06, 0.98, 3, 8, 46, 8, 0.66, [0.885, 0.017, 80], [0.966, 0.015, 80]],
  eftermiddag: [0.46, 0.52, 1.14, 1.02, 6, 14, 52, 14, 0.56, [0.89, 0.011, 85], [0.967, 0.01, 86]],
  varmvit: [0.5, 0.5, 1.2, 1.1, 3, 6, 54, 22, 0.4, [0.9, 0.008, 88], [0.965, 0.008, 88]]
};
const ANCHORS: [string, string, number][] = [
  // [state, selector, offset in vh relative to the section's top]
  ["soluppgang", "[data-mo=\"hero\"]", 0],
  ["morgon", "[data-mo=\"produktbilder\"]", -0.5],
  ["formiddag", "#demo", -0.2],
  ["middag", "[data-mo=\"place\"]", -0.3],
  ["eftermiddag", "#fragor", -0.2],
  ["varmvit", "#priser", -0.2]
];

const smooth = (x: number) => x * x * (3 - 2 * x);
const lab = ([L, C, H]: [number, number, number]) => [L, C * Math.cos((H * Math.PI) / 180), C * Math.sin((H * Math.PI) / 180)];
const ok = (L: number, a: number, b: number) => `oklab(${L.toFixed(4)} ${a.toFixed(4)} ${b.toFixed(4)})`;

// Skuggans tak. Lagret komponeras med vanlig alfa i gamma-kodad sRGB:
// mörkast = ground * (1 - a) + shade * a per kanal. capStr ger största a <= str
// som håller det bandet på OKLab L >= 0.90.
const FLOOR = 0.9;
const toRgb = (L: number, a: number, b: number) => {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s
  ].map((c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.max(c, 0) ** (1 / 2.4) - 0.055));
};
const okL = (rgb: number[]) => {
  const [r, g, b] = rgb.map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return (
    0.2104542553 * Math.cbrt(0.4122214708 * r + 0.5363083019 * g + 0.0514633307 * b) +
    0.793617785 * Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) -
    0.0040720468 * Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  );
};
function capStr(v: number[]) {
  const sh = toRgb(v[9], v[10], v[11]);
  const g = toRgb(v[12], v[13], v[14]);
  const dark = (a: number) => okL(g.map((c, i) => c * (1 - a) + sh[i] * a));
  if (dark(v[8]) >= FLOOR) return v[8];
  let lo = 0;
  let hi = v[8];
  for (let i = 0; i < 14; i++) {
    const mid = (lo + hi) / 2;
    if (dark(mid) >= FLOOR) lo = mid;
    else hi = mid;
  }
  return lo;
}

// Nyckelbana: [[p, värde], ...], smoothstep mellan nycklarna. Samma p ger samma bild åt båda hållen.
type Keys = [number, number][];
function at(keys: Keys, p: number) {
  if (p <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [p0, v0] = keys[i];
    const [p1, v1] = keys[i + 1];
    if (p <= p1) return v0 + (v1 - v0) * (p1 === p0 ? 1 : smooth((p - p0) / (p1 - p0)));
  }
  return keys[keys.length - 1][1];
}

let doorPlayed = false; // hela dörren bara en gång per sidladdning; produkt- och språkbyten får en kort avtäckning

export function useLandingMotion({ root, lenis: lenisRef }: DomRefs, product: string, locale: string): void {
  const first = useRef(true);

  useEffect(() => {
    let cancelled = false;
    let teardown: (() => void) | undefined;

    (async () => {
      const [{ gsap, ScrollTrigger, SplitText, spring }, { default: lenis }] = await Promise.all([
        import("@/gsap.js"),
        import("@/smooth-scroll.js")
      ]);
      const rootEl = root.current;
      if (cancelled || !rootEl) return;
      lenisRef.current = lenis;
      const firstRun = first.current;
      first.current = false;
      teardown = setup({ gsap, ScrollTrigger, SplitText, spring } as Gsap, rootEl, firstRun && !doorPlayed);
      if (firstRun) doorPlayed = true;
    })().catch((e: unknown) => {
      // Importen föll (nätet, en gammal webbläsare): sidan står synlig utan
      // rörelse, och orsaken syns i konsolen i stället för att svaljas.
      console.error("landing motion:", e);
    });

    return () => {
      cancelled = true;
      teardown?.();
    };
    // product/locale: React byter de nyckelsatta rubrikerna, och uppsättningen görs om mot de nya noderna.
  }, [root, lenisRef, product, locale]);
}

// Ett tankstreck med mellanslag runt börjar aldrig en rad: mellanslaget före strecket är inget
// ordskilje för SplitText, så "dig –" mäts som ett ord. (Ett hårt mellanslag i texten hjälper inte:
// SplitText kollapsar allt \s till vanliga mellanslag innan den mäter.) Orden är orörda (F-028).
const ORDSKILJE = { delimiter: / (?![–—] )/, replaceWith: " " };

// Rutornas ankomst (caseEntry). Dämpning 0.66 passerar målet med drygt 6 % (cirka 11 px)
// och fjädrar tydligt tillbaka, respons 0.95 s ger en mjukare, längre glidning (Anton
// 2026-10-19: "jämnare och mjukare, studsen tydligare"; var 0.75/0.75). Studs bara där
// rörelsen bär fart, här själva inglidningen (apple-design § 4). Texten börjar när rutan
// passerat målet, nästa ruta när den förra har landat.
const CASE_GAP = 0.85;
const TEXT_AFTER = 0.6;
let queueEnd = 0;

function setup(G: Gsap, rootEl: HTMLElement, fullDoor: boolean): () => void {
  const { gsap, ScrollTrigger, SplitText, spring } = G;
  const ARRIVAL = spring(0.66, 0.95);
  const $ = <T extends HTMLElement = HTMLElement>(s: string, r: ParentNode = rootEl) => r.querySelector<T>(s);
  const $$ = <T extends HTMLElement = HTMLElement>(s: string, r: ParentNode = rootEl) => [...r.querySelectorAll<T>(s)];
  const timers: number[] = [];
  // Städning som inte är GSAP-objekt (ticker, lyssnare). Inte ctx.add inne i
  // kontextens egen funktion: den körs synkront medan `ctx` ännu är oinitierad.
  const cleanups: (() => void)[] = [];

  const ctx = gsap.context(() => {
    // ---------------------------------------------------------------- dörren
    const hero = $("[data-mo=\"hero\"]");
    const heroImg = $("[data-mo=\"hero-img\"]");
    const heroScrim = $("[data-mo=\"hero-scrim\"]");
    const h1 = $("[data-mo=\"hero-h1\"]");
    const lede = $("[data-mo=\"hero-lede\"]");
    const acts = $("[data-mo=\"hero-acts\"]");
    const side = $("[data-mo=\"hero-side\"]");
    const header = $("[data-mo=\"header\"]");
    const door = { on: fullDoor ? 0 : 1 };

    if (h1) {
      const late = [lede, acts, side, header].filter(Boolean) as HTMLElement[];
      if (fullDoor) {
        gsap.set(h1, { autoAlpha: 0 });
        gsap.set(late, { opacity: 0, y: 14 });
        if (heroImg) gsap.set(heroImg, { scale: 1.06 });
        if (heroScrim) gsap.set(heroScrim, { opacity: 0.4 });
      } else {
        gsap.set(h1, { autoAlpha: 0 });
      }
      // samma värden står nu inline: inline-skriptets <style> (LandingPhoto) har gjort sitt
      document.getElementById("door-armed")?.remove();
      let doorShown = false;
      timers.push(
        window.setTimeout(() => {
          if (h1.dataset.door) return;
          doorShown = true;
          gsap.set(h1, { autoAlpha: 1 });
          gsap.set(late, { opacity: 1, y: 0 });
          if (heroImg) gsap.set(heroImg, { scale: 1 });
          if (heroScrim) gsap.set(heroScrim, { opacity: 1 });
          door.on = 1;
        }, DOOR_FAILSAFE_MS)
      );
      // ctx.add: spaltningen sker efter att fonterna laddat, alltså utanför
      // kontextens synkrona körning, och ska ändå återställas med den.
      document.fonts.ready.then(() => ctx.add(() => {
        if (h1.dataset.door) return;
        SplitText.create(h1, {
          type: "lines",
          mask: "lines",
          linesClass: "ln",
          autoSplit: true,
          wordDelimiter: ORDSKILJE,
          onSplit(self) {
            if (h1.dataset.door) return;
            h1.dataset.door = "1";
            if (doorShown) {
              gsap.to(door, { on: 1, duration: 1.2 });
              return;
            }
            gsap.set(self.lines, { yPercent: 120 });
            gsap.set(h1, { autoAlpha: 1 });
            if (!fullDoor) {
              gsap.to(self.lines, { yPercent: 0, duration: 0.8, ease: "power4.out", stagger: 0.07 });
              return;
            }
            const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
            if (heroImg) tl.to(heroImg, { scale: 1, duration: 2.2, ease: "power2.out" }, 0);
            if (heroScrim) tl.to(heroScrim, { opacity: 1, duration: 1.4, ease: "power2.inOut" }, 0);
            tl.to(self.lines, { yPercent: 0, duration: 1.1, ease: "power4.out", stagger: 0.09 }, 0.25)
              .to(late, { opacity: 1, y: 0, duration: 0.8, stagger: 0.1 }, 0.7)
              .to(door, { on: 1, duration: 1.6, ease: "power2.inOut" }, 1.0);
          }
        });
      }));
      // hjältens foto glider långsammare än sidan när man lämnar den
      if (hero && heroImg) {
        gsap.fromTo(heroImg, { yPercent: 0 }, { yPercent: 12, ease: "none",
          scrollTrigger: { trigger: hero, start: "top top", end: "bottom top", scrub: true } });
      }
    }

    // ------------------------------------------------------------ ljusmotorn
    const light = $("[data-mo=\"light\"]");
    const panes = light && $(".light__panes", light);
    // marken ritas på ett eget fast lager: en variabel på roten hade räknat om stilen för hela sidan varje bildruta
    const groundEl = $("[data-mo=\"ground\"]");
    let keys: { name: string; s: number; v: number[] }[] = [];
    const px = (st: (typeof STATES)[string], vw: number, vh: number, k: number) =>
      [st[0] * vw, st[1] * vh, st[2] * vw, st[3] * vh, st[4], st[5], st[6] * k, st[7] * k, st[8], ...lab(st[9]), ...lab(st[10])];
    const docTop = (el: Element) => el.getBoundingClientRect().top + window.scrollY;
    function computeKeys() {
      const vw = innerWidth;
      const vh = innerHeight;
      const k = Math.min(vw, vh) / 900;
      keys = [];
      for (const [name, sel, off] of ANCHORS) {
        const el = $(sel);
        if (!el) continue;
        keys.push({ name, s: Math.max(0, docTop(el) + off * vh), v: px(STATES[name], vw, vh, k) });
      }
      for (let i = 1; i < keys.length; i++) if (keys[i].s <= keys[i - 1].s) keys[i].s = keys[i - 1].s + 1;
    }
    function sample(s: number) {
      if (s <= keys[0].s) return keys[0].v.slice();
      const last = keys[keys.length - 1];
      if (s >= last.s) return last.v.slice();
      let i = 0;
      while (s > keys[i + 1].s) i++;
      const a = keys[i];
      const b = keys[i + 1];
      const f = smooth((s - a.s) / (b.s - a.s));
      return a.v.map((x, j) => x + (b.v[j] - x) * f);
    }
    // Rutorna är 1000 x 1000 i CSS och skalas med transform: bredd, höjd och gap per bildruta
    // tvingade fram ny layout och ny oskärpa varje gång. Oskärpan byts i steg om 3 px, så att
    // kompositorn kan återanvända det suddade lagret medan det bara flyttas och skalas.
    const PANE = 1000;
    let lastKey = "";
    let lastGround = "";
    let lastBlur = -1;
    let lastShade = "";
    function render() {
      if (!light || !panes || !keys.length) return;
      const vw = innerWidth;
      const vh = innerHeight;
      const s = window.scrollY;
      const key = `${s}|${door.on}|${vw}x${vh}`;
      if (key === lastKey) return; // stilla bildruta
      lastKey = key;
      const v = sample(s);
      const [cx, cy, w, h, rot, skx, , blur] = v;
      const str = capStr(v);
      panes.style.transform = `translate3d(${(cx - PANE / 2 - (1 - door.on) * 0.25 * vw).toFixed(2)}px, ${(cy - PANE / 2).toFixed(2)}px, 0) rotate(${rot.toFixed(3)}deg) skewX(${skx.toFixed(3)}deg) scale(${(w / PANE).toFixed(4)}, ${(h / PANE).toFixed(4)})`;
      const bl = Math.round((blur + (1 - door.on) * 30) / 3) * 3;
      if (bl !== lastBlur) { panes.style.filter = `blur(${bl}px)`; lastBlur = bl; }
      light.style.opacity = (str * door.on).toFixed(3);
      const shade = ok(v[9], v[10], v[11]);
      if (shade !== lastShade) { light.style.background = shade; lastShade = shade; }
      const g = ok(v[12], v[13], v[14]);
      if (g !== lastGround) {
        if (groundEl) groundEl.style.background = g;
        panes.style.setProperty("--pane", g); // rutorna är marken, oförändrad
        lastGround = g;
      }
    }
    const onRefresh = () => { computeKeys(); lastKey = ""; render(); };
    gsap.ticker.add(render);
    ScrollTrigger.addEventListener("refresh", onRefresh);
    cleanups.push(() => { gsap.ticker.remove(render); ScrollTrigger.removeEventListener("refresh", onRefresh); });

    // ------------------------------------------------- avslöjandena (idempotenta)
    const shows = new Map<HTMLElement, () => void>();
    const revealed = (el: HTMLElement) => el.dataset.rv === "1";
    function play(el: HTMLElement) {
      const show = shows.get(el);
      if (!show || revealed(el)) return;
      el.dataset.rv = "1";
      show();
    }
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) play(e.target as HTMLElement);
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0 });
    cleanups.push(() => io.disconnect());
    // arm: dölj en gång, visa en gång. Tre vägar till play, alla idempotenta.
    function arm(el: HTMLElement, hide: () => void, show: () => void, start = "top 88%") {
      if (revealed(el)) return;
      hide();
      shows.set(el, show);
      ScrollTrigger.create({ trigger: el, start, once: true, onEnter: () => play(el) });
      io.observe(el);
    }

    function fadeUp(el: HTMLElement, delay = 0) {
      arm(el, () => gsap.set(el, { opacity: 0, y: 18 }),
        () => gsap.to(el, { opacity: 1, y: 0, duration: 0.9, ease: "power3.out", delay }));
    }
    function splitLines(el: HTMLElement) {
      SplitText.create(el, {
        aria: /^H[1-6]$/.test(el.tagName) ? "auto" : "none",
        type: "lines", mask: "lines", linesClass: "ln", autoSplit: true, wordDelimiter: ORDSKILJE,
        // varje omspaltning: dolda rader bara om elementet ännu inte visats; ett visat element står i vila
        onSplit(self) { if (!revealed(el)) gsap.set(self.lines, { yPercent: 120 }); }
      });
    }
    const showLines = (el: HTMLElement) => gsap.to($$(".ln", el), { yPercent: 0, duration: 0.9, ease: "power4.out", stagger: 0.07 });
    function headingLines(el: HTMLElement) {
      splitLines(el);
      arm(el, () => {}, () => showLines(el));
    }
    function words(el: HTMLElement) {
      SplitText.create(el, {
        aria: "none", type: "words", wordsClass: "st-w", autoSplit: true,
        onSplit(self) {
          return gsap.fromTo(self.words, { "--fill": 0 }, { "--fill": 1, ease: "none", stagger: 0.08,
            scrollTrigger: { trigger: el, start: "top 80%", end: "center 45%", scrub: true } });
        }
      });
    }
    // ------------------------------------------------ rutornas ankomst (data-case)
    // Antons beställning 2026-10-19: rutan tonas inte och klipps inte fram. Den glider in,
    // passerar målet en aning och fjädrar tillbaka (Apples fjäder, gsap.js: spring), och
    // först när den landat avtäcks den beskrivande texten rad för rad. En ruta i taget:
    // kön låter nästa ruta vänta tills den förra har landat. Ankomsten spelar en gång och
    // skrubbas aldrig, så att skrolla fram och tillbaka inte kan få rutan att darra.
    //   data-case        behållaren (utlösare och kö-enhet)
    //   data-case-box    det som rör sig, annars behållaren själv; data-from="left|right|up"
    //   data-case-text   avtäcks efter landningen
    // Rutan blir aldrig osynlig: utan JS, eller om utlösaren aldrig nås, står den bara förskjuten
    // tills säkringen spelar den.
    const wide = matchMedia("(min-width: 1024px)").matches;
    function caseEntry(el: HTMLElement) {
      const box = $("[data-case-box]", el) ?? el;
      const from = box.dataset.from ?? "up";
      let texts = $$("[data-case-text]", el);
      // Staplat (mobil) står text som kommer före rutan i läsordningen ovanför den: den får
      // sin egen avtäckning i stället för att vänta på en ruta som ännu är under skärmkanten.
      if (!wide) {
        texts.filter((t) => t.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING).forEach(headingLines);
        texts = texts.filter((t) => !(t.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING));
      }
      texts.forEach(splitLines);
      const offset = () => from === "up" ? { x: 0, y: 120 } : { x: (from === "left" ? -1 : 1) * Math.min(180, innerWidth * 0.14), y: 0 };
      // will-change redan i viloläget: lagret finns när glidningen börjar, så första bildrutan
      // målas inte om mitt i rörelsen. LiveText lyssnar på case:armed / case:landed.
      arm(el, () => {
        gsap.set(box, { ...offset(), willChange: "transform" });
        el.dispatchEvent(new Event("case:armed"));
      }, () => {
        const now = gsap.ticker.time;
        const start = Math.max(now, queueEnd);
        queueEnd = start + CASE_GAP;
        const tl = gsap.timeline({ delay: start - now });
        tl.to(box, { x: 0, y: 0, ease: ARRIVAL.ease, duration: ARRIVAL.duration, force3D: true, clearProps: "transform,willChange" }, 0);
        tl.call(() => { el.dispatchEvent(new Event("case:landed")); }, [], TEXT_AFTER);
        texts.forEach((t, i) => {
          t.dataset.rv = "1";
          tl.add(showLines(t), TEXT_AFTER + i * 0.12);
        });
      }, wide ? "top 85%" : "top 90%");
    }
    function plate(el: HTMLElement) {
      const dir = el.dataset.dir === "left" ? "inset(0% 100% 0% 0%)" : "inset(100% 0% 0% 0%)";
      arm(el, () => gsap.set(el, { clipPath: dir }),
        () => gsap.to(el, { clipPath: "inset(0% 0% 0% 0%)", duration: 1.2, ease: "power3.out" }), "top 90%");
      const img = el.querySelector<HTMLElement>("[data-parallax]");
      if (img) {
        gsap.set(img, { scale: 1.12 });
        gsap.fromTo(img, { yPercent: -5 }, { yPercent: 5, ease: "none",
          scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true } });
      }
    }
    function band(el: HTMLElement) {
      // det mörka bandet täcks av marken tills det skrubbas fram: ett materiellt sektionsbyte
      gsap.fromTo(el, { clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", ease: "none",
        scrollTrigger: { trigger: el, start: "top 95%", end: "top 40%", scrub: true } });
      const img = el.querySelector<HTMLElement>("[data-parallax]");
      if (img) {
        gsap.fromTo(img, { yPercent: -8 }, { yPercent: 8, ease: "none",
          scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true } });
      }
    }
    function rule(el: HTMLElement) {
      gsap.fromTo(el, { scaleX: 0 }, { scaleX: 1, ease: "none",
        scrollTrigger: { trigger: el, start: "top 94%", end: "top 62%", scrub: true } });
    }
    const units = $$("[data-mo=\"lines\"], [data-mo=\"up\"], [data-mo=\"row\"], [data-mo=\"plate\"], [data-mo=\"band\"], [data-mo=\"words\"], [data-mo=\"rule\"]");
    const isUnit = new Set(units);
    for (const el of units) {
      // en enhet inuti en annan bärs av sin förälder (bandets ord är undantaget: bandet klipps, orden fylls)
      let carried = false;
      for (let p = el.parentElement; p && p !== rootEl; p = p.parentElement) {
        if (isUnit.has(p) && p.dataset.mo !== "band") { carried = true; break; }
      }
      if (carried) continue;
      switch (el.dataset.mo) {
        case "lines": headingLines(el); break;
        case "words": words(el); break;
        case "plate": plate(el); break;
        case "band": band(el); break;
        case "rule": rule(el); break;
        case "row": {
          const sib = el.parentElement ? [...el.parentElement.children].indexOf(el) : 0;
          fadeUp(el, Math.min(sib, 5) * 0.07);
          break;
        }
        default: fadeUp(el);
      }
    }
    $$("[data-case]").forEach(caseEntry);

    // ----------------------------------------- den isärtagna översikten
    const stage = $("[data-isar]");
    const pinEl = $("[data-isar-pin]");
    const spacerEl = $("[data-isar-spacer]");
    if (stage && pinEl && spacerEl) {
      const base = $("[data-isar-base]", stage);
      const blur = $("[data-isar-blur]", stage);
      const part = (n: string) => $(`[data-isar-part="${n}"]`, stage);
      const rail = part("rail");
      const kpi = part("kpi");
      const pagar = part("pagar");
      const diagram = part("diagram");
      const parts = [rail, kpi, pagar, diagram].filter(Boolean) as HTMLElement[];
      const svg = $<HTMLElement>("[data-isar-lines]", pinEl);
      const lines = svg ? [...svg.querySelectorAll<SVGLineElement>("line")] : [];
      const dots = svg ? [...svg.querySelectorAll<SVGCircleElement>("circle")] : [];
      const pts = $$("[data-isar-pt]", pinEl);
      const marks = [kpi, pagar, diagram].filter(Boolean) as HTMLElement[]; // en förklaring per lyft del, i ordning
      if (base && blur && parts.length === 4) {
        // konstanter för stängningarna nedan: TS tappar annars att de inte är null
        const baseEl = base;
        const blurEl = blur;
        const [railEl, kpiEl, pagarEl, diagramEl] = parts;
        const mm = gsap.matchMedia();
        mm.add({ desk: "(min-width: 1024px)", mob: "(max-width: 1023px)" }, (c) => {
          const desk = !!c.conditions?.desk;
          const u = desk ? 1 : 0.6; // lyftet i skärmens skala
          const moving = [baseEl, blurEl, ...parts];
          // pin 1.9 vh på desktop. hel .00-.18 · isär .18-.46 · linjerna ritas .42-.62 · hålls till .76 ·
          // linjerna släpps .76-.82 · ihop .80-.97. Samma p ger samma bild åt båda hållen (scrub).
          const K = {
            dim: [[0, 0], [0.18, 0], [0.46, 1], [0.76, 1], [0.97, 0]] as Keys,
            zr: [[0, 0], [0.18, 0], [0.44, 50 * u], [0.78, 50 * u], [0.96, 0]] as Keys,
            zk: [[0, 0], [0.21, 0], [0.47, 110 * u], [0.78, 110 * u], [0.955, 0]] as Keys,
            zp: [[0, 0], [0.24, 0], [0.5, 70 * u], [0.78, 70 * u], [0.95, 0]] as Keys,
            zd: [[0, 0], [0.27, 0], [0.53, 140 * u], [0.78, 140 * u], [0.945, 0]] as Keys,
            yk: [[0, 0], [0.21, 0], [0.47, -7], [0.78, -7], [0.955, 0]] as Keys,
            yd: [[0, 0], [0.27, 0], [0.53, 5], [0.78, 5], [0.945, 0]] as Keys,
            on: [0, 1, 2].map((i) => [[0, 0], [0.42 + i * 0.06, 0], [0.5 + i * 0.06, 1], [0.76, 1], [0.82, 0]] as Keys),
            // förklaringarna tänds med sin linje men släcks inte med den: efter akten ska texten
            // stå läsbar, inte dämpad som avstängd (Anton 2026-10-19, "poleras ytterligare")
            pt: [0, 1, 2].map((i) => [[0, 0], [0.42 + i * 0.06, 0], [0.5 + i * 0.06, 1]] as Keys)
          };
          const proxy = { p: 0 };
          let last = -1;
          // Linjernas geometri, mätt en gång per refresh med offset* (som bortser från transforms,
          // alltså också från ankomstens förskjutning) i stället för getBoundingClientRect per
          // bildruta: läsningarna efter stilskrivningarna tvingade fram en ny layout varje
          // bildruta, och det var det som hackade. Delarnas läge räknas ur perspektivet.
          type Geo = { sx: number; sy: number; w: number; h: number; pts: { x: number; y: number }[]; boxes: number[][] };
          let geo: Geo | null = null;
          const offIn = (el: HTMLElement) => {
            let x = 0;
            let y = 0;
            for (let n: HTMLElement | null = el; n && n !== pinEl; n = n.offsetParent as HTMLElement | null) { x += n.offsetLeft; y += n.offsetTop; }
            return { x, y };
          };
          const css = (el: HTMLElement, v: string) => parseFloat(el.style.getPropertyValue(v));
          function measure(): Geo {
            const s = offIn(baseEl.parentElement as HTMLElement);
            return {
              sx: s.x, sy: s.y, w: baseEl.offsetWidth, h: baseEl.offsetHeight,
              pts: pts.map((pt) => { const o = offIn(pt); return { x: o.x - 14, y: o.y + Math.min(pt.offsetHeight, 24) / 2 }; }),
              boxes: marks.map((mk) => ["--cx", "--cy", "--cw", "--ch"].map((v) => css(mk, v)))
            };
          }
          const PERSPECTIVE = 1600; // .isar__stage
          function renderStage() {
            const p = proxy.p;
            if (p === last) return;
            last = p;
            const dim = at(K.dim, p);
            baseEl.style.opacity = (1 - 0.7 * dim).toFixed(3);
            blurEl.style.opacity = (0.55 * dim).toFixed(3);
            railEl.style.transform = `translateZ(${at(K.zr, p).toFixed(2)}px)`;
            kpiEl.style.transform = `translate3d(0, ${at(K.yk, p).toFixed(3)}%, ${at(K.zk, p).toFixed(2)}px)`;
            pagarEl.style.transform = `translateZ(${at(K.zp, p).toFixed(2)}px)`;
            diagramEl.style.transform = `translate3d(0, ${at(K.yd, p).toFixed(3)}%, ${at(K.zd, p).toFixed(2)}px)`;
            pts.forEach((pt, i) => pt.style.setProperty("--on", at(K.pt[i], p).toFixed(3)));
            if (!desk || !svg) return;
            const g = (geo ??= measure());
            const zs = [at(K.zk, p), at(K.zp, p), at(K.zd, p)];
            const ys = [at(K.yk, p), 0, at(K.yd, p)];
            marks.forEach((_, i) => {
              const on = at(K.on[i], p);
              const ln = lines[i];
              const dot = dots[i];
              const pt = g.pts[i];
              if (!ln || !dot || !pt) return;
              ln.style.strokeDashoffset = (1 - on).toFixed(4);
              dot.style.opacity = on > 0.02 ? Math.min(1, on * 3).toFixed(3) : "0";
              if (on <= 0) return;
              // från förklaringens vänsterkant (texten står till höger om bilden) till den lyfta delens
              // högerkant, i delens höjdmitt: ingen linje korsar den mörka rälen. translateZ skalar
              // delen kring scenens mitt med perspektiv / (perspektiv - z).
              const [cx, cy, cw, ch] = g.boxes[i];
              const k = PERSPECTIVE / (PERSPECTIVE - zs[i]);
              const right = (cx + cw) * g.w;
              const mid = (cy + ch / 2 + (ys[i] / 100) * ch) * g.h;
              const x2 = g.sx + g.w / 2 + (right - g.w / 2) * k + 10;
              const y2 = g.sy + g.h / 2 + (mid - g.h / 2) * k;
              ln.setAttribute("x1", pt.x.toFixed(1)); ln.setAttribute("y1", pt.y.toFixed(1));
              ln.setAttribute("x2", x2.toFixed(1)); ln.setAttribute("y2", y2.toFixed(1));
              dot.setAttribute("cx", x2.toFixed(1)); dot.setAttribute("cy", y2.toFixed(1));
            });
          }
          const onToggle = (self: { isActive: boolean }) => { const w = self.isActive ? "transform, opacity" : "auto"; moving.forEach((m) => { m.style.willChange = w; }); };
          const tl = gsap.timeline({ scrollTrigger: desk
            // ingen anticipatePin: den förflyttar pinnen en bildruta i förväg för vanlig skroll,
            // och mot Lenis mjukade skroll blev det ett ryck i sidled vid pinnens start
            ? { trigger: pinEl, start: "top 10%", end: () => "+=" + Math.round(innerHeight * 1.9), pin: true, pinSpacer: spacerEl, scrub: true, invalidateOnRefresh: true, onToggle, onRefresh: () => { last = -1; geo = null; } }
            : { trigger: stage, start: "top 78%", end: "bottom 30%", scrub: true, invalidateOnRefresh: true, onToggle } });
          tl.fromTo(proxy, { p: 0 }, { p: 1, ease: "none", duration: 1 }).set({}, {}, 1);
          gsap.ticker.add(renderStage);
          renderStage();
          return () => {
            gsap.ticker.remove(renderStage);
            moving.forEach((m) => m.removeAttribute("style"));
            pts.forEach((pt) => pt.style.removeProperty("--on"));
            lines.forEach((l) => { l.style.strokeDashoffset = "1"; });
            dots.forEach((d) => { d.style.opacity = "0"; });
          };
        });
      }
    }

    // tangentbord: ett fokuserat element visas alltid, även före sitt avslöjande
    const onFocus = (e: FocusEvent) => {
      for (let n = e.target as HTMLElement | null; n && n !== document.body; n = n.parentElement) {
        if (shows.has(n)) play(n);
        else if (getComputedStyle(n).opacity === "0") gsap.set(n, { opacity: 1 });
      }
    };
    rootEl.addEventListener("focusin", onFocus);
    cleanups.push(() => rootEl.removeEventListener("focusin", onFocus));

    // säkringen: det som står i eller ovanför vyn och ännu väntar visas efter 2,5 s
    timers.push(
      window.setTimeout(() => {
        shows.forEach((_, el) => { if (el.getBoundingClientRect().top < innerHeight) play(el); });
      }, REVEAL_FAILSAFE_MS)
    );

    computeKeys();
    render();
    // Sidordning före refresh: avslöjandena skapas före översiktens pin, även de som ligger
    // nedanför den, och refresh i skapandeordning räknade deras start utan pinnens höjd
    // (fasadbandet var helt framme en hel pinnlängd för tidigt, uppmätt 2026-10-19).
    ScrollTrigger.sort();
    ScrollTrigger.refresh();
  }, rootEl);

  return () => {
    timers.forEach((t) => window.clearTimeout(t));
    cleanups.forEach((fn) => fn());
    ctx.revert();
  };
}
