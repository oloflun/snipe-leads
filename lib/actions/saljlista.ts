"use server";

import { addonKeys } from "@/lib/addons";
import { arLasare } from "@/lib/auth/lasroll";
import { sqlAsUser } from "@/lib/db";
import {
  RAD_ID,
  SALJLISTA_FALT,
  arSaljstatus,
  normaliseraFalt,
  type Saljfalt,
  type Saljfel,
  type Saljrad,
  type Saljstatus,
  type Saljsvar
} from "@/lib/leads/saljlista";
import { aktivVy } from "@/lib/vy";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Säljlistan — CRM över bolag man ringt, en per arbetsyta. Ingår i tillägget
 * Leadslistor (Sebbes beslut 2026-10-06); tillägget slås på av oss när kunden
 * hört av sig. Tabellen är `saljlista` (migration 100 + 103).
 *
 * ## Grinden står i varje funktion
 *
 * En server action är en POST-endpoint med ett genererat id; att den bara
 * anropas från Listor-vyn är ett antagande om klienten (samma regel som
 * paket.ts och tillagg.ts). `grind()` körs därför först i varje funktion:
 * inloggad, tillägget på arbetsytan, adminens egen vy (i demovyn och i ett
 * kundbesök hade skrivningen hamnat i adminens EGEN arbetsyta medan skärmen
 * visade någon annans), och skrivningar nekas läsrollen. RLS-policyn i 103
 * isolerar sedan arbetsytorna från varandra.
 *
 * ## Felkoder, inte feltexter
 *
 * Svaren bär en kod; komponenten översätter den till svenska eller engelska
 * (INV-COPY-001). Databasens råa felmeddelande följer med i `detalj` bara
 * för det oväntade fallet.
 */

const KOLUMNER = `id, foretagsnamn, orgnr, kontaktperson, kontaktnummer, kontaktmail,
  to_char(senast_kontaktad, 'YYYY-MM-DD') as senast_kontaktad, anteckningar, status,
  created_at::text as created_at, updated_at::text as updated_at`;

const TILLAGG = "leadlists" satisfies (typeof addonKeys)[number];

type Behorighet = { ok: true; userId: string; workspaceId: string } | { ok: false; fel: Saljfel };

async function grind(skriv: boolean): Promise<Behorighet> {
  const context = await getWorkspaceContext();
  if (!context) return { ok: false, fel: "ej_inloggad" };
  if ((await aktivVy()).vy !== "admin") return { ok: false, fel: "fel_vy" };
  if (!(context.workspace.addons ?? []).includes(TILLAGG)) return { ok: false, fel: "saknar_tillagg" };
  if (skriv && arLasare(context)) return { ok: false, fel: "las_roll" };
  return { ok: true, userId: context.user.id, workspaceId: context.workspace.id };
}

/** 42P01 undefined_table / 42703 undefined_column: 100 eller 103 är inte körd i miljön. */
function felsvar(error: unknown): Saljsvar<never> {
  const fel = error as { code?: string; message?: string } | null;
  if (fel?.code === "42P01" || fel?.code === "42703") {
    return { ok: false, fel: "migration_saknas" };
  }
  console.error("saljlista:", fel?.message);
  return { ok: false, fel: "databasfel", detalj: fel?.message ?? undefined };
}

export async function hamtaSaljlista(): Promise<Saljsvar<Saljrad[]>> {
  const g = await grind(false);
  if (!g.ok) return g;
  try {
    const rader = await sqlAsUser<Saljrad>(
      g.userId,
      `select ${KOLUMNER} from public.saljlista where workspace_id = $1::uuid order by created_at desc`,
      [g.workspaceId]
    );
    return { ok: true, data: rader };
  } catch (error) {
    return felsvar(error);
  }
}

export async function laggTillSaljrad(
  falt: Partial<Record<Saljfalt, string | null>>
): Promise<Saljsvar<Saljrad>> {
  const g = await grind(true);
  if (!g.ok) return g;

  const varden: Record<Saljfalt, string | null> = {} as Record<Saljfalt, string | null>;
  for (const namn of SALJLISTA_FALT) {
    const normaliserat = normaliseraFalt(namn, falt[namn] ?? null);
    if (!normaliserat.ok) return { ok: false, fel: normaliserat.fel };
    varden[namn] = normaliserat.varde;
  }
  if (!varden.foretagsnamn) return { ok: false, fel: "namn_saknas" };

  try {
    const rader = await sqlAsUser<Saljrad>(
      g.userId,
      `insert into public.saljlista
         (workspace_id, foretagsnamn, orgnr, kontaktperson, kontaktnummer, kontaktmail,
          senast_kontaktad, anteckningar, skapad_av, uppdaterad_av)
       values ($1::uuid, $2, $3, $4, $5, $6, $7::date, $8, $9::uuid, $9::uuid)
       returning ${KOLUMNER}`,
      [
        g.workspaceId,
        varden.foretagsnamn,
        varden.orgnr ?? "",
        varden.kontaktperson ?? "",
        varden.kontaktnummer ?? "",
        varden.kontaktmail ?? "",
        varden.senast_kontaktad,
        varden.anteckningar ?? "",
        g.userId
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
  const g = await grind(true);
  if (!g.ok) return g;

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
      g.userId,
      `update public.saljlista
          set ${namn} = $3${typ}, uppdaterad_av = $4::uuid, updated_at = now()
        where id = $1::uuid and workspace_id = $2::uuid
        returning ${KOLUMNER}`,
      [id, g.workspaceId, nytt, g.userId]
    );
    const rad = rader[0];
    return rad ? { ok: true, data: rad } : { ok: false, fel: "finns_inte" };
  } catch (error) {
    return felsvar(error);
  }
}

/** Radens statusfärg (migration 104). Egen väg: status är ett val, inte fritext. */
export async function sattSaljstatus(id: string, status: Saljstatus): Promise<Saljsvar<Saljrad>> {
  const g = await grind(true);
  if (!g.ok) return g;
  if (!RAD_ID.test(id)) return { ok: false, fel: "finns_inte" };
  if (!arSaljstatus(status)) return { ok: false, fel: "okant_falt" };
  try {
    const rader = await sqlAsUser<Saljrad>(
      g.userId,
      `update public.saljlista
          set status = $3, uppdaterad_av = $4::uuid, updated_at = now()
        where id = $1::uuid and workspace_id = $2::uuid
        returning ${KOLUMNER}`,
      [id, g.workspaceId, status, g.userId]
    );
    const rad = rader[0];
    return rad ? { ok: true, data: rad } : { ok: false, fel: "finns_inte" };
  } catch (error) {
    return felsvar(error);
  }
}

export async function taBortSaljrad(id: string): Promise<Saljsvar<{ id: string }>> {
  const g = await grind(true);
  if (!g.ok) return g;
  if (!RAD_ID.test(id)) return { ok: false, fel: "finns_inte" };
  try {
    const rader = await sqlAsUser<{ id: string }>(
      g.userId,
      "delete from public.saljlista where id = $1::uuid and workspace_id = $2::uuid returning id",
      [id, g.workspaceId]
    );
    return rader[0] ? { ok: true, data: rader[0] } : { ok: false, fel: "finns_inte" };
  } catch (error) {
    return felsvar(error);
  }
}
