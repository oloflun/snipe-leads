/**
 * Organisationsnummer, validerat i webbläsaren.
 *
 * SPEGLAR `snajp-support/app/leads/orgnr.py`. Att samma regel finns på två
 * ställen är en risk — de kan glida isär — och görs ändå, av ett skäl som
 * väger tyngre: ett formulär som först efter inskickning säger "kontrollsiffran
 * stämmer inte" är ett formulär man skriver fel i två gånger. Fältet ska säga
 * ifrån medan markören står kvar i det.
 *
 * Serversidan validerar OM. Den här filen är hjälp, inte skydd — det som
 * skyddar är alltid Python-sidan, eftersom klientkod går att kringgå.
 *
 * Ändras reglerna här måste orgnr.py ändras likadant, och tvärtom.
 */

const PERSONNUMMER_SVAR =
  "Det där ser ut som ett personnummer, inte ett organisationsnummer. Skriv inte in ditt " +
  "personnummer här — vi behöver bolagets nummer, det som står på fakturor och registreringsbeviset.";

/** Publika e-postdomäner säger ingenting om var bolaget har sin sajt. */
const PUBLIKA_EPOSTDOMANER = new Set([
  "gmail.com", "hotmail.com", "outlook.com", "live.se", "live.com",
  "yahoo.com", "icloud.com", "telia.com", "bredband.net", "spray.se",
  "comhem.se", "me.com", "msn.com"
]);

export function normaliseraOrgnr(rå: string): string {
  const siffror = (rå ?? "").replace(/\D/g, "");
  // Prefixet 16 är en sekelmarkör ur myndighetsregister och ska bort innan
  // kontrollsiffran räknas, annars faller giltiga nummer.
  return siffror.length === 12 && siffror.startsWith("16") ? siffror.slice(2) : siffror;
}

function luhnStammer(siffror: string): boolean {
  let summa = 0;
  const omvänt = siffror.split("").reverse();
  for (let i = 0; i < omvänt.length; i += 1) {
    let värde = Number(omvänt[i]);
    if (i % 2 === 1) {
      värde *= 2;
      if (värde > 9) värde -= 9;
    }
    summa += värde;
  }
  return summa % 10 === 0;
}

/** Returnerar ett felmeddelande, eller null när numret är välformat. */
export function orgnrFel(rå: string): string | null {
  const siffror = normaliseraOrgnr(rå);

  if (!siffror) return "Fyll i organisationsnumret.";

  // Före längdkontrollen: ett tolvsiffrigt personnummer hade annars fällts som
  // "fel längd", och användaren hade rättat längden i stället för att förstå
  // att fältet inte ska innehålla ett personnummer alls.
  if (siffror.length === 12 && (siffror.startsWith("19") || siffror.startsWith("20"))) {
    return PERSONNUMMER_SVAR;
  }
  if (siffror.length === 10 && Number(siffror[2]) < 2) {
    return PERSONNUMMER_SVAR;
  }

  if (siffror.length !== 10) {
    return `Ett organisationsnummer har tio siffror, det här har ${siffror.length}. Skriv det som 556824-9022.`;
  }

  if (!luhnStammer(siffror)) {
    return "Kontrollsiffran stämmer inte, vilket nästan alltid betyder ett skrivfel. Kontrollera numret mot en faktura eller registreringsbeviset.";
  }

  return null;
}

export function formateraOrgnr(rå: string): string {
  const siffror = normaliseraOrgnr(rå);
  return siffror.length === 10 ? `${siffror.slice(0, 6)}-${siffror.slice(6)}` : rå;
}

/**
 * Gissar bolagets webbplats ur en e-postadress, så att kunden slipper fylla i
 * en uppgift vi nästan alltid kan räkna fram. Gissningen ska föreslå, aldrig
 * bestämma — fältet är redigerbart.
 */
export function harledWebbplats(epost: string): string {
  const text = (epost ?? "").trim().toLowerCase();
  if (!text.includes("@")) return "";
  const domän = text.split("@").pop() ?? "";
  if (!domän || !domän.includes(".") || PUBLIKA_EPOSTDOMANER.has(domän)) return "";
  return `https://${domän}`;
}
