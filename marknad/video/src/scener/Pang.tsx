import React from "react";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { LEADS } from "../data";
import { farg, inn, mellan, pop, sans, serif } from "../tema";
import { Yta, useYta } from "../delar/Yta";
import { Bildtext } from "../delar/Bildtext";
import { Panel } from "../delar/Panel";
import { LeadRad, RADHOJD } from "../delar/LeadRad";

export const PANG_LANGD = 120;

/*
 * Lokala bildrutor:
 *   0–8    ockrablixten klingar av, strålarna sprids
 *   4–45   räknaren 0 → 50, raderna strömmar in underifrån i samma takt
 *  45      punch på 50:an, understrykning i ockra
 *  52–70   filterchips poppar: Göteborg · Bygg & anläggning
 * 100–120  listan växer upp till hel panel, räknaren viker undan → Utkast
 */

const LISTA = { x: 80, y: 590, b: 920, h: 720 };
const LISTA_SLUT = { x: 80, y: 170, b: 920, h: 1140 };
const HUVUD = 90;

/** Räknarens värde per bildruta och den bildruta då varje rad kom in. */
const UTEASE = Easing.out(Easing.cubic);
export function antalVid(frame: number): number {
  return mellan(frame, [4, 45], [0, 50], UTEASE);
}
const ANKOMST: number[] = [];
for (let i = 0; i < 50; i += 1) {
  let f = 0;
  while (f < PANG_LANGD && Math.floor(antalVid(f)) <= i) f += 1;
  ANKOMST.push(f);
}

export const Pang: React.FC = () => {
  const frame = useCurrentFrame();
  const { topp } = useYta();
  const blixt = mellan(frame, [0, 9], [1, 0], inn);
  const stralar = mellan(frame, [0, 22], [0, 1]);
  const n = antalVid(frame);
  const hel = Math.floor(n);
  const punch = frame >= 45 ? 1 + 0.12 * Math.max(0, 1 - (frame - 45) / 10) : 1;
  const streck = mellan(frame, [45, 58], [0, 1]);

  const morf = mellan(frame, [100, 120], [0, 1]);
  const lista = {
    x: LISTA.x,
    y: LISTA.y + (LISTA_SLUT.y - LISTA.y) * morf,
    b: LISTA.b,
    h: LISTA.h + (LISTA_SLUT.h - LISTA.h) * morf
  };
  const fonsterH = lista.h - HUVUD - 40;
  const rull = Math.max(0, n * RADHOJD - fonsterH);
  const raknareUte = mellan(frame, [100, 114], [0, 1], inn);

  return (
    <AbsoluteFill>
      {/* Strålarna från smällen, i hela bildrutan kring scenytans mitt. */}
      <AbsoluteFill style={{ opacity: 1 - stralar, pointerEvents: "none" }}>
        {Array.from({ length: 18 }, (_, i) => {
          const vinkel = (i / 18) * 360;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: 540,
                top: topp + 440,
                width: 6,
                height: 160 + (i % 3) * 90,
                background: `linear-gradient(${farg.ochre}, transparent)`,
                transformOrigin: "3px 0",
                transform: `rotate(${vinkel}deg) translateY(${80 + stralar * 900}px) scaleY(${1 + stralar})`
              }}
            />
          );
        })}
      </AbsoluteFill>

      <Yta>
        <Bildtext text="Iris hittar bolagen åt dig" fran={14} till={100} />

        <div
          style={{
            position: "absolute",
            left: 80,
            top: 150,
            display: "flex",
            alignItems: "baseline",
            gap: 30,
            opacity: 1 - raknareUte,
            transform: `translateY(${-120 * raknareUte}px) scale(${punch})`,
            transformOrigin: "left bottom",
            filter: `blur(${raknareUte * 10}px)`
          }}
        >
          <div style={{ position: "relative" }}>
            <span
              style={{
                fontFamily: serif,
                fontSize: 360,
                lineHeight: 1,
                fontWeight: 500,
                color: farg.paper,
                letterSpacing: -14,
                fontVariantNumeric: "tabular-nums"
              }}
            >
              {hel}
            </span>
            <div style={{ position: "absolute", left: 6, bottom: -6, height: 16, width: `${streck * 100}%`, background: farg.ochre, borderRadius: 8 }} />
          </div>
          <span style={{ fontFamily: sans, fontSize: 70, fontWeight: 600, color: farg.paper }}>leads</span>
        </div>

        <div style={{ position: "absolute", left: 80, top: 520, display: "flex", gap: 16, opacity: 1 - raknareUte, transform: `translateY(${-80 * raknareUte}px)` }}>
          {["Göteborg", "Bygg & anläggning", "Kontakt hittad"].map((c, i) => {
            const p = pop(frame, 52 + i * 4);
            return (
              <div
                key={c}
                style={{
                  height: 58,
                  padding: "0 24px",
                  borderRadius: 29,
                  background: "oklch(0.965 0.008 88 / 0.12)",
                  border: "2px solid oklch(0.965 0.008 88 / 0.35)",
                  color: farg.paper,
                  fontFamily: sans,
                  fontSize: 27,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  transform: `scale(${p})`,
                  opacity: Math.min(1, p),
                  whiteSpace: "nowrap"
                }}
              >
                {c}
              </div>
            );
          })}
        </div>

        <Panel x={lista.x} y={lista.y} bredd={lista.b} hojd={lista.h}>
          <div style={{ position: "absolute", left: 48, right: 48, top: 0, height: HUVUD, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${farg.linje}` }}>
            <span style={{ fontSize: 34, fontWeight: 600 }}>Iris-leads</span>
            <span style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 26, color: farg.inkDov }}>
              <span style={{ width: 14, height: 14, borderRadius: 7, background: farg.ochre, display: "inline-block" }} />
              Uppdateras live
            </span>
          </div>
          <div style={{ position: "absolute", left: 48, right: 48, top: HUVUD + 20, height: fonsterH, overflow: "hidden", maskImage: "linear-gradient(to bottom, transparent 0, black 70px, black 100%)", WebkitMaskImage: "linear-gradient(to bottom, transparent 0, black 70px, black 100%)" }}>
            <div style={{ position: "absolute", left: 0, top: -rull, width: "100%" }}>
              {LEADS.map((lead, i) => {
                if (i >= hel) return null;
                const t = mellan(frame, [ANKOMST[i], ANKOMST[i] + 6], [0, 1]);
                return <LeadRad key={lead.bolag} lead={lead} index={i} bredd={lista.b - 96} opacity={t} forskjutning={(1 - t) * 60} />;
              })}
            </div>
          </div>
        </Panel>
      </Yta>
      <AbsoluteFill style={{ background: farg.ochre, opacity: blixt, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
