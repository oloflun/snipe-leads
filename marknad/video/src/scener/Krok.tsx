import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FRISKRIVNING, SVAR } from "../data";
import { farg, inn, mellan, sans, serif } from "../tema";
import { Yta } from "../delar/Yta";
import { Friskrivning } from "./Svar";

export const KROK_LANGD = 60;

/**
 * Kroken, 2 sekunder: resultatet först (principen från Linear och Raycast),
 * tre slag i takt med ljudet. "50 leads." räknas upp, "30 svar." landar
 * med ett svarskort bakom sig, "En körning." i kursiv Fraunces. Sedan
 * piskas allt uppåt och körningen börjar från början.
 */
export const Krok: React.FC = () => {
  const frame = useCurrentFrame();
  const slag = [0, 15, 30];
  const ute = mellan(frame, [50, 60], [0, 1], inn);

  const rad = (i: number, barn: React.ReactNode) => {
    const t = mellan(frame, [slag[i], slag[i] + 8], [0, 1]);
    const uteRad = mellan(frame, [50 + i * 2, 58 + i * 2], [0, 1], inn);
    return (
      <div
        key={i}
        style={{
          fontFamily: serif,
          fontSize: 172,
          lineHeight: 1.0,
          fontWeight: 500,
          color: farg.paper,
          letterSpacing: -4,
          opacity: t * (1 - uteRad),
          transform: `scale(${1.35 - 0.35 * t}) translateY(${-260 * uteRad}px)`,
          transformOrigin: "left center",
          filter: `blur(${(1 - t) * 14 + uteRad * 10}px)`,
          whiteSpace: "nowrap"
        }}
      >
        {barn}
      </div>
    );
  };

  const antal = Math.round(mellan(frame, [0, 11], [0, 50]));
  const svar = SVAR[0];
  const kortT = mellan(frame, [16, 26], [0, 1]);

  return (
    <AbsoluteFill>
      <Yta>
        <div style={{ position: "absolute", left: 80, top: 330, display: "flex", flexDirection: "column", gap: 36 }}>
          {rad(0, (
            <>
              <span style={{ color: farg.ochre, fontVariantNumeric: "tabular-nums" }}>{antal}</span> leads.
            </>
          ))}
          {rad(1, (
            <>
              <span style={{ color: farg.ochre }}>30</span> svar.
            </>
          ))}
          {rad(2, <span style={{ fontStyle: "italic", fontWeight: 400 }}>En körning.</span>)}
        </div>

        <div
          style={{
            position: "absolute",
            left: 120,
            top: 980,
            width: 840,
            background: farg.paper,
            borderRadius: 28,
            padding: "26px 32px",
            display: "flex",
            gap: 22,
            alignItems: "center",
            boxShadow: "0 30px 70px oklch(0.10 0.016 252 / 0.5)",
            opacity: kortT * (1 - ute),
            transform: `translateY(${(1 - kortT) * 60 - ute * 200}px) scale(${0.92 + kortT * 0.08})`,
            fontFamily: sans,
            color: farg.ink
          }}
        >
          <div
            style={{
              width: 76,
              height: 76,
              borderRadius: 38,
              background: farg.ochre,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: serif,
              fontSize: 38,
              flex: "0 0 auto"
            }}
          >
            {svar.namn[0]}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 30, fontWeight: 600, display: "flex", alignItems: "center", gap: 14 }}>
              <span style={{ width: 14, height: 14, borderRadius: 7, background: farg.ochre, display: "inline-block" }} />
              Nytt svar · {svar.namn}, {svar.bolag.replace(" AB", "")}
            </div>
            <div style={{ fontSize: 30, color: farg.inkDov, marginTop: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {svar.text}
            </div>
          </div>
        </div>
        <Friskrivning opacity={1 - ute} />
      </Yta>
    </AbsoluteFill>
  );
};

export { FRISKRIVNING };
