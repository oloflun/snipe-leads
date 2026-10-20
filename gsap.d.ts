// Typerna för gsap.js (allowJs är av). `import "gsap"` drar in gsap/types/index.d.ts,
// som deklarerar den ambienta modulen "gsap/all" med alla plugin-exporter.
import "gsap";

export * from "gsap/all";

/** Apples fjäder som GSAP-ease: dämpning (< 1 studsar) och respons i sekunder. */
export function spring(damping: number, response: number): { ease: (t: number) => number; duration: number };
