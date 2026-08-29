"use client";

/**
 * Sista skyddsnätet: fångar fel i rotlayouten själv, där app/error.tsx inte
 * når. Renderas UTANFÖR layouten och måste därför bära sin egen <html>/<body>
 * — och kan inte lita på att globals.css laddats, därav inline-stilarna.
 *
 * ## Färgerna är literala OKLCH, inte hex, och inte gissade
 *
 * Utan globals.css finns inga `--ink`/`--paper`-variabler att peka på, så
 * värdena måste stå här. Första versionen hade hex jag skrev ur minnet
 * (#1f1d1a mot #faf7f2) och de bröt husets bärande regel: DESIGN.md säger
 * "warm ground, cool ink", alltså varmt papper (hue 88) och KALL ink
 * (hue 252). Min varma ink vände på precis det som gör paletten till vår.
 * Värdena nedan är kopierade ur app/globals.css.
 *
 * Samma princip som app/error.tsx i övrigt: inget felinnehåll visas, bara
 * digest — ett serverfel kan bära interna detaljer, och den som behöver dem
 * läser loggen.
 */

const PAPER = "oklch(0.965 0.008 88)";
const INK = "oklch(0.20 0.018 252)";
const INK2 = "oklch(0.28 0.018 252)";
const OCHRE = "oklch(0.74 0.16 64)";
const MINERAL = "oklch(0.55 0.015 252)";

export default function GlobalError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="sv">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: PAPER,
          color: INK,
          // Fraunces laddas via layouten, som inte kört här. Georgia är den
          // närmaste stationära serifen och står redan som fallback i
          // tailwind.config.ts font-display.
          fontFamily: "Georgia, 'Times New Roman', serif",
          padding: "24px"
        }}
      >
        <div style={{ maxWidth: "34rem", textAlign: "center" }}>
          <h1
            style={{
              fontSize: "2.5rem",
              lineHeight: 1.15,
              letterSpacing: "-0.02em",
              margin: 0,
              fontWeight: 600
            }}
          >
            Något gick fel
          </h1>
          <p
            style={{
              fontSize: "17px",
              lineHeight: 1.8,
              marginTop: "16px",
              color: INK2,
              fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
            }}
          >
            Felet är loggat på vår sida. Prova igen — hjälper inte det, mejla{" "}
            <a href="mailto:kontakt@snajp.se" style={{ color: OCHRE }}>
              kontakt@snajp.se
            </a>
            .
          </p>
          {error.digest ? (
            <p
              style={{
                fontSize: "13px",
                letterSpacing: "0.04em",
                marginTop: "12px",
                color: MINERAL,
                fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif"
              }}
            >
              FELKOD {error.digest}
            </p>
          ) : null}
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: "32px",
              minHeight: "44px",
              padding: "0 24px",
              borderRadius: "8px",
              border: "none",
              background: INK,
              color: PAPER,
              fontSize: "15px",
              fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif",
              cursor: "pointer"
            }}
          >
            Försök igen
          </button>
        </div>
      </body>
    </html>
  );
}
