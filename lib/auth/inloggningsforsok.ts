import "server-only";

import { sql } from "@/lib/db";
import {
  REGLER,
  klientIp,
  maskeraEpost,
  nyckel,
  type Handling,
  type Omfang
} from "@/lib/auth/inloggningsregler";

/**
 * Spärren mot upprepade inloggningsförsök, mot databasen (migration 125).
 * Reglerna och skälen står i `lib/auth/inloggningsregler.ts`.
 *
 * Ett fel mot databasen släpper igenom försöket och loggas högt. Skälet: när
 * databasen inte svarar går inloggningen ändå inte, och när bara funktionerna
 * saknas (en deploy som hann före migrationen) hade en stängd spärr låst ute
 * alla. Lösenordet prövas fortfarande; spärren är ett lager ovanpå.
 */

type Mal = { handling: Handling; omfang: Omfang; nyckel: string };

function mal(handling: Handling, epost: string, headers?: Pick<Headers, "get"> | null): Mal[] {
  const hemlighet = process.env.AUTH_SECRET;
  const lista: Mal[] = [
    { handling, omfang: "epost", nyckel: nyckel(handling, "epost", epost, hemlighet) }
  ];
  const ip = klientIp(headers);
  if (ip) {
    lista.push({ handling, omfang: "ip", nyckel: nyckel(handling, "ip", ip, hemlighet) });
  }
  return lista;
}

/** En rad i loggen per spärrat försök. Aldrig lösenordet, aldrig hela adressen. */
function loggaSparr(
  handelse: "sparrat_forsok" | "ny_sparr",
  handling: Handling,
  epost: string,
  headers: Pick<Headers, "get"> | null | undefined,
  till: Date | string | null,
  omfang?: Omfang
): void {
  console.warn(
    JSON.stringify({
      logg: "inloggningsspärr",
      handelse,
      handling,
      omfang: omfang ?? null,
      epost: maskeraEpost(epost),
      ip: klientIp(headers),
      sparrad_till: till ? new Date(till).toISOString() : null
    })
  );
}

/** Spärrad just nu? Svarar med spärrtiden, eller null. */
export async function arSparrad(
  handling: Handling,
  epost: string,
  headers?: Pick<Headers, "get"> | null
): Promise<Date | null> {
  try {
    const nycklar = mal(handling, epost, headers).map((m) => m.nyckel);
    const rader = await sql<{ till: Date | null }>(
      "select public.inloggningsforsok_sparrad($1::text[]) as till",
      [nycklar]
    );
    const till = rader[0]?.till ?? null;
    if (till) {
      loggaSparr("sparrat_forsok", handling, epost, headers, till);
    }
    return till ? new Date(till) : null;
  } catch (fel) {
    console.error("inloggningsspärr (kontroll) släppte igenom:", (fel as Error).message);
    return null;
  }
}

/**
 * Registrera ett försök (ett misslyckat lösenord, eller en återställningsbegäran)
 * på adressen och IP:t. Svarar med spärrtiden om försöket utlöste en spärr.
 */
export async function registreraForsok(
  handling: Handling,
  epost: string,
  headers?: Pick<Headers, "get"> | null
): Promise<Date | null> {
  let senast: Date | null = null;
  for (const m of mal(handling, epost, headers)) {
    const regel = REGLER[handling][m.omfang];
    try {
      const rader = await sql<{ till: Date | null }>(
        "select public.inloggningsforsok_registrera($1, $2, $3) as till",
        [m.nyckel, regel.troskel, regel.fonsterSekunder]
      );
      const till = rader[0]?.till ?? null;
      if (till) {
        loggaSparr("ny_sparr", handling, epost, headers, till, m.omfang);
        const d = new Date(till);
        if (!senast || d > senast) senast = d;
      }
    } catch (fel) {
      console.error("inloggningsspärr (registrering) misslyckades:", (fel as Error).message);
    }
  }
  return senast;
}

/** En lyckad inloggning: adressens räknare börjar om. IP:ts lämnas. */
export async function nollstallEpost(handling: Handling, epost: string): Promise<void> {
  try {
    await sql("select public.inloggningsforsok_nollstall($1)", [
      nyckel(handling, "epost", epost, process.env.AUTH_SECRET)
    ]);
  } catch (fel) {
    console.error("inloggningsspärr (nollställning) misslyckades:", (fel as Error).message);
  }
}
