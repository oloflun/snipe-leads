"use client";

import { useEffect, useRef, useState } from "react";
import { skrivFram } from "@/lib/skrivs";

/**
 * En text i en showcase-ruta som skrivs fram när rutan har landat.
 *
 * Rörelsen (useLandingMotion, caseEntry) skickar `case:armed` när rutan
 * förskjuts och `case:landed` när den har landat. Utan JS, eller om rutan
 * redan visats, kommer inga händelser och texten står hel. Resten av texten
 * finns kvar osynlig, så att rutan inte växer medan texten skrivs.
 */
export function LiveText({ text }: Readonly<{ text: string }>) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [n, setN] = useState(text.length);

  useEffect(() => {
    const host = ref.current?.closest("[data-case]");
    if (!host) return;
    let stop = () => {};
    const armed = () => {
      stop();
      setN(0);
    };
    const landed = () => {
      stop = skrivFram(text, (visad) => setN(visad.length));
    };
    host.addEventListener("case:armed", armed);
    host.addEventListener("case:landed", landed);
    return () => {
      stop();
      host.removeEventListener("case:armed", armed);
      host.removeEventListener("case:landed", landed);
    };
  }, [text]);

  return (
    <span ref={ref}>
      {text.slice(0, n)}
      {n > 0 && n < text.length ? <span className="live-caret" /> : null}
      <span className="invisible">{text.slice(n)}</span>
    </span>
  );
}
