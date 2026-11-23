import { parseCsv } from "./csv.ts";

/**
 * Listimportens filläsare: byte in, tabeller ut. Läser det säljare faktiskt
 * har på datorn (hårdtest 2026-11-23, Antons beställning):
 *
 *   - CSV, TSV och textfiler i UTF-8, UTF-16 (Excels "Unicode-text"),
 *     Windows-1252 (svensk Excels "CSV (avgränsad)") och Mac Roman.
 *   - Excel-arbetsböcker (.xlsx), med delade strängar, datumformat och flera
 *     blad. Läses utan beroende: zip-katalogen, DecompressionStream och
 *     reguljära uttryck över maskinskriven XML.
 *   - HTML-tabeller och XML Spreadsheet 2003, som äldre CRM sparar som ".xls".
 *
 * Det gamla binära .xls-formatet och andra filer avvisas med en kod som
 * UI:t översätter till en anvisning ("spara som .xlsx eller CSV").
 */

export type Blad = { namn: string; rader: string[][] };
export type Importfil = { format: "csv" | "xlsx" | "html" | "xml"; kodning?: string; blad: Blad[] };

/** `xls` gammal binär Excel · `format` ingen tabell · `stor` över taket ·
 *  `trasig` gick inte att packa upp · `tom` inga rader. */
export type ImportFelkod = "xls" | "format" | "stor" | "trasig" | "tom";

export class ImportFel extends Error {
  kod: ImportFelkod;
  constructor(kod: ImportFelkod) {
    super(kod);
    this.kod = kod;
  }
}

/** Filer över taket läses inte: de fryser fliken innan något hinner visas. */
export const MAX_FILSTORLEK = 15 * 1024 * 1024;
/** Tak för en uppackad del i en arbetsbok (skydd mot zip-bomber). */
const MAX_UPPACKAT = 200 * 1024 * 1024;

// ------------------------------------------------------------ teckenkodning

function avkodaMed(kodning: string, bytes: Uint8Array, strikt = false): string {
  return new TextDecoder(kodning, { fatal: strikt }).decode(bytes);
}

/**
 * Texten och kodningen den lästes i. BOM avgör; utan BOM prövas UTF-16
 * (varannan byte noll), sedan strikt UTF-8, sist Windows-1252. Mac Roman
 * känns igen på byten: å, ä och ö är 0x8C, 0x8A och 0x9A där (Œ, Š och š i
 * Windows-1252, som svenska listor inte innehåller), och Windows-1252 har
 * dem på 0xE5, 0xE4 och 0xF6.
 */
export function avkoda(bytes: Uint8Array): { text: string; kodning: string } {
  if (bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) return { text: avkodaMed("utf-8", bytes.subarray(3)), kodning: "utf-8" };
  if (bytes[0] === 0xff && bytes[1] === 0xfe) return { text: avkodaMed("utf-16le", bytes.subarray(2)), kodning: "utf-16le" };
  if (bytes[0] === 0xfe && bytes[1] === 0xff) return { text: avkodaMed("utf-16be", bytes.subarray(2)), kodning: "utf-16be" };

  const prov = Math.min(bytes.length, 4000) & ~1;
  let jamna = 0;
  let udda = 0;
  for (let i = 0; i < prov; i += 2) {
    if (bytes[i] === 0) jamna++;
    if (bytes[i + 1] === 0) udda++;
  }
  if (prov >= 8 && udda > prov * 0.2 && jamna < prov * 0.02) return { text: avkodaMed("utf-16le", bytes), kodning: "utf-16le" };
  if (prov >= 8 && jamna > prov * 0.2 && udda < prov * 0.02) return { text: avkodaMed("utf-16be", bytes), kodning: "utf-16be" };

  try {
    return { text: avkodaMed("utf-8", bytes, true), kodning: "utf-8" };
  } catch {
    let mac = 0;
    let windows = 0;
    for (const byte of bytes) {
      if (byte === 0x8a || byte === 0x8c || byte === 0x9a) mac++;
      else if (byte === 0xe4 || byte === 0xe5 || byte === 0xf6 || byte === 0xc4 || byte === 0xc5 || byte === 0xd6) windows++;
    }
    const kodning = mac > 0 && windows === 0 ? "macintosh" : "windows-1252";
    return { text: avkodaMed(kodning, bytes), kodning };
  }
}

// ------------------------------------------------------------------ XML-hjälp

const ENTITETER: Record<string, string> = {
  amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ",
  aring: "å", auml: "ä", ouml: "ö", Aring: "Å", Auml: "Ä", Ouml: "Ö", eacute: "é", Eacute: "É", uuml: "ü", Uuml: "Ü"
};

function avkodaEntiteter(s: string): string {
  if (!s.includes("&") && !s.includes("_x")) return s;
  return s
    .replace(/&(#x[0-9a-f]+|#\d+|\w+);/gi, (hel, namn: string) => {
      if (namn[0] !== "#") return ENTITETER[namn] ?? hel;
      const kod = namn[1].toLowerCase() === "x" ? parseInt(namn.slice(2), 16) : parseInt(namn.slice(1), 10);
      return Number.isFinite(kod) && kod > 0 && kod <= 0x10ffff ? String.fromCodePoint(kod) : "";
    })
    // Excel skriver styrtecken som _x000D_ i strängar.
    .replace(/_x([0-9A-Fa-f]{4})_/g, (_, hex: string) => String.fromCharCode(parseInt(hex, 16)));
}

function attribut(tagg: string): Record<string, string> {
  const ut: Record<string, string> = {};
  for (const m of tagg.matchAll(/([\w:.-]+)\s*=\s*"([^"]*)"/g)) ut[m[1]] = avkodaEntiteter(m[2]);
  return ut;
}

/** Tar bort tomma celler i slutet av varje rad och rader utan innehåll. */
function stada(rader: string[][]): string[][] {
  return rader
    .map((rad) => {
      const r = rad.map((c) => (c ?? "").replace(/\r\n?/g, "\n").trim());
      while (r.length && r[r.length - 1] === "") r.pop();
      return r;
    })
    .filter((rad) => rad.length > 0);
}

// ------------------------------------------------------------------- .xlsx

type ZipPost = { metod: number; komprimerad: number; okomprimerad: number; offset: number };

function zipKatalog(b: Uint8Array): Map<string, ZipPost> {
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
  // Katalogens slutpost ligger sist, före en kommentar på högst 65 535 byte.
  let i = b.length - 22;
  const golv = Math.max(0, i - 65535);
  while (i >= golv && v.getUint32(i, true) !== 0x06054b50) i--;
  if (i < golv) throw new ImportFel("trasig");
  const antal = v.getUint16(i + 10, true);
  let p = v.getUint32(i + 16, true);
  const ut = new Map<string, ZipPost>();
  for (let n = 0; n < antal && p + 46 <= b.length && v.getUint32(p, true) === 0x02014b50; n++) {
    const namnLangd = v.getUint16(p + 28, true);
    ut.set(avkodaMed("utf-8", b.subarray(p + 46, p + 46 + namnLangd)), {
      metod: v.getUint16(p + 10, true),
      komprimerad: v.getUint32(p + 20, true),
      okomprimerad: v.getUint32(p + 24, true),
      offset: v.getUint32(p + 42, true)
    });
    p += 46 + namnLangd + v.getUint16(p + 30, true) + v.getUint16(p + 32, true);
  }
  return ut;
}

async function zipText(b: Uint8Array, post: ZipPost | undefined): Promise<string> {
  if (!post) return "";
  if (post.okomprimerad > MAX_UPPACKAT) throw new ImportFel("stor");
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
  const start = post.offset + 30 + v.getUint16(post.offset + 26, true) + v.getUint16(post.offset + 28, true);
  const data = b.slice(start, start + post.komprimerad);
  if (post.metod === 0) return avkodaMed("utf-8", data);
  if (post.metod !== 8) throw new ImportFel("trasig");
  try {
    const strom = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return avkodaMed("utf-8", new Uint8Array(await new Response(strom).arrayBuffer()));
  } catch {
    throw new ImportFel("trasig");
  }
}

/** Excels inbyggda datumformat (ECMA-376 del 1, 18.8.30) plus de östasiatiska. */
const DATUMFORMAT = new Set([14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58]);

/** Sant per cellformat (index i cellXfs) när formatet visar ett datum. */
function datumstilar(styles: string): boolean[] {
  const egna = new Map<number, boolean>();
  for (const m of styles.matchAll(/<(?:\w+:)?numFmt\b([^>]*)>/g)) {
    const a = attribut(m[1]);
    // Citerad text, escapade tecken och [färg]/[$-41D] är inte formatkoder.
    const kod = (a.formatCode ?? "").replace(/"[^"]*"|\\.|\[[^\]]*\]/g, "");
    egna.set(Number(a.numFmtId), /[dmyhs]/i.test(kod));
  }
  const xfs = /<(?:\w+:)?cellXfs\b[^>]*>([\s\S]*?)<\/(?:\w+:)?cellXfs>/.exec(styles)?.[1] ?? "";
  return [...xfs.matchAll(/<(?:\w+:)?xf\b([^>]*)>/g)].map((m) => {
    const id = Number(attribut(m[1]).numFmtId ?? 0);
    return egna.get(id) ?? DATUMFORMAT.has(id);
  });
}

const tva = (n: number) => String(n).padStart(2, "0");

/** Excels löpnummer som ISO-datum (med klockslag om det finns ett). */
export function excelDatum(lopnummer: number, bas1904 = false): string {
  const ms = Math.round((lopnummer + (bas1904 ? 1462 : 0)) * 86_400_000);
  const d = new Date(Date.UTC(1899, 11, 30) + ms);
  const dag = `${d.getUTCFullYear()}-${tva(d.getUTCMonth() + 1)}-${tva(d.getUTCDate())}`;
  return ms % 86_400_000 === 0 ? dag : `${dag} ${tva(d.getUTCHours())}:${tva(d.getUTCMinutes())}`;
}

/** Talet som text utan exponent och flyttalsbrus: 5.560000001E9 → 5560000001. */
function talText(ra: string): string {
  const n = Number(ra);
  if (ra.trim() === "" || !Number.isFinite(n)) return ra;
  return Number.isInteger(n) ? n.toLocaleString("en-US", { useGrouping: false, maximumFractionDigits: 0 }) : String(Number(n.toPrecision(15)));
}

const textdelar = (xml: string) =>
  [...xml.replace(/<(?:\w+:)?rPh\b[\s\S]*?<\/(?:\w+:)?rPh>/g, "").matchAll(/<(?:\w+:)?t\b[^>]*>([\s\S]*?)<\/(?:\w+:)?t>/g)]
    .map((m) => avkodaEntiteter(m[1]))
    .join("");

function kolumnindex(ref: string): number {
  let n = 0;
  for (const tecken of ref) {
    const kod = tecken.charCodeAt(0);
    if (kod < 65 || kod > 90) break;
    n = n * 26 + (kod - 64);
  }
  return n - 1;
}

function bladrader(xml: string, strangar: string[], datum: boolean[], bas1904: boolean): string[][] {
  const rader: string[][] = [];
  for (const radtraff of xml.matchAll(/<(?:\w+:)?row\b[^>]*?(?:\/>|>([\s\S]*?)<\/(?:\w+:)?row>)/g)) {
    const rad: string[] = [];
    for (const c of (radtraff[1] ?? "").matchAll(/<(?:\w+:)?c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/(?:\w+:)?c>)/g)) {
      const a = attribut(c[1]);
      const inre = c[2] ?? "";
      const ra = /<(?:\w+:)?v\b[^>]*>([\s\S]*?)<\/(?:\w+:)?v>/.exec(inre)?.[1] ?? "";
      let varde: string;
      if (a.t === "s") varde = strangar[Number(ra)] ?? "";
      else if (a.t === "inlineStr") varde = textdelar(inre);
      else if (a.t === "str") varde = avkodaEntiteter(ra);
      else if (a.t === "e") varde = "";
      else if (a.t === "d") varde = ra.replace(/T00:00:00(\.0+)?Z?$/, "").replace("T", " ");
      else if (a.t === "b") varde = ra === "1" ? "true" : ra === "0" ? "false" : "";
      else if (ra !== "" && datum[Number(a.s ?? -1)] && Number(ra) >= 1) varde = excelDatum(Number(ra), bas1904);
      else varde = talText(ra);
      const index = a.r ? kolumnindex(a.r) : rad.length;
      while (rad.length < index) rad.push("");
      rad[index] = varde;
    }
    rader.push(rad);
  }
  return rader;
}

async function lasXlsx(bytes: Uint8Array): Promise<Blad[]> {
  const katalog = zipKatalog(bytes);
  const bok = await zipText(bytes, katalog.get("xl/workbook.xml"));
  // En .ods eller .docx är också en zip, men ingen arbetsbok vi läser.
  if (!bok) throw new ImportFel("format");
  const relationer = new Map<string, { typ: string; mal: string }>();
  for (const m of (await zipText(bytes, katalog.get("xl/_rels/workbook.xml.rels"))).matchAll(/<(?:\w+:)?Relationship\b([^>]*)>/g)) {
    const a = attribut(m[1]);
    const mal = (a.Target ?? "").replace(/^\/xl\//, "").replace(/^\//, "");
    relationer.set(a.Id, { typ: a.Type ?? "", mal: `xl/${mal}` });
  }
  const mal = (slut: string, forval: string) =>
    [...relationer.values()].find((r) => r.typ.endsWith(slut))?.mal ?? forval;

  const strangar = [
    ...(await zipText(bytes, katalog.get(mal("/sharedStrings", "xl/sharedStrings.xml")))).matchAll(
      /<(?:\w+:)?si\b[^>]*?(?:\/>|>([\s\S]*?)<\/(?:\w+:)?si>)/g
    )
  ].map((m) => textdelar(m[1] ?? ""));
  const datum = datumstilar(await zipText(bytes, katalog.get(mal("/styles", "xl/styles.xml"))));
  const bas1904 = /<(?:\w+:)?workbookPr\b[^>]*date1904="(?:1|true)"/.test(bok);

  const blad: Blad[] = [];
  const dolda: Blad[] = [];
  for (const m of bok.matchAll(/<(?:\w+:)?sheet\b([^>]*)>/g)) {
    const a = attribut(m[1]);
    const post = katalog.get(relationer.get(a["r:id"] ?? a.id ?? "")?.mal ?? "");
    if (!post) continue;
    const rader = stada(bladrader(await zipText(bytes, post), strangar, datum, bas1904));
    if (rader.length === 0) continue;
    (a.state && a.state !== "visible" ? dolda : blad).push({ namn: a.name ?? "", rader });
  }
  return blad.length ? blad : dolda;
}

// ---------------------------------------------- HTML och XML Spreadsheet 2003

function lasHtml(text: string): Blad[] {
  const rader = [...text.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)].map((tr) =>
    [...tr[1].matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi)].map((c) =>
      avkodaEntiteter(c[1].replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "")).replace(/[ \t]+/g, " ")
    )
  );
  return [{ namn: "", rader: stada(rader) }];
}

function lasXml2003(text: string): Blad[] {
  const blad: Blad[] = [];
  for (const ark of text.matchAll(/<(?:\w+:)?Worksheet\b([^>]*)>([\s\S]*?)<\/(?:\w+:)?Worksheet>/g)) {
    const rader: string[][] = [];
    for (const radtraff of ark[2].matchAll(/<(?:\w+:)?Row\b[^>]*?(?:\/>|>([\s\S]*?)<\/(?:\w+:)?Row>)/g)) {
      const rad: string[] = [];
      for (const c of (radtraff[1] ?? "").matchAll(/<(?:\w+:)?Cell\b([^>]*?)(?:\/>|>([\s\S]*?)<\/(?:\w+:)?Cell>)/g)) {
        const index = Number(attribut(c[1])["ss:Index"] ?? 0);
        while (index && rad.length < index - 1) rad.push("");
        const data = /<(?:\w+:)?Data\b([^>]*)>([\s\S]*?)<\/(?:\w+:)?Data>/.exec(c[2] ?? "");
        const varde = avkodaEntiteter((data?.[2] ?? "").replace(/<[^>]+>/g, ""));
        rad.push(/DateTime/.test(data?.[1] ?? "") ? varde.replace(/T00:00:00(\.0+)?$/, "").replace("T", " ") : varde);
      }
      rader.push(rad);
    }
    const stadade = stada(rader);
    if (stadade.length) blad.push({ namn: attribut(ark[1])["ss:Name"] ?? "", rader: stadade });
  }
  return blad;
}

// ---------------------------------------------------------------- ingången

export async function lasImportfil(bytes: Uint8Array): Promise<Importfil> {
  if (bytes.length > MAX_FILSTORLEK) throw new ImportFel("stor");
  const ar = (...magi: number[]) => magi.every((byte, i) => bytes[i] === byte);
  if (ar(0xd0, 0xcf, 0x11, 0xe0)) throw new ImportFel("xls");
  if (ar(0x25, 0x50, 0x44, 0x46)) throw new ImportFel("format"); // %PDF

  let fil: Importfil;
  if (ar(0x50, 0x4b, 0x03, 0x04)) {
    fil = { format: "xlsx", blad: await lasXlsx(bytes) };
  } else {
    const { text, kodning } = avkoda(bytes);
    const borjan = text.slice(0, 2000);
    // Styrtecken som inte hör hemma i text: en binär fil med fel ändelse.
    if (/[\u0000-\u0008\u000e-\u001f]/.test(borjan)) throw new ImportFel("format");
    if (/urn:schemas-microsoft-com:office:spreadsheet/.test(borjan)) fil = { format: "xml", kodning, blad: lasXml2003(text) };
    else if (/^\s*</.test(borjan) && /<table\b/i.test(text)) fil = { format: "html", kodning, blad: lasHtml(text) };
    else if (/^\s*<(\?xml|!doctype|html)\b/i.test(borjan)) throw new ImportFel("format");
    else fil = { format: "csv", kodning, blad: [{ namn: "", rader: stada(parseCsv(text)) }] };
  }
  fil.blad = fil.blad.filter((b) => b.rader.length > 0);
  if (fil.blad.length === 0) throw new ImportFel("tom");
  return fil;
}
