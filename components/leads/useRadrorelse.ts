"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

/** DESIGN.md § Motion: --dur-mid och --ease-out. */
const DUR_MID = 300;
const EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)";
const MARKERING = 900;

/**
 * Rörelse för en lista som uppdateras live (Sebbe 2026-10-07: "så man ser hur
 * de flyttas och granskas"). Tre saker, alla med Web Animations API så att
 * ingen klass behöver tas bort efteråt:
 *
 * - Ny rad (ett id som inte fanns i förra datat) glider in med en ockraton.
 * - Rad som bytt plats (sorteringen ändrades, t.ex. när researchen gav
 *   poäng) glider från sin gamla plats till den nya — FLIP mot förra
 *   renderingens offsetTop, som inte påverkas av scroll.
 * - Rad som bytt status blinkar till i ockra och tonar tillbaka.
 *
 * Bara ny DATA animeras (kritiken 2026-10-07): när användaren själv byter
 * filter är det inte en nyhet att raderna flyttar, och glidningen följde
 * hans egna klick. Arrayen `rader` byts bara när datat hämtats om, så dess
 * identitet skiljer en datauppdatering från ett filterbyte.
 *
 * Tiderna är DESIGN.md:s (--dur-mid 300 ms, --ease-out). Färgmarkeringen
 * tonar längre, 900 ms: den är en markering som ska hinna ses, inte en rörelse.
 *
 * Första datat animeras aldrig (det vore hela listan som flimrade vid
 * sidladdning). `prefers-reduced-motion` stänger av glidningarna men inte
 * färgmarkeringen: en färg som tonar rör sig inte, och utan den syns inte
 * flytten alls för den som slagit av Windows animeringseffekter (uppmätt i
 * webbläsarpanelen 2026-10-07).
 *
 * Raderna märks med `data-rad-id`. Dolda varianter (tabellen när korten
 * visas och tvärtom) har offsetParent null och hoppas över.
 */
export function useRadrorelse(
  behallare: RefObject<HTMLElement | null>,
  rader: readonly { id: string; status: string }[] | null
): void {
  const positioner = useRef(new Map<string, number>());
  const forraStatus = useRef<Map<string, string> | null>(null);
  const forraRader = useRef(rader);

  // Utan beroendelista med flit: positionerna ska mätas efter VARJE
  // rendering, annars blir "First" i FLIP en gammal mätning.
  useLayoutEffect(() => {
    const rot = behallare.current;
    if (!rot || rader === null) return;
    const lugn = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const forra = forraStatus.current;
    const nu = new Map(rader.map((r) => [r.id, r.status]));
    const andrat = forra === null || forra.size !== nu.size || [...nu].some(([id, s]) => forra.get(id) !== s);
    const nyttData = rader !== forraRader.current;
    forraRader.current = rader;
    const ton = ockra();
    const nyaPositioner = new Map<string, number>();

    for (const el of rot.querySelectorAll<HTMLElement>("[data-rad-id]")) {
      if (el.offsetParent === null) continue;
      const id = el.dataset.radId;
      if (!id) continue;
      const topp = el.offsetTop;
      nyaPositioner.set(id, topp);
      if (forra === null || typeof el.animate !== "function") continue;

      const bas = getComputedStyle(el).backgroundColor;
      if (!forra.has(id)) {
        // Rörelsen i husets takt, markeringen för sig och längre.
        if (!lugn) {
          el.animate([{ opacity: 0, transform: "translateY(-8px)" }, { opacity: 1, transform: "none" }], {
            duration: DUR_MID,
            easing: EASE_OUT
          });
        }
        el.animate([{ backgroundColor: ton }, { backgroundColor: ton, offset: 0.3 }, { backgroundColor: bas }], {
          duration: MARKERING,
          easing: EASE_OUT
        });
        continue;
      }
      const fran = positioner.current.get(id);
      if (nyttData && !lugn && fran !== undefined && fran !== topp && Math.abs(fran - topp) < 4000) {
        el.animate([{ transform: `translateY(${fran - topp}px)` }, { transform: "none" }], {
          duration: DUR_MID,
          easing: EASE_OUT
        });
      }
      if (andrat && forra.get(id) !== nu.get(id)) {
        el.animate([{ backgroundColor: ton }, { backgroundColor: bas }], { duration: MARKERING, easing: EASE_OUT });
      }
    }

    positioner.current = nyaPositioner;
    if (andrat) forraStatus.current = nu;
  });
}

function ockra(): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue("--ochre").trim();
  return v ? `oklch(${v} / 0.22)` : "rgba(214, 160, 60, 0.22)";
}
