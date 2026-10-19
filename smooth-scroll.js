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
import Lenis from "lenis";
import { gsap, ScrollTrigger } from "./gsap.js";

// One scroll owner, also across a dev server's hot reload: if this module is
// evaluated again while a Lenis already drives the window, reuse it. A second
// instance fought the first for scrollTop and read as jitter (2026-10-18).
const existing = typeof window !== "undefined" ? window.__lenis : undefined;
const lenis = existing || new Lenis({
  autoRaf: false,
  anchors: true,
  respectReducedMotion: false,
  lerp: 0.075,
  wheelMultiplier: 0.6,
});

if (!existing) {
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(500, 33);
  if (typeof window !== "undefined") window.__lenis = lenis; // jump tests: lenis.scrollTo(el, { immediate: true })
}

export default lenis;
