import "server-only";

import { Pool, type PoolClient } from "pg";

/**
 * Postgres-anslutningen för Next-appen. Ersätter lib/supabase/server.ts.
 *
 * Rå SQL, ingen ORM: backenden kör redan rå SQL med asyncpg, och 18
 * anropsställen ger en ORM för lite hävstång för sin inlärningskostnad. Ett
 * mentalt mönster i kodbasen i stället för två.
 */

declare global {
  // Next laddar om moduler vid varje ändring i dev. Utan den här cachen läcker
  // en pool per omladdning tills Postgres vägrar fler anslutningar.
  // eslint-disable-next-line no-var
  var __snajpPool: Pool | undefined;
}

function connectionString(): string {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error("DATABASE_URL saknas — Next-appen kan inte nå databasen.");
  }
  return url;
}

export function hasDatabase(): boolean {
  return Boolean(process.env.DATABASE_URL);
}

export function pool(): Pool {
  if (!globalThis.__snajpPool) {
    globalThis.__snajpPool = new Pool({
      connectionString: connectionString(),
      max: 5,
      idleTimeoutMillis: 30_000,
      // Railway-Postgres kör med självsignerat certifikat i sitt privata nät.
      // rejectUnauthorized: false är rätt här och bara här: trafiken lämnar
      // aldrig Railways nät, och alternativet är att stänga av TLS helt.
      ssl: process.env.DATABASE_URL?.includes("proxy.rlwy.net")
        ? { rejectUnauthorized: false }
        : undefined
    });
  }
  return globalThis.__snajpPool;
}

/** En fråga utan användaridentitet. Använd bara där cross-tenant-läsning är avsikten. */
export async function sql<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  const result = await pool().query(text, params);
  return result.rows as T[];
}

/**
 * Kör frågor som en given användare, så att RLS-policyerna gäller.
 *
 * `set_config(..., true)` är transaktionslokalt med flit. Session-lokalt hade
 * läckt identiteten till nästa lånare av samma poolade anslutning — samma
 * klass av fel som migration 028 fick städa upp, fast åt andra hållet: där
 * blev värdet kvar som tom sträng, här hade det blivit kvar som NÅGON ANNANS
 * användar-id.
 */
export async function withUser<T>(
  userId: string,
  fn: (client: PoolClient) => Promise<T>
): Promise<T> {
  const client = await pool().connect();
  try {
    await client.query("begin");
    await client.query("select set_config('app.user_id', $1, true)", [userId]);
    const value = await fn(client);
    await client.query("commit");
    return value;
  } catch (error) {
    await client.query("rollback");
    throw error;
  } finally {
    client.release();
  }
}

/** Bekvämlighet: en enda skopad fråga, som är vad de flesta anropsställen gör. */
export async function sqlAsUser<T = Record<string, unknown>>(
  userId: string,
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  return withUser(userId, async (client) => {
    const result = await client.query(text, params);
    return result.rows as T[];
  });
}
