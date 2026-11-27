/**
 * Ren logik om ett mejls text, för CRM:ets Iris-vyer. Samma regler som dagens
 * Leads (components/leads/IrisGranskning.delaMejl, BekraftaUtskick.forstaMening),
 * men här i lib/crm så att CRM:et inte hänger på dagens gränssnittskomponenter,
 * som försvinner när dagens app avvecklas. Delningen speglar backendens
 * `signatur.dela_utkast` och `signatur._foraldrat_start`: ändras den där, ändra här.
 */
import type { Signatur } from "@/lib/crm/iris/utkast";

/** Avsändarens persongrupp: namn, titel, verksamhet, telefon och e-post, en per rad. */
function persongrupp(signatur: Signatur | null): string {
  if (!signatur) return "";
  return [signatur.namn, signatur.titel, signatur.verksamhet, signatur.telefon, signatur.epost].filter((rad): rad is string => Boolean(rad)).join("\n");
}

/**
 * Var ett föråldrat signaturblock börjar, eller -1: persongruppen ordagrant,
 * annars en rad som är exakt avsändarens namn följd av två till tolv korta
 * rader fram till foten (titeln eller adressen har bytts sedan mejlet skrevs).
 */
function foraldratStart(text: string, signatur: Signatur | null): number {
  if (!signatur) return -1;
  const pg = persongrupp(signatur);
  const pgIndex = pg ? text.indexOf(pg) : -1;
  if (pgIndex >= 0) return pgIndex;
  if (!signatur.namn) return -1;
  const fot = text.indexOf("\n--\n");
  const huvud = text.slice(0, fot >= 0 ? fot : text.length);
  let start = -1;
  let fran = 0;
  for (;;) {
    const i = huvud.indexOf(signatur.namn, fran);
    if (i < 0) break;
    const fore = i === 0 || huvud[i - 1] === "\n";
    const efter = huvud.slice(i + signatur.namn.length).match(/^[ \t]*(\n|$)/);
    if (fore && efter) start = i;
    fran = i + 1;
  }
  if (start < 0) return -1;
  const rader = huvud.slice(start).split("\n").filter((r) => r.trim());
  return rader.length >= 2 && rader.length <= 12 && rader.every((r) => r.length <= 90) ? start : -1;
}

/**
 * Mejlet delat i brödtexten och svansen (signaturblocket och/eller den
 * lagstadgade foten), från där den första av dem börjar. Ett föråldrat block
 * hör också till svansen.
 */
export function delaMejl(body: string, signatur: Signatur | null): [string, string] {
  const start: number[] = [];
  const sigIndex = signatur?.text ? body.indexOf(signatur.text) : -1;
  if (sigIndex >= 0) start.push(sigIndex);
  else {
    const pgIndex = foraldratStart(body, signatur);
    if (pgIndex >= 0) start.push(pgIndex);
  }
  const fotIndex = body.indexOf("\n--\n");
  if (fotIndex >= 0) start.push(fotIndex + 1);
  if (start.length === 0) return [body.trimEnd(), ""];
  const forst = Math.min(...start);
  return [body.slice(0, forst).trimEnd(), body.slice(forst).replace(/^\n+|\n+$/g, "")];
}

/** Mejlets första riktiga mening: hälsningsraden ("Hej," / "Hej Anna,") hoppas över. */
export function forstaMening(brodtext: string | null | undefined): string | null {
  const rader = String(brodtext ?? "")
    .split("\n")
    .map((r) => r.trim())
    .filter(Boolean);
  const rad = rader.find((r) => !/^(hej|hejsan|hallå|god (morgon|dag)|hi|hello)\b[^.!?]*,?$/i.test(r));
  if (!rad) return null;
  return rad.length > 180 ? `${rad.slice(0, 177)}…` : rad;
}
