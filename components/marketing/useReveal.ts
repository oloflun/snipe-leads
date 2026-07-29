"use client";

import { useEffect } from "react";

/**
 * Adds `is-visible` to every `.rise` element as it enters the viewport.
 *
 * One observer for the whole page rather than a hook per component, and it
 * unobserves on first reveal so scrolling back up does not re-animate. Under
 * prefers-reduced-motion the stylesheet zeroes the transition, so elements
 * simply appear.
 */
export function useReveal(): void {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(".rise"));
    if (nodes.length === 0) return;

    if (!("IntersectionObserver" in window)) {
      nodes.forEach((n) => n.classList.add("is-visible"));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
    );

    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);
}
