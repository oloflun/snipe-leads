import React from "react";
import { useCurrentFrame } from "remotion";
import { farg, inUt, mellan } from "../tema";

export type Markorpunkt = { frame: number; x: number; y: number };

/**
 * Muspekaren: glider mellan nyckelpunkter med mjuk in-ut-easing och gör
 * ett litet nedtryck plus en ring vid varje klick. Koordinaterna är
 * scenytans.
 */
export const Markor: React.FC<{ punkter: Markorpunkt[]; klick?: number[]; synligFran?: number; synligTill?: number }> = ({
  punkter,
  klick = [],
  synligFran = 0,
  synligTill = Infinity
}) => {
  const frame = useCurrentFrame();
  if (frame < synligFran || frame > synligTill || punkter.length === 0) return null;
  let a = punkter[0];
  let b = punkter[punkter.length - 1];
  for (let i = 0; i < punkter.length - 1; i += 1) {
    if (frame >= punkter[i].frame && frame <= punkter[i + 1].frame) {
      a = punkter[i];
      b = punkter[i + 1];
      break;
    }
  }
  if (frame < punkter[0].frame) b = punkter[0];
  if (frame > punkter[punkter.length - 1].frame) a = punkter[punkter.length - 1];
  const t = a.frame === b.frame ? 1 : mellan(frame, [a.frame, b.frame], [0, 1], inUt);
  const x = a.x + (b.x - a.x) * t;
  const y = a.y + (b.y - a.y) * t;

  const senasteKlick = klick.filter((k) => frame >= k).sort((p, q) => q - p)[0];
  const sedanKlick = senasteKlick === undefined ? 99 : frame - senasteKlick;
  const tryck = sedanKlick < 6 ? 1 - Math.abs(sedanKlick - 3) / 3 : 0;
  const ring = sedanKlick <= 14 ? sedanKlick / 14 : null;
  const synlig = mellan(frame, [synligFran, synligFran + 6], [0, 1]);

  return (
    <div style={{ position: "absolute", left: x, top: y, opacity: synlig, pointerEvents: "none", zIndex: 50 }}>
      {ring !== null ? (
        <div
          style={{
            position: "absolute",
            left: -44,
            top: -44,
            width: 88,
            height: 88,
            borderRadius: 44,
            border: `5px solid ${farg.ochre}`,
            opacity: 0.9 * (1 - ring),
            transform: `scale(${0.3 + ring * 1.1})`
          }}
        />
      ) : null}
      <svg
        width="64"
        height="76"
        viewBox="0 0 24 28"
        style={{
          position: "absolute",
          left: -4,
          top: -3,
          transform: `scale(${1 - tryck * 0.16})`,
          transformOrigin: "6px 4px",
          filter: "drop-shadow(0 6px 10px oklch(0.15 0.016 252 / 0.45))"
        }}
      >
        <path
          d="M5 3 L5 22 L9.6 17.6 L13 25.5 L16.4 24 L13 16.2 L19.5 16 Z"
          fill={farg.paper}
          stroke={farg.ink}
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
};
