/**
 * Inloggningens två steg som ren logik: spärren, lösenordet och
 * tvåstegsverifieringen, i den ordning `authorize` i `lib/auth.ts` kör dem.
 * Databasen och kryptot kommer in som beroenden, så att ordningen och
 * spärrens räkning går att pröva med `node --test lib/auth/inloggningssteg.test.ts`
 * utan databas. Delarna prövas mot databasen i
 * `snajp-support/tests/db/test_inloggningsforsok.py` och `test_tvafaktor.py`.
 *
 * Reglerna:
 *  - En spärrad adress eller IP prövar varken lösenord eller kod.
 *  - Lösenordet prövas alltid, också när kontot saknas (svarstiden).
 *  - Ett fel lösenord räknas som ett misslyckat försök.
 *  - Har kontot aktiv tvåfaktor och ingen kod gavs: "tvafaktor_kravs", utan
 *    att något räknas eller nollställs.
 *  - En fel eller redan använd kod räknas som ett misslyckat försök, i samma
 *    räknare som lösenordet: andra steget omfattas av samma spärr.
 *  - Räknaren nollställs bara när BÅDA stegen gått igenom.
 *  - Utfallet säger om andra steget prövades. Sessionen bär det, och
 *    adminrätten kräver det för ett konto med aktiv tvåfaktor
 *    (lib/auth/admin.ts:sessionenUppfyllerTvafaktor): en session från före
 *    aktiveringen, eller från en OAuth-inloggning, blir då ingen admin.
 */

export type Konto = { id: string; losenordshash: string | null };
export type TvafaktorLageMin = { aktiv: boolean };

export type Beroenden<L extends TvafaktorLageMin = TvafaktorLageMin> = {
  arSparrad(): Promise<boolean>;
  hittaKonto(): Promise<Konto | null>;
  provaLosenord(hash: string | null): Promise<boolean>;
  /** Registrerar ett misslyckat försök. Svarar true om försöket utlöste en spärr. */
  registreraMisslyckat(): Promise<boolean>;
  nollstall(): Promise<void>;
  lasTvafaktor(userId: string): Promise<L | null>;
  provaKod(userId: string, lage: L, kod: string): Promise<"ok" | "fel">;
};

export type Utfall =
  /** `tvafaktor`: andra steget prövades och godtogs i just den här inloggningen. */
  | { typ: "ok"; konto: Konto; tvafaktor: boolean }
  | { typ: "fel" }
  | { typ: "sparrad" }
  | { typ: "tvafaktor_kravs" }
  | { typ: "tvafaktor_fel" };

export async function loggaIn<L extends TvafaktorLageMin>(kod: string, b: Beroenden<L>): Promise<Utfall> {
  if (await b.arSparrad()) {
    return { typ: "sparrad" };
  }

  const konto = await b.hittaKonto();
  const ok = await b.provaLosenord(konto?.losenordshash ?? null);
  if (!ok || !konto) {
    return (await b.registreraMisslyckat()) ? { typ: "sparrad" } : { typ: "fel" };
  }

  const lage = await b.lasTvafaktor(konto.id);
  if (lage?.aktiv) {
    const ren = kod.trim();
    if (!ren) {
      return { typ: "tvafaktor_kravs" };
    }
    if ((await b.provaKod(konto.id, lage, ren)) !== "ok") {
      return (await b.registreraMisslyckat()) ? { typ: "sparrad" } : { typ: "tvafaktor_fel" };
    }
  }

  await b.nollstall();
  return { typ: "ok", konto, tvafaktor: Boolean(lage?.aktiv) };
}
