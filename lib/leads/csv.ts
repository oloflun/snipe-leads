/**
 * CSV-parser med citattecken ("" som escape) och radbrytningar inne i fält.
 *
 * Flyttad ur components/crm/CrmDemo.tsx (Fas 10) så att CRM-demon och
 * listimporten läser filer på exakt samma sätt. Hårdtestad 2026-11-23 mot
 * exporter ur ett tjugotal CRM (lib/leads/fixtures/crm-export):
 *
 *   - Avgränsaren avgörs över de första posterna, inte bara rubrikraden, och
 *     med citaten lästa: en rubrik som "Bolag, namn" i en semikolonfil gav
 *     förut komma som avgränsare och en enda kolumn.
 *   - `sep=;` på första raden (Excels egen anvisning) styr och stryks.
 *   - Ett citattecken öppnar bara ett citat i början av ett fält och stänger
 *     det bara före en avgränsare eller radbrytning. `Bygg "Kalle" AB` och
 *     `5" skärm` är vanlig text; förut slukade ett udda citattecken resten av
 *     filen i ett enda fält.
 */

const AVGRANSARE = [";", ",", "\t", "|"] as const;

/** Posterna i `text` för en given avgränsare. Tomma rader hoppas över. */
function poster(text: string, avgransare: string, tak = Number.POSITIVE_INFINITY): string[][] {
  const rader: string[][] = [];
  let rad: string[] = [];
  let falt = "";
  let iCitat = false;
  // Sant medan fältet bara består av blanktecken: där får ett citat börja.
  let faltStart = true;

  const slutRad = () => {
    rad.push(falt);
    falt = "";
    faltStart = true;
    if (rad.some((f) => f.trim() !== "")) rader.push(rad);
    rad = [];
  };

  for (let i = 0; i < text.length && rader.length < tak; i++) {
    const tecken = text[i];
    if (iCitat) {
      if (tecken !== '"') {
        falt += tecken;
      } else if (text[i + 1] === '"') {
        falt += '"';
        i++;
      } else {
        // Citatet stänger bara om fältet tar slut här (blanktecken tillåts
        // emellan). Annars är tecknet ett oescapat citat inne i texten.
        let j = i + 1;
        while (text[j] === " ") j++;
        const nasta = text[j];
        if (nasta === undefined || nasta === avgransare || nasta === "\n" || nasta === "\r") {
          iCitat = false;
          i = j - 1;
        } else {
          falt += '"';
        }
      }
    } else if (tecken === '"' && faltStart) {
      iCitat = true;
      faltStart = false;
      falt = "";
    } else if (tecken === avgransare) {
      rad.push(falt);
      falt = "";
      faltStart = true;
    } else if (tecken === "\n" || tecken === "\r") {
      if (tecken === "\r" && text[i + 1] === "\n") i++;
      slutRad();
    } else {
      falt += tecken;
      if (tecken !== " ") faltStart = false;
    }
  }
  if (rader.length < tak && (falt !== "" || rad.length > 0)) slutRad();
  return rader;
}

/**
 * Avgränsaren som ger flest poster med samma kolumnantal (fler än en kolumn)
 * bland de trettio första. Vid lika vinner den med flest kolumner. Minst två
 * poster och tre av tio måste dela kolumnantalet: ett komma i ett enda
 * bolagsnamn gör inte en lista med en kolumn till en kommafil. Håller ingen
 * avgränsare är filen en enda kolumn, och då väljs ett tecken som inte finns
 * i texten.
 */
export function gissaAvgransare(text: string): string {
  let bast: { avgransare: string; poang: number } | null = null;
  for (const avgransare of AVGRANSARE) {
    const antal = new Map<number, number>();
    const prov = poster(text, avgransare, 30);
    for (const rad of prov) {
      if (rad.length > 1) antal.set(rad.length, (antal.get(rad.length) ?? 0) + 1);
    }
    let poang = 0;
    for (const [kolumner, rader] of antal) {
      const haller = prov.length === 1 || (rader >= 2 && rader >= prov.length * 0.3);
      if (haller) poang = Math.max(poang, rader * 1000 + kolumner);
    }
    if (poang > (bast?.poang ?? 0)) bast = { avgransare, poang };
  }
  return bast?.avgransare ?? AVGRANSARE.find((a) => !text.includes(a)) ?? ";";
}

export function parseCsv(ratext: string): string[][] {
  let text = ratext.charCodeAt(0) === 0xfeff ? ratext.slice(1) : ratext;
  const sep = /^sep=(.)\r?\n/i.exec(text);
  if (sep) text = text.slice(sep[0].length);
  return poster(text, sep ? sep[1] : gissaAvgransare(text));
}
