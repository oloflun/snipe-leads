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
  // Startsidan (Startsida.tsx) har inga produktbilder och ingen #demo: där bär agenternas sektioner ljuset.
  ["soluppgang", "[data-mo=\"hero\"]", 0],
  ["morgon", "[data-mo=\"produktbilder\"], #iris", -0.5],
  ["formiddag", "#demo, #support", -0.2],
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
      teardown = setup({ gsap, ScrollTrigger, SplitText, spring } as Gsap, rootEl, firstRun && !doorPlayed, lenis);
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

// Startsidans flöde (data-mo="steg" och rader med data-full). Varje sak börjar i samma
// ögonblick som den står helt i bild. Ingen kö i tid: kön (0,6 s per sak) lät innehållet
// halka efter skrollen och lämnade tomma skärmar (Anton 2026-11-09). Det som når bilden
// i samma bildruta får bara ett kort steg emellan, så att det läses som en följd.
const STEG_STEG = 0.07;
const STEG_TID = 0.55;
// Hjältens ytor (data-mo="svav"): första ytan när rubriken skrivit sina första ord, nästa
// när den förra har landat. Hela hjälten står inom drygt två sekunder.
const SVAV_START = 0.7;
const SVAV_GAP = 0.8;
const SVAV_TEXT = 0.6;
const SVAV_FAILSAFE_MS = 6000;

function setup(G: Gsap, rootEl: HTMLElement, fullDoor: boolean, lenis: Lenis): () => void {
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
    // Startsidan (Startsida.tsx): sidhuvudet står från första målningen och ingressen
    // reser sig rad för rad, i stället för att tonas upp sent som en sida som laddar.
    const hem = !!$("[data-mo=\"svav\"]");
    let visaIngress = () => {};

    if (h1) {
      const late = (hem ? [] : [lede, acts, side, header]).filter(Boolean) as HTMLElement[];
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
          h1.dispatchEvent(new Event("hero:type"));
          gsap.set(late, { opacity: 1, y: 0 });
          visaIngress();
          if (heroImg) gsap.set(heroImg, { scale: 1 });
          if (heroScrim) gsap.set(heroScrim, { opacity: 1 });
          door.on = 1;
        }, DOOR_FAILSAFE_MS)
      );
      // Rubriken skrivs fram (HeroText i LiveText.tsx) i stället för att radspaltas
      // (Anton 2026-10-19). Fonterna väntas in så att de osynliga tecknen redan
      // står i rätt bredd när skrivningen börjar.
      document.fonts.ready.then(() => ctx.add(() => {
        if (h1.dataset.door) return;
        h1.dataset.door = "1";
        gsap.set(h1, { autoAlpha: 1 });
        h1.dispatchEvent(new Event("hero:type"));
        if (doorShown) {
          gsap.to(door, { on: 1, duration: 1.2 });
          return;
        }
        if (!fullDoor) { visaIngress(); return; }
        const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
        if (heroImg) tl.to(heroImg, { scale: 1, duration: 2.2, ease: "power2.out" }, 0);
        if (heroScrim) tl.to(heroScrim, { opacity: 1, duration: 1.4, ease: "power2.inOut" }, 0);
        if (late.length) tl.to(late, { opacity: 1, y: 0, duration: 0.8, stagger: 0.1 }, 1.2);
        tl.call(() => visaIngress(), [], 0.45)
          .to(door, { on: 1, duration: 1.6, ease: "power2.inOut" }, 1.0);
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
    // Helt i bild (startsidans flöde, Anton 2026-11-07: inget får börja "innan det är
    // fullt synligt"). Ett element som är högre än skärmen kan aldrig stå helt i bild;
    // det startar när en bra bit av det syns i stället för först vid sin nederkant.
    const ioHel = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) play(e.target as HTMLElement);
    }, { rootMargin: "0px 0px -4% 0px", threshold: 1 });
    cleanups.push(() => ioHel.disconnect());
    // Det som är lägre än knappt halva skärmen väntar tills det står helt i bild. Det som
    // är högre startar när överkanten nått en bit upp: att vänta in hela höjden lät
    // läsaren skrolla förbi tom yta.
    const ryms = (el: HTMLElement) => el.offsetHeight < innerHeight * 0.45;
    // arm: dölj en gång, visa en gång. Tre vägar till play, alla idempotenta.
    // hel: starta först helt i bild (startsidans flöde). `start` gäller annars, och med
    // utanIo är ScrollTrigger ensam utlösare (io eldar redan vid 92 %).
    function arm(el: HTMLElement, hide: () => void, show: () => void, start = "top 88%", hel = false, utanIo = false) {
      if (revealed(el)) return;
      hide();
      shows.set(el, show);
      const helt = hel && ryms(el);
      ScrollTrigger.create({ trigger: el, start: hel ? (helt ? "bottom 96%" : "top 62%") : start, once: true, onEnter: () => play(el) });
      if (hel) { if (helt) ioHel.observe(el); }
      else if (!utanIo) io.observe(el);
    }
    // Ett kort steg mellan det som når bilden i samma bildruta (STEG_STEG), aldrig en kö.
    let slotTid = -1;
    let slotN = 0;
    const slot = () => {
      const now = gsap.ticker.time;
      if (now - slotTid > 0.05) { slotTid = now; slotN = 0; }
      return Math.min(slotN++, 6) * STEG_STEG;
    };

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
    const showLines = (el: HTMLElement, delay = 0) => gsap.to($$(".ln", el), { yPercent: 0, duration: 0.9, ease: "power4.out", stagger: 0.07, delay });
    function headingLines(el: HTMLElement) {
      splitLines(el);
      // data-full (startsidans flöde): texten reser sig ur sina rader när den står helt i
      // bild. Den tonas aldrig: en toning läses som en sida som renderas (Anton 2026-11-09).
      if (el.hasAttribute("data-full")) arm(el, () => {}, () => showLines(el, slot()), "", true);
      else arm(el, () => {}, () => showLines(el));
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
      // data-full (startsidan): rutan glider in när en dryg tredjedel av den står i bild
      // (top 68 %), så att glidningen syns. Den är aldrig osynlig (spring-arrival): en ruta
      // som väntade dold tills hela höjden stod i bild lämnade skärmen tom (Anton 2026-11-09).
      const hel = el.hasAttribute("data-full");
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
      }, hel ? "top 68%" : wide ? "top 85%" : "top 90%", false, hel);
    }
    // ------------------------------------------- startsidans flöde (data-mo="steg")
    // Det i flödet som inte är löptext (talraden, länkraden): kommer upp i samma ögonblick
    // som det står helt i bild. Spelar en gång och skrubbas aldrig: inget backar eller
    // försvinner innan animationen är klar. Texten går genom headingLines (data-full).
    function steg(el: HTMLElement) {
      arm(el, () => {
        gsap.set(el, { opacity: 0, y: 20 });
        el.dataset.armerad = "1";
      }, () => {
        gsap.to(el, {
          opacity: 1, y: 0, duration: STEG_TID, ease: "power3.out", delay: slot(),
          // RaknaUpp (AgentResultat) väntar på den här innan talen räknas.
          onComplete: () => { el.dataset.visad = "1"; el.dispatchEvent(new Event("steg:visad")); }
        });
      }, "", true);
    }
    // ------------------------------------- kapitelrubriken (data-mo="kapitel", Startsida.tsx)
    // Agentens namn i displaygrad på bläck. Två lager som hör ihop: bokstäverna reser sig
    // en i taget ur sin rad när namnet står helt i bild, och ljuset från ett fönster faller
    // in över golvet i samma ögonblick och vandrar sedan med skrollen (skrubbat, åt båda
    // hållen). Löftet under namnet reser sig när namnet står.
    function kapitel(el: HTMLElement) {
      const namn = $("[data-kapitel-namn]", el);
      const rad = $("[data-kapitel-rad]", el);
      const ljus = $("[data-kapitel-ljus]", el);
      if (ljus) {
        const hoger = ljus.hasAttribute("data-hoger");
        gsap.fromTo(ljus, { xPercent: hoger ? 16 : -16, skewX: hoger ? 30 : -30 }, { xPercent: hoger ? -10 : 10, skewX: hoger ? 14 : -14, ease: "none",
          scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true } });
      }
      if (!namn) return;
      SplitText.create(namn, {
        aria: "none", type: "lines,chars", mask: "lines", linesClass: "ln", charsClass: "kb", autoSplit: true,
        onSplit(self) { if (!revealed(namn)) gsap.set(self.chars, { yPercent: 118 }); }
      });
      if (rad) splitLines(rad);
      arm(namn, () => { if (ljus) gsap.set(ljus, { opacity: 0 }); }, () => {
        gsap.to($$(".kb", namn), { yPercent: 0, duration: 1.05, ease: "power4.out", stagger: 0.045 });
        if (ljus) gsap.to(ljus, { opacity: 1, duration: 1.8, ease: "power2.out" });
        if (rad) { rad.dataset.rv = "1"; showLines(rad, 0.45); }
      }, "", true);
    }
    // --------------------------------------- hjältens ytor (data-mo="svav", Startsida.tsx)
    // Glider in på fjädern en i taget när rubriken skrivits en bit, skriver sitt utkast när de
    // landat, svävar sedan några pixlar i vila (F-045) och lutar sig mot pekaren.
    function svav(figurer: HTMLElement[]) {
      if (!figurer.length) return;
      const text = figurer.map((f) => $("[data-svav-text]", f)).filter(Boolean) as HTMLElement[];
      const dx = () => Math.min(180, innerWidth * 0.14);
      gsap.set(figurer, { x: dx, opacity: 0 });
      gsap.set(text, { opacity: 0, y: 12 });
      figurer.forEach((f) => f.dispatchEvent(new Event("case:armed")));
      const landad = figurer.map(() => false);
      let startad = false;
      const kom = (fordrojning: number) => {
        if (startad) return;
        startad = true;
        figurer.forEach((f, i) => {
          const tl = gsap.timeline({ delay: fordrojning + i * SVAV_GAP });
          tl.to(f, { x: 0, ease: ARRIVAL.ease, duration: ARRIVAL.duration, force3D: true }, 0)
            .to(f, { opacity: 1, duration: 0.35, ease: "power1.out" }, 0)
            .call(() => { landad[i] = true; f.dispatchEvent(new Event("case:landed")); }, [], SVAV_TEXT);
          const t = $("[data-svav-text]", f);
          if (t) tl.to(t, { opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }, SVAV_TEXT + 0.25);
        });
      };
      const h1 = $("[data-mo=\"hero-h1\"]");
      const onType = () => kom(SVAV_START);
      h1?.addEventListener("hero:type", onType);
      cleanups.push(() => h1?.removeEventListener("hero:type", onType));
      timers.push(window.setTimeout(() => kom(0), SVAV_FAILSAFE_MS));

      // Vilan: några pixlar och en halv grad över 4,6–5,8 s, i olika takt. Tonar ut medan
      // man skrollar och står still när hjälten är utanför skärmen.
      const hero = $("[data-mo=\"hero\"]");
      const lager = figurer.map((f, i) => {
        const flyt = $(".svav-flyt", f);
        return flyt && {
          y: gsap.quickSetter(flyt, "y", "px"), r: gsap.quickSetter(flyt, "rotation", "deg"),
          fas: i * 1.9, periodY: 4.6 + i * 0.7, periodR: 5.8 - i * 0.6, styrka: 0
        };
      });
      // Om hjälten syns avgörs av en utlösare, inte av en mätning per bildruta: en läsning
      // av layouten efter att rörelsen skrivit stilar tvingar fram en omräkning varje gång.
      let heroSyns = true;
      // onRefresh också: en sida som laddas nedanför hjälten (#iris) växlar aldrig läge,
      // och utan den avläsningen hade vilan fortsatt räkna på ytor som inte syns.
      if (hero) {
        const satt = (self: { isActive: boolean }) => { heroSyns = self.isActive; };
        ScrollTrigger.create({ trigger: hero, start: "top bottom", end: "bottom top", onToggle: satt, onRefresh: satt });
      }
      const vila = (tid: number) => {
        if (!heroSyns) return;
        const lugn = Math.max(0, 1 - Math.abs(lenis.velocity) / 6);
        lager.forEach((l, i) => {
          if (!l) return;
          l.styrka += ((landad[i] ? lugn : 0) - l.styrka) * 0.04;
          l.y(Math.sin((tid / l.periodY) * Math.PI * 2 + l.fas) * 6 * l.styrka);
          l.r(Math.sin((tid / l.periodR) * Math.PI * 2 + l.fas) * 0.45 * l.styrka);
        });
      };
      gsap.ticker.add(vila);
      cleanups.push(() => gsap.ticker.remove(vila));

      // Hovringen, bara med mus: ytan lutar sig mot pekaren, lyfts och skuggan djupnar (--lyft).
      if (!matchMedia("(hover: hover) and (pointer: fine)").matches) return;
      for (const f of figurer) {
        const lut = $(".svav-lut", f);
        const yta = $(".hem-yta", f);
        if (!lut || !yta) continue;
        gsap.set(lut, { transformPerspective: 900 });
        const rx = gsap.quickTo(lut, "rotationX", { duration: 0.7, ease: "power3.out" });
        const ry = gsap.quickTo(lut, "rotationY", { duration: 0.7, ease: "power3.out" });
        const in_ = () => { gsap.to(lut, { y: -8, scale: 1.02, duration: 0.6, ease: "power3.out" }); gsap.to(yta, { "--lyft": 1, duration: 0.6, ease: "power3.out" }); };
        const rör = (e: PointerEvent) => {
          const b = yta.getBoundingClientRect();
          ry(((e.clientX - b.left) / b.width - 0.5) * 7);
          rx(-((e.clientY - b.top) / b.height - 0.5) * 5);
        };
        const ut = () => { rx(0); ry(0); gsap.to(lut, { y: 0, scale: 1, duration: 0.8, ease: "power3.out" }); gsap.to(yta, { "--lyft": 0, duration: 0.8, ease: "power3.out" }); };
        yta.addEventListener("pointerenter", in_);
        yta.addEventListener("pointermove", rör);
        yta.addEventListener("pointerleave", ut);
        cleanups.push(() => { yta.removeEventListener("pointerenter", in_); yta.removeEventListener("pointermove", rör); yta.removeEventListener("pointerleave", ut); });
      }
    }
    function plate(el: HTMLElement) {
      // Fotot står helt från början, ingen avtäckning: en klippning som drogs
      // undan såg ut som en bild som laddade långsamt (Anton 2026-10-19).
      const img = el.querySelector<HTMLElement>("[data-parallax]");
      if (img) {
        gsap.set(img, { scale: 1.12 });
        gsap.fromTo(img, { yPercent: -5 }, { yPercent: 5, ease: "none",
          scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true } });
      }
    }
    function band(el: HTMLElement) {
      // bandet står helt, bara fotot glider (klippningen togs bort 2026-10-19, se plate)
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
    $$("[data-case]:not([data-mo=\"svav\"])").forEach(caseEntry);
    $$("[data-mo=\"steg\"]").forEach(steg);
    $$("[data-mo=\"kapitel\"]").forEach(kapitel);
    svav($$("[data-mo=\"svav\"]"));
    // Startsidans ingress: radspaltad här, visad av dörren (visaIngress).
    if (hem && lede) {
      splitLines(lede);
      visaIngress = () => {
        if (revealed(lede)) return;
        lede.dataset.rv = "1";
        showLines(lede);
      };
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
