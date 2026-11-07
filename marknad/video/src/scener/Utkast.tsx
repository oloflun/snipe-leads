import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { LEADS, UTKAST } from "../data";
import { farg, glid, inn, mellan, pop, sans, serif, ut } from "../tema";
import { Yta } from "../delar/Yta";
import { Bildtext } from "../delar/Bildtext";
import { Markor } from "../delar/Markor";
import { Knapp, Panel } from "../delar/Panel";
import { LeadRad, RADHOJD } from "../delar/LeadRad";

export const UTKAST_LANGD = 150;

/*
 * Lokala bildrutor:
 *   0–30   "Utkast klart" sveper nedåt genom listan, räknaren 0 → 50
 *  30–40   ett utkast lyfter upp över listan
 *  40–90   mejlet skrivs i läsbar fart
 *  90–102  den personliga meningen stryks under i ockra, etikett poppar
 * 100–120  Godkänn och skicka alla 50, klick vid 120
 * 120–150  utkastet flyger i väg, kuverten sprids, "50 skickade"
 */

const LISTA = { x: 80, y: 170, b: 920, h: 1140 };
const HUVUD = 90;
const KORT = { x: 110, y: 340, b: 860, h: 650 };
const SKICKA = { x: 110, y: 1136, b: 860, h: 110 };
const SYNLIGA = 10;
const FORSTA = LEADS.length - SYNLIGA;
const TECKEN_PER_RUTA = 4;

export const Utkast: React.FC = () => {
  const frame = useCurrentFrame();
  const raknare = Math.round(mellan(frame, [2, 30], [0, 50], ut));
  const kortIn = glid(frame, 30);
  const skrivStart = 40;
  const antalTecken = Math.max(0, Math.floor((frame - skrivStart) * TECKEN_PER_RUTA));
  const markering = mellan(frame, [90, 102], [0, 1]);
  const etikett = pop(frame, 96);
  const skickaIn = glid(frame, 100);
  const klickat = frame >= 120;
  const flyg = mellan(frame, [120, 138], [0, 1], inn);
  const ute = mellan(frame, [142, 150], [0, 1], inn);
  const knappNer = frame >= 120 && frame < 126;

  let kvar = antalTecken;
  const delar = UTKAST.delar.map((d) => {
    const visat = d.text.slice(0, Math.max(0, kvar));
    kvar -= d.text.length;
    return { ...d, visat };
  });
  const skriverKlart = antalTecken >= UTKAST.delar.reduce((s, d) => s + d.text.length, 0);

  const kuvert = Array.from({ length: 14 }, (_, i) => {
    const start = 121 + i * 1.4;
    const t = mellan(frame, [start, start + 18], [0, 1], ut);
    const vinkel = -110 + (i / 13) * 70;
    const rad = vinkel * (Math.PI / 180);
    const avst = 160 + t * (520 + (i % 4) * 110);
    return { x: 540 + Math.cos(rad) * avst, y: SKICKA.y + 55 + Math.sin(rad) * avst, t, rot: (i % 2 ? 1 : -1) * t * 40 };
  });

  return (
    <AbsoluteFill>
      <Yta style={{ opacity: 1 - ute, transform: `translateY(${-140 * ute}px)`, filter: `blur(${ute * 8}px)` }}>
        <Bildtext text="Utkasten är redan skrivna" fran={4} till={96} />
        <Bildtext text="Ett klick. Alla iväg." fran={102} till={146} />

        <Panel x={LISTA.x} y={LISTA.y} bredd={LISTA.b} hojd={LISTA.h} style={{ filter: `blur(${kortIn * 6}px)` }}>
          <div style={{ position: "absolute", left: 48, right: 48, top: 0, height: HUVUD, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${farg.linje}` }}>
            <span style={{ fontSize: 34, fontWeight: 600 }}>Iris-leads</span>
            <span style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 28, fontWeight: 600, color: farg.moss, background: farg.mossLjus, padding: "10px 22px", borderRadius: 999 }}>
              Utkast <span style={{ fontVariantNumeric: "tabular-nums" }}>{raknare}</span>/50
            </span>
          </div>
          <div style={{ position: "absolute", left: 48, right: 48, top: HUVUD + 20, height: SYNLIGA * RADHOJD, overflow: "hidden" }}>
            {LEADS.slice(FORSTA).map((lead, i) => (
              <LeadRad key={lead.bolag} lead={lead} index={i} bredd={LISTA.b - 96} utkastKlart={pop(frame, 4 + i * 2.4)} />
            ))}
          </div>
          <div style={{ position: "absolute", inset: 0, background: `oklch(0.15 0.016 252 / ${0.42 * kortIn})` }} />
        </Panel>

        {/* Utkastet: lyfter, skrivs, flyger i väg. */}
        <div
          style={{
            position: "absolute",
            left: KORT.x,
            top: KORT.y,
            width: KORT.b,
            height: KORT.h,
            opacity: Math.min(1, kortIn) * (1 - flyg),
            transform: `translate(${flyg * 520}px, ${(1 - kortIn) * 300 - flyg * 900}px) scale(${0.9 + kortIn * 0.1 - flyg * 0.5}) rotate(${flyg * 18}deg)`,
            transformOrigin: "center",
            background: farg.vit,
            borderRadius: 30,
            boxShadow: "0 50px 100px oklch(0.10 0.016 252 / 0.6)",
            color: farg.ink,
            fontFamily: sans,
            padding: "36px 44px",
            boxSizing: "border-box"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 26, color: farg.inkDov }}>
            <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ width: 40, height: 40, borderRadius: 20, background: farg.mossLjus, color: farg.moss, fontFamily: serif, fontSize: 24, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>A</span>
              Utkast · {UTKAST.bolag}
            </span>
            <span>{UTKAST.till}</span>
          </div>
          <div style={{ marginTop: 26, paddingBottom: 22, borderBottom: `1px solid ${farg.linje}`, fontSize: 40, fontWeight: 600 }}>
            {UTKAST.amne}
          </div>
          <div style={{ marginTop: 24, fontSize: 33, lineHeight: 1.42, whiteSpace: "pre-wrap", position: "relative" }}>
            {delar.map((d, i) =>
              d.markera ? (
                <span
                  key={i}
                  style={{
                    backgroundImage: `linear-gradient(${farg.ochreSvag}, ${farg.ochreSvag})`,
                    backgroundRepeat: "no-repeat",
                    backgroundSize: `${markering * 100}% 100%`,
                    boxDecorationBreak: "clone",
                    WebkitBoxDecorationBreak: "clone",
                    borderRadius: 6
                  }}
                >
                  {d.visat}
                </span>
              ) : (
                <span key={i}>{d.visat}</span>
              )
            )}
            {!skriverKlart && frame >= skrivStart ? <span style={{ display: "inline-block", width: 3, height: 36, background: farg.ink, verticalAlign: -6, marginLeft: 2 }} /> : null}
          </div>
          <div
            style={{
              position: "absolute",
              right: 44,
              top: -34,
              padding: "12px 22px",
              borderRadius: 999,
              background: farg.ochre,
              color: farg.ink,
              fontSize: 26,
              fontWeight: 600,
              transform: `scale(${etikett})`,
              opacity: Math.min(1, etikett),
              transformOrigin: "right bottom",
              whiteSpace: "nowrap",
              boxShadow: "0 10px 24px oklch(0.15 0.016 252 / 0.25)"
            }}
          >
            Läst på bolagets egen sajt
          </div>
        </div>

        <div style={{ position: "absolute", left: 0, top: 0, opacity: Math.min(1, skickaIn), transform: `translateY(${(1 - skickaIn) * 120}px)` }}>
          <Knapp
            x={SKICKA.x}
            y={SKICKA.y}
            bredd={SKICKA.b}
            hojd={SKICKA.h}
            text={klickat ? "✓  50 skickade" : "Godkänn och skicka alla 50"}
            ton={klickat ? "moss" : "ink"}
            skala={knappNer ? 0.96 : 1}
          />
        </div>

        {kuvert.map((k, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: k.x - 28,
              top: k.y - 20,
              width: 56,
              height: 40,
              borderRadius: 8,
              background: farg.paper,
              border: `3px solid ${farg.ochre}`,
              opacity: k.t > 0 ? Math.max(0, 1 - k.t * 1.1) : 0,
              transform: `rotate(${k.rot}deg) scale(${0.6 + k.t * 0.6})`
            }}
          >
            <svg width="50" height="34" viewBox="0 0 50 34" style={{ position: "absolute", left: 0, top: 0 }}>
              <path d="M2 4 L25 20 L48 4" fill="none" stroke={farg.ochre} strokeWidth="3" />
            </svg>
          </div>
        ))}

        <Markor
          punkter={[
            { frame: 100, x: 980, y: 1300 },
            { frame: 116, x: 540 + 120, y: SKICKA.y + 62 },
            { frame: 150, x: 540 + 120, y: SKICKA.y + 62 }
          ]}
          klick={[120]}
          synligFran={100}
        />
      </Yta>
    </AbsoluteFill>
  );
};
