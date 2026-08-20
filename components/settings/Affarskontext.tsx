"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { btnPrimary } from "@/components/ui";
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

const FALT: { nyckel: keyof Affarskontextfalt; etikett: string; hjalp: string; rader: number }[] = [
  {
    nyckel: "product",
    etikett: "Vad ni säljer",
    hjalp: "En eller två meningar. Det här är det agenten ska sälja.",
    rader: 3
  },
  {
    nyckel: "target_audience",
    etikett: "Vem ni säljer till",
    hjalp: "Vilka bolag och vilka roller. Skriv som ni skulle beskrivit det för en ny säljare.",
    rader: 3
  },
  {
    nyckel: "offer",
    etikett: "Erbjudandet",
    hjalp: "Vad kunden får, och vad det kostar dem att inte ha det.",
    rader: 3
  },
  {
    nyckel: "cta",
    etikett: "Nästa steg ni vill ha",
    hjalp: "Vad ett lyckat mejl leder till. Ett kort samtal, en demo, ett prisförslag.",
    rader: 2
  }
];

const TOMT: Affarskontextfalt = { product: "", target_audience: "", offer: "", cta: "" };

export function Affarskontext() {
  const vag = useArbetsvag();
  const [falt, setFalt] = useState<Affarskontextfalt | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [klart, setKlart] = useState<string | null>(null);

  useEffect(() => {
    let avbruten = false;
    void hamtaAffarskontext().then((rad) => {
      if (!avbruten) setFalt(rad ?? TOMT);
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
        setFel(svar.error ?? "Kunde inte spara.");
        return;
      }
      setKlart(svar.varning ?? "Sparat. Båda agenterna läser texten från nästa körning.");
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte spara.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-7">
      {FALT.map((f) => (
        <label key={f.nyckel} className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
          <span className="col-span-12 md:col-span-3">
            <span className="kicker block text-mineral">{f.etikett}</span>
            <span className="mt-2 block text-[0.8125rem] leading-5 text-ink/50">{f.hjalp}</span>
          </span>
          <textarea
            value={falt[f.nyckel]}
            rows={f.rader}
            onChange={(e) => setFalt({ ...falt, [f.nyckel]: e.target.value })}
            className="focus-ring col-span-12 mt-3 w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6 outline-none md:col-span-9 md:mt-0"
          />
        </label>
      ))}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-ink/15 pt-6">
        <button type="button" onClick={() => void spara()} disabled={busy} className={btnPrimary}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          {busy ? "Sparar…" : "Spara affärskontexten"}
        </button>
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

      <p className="max-w-[62ch] text-[0.875rem] leading-6 text-ink/55">
        Tonläget skrivs under{" "}
        <Link
          href={vag("/settings/soul")}
          className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
        >
          Röst och tonläge
        </Link>
        , och vilka bolag agenten ska leta efter under{" "}
        <Link
          href={vag("/settings/leads")}
          className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
        >
          Målgrupp och autonomi
        </Link>
        . De ligger inte här för att samma uppgift på två ställen betyder att den som skriver i fel
        ruta inte hörs.
      </p>
    </div>
  );
}
