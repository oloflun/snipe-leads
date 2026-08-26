"use client";

/**
 * Sista skyddsnätet: fångar fel i rotlayouten själv, där app/error.tsx inte
 * når. Renderas UTANFÖR layouten och måste därför bära sin egen <html>/<body>
 * — och kan inte lita på att globala stilar laddats, därav inline-stilarna.
 * Samma princip som app/error.tsx: inget felinnehåll visas, bara digest.
 */
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
          background: "#faf7f2",
          color: "#1f1d1a",
          fontFamily: "Georgia, 'Times New Roman', serif",
          padding: "24px"
        }}
      >
        <div style={{ maxWidth: "32rem", textAlign: "center" }}>
          <h1 style={{ fontSize: "2.2rem", lineHeight: 1.2, margin: 0 }}>Något gick fel</h1>
          <p style={{ fontSize: "17px", lineHeight: 1.8, marginTop: "16px", color: "#57534e" }}>
            Felet är loggat på vår sida. Prova igen — hjälper inte det, mejla{" "}
            <a href="mailto:hej@snajp.se" style={{ color: "#b45309" }}>
              hej@snajp.se
            </a>
            {error.digest ? ` och ange felkoden ${error.digest}` : ""}.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: "32px",
              minHeight: "44px",
              padding: "0 24px",
              borderRadius: "9999px",
              border: "none",
              background: "#1f1d1a",
              color: "#faf7f2",
              fontSize: "15px",
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
