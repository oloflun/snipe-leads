// Typerna för smooth-scroll.js (allowJs är av): projektets ENDA Lenis-instans.
import type Lenis from "lenis";

/** null på en sida som startat med webbläsarens egen scroll (se smooth-scroll.js). */
declare const lenis: Lenis | null;
export default lenis;

/** Sant medan Lenis äger scrollen. */
export function arMjuk(): boolean;
/** Lämnar över scrollen till webbläsaren för resten av besöket. */
export function tillNativ(): void;
/** Kör `fn` när scrollen blir webbläsarens egen; genast om den redan är det. Returnerar en avanmälan. */
export function vidNativ(fn: () => void): () => void;
