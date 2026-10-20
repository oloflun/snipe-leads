// The project's ONE GSAP entry. Every other file imports from here:
//   import { gsap, ScrollTrigger, SplitText } from "./gsap.js";
// gsap resolves to the machine's global install through `npm link gsap lenis`
// (design skill: scripts/motion/link_motion.py). Never npm install gsap, never
// register a plugin anywhere else.
import {
  gsap,
  ScrollTrigger,
  ScrollToPlugin,
  ScrollSmoother,
  SplitText,
  ScrambleTextPlugin,
  TextPlugin,
  DrawSVGPlugin,
  MorphSVGPlugin,
  MotionPathPlugin,
  MotionPathHelper,
  Flip,
  Draggable,
  InertiaPlugin,
  Observer,
  CustomEase,
  CustomBounce,
  CustomWiggle,
  EasePack,
  Physics2DPlugin,
} from "gsap/all";

gsap.registerPlugin(
  ScrollTrigger,
  ScrollToPlugin,
  ScrollSmoother, // ponytail: registered, but never ScrollSmoother.create() on a page that runs Lenis - one scroll owner
  SplitText,
  ScrambleTextPlugin,
  TextPlugin,
  DrawSVGPlugin,
  MorphSVGPlugin,
  MotionPathPlugin,
  MotionPathHelper,
  Flip,
  Draggable,
  InertiaPlugin,
  Observer,
  CustomEase,
  CustomBounce,
  CustomWiggle,
  Physics2DPlugin,
);

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

export {
  gsap,
  ScrollTrigger,
  ScrollToPlugin,
  ScrollSmoother,
  SplitText,
  ScrambleTextPlugin,
  TextPlugin,
  DrawSVGPlugin,
  MorphSVGPlugin,
  MotionPathPlugin,
  MotionPathHelper,
  Flip,
  Draggable,
  InertiaPlugin,
  Observer,
  CustomEase,
  CustomBounce,
  CustomWiggle,
  EasePack,
  Physics2DPlugin,
};
