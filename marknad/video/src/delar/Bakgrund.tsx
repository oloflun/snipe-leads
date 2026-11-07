import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { farg } from "../tema";
import { useYta } from "./Yta";

/**
 * Bläckmörk botten med två mjuka ljuskällor som driver långsamt, och ett
 * svagt brus som bryter upp gradientbanden i H.264. Ritas i hela bildrutan.
 */
export const Bakgrund: React.FC = () => {
  const frame = useCurrentFrame();
  const { topp } = useYta();
  const mittY = topp + 665;
  const ax = 30 + Math.sin(frame / 140) * 12;
  const ay = mittY - 420 + Math.cos(frame / 170) * 60;
  const bx = 78 + Math.cos(frame / 160) * 10;
  const by = mittY + 380 + Math.sin(frame / 150) * 70;
  return (
    <AbsoluteFill style={{ background: farg.inkDjup }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(820px circle at ${ax}% ${ay}px, oklch(0.74 0.16 64 / 0.18), transparent 62%),
            radial-gradient(1000px circle at ${bx}% ${by}px, oklch(0.48 0.12 252 / 0.26), transparent 62%)`
        }}
      />
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.05, mixBlendMode: "overlay" }}>
        <filter id="brus">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" seed="7" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#brus)" />
      </svg>
    </AbsoluteFill>
  );
};
