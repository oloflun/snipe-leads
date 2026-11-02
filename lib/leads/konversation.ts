/**
 * Konversationen bakom ett skickat leadsmejl (Leads › Inkorg › Skickat,
 * Sebbe 2026-11-02: "man ska se hela konversationen"). Backend:
 * GET /api/leads/skickat lägger `konversation` på varje rad vars tråd fått svar.
 */

export type KonversationsMejl = {
  id: string;
  direction: "inbound" | "outbound";
  subject: string | null;
  body: string;
  sent_at: string;
};

/** Raderna där ett svar börjar citera det tidigare mejlet: Gmails "Den … skrev
 *  …:" / "On … wrote:" (ibland radbruten), Outlooks Från:/Skickat:-block,
 *  avdelaren "-----Ursprungligt meddelande-----" och ">"-citat. */
const CITATSTART = [
  /^(?:Den|On)\s[^\n]*(?:\n[^\n]*)?\b(?:skrev|wrote)\b[^\n]*:[ \t]*$/m,
  /^-{2,}\s*(?:Ursprungligt meddelande|Original Message|Vidarebefordrat meddelande|Forwarded message)\s*-{2,}/im,
  /^(?:Från|From):[^\n]*\n(?:Skickat|Sent|Datum|Date):/m,
  /^>/m
];

/** Delar ett inkommet svar i det mottagaren skrev och det citerade mejlet
 *  under. Utan citat, eller när allt är citat, är hela texten svaret. */
export function delaCitat(body: string): [svar: string, citat: string] {
  const start = CITATSTART.map((re) => body.search(re)).filter((i) => i > 0);
  if (start.length === 0) return [body.trim(), ""];
  const i = Math.min(...start);
  const svar = body.slice(0, i).trim();
  return svar ? [svar, body.slice(i).trim()] : [body.trim(), ""];
}

/** Det senaste inkomna svaret i konversationen, eller null. */
export function senasteSvar(konversation: readonly KonversationsMejl[] | undefined): KonversationsMejl | null {
  const svar = (konversation ?? []).filter((m) => m.direction === "inbound");
  return svar.length ? svar[svar.length - 1] : null;
}
