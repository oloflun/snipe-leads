import type { Locale, Localized } from "@/lib/i18n";

/**
 * Utkaststatusen per lead (Antons beställning 2026-10-07): samma sanning i
 * listan, lådan och nyckeltalen. Härledningen bor i backenden
 * (snajp-support/app/leads/utkaststatus.py) och följer med varje rad i
 * GET /leads/prospects och svaret från GET /leads/prospects/{id}/utkast.
 */

export type UtkastStatus = "saknas" | "vantar" | "godkant" | "koad" | "skickat" | "avvisat" | "stoppat";

export type Utkastfalt = {
  utkast_status?: UtkastStatus | null;
  /** Sändspärrens eller granskningens skäl (stoppat, ibland väntar). */
  utkast_skal?: string | null;
  /** Spärren som stoppade utkastet (send_guard_regel), bara för stoppat. */
  utkast_regel?: string | null;
  /** Köposten ett godkännande eller en redigering gäller (väntar, godkänt, köat). */
  queue_item_id?: string | null;
  /** När ett godkänt eller köat utkast tidigast går ut (nästa sändfönster). */
  skickas_tidigast?: string | null;
  skickat_at?: string | null;
};

export const UTKAST_ETIKETT: Record<UtkastStatus, Localized> = {
  saknas: { sv: "Inget utkast", en: "No draft" },
  vantar: { sv: "Väntar på ditt ja", en: "Waiting for your yes" },
  godkant: { sv: "Godkänt", en: "Approved" },
  koad: { sv: "Köat, ej granskat", en: "Queued, not reviewed" },
  skickat: { sv: "Skickat", en: "Sent" },
  avvisat: { sv: "Avvisat", en: "Rejected" },
  stoppat: { sv: "Stoppat av sändspärr", en: "Stopped by a send guard" }
};

/** Färgen per status, samma som körningsvyn (KorningensUtkast): ochre-text
 *  för det som väntar på kunden, moss för skickat, danger för stoppat. */
export const UTKAST_TON: Record<UtkastStatus, string> = {
  saknas: "text-ink-subtle",
  vantar: "text-warning",
  godkant: "text-ink-muted",
  koad: "text-warning",
  skickat: "text-moss",
  avvisat: "text-ink-subtle",
  stoppat: "text-danger"
};

/** Utkast som Godkänn och skicka tar: väntande, äldre köade och stoppade
 *  (2026-10-09: ett stopp kan vara åtgärdat, och spärrarna prövas om). */
export function kanSkickas(p: Utkastfalt): boolean {
  return Boolean(p.queue_item_id) && (p.utkast_status === "vantar" || p.utkast_status === "koad" || p.utkast_status === "stoppat");
}

/** Utkast som saknas eller avvisats: Skapa utkast skriver ett nytt. */
export const UTAN_UTKAST: ReadonlySet<string> = new Set(["saknas", "avvisat"]);

/** "08:00" i dag, annars "tors 08:00" — svensk tid, som sändfönstret. */
export function sandtid(iso: string, locale: Locale): string {
  const nar = new Date(iso);
  if (Number.isNaN(nar.getTime())) return "";
  const lokal = locale === "en" ? "en-GB" : "sv-SE";
  const dag = (d: Date) => d.toLocaleDateString(lokal, { timeZone: "Europe/Stockholm" });
  const klocka = nar.toLocaleTimeString(lokal, { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Stockholm" });
  if (dag(nar) === dag(new Date())) return klocka;
  return `${nar.toLocaleDateString(lokal, { weekday: "short", timeZone: "Europe/Stockholm" })} ${klocka}`;
}

/** Radens text: "Godkänt – skickas 08:00", "Stoppat av sändspärr" … */
export function utkastText(p: Utkastfalt, locale: Locale, text: (v: Localized) => string): string | null {
  const status = p.utkast_status;
  if (!status) return null;
  const etikett = text(UTKAST_ETIKETT[status]);
  if ((status === "godkant" || status === "koad") && p.skickas_tidigast) {
    const tid = sandtid(p.skickas_tidigast, locale);
    return tid ? `${etikett} – ${text({ sv: `skickas ${tid}`, en: `sends ${tid}` })}` : etikett;
  }
  return etikett;
}

/** Signalen att leads, utkast eller utskick ändrats (massåtgärd, godkännande,
 *  avvisning): listan, nyckeltalen och utkastrutan hämtar om. `kalla` låter
 *  avsändaren känna igen sin egen signal. */
export const LEADS_UPPDATERADE = "snipra:leads-uppdaterade";

export function meddelaLeadsUppdaterade(kalla: string): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(LEADS_UPPDATERADE, { detail: kalla }));
}
