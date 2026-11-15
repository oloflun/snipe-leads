"use client";

import { useEffect } from "react";

/**
 * Räknar ett BESÖK på demon från en spårad demolänk (app/prova/[token]).
 *
 * Länken i utskicket skickar hit med `?besok=<token>`. Parametern tas bort ur
 * adressen direkt, så att den inte följer med när adressen kopieras eller
 * delas. Besöket skickas först vid första riktiga interaktionen: e-postskydd
 * öppnar länkar men skrollar och klickar inte, så ett besök betyder en
 * människa. Ingen synlig UI, och inget fel får nå besökaren.
 */

const HANDELSER = ["pointerdown", "keydown", "wheel", "touchstart", "scroll"] as const;
const TOKEN = /^[A-Za-z0-9_-]{6,64}$/;

function skicka(token: string): void {
  const adress = `/prova/${encodeURIComponent(token)}`;
  try {
    if (typeof navigator !== "undefined" && navigator.sendBeacon?.(adress)) return;
  } catch {
    // Faller tillbaka på fetch nedan.
  }
  try {
    void fetch(adress, { method: "POST", keepalive: true }).catch(() => undefined);
  } catch {
    // Ett tappat besök är bättre än ett fel hos besökaren.
  }
}

export function DemoBesok() {
  useEffect(() => {
    let token: string | null = null;
    try {
      const url = new URL(window.location.href);
      token = url.searchParams.get("besok");
      if (!token) return;
      url.searchParams.delete("besok");
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
    } catch {
      return;
    }
    if (!token || !TOKEN.test(token)) return;

    const flagga = `demobesok:${token}`;
    try {
      if (window.sessionStorage.getItem(flagga)) return;
    } catch {
      // Utan sessionStorage räknas besöket ändå, högst en gång per sidvisning.
    }

    const fast = token;
    let skickat = false;
    function taBort() {
      for (const h of HANDELSER) window.removeEventListener(h, vidInteraktion, true);
    }
    function vidInteraktion() {
      if (skickat) return;
      skickat = true;
      taBort();
      try {
        window.sessionStorage.setItem(flagga, "1");
      } catch {
        // Se ovan.
      }
      skicka(fast);
    }
    for (const h of HANDELSER) window.addEventListener(h, vidInteraktion, { capture: true, passive: true });
    return taBort;
  }, []);

  return null;
}
