import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { farg, inn, kamera, mellan, pop, sans, serif, ut } from "../tema";
import { Yta } from "../delar/Yta";
import { Bildtext } from "../delar/Bildtext";
import { Markor } from "../delar/Markor";
import { Falt, Knapp, Panel } from "../delar/Panel";

export const KORNING_LANGD = 210;

/*
 * Tidslinje (lokala bildrutor, 30 fps, 15 = ett slag):
 *   0–30   Leads-sidan glider in, pekaren går till Kör Iris, klick vid 30
 *  36–56   formuläret Hitta bolag fälls ut under rubriken
 *  60–84   "Göteborg" skrivs i Stad
 *  96–112  "Bygg" skrivs i Bransch, förslagen dyker upp, klick på chip vid 120
 * 130–150  antalet dras till 50
 * 158–180  pekaren till Starta körning, klick vid 180
 * 180–210  Startar… med förloppsstapel, kameran trycker in, ockrablixt mot PANG
 */

const PANEL = { x: 80, y: 170, b: 920, h: 1130 };
const KNAPP_KOR = { x: PANEL.x + 622, y: PANEL.y + 44, b: 250, h: 92 };
const KORT = { x: PANEL.x + 48, y: PANEL.y + 176, b: 824, h: 800 };
const INRE_X = KORT.x + 40;
const FALT_B = 744;
const STAD = "Göteborg";
const BRANSCH = "Bygg";
const CHIPS = ["Bygg & anläggning", "Byggmaterial", "Byggkonsult"];

function skrivet(frame: number, start: number, text: string, perTecken = 3): string {
  return text.slice(0, Math.max(0, Math.floor((frame - start) / perTecken)));
}

export const Korning: React.FC = () => {
  const frame = useCurrentFrame();
  const inT = mellan(frame, [0, 12], [0, 1]);
  const kortT = mellan(frame, [36, 54], [0, 1]);
  const kortH = KORT.h * kortT;

  const stad = skrivet(frame, 60, STAD);
  const bransch = skrivet(frame, 96, BRANSCH);
  const chipsSyns = frame >= 110;
  const chipVald = frame >= 120;
  const antal = Math.round(mellan(frame, [130, 150], [10, 50]));
  const knappNer = frame >= 30 && frame < 36;
  const startad = frame >= 180;
  const forlopp = mellan(frame, [180, 212], [0, 1], ut);
  const blixt = mellan(frame, [198, 210], [0, 1], inn);

  const kam = kamera(frame, [
    { frame: 0, skala: 1, fokus: [KNAPP_KOR.x + 125, KNAPP_KOR.y + 46] },
    { frame: 18, skala: 1, fokus: [KNAPP_KOR.x + 125, KNAPP_KOR.y + 46] },
    { frame: 32, skala: 1.16, fokus: [KNAPP_KOR.x + 125, KNAPP_KOR.y + 46] },
    { frame: 40, skala: 1.16, fokus: [KNAPP_KOR.x + 125, KNAPP_KOR.y + 46] },
    { frame: 60, skala: 1.0, fokus: [540, 620] },
    { frame: 150, skala: 1.06, fokus: [540, 760] },
    { frame: 176, skala: 1.06, fokus: [540, KORT.y + 708] },
    { frame: 210, skala: 1.7, fokus: [540, KORT.y + 708] }
  ]);

  const sliderX0 = INRE_X;
  const sliderB = FALT_B;
  const knoppX = sliderX0 + 14 + (sliderB - 28) * ((antal - 10) / 40);
  const sliderY = KORT.y + 610;

  return (
    <AbsoluteFill>
      <Yta style={{ transform: kam, transformOrigin: "540px 665px" }}>
        <div style={{ opacity: inT, transform: `translateY(${(1 - inT) * 160}px)` }}>
          <Panel x={PANEL.x} y={PANEL.y} bredd={PANEL.b} hojd={PANEL.h}>
            <div style={{ position: "absolute", left: 48, top: 36, fontFamily: serif, fontSize: 88, fontWeight: 400, letterSpacing: -2, lineHeight: 1 }}>
              Leads
            </div>
            <Knapp
              x={KNAPP_KOR.x - PANEL.x}
              y={KNAPP_KOR.y - PANEL.y}
              bredd={KNAPP_KOR.b}
              hojd={KNAPP_KOR.h}
              text="Kör Iris"
              skala={knappNer ? 0.94 : 1}
            />

            {/* Formuläret Hitta bolag fälls ut under rubriken. */}
            <div
              style={{
                position: "absolute",
                left: KORT.x - PANEL.x,
                top: KORT.y - PANEL.y,
                width: KORT.b,
                height: kortH,
                overflow: "hidden",
                borderRadius: 24,
                border: `1.5px solid ${farg.linje}`,
                background: farg.paperDov,
                opacity: kortT
              }}
            >
              <div style={{ position: "absolute", left: 40, top: 32, fontSize: 44, fontWeight: 600 }}>Hitta bolag</div>
              <Falt x={40} y={118} bredd={FALT_B} etikett="Stad" varde={stad} aktiv={frame >= 58 && frame < 96} markor={frame >= 58 && frame < 96 && frame % 16 < 9} platshallare="Var ska Iris leta?" />
              <Falt x={40} y={280} bredd={FALT_B} etikett="Bransch" varde={bransch} aktiv={frame >= 96 && frame < 124} markor={frame >= 96 && frame < 124 && frame % 16 < 9} platshallare="Vilken bransch?" />
              <div style={{ position: "absolute", left: 40, top: 432, display: "flex", gap: 14 }}>
                {chipsSyns
                  ? CHIPS.map((c, i) => {
                      const p = pop(frame, 110 + i * 2);
                      const vald = chipVald && i === 0;
                      return (
                        <div
                          key={c}
                          style={{
                            height: 68,
                            padding: "0 26px",
                            borderRadius: 34,
                            border: `2px solid ${vald ? farg.ink : farg.linje}`,
                            background: vald ? farg.ink : farg.vit,
                            color: vald ? farg.paper : farg.ink,
                            fontSize: 28,
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
                    })
                  : null}
              </div>
              <div style={{ position: "absolute", left: 40, top: 506, width: FALT_B, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 28, fontWeight: 500, color: farg.inkDov }}>Antal leads</span>
                <span style={{ fontFamily: serif, fontSize: 56, fontWeight: 500, fontVariantNumeric: "tabular-nums", color: antal === 50 ? farg.ochre : farg.ink }}>
                  {antal}
                </span>
              </div>
              <div style={{ position: "absolute", left: 40, top: 604, width: FALT_B, height: 12, borderRadius: 6, background: farg.linje }}>
                <div style={{ width: `${((antal - 10) / 40) * 100}%`, height: "100%", borderRadius: 6, background: farg.ochre }} />
              </div>
              <div
                style={{
                  position: "absolute",
                  left: knoppX - KORT.x - 22,
                  top: 588,
                  width: 44,
                  height: 44,
                  borderRadius: 22,
                  background: farg.vit,
                  border: `3px solid ${farg.ochre}`,
                  boxShadow: "0 4px 12px oklch(0.15 0.016 252 / 0.25)"
                }}
              />
              <Knapp
                x={40}
                y={656}
                bredd={FALT_B}
                hojd={104}
                text={startad ? "Iris letar bolag…" : "Starta körning"}
                ton={startad ? "ochre" : "ink"}
                skala={frame >= 180 && frame < 186 ? 0.96 : 1}
                style={{ overflow: "hidden" }}
              />
              {startad ? (
                <div style={{ position: "absolute", left: 40, top: 756, width: FALT_B * forlopp, height: 6, borderRadius: 3, background: farg.ink }} />
              ) : null}
            </div>

            {/* Nyckeltalen, tomma före körningen; trycks ner när formuläret öppnas. */}
            <div style={{ position: "absolute", left: 48, top: 176 + (kortH > 0 ? kortH + 24 : 0), width: 824, fontFamily: sans }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 48px" }}>
                {["Leads i listan", "Utkast att godkänna", "Skickade mejl", "Svar från leads"].map((r) => (
                  <div key={r} style={{ borderTop: `1px solid ${farg.linje}`, padding: "22px 0 28px" }}>
                    <div style={{ fontSize: 28, color: farg.inkDov }}>{r}</div>
                    <div style={{ fontFamily: serif, fontSize: 72, lineHeight: 1.1, marginTop: 6 }}>0</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 20, border: `1.5px solid ${farg.linje}`, borderRadius: 24, height: 420, display: "flex", alignItems: "center", justifyContent: "center", color: farg.inkSvag, fontSize: 32 }}>
                Inga leads än. Kör Iris för att hitta dina första.
              </div>
            </div>
          </Panel>
        </div>

        <Bildtext steg={1} text="Tryck på Kör Iris" fran={4} till={40} />
        <Bildtext steg={2} text="Välj stad och bransch" fran={46} till={128} />
        <Bildtext steg={3} text="Starta körningen" fran={134} till={200} />

        <Markor
          punkter={[
            { frame: 6, x: 980, y: 1250 },
            { frame: 28, x: KNAPP_KOR.x + 150, y: KNAPP_KOR.y + 56 },
            { frame: 44, x: KNAPP_KOR.x + 150, y: KNAPP_KOR.y + 56 },
            { frame: 58, x: INRE_X + 300, y: KORT.y + 204 },
            { frame: 92, x: INRE_X + 300, y: KORT.y + 204 },
            { frame: 96, x: INRE_X + 240, y: KORT.y + 366 },
            { frame: 112, x: INRE_X + 240, y: KORT.y + 366 },
            { frame: 119, x: INRE_X + 150, y: KORT.y + 466 },
            { frame: 126, x: INRE_X + 150, y: KORT.y + 466 },
            { frame: 130, x: sliderX0 + 14 + 10, y: sliderY + 6 },
            { frame: 150, x: sliderX0 + sliderB - 14, y: sliderY + 6 },
            { frame: 158, x: sliderX0 + sliderB - 14, y: sliderY + 6 },
            { frame: 174, x: 540 + 30, y: KORT.y + 708 + 14 },
            { frame: 210, x: 540 + 30, y: KORT.y + 708 + 14 }
          ]}
          klick={[30, 120, 180]}
          synligFran={6}
        />
      </Yta>
      <AbsoluteFill style={{ background: farg.ochre, opacity: blixt, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
