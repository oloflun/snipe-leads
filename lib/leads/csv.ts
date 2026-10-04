/**
 * Minimal CSV-parser med citattecken ("" som escape) och radbrytningar inne i
 * fält. Avgränsaren gissas ur rubrikraden: svensk Excel exporterar semikolon,
 * de flesta CRM komma, några tab.
 *
 * Flyttad ur components/crm/CrmDemo.tsx (Fas 10) så att CRM-demon och
 * CSV-importen i Iris › Listor läser filer på exakt samma sätt.
 */
export function parseCsv(ratext: string): string[][] {
  const text = ratext.replace(/^﻿/, "");
  const forstaRad = text.slice(0, text.indexOf("\n") === -1 ? text.length : text.indexOf("\n"));
  const kandidater: Array<[string, number]> = [";", ",", "\t"].map((d) => [d, forstaRad.split(d).length - 1]);
  kandidater.sort((a, b) => b[1] - a[1]);
  const avgransare = kandidater[0][1] > 0 ? kandidater[0][0] : ";";

  const rader: string[][] = [];
  let rad: string[] = [];
  let falt = "";
  let iCitat = false;
  for (let i = 0; i < text.length; i++) {
    const tecken = text[i];
    if (iCitat) {
      if (tecken === '"') {
        if (text[i + 1] === '"') {
          falt += '"';
          i++;
        } else {
          iCitat = false;
        }
      } else {
        falt += tecken;
      }
    } else if (tecken === '"') {
      iCitat = true;
    } else if (tecken === avgransare) {
      rad.push(falt);
      falt = "";
    } else if (tecken === "\n" || tecken === "\r") {
      if (tecken === "\r" && text[i + 1] === "\n") i++;
      rad.push(falt);
      falt = "";
      if (rad.some((f) => f.trim() !== "")) rader.push(rad);
      rad = [];
    } else {
      falt += tecken;
    }
  }
  rad.push(falt);
  if (rad.some((f) => f.trim() !== "")) rader.push(rad);
  return rader;
}
