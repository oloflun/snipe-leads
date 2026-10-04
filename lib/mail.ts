import "server-only";

/**
 * Webbappens enda utgående mailväg — transaktionsmail (lösenordsåterställning).
 *
 * Resend över HTTPS, samma kanal och av samma skäl som backendens
 * send_provider.py: Railway blockerar utgående SMTP under Pro-planen, HTTPS
 * berörs inte, och Resend DKIM-signerar för den verifierade domänen. Ingen
 * SMTP-fallback här — webben har inget smtplib, och EN kanal räcker för de
 * här volymerna.
 *
 * Kontraktet är ärligt, samma princip som sender.py: skickas inget mail säger
 * `harMailvag()` det INNAN någon lovar användaren något, och ett misslyckat
 * anrop kastar så att anroparen aldrig kan säga "skickat" om en lögn.
 *
 * Kallmejlens spärrlista (suppressions) kontrolleras medvetet inte: ett
 * återställningsmail är ett svar på mottagarens egen begäran, inte
 * marknadsföring — samma gränsdragning som supportsvaren i sender.py.
 */

const RESEND_ENDPOINT = "https://api.resend.com/emails";

export function harMailvag(): boolean {
  return Boolean((process.env.RESEND_API_KEY ?? "").trim());
}

/**
 * Appens publika bas-URL för länkar i utgående mail.
 *
 * Ordningen: uttryckligt satt `SITE_URL` vinner (custom-domän), annars
 * Railways automatiska `RAILWAY_PUBLIC_DOMAIN`, annars localhost. Läses vid
 * RUNTIME med flit — NEXT_PUBLIC_SITE_URL bakades in vid build och gav
 * produktionslänkar från previewen (DEPLOY.md, "NEXT_PUBLIC_SITE_URL är
 * fällan").
 *
 * Aldrig ur requestens Host-header: en förfalskad header hade annars styrt
 * vart återställningslänken pekar — klassisk password reset poisoning, där
 * offrets länk går via angriparens domän.
 */
export function appBasUrl(): string {
  const uttrycklig = (process.env.SITE_URL ?? "").trim().replace(/\/+$/, "");
  if (uttrycklig) {
    return uttrycklig;
  }
  const railway = (process.env.RAILWAY_PUBLIC_DOMAIN ?? "").trim();
  if (railway) {
    return `https://${railway}`;
  }
  return "http://localhost:3000";
}

/** Kastar vid fel — anroparen får aldrig rapportera "skickat" på ett mail som inte gick. */
export async function skickaTransaktionsmail(args: {
  till: string;
  amne: string;
  brodtext: string;
}): Promise<void> {
  const apiKey = (process.env.RESEND_API_KEY ?? "").trim();
  if (!apiKey) {
    throw new Error("RESEND_API_KEY saknas — ingen utgående mailväg i den här miljön.");
  }

  const avsandare = (process.env.SMTP_FROM ?? "").trim() || "hej@snajp.se";
  const namn = (process.env.SMTP_FROM_NAME ?? "").trim() || "Snajp";

  const svar = await fetch(RESEND_ENDPOINT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from: `${namn} <${avsandare}>`,
      to: [args.till],
      subject: args.amne,
      text: args.brodtext
    }),
    cache: "no-store"
  });

  if (!svar.ok) {
    // Kroppen bär Resends förklaring (overifierad domän, ogiltig nyckel, kvot
    // slut) — klipps så en HTML-gatewaysida inte fyller loggen.
    const kropp = (await svar.text()).slice(0, 300);
    throw new Error(`Resend avvisade sändningen (${svar.status}): ${kropp}`);
  }
}
