/**
 * Webbgrinden, på ETT ställe (LR-090 till LR-097, Antons beslut 2026-10-08).
 *
 * Webbplatsbedömningen är hemlig: bara plattformsadmin, Umeå Webdesign och
 * Alunix får se den. Grinden sitter i backenden (`webbpool.far_se`, `dolj`): för
 * alla andra tas `webbrevision` och `webbniva` bort ur varje svar. Gränssnittet
 * räknar aldrig ut bedömningen själv och gissar aldrig om kunden får se den:
 * det visar en kolumn, ett filter, en sortering eller panelens del om sajten
 * BARA när svaret bär fälten. Saknas de finns inget val att visa, inte ens en tom
 * kolumn.
 */
import type { Lead, Webbrevision } from "@/lib/crm/iris/lead";

/** Bär raden webbplatsbedömningen? Sant bara när backenden lämnat fältet. */
export function barWebb(rad: Pick<Lead, "webbrevision" | "webbniva"> | null | undefined): boolean {
  if (!rad) return false;
  return (rad.webbrevision != null && typeof rad.webbrevision === "object") || typeof rad.webbniva === "string";
}

/** Bär någon av raderna ett betyg? Då, och bara då, finns kolumnen, filtret och sorteringen (LR-090). */
export function nagonHarBetyg(rader: readonly Lead[]): boolean {
  return rader.some((r) => typeof betyg(r) === "number");
}

/** Betyget (modernitet 1 till 10) som backenden satte, eller null. */
export function betyg(rad: Pick<Lead, "webbrevision">): number | null {
  const m = (rad.webbrevision as Webbrevision | null | undefined)?.modernitet;
  return typeof m === "number" ? m : null;
}

/** Första synliga bristen, som backenden lämnar den. */
export function forstaBrist(rad: Pick<Lead, "webbrevision">): string | null {
  const b = (rad.webbrevision as Webbrevision | null | undefined)?.brister;
  return Array.isArray(b) && b.length ? String(b[0]) : null;
}

/**
 * Betygets band i dagens Iris-lista (LR-090): 1 till 4 är ett bra lead för en
 * webbyrå (dålig sajt), 5 till 6 mitt emellan, 7 till 10 en bra sajt. Bandet
 * är bara färg och filter för ett betyg som redan finns; det räknar inte ut
 * någon bedömning.
 */
export type Betygsband = "lag" | "mellan" | "hog";

export function band(m: number): Betygsband {
  return m <= 4 ? "lag" : m <= 6 ? "mellan" : "hog";
}
