"use server";

import { getPlatformAdmin } from "@/lib/auth/admin";
import { sqlAsUser } from "@/lib/db";
import {
  RAD_ID,
  SALJLISTA_FALT,
  normaliseraFalt,
  type Saljfalt,
  type Saljrad,
  type Saljsvar
} from "@/lib/leads/saljlista";

/**
 * Snajps egen säljlista — plattformsadminens CRM över bolag vi ringt
 * (migration 100, Sebbes beställning 2026-10-06).
 *
 * ## Grinden står i varje funktion
 *
 * En server action är en POST-endpoint med ett genererat id; att den bara
 * anropas från adminvyn är ett antagande om klienten (samma regel som
 * paket.ts och tillagg.ts). `getPlatformAdmin()` körs därför först i varje
 * funktion, och RLS-policyn i 100 kontrollerar platform_admins en gång till.
 *
 * ## Felkoder, inte feltexter
 *
 * Svaren bär en kod; komponenten översätter den till svenska eller engelska
 * (INV-COPY-001). Databasens råa felmeddelande följer med i `detalj` bara
 * för det oväntade fallet.
 */

const KOLUMNER = `id, foretagsnamn, orgnr, kontaktperson, kontaktnummer, kontaktmail,
  to_char(senast_kontaktad, 'YYYY-MM-DD') as senast_kontaktad, anteckningar,
  created_at::text as created_at, updated_at::text as updated_at`;

/** 42P01 är undefined_table: migration 100 är inte körd i miljön. */
function felsvar(error: unknown): Saljsvar<never> {
  const fel = error as { code?: string; message?: string } | null;
  if (fel?.code === "42P01" || /snajp_saljlista.*does not exist/i.test(fel?.message ?? "")) {
    return { ok: false, fel: "migration_saknas" };
  }
  console.error("saljlista:", fel?.message);
  return { ok: false, fel: "databasfel", detalj: fel?.message ?? undefined };
}

export async function hamtaSaljlista(): Promise<Saljsvar<Saljrad[]>> {
  const admin = await getPlatformAdmin();
  if (!admin) return { ok: false, fel: "ej_admin" };
  try {
    const rader = await sqlAsUser<Saljrad>(
      admin.userId,
      `select ${KOLUMNER} from public.snajp_saljlista order by created_at desc`
    );
    return { ok: true, data: rader };
  } catch (error) {
    return felsvar(error);
  }
}

export async function laggTillSaljrad(
  falt: Partial<Record<Saljfalt, string | null>>
): Promise<Saljsvar<Saljrad>> {
  const admin = await getPlatformAdmin();
  if (!admin) return { ok: false, fel: "ej_admin" };

  const varden: Record<Saljfalt, string | null> = {} as Record<Saljfalt, string | null>;
  for (const namn of SALJLISTA_FALT) {
    const normaliserat = normaliseraFalt(namn, falt[namn] ?? null);
    if (!normaliserat.ok) return { ok: false, fel: normaliserat.fel };
    varden[namn] = normaliserat.varde;
  }
  if (!varden.foretagsnamn) return { ok: false, fel: "namn_saknas" };

  try {
    const rader = await sqlAsUser<Saljrad>(
      admin.userId,
      `insert into public.snajp_saljlista
         (foretagsnamn, orgnr, kontaktperson, kontaktnummer, kontaktmail,
          senast_kontaktad, anteckningar, skapad_av, uppdaterad_av)
       values ($1, $2, $3, $4, $5, $6::date, $7, $8::uuid, $8::uuid)
       returning ${KOLUMNER}`,
      [
        varden.foretagsnamn,
        varden.orgnr ?? "",
        varden.kontaktperson ?? "",
        varden.kontaktnummer ?? "",
        varden.kontaktmail ?? "",
        varden.senast_kontaktad,
        varden.anteckningar ?? "",
        admin.userId
      ]
    );
    const rad = rader[0];
    return rad ? { ok: true, data: rad } : { ok: false, fel: "databasfel" };
  } catch (error) {
    return felsvar(error);
  }
}

export async function uppdateraSaljrad(
  id: string,
  namn: Saljfalt,
  varde: string | null
): Promise<Saljsvar<Saljrad>> {
  const admin = await getPlatformAdmin();
  if (!admin) return { ok: false, fel: "ej_admin" };

  if (!RAD_ID.test(id)) return { ok: false, fel: "finns_inte" };
  // Kolumnnamnet interpoleras i SQL:en — därför vitlistan, aldrig klientens sträng rakt av.
  if (!SALJLISTA_FALT.includes(namn)) return { ok: false, fel: "okant_falt" };
  const normaliserat = normaliseraFalt(namn, varde);
  if (!normaliserat.ok) return { ok: false, fel: normaliserat.fel };
  if (namn === "foretagsnamn" && !normaliserat.varde) return { ok: false, fel: "namn_saknas" };

  const typ = namn === "senast_kontaktad" ? "::date" : "";
  const nytt = namn === "senast_kontaktad" ? normaliserat.varde : (normaliserat.varde ?? "");

  try {
    const rader = await sqlAsUser<Saljrad>(
      admin.userId,
      `update public.snajp_saljlista
          set ${namn} = $2${typ}, uppdaterad_av = $3::uuid, updated_at = now()
        where id = $1::uuid
        returning ${KOLUMNER}`,
      [id, nytt, admin.userId]
    );
    const rad = rader[0];
    return rad ? { ok: true, data: rad } : { ok: false, fel: "finns_inte" };
  } catch (error) {
    return felsvar(error);
  }
}

export async function taBortSaljrad(id: string): Promise<Saljsvar<{ id: string }>> {
  const admin = await getPlatformAdmin();
  if (!admin) return { ok: false, fel: "ej_admin" };
  if (!RAD_ID.test(id)) return { ok: false, fel: "finns_inte" };
  try {
    const rader = await sqlAsUser<{ id: string }>(
      admin.userId,
      "delete from public.snajp_saljlista where id = $1::uuid returning id",
      [id]
    );
    return rader[0] ? { ok: true, data: rader[0] } : { ok: false, fel: "finns_inte" };
  } catch (error) {
    return felsvar(error);
  }
}
