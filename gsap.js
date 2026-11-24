// The project's ONE GSAP entry. Every other file imports from here:
//   import { gsap, ScrollTrigger, SplitText } from "./gsap.js";
// gsap resolves to the machine's global install through `npm link gsap lenis`
// (design skill: scripts/motion/link_motion.py). Never npm install gsap, never
// register a plugin anywhere else.
//
// ONLY THE PLUGINS THE SITE USES (2026-11-23). This file used to import
// "gsap/all" and register all eighteen plugins. A registered plugin cannot be
// tree-shaken, so every visitor to the start page downloaded and evaluated
// ScrollSmoother, MorphSVG, Draggable, Physics2D and the rest: 105 kB over the
// wire of which 68 kB was never run (Lighthouse, unused-javascript), and part of
// the 2.8 s this chunk cost a throttled phone at load. useLandingMotion uses
// gsap, ScrollTrigger and SplitText and nothing else.
//
// Need another plugin? Import it from its own module ("gsap/Flip") and add it to
// registerPlugin and the export list below, and to gsap.d.ts. Do not go back to
// "gsap/all".
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

gsap.registerPlugin(ScrollTrigger, SplitText);

// Apple's spring as a GSAP ease (apple-design § 4, Designing Fluid Interfaces):
// two designer parameters instead of mass/stiffness/damping. `damping` < 1
// overshoots and settles back (0.75 ≈ 2.8 % past the target), `response` is how
// fast it gets there in seconds. The duration is not chosen, it falls out of the
// physics: the time until the motion is within 0.1 % of rest.
//   const s = spring(0.75, 0.75); gsap.to(el, { x: 0, ease: s.ease, duration: s.duration });
export function spring(damping, response) {
  const w = (2 * Math.PI) / response;
  const wd = w * Math.sqrt(1 - damping * damping);
  const duration = Math.log(1000) / (damping * w);
  const ease = (t) => {
    if (t >= 1) return 1;
    const s = t * duration;
    return 1 - Math.exp(-damping * w * s) * (Math.cos(wd * s) + ((damping * w) / wd) * Math.sin(wd * s));
  };
  return { ease, duration };
}

export { gsap, ScrollTrigger, SplitText };
