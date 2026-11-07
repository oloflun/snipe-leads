import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { farg, mellan, pop, sans, serif } from "../tema";
import { Yta, useYta } from "../delar/Yta";

export const SLUT_LANGD = 105;

/**
 * Slutet: papperet sveper över bläcket, S-symbolen landar, en mening och ett
 * steg. Filmen stannar tvärt på sista rutan (ingen uttoning), som Apples
 * "Don't Blink".
 */
export const Slut: React.FC = () => {
  const frame = useCurrentFrame();
  const { topp } = useYta();
  const svep = mellan(frame, [0, 16], [0, 1]);
  const symbol = pop(frame, 6);
  const rad1 = mellan(frame, [18, 32], [0, 1]);
  const rad2 = mellan(frame, [26, 40], [0, 1]);
  const cta = pop(frame, 40);
  const puls = frame > 60 ? 1 + Math.sin((frame - 60) / 7) * 0.012 : 1;

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: farg.paper, clipPath: `circle(${svep * 1500}px at 540px ${topp + 665}px)` }} />
      <Yta>
        <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center" }}>
          <Img
            src={staticFile("symbol-svart.svg")}
            style={{ width: 300, transform: `scale(${symbol}) rotate(${(1 - symbol) * -12}deg)`, opacity: Math.min(1, symbol) }}
          />
        </div>
        <div style={{ position: "absolute", left: 60, right: 60, top: 470, textAlign: "center", fontFamily: serif, color: farg.ink, fontSize: 96, lineHeight: 1.1, letterSpacing: -2 }}>
          <div style={{ opacity: rad1, transform: `translateY(${(1 - rad1) * 40}px)`, fontWeight: 500 }}>Nya företagskunder.</div>
          <div style={{ opacity: rad2, transform: `translateY(${(1 - rad2) * 40}px)`, fontStyle: "italic", fontWeight: 400 }}>
            Rakt in i <span style={{ color: farg.ochre }}>inkorgen.</span>
          </div>
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 800, display: "flex", justifyContent: "center" }}>
          <div
            style={{
              background: farg.ink,
              color: farg.paper,
              fontFamily: sans,
              fontSize: 44,
              fontWeight: 600,
              padding: "32px 54px",
              borderRadius: 999,
              transform: `scale(${cta * puls})`,
              opacity: Math.min(1, cta),
              display: "flex",
              alignItems: "center",
              gap: 20,
              boxShadow: "0 24px 60px oklch(0.15 0.016 252 / 0.25)"
            }}
          >
            Prova demon: <span style={{ color: farg.ochre }}>snajp.se/demo</span>
          </div>
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 960, textAlign: "center", fontFamily: sans, fontSize: 30, color: farg.inkDov, opacity: Math.min(1, cta) }}>
          Utan konto. Inget skickas.
        </div>
      </Yta>
    </AbsoluteFill>
  );
};
