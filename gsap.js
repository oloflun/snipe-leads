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
