"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Rad, Radlista, btnPrimary, rubrikPanel } from "@/components/ui";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";
import {
  hamtaAffarskontext,
  sparaAffarskontext,
  type Affarskontextfalt
} from "@/lib/actions/affarskontext";

/**
 * Affärskontexten — den flik som fanns men inte gjorde något.
 *
 * Den förra versionen låg i components/WorkspaceViews.tsx och var fem
 * `<textarea defaultValue={mockdata}>` utan spara-knapp och utan koppling till
 * arbetsytan. En kund kunde skriva i den, ladda om sidan och få tillbaka
 * exempeltexten — vilket ser ut som att sparningen misslyckades tyst.
 *
 * Fyra fält, inte nio: tonläget ägs av röstdokumentet och målgruppens
 * branscher/geografi/roller av leads-agentens ICP. Motiveringen står i
 * lib/actions/affarskontext.ts.
 */

const FALT: { nyckel: keyof Affarskontextfalt; etikett: Localized; hjalp: Localized; rader: number }[] = [
  {
    nyckel: "product",
    etikett: { sv: "Vad ni säljer", en: "What you sell" },
    hjalp: { sv: "En eller två meningar.", en: "One or two sentences." },
    rader: 3
  },
  {
    nyckel: "target_audience",
    etikett: { sv: "Vem ni säljer till", en: "Who you sell to" },
    hjalp: { sv: "Vilka bolag och vilka roller.", en: "Which companies and which roles." },
    rader: 3
  },
  {
    nyckel: "offer",
    etikett: { sv: "Erbjudandet", en: "The offer" },
    hjalp: { sv: "Vad kunden får.", en: "What the customer gets." },
    rader: 3
  },
  {
    nyckel: "cta",
    etikett: { sv: "Nästa steg ni vill ha", en: "The next step you want" },
    hjalp: { sv: "Samtal, demo eller prisförslag.", en: "A call, a demo or a quote." },
    rader: 2
  }
];

const ord = (s: string): Localized => ({ sv: s, en: s });

const TOMT: Affarskontextfalt = { product: "", target_audience: "", offer: "", cta: "" };

export function Affarskontext() {
  const { text } = useLocale();
  const [falt, setFalt] = useState<Affarskontextfalt | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<Localized | null>(null);
  const [klart, setKlart] = useState<Localized | null>(null);

  useEffect(() => {
    let avbruten = false;
    hamtaAffarskontext()
      .then((rad) => {
        if (!avbruten) setFalt(rad ?? TOMT);
      })
      // Utan catch fastnade vyn i skelettet för alltid vid nätverksfel —
      // falt förblev null och ingenting sa varför. Tomma fält + felraden är
      // ett läge användaren kan agera på; ett evigt skelett är det inte.
      .catch((orsak) => {
        if (avbruten) return;
        setFalt(TOMT);
        setFel(
          orsak instanceof Error
            ? ord(orsak.message)
            : { sv: "Kunde inte hämta affärskontexten.", en: "Could not load the business context." }
        );
      });
    return () => {
      avbruten = true;
    };
  }, []);

  if (falt === null) {
    return (
      <div className="grid gap-6" aria-busy="true">
        {FALT.map((f) => (
          <div key={f.nyckel} className="h-24 animate-pulse rounded-card bg-ink/[0.055]" />
        ))}
      </div>
    );
  }

  async function spara() {
    if (!falt) return;
    setBusy(true);
    setFel(null);
    setKlart(null);
    try {
      const svar = await sparaAffarskontext(falt);
      if (!svar.success) {
        setFel(svar.error ? ord(svar.error) : { sv: "Kunde inte spara.", en: "Could not save." });
        return;
      }
      setKlart(svar.varning ? ord(svar.varning) : { sv: "Sparat.", en: "Saved." });
    } catch (orsak) {
      setFel(orsak instanceof Error ? ord(orsak.message) : { sv: "Kunde inte spara.", en: "Could not save." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6">
      {/* Samma radform som resten av inställningarna: etikett, en mening
          hjälp i brödtextstorlek, fältet under. Hjälpen är kopplad till fältet
          med aria-describedby, så den läses upp när fältet får fokus. */}
      <Radlista ariaLabel={text({ sv: "Affärskontext", en: "Business context" })}>
        {FALT.map((f) => (
          <Rad key={f.nyckel} className="grid gap-3">
            <div>
              <label htmlFor={`affarskontext-${f.nyckel}`} className={cn(rubrikPanel, "block")}>
                {text(f.etikett)}
              </label>
              <p
                id={`affarskontext-${f.nyckel}-hjalp`}
                className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted"
              >
                {text(f.hjalp)}
              </p>
            </div>
            <textarea
              id={`affarskontext-${f.nyckel}`}
              aria-describedby={`affarskontext-${f.nyckel}-hjalp`}
              value={falt[f.nyckel]}
              rows={f.rader}
              onChange={(e) => setFalt({ ...falt, [f.nyckel]: e.target.value })}
              className="focus-ring w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6"
            />
          </Rad>
        ))}
      </Radlista>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <button type="button" onClick={() => void spara()} disabled={busy} className={btnPrimary}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          {busy ? text({ sv: "Sparar…", en: "Saving…" }) : text({ sv: "Spara affärskontexten", en: "Save business context" })}
        </button>
        {klart ? (
          <p role="status" className="text-[0.9375rem] text-moss">
            {text(klart)}
          </p>
        ) : null}
        {fel ? (
          <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
            {text(fel)}
          </p>
        ) : null}
      </div>
    </div>
  );
}
