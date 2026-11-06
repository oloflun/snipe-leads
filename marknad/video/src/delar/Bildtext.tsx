import React from "react";
import { useCurrentFrame } from "remotion";
import { farg, mellan, sans, serif } from "../tema";

/**
 * Bildtexten överst i scenytan: ett ord i taget i läshastighet (principen om
 * ~0,2 s per ord), med ett valfritt stegnummer i ockra. Fungerar stum.
 */
export const Bildtext: React.FC<{
  text: string;
  steg?: number;
  fran: number;
  till?: number;
  y?: number;
}> = ({ text, steg, fran, till, y = 18 }) => {
  const frame = useCurrentFrame();
  if (frame < fran) return null;
  const ord = text.split(" ");
  const ute = till !== undefined ? mellan(frame, [till - 6, till], [0, 1]) : 0;
  if (ute >= 1) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        top: y,
        height: 130,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 22,
        opacity: 1 - ute,
        transform: `translateY(${-30 * ute}px)`,
        filter: `blur(${6 * ute}px)`
      }}
    >
      {steg !== undefined ? (
        <div
          style={{
            width: 70,
            height: 70,
            borderRadius: 35,
            background: farg.ochre,
            color: farg.ink,
            fontFamily: serif,
            fontSize: 44,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: "0 0 auto",
            transform: `scale(${mellan(frame, [fran, fran + 8], [0.4, 1])})`,
            opacity: mellan(frame, [fran, fran + 5], [0, 1])
          }}
        >
          {steg}
        </div>
      ) : null}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0 16px", justifyContent: "center" }}>
        {ord.map((o, i) => {
          const start = fran + i * 4;
          const t = mellan(frame, [start, start + 9], [0, 1]);
          return (
            <span
              key={`${o}-${i}`}
              style={{
                fontFamily: sans,
                fontWeight: 600,
                fontSize: 58,
                letterSpacing: -0.5,
                color: farg.paper,
                opacity: t,
                transform: `translateY(${(1 - t) * 26}px)`,
                display: "inline-block",
                whiteSpace: "nowrap"
              }}
            >
              {o}
            </span>
          );
        })}
      </div>
    </div>
  );
};
