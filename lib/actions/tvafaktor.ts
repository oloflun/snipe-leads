"use server";

import { headers } from "next/headers";
import { encode } from "uqr";

import { getPlatformAdminUtanTvafaktorkrav } from "@/lib/auth/admin";
import { arSparrad, registreraForsok } from "@/lib/auth/inloggningsforsok";
import { nyTotpHemlighet, otpauthAdress, provaTotp, serUtSomTotp } from "@/lib/auth/totp";
import {
  aktiveraTvafaktor,
  avaktiveraTvafaktor,
  lasTvafaktor,
  paborjaTvafaktor,
  provaOchForbruka
} from "@/lib/auth/tvafaktor";
import {
  ANTAL_ATERSTALLNINGSKODER,
  TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN,
  dekrypteraHemlighet,
  hashaAterstallningskod,
  krypteraHemlighet,
  nyaAterstallningskoder
} from "@/lib/auth/tvafaktor-krypto";

/**
 * Tvåstegsverifieringen för plattformsadmin: läge, inrullning och
 * avaktivering. Varje action prövar själv att anroparen är plattformsadmin;
 * en action är en POST-endpoint som vem som helst kan anropa.
 *
 * Svaren bär koder, inte text: komponenten (components/settings/Tvafaktor.tsx)
 * skriver beskedet på sidans språk.
 */

export type TvafaktorFelkod = "ej_admin" | "fel_kod" | "for_manga_forsok" | "redan_aktiv" | "ingen_inrullning" | "fel";

export type TvafaktorStatus =
  | { ok: true; aktiv: boolean; paborjad: boolean; koderKvar: number; kravs: boolean }
  | { ok: false; fel: TvafaktorFelkod };

export type TvafaktorInrullning =
  | { ok: true; hemlighet: string; otpauth: string; qr: boolean[][] }
  | { ok: false; fel: TvafaktorFelkod };

export type TvafaktorAktivering = { ok: true; koder: string[] } | { ok: false; fel: TvafaktorFelkod };

export type TvafaktorSvar = { ok: true } | { ok: false; fel: TvafaktorFelkod };

const UTFARDARE = "Snajp";

export async function hamtaTvafaktorStatus(): Promise<TvafaktorStatus> {
  const admin = await getPlatformAdminUtanTvafaktorkrav();
  if (!admin) return { ok: false, fel: "ej_admin" };
  try {
    const lage = await lasTvafaktor(admin.userId);
    return {
      ok: true,
      aktiv: Boolean(lage?.aktiv),
      paborjad: Boolean(lage && !lage.aktiv),
      koderKvar: lage?.koderKvar ?? 0,
      kravs: TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN
    };
  } catch (fel) {
    console.error("hamtaTvafaktorStatus:", (fel as Error).message);
    return { ok: false, fel: "fel" };
  }
}

/**
 * Steg 1: en ny hemlighet, krypterad i databasen men inte aktiverad.
 * Klienten får hemligheten (för den manuella inmatningen) och QR-kodens
 * moduler; QR-koden ritas i komponenten, ingen bild lämnar servern.
 */
export async function paborjaInrullning(): Promise<TvafaktorInrullning> {
  const admin = await getPlatformAdminUtanTvafaktorkrav();
  if (!admin) return { ok: false, fel: "ej_admin" };
  try {
    const lage = await lasTvafaktor(admin.userId);
    if (lage?.aktiv) return { ok: false, fel: "redan_aktiv" };
    const hemlighet = nyTotpHemlighet();
    const sparad = await paborjaTvafaktor(
      admin.userId,
      krypteraHemlighet(hemlighet, admin.userId, process.env.AUTH_SECRET)
    );
    if (!sparad) return { ok: false, fel: "fel" };
    const otpauth = otpauthAdress(UTFARDARE, admin.email ?? admin.userId, hemlighet);
    return { ok: true, hemlighet, otpauth, qr: encode(otpauth, { ecc: "M", border: 2 }).data };
  } catch (fel) {
    console.error("paborjaInrullning:", (fel as Error).message);
    return { ok: false, fel: "fel" };
  }
}

/**
 * Steg 2: koden ur appen bekräftar att hemligheten kom fram. Då aktiveras
 * tvåfaktorn och återställningskoderna skapas. Koderna visas EN gång, här;
 * databasen får bara deras hashar.
 */
export async function bekraftaInrullning(kod: string): Promise<TvafaktorAktivering> {
  const admin = await getPlatformAdminUtanTvafaktorkrav();
  if (!admin) return { ok: false, fel: "ej_admin" };
  try {
    const lage = await lasTvafaktor(admin.userId);
    if (!lage) return { ok: false, fel: "ingen_inrullning" };
    if (lage.aktiv) return { ok: false, fel: "redan_aktiv" };
    const authSecret = process.env.AUTH_SECRET;
    const hemlighet = dekrypteraHemlighet(lage.hemlighet, admin.userId, authSecret);
    if (!hemlighet) return { ok: false, fel: "ingen_inrullning" };
    const steg = serUtSomTotp(kod) ? provaTotp(hemlighet, kod) : null;
    if (steg === null) return { ok: false, fel: "fel_kod" };
    const koder = nyaAterstallningskoder(ANTAL_ATERSTALLNINGSKODER);
    const aktiverad = await aktiveraTvafaktor(
      admin.userId,
      steg,
      koder.map((k) => hashaAterstallningskod(k, authSecret))
    );
    if (!aktiverad) return { ok: false, fel: "fel" };
    return { ok: true, koder };
  } catch (fel) {
    console.error("bekraftaInrullning:", (fel as Error).message);
    return { ok: false, fel: "fel" };
  }
}

/** Avbryt en påbörjad (ej bekräftad) inrullning. Kräver ingen kod: inget skydd är på. */
export async function avbrytInrullning(): Promise<TvafaktorSvar> {
  const admin = await getPlatformAdminUtanTvafaktorkrav();
  if (!admin) return { ok: false, fel: "ej_admin" };
  try {
    const lage = await lasTvafaktor(admin.userId);
    if (lage?.aktiv) return { ok: false, fel: "redan_aktiv" };
    await avaktiveraTvafaktor(admin.userId);
    return { ok: true };
  } catch (fel) {
    console.error("avbrytInrullning:", (fel as Error).message);
    return { ok: false, fel: "fel" };
  }
}

/**
 * Stäng av tvåfaktorn. Kräver en giltig kod (TOTP eller återställningskod),
 * prövad och förbrukad som vid inloggningen, och omfattas av samma spärr: en
 * stulen session kan inte gissa sig fram till att stänga av skyddet.
 * Databasen vägrar dessutom själv utan en godkänd kod de senaste två minuterna.
 */
export async function avaktiveraMedKod(kod: string): Promise<TvafaktorSvar> {
  const admin = await getPlatformAdminUtanTvafaktorkrav();
  if (!admin) return { ok: false, fel: "ej_admin" };
  const epost = admin.email ?? admin.userId;
  const inkommande = await headers();
  try {
    if (await arSparrad("inloggning", epost, inkommande)) {
      return { ok: false, fel: "for_manga_forsok" };
    }
    const lage = await lasTvafaktor(admin.userId);
    if (!lage?.aktiv) return { ok: false, fel: "ingen_inrullning" };
    if ((await provaOchForbruka(admin.userId, lage, kod.trim())) !== "ok") {
      if (await registreraForsok("inloggning", epost, inkommande)) {
        return { ok: false, fel: "for_manga_forsok" };
      }
      return { ok: false, fel: "fel_kod" };
    }
    return (await avaktiveraTvafaktor(admin.userId)) ? { ok: true } : { ok: false, fel: "fel" };
  } catch (fel) {
    console.error("avaktiveraMedKod:", (fel as Error).message);
    return { ok: false, fel: "fel" };
  }
}
