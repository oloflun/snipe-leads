"use client";

import { useLayoutEffect } from "react";

const ARMED = "reveal-armed";
/** Hur länge ett enskilt element får vara dolt innan det avslöjas ändå. */
const REVEAL_DEADLINE_MS = 1200;

/**
 * Adds `is-visible` to every `.rise` element as it enters the viewport.
 *
 * One observer for the whole page rather than a hook per component, and it
 * unobserves on first reveal so scrolling back up does not re-animate.
 *
 * ## The failure direction is the whole design here
 *
 * `.rise` content shipped permanently blank twice — a section heading with
 * nothing under it. Both times the cause had the same shape: the stylesheet
 * made INVISIBLE the default, so revealing was a JS action that had to
 * succeed, and any element this hook never saw stayed hidden forever.
 *
 * That is now inverted. The stylesheet only hides `.rise` while `<html>`
 * carries `reveal-armed`, which this hook adds before first paint and owns for
 * as long as it is running. Every path where the hook does not run — no JS,
 * blocked JS, hook not mounted on a route, an exception during mount — leaves
 * the page fully legible without animation.
 *
 * On top of that, four guards make a *missed element* impossible while the
 * hook IS running:
 *
 *   1. `threshold: 0`. An element taller than the viewport can never reach a
 *      ratio of 0.08, because the ratio is capped at viewportHeight divided by
 *      elementHeight. A non-zero threshold silently excludes tall sections.
 *   2. Anything already on screen or above it at mount is revealed immediately.
 *      Land mid-page from a restored scroll position or an anchor and everything
 *      above never intersects again.
 *   3. A MutationObserver registers `.rise` nodes added AFTER mount. The old
 *      version snapshotted the DOM once, so anything rendered later was never
 *      observed and never covered by the failsafe either.
 *   4. A per-node deadline reveals anything still hidden after
 *      REVEAL_DEADLINE_MS — including nodes that appeared long after load.
 *
 * useLayoutEffect, not useEffect: `reveal-armed` has to land before the browser
 * paints, otherwise the first frame shows the content and the second hides it.
 */
export function useReveal(): void {
  useLayoutEffect(() => {
    const root = document.documentElement;
    const show = (n: Element) => n.classList.add("is-visible");

    if (!("IntersectionObserver" in window) || !("MutationObserver" in window)) {
      return; // aldrig armerad => allt är synligt via CSS
    }

    root.classList.add(ARMED);

    const timers = new Set<number>();
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

    const register = (node: HTMLElement) => {
      if (node.classList.contains("is-visible")) return;
      // Guard 2.
      if (node.getBoundingClientRect().top < window.innerHeight) {
        show(node);
        return;
      }
      io.observe(node);
      // Guard 4 — per nod, så sent tillagda element också täcks.
      timers.add(window.setTimeout(() => show(node), REVEAL_DEADLINE_MS));
    };

    document.querySelectorAll<HTMLElement>(".rise").forEach(register);

    // Guard 3.
    const mo = new MutationObserver((records) => {
      records.forEach((record) => {
        record.addedNodes.forEach((added) => {
          if (!(added instanceof HTMLElement)) return;
          if (added.classList.contains("rise")) register(added);
          added.querySelectorAll<HTMLElement>(".rise").forEach(register);
        });
      });
    });
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      timers.forEach((t) => window.clearTimeout(t));
      mo.disconnect();
      io.disconnect();
      // Lämna aldrig sidan armerad utan något som avslöjar den.
      root.classList.remove(ARMED);
    };
  }, []);
}
