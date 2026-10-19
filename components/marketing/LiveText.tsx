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

// Hjälterubrikens takt (Anton 2026-10-19: "långsammare och mer effektfullt").
// Ett andetag efter kommatecken, en paus före det betonade ordet och sedan
// det ordet i halv fart.
const RUBRIK_MS = 58;
const BETONAT_MS = 140;
const KOMMA_PAUS = 260;
const BETONING_PAUS = 650;

/**
 * Hjälterubriken, framskriven när dörren öppnas. `*ord*` är betoningen och
 * får accentfärgen. Rörelsen (useLandingMotion) skickar `hero:type` på
 * rubriken; kommer den inte inom 4 s skrivs den ändå. Utan JS står rubriken
 * hel. Skärmläsaren får hela rubriken direkt.
 */
export function HeroText({ text }: Readonly<{ text: string }>) {
  const delar = text.split(/\*([^*]+)\*/g).map((del, i) => ({ del, betonad: i % 2 === 1 }));
  const hel = delar.map((d) => d.del).join("");
  const sista = delar.findLastIndex((d) => d.betonad && d.del);
  const betoning = sista < 0 ? hel.length : delar.slice(0, sista).reduce((a, d) => a + d.del.length, 0);
  const ref = useRef<HTMLSpanElement | null>(null);
  const [n, setN] = useState(hel.length);

  useEffect(() => {
    const host = ref.current?.parentElement;
    // Ingen spärr för reducerad rörelse: inget förflyttas, tecknen tänds bara på
    // plats, som i rutornas LiveText. Windows med animationer avstängda rapporterar
    // reduce, och där hade rubriken annars aldrig skrivits.
    if (!host) return;
    setN(0);
    let id = 0;
    let startad = false;
    const skriv = () => {
      if (startad) return;
      startad = true;
      let i = 0;
      const steg = () => {
        i += 1;
        setN(i);
        if (i >= hel.length) return;
        let paus = i >= betoning ? BETONAT_MS : RUBRIK_MS;
        if (hel[i - 1] === ",") paus += KOMMA_PAUS;
        if (i === betoning) paus += BETONING_PAUS;
        id = window.setTimeout(steg, paus);
      };
      id = window.setTimeout(steg, 250);
    };
    const reserv = window.setTimeout(skriv, 4000);
    host.addEventListener("hero:type", skriv);
    return () => {
      window.clearTimeout(id);
      window.clearTimeout(reserv);
      host.removeEventListener("hero:type", skriv);
    };
  }, [hel, betoning]);

  let o = 0;
  let markor = false;
  return (
    <>
      <span className="sr-only">{hel}</span>
      <span ref={ref} aria-hidden="true">
        {delar.map(({ del, betonad }, i) => {
          const syns = Math.max(0, Math.min(del.length, n - o));
          const harMarkor = !markor && n < hel.length && n >= o && n <= o + del.length;
          if (harMarkor) markor = true;
          o += del.length;
          return (
            // text-ochre, inte text-warning: den mörkare ockran försvann mot solnedgången i fotot.
            <span key={i} className={betonad ? "italic-disp text-ochre" : undefined}>
              {del.slice(0, syns)}
              {harMarkor ? <span className="live-caret hero-caret" /> : null}
              <span className="invisible">{del.slice(syns)}</span>
            </span>
          );
        })}
      </span>
    </>
  );
}
