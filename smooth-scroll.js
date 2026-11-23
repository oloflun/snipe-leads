// The project's ONE Lenis instance, driven by GSAP's ticker. Import once, early:
//   import lenis from "./smooth-scroll.js";
// CSS: bundlers `import "lenis/dist/lenis.css"` in the app entry; static HTML
// links node_modules/lenis/dist/lenis.css (importmap: design skill,
// references/scroll/toolchain.md).
// House values, not Lenis defaults (references/scroll/devices.md, measured):
//   respectReducedMotion:false - motion always plays (F-011)
//   anchors:true               - in-page links keep working
//   autoRaf:false              - gsap.ticker is the only RAF loop
//   lerp .075 / wheel .6       - house pace (Anton 2026-09-25)
//   lagSmoothing(500, 33)      - not 0: one stalled frame made scrollTo jump 490-724 px (V3g)
//
// THE FALLBACK TO NATIVE SCROLL (2026-11-23, see docs/BESLUT.md).
// Lenis moves the page from the main thread: every scrolled frame is a script
// run, a style pass and a new layer split, measured at about 17 ms a frame on a
// CPU throttled four times, with nothing on the page animating. That is the whole
// frame budget, so on a slow or busy machine frames drop, and because the scroll
// position itself is what is being animated, a dropped frame is a visible stutter.
// The browser's own scroll runs on the compositor and does not stutter when the
// main thread is busy; the same measurement costs a third as much.
//
// So Lenis stays the house scroll wherever it holds its frame rate, and steps
// aside where it does not. `vakta()` counts slow frames at two moments: during the
// first seconds of the page (the door animation is a fair sample of what the
// machine can do, and a visitor who has not scrolled yet never sees the stutter),
// and afterwards while the page is being scrolled. It calls `tillNativ()` when the
// share of dropped frames among the last sixty passes the limit for that moment.
// The choice is remembered for the browser session, so the next page does not
// stutter first and learn again. Nothing else changes: ScrollTrigger reads the
// browser's scroll events either way.
import Lenis from "lenis";
import { gsap, ScrollTrigger } from "./gsap.js";

const MINNE = "snajp:nativ-scroll";
const FONSTER = 60; // scrolled frames looked at
const TAPPAD_MS = 25; // slower than this at 60 Hz means at least one frame was skipped
const GRANS = 0.2; // share of dropped frames, while scrolling, that hands the scroll back to the browser
// The opening is busier than a scroll (hydration, fonts, the motion setup), so a healthy
// machine drops some frames there too: the limit is higher, and only a full window counts.
const OPPNING_S = 4;
const OPPNING_GRANS = 0.35;

function minns() {
  try {
    return sessionStorage.getItem(MINNE) === "1";
  } catch {
    return false; // storage blocked: decide again on this page
  }
}

// One scroll owner, also across a dev server's hot reload: if this module is
// evaluated again while a Lenis already drives the window, reuse it. A second
// instance fought the first for scrollTop and read as jitter (2026-10-18).
const finns = typeof window !== "undefined";
const existing = finns ? window.__lenis : undefined;
const nativFranBorjan = finns && !existing && minns();
const lenis = existing || (nativFranBorjan ? null : new Lenis({
  autoRaf: false,
  anchors: true,
  respectReducedMotion: false,
  lerp: 0.075,
  wheelMultiplier: 0.6,
}));

let aktiv = !!lenis;
const drivare = (time) => { if (aktiv) lenis.raf(time * 1000); };

/** True while Lenis owns the scroll. False after the fallback, and on a page that started native. */
export function arMjuk() {
  return aktiv;
}

// Callers that hold on to the instance (the landing page's anchor scrolling) hear about the handover.
const lyssnare = new Set();

/** Run `fn` when the scroll goes native; at once if it already has. Returns an unsubscribe. */
export function vidNativ(fn) {
  if (!aktiv) {
    fn();
    return () => {};
  }
  lyssnare.add(fn);
  return () => lyssnare.delete(fn);
}

/** Hand the scroll back to the browser for the rest of the session. Safe to call twice. */
export function tillNativ() {
  if (!aktiv) return;
  aktiv = false;
  lyssnare.forEach((fn) => fn());
  lyssnare.clear();
  gsap.ticker.remove(drivare);
  gsap.ticker.remove(vakta);
  lenis.destroy();
  if (finns) {
    window.__lenis = undefined;
    // lenis.destroy() removes its own classes; these are the ones globals.css keys on.
    document.documentElement.classList.remove("lenis", "lenis-smooth", "lenis-scrolling", "lenis-stopped");
    try {
      sessionStorage.setItem(MINNE, "1");
    } catch {
      /* storage blocked: the page still scrolls natively until it is reloaded */
    }
  }
}

// Slow frames among the last FONSTER scrolled ones. A ring of flags, no allocation per frame.
const ring = new Uint8Array(FONSTER);
let plats = 0;
let fyllda = 0;
let tappade = 0;
let forstaTick = -1;
function vakta(time, deltaMs) {
  if (!aktiv) return;
  if (forstaTick < 0) forstaTick = time;
  const oppning = time - forstaTick < OPPNING_S;
  if (!oppning && !lenis.isScrolling) return;
  // A frame longer than a quarter of a second is a tab that was in the background, not a slow machine.
  if (deltaMs > 250) return;
  const tappad = deltaMs > TAPPAD_MS ? 1 : 0;
  tappade += tappad - ring[plats];
  ring[plats] = tappad;
  plats = (plats + 1) % FONSTER;
  if (fyllda < FONSTER) fyllda += 1;
  if (fyllda === FONSTER && tappade / FONSTER >= (oppning ? OPPNING_GRANS : GRANS)) tillNativ();
}

if (lenis && !existing) {
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add(drivare);
  gsap.ticker.add(vakta);
  gsap.ticker.lagSmoothing(500, 33);
  if (finns) window.__lenis = lenis; // jump tests: lenis.scrollTo(el, { immediate: true })
}

export default lenis;
