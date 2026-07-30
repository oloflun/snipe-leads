"use client";

import { useEffect } from "react";

/**
 * Adds `is-visible` to every `.rise` element as it enters the viewport.
 *
 * One observer for the whole page rather than a hook per component, and it
 * unobserves on first reveal so scrolling back up does not re-animate. Under
 * prefers-reduced-motion the stylesheet zeroes the transition, so elements
 * simply appear.
 *
 * The failure mode is the whole design here. `.rise` starts at `opacity: 0`, so
 * anything this hook misses stays INVISIBLE — a section heading with nothing
 * under it. That shipped once. Three guards now make the failure direction
 * over-revealed rather than half empty:
 *
 *   1. `threshold: 0`. An element taller than the viewport can never reach a
 *      ratio of 0.08, because the ratio is capped at viewportHeight divided by
 *      elementHeight. A non-zero threshold silently excludes tall sections.
 *   2. Anything already on screen or above it at mount is revealed immediately.
 *      Land mid-page from a restored scroll position or an anchor and everything
 *      above never intersects again.
 *   3. A 1200ms failsafe reveals whatever is left.
 */
export function useReveal(): void {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(".rise"));
    if (nodes.length === 0) return;

    const show = (n: Element) => n.classList.add("is-visible");

    if (!("IntersectionObserver" in window)) {
      nodes.forEach(show);
      return;
    }

    // Guard 2.
    nodes.forEach((n) => {
      if (n.getBoundingClientRect().top < window.innerHeight) show(n);
    });

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            show(entry.target);
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0 }
    );

    nodes.forEach((n) => {
      if (!n.classList.contains("is-visible")) io.observe(n);
    });

    // Guard 3.
    const failsafe = window.setTimeout(() => nodes.forEach(show), 1200);

    return () => {
      window.clearTimeout(failsafe);
      io.disconnect();
    };
  }, []);
}
