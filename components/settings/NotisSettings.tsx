"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { btnPrimary } from "@/components/ui";
import { Vaxel } from "@/components/settings/Vaxel";
import { hamtaNotiser, sparaNotiser } from "@/lib/actions/notiser";
import { STANDARD, type Notishandelse, type Notisinstallningar } from "@/lib/notiser";

/**
 * Mejlnotiser — vill du bli störd, och av vad.
 *
 * ## Varför huvudväxeln inte döljer händelserna
 *
 * Det uppenbara vore att fälla ihop listan när notiser är avstängda. Effekten
 * är att den som slår PÅ notiser möts av ett tomt utrymme som plötsligt fylls,
 * och inte kan se vad hen tackar ja till förrän efter att ha tackat ja.
 * Raderna står kvar, nedtonade och inaktiva: valet syns, men går inte att röra
 * förrän frågan ovanför är besvarad.
 *
 * ## Varför det inte går att spara "på" utan någon händelse
 *
 * Servern tvingar ner huvudväxeln till av när listan är tom (se
 * lib/actions/notiser.ts). Knappen härmar den regeln i förväg i stället för att
 * låta kunden trycka Spara och få tillbaka ett annat värde än det på skärmen —
 * en växel som hoppar tillbaka efter sparning ser ut som en bugg, även när det
 * är regeln som är rätt.
 */

const HANDELSER: { nyckel: Notishandelse; etikett: string; beskrivning: string }[] = [
  {
    nyckel: "lead",
    etikett: "Nytt lead",
    beskrivning: "Ett mejl per kvalificerat bolag."
  },
  {
    nyckel: "escalation",
    etikett: "Eskalering",
    beskrivning: "Ett ärende lämnades över till dig."
  }
];

export function NotisSettings() {
  const [falt, setFalt] = useState<Notisinstallningar | null>(null);
  const [saknasSession, setSaknasSession] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [klart, setKlart] = useState<string | null>(null);

  useEffect(() => {
    let avbruten = false;
    void hamtaNotiser().then((rad) => {
      if (avbruten) return;
      // null betyder ingen session eller ingen databas — INTE "inga notiser".
      // Att rita standarden då hade visat en påslagen växel för någon vars val
      // ingenstans kan sparas.
      if (rad === null) {
        setSaknasSession(true);
        setFalt(STANDARD);
        return;
      }
      setFalt(rad);
    });
    return () => {
      avbruten = true;
    };
  }, []);

  if (falt === null) {
    return (
      <div className="grid gap-6" aria-busy="true">
        <div className="h-20 animate-pulse rounded-card bg-ink/[0.055]" />
        <div className="h-32 animate-pulse rounded-card bg-ink/[0.055]" />
      </div>
    );
  }

  function vaxlaHandelse(nyckel: Notishandelse, pa: boolean) {
    if (!falt) return;
    const handelser = pa
      ? [...falt.handelser, nyckel]
      : falt.handelser.filter((h) => h !== nyckel);
    // Sista rutan av = notiser av. Se docstringen: servern gör samma sak, och
    // två olika svar på samma klick är värre än regeln i sig.
    setFalt({ epost: handelser.length > 0 && falt.epost, handelser });
  }

  function vaxlaEpost(pa: boolean) {
    if (!falt) return;
    // Slås notiser på igen utan att någon händelse är vald återställs båda.
    // Alternativet är en växel som står på ON och inte skickar något.
    const handelser = pa && falt.handelser.length === 0 ? [...STANDARD.handelser] : falt.handelser;
    setFalt({ epost: pa, handelser });
  }

  async function spara() {
    if (!falt) return;
    setBusy(true);
    setFel(null);
    setKlart(null);
    try {
      const svar = await sparaNotiser(falt);
      if (!svar.success) {
        setFel(svar.error ?? "Kunde inte spara.");
        return;
      }
      setKlart(falt.epost ? "Sparat. Notiserna går till din inloggningsadress." : "Sparat.");
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte spara.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-7">
      <div className="border-t border-ink/15 pt-5">
        <Vaxel
          etikett="Mejla mig"
          pa={falt.epost}
          onChange={vaxlaEpost}
        />
      </div>

      <fieldset className="border-t border-ink/15 pt-5" disabled={!falt.epost}>
        <legend className="kicker text-mineral">Vad vi mejlar om</legend>

        {/* Nedtonad, inte gömd. Se docstringen: den som slår på notiser ska
            kunna se vad hen tackar ja till innan hen gör det. */}
        <div
          className={`mt-5 grid gap-5 transition-opacity ${falt.epost ? "" : "opacity-45"}`}
        >
          {HANDELSER.map((h) => (
            <Vaxel
              key={h.nyckel}
              etikett={h.etikett}
              beskrivning={h.beskrivning}
              pa={falt.handelser.includes(h.nyckel)}
              disabled={!falt.epost}
              onChange={(pa) => vaxlaHandelse(h.nyckel, pa)}
            />
          ))}
        </div>
      </fieldset>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-ink/15 pt-6">
        <button
          type="button"
          onClick={() => void spara()}
          disabled={busy || saknasSession}
          className={btnPrimary}
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          {busy ? "Sparar…" : "Spara notisinställningarna"}
        </button>
        {saknasSession ? (
          <p role="status" className="max-w-[60ch] text-[0.875rem] text-mineral">
            Kräver inloggning.
          </p>
        ) : null}
        {klart ? (
          <p role="status" className="text-[0.875rem] text-moss">
            {klart}
          </p>
        ) : null}
        {fel ? (
          <p role="alert" className="max-w-[60ch] break-words text-[0.875rem] text-danger">
            {fel}
          </p>
        ) : null}
      </div>
    </div>
  );
}
