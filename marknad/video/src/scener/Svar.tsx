import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FRISKRIVNING, SVAR } from "../data";
import { farg, inn, mellan, sans, serif, ut } from "../tema";
import { Yta } from "../delar/Yta";
import { Bildtext } from "../delar/Bildtext";

export const SVAR_LANGD = 150;

/** De 30 svarens ankomst: glest först, sedan allt tätare (siffror som händelser). */
export const ANKOMSTER: number[] = Array.from({ length: 30 }, (_, i) => Math.round(8 + 124 * Math.pow(i / 29, 0.6)));

const STAPEL = { x: 80, y: 450, b: 920, kortH: 146, mellanrum: 14 };
const STEG = STAPEL.kortH + STAPEL.mellanrum;

export const Friskrivning: React.FC<{ opacity?: number }> = ({ opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      right: 0,
      top: 1272,
      textAlign: "center",
      fontFamily: sans,
      fontSize: 30,
      fontWeight: 500,
      color: "oklch(0.965 0.008 88 / 0.78)",
      opacity
    }}
  >
    {FRISKRIVNING}
  </div>
);

export const Svar: React.FC = () => {
  const frame = useCurrentFrame();
  const antal = ANKOMSTER.filter((a) => a <= frame).length;
  const senaste = ANKOMSTER.filter((a) => a <= frame).pop();
  const blipp = senaste === undefined ? 0 : Math.max(0, 1 - (frame - senaste) / 8);
  const inT = mellan(frame, [0, 10], [0, 1]);
  const ute = mellan(frame, [140, 150], [0, 1], inn);
  const klar = antal === 30 ? mellan(frame, [ANKOMSTER[29], ANKOMSTER[29] + 12], [0, 1]) : 0;

  const tonFarg = { ochre: farg.ochre, moss: farg.mossLjus, bla: farg.blaLjus };
  const tonText = { ochre: farg.ink, moss: farg.moss, bla: farg.bla };

  return (
    <AbsoluteFill>
      <Yta style={{ opacity: inT * (1 - ute), transform: `scale(${1 - ute * 0.06})`, transformOrigin: "540px 665px", filter: `blur(${ute * 8}px)` }}>
        <Bildtext text="Svaren landar i din inkorg" fran={2} till={140} />

        <div style={{ position: "absolute", left: 80, top: 150, display: "flex", alignItems: "baseline", gap: 26 }}>
          <span
            style={{
              fontFamily: serif,
              fontSize: 280,
              lineHeight: 1,
              fontWeight: 500,
              color: farg.paper,
              letterSpacing: -10,
              fontVariantNumeric: "tabular-nums",
              display: "inline-block",
              transform: `scale(${1 + blipp * 0.05})`,
              transformOrigin: "left bottom"
            }}
          >
            {antal}
          </span>
          <span style={{ fontFamily: sans, fontSize: 64, fontWeight: 600, color: farg.paper }}>svar</span>
          <span
            style={{
              marginLeft: 10,
              fontFamily: sans,
              fontSize: 30,
              fontWeight: 600,
              color: farg.ink,
              background: farg.ochre,
              padding: "10px 22px",
              borderRadius: 999,
              opacity: klar,
              transform: `scale(${0.6 + klar * 0.4})`,
              whiteSpace: "nowrap"
            }}
          >
            Möten att boka
          </span>
        </div>

        <div style={{ position: "absolute", left: STAPEL.x, top: STAPEL.y, width: STAPEL.b, height: 5 * STEG, overflow: "visible" }}>
          {SVAR.map((s, i) => {
            const ank = ANKOMSTER[i];
            if (frame < ank) return null;
            let plats = 0;
            for (let j = i + 1; j < 30; j += 1) {
              if (frame >= ANKOMSTER[j]) plats += mellan(frame, [ANKOMSTER[j], ANKOMSTER[j] + 9], [0, 1], ut);
            }
            if (plats > 4.1) return null;
            const inK = mellan(frame, [ank, ank + 8], [0, 1]);
            const dim = Math.max(0, Math.min(1, 1 - (plats - 3.1) / 0.9));
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: 0,
                  top: plats * STEG,
                  width: STAPEL.b,
                  height: STAPEL.kortH,
                  borderRadius: 26,
                  background: farg.paper,
                  color: farg.ink,
                  fontFamily: sans,
                  display: "flex",
                  alignItems: "center",
                  gap: 22,
                  padding: "0 30px",
                  boxSizing: "border-box",
                  boxShadow: "0 24px 60px oklch(0.10 0.016 252 / 0.45)",
                  opacity: inK * dim,
                  transform: `translateY(${(1 - inK) * -50}px) scale(${0.9 + inK * 0.1})`,
                  transformOrigin: "center top"
                }}
              >
                <div
                  style={{
                    width: 76,
                    height: 76,
                    borderRadius: 38,
                    background: tonFarg[s.ton],
                    color: tonText[s.ton],
                    fontFamily: serif,
                    fontSize: 38,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flex: "0 0 auto"
                  }}
                >
                  {s.namn[0]}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 30, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    <span style={{ width: 14, height: 14, borderRadius: 7, background: farg.ochre, display: "inline-block", flex: "0 0 auto" }} />
                    {s.namn} · {s.bolag.replace(" AB", "")}
                  </div>
                  <div style={{ fontSize: 30, color: farg.inkDov, marginTop: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.text}</div>
                </div>
                <div style={{ fontSize: 24, color: farg.inkSvag, flex: "0 0 auto" }}>nu</div>
              </div>
            );
          })}
        </div>

        <Friskrivning />
      </Yta>
    </AbsoluteFill>
  );
};
