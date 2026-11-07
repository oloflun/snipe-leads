import React from "react";
import type { Lead } from "../data";
import { farg, sans, serif } from "../tema";

export const RADHOJD = 105;

/** En rad i Iris-leads, som i LeadsTabell: nivåmärke, bolag, ort och bransch. */
export const LeadRad: React.FC<{
  lead: Lead;
  index: number;
  bredd: number;
  opacity?: number;
  forskjutning?: number;
  utkastKlart?: number;
}> = ({ lead, index, bredd, opacity = 1, forskjutning = 0, utkastKlart = 0 }) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      top: index * RADHOJD,
      width: bredd,
      height: RADHOJD,
      display: "flex",
      alignItems: "center",
      gap: 22,
      padding: "0 8px",
      borderBottom: `1px solid ${farg.linjeSvag}`,
      opacity,
      transform: `translateX(${forskjutning}px)`,
      fontFamily: sans
    }}
  >
    <div
      style={{
        width: 58,
        height: 58,
        borderRadius: 29,
        background: lead.niva === "A" ? farg.mossLjus : farg.blaLjus,
        color: lead.niva === "A" ? farg.moss : farg.bla,
        fontFamily: serif,
        fontSize: 34,
        fontWeight: 500,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "0 0 auto"
      }}
    >
      {lead.niva}
    </div>
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 33, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {lead.bolag}
      </div>
      <div style={{ fontSize: 26, color: farg.inkDov, marginTop: 2 }}>
        {lead.ort} · Bygg & anläggning
      </div>
    </div>
    {utkastKlart > 0 ? (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 18px",
          borderRadius: 999,
          background: farg.mossLjus,
          color: farg.moss,
          fontSize: 26,
          fontWeight: 600,
          whiteSpace: "nowrap",
          transform: `scale(${utkastKlart})`,
          opacity: Math.min(1, utkastKlart),
          transformOrigin: "right center"
        }}
      >
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={farg.moss} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 12.5 L9.5 18 L20 6.5" />
        </svg>
        Utkast klart
      </div>
    ) : null}
  </div>
);
