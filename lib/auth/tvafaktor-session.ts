/**
 * Duger sessionen för adminrätt med hänsyn till tvåfaktorn? Ren regel, prövad
 * med `node --test lib/auth/tvafaktor-session.test.ts` utan databas.
 *
 * Sant när inloggningen gick igenom andra steget (markeringen i JWT:n,
 * lib/auth.ts), eller när kontot inte har aktiv tvåfaktor. Ett uppslagsfel
 * räknas som "har tvåfaktor" (fail closed). Uppslaget görs bara när
 * markeringen saknas.
 *
 * Varför: aktiveringen återkallar inga sessioner. Utan regeln behöll en
 * session från före aktiveringen, eller en stulen sådan, adminrätten utan kod
 * (Codex-granskningen 2026-11-19).
 */
export async function sessionenUppfyllerTvafaktor(
  userId: string,
  tvafaktorISessionen: boolean,
  harAktiv: (userId: string) => Promise<boolean>
): Promise<boolean> {
  if (tvafaktorISessionen) {
    return true;
  }
  try {
    return !(await harAktiv(userId));
  } catch (error) {
    console.error("sessionenUppfyllerTvafaktor:", (error as Error).message);
    return false;
  }
}
