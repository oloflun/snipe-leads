// Typerna för gsap.js (allowJs är av). `import "gsap"` drar in gsap/types/index.d.ts,
// som deklarerar den ambienta modulen "gsap/all" med alla plugin-exporter.
import "gsap";

// Bara det gsap.js faktiskt exporterar (se filens huvud): en plugin som inte är
// registrerad där ska inte heller gå att importera härifrån utan typfel.
export { gsap, ScrollTrigger, SplitText } from "gsap/all";

/** Apples fjäder som GSAP-ease: dämpning (< 1 studsar) och respons i sekunder. */
export function spring(damping: number, response: number): { ease: (t: number) => number; duration: number };
