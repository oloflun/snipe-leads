import "server-only";

import { sql, sqlAsUser } from "@/lib/db";
import { provaTotp, serUtSomTotp } from "@/lib/auth/totp";
import {
  dekrypteraHemlighet,
  hashaAterstallningskod,
  serUtSomAterstallningskod
} from "@/lib/auth/tvafaktor-krypto";

/**
 * Tvåstegsverifieringen mot databasen (migration 128). Logiken som inte
 * behöver databasen står i `lib/auth/totp.ts` och `lib/auth/tvafaktor-krypto.ts`.
 *
 * Tabellerna nås bara genom funktionerna i 128. Databasen ser aldrig
 * hemligheten i klartext; webben dekrypterar och prövar koden, och databasen
 * förbrukar steget eller återställningskoden atomiskt.
 */

export type TvafaktorLage = {
  aktiv: boolean;
  /** Krypterad. Lämnar aldrig servern. */
  hemlighet: string;
  senasteSteg: number | null;
  koderKvar: number;
};

type Rad = { aktiv: boolean; hemlighet: string; senaste_steg: string | null; koder_kvar: number };

function tillLage(rad: Rad | undefined): TvafaktorLage | null {
  if (!rad) return null;
  return {
    aktiv: rad.aktiv,
    hemlighet: rad.hemlighet,
    senasteSteg: rad.senaste_steg === null ? null : Number(rad.senaste_steg),
    koderKvar: rad.koder_kvar
  };
}

/** Postgres felkod för en funktion som inte finns (migrationen ännu inte körd). */
const FUNKTION_SAKNAS = "42883";

/**
 * Kontots tvåfaktorläge, eller null om ingen rad finns.
 *
 * Ett databasfel KASTAS (fail closed): en uppslagning som inte gick att göra
 * får inte betyda "ingen tvåfaktor", då hade ett avbrott stängt av skyddet.
 * Undantaget är en funktion som inte finns ännu (en deploy som hann före
 * migration 128): då kan ingen ha rullat in tvåfaktor, och svaret null är sant.
 */
export async function lasTvafaktor(userId: string): Promise<TvafaktorLage | null> {
  try {
    const rader = await sql<Rad>(
      "select aktiv, hemlighet, senaste_steg, koder_kvar from public.tvafaktor_las($1::uuid)",
      [userId]
    );
    return tillLage(rader[0]);
  } catch (fel) {
    if ((fel as { code?: string }).code === FUNKTION_SAKNAS) {
      console.error("tvåfaktor: migration 128 saknas, ingen tvåfaktor prövas");
      return null;
    }
    throw fel;
  }
}

export async function harAktivTvafaktor(userId: string): Promise<boolean> {
  return Boolean((await lasTvafaktor(userId))?.aktiv);
}

export type Provning = "ok" | "fel";

/**
 * Prövar en kod mot ett aktivt läge och förbrukar den: en TOTP-kod (sex
 * siffror) förbrukar sitt tidssteg, en återställningskod förbrukas helt.
 * Svarar "ok" bara om koden var giltig OCH inte använd förut.
 */
export async function provaOchForbruka(userId: string, lage: TvafaktorLage, kod: string): Promise<Provning> {
  const authSecret = process.env.AUTH_SECRET;
  if (serUtSomTotp(kod)) {
    const hemlighet = dekrypteraHemlighet(lage.hemlighet, userId, authSecret);
    if (!hemlighet) {
      // Bytt AUTH_SECRET eller en skadad rad: ingen TOTP-kod kan stämma.
      // Återställningskoderna är bundna till samma nyckel; kontot måste
      // rullas in på nytt (AUTH.md).
      console.error("tvåfaktor: hemligheten går inte att dekryptera (bytt AUTH_SECRET?)");
      return "fel";
    }
    const steg = provaTotp(hemlighet, kod, Date.now(), lage.senasteSteg);
    if (steg === null) return "fel";
    const rader = await sql<{ ok: boolean }>("select public.tvafaktor_anvand_steg($1::uuid, $2::bigint) as ok", [
      userId,
      steg
    ]);
    return rader[0]?.ok ? "ok" : "fel";
  }
  if (serUtSomAterstallningskod(kod)) {
    const rader = await sql<{ ok: boolean }>(
      "select public.tvafaktor_anvand_aterstallningskod($1::uuid, $2) as ok",
      [userId, hashaAterstallningskod(kod, authSecret)]
    );
    return rader[0]?.ok ? "ok" : "fel";
  }
  return "fel";
}

/** Påbörja inrullningen med en krypterad hemlighet. Bara plattformsadmin (128). */
export async function paborjaTvafaktor(userId: string, krypterad: string): Promise<boolean> {
  const rader = await sqlAsUser<{ ok: boolean }>(userId, "select public.tvafaktor_paborja($1) as ok", [krypterad]);
  return Boolean(rader[0]?.ok);
}

/** Aktivera efter en godkänd kod; byter återställningskoderna (hashar). */
export async function aktiveraTvafaktor(userId: string, steg: number, kodhashar: string[]): Promise<boolean> {
  const rader = await sqlAsUser<{ ok: boolean }>(
    userId,
    "select public.tvafaktor_aktivera($1::bigint, $2::text[]) as ok",
    [steg, kodhashar]
  );
  return Boolean(rader[0]?.ok);
}

/** Ta bort tvåfaktorn. Databasen kräver en godkänd kod de senaste två minuterna. */
export async function avaktiveraTvafaktor(userId: string): Promise<boolean> {
  const rader = await sqlAsUser<{ ok: boolean }>(userId, "select public.tvafaktor_avaktivera() as ok");
  return Boolean(rader[0]?.ok);
}
